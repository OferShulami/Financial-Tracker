import telebot
import time
from telebot import types
from src import config


class TelegramBot:
    def __init__(self):
        self.bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
        self.user_responses = {}
        print("🛠️ [DEBUG] רושם Handlers...")  # תוסיף את זה

        @self.bot.callback_query_handler(func=lambda call: True)
        def _callback_handler(call):
            print("🎯 [DEBUG] Callback Handler הופעל!")  # ותוסיף את זה
            self.handle_callback(call)

    def send_message(self, chat_id, text, **kwargs):
        """
        שולחת הודעה למשתמש.
        השימוש ב-**kwargs מאפשר להעביר פרמטרים כמו reply_markup ו-parse_mode
        """
        try:
            return self.bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            print(f"❌ שגיאה בשליחת הודעה: {e}")
            return None

    def wait_for_confirmation(self, user_id):
        """עוצרת את הרצת הקוד עד שהמשתמש לוחץ על 'כן' או 'לא'"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ כן", callback_data="yes"),
                   types.InlineKeyboardButton("❌ לא", callback_data="no"))

        self.send_message(user_id, "נא אשר את הפעולה:", reply_markup=markup)
        return self._loop_until_response(user_id)

    def ask_for_category_text(self, user_id, description):
        """מבקשת מהמשתמש להקליד קטגוריה בטקסט חופשי - ללא כפתורים"""
        msg = f"🔍 לא מצאתי קטגוריה מוכרת ל-'{description}'.\nאנא הקלד את שם הקטגוריה:"
        self.send_message(user_id, msg)
        # מחכה להודעת טקסט מהמשתמש (ה-handler כבר שומר אותה ב-user_responses)
        return self._loop_until_response(user_id)

    def ask_for_display_name(self, user_id, raw_description):
        """מבקשת מהמשתמש להקליד שם תצוגה "נקי" """
        self.send_message(user_id, f"איך תרצה שזה יופיע בגיליון? (המקור: {raw_description})")
        # בטלגרם, המתנה להודעת טקסט דורשת לוגיקה של register_next_step_handler
        # לצורך הפשטות ב-Stream, נשתמש ב-Loop דומה
        return self._loop_until_response(user_id)

    def _loop_until_response(self, user_id):
        # המרה ל-int כדי לוודא התאמה מושלמת
        uid = int(user_id)
        self.user_responses[uid] = None

        print(f"⏳ [DEBUG] מחכה לתשובה מ-ID: {uid}...")

        while self.user_responses.get(uid) is None:
            time.sleep(0.1)
            # הדפסה אופציונלית רק אם רוצים לראות שהלולאה רצה:
            # print(f"Checking {uid}: {self.user_responses.get(uid)}")

        response = self.user_responses[uid]
        print(f"🔓 [DEBUG] התקבלה תשובה: {response}")
        return response

    def handle_callback(self, call):
        uid = int(call.from_user.id)  # המרה ל-int
        data = call.data
        print(f"📩 [DEBUG] Callback הגיע מ-ID: {uid}, Data: {data}")

        # עדכון המילון
        self.user_responses[uid] = data

        try:
            self.bot.answer_callback_query(call.id)
        except:
            pass

    def handle_callback(self, call):
        uid = int(call.from_user.id)  # המרה ל-int
        data = call.data
        print(f"📩 [DEBUG] Callback הגיע מ-ID: {uid}, Data: {data}")

        # עדכון המילון
        self.user_responses[uid] = data

        try:
            self.bot.answer_callback_query(call.id)
        except:
            pass

    def handle_message(self, message):
        """קליטת טקסט חופשי מהמשתמש"""
        # אנחנו בודקים אם המשתמש נמצא כרגע ב"המתנה" לתשובה
        if message.from_user.id in self.user_responses:
            self.user_responses[message.from_user.id] = message.text

    def ask_for_text(self, user_id, prompt_text):
        """שולחת הודעה ומחכה שהמשתמש יקליד טקסט חופשי"""
        self.send_message(user_id, prompt_text)
        return self._loop_until_response(user_id)

    def confirm_mapping(self, user_id, description, display_name, category):
        """מציעה את המיפוי הקיים עם אפשרות לשינוי"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"✅ להשתמש ב: {display_name} ({category})", callback_data="use_existing"),
            types.InlineKeyboardButton("✏️ משהו אחר", callback_data="other")
        )

        msg = f"העסק '{description}' מוכר לי. מה תרצה לעשות?"
        self.send_message(user_id, msg, reply_markup=markup)
        return self._loop_until_response(user_id)

    def build_category_markup(self, suggested_categories=None):
        """
        בונה את המקלדת.
        אם יש הצעות - מציגה אותן + כפתור 'אחר'.
        אם אין הצעות - מחזירה None (כדי שה-main ידע להציג את הרשימה המלאה).
        """
        if not suggested_categories:
            return None

        markup = types.InlineKeyboardMarkup(row_width=1)

        # הוספת כפתורים לכל הצעה (בדרך כלל תהיה אחת, אבל המבנה תומך ביותר)
        for cat in suggested_categories:
            markup.add(types.InlineKeyboardButton(f"📌 הצעה: {cat}", callback_data=f"cat_{cat}"))

        # הוספת כפתור "אחר" שיוביל לרשימה המלאה
        markup.add(types.InlineKeyboardButton("🔍 קטגוריה אחרת...", callback_data="show_all_categories"))

        return markup

    def send_question_with_markup(self, user_id, text, markup):
        """פונקציה גנרית ששולחת שאלה עם כפתורים ומחכה לתשובה"""
        self.send_message(user_id, text, reply_markup=markup)
        return self._loop_until_response(user_id)

    def delete_message(self, user_id, message_id):
        """מוחקת הודעה ספציפית כדי לשמור על סדר"""
        try:
            self.bot.delete_message(user_id, message_id)
        except Exception as e:
            print(f"לא ניתן למחוק הודעה: {e}")

    def clear_session(self, user_id, message_ids_list):
        """מוחקת רשימה של הודעות במכה אחת"""
        for msg_id in message_ids_list:
            self.delete_message(user_id, msg_id)

    def get_user_sheet_selection(self, user_id, transaction_details):
        """Displays a transaction and asks the user to select the target Google Sheet.

            This method sends an Inline Keyboard to the user via Telegram. It pauses
            the execution for the current transaction until the user clicks one of
             the predefined sheet options (Home, Ofer, or Shay).

            Args:
                user_id (int or str): The Telegram ID of the authorized user.
                transaction_info (str): A formatted string containing date, business name, and amount.

            Returns:
                str: The name of the selected sheet ('בית', 'עופר', or 'שי').
                None: If the user cancels or an error occurs.
            """


        markup = types.InlineKeyboardMarkup(row_width=2)
        home_btn = types.InlineKeyboardButton("🏠 בית", callback_data="sheet_בית")

        name = "עופר" if str(user_id) == str(config.OFER_ID) else "שי"
        personal_btn = types.InlineKeyboardButton(f"👤 {name}", callback_data=f"sheet_{name}")

        markup.add(personal_btn, home_btn)

        msg_text = f"📍 לאן לשייך?\n**{transaction_details}**"
        sent_msg = self.send_message(user_id, msg_text, reply_markup=markup, parse_mode="Markdown")

        # 3. המתנה ללחיצה
        choice_data = self._loop_until_response(user_id)
        sheet_name = choice_data.replace("sheet_", "")

        # 4. פידבק ויזואלי - עריכת ההודעה והסרת הכפתורים
        feedback = f"✅ נבחר: **{sheet_name}**\nעבור: {transaction_details}"
        self.bot.edit_message_text(feedback, user_id, sent_msg.message_id, parse_mode="Markdown")

        return sheet_name

    def check_authorization(self, user_id):
        """
        Checks if a given Telegram user ID is authorized to run the synchronization.

        This function acts as a security gate, ensuring only pre-defined users (e.g., Ofer and Shai)
        can interact with the budget integration logic.

        Args:
            user_id (Union[int, str]): The unique Telegram user ID of the sender.

        Returns:
            bool: True if the user is authorized, False otherwise.
        """
        from src import config  # ייבוא לצורך הדוגמה, וודא שזה קיים אצלך

        # הגדרת הרשימה הלבנה מתוך ה-Config
        authorized_users = [str(config.OFER_ID), str(config.SHAY_ID)]

        # המרה ל-string כדי למנוע בעיות של השוואת מספר לטקסט
        current_user = str(user_id)

        if current_user not in authorized_users:
            print(f"🛑 Security Alert: Unauthorized access attempt by {current_user}")
            self.send_message(user_id, "🚫 גישה חסומה. המערכת מיועדת לעופר ושי בלבד.")
            return False

        print(f"✅ User {current_user} authorized. Starting integration process.")
        return True

def setup_handlers(bot_manager):
    bot = bot_manager.bot

    @bot.callback_query_handler(func=lambda call: True)
    def callback_inline(call):
        bot_manager.handle_callback(call)

    @bot.message_handler(func=lambda message: True)
    def message_receive(message):
        bot_manager.handle_message(message)