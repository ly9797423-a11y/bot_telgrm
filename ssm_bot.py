# ssm_bot.py - النسخة الكاملة المصححة
import os
import sys
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify
import requests

# ==================== المكتبات المطلوبة ====================
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    print("✅ مكتبة Telegram مثبتة")
except ImportError:
    print("❌ مكتبة python-telegram-bot غير مثبتة")
    print("✅ قم بتشغيل: pip install python-telegram-bot")
    sys.exit(1)

# ==================== التكوين ====================
TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04@"
BOT_USERNAME = "FC4Xbot"
DATABASE_NAME = "ssm_bot.db"
BOT_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# أسعار الخدمات
SERVICE_PRICES = {
    "exemption": 1000,
    "summarize": 1000,
    "qna": 1000,
    "materials": 1000
}

# ==================== تطبيق Flask ====================
app = Flask(__name__)

# ==================== دوال Telegram API ====================
def send_telegram_request(method: str, data: dict = None):
    """إرسال طلب إلى Telegram API"""
    try:
        url = f"{BOT_API_URL}/{method}"
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"خطأ في Telegram API: {e}")
        return None

def send_message(chat_id: int, text: str, reply_markup=None):
    """إرسال رسالة إلى مستخدم"""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    return send_telegram_request("sendMessage", data)

def edit_message_text(chat_id: int, message_id: int, text: str, reply_markup=None):
    """تعديل نص رسالة"""
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    return send_telegram_request("editMessageText", data)

def answer_callback_query(callback_query_id: str, text: str = None):
    """الرد على Callback Query"""
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
    
    return send_telegram_request("answerCallbackQuery", data)

def send_document(chat_id: int, document: str, caption: str = None):
    """إرسال مستند"""
    data = {
        "chat_id": chat_id,
        "document": document
    }
    
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    
    return send_telegram_request("sendDocument", data)

# ==================== دوال Keyboard ====================
def create_main_menu_keyboard():
    """لوحة المفاتيح الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("🧮 حساب الإعفاء", callback_data="service_exemption"),
            InlineKeyboardButton("📄 تلخيص PDF", callback_data="service_summarize")
        ],
        [
            InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data="service_qna"),
            InlineKeyboardButton("📚 الملازم", callback_data="service_materials")
        ],
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data="invite")
        ],
        [
            InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_back_keyboard():
    """زر الرجوع فقط"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard():
    """لوحة تحكم المدير"""
    keyboard = [
        [
            InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")
        ],
        [
            InlineKeyboardButton("⚙️ تغيير الأسعار", callback_data="admin_prices"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("📚 إدارة الملازم", callback_data="admin_materials"),
            InlineKeyboardButton("🛠️ وضع الصيانة", callback_data="admin_maintenance")
        ],
        [
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_balance_keyboard():
    """لوحة رصيد المستخدم"""
    keyboard = [
        [
            InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data="invite"),
            InlineKeyboardButton("📊 سجل المعاملات", callback_data="transactions")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_invite_keyboard(user_id: int):
    """لوحة الدعوة"""
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    keyboard = [
        [
            InlineKeyboardButton(
                "📤 مشاركة الرابط",
                url=f"https://t.me/share/url?url={referral_link}&text=انضم%20للبوت%20التعليمي%20يلا%20نتعلم"
            )
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_prices_keyboard():
    """لوحة أسعار الخدمات للمدير"""
    keyboard = [
        [
            InlineKeyboardButton("تغيير سعر الإعفاء", callback_data="change_exemption"),
            InlineKeyboardButton("تغيير سعر التلخيص", callback_data="change_summarize")
        ],
        [
            InlineKeyboardButton("تغيير سعر الأسئلة", callback_data="change_qna"),
            InlineKeyboardButton("تغيير سعر الملازم", callback_data="change_materials")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_materials_keyboard(materials):
    """لوحة الملازم"""
    keyboard = []
    for mat_id, name, grade, downloads in materials:
        button_text = f"{name[:15]}... ({grade}) 📥{downloads}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"mat_{mat_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

# ==================== قاعدة البيانات ====================
def init_db():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            invited_by INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المعاملات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الدعوات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER,
            invited_id INTEGER UNIQUE,
            reward_claimed INTEGER DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الملازم
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            file_id TEXT,
            grade TEXT,
            downloads INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإعدادات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # الإعدادات الافتراضية
    default_settings = [
        ("welcome_bonus", "1000"),
        ("referral_bonus", "500"),
        ("maintenance_mode", "0"),
        ("support_username", SUPPORT_USERNAME),
        ("admin_id", str(ADMIN_ID)),
        ("exemption_price", "1000"),
        ("summarize_price", "1000"),
        ("qna_price", "1000"),
        ("materials_price", "1000"),
        ("bot_username", BOT_USERNAME)
    ]
    
    for key, value in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    # مواد افتراضية
    cursor.execute("SELECT COUNT(*) FROM materials")
    if cursor.fetchone()[0] == 0:
        default_materials = [
            ("رياضيات السادس العلمي", "ملزمة شاملة مع حلول", "", "السادس العلمي"),
            ("الفيزياء السادس الأدبي", "ملخص فيزياء شامل", "", "السادس الأدبي"),
            ("الكيمياء السادس العلمي", "ملزمة كيمياء مع تجارب", "", "السادس العلمي"),
            ("الأحياء السادس العلمي", "ملخص أحياء مع رسوم", "", "السادس العلمي"),
            ("اللغة العربية", "قواعد اللغة العربية", "", "السادس")
        ]
        cursor.executemany(
            "INSERT INTO materials (name, description, file_id, grade) VALUES (?, ?, ?, ?)",
            default_materials
        )
    
    conn.commit()
    conn.close()
    print("✅ تم تهيئة قاعدة البيانات")

def get_db():
    """الحصول على اتصال قاعدة البيانات"""
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)

def get_user(user_id: int):
    """الحصول على بيانات المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id: int, username: str, first_name: str, invited_by: int = 0):
    """إنشاء مستخدم جديد"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # مكافأة الترحيب
        cursor.execute("SELECT value FROM settings WHERE key = 'welcome_bonus'")
        welcome_bonus = int(cursor.fetchone()[0])
        
        # إضافة المستخدم
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, balance, invited_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, welcome_bonus, invited_by))
        
        # تسجيل المعاملة
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, welcome_bonus, "welcome_bonus", "مكافأة ترحيب"))
        
        # مكافأة الدعوة
        if invited_by > 0:
            cursor.execute("SELECT value FROM settings WHERE key = 'referral_bonus'")
            referral_bonus = int(cursor.fetchone()[0])
            
            # تسجيل الدعوة
            cursor.execute('''
                INSERT OR IGNORE INTO referrals (inviter_id, invited_id)
                VALUES (?, ?)
            ''', (invited_by, user_id))
            
            # منح المكافأة
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (referral_bonus, invited_by))
            cursor.execute('''
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (?, ?, ?, ?)
            ''', (invited_by, referral_bonus, "referral_bonus", f"مكافأة دعوة {user_id}"))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"خطأ في إنشاء المستخدم: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_balance(user_id: int, amount: int, trans_type: str, description: str = ""):
    """تحديث رصيد المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # تحديث الرصيد
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        
        if cursor.rowcount == 0:
            return False
        
        # تسجيل المعاملة
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, trans_type, description))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"خطأ في تحديث الرصيد: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_setting(key: str, default: str = ""):
    """الحصول على إعداد"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def update_setting(key: str, value: str):
    """تحديث إعداد"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

# ==================== دوال المساعدة ====================
def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}"

def create_referral_link(user_id: int) -> str:
    """إنشاء رابط دعوة"""
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

# ==================== معالجة Webhook ====================
user_sessions = {}  # تخزين جلسات المستخدمين

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>بوت يلا نتعلم</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .status { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت "يلا نتعلم"</h1>
            <div class="status">
                <h3>✅ البوت يعمل على Render</h3>
                <p>🕒 الوقت: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p>👑 المدير: """ + str(ADMIN_ID) + """</p>
                <p>💬 الدعم: """ + SUPPORT_USERNAME + """</p>
            </div>
            <p style="text-align: center; margin-top: 20px;">
                <a href="https://t.me/FC4Xbot" style="color: #3498db; font-size: 18px;">🚀 اضغط هنا للدخول للبوت</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/setwebhook')
def set_webhook_route():
    """تعيين Webhook"""
    try:
        service_name = os.environ.get('RENDER_SERVICE_NAME', 'yalanatelim-bot')
        webhook_url = f"https://{service_name}.onrender.com/webhook"
        
        # حذف الـ webhook القديم
        requests.get(f"{BOT_API_URL}/deleteWebhook")
        
        # تعيين الجديد
        response = requests.get(f"{BOT_API_URL}/setWebhook?url={webhook_url}")
        
        if response.status_code == 200:
            return f"""
            <h2>✅ تم تعيين Webhook بنجاح!</h2>
            <p>الرابط: {webhook_url}</p>
            <p><a href="/">العودة للصفحة الرئيسية</a></p>
            """
        else:
            return f"""
            <h2>❌ فشل تعيين Webhook</h2>
            <p>خطأ: {response.text}</p>
            <p><a href="/">العودة</a></p>
            """
    except Exception as e:
        return f"<h2>خطأ: {str(e)}</h2>"

@app.route('/webhook', methods=['POST'])
def webhook():
    """استقبال التحديثات من Telegram"""
    try:
        update = request.get_json()
        
        if 'message' in update:
            process_message(update['message'])
        elif 'callback_query' in update:
            process_callback_query(update['callback_query'])
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        print(f"خطأ في webhook: {e}")
        return jsonify({"status": "error"}), 500

def process_message(message):
    """معالجة الرسائل"""
    chat_id = message['chat']['id']
    text = message.get('text', '')
    
    # التحقق من وضع الصيانة
    if get_setting("maintenance_mode") == "1":
        send_message(chat_id, "⛔ البوت تحت الصيانة حالياً.")
        return
    
    # معالجة الأوامر
    if text.startswith('/start'):
        handle_start_command(chat_id, message)
    elif text.startswith('/help'):
        send_message(chat_id, f"📞 الدعم: {SUPPORT_USERNAME}\n💰 للشحن والتواصل")
    elif 'awaiting_grades' in user_sessions.get(chat_id, {}):
        handle_grades_input(chat_id, text)
    elif 'admin_awaiting_charge' in user_sessions.get(chat_id, {}):
        handle_admin_charge(chat_id, text)
    elif 'admin_awaiting_price' in user_sessions.get(chat_id, {}):
        handle_admin_price(chat_id, text)
    else:
        send_message(chat_id, "🔍 استخدم /start للبدء", create_main_menu_keyboard())

def process_callback_query(callback_query):
    """معالجة Callback Query"""
    query_id = callback_query['id']
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']
    
    # الرد على Callback Query
    answer_callback_query(query_id)
    
    # معالجة البيانات
    if data == 'main_menu':
        show_main_menu(chat_id, message_id)
    elif data == 'balance':
        show_balance(chat_id, message_id)
    elif data == 'invite':
        show_invite(chat_id, message_id)
    elif data == 'admin_panel':
        show_admin_panel(chat_id, message_id)
    elif data.startswith('service_'):
        handle_service_selection(chat_id, message_id, data.replace('service_', ''))
    elif data.startswith('mat_'):
        send_material(chat_id, data.replace('mat_', ''))
    elif data == 'admin_users':
        admin_show_users(chat_id)
    elif data == 'admin_charge':
        admin_start_charge(chat_id, message_id)
    elif data == 'admin_prices':
        admin_show_prices(chat_id, message_id)
    elif data.startswith('change_'):
        admin_start_change_price(chat_id, message_id, data.replace('change_', ''))
    elif data == 'admin_maintenance':
        admin_toggle_maintenance(chat_id, message_id)
    elif data == 'admin_stats':
        admin_show_stats(chat_id, message_id)
    elif data == 'admin_materials':
        admin_show_materials(chat_id, message_id)
    elif data == 'transactions':
        show_transactions(chat_id, message_id)

# ==================== معالجات الأوامر ====================
def handle_start_command(chat_id, message):
    """معالجة أمر /start"""
    user = message['from']
    user_id = user['id']
    username = user.get('username', '')
    first_name = user.get('first_name', '')
    
    # التحقق من رابط الدعوة
    invited_by = 0
    text = message.get('text', '')
    if ' ' in text:
        args = text.split()
        if len(args) > 1 and args[1].startswith('ref_'):
            try:
                invited_by = int(args[1].split('_')[1])
            except:
                pass
    
    # التحقق إذا كان المستخدم جديداً
    existing_user = get_user(user_id)
    
    if not existing_user:
        # إنشاء مستخدم جديد
        if create_user(user_id, username, first_name, invited_by):
            welcome_bonus = int(get_setting("welcome_bonus", "1000"))
            
            welcome_text = f"""
            🎉 أهلاً وسهلاً {first_name}!
            
            ✅ تم إضافتك إلى بوت "يلا نتعلم"
            
            🎁 مكافأة الترحيب: {format_number(welcome_bonus)} دينار
            💰 رصيدك الحالي: {format_number(welcome_bonus)} دينار
            
            📚 خدمات البوت:
            • حساب درجة الإعفاء
            • تلخيص الملازم (PDF)
            • أسئلة وأجوبة
            • ملازم ومرشحات
            
            💸 كل خدمة: 1,000 دينار
            
            🔗 لدعوة الأصدقاء
            👑 للشحن: {SUPPORT_USERNAME}
            """
        else:
            welcome_text = "❌ حدث خطأ في إنشاء حسابك"
    else:
        balance = existing_user[4]
        welcome_text = f"""
        👋 أهلاً بعودتك {first_name}!
        
        💰 رصيدك الحالي: {format_number(balance)} دينار
        
        📚 اختر الخدمة التي تحتاجها:
        """
    
    send_message(chat_id, welcome_text, create_main_menu_keyboard())

def show_main_menu(chat_id, message_id=None):
    """عرض القائمة الرئيسية"""
    text = "🏠 القائمة الرئيسية\n\nاختر الخدمة:"
    
    if message_id:
        edit_message_text(chat_id, message_id, text, create_main_menu_keyboard())
    else:
        send_message(chat_id, text, create_main_menu_keyboard())

def show_balance(chat_id, message_id):
    """عرض رصيد المستخدم"""
    user = get_user(chat_id)
    
    if not user:
        edit_message_text(chat_id, message_id, "❌ لم يتم العثور على حسابك", create_back_keyboard())
        return
    
    balance = user[4]
    join_date = user[6]
    
    balance_text = f"""
    💰 معلومات رصيدك
    
    👤 الاسم: {user[2] or 'غير معروف'}
    🆔 الأيدي: {chat_id}
    📅 الانضمام: {join_date[:10] if join_date else 'غير معروف'}
    
    ⚖️ الرصيد الحالي: {format_number(balance)} دينار
    
    💸 أسعار الخدمات:
    • حساب الإعفاء: {format_number(SERVICE_PRICES['exemption'])} دينار
    • تلخيص PDF: {format_number(SERVICE_PRICES['summarize'])} دينار
    • أسئلة وأجوبة: {format_number(SERVICE_PRICES['qna'])} دينار
    • الملازم: {format_number(SERVICE_PRICES['materials'])} دينار
    
    📞 للشحن: {SUPPORT_USERNAME}
    """
    
    edit_message_text(chat_id, message_id, balance_text, create_balance_keyboard())

def show_invite(chat_id, message_id):
    """عرض معلومات الدعوة"""
    referral_link = create_referral_link(chat_id)
    referral_bonus = int(get_setting("referral_bonus", "500"))
    
    invite_text = f"""
    🔗 نظام الدعوة والمكافآت
    
    💰 احصل على {format_number(referral_bonus)} دينار لكل صديق ينضم عبر رابطك!
    
    📎 رابط دعوتك:
    {referral_link}
    
    📢 شارك الرابط مع أصدقائك!
    """
    
    edit_message_text(chat_id, message_id, invite_text, create_invite_keyboard(chat_id))

def show_transactions(chat_id, message_id):
    """عرض سجل المعاملات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, type, description, date 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT 10
    ''', (chat_id,))
    transactions = cursor.fetchall()
    conn.close()
    
    if not transactions:
        text = "📭 لا توجد معاملات سابقة"
    else:
        text = "📊 آخر 10 معاملات:\n\n"
        total = 0
        
        for amount, trans_type, description, date in transactions:
            total += amount
            sign = "➕" if amount > 0 else "➖"
            text += f"{sign} {format_number(abs(amount))} دينار\n"
            text += f"   📝 {description}\n"
            text += f"   🕒 {date[:19]}\n\n"
        
        text += f"💰 الإجمالي: {format_number(total)} دينار"
    
    edit_message_text(chat_id, message_id, text, create_back_keyboard())

# ==================== معالجة الخدمات ====================
def handle_service_selection(chat_id, message_id, service_type):
    """معالجة اختيار خدمة"""
    user = get_user(chat_id)
    
    if not user:
        edit_message_text(chat_id, message_id, "❌ لم يتم العثور على حسابك", create_back_keyboard())
        return
    
    price = SERVICE_PRICES.get(service_type, 1000)
    balance = user[4]
    
    if balance < price:
        text = f"""
        ⚠️ رصيدك غير كافي
        
        💰 السعر: {format_number(price)} دينار
        💵 رصيدك: {format_number(balance)} دينار
        
        📞 للشحن: {SUPPORT_USERNAME}
        """
        
        edit_message_text(chat_id, message_id, text, create_back_keyboard())
        return
    
    # خصم المبلغ
    service_names = {
        'exemption': 'حساب درجة الإعفاء',
        'summarize': 'تلخيص PDF',
        'qna': 'أسئلة وأجوبة',
        'materials': 'الملازم'
    }
    
    service_name = service_names.get(service_type, service_type)
    
    if update_balance(chat_id, -price, "service_payment", service_name):
        new_balance = balance - price
        
        if service_type == 'exemption':
            text = f"""
            🧮 خدمة حساب درجة الإعفاء
            
            ✅ تم خصم {format_number(price)} دينار
            💰 رصيدك المتبقي: {format_number(new_balance)} دينار
            
            📝 أرسل درجات الكورسات الثلاثة:
            مثال: 85 90 95
            
            سيتم حساب المعدل وتحديد إذا كنت معفياً
            """
            
            # تخزين حالة انتظار الدرجات
            if chat_id not in user_sessions:
                user_sessions[chat_id] = {}
            user_sessions[chat_id]['awaiting_grades'] = True
            
        elif service_type == 'summarize':
            text = f"""
            📄 خدمة تلخيص PDF
            
            ✅ تم خصم {format_number(price)} دينار
            💰 رصيدك المتبقي: {format_number(new_balance)} دينار
            
            📤 أرسل ملف PDF الآن
            سيتم تلخيصه لك
            """
            
            user_sessions[chat_id]['awaiting_pdf'] = True
            
        elif service_type == 'qna':
            text = f"""
            ❓ خدمة الأسئلة والأجوبة
            
            ✅ تم خصم {format_number(price)} دينار
            💰 رصيدك المتبقي: {format_number(new_balance)} دينار
            
            💬 أرسل سؤالك الآن
            سيتم الرد عليك
            """
            
            user_sessions[chat_id]['awaiting_question'] = True
            
        elif service_type == 'materials':
            show_materials_list(chat_id, message_id)
            return
        
        edit_message_text(chat_id, message_id, text, create_back_keyboard())
    else:
        edit_message_text(chat_id, message_id, "❌ حدث خطأ في المعاملة", create_back_keyboard())

def handle_grades_input(chat_id, text):
    """معالجة إدخال الدرجات"""
    try:
        grades = [float(g.strip()) for g in text.split()]
        
        if len(grades) != 3:
            send_message(chat_id, "⚠️ يرجى إدخال 3 درجات فقط")
            return
        
        for grade in grades:
            if grade < 0 or grade > 100:
                send_message(chat_id, "⚠️ الدرجات يجب أن تكون بين 0 و 100")
                return
        
        average = sum(grades) / 3
        
        if average >= 90:
            result = f"""
            🎉 مبروك! أنت معفي من المادة
            
            📊 الدرجات: {grades[0]}, {grades[1]}, {grades[2]}
            🧮 المعدل: {average:.2f}
            
            ✅ معدلك 90 أو أعلى، أنت معفي بنجاح!
            """
        else:
            result = f"""
            ⚠️ للأسف لست معفياً
            
            📊 الدرجات: {grades[0]}, {grades[1]}, {grades[2]}
            🧮 المعدل: {average:.2f}
            
            ❌ معدلك أقل من 90
            """
        
        send_message(chat_id, result, create_main_menu_keyboard())
        
        # إزالة حالة الانتظار
        if chat_id in user_sessions:
            user_sessions[chat_id].pop('awaiting_grades', None)
            
    except ValueError:
        send_message(chat_id, "⚠️ يرجى إدخال أرقام صحيحة")

# ==================== الملازم ====================
def show_materials_list(chat_id, message_id):
    """عرض قائمة الملازم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, grade, downloads FROM materials ORDER BY downloads DESC LIMIT 15")
    materials = cursor.fetchall()
    conn.close()
    
    if not materials:
        edit_message_text(chat_id, message_id, "📭 لا توجد ملازم متاحة", create_back_keyboard())
        return
    
    text = "📚 الملازم المتاحة:\n\nاختر من القائمة:"
    
    edit_message_text(chat_id, message_id, text, create_materials_keyboard(materials))

def send_material(chat_id, material_id):
    """إرسال ملزمة"""
    try:
        mat_id = int(material_id)
    except:
        send_message(chat_id, "❌ معرف الملزمة غير صحيح")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, file_id FROM materials WHERE id = ?", (mat_id,))
    material = cursor.fetchone()
    
    if material:
        name, description, file_id = material
        
        # زيادة العداد
        cursor.execute("UPDATE materials SET downloads = downloads + 1 WHERE id = ?", (mat_id,))
        conn.commit()
        
        if file_id:
            send_document(chat_id, file_id, f"📚 {name}\n{description or ''}\n✅ تم التحميل")
        else:
            send_message(chat_id, f"📚 {name}\n{description or ''}\n❌ الملف غير متوفر حالياً")
    else:
        send_message(chat_id, "❌ الملزمة غير متوفرة")
    
    conn.close()

# ==================== لوحة التحكم ====================
def show_admin_panel(chat_id, message_id):
    """عرض لوحة تحكم المدير"""
    if chat_id != ADMIN_ID:
        edit_message_text(chat_id, message_id, "⛔ ليس لديك صلاحية", create_back_keyboard())
        return
    
    # إحصائيات
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
    today_users = cursor.fetchone()[0]
    
    conn.close()
    
    maintenance = get_setting("maintenance_mode", "0")
    
    text = f"""
    👑 لوحة تحكم المدير
    
    📊 الإحصائيات:
    • إجمالي المستخدمين: {format_number(total_users)}
    • المستخدمين الجدد اليوم: {format_number(today_users)}
    • إجمالي الأرصدة: {format_number(total_balance)} دينار
    • وضع الصيانة: {'✅ مفعل' if maintenance == '1' else '❌ غير مفعل'}
    
    ⚙️ اختر الإجراء:
    """
    
    edit_message_text(chat_id, message_id, text, create_admin_keyboard())

def admin_show_users(chat_id):
    """عرض قائمة المستخدمين للمدير"""
    if chat_id != ADMIN_ID:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, balance FROM users ORDER BY user_id DESC LIMIT 50")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        send_message(chat_id, "📭 لا يوجد مستخدمين")
        return
    
    text = "👥 آخر 50 مستخدم:\n\n"
    for user_id, username, first_name, balance in users:
        text += f"🆔 {user_id} | 👤 {first_name or 'N/A'} | 💰 {format_number(balance)}\n"
    
    send_message(chat_id, text)

def admin_start_charge(chat_id, message_id):
    """بدء شحن رصيد"""
    if chat_id != ADMIN_ID:
        return
    
    text = """
    💰 شحن رصيد مستخدم
    
    أرسل أيدي المستخدم والمبلغ:
    <code>123456789 5000</code>
    
    مثال: <code>123456789 5000</code>
    """
    
    edit_message_text(chat_id, message_id, text, create_back_keyboard())
    
    # تخزين حالة الانتظار
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    user_sessions[chat_id]['admin_awaiting_charge'] = True

def handle_admin_charge(chat_id, text):
    """معالجة شحن الرصيد"""
    if chat_id != ADMIN_ID:
        return
    
    try:
        parts = text.split()
        if len(parts) != 2:
            send_message(chat_id, "⚠️ صيغة غير صحيحة. استخدم: أيدي المبلغ")
            return
        
        user_id = int(parts[0])
        amount = int(parts[1])
        
        user = get_user(user_id)
        if not user:
            send_message(chat_id, "❌ المستخدم غير موجود")
            return
        
        if update_balance(user_id, amount, "admin_charge", f"شحن من المدير {ADMIN_ID}"):
            new_balance = user[4] + amount
            
            # إرسال إشعار للمستخدم
            try:
                send_message(user_id, f"""
                💰 إشعار شحن رصيد
                
                ✅ تم شحن رصيدك بمبلغ: {format_number(amount)} دينار
                
                ⚖️ رصيدك السابق: {format_number(user[4])} دينار
                ⚖️ رصيدك الجديد: {format_number(new_balance)} دينار
                
                📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                """)
            except:
                pass
            
            send_message(chat_id, f"""
            ✅ تم شحن {format_number(amount)} دينار للمستخدم {user_id}
            💰 رصيده الجديد: {format_number(new_balance)} دينار
            """)
        else:
            send_message(chat_id, "❌ فشلت عملية الشحن")
        
        # إزالة حالة الانتظار
        if chat_id in user_sessions:
            user_sessions[chat_id].pop('admin_awaiting_charge', None)
        
        # العودة للوحة التحكم
        show_admin_panel(chat_id, None)
            
    except ValueError:
        send_message(chat_id, "⚠️ يرجى إرسال أرقام صحيحة")

def admin_show_prices(chat_id, message_id):
    """عرض أسعار الخدمات"""
    if chat_id != ADMIN_ID:
        return
    
    text = f"""
    💰 أسعار الخدمات الحالية:
    
    • حساب الإعفاء: {format_number(SERVICE_PRICES['exemption'])} دينار
    • تلخيص PDF: {format_number(SERVICE_PRICES['summarize'])} دينار
    • أسئلة وأجوبة: {format_number(SERVICE_PRICES['qna'])} دينار
    • الملازم: {format_number(SERVICE_PRICES['materials'])} دينار
    
    اختر السعر الذي تريد تغييره:
    """
    
    edit_message_text(chat_id, message_id, text, create_prices_keyboard())

def admin_start_change_price(chat_id, message_id, service_type):
    """بدء تغيير سعر خدمة"""
    if chat_id != ADMIN_ID:
        return
    
    service_names = {
        'exemption': 'حساب الإعفاء',
        'summarize': 'تلخيص PDF',
        'qna': 'أسئلة وأجوبة',
        'materials': 'الملازم'
    }
    
    service_name = service_names.get(service_type, service_type)
    current_price = SERVICE_PRICES.get(service_type, 1000)
    
    # تخزين الخدمة المراد تغييرها
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    user_sessions[chat_id]['admin_awaiting_price'] = service_type
    
    text = f"""
    ✏️ تغيير سعر {service_name}
    
    السعر الحالي: {format_number(current_price)} دينار
    
    أرسل السعر الجديد بالدينار:
    """
    
    edit_message_text(chat_id, message_id, text, create_back_keyboard())

def handle_admin_price(chat_id, text):
    """معالجة تغيير السعر"""
    if chat_id != ADMIN_ID:
        return
    
    try:
        new_price = int(text)
        
        if new_price < 100:
            send_message(chat_id, "⚠️ السعر يجب أن يكون 100 دينار على الأقل")
            return
        
        service_type = user_sessions[chat_id].get('admin_awaiting_price')
        if not service_type:
            send_message(chat_id, "⚠️ لم يتم تحديد السعر المراد تغييره")
            return
        
        service_names = {
            'exemption': 'حساب الإعفاء',
            'summarize': 'تلخيص PDF',
            'qna': 'أسئلة وأجوبة',
            'materials': 'الملازم'
        }
        
        service_name = service_names.get(service_type, service_type)
        
        # تحديث السعر
        SERVICE_PRICES[service_type] = new_price
        
        send_message(chat_id, f"✅ تم تغيير سعر {service_name} إلى {format_number(new_price)} دينار")
        
        # إزالة حالة الانتظار
        if chat_id in user_sessions:
            user_sessions[chat_id].pop('admin_awaiting_price', None)
        
        # العودة للوحة التحكم
        show_admin_panel(chat_id, None)
        
    except ValueError:
        send_message(chat_id, "⚠️ يرجى إرسال رقم صحيح")

def admin_toggle_maintenance(chat_id, message_id):
    """تبديل وضع الصيانة"""
    if chat_id != ADMIN_ID:
        return
    
    current = get_setting("maintenance_mode", "0")
    new_value = "0" if current == "1" else "1"
    
    if update_setting("maintenance_mode", new_value):
        status = "✅ تم تفعيل وضع الصيانة" if new_value == "1" else "❌ تم إلغاء وضع الصيانة"
        edit_message_text(chat_id, message_id, status, create_back_keyboard())
    else:
        edit_message_text(chat_id, message_id, "❌ فشل تغيير وضع الصيانة", create_back_keyboard())

def admin_show_stats(chat_id, message_id):
    """عرض إحصائيات كاملة"""
    if chat_id != ADMIN_ID:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    # إحصائيات المستخدمين
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE balance > 0")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    # إحصائيات المعاملات
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE amount > 0")
    total_income = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE amount < 0")
    total_expenses = cursor.fetchone()[0] or 0
    
    # إحصائيات الدعوات
    cursor.execute("SELECT COUNT(*) FROM referrals")
    total_referrals = cursor.fetchone()[0]
    
    conn.close()
    
    text = f"""
    📊 إحصائيات كاملة:
    
    👥 المستخدمين:
    • الإجمالي: {format_number(total_users)}
    • اليوم: {format_number(today_users)}
    • النشطين: {format_number(active_users)}
    
    💰 الأرصدة:
    • إجمالي الأرصدة: {format_number(total_balance)} دينار
    
    💳 المعاملات:
    • عدد المعاملات: {format_number(total_transactions)}
    • إجمالي الإيرادات: {format_number(total_income)} دينار
    • إجمالي المصروفات: {format_number(abs(total_expenses))} دينار
    
    🔗 الدعوات:
    • إجمالي الدعوات: {format_number(total_referrals)}
    
    ⚙️ الإعدادات:
    • وضع الصيانة: {'✅ مفعل' if get_setting("maintenance_mode") == "1" else '❌ غير مفعل'}
    • مكافأة الترحيب: {format_number(int(get_setting("welcome_bonus", "1000")))} دينار
    • مكافأة الدعوة: {format_number(int(get_setting("referral_bonus", "500")))} دينار
    """
    
    edit_message_text(chat_id, message_id, text, create_back_keyboard())

def admin_show_materials(chat_id, message_id):
    """إدارة الملازم"""
    if chat_id != ADMIN_ID:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, grade, downloads FROM materials ORDER BY id DESC")
    materials = cursor.fetchall()
    conn.close()
    
    if not materials:
        text = "📭 لا توجد ملازم"
    else:
        text = "📚 جميع الملازم:\n\n"
        for mat_id, name, grade, downloads in materials:
            text += f"🆔 {mat_id} | {name} ({grade}) | 📥{downloads}\n"
    
    edit_message_text(chat_id, message_id, text, create_back_keyboard())

# ==================== التشغيل الرئيسي ====================
@app.route('/startup')
def startup():
    """صفحة بدء التشغيل"""
    init_db()
    
    # محاولة تعيين Webhook تلقائياً
    try:
        service_name = os.environ.get('RENDER_SERVICE_NAME', 'yalanatelim-bot')
        webhook_url = f"https://{service_name}.onrender.com/webhook"
        requests.get(f"{BOT_API_URL}/setWebhook?url={webhook_url}")
    except:
        pass
    
    return """
    <h2>✅ البوت يعمل!</h2>
    <p>تم تشغيل البوت بنجاح</p>
    <p><a href="/">العودة للصفحة الرئيسية</a></p>
    """

if __name__ == '__main__':
    # تهيئة قاعدة البيانات
    init_db()
    
    # تشغيل Flask
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 بدء تشغيل البوت على المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
