# ssm_bot.py - النسخة الكاملة المتوافقة مع Render
import os
import sys
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import threading
from pathlib import Path
from flask import Flask, request, jsonify
import requests

# مكتبات تليجرام
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        filters,
        ContextTypes,
        ConversationHandler
    )
    from telegram.constants import ParseMode
except ImportError:
    print("خطأ: يجب تثبيت مكتبة python-telegram-bot")
    print("أمر التثبيت: pip install python-telegram-bot")
    sys.exit(1)

# مكتبات الذكاء الاصطناعي والملفات
try:
    import google.generativeai as genai
    from PIL import Image
    import io
    import aiohttp
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError as e:
    print(f"خطأ في المكتبات: {e}")
    print("قم بتثبيت المتطلبات من requirements.txt")

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN", "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI")
GEMINI_API_KEY = os.environ.get("GEMINI_KEY", "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6130994941"))
SUPPORT_USERNAME = os.environ.get("SUPPORT_USER", "Allawi04@")
DATABASE_NAME = "database.db"
BASE_DIR = Path(__file__).parent

# أسعار الخدمات (قابلة للتعديل من لوحة التحكم)
SERVICE_PRICES = {
    "exemption": 1000,
    "summarize": 1000, 
    "qna": 1000,
    "materials": 1000
}

# ==================== FLASK APP FOR RENDER ====================
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>بوت يلا نتعلم</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; }
            .status { padding: 20px; margin: 20px 0; border-radius: 5px; }
            .online { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; margin-top: 20px; }
            .btn { display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت "يلا نتعلم" للطلاب العراقيين</h1>
            <div class="status online">
                <h2>✅ البوت يعمل بشكل طبيعي</h2>
                <p>تم تشغيل البوت على منصة Render بنجاح</p>
            </div>
            <div class="info">
                <h3>📊 معلومات التشغيل:</h3>
                <p>🕒 وقت التشغيل: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p>🔧 المنصة: Render.com (الخطة المجانية)</p>
                <p>👥 المدير: """ + str(ADMIN_ID) + """</p>
                <p>💬 الدعم: """ + SUPPORT_USERNAME + """</p>
            </div>
            <a href="https://t.me/FC4Xbot" class="btn" target="_blank">🚀 استخدام البوت في تلجرام</a>
            <a href="https://t.me/""" + SUPPORT_USERNAME.replace("@", "") + """" class="btn" target="_blank">👨‍💻 الدعم الفني</a>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()}), 200

@app.route('/admin/stats')
def admin_stats():
    """إحصائيات للمدير عبر الويب"""
    try:
        # التحقق من هوية المدير
        admin_key = request.args.get('key')
        if admin_key != hashlib.md5(str(ADMIN_ID).encode()).hexdigest()[:8]:
            return jsonify({"error": "غير مصرح"}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
        today_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(balance) FROM users")
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE DATE(date) = DATE('now')")
        today_transactions = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total_users": total_users,
            "today_users": today_users,
            "total_balance": total_balance,
            "today_transactions": today_transactions,
            "services": SERVICE_PRICES,
            "status": "online"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/' + TOKEN.split(':')[1], methods=['POST'])
def webhook():
    """Webhook endpoint لرسائل تلجرام"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, bot_instance)
        asyncio.run_coroutine_threadsafe(process_update(update), bot_loop)
        return 'ok'
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'error', 400

# ==================== DATABASE ====================
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
            invited_by INTEGER,
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
            name TEXT,
            description TEXT,
            file_id TEXT,
            grade TEXT,
            downloads INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إضافة مواد افتراضية
    cursor.execute("SELECT COUNT(*) FROM materials")
    if cursor.fetchone()[0] == 0:
        default_materials = [
            ("رياضيات السادس العلمي", "ملزمة شاملة لرياضيات السادس العلمي", "", "السادس العلمي"),
            ("الفيزياء السادس الأدبي", "ملخص فيزياء للسادس الأدبي", "", "السادس الأدبي"),
            ("الكيمياء السادس العلمي", "ملزمة كيمياء مع حلول", "", "السادس العلمي")
        ]
        cursor.executemany("INSERT INTO materials (name, description, file_id, grade) VALUES (?, ?, ?, ?)", default_materials)
    
    # إعدادات افتراضية
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    
    default_settings = [
        ("welcome_bonus", "1000"),
        ("referral_bonus", "500"),
        ("maintenance", "0"),
        ("support_username", SUPPORT_USERNAME)
    ]
    
    for key, value in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    conn.commit()
    conn.close()
    print("✅ تم تهيئة قاعدة البيانات")

def get_db_connection():
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)

