import pandas as pd
import json
import warnings
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.utils.constants import MONTH_MAP
from src import config

# השתקת אזהרות openpyxl
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


class BudgetProcessor:
    def __init__(self, sheets_handler=None, mapping_path: Optional[str] = None):
        self.sheets_handler = sheets_handler
        target_path = mapping_path or config.MAPPING_PATH
        self.mapping_path = Path(target_path)
        self.mapping = self._load_mapping()

    def _load_mapping(self):
        """טוענת את ה-JSON מהדיסק"""
        try:
            if not self.mapping_path.exists():
                return {"shared": {"keywords": {}}, "ofer": {"keywords": {}}, "shay": {"keywords": {}}}
            with open(self.mapping_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ שגיאה בטעינת המיפוי: {e}")
            return {"shared": {"keywords": {}}, "ofer": {"keywords": {}}, "shay": {"keywords": {}}}

    def find_existing_mapping(self, description: str, sheet_name: str):
        """
        מחפשת התאמה מדויקת ב-JSON עבור תיאור העסקה הגולמי.
        """
        mapping_keys = {"בית": "shared", "עופר": "ofer", "שי": "shay"}
        target_section = mapping_keys.get(sheet_name, "shared")

        # שליפת רשימת העסקים (Keywords) מהמדור הרלוונטי
        keywords = self.mapping.get(target_section, {}).get('keywords', {})

        # ניקוי רווחים בלבד מהתיאור שהגיע מהבנק
        clean_description = description.strip()

        for key, info in keywords.items():
            # בדיקה של התאמה מדויקת (כולל אותיות גדולות/קטנות וסימנים מיוחדים)
            if key.strip() == clean_description:
                return {
                    "display_name": info['display_name'],
                    "categories": info.get('categories', [])
                }

        # אם אין התאמה מושלמת - העסק ייחשב כחדש
        return None

    def get_user_classification(self, user_id, tx_description, existing_mapping):
        """
        מנהלת דיאלוג לקביעת קטגוריה ושם תצוגה.
        """
        from telebot import types

        # תרחיש א': העסק כבר מוכר
        if existing_mapping:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(f"✅ השתמש ב '{existing_mapping['category']}'",
                                           callback_data=f"cat_{existing_mapping['category']}"),
                types.InlineKeyboardButton("✏️ שנה קטגוריה", callback_data="change_cat")
            )

            self.send_message(user_id,
                              f"🔍 מצאתי את העסק **{existing_mapping['display_name']}**.\n"
                              f"הקטגוריה השמורה: **{existing_mapping['category']}**.\n"
                              f"מה לעשות?",
                              reply_markup=markup, parse_mode="Markdown")

            choice = self._loop_until_response(user_id)

            if choice != "change_cat":
                # המשתמש אישר את הקטגוריה הקיימת
                return existing_mapping['category'], existing_mapping['display_name']

        # תרחיש ב': עסק חדש או שהמשתמש בחר "שנה קטגוריה"
        self.send_message(user_id, f"📝 הזן קטגוריה עבור: **{tx_description}**")
        category = self._loop_until_text_response(user_id)  # פונקציה חדשה שנממש

        self.send_message(user_id, f"📛 איזה שם תצוגה תרצה לתת?")
        display_name = self._loop_until_text_response(user_id)

        return category, display_name

    def update_mapping(self, business_name: str, category: str, display_name: str, user_id: str):
        """מעדכנת את ה-JSON ושומרת לדיסק"""
        user_key = "ofer" if str(user_id) == str(config.OFER_ID) else "shay"

        if user_key not in self.mapping:
            self.mapping[user_key] = {"keywords": {}}

        keywords = self.mapping[user_key]["keywords"]

        if business_name not in keywords:
            keywords[business_name] = {"display_name": display_name, "categories": [category]}
        else:
            if category not in keywords[business_name]["categories"]:
                keywords[business_name]["categories"].append(category)

        self._save_mapping()
        print(f"✅ המיפוי עודכן ל-{user_key}: {business_name} -> {category}")

    def _save_mapping(self):
        """שמירה פיזית ל-JSON"""
        try:
            with open(self.mapping_path, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"❌ שגיאה בשמירת הקובץ: {e}")

    def _parse_isracard_data(self, file_path) -> pd.DataFrame:
        """Parses an Isracard Excel export into a structured DataFrame.

            This method specifically handles the Isracard format by skipping metadata headers,
            standardizing Hebrew column names to English keys, and cleaning numerical 
            and date values for consistent tracking.

            Args:
                file_path (Union[str, BytesIO]): The path to the file or a byte stream 
                    of the Excel file from Telegram memory.

            Returns:
                pd.DataFrame: A cleaned DataFrame containing ['date', 'description', 'amount'].
                             Returns an empty DataFrame if parsing fails.
            """
        try:
            # פאנדס יודע לקרוא גם אובייקט BytesIO וגם נתיב סטרינג
            df = pd.read_excel(file_path, header=9)

            column_mapping = {'תאריך רכישה': 'date', 'שם בית עסק': 'description', 'סכום חיוב': 'amount'}
            df = df.rename(columns=column_mapping)
            df = df[['date', 'description', 'amount']].dropna(subset=['date', 'amount'])

            df['date'] = pd.to_datetime(df['date'], format='%d.%m.%y', errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').abs()
            return df[df['amount'] != 0].dropna(subset=['date'])
        except Exception as e:
            print(f"❌ שגיאה בקריאת האקסל: {e}")
            return pd.DataFrame()

    def get_target_month_name(self, dt):
        """המרה לפורמט 'מרץ 26'"""
        if not dt or not hasattr(dt, 'month'): return None
        heb_month = MONTH_MAP.get(f"{dt.month:02d}")
        return f"{heb_month} {str(dt.year)[-2:]}" if heb_month else None

    def _is_duplicate(self, transaction: Dict, existing_data: pd.DataFrame) -> bool:
        """בדיקת כפילות ב-Snapshot"""
        if existing_data is None or existing_data.empty: return False
        match = existing_data[
            (existing_data['date'] == transaction['date']) &
            (existing_data['display_name'] == transaction['display_name']) &
            (existing_data['amount'] == transaction['amount'])
            ]
        return not match.empty