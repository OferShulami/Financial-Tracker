import io
import sys
import os
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.sheets_handler import SheetsHandler
from src.services.processor import BudgetProcessor
from src.services.bot_manager import TelegramBot, setup_handlers
from src import config


def run_integration(file_path, user_id):
    # 1. אתחול ותשתית
    handler = SheetsHandler(config.SPREADSHEET_ID, config.CREDENTIALS_PATH)
    processor = BudgetProcessor(handler, config.MAPPING_PATH)
    bot = TelegramBot()
    setup_handlers(bot)

    # אבטחה: בדיקה ראשונית לפני שבכלל נוגעים בקובץ
    if not bot.check_authorization(user_id):
        return

    # הפעלת האזנה לבוט ברקע (בשביל לקלוט את הלחיצות שלך)
    threading.Thread(target=bot.bot.infinity_polling, daemon=True).start()

    # 2. קריאת הקובץ
    raw_df = processor._parse_isracard_data(file_path)
    if raw_df.empty:
        bot.send_message(user_id, "❌ הקובץ ששלחת לא קריא או ריק.")
        return

    transactions = raw_df.to_dict('records')
    bot.send_message(user_id, f"🚀 מצאתי {len(transactions)} עסקאות. מתחילים...")

    last_sheet = None
    current_data = None

    # 3. הלולאה המרכזית - עסקה אחרי עסקה
    for tx in transactions:
        # א. בחירת גיליון (🏠 בית / 👤 עופר / 👤 שי)
        tx_info = f"{tx['date'].strftime('%d/%m')} | {tx['description']} | ₪{tx['amount']}"
        sheet_name = bot.get_user_sheet_selection(user_id, tx_info)

        if sheet_name is None:
            return

        # ב. רענון Snapshot רק אם החלפנו גיליון
        if sheet_name != last_sheet:
            current_data = handler.get_sheet_data(sheet_name)
            last_sheet = sheet_name

        # ג. חיפוש התאמה מדויקת ב-JSON
        existing = processor.find_existing_mapping(tx['description'], sheet_name)

        if existing is None:
            display_name = bot.ask_for_text(user_id, f"✨ עסק חדש!\nבנק: `{tx['description']}`\nאיך לקרוא לו?")
            category = bot.ask_for_text(user_id, f"📂 לאיזה קטגוריה לשייך את '{display_name}'?")
        else:
            display_name = existing['display_name']
            category = bot.get_category_selection(user_id, display_name, existing['categories'])

            if category == "OTHER":
                display_name = bot.ask_for_text(user_id, f"📝 שנה שם תצוגה (נוכחי: `{display_name}`):")
                category = bot.ask_for_text(user_id, f"📂 הזן קטגוריה חדשה עבור '{display_name}':")

        # ד. למידה: עדכון ה-JSON
        processor.update_mapping(tx['description'], category, display_name, sheet_name)

        # ה. מציאת מיקום בגיליון
        month_name = processor.get_target_month_name(tx['date'])
        month_row = handler.find_month_row(current_data, month_name)

        if not month_row:
            bot.send_message(user_id, f"❓ חודש {month_name} לא נמצא בגיליון '{sheet_name}'. מדלג.")
            continue

        # --- ו. בדיקת כפילויות חכמה (Fuzzy Match) ---
        tx_date_str = tx['date'].strftime('%d/%m/%Y')

        # אנחנו מעבירים גם את התאריך כדי לבדוק כפילויות בטווח מחיר או תאריך
        if handler.check_duplicate(current_data, month_row, display_name, tx['amount'], tx_date_str):
            bot.send_message(user_id, f"🔍 '{display_name}' זוהה ככפילות (דומה מאוד לרשומה קיימת). מדלג.")
            continue
        # --------------------------------------------

        # ז. מציאת שורה והזרקה (אם אין מקום פנוי בבלוק)
        target_row, needs_insert = handler.find_next_available_row(current_data, month_row)
        if needs_insert:
            handler.insert_row(sheet_name, target_row)

        # ח. כתיבת הנתונים הסופית
        handler.update_cell(sheet_name, f"C{target_row}", tx_date_str)
        handler.update_cell(sheet_name, f"D{target_row}", display_name)
        handler.update_cell(sheet_name, f"E{target_row}", tx['amount'])

        bot.send_message(user_id, f"✅ נרשם ב-{sheet_name}: {display_name}")

        # ט. עדכון ה-Snapshot המקומי כדי שהעסקה הבאה תזהה את השורה התפוסה
        current_data = handler.get_sheet_data(sheet_name)

    bot.send_message(user_id, "🏁 כל העסקאות סונכרנו בהצלחה!")

def start_bot():
    # 1. אתחול הבוט והגדרת ה-Handlers (Callback וטקסט)
    bot_manager = TelegramBot()
    bot = bot_manager.bot
    setup_handlers(bot_manager)

    print("🤖 הבוט באוויר... מחכה לקובץ אקסל מישראכרט.")

    @bot.message_handler(content_types=['document'])
    def handle_excel_file(message):
        user_id = message.from_user.id
        file_name = message.document.file_name

        # 2. בדיקת סיומת הקובץ
        if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            bot.reply_to(message, "❌ שגיאה: אנא שלח קובץ אקסל (xlsx) בלבד.")
            return

        bot.send_message(user_id, f"⏳ מעבד את '{file_name}' ישירות מהזיכרון... שניה אחת.")

        try:
            # 3. הורדת הקובץ מהשרת של טלגרם לתוך משתנה (ולא לדיסק!)
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # 4. יצירת אובייקט "דמוי-קובץ" בזיכרון (BytesIO)
            # זה מחליף את הצורך ב-local_path ובשמירה פיזית
            excel_stream = io.BytesIO(downloaded_file)

            # 5. הפעלת מנוע הסנכרון
            # שלחנו את ה-Stream במקום נתיב לקובץ
            run_integration(excel_stream, user_id)

        except Exception as e:
            bot.send_message(user_id, f"⚠️ תקלה במערכת: {str(e)}")
            print(f"Error during integration: {e}")

    # 6. הפעלת האזנה אינסופית
    bot.infinity_polling()

if __name__ == "__main__":
    start_bot()