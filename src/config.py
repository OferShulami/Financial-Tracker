import os
from pathlib import Path
from dotenv import load_dotenv

# 1. טעינת משתני סביבה מהקובץ .env
load_dotenv()

# 2. חישוב נתיב השורש (Root Directory)
# __file__ הוא הנתיב של הקובץ הנוכחי (src/config.py)
# .parent לוקח אותנו ל-src, וה-.parent השני לוקח אותנו לתיקייה הראשית
BASE_DIR = Path(__file__).resolve().parent.parent

# 3. הגדרת נתיבי התיקיות
CONFIG_DIR = BASE_DIR / "config"
LOGS_PATH = BASE_DIR / "logs"
IMPORTS_PATH = BASE_DIR / "imports"

# 4. נתיבים לקבצים ספציפיים (JSON)
MAPPING_PATH = CONFIG_DIR / "mapping.json"
CREDENTIALS_PATH = CONFIG_DIR / "service_account.json"

# 5. הגדרות API מתוך ה-.env
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
# אנחנו משתמשים בשם אחד קבוע לטוקן של הבוט
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# 6. הגדרת משתמשים (IDs של טלגרם מתוך ה-.env)
OFER_ID = int(os.getenv("USER_ID_OFER", 0))
SHAY_ID = int(os.getenv("USER_ID_SHAY", 0))

# רשימה לבדיקה מהירה של הרשאות
AUTHORIZED_USERS = [OFER_ID, SHAY_ID]

# מיפוי שמות (נשאר בקוד כי זה חלק מהלוגיקה של הגיליון)
USER_NAME_MAP = {
    OFER_ID: "עופר",
    SHAY_ID: "שי"
}

# 7. הגדרות לוגיות של הגיליון
CATEGORIES = ["חובה", "בית", "שוטף", "קניות שבועיות", "דלק"]

# מפת חודשים לעברית (כדי שיתאים לכותרות בגיליון שלך)
MONTH_MAP = {
    "01": "ינואר", "02": "פברואר", "03": "מרץ", "04": "אפריל",
    "05": "מאי", "06": "יוני", "07": "יולי", "08": "אוגוסט",
    "09": "ספטמבר", "10": "אוקטובר", "11": "נובמבר", "12": "דצמבר"
}