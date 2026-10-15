import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import sqlite3

# Aapka Telegram Bot Token
TOKEN = "8600435969:AAFQAX27jmwbyw6xwGgE3VNaVa1ymSc4sU4"
bot = telebot.TeleBot(TOKEN)

# Database Setup (Emails aur active state save karne ke liye)
def init_db():
    conn = sqlite3.connect('temp_mails_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_emails (
            user_id INTEGER,
            email TEXT,
            login TEXT,
            domain TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_emails (
            user_id INTEGER PRIMARY KEY,
            active_email TEXT,
            login TEXT,
            domain TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_active_email(user_id):
    conn = sqlite3.connect('temp_mails_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT email, login, domain FROM active_emails WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def set_active_email(user_id, email, login, domain):
    conn = sqlite3.connect('temp_mails_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_emails (user_id, active_email, login, domain) VALUES (?, ?, ?, ?)", 
                   (user_id, email, login, domain))
    conn.commit()
    conn.close()

# Start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("✨ Generate New Email", callback_data="gen_mail"),
        InlineKeyboardButton("📬 Check Inbox", callback_data="check_inbox"),
        InlineKeyboardButton("📁 My Saved Emails", callback_data="my_mails"),
        InlineKeyboardButton("ℹ️ Help / Guide", callback_data="help_guide")
    )
    
    welcome_text = (
        "👋 **Welcome to Master's Temp Mail Bot!**\n\n"
        "Aap is bot se temporary email address bana sakte hain, unhe save kar sakte hain, aur real-time inbox messages padh sakte hain.\n\n"
        "Neeche diye gaye buttons ka use karein:"
    )
    bot.reply_to(message, welcome_text, reply_markup=markup)

# Button Clicks Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == "gen_mail":
        try:
            response = requests.get("https://www.1secmail.com/api/v1/?action=genMailbox&count=1")
            data = response.json()
            email = data[0]
            login, domain = email.split('@')

            conn = sqlite3.connect('temp_mails_pro.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user_emails (user_id, email, login, domain) VALUES (?, ?, ?, ?)", 
                           (user_id, email, login, domain))
            conn.commit()
            conn.close()

            set_active_email(user_id, email, login, domain)

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📬 Check Inbox Now", callback_data="check_inbox"),
                InlineKeyboardButton("✨ Generate Another", callback_data="gen_mail")
            )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ **New Temp Email Generated & Activated!**\n\n`{email}`\n\nYeh email ab aapka active email hai. Koi bhi mail aane par yahan check karein.",
                reply_markup=markup
            )
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Error generating email!")

    elif call.data == "check_inbox":
        active = get_active_email(user_id)
        if not active:
            bot.answer_callback_query(call.id, "Pehle ek email generate karein!")
            return

        email, login, domain = active
        try:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
            response = requests.get(url)
            messages = response.json()

            markup = InlineKeyboardMarkup()
            markup.row_width = 1

            if not messages:
                text = f"📭 **Inbox is Empty**\nActive Email: `{email}`"
                markup.add(
                    InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_inbox"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
                )
            else:
                text = f"📬 **Inbox for `{email}`:**\n\n"
                for msg in messages:
                    msg_id = msg['id']
                    sender = msg['from']
                    subject = msg['subject']
                    text += f"✉️ **From:** {sender}\n📝 **Subject:** {subject}\n-------------------\n"
                    markup.add(InlineKeyboardButton(f"📖 Read: {subject[:20]}...", callback_data=f"read__{msg_id}"))
                
                markup.add(InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_inbox"))

            markup.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Error fetching inbox!")

    elif call.data.startswith("read__"):
        msg_id = call.data.split("__")[1]
        active = get_active_email(user_id)
        if not active:
            return
        email, login, domain = active
        
        try:
            url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}"
            response = requests.get(url)
            msg_data = response.json()

            sender = msg_data.get('from')
            subject = msg_data.get('subject')
            date = msg_data.get('date')
            body = msg_data.get('body', 'No Content')

            text = (
                f"📨 **Email Details:**\n\n"
                f"👤 **From:** {sender}\n"
                f"📌 **Subject:** {subject}\n"
                f"⏱ **Date:** {date}\n\n"
                f"📜 **Message Body:**\n{body}"
            )

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📬 Back to Inbox", callback_data="check_inbox"),
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
            )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Error reading message content!")

    elif call.data == "my_mails":
        conn = sqlite3.connect('temp_mails_pro.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM user_emails WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            bot.answer_callback_query(call.id, "Aapke paas koi saved email nahi hai.")
            return

        active = get_active_email(user_id)
        active_email = active[0] if active else ""

        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        text = "📁 **Aapke Saved Temp Emails:**\n(Active email par ✅ mark hai)\n\n"
        
        for row in rows:
            em = row[0]
            prefix = "✅ " if em == active_email else "✉️ "
            text += f"{prefix}`{em}`\n"
            markup.add(InlineKeyboardButton(f"Switch to: {em[:20]}...", callback_data=f"switch_{em}"))

        markup.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))

        bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
        )

    elif call.data.startswith("switch_"):
        target_email = call.data.split("_")[1]
        login, domain = target_email.split('@')
        set_active_email(user_id, target_email, login, domain)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📬 Check Inbox", callback_data="check_inbox"),
            InlineKeyboardButton("📁 View All Mails", callback_data="my_mails"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🔄 **Successfully switched active email to:**\n`{target_email}`",
            reply_markup=markup
        )

    elif call.data == "help_guide":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))
        
        help_text = (
            "ℹ️ **Bot Guide:**\n\n"
            "1. **Generate New Email:** Naya random address banata hai aur use active karta hai.\n"
            "2. **Check Inbox:** Aapke active email par aaye naye messages dikhata hai.\n"
            "3. **My Saved Emails:** Saare saved emails ki list jisse aap switch kar sakte hain.\n"
            "4. **Read Message:** Kisi bhi incoming email par click karke uska poora content padh sakte hain."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=help_text,
            reply_markup=markup
        )

    elif call.data == "main_menu":
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("✨ Generate New Email", callback_data="gen_mail"),
            InlineKeyboardButton("📬 Check Inbox", callback_data="check_inbox"),
            InlineKeyboardButton("📁 My Saved Emails", callback_data="my_mails"),
            InlineKeyboardButton("ℹ️ Help / Guide", callback_data="help_guide")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👋 **Main Menu:**",
            reply_markup=markup
        )

print("Bot is running...")
bot.polling()