def get_user_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_balance(user_id: int, amount: int, trans_type: str, desc: str = ""):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                      (user_id, amount, trans_type, desc))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating balance: {e}")
        return False
    finally:
        conn.close()

# ==================== BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # إضافة مستخدم جديد
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        welcome_bonus = 1000
        
        # إضافة المستخدم
        cursor.execute("INSERT INTO users (user_id, username, first_name, last_name, balance) VALUES (?, ?, ?, ?, ?)",
                      (user_id, user.username, user.first_name, user.last_name, welcome_bonus))
        cursor.execute("INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                      (user_id, welcome_bonus, "welcome_bonus", "منحة ترحيبية"))
        
        conn.commit()
        
        await update.message.reply_text(
            f"🎉 أهلاً وسهلاً {user.first_name}!\n\n"
            f"✅ تم إضافتك بنجاح إلى بوت 'يلا نتعلم'\n\n"
            f"🎁 حصلت على منحة ترحيبية: {welcome_bonus} دينار\n"
            f"💰 رصيدك الحالي: {welcome_bonus} دينار\n\n"
            f"📚 خدمات البوت المدفوعة:\n"
            f"• 🧮 حساب درجة الإعفاء: {SERVICE_PRICES['exemption']} دينار\n"
            f"• 📄 تلخيص الملازم: {SERVICE_PRICES['summarize']} دينار\n"
            f"• ❓ أسئلة وأجوبة: {SERVICE_PRICES['qna']} دينار\n"
            f"• 📚 ملازمي ومرشحاتي: {SERVICE_PRICES['materials']} دينار\n\n"
            f"🔗 لدعوة الأصدقاء: /invite",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"👋 أهلاً بعودتك {user.first_name}!\n\n"
            f"💰 رصيدك الحالي: {existing_user[4]} دينار\n\n"
            f"📚 اختر الخدمة التي تحتاجها:",
            reply_markup=get_main_menu()
        )
    
    conn.close()

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🧮 حساب درجة الإعفاء", callback_data='service_exemption')],
        [InlineKeyboardButton("📄 تلخيص الملازم (PDF)", callback_data='service_summarize')],
        [InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data='service_qna')],
        [InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data='service_materials')],
        [InlineKeyboardButton("💰 رصيدي", callback_data='balance'), 
         InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
        [InlineKeyboardButton("👑 لوحة التحكم", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    service = query.data.replace('service_', '')
    
    user = get_user_data(user_id)
    if not user:
        await query.edit_message_text("❌ لم يتم العثور على حسابك")
        return
    
    price = SERVICE_PRICES.get(service, 1000)
    
    if user[4] < price:  # user[4] = balance
        await query.edit_message_text(
            f"⚠️ رصيدك غير كافي\n\n"
            f"💰 السعر: {price} دينار\n"
            f"💵 رصيدك: {user[4]} دينار\n\n"
            f"لشحن الرصيد تواصل مع: {SUPPORT_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]])
        )
        return
    
    # خصم المبلغ
    if update_user_balance(user_id, -price, "service_payment", f"خدمة {service}"):
        if service == 'exemption':
            await query.edit_message_text(
                "🧮 حساب درجة الإعفاء\n\n"
                "أرسل درجات الكورسات الثلاثة (مثال: 85 90 95)\n"
                "سيتم حساب المعدل وتحديد إذا كنت معفياً (90 فأعلى)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]])
            )
            context.user_data['awaiting_grades'] = True
            
        elif service == 'summarize':
            await query.edit_message_text(
                "📤 أرسل ملف PDF الآن\n\n"
                "سيتم تلخيصه لك باستخدام الذكاء الاصطناعي\n"
                "وسيرسل لك ملف PDF جديد منظم",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]])
            )
            context.user_data['awaiting_pdf'] = True
            
        elif service == 'qna':
            await query.edit_message_text(
                "❓ أرسل سؤالك الآن (نص أو صورة)\n\n"
                "سيتم الرد عليك باستخدام الذكاء الاصطناعي\n"
                "بناءً على المنهج العراقي",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]])
            )
            context.user_data['awaiting_question'] = True
            
        elif service == 'materials':
            await show_materials(query)
    else:
        await query.edit_message_text("❌ حدث خطأ في المعاملة")

async def process_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_grades'):
        return
    
    try:
        grades = list(map(float, update.message.text.split()))
        if len(grades) != 3:
            await update.message.reply_text("⚠️ يرجى إدخال 3 درجات فقط")
            return
        
        average = sum(grades) / 3
        
        if average >= 90:
            result = f"🎉 مبروك! أنت معفي من المادة\n\n📊 الدرجات: {grades[0]}, {grades[1]}, {grades[2]}\n🧮 المعدل: {average:.2f}\n✅ معدلك 90 أو أعلى، أنت معفي بنجاح!"
        else:
            result = f"⚠️ للأسف لست معفياً\n\n📊 الدرجات: {grades[0]}, {grades[1]}, {grades[2]}\n🧮 المعدل: {average:.2f}\n❌ معدلك أقل من 90، تحتاج إلى تحسين درجاتك."
        
        await update.message.reply_text(result)
        context.user_data.pop('awaiting_grades', None)
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إدخال أرقام صحيحة")

async def show_materials(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, grade, downloads FROM materials ORDER BY downloads DESC LIMIT 10")
    materials = cursor.fetchall()
    conn.close()
    
    if not materials:
        await query.edit_message_text("📭 لا توجد ملازم متاحة حالياً")
        return
    
    keyboard = []
    for mat_id, name, desc, grade, downloads in materials:
        btn_text = f"{name[:15]}... ({grade}) 📥{downloads}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'mat_{mat_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')])
    
    await query.edit_message_text(
        "📚 الملازم المتاحة:\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    mat_id = int(query.data.replace('mat_', ''))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, file_id FROM materials WHERE id = ?", (mat_id,))
    material = cursor.fetchone()
    
    if material and material[1]:  # إذا كان هناك file_id
        cursor.execute("UPDATE materials SET downloads = downloads + 1 WHERE id = ?", (mat_id,))
        conn.commit()
        
        await query.message.reply_document(
            document=material[1],
            caption=f"📚 {material[0]}\n✅ تم التحميل بنجاح"
        )
    else:
        await query.message.reply_text(f"📚 {material[0]}\n\n❌ الملف غير متوفر للتحميل حالياً")
    
    conn.close()

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    
    if user:
        await query.edit_message_text(
            f"💰 معلومات رصيدك:\n\n"
            f"👤 الاسم: {user[2] or 'غير معروف'}\n"
            f"⚖️ الرصيد: {user[4]} دينار\n"
            f"📅 الانضمام: {user[6][:10] if user[6] else 'غير معروف'}\n\n"
            f"💸 أسعار الخدمات:\n"
            f"• حساب الإعفاء: {SERVICE_PRICES['exemption']} دينار\n"
            f"• تلخيص PDF: {SERVICE_PRICES['summarize']} دينار\n"
            f"• أسئلة وأجوبة: {SERVICE_PRICES['qna']} دينار\n"
            f"• الملازم: {SERVICE_PRICES['materials']} دينار",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
    else:
        await query.edit_message_text("❌ لم يتم العثور على حسابك")

async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    referral_link = f"https://t.me/FC4Xbot?start=ref_{user_id}"
    
    await query.edit_message_text(
        f"🔗 دعوة الأصدقاء\n\n"
        f"💰 احصل على 500 دينار لكل صديق ينضم عبر رابطك\n\n"
        f"📎 رابط دعوتك:\n{referral_link}\n\n"
        f"📢 شارك الرابط مع أصدقائك!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 مشاركة الرابط", 
             url=f"https://t.me/share/url?url={referral_link}&text=انضم%20للبوت%20التعليمي%20يلا%20نتعلم")],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ]),
        disable_web_page_preview=True
    )

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.message.reply_text("⛔ ليس لديك صلاحية الوصول")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("💰 شحن رصيد", callback_data='admin_charge')],
        [InlineKeyboardButton("⚙️ تغيير الأسعار", callback_data='admin_prices')],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data='admin_stats')],
        [InlineKeyboardButton("📚 إدارة الملازم", callback_data='admin_materials')],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        f"👑 لوحة تحكم المدير\n\n"
        f"📊 الإحصائيات:\n"
        f"• إجمالي المستخدمين: {total_users}\n"
        f"• إجمالي الأرصدة: {total_balance} دينار\n\n"
        f"⚙️ اختر الإجراء:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, balance FROM users ORDER BY user_id DESC LIMIT 50")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("📭 لا يوجد مستخدمين")
        return
    
    users_text = "👥 آخر 50 مستخدم:\n\n"
    for user_id, username, first_name, balance in users:
        users_text += f"🆔 {user_id} | 👤 {first_name or 'N/A'} | 💰 {balance}\n"
    
    # إرسال في رسالة منفصلة إذا كان النص طويلاً
    if len(users_text) > 4000:
        await query.message.reply_text(users_text[:4000])
    else:
        await query.message.reply_text(users_text)
    
    await query.edit_message_text(
        "✅ تم إرسال قائمة المستخدمين",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
        ])
    )

async def admin_charge_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        "💰 شحن رصيد مستخدم\n\n"
        "أرسل أيدي المستخدم والمبلغ بهذا الشكل:\n"
        "<code>أيدي_المستخدم المبلغ</code>\n\n"
        "مثال: 123456789 5000",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
        ])
    )
    
    return 'AWAITING_CHARGE_INFO'

async def process_admin_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ صيغة غير صحيحة. استخدم: أيدي المبلغ")
            return 'AWAITING_CHARGE_INFO'
        
        user_id = int(parts[0])
        amount = int(parts[1])
        
        user = get_user_data(user_id)
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return 'AWAITING_CHARGE_INFO'
        
        if update_user_balance(user_id, amount, "admin_charge", f"شحن من المدير {ADMIN_ID}"):
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 إشعار شحن رصيد\n\n✅ تم شحن رصيدك بمبلغ: {amount} دينار\n⚖️ رصيدك الجديد: {user[4] + amount} دينار"
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ تم شحن {amount} دينار للمستخدم {user_id}")
        else:
            await update.message.reply_text("❌ فشلت عملية الشحن")
        
        # العودة للوحة التحكم
        await admin_panel(update, context)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إرسال أرقام صحيحة")
        return 'AWAITING_CHARGE_INFO'

async def admin_change_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    prices_text = "💰 أسعار الخدمات الحالية:\n\n"
    for service, price in SERVICE_PRICES.items():
        service_name = {
            'exemption': 'حساب الإعفاء',
            'summarize': 'تلخيص PDF',
            'qna': 'أسئلة وأجوبة',
            'materials': 'الملازم'
        }.get(service, service)
        prices_text += f"• {service_name}: {price} دينار\n"
    
    keyboard = [
        [InlineKeyboardButton("تغيير سعر الإعفاء", callback_data='change_exemption')],
        [InlineKeyboardButton("تغيير سعر التلخيص", callback_data='change_summarize')],
        [InlineKeyboardButton("تغيير سعر الأسئلة", callback_data='change_qna')],
        [InlineKeyboardButton("تغيير سعر الملازم", callback_data='change_materials')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        prices_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    service = query.data.replace('change_', '')
    context.user_data['changing_service'] = service
    
    service_name = {
        'exemption': 'حساب الإعفاء',
        'summarize': 'تلخيص PDF',
        'qna': 'أسئلة وأجوبة',
        'materials': 'الملازم'
    }.get(service, service)
    
    await query.edit_message_text(
        f"✏️ تغيير سعر {service_name}\n\nأرسل السعر الجديد بالدينار:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_prices')]
        ])
    )
    
    return 'AWAITING_NEW_PRICE'

