import threading
import time
import os
import sys

# 1. הגדרת נתיבים (מוודא שפייתון מוצא את תיקיית ה-src שלך ב-Mac)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.services.bot_manager import TelegramBot


def run_test():
    # 2. אתחול הבוט (ה-Handlers נרשמים אוטומטית ב-__init__)
    print("🤖 מאתחל את הבוט...")
    bot_manager = TelegramBot()

    # 3. הפעלת ה-Polling ב-Thread נפרד
    # זה ה"קו טלפון" שמאפשר לבוט להקשיב לטלגרם בזמן שהקוד הראשי מחכה
    polling_thread = threading.Thread(target=bot_manager.bot.infinity_polling, daemon=True)
    polling_thread.start()

    print(f"📡 הבוט מחובר! שולח הודעה ל-ID: {config.OFER_ID}")
    print("⚠️  שים לב: אם הבוט לא מגיב, וודא שאין סקריפט אחר של הבוט שרץ ברקע.")

    # 4. נתוני דוגמה לעסקה
    sample_details = "10/04/2026 | Super-Pharm | ₪89.90"

    try:
        print("\n⏳ שולח כפתורים... עבור לטלגרם ותלחץ על בחירה!")

        # הקריאה לפונקציה שעוצרת ומחכה ללחיצה שלך
        start_time = time.time()
        selected_sheet = bot_manager.get_user_sheet_selection(config.OFER_ID, sample_details)
        end_time = time.time()

        # 5. הצגת התוצאה שחזרה מהפונקציה
        if selected_sheet:
            print(f"\n✅ הבדיקה הצליחה!")
            print(f"📊 הגיליון שנבחר: {selected_sheet}")
            print(f"⏱️ זמן תגובה: {round(end_time - start_time, 2)} שניות")
        else:
            print("\n❌ לא התקבלה תשובה תקינה.")

    except KeyboardInterrupt:
        print("\n🛑 הבדיקה הופסקה על ידי המשתמש.")
    except Exception as e:
        print(f"\n❌ שגיאה במהלך הבדיקה: {e}")

    print("\n🏁 סיום בדיקה.")


if __name__ == "__main__":
    run_test()