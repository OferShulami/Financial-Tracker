import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src import config

class SheetsHandler:

    def __init__(self, spreadsheet_id: str, credentials_path: str):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.service = self._authenticate()


    def _authenticate(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"❌ לא נמצא קובץ: {self.credentials_path}")
        creds = service_account.Credentials.from_service_account_file(self.credentials_path, scopes=self.scopes)
        return build('sheets', 'v4', credentials=creds)


    def test_connection(self):
        """פונקציית בדיקה: מנסה לקרוא את הכותרת של הגיליון"""
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            title = sheet_metadata.get('properties', {}).get('title')
            print(f"✅ התחברות הצליחה! שם הגיליון: {title}")
            return True
        except Exception as e:
            print(f"❌ שגיאה בהתחברות לגוגל שיטס: {e}")
            return False


    def get_sheet_data(self, sheet_name: str):
        try:
            range_name = f"'{sheet_name}'!A:Z"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            return result.get('values', [])
        except Exception as e:
            print(f"❌ שגיאה בשליפת נתונים: {e}")
            return []


    def find_month_row(self, data, month_name):
        """חיפוש גמיש של שם החודש בכל הגיליון"""
        print(f"DEBUG: מחפש חודש: '{month_name}'...")
        search_term = str(month_name).strip()
        for i, row in enumerate(data):
            row_str = " ".join([str(cell).strip() for cell in row])
            if search_term in row_str:
                print(f"DEBUG: ✅ חודש נמצא בשורה {i + 1}")
                return i + 1
        print(f"DEBUG: ❌ חודש '{month_name}' לא נמצא!")
        return None


    def find_category_row(self, data, category_name, start_row):
        """חיפוש קטגוריה אך ורק בעמודה A החל משורה מסוימת"""
        print(f"DEBUG: מחפש קטגוריה '{category_name}' בעמודה A החל משורה {start_row}...")
        search_term = str(category_name).strip()
        for i in range(start_row - 1, len(data)):
            row = data[i]
            if not row: continue
            col_a = str(row[0]).strip()
            if col_a == search_term:
                print(f"DEBUG: ✅ קטגוריה נמצאה בשורה {i + 1}")
                return i + 1
        print(f"DEBUG: ❌ קטגוריה '{category_name}' לא נמצאה בעמודה A.")
        return None


    def find_transaction_row(self, data, month_row, tx_desc, tx_amount, tx_date, category_name):
        """מרכזת את החיפוש ומחזירה מיקום וסטטוס"""
        anchor = self.find_category_row(data, category_name, month_row)

        # Fallback לדלק בתוך חובה אם לא נמצאה קטגוריית דלק עצמאית
        if not anchor and category_name == "דלק":
            print("DEBUG: קטגוריית דלק לא נמצאה, מנסה לחפש בתוך 'חובה'...")
            anchor = self.find_category_row(data, "חובה", month_row)

        if not anchor:
            return None, "CATEGORY_NOT_FOUND", False

        return self._find_target_row(data, anchor, tx_desc, tx_amount, tx_date)


    def _find_target_row(self, data, anchor_row, tx_desc, tx_amount, tx_date):
        """
        הלוגיקה הפנימית:
        - בודקת כפילויות ב-D.
        - עוצרת ב'קיר' ב-A.
        - מוצאת חור פנוי ב-B.
        """
        first_empty_row = None
        current_cat_name = str(data[anchor_row - 1][0]).strip()

        for i in range(anchor_row, len(data)):
            row = data[i]
            col_a = str(row[0]).strip() if len(row) > 0 else ""
            col_b = str(row[1]).strip() if len(row) > 1 else ""
            col_d = str(row[3]).strip() if len(row) > 3 else ""

            # 1. זיהוי 'קיר' (קטגוריה חדשה ב-A)
            if col_a != "" and col_a != current_cat_name:
                print(f"DEBUG: זוהה קיר (קטגוריה '{col_a}') בשורה {i + 1}")
                if first_empty_row:
                    return first_empty_row, "ADD_NEW", False
                return i + 1, "ADD_NEW", True

            # 2. מניעת כפילויות (בדיקה ב-D)
            if col_d != "" and tx_desc in col_d:
                try:
                    price_val = float(str(row[4]).replace('₪', '').replace(',', '').strip())
                    if abs(tx_amount - price_val) <= 2.5:
                        print(f"DEBUG: נמצאה כפילות בשורה {i + 1}")
                        return i + 1, "EXISTS", False
                except:
                    pass

            # 3. זיהוי שורה פנויה לפי עמודה B (הבקשה שלך)
            if col_b == "" and first_empty_row is None:
                first_empty_row = i + 1
                print(f"DEBUG: סומנה שורה פנויה פוטנציאלית ב-{i + 1}")

        return (first_empty_row if first_empty_row else len(data) + 1), "ADD_NEW", False



    def update_cell(self, sheet_name, cell_address, value):
        try:
            range_name = f"'{sheet_name}'!{cell_address}"
            body = {'values': [[value]]}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id, range=range_name,
                valueInputOption='USER_ENTERED', body=body).execute()
            return True
        except Exception as e:
            print(f"❌ שגיאה ב-update: {e}")
            return False


    def _get_sheet_id(self, sheet_name):
        """שולף את ה-ID הפנימי של הטאב (דרוש להזרקת שורות)"""
        meta = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        for s in meta.get('sheets', []):
            if s.get('properties', {}).get('title') == sheet_name:
                return s.get('properties', {}).get('sheetId')
        return None


    def insert_row(self, sheet_name, row_index):
        """יוצר רווח בגיליון על ידי הזרקת שורה פיזית"""
        try:
            s_id = self._get_sheet_id(sheet_name)
            request = {
                "insertDimension": {
                    "range": {"sheetId": s_id, "dimension": "ROWS", "startIndex": row_index - 1, "endIndex": row_index},
                    "inheritFromBefore": True
                }
            }
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                    body={'requests': [request]}).execute()
            return True
        except Exception as e:
            print(f"❌ שגיאה בהזרקת שורה: {e}")
            return False


    def _find_insertion_point(self, data, anchor_row):
        """
        סורקת את הקטגוריה מהעוגן ומטה כדי למצוא שורה פנויה או את סוף הקטגוריה.
        """
        first_empty_row = None
        current_category = str(data[anchor_row - 1][1]).strip()  # השם בעמודה B (למשל 'חובה')

        for i in range(anchor_row, len(data)):
            row = data[i]
            col_b = str(row[1]).strip() if len(row) > 1 else ""
            col_d = str(row[3]).strip() if len(row) > 3 else ""

            # בדיקה אם הגענו לקטגוריה הבאה (ה'קיר')
            # אם יש טקסט בעמודה B והוא שונה מהקטגוריה הנוכחית
            if col_b != "" and col_b != current_category:
                if first_empty_row:
                    return first_empty_row, False  # מצאנו חור קודם, נשתמש בו
                return i + 1, True  # אין חורים, חייבים להזריק פיזית מעל הקטגוריה הבאה

            # שמירת השורה הריקה הראשונה (בודקים את עמודה D - הפירוט)
            if col_d == "" and col_b == "" and first_empty_row is None:
                first_empty_row = i + 1

        return (first_empty_row if first_empty_row else len(data) + 1), False


    def _get_category_anchor(self, data, month_row, category_name):
        """מוצאת את שורת הכותרת של הקטגוריה (דלק או חובה)"""
        anchor = self.find_row_by_value(data, category_name, start_row=month_row)
        # Fallback: אם חיפשנו דלק ולא מצאנו, ננסה חובה
        if not anchor and category_name == "דלק":
            anchor = self.find_row_by_value(data, "חובה", start_row=month_row)
        return anchor


    def _find_target_row(self, data, anchor_row, tx_desc, tx_amount, tx_date):
        """
        מוצאת מיקום להוצאה לפי 'חוק המספור ב-B':
        1. בודקת כפילויות בעמודה D.
        2. מזהה שורה פנויה אם עמודה B ריקה.
        3. עוצרת כשיש טקסט חדש ב-A (קיר).
        """
        first_empty_row = None
        # השם של הקטגוריה הנוכחית נמצא בעמודה A בשורת העוגן (anchor_row)
        current_cat_name = str(data[anchor_row - 1][0]).strip()

        # הסריקה מתחילה שורה אחת אחרי הכותרת
        for i in range(anchor_row, len(data)):
            row = data[i]
            col_a = str(row[0]).strip() if len(row) > 0 else ""  # שם קטגוריה (חובה/בילוי)
            col_b = str(row[1]).strip() if len(row) > 1 else ""  # המספור (2, 3, 4...)
            col_d = str(row[3]).strip() if len(row) > 3 else ""  # תיאור העסקה

            # --- בדיקה 1: מניעת כפילויות (חייבים לבדוק ב-D) ---
            if col_d != "" and tx_desc in col_d:
                try:
                    price_val = float(str(row[4]).replace('₪', '').replace(',', '').strip())
                    if abs(tx_amount - price_val) <= 2.5:
                        col_c_date = str(row[2]).strip() if len(row) > 2 else ""
                        if col_c_date == tx_date:
                            return i + 1, "EXISTS", False
                        return i + 1, "ASK_USER", False
                except:
                    pass

            # --- בדיקה 2: זיהוי 'קיר' (קטגוריה חדשה ב-A) ---
            # אם מצאנו טקסט ב-A והוא לא הקטגוריה שלנו - הגענו לסוף הבלוק
            if col_a != "" and col_a != current_cat_name:
                if first_empty_row:
                    return first_empty_row, "ADD_NEW", False
                # אם הגענו לקיר ולא היה אף תא ריק ב-B בדרך -> צריך להזריק שורה
                return i + 1, "ADD_NEW", True

            # --- בדיקה 3: זיהוי שורה פנויה לפי עמודה B (הבקשה שלך) ---
            # אם עמודה B ריקה, זה אומר שאין פה מספור של עסקה וזו שורה פנויה
            if col_b == "" and first_empty_row is None:
                # מוודא שזו לא שורת כותרת בטעות (בדיקה כפולה מול col_a)
                if col_a == "":
                    first_empty_row = i + 1

        return (first_empty_row if first_empty_row else len(data) + 1), "ADD_NEW", False


    def find_end_of_category(self, data, anchor_row):
        """מוצאת את סוף הבלוק על ידי זיהוי שינוי בטקסט בעמודה A"""
        current_cat = str(data[anchor_row - 1][0]).strip()
        for i in range(anchor_row, len(data)):
            col_a = str(data[i][0]).strip() if len(data[i]) > 0 else ""
            if col_a != "" and col_a != current_cat:
                return i + 1
        return len(data) + 1