async def save_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text)
        service = context.user_data.get('changing_service')
        
        if service in SERVICE_PRICES:
            SERVICE_PRICES[service] = new_price
            
            service_name = {
                'exemption': 'حساب الإعفاء',
                'summarize': 'تلخيص PDF',
                'qna': 'أسئلة وأجوبة',
                'materials': 'الملازم'
            }.get(service, service)
            
            await update.message.reply_text(f"✅ تم تغيير سعر {service_name} إلى {new_price} دينار")
            
            # العودة للوحة التحكم
            await admin_panel(update, context)
            
        context.user_data.pop('changing_service', None)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح")
        return 'AWAITING_NEW_PRICE'

# ==================== MAIN BOT SETUP ====================
async def process_update(update):
    """معالجة التحديثات من webhook"""
    if update.message:
        if update.message.text and context.user_data.get('awaiting_grades'):
            await process_grades(update, context)
        elif update.message.text:
            await start(update, context)
    elif update.callback_query:
        query = update.callback_query
        data = query.data
        
        if data.startswith('service_'):
            await handle_service(update, context)
        elif data == 'balance':
            await show_balance(update, context)
        elif data == 'invite':
            await show_invite(update, context)
        elif data == 'admin_panel':
            await admin_panel(update, context)
        elif data == 'admin_users':
            await admin_users(update, context)
        elif data == 'admin_charge':
            await admin_charge_user(update, context)
        elif data == 'admin_prices':
            await admin_change_prices(update, context)
        elif data.startswith('change_'):
            await change_price_handler(update, context)
        elif data.startswith('mat_'):
            await send_material(update, context)
        elif data == 'main_menu':
            await start(update, context)

def setup_bot():
    """إعداد البوت"""
    global bot_instance, bot_loop
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(TOKEN).build()
    bot_instance = application.bot
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    
    # إضافة معالجات CallbackQuery
    application.add_handler(CallbackQueryHandler(handle_service, pattern='^service_'))
    application.add_handler(CallbackQueryHandler(show_balance, pattern='^balance$'))
    application.add_handler(CallbackQueryHandler(show_invite, pattern='^invite$'))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_charge_user, pattern='^admin_charge$'))
    application.add_handler(CallbackQueryHandler(admin_change_prices, pattern='^admin_prices$'))
    application.add_handler(CallbackQueryHandler(change_price_handler, pattern='^change_'))
    application.add_handler(CallbackQueryHandler(send_material, pattern='^mat_'))
    
    # إعداد webhook
    webhook_url = f"https://{os.environ.get('RENDER_SERVICE_NAME', 'your-service-name')}.onrender.com/webhook/{TOKEN.split(':')[1]}"
    
    try:
        # حذف webhook الحالي
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        
        # تعيين webhook جديد
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
        
        if response.status_code == 200:
            print(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
        else:
            print(f"❌ فشل تعيين Webhook: {response.text}")
    except Exception as e:
        print(f"⚠️ تحذير في تعيين Webhook: {e}")
        print("📝 البوت سيعمل باستخدام polling بدلاً من webhook")
    
    # بدء البوت
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    
    # تشغيل البوت في thread منفصل
    def run_bot():
        application.run_polling()
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("🤖 بوت 'يلا نتعلم' يعمل الآن!")
    print(f"👑 المدير: {ADMIN_ID}")
    print(f"💬 الدعم: {SUPPORT_USERNAME}")
    print(f"🌐 رابط الويب: https://{os.environ.get('RENDER_SERVICE_NAME', 'your-service-name')}.onrender.com")

# ==================== START APPLICATION ====================
if __name__ == '__main__':
    # تشغيل Flask في thread منفصل
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # تشغيل البوت
    setup_bot()
    
    # إبقاء البرنامج شغالاً
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ إيقاف البوت...")
