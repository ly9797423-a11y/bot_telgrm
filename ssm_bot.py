# ssm_bot.py
import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pdfkit
from PIL import Image
import io
import aiohttp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    BotCommand
)
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
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import arabic_reshaper
from bidi.algorithm import get_display
import sqlite3
import hashlib
import qrcode
import random
import string

# ==================== CONFIGURATION ====================
TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04@"
BOT_USERNAME = "@FC4Xbot"
DATABASE_NAME = "ssm_bot.db"
FONT_ARABIC = "fonts/arabic.ttf"  # سيتم إنشاء مجلد fonts
FONT_ENGLISH = "fonts/english.ttf"

# أسعار الخدمات (بالدينار العراقي)
SERVICE_PRICES = {
    "exemption_calc": 1000,
    "summarize_pdf": 1000,
    "qna": 1000,
    "materials": 1000
}

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        balance INTEGER DEFAULT 0,
        invited_by INTEGER,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_banned INTEGER DEFAULT 0
    )''')
    
    # جدول العمليات
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        type TEXT,
        description TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول الدعوات
    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invited_id INTEGER,
        reward_claimed INTEGER DEFAULT 0,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول الملازم
    cursor.execute('''CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        file_id TEXT,
        grade TEXT,
        added_by INTEGER,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول الإعدادات
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # إعدادات افتراضية
    default_settings = [
        ('welcome_bonus', '1000'),
        ('referral_bonus', '500'),
        ('maintenance', '0'),
        ('bot_channel', ''),
        ('support_username', SUPPORT_USERNAME)
    ]
    
    for key, value in default_settings:
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    conn.commit()
    conn.close()

# ==================== HELPER FUNCTIONS ====================
def get_db_connection():
    return sqlite3.connect(DATABASE_NAME)

def get_user_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_balance(user_id: int, amount: int, trans_type: str, desc: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تحديث الرصيد
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    
    # تسجيل العملية
    cursor.execute('''INSERT INTO transactions (user_id, amount, type, description)
                      VALUES (?, ?, ?, ?)''', (user_id, amount, trans_type, desc))
    
    conn.commit()
    conn.close()

def check_balance(user_id: int, service_price: int) -> bool:
    user = get_user_data(user_id)
    if user and user[4] >= service_price:  # العمود 4 هو balance
        return True
    return False

def format_arabic(text: str) -> str:
    """تنسيق النص العربي للعرض الصحيح"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def create_referral_link(user_id: int) -> str:
    """إنشاء رابط دعوة فريد"""
    hash_input = f"{user_id}{datetime.now().timestamp()}"
    hash_code = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"https://t.me/{BOT_USERNAME[1:]}?start=ref_{user_id}_{hash_code}"

# ==================== GEMINI AI SETUP ====================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

async def generate_ai_response(prompt: str) -> str:
    """التفاعل مع Gemini AI"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة لاحقاً."

async def process_image_with_ai(image_bytes: bytes, prompt: str) -> str:
    """معالجة الصور مع Gemini Vision"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        response = vision_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        logger.error(f"Vision AI Error: {e}")
        return "عذراً، حدث خطأ في معالجة الصورة."

# ==================== PDF HANDLING ====================
def register_fonts():
    """تسجيل الخطوط العربية والإنجليزية"""
    try:
        # إنشاء مجلد الخطوط إذا لم يكن موجوداً
        os.makedirs("fonts", exist_ok=True)
        
        # تنزيل خط عربي افتراضي (يمكن استبداله بخط مخصص)
        if not os.path.exists(FONT_ARABIC):
            # هنا يمكن إضافة كود لتنزيل خط عربي
            pass
            
        pdfmetrics.registerFont(TTFont('Arabic', FONT_ARABIC))
        pdfmetrics.registerFont(TTFont('English', FONT_ENGLISH))
    except Exception as e:
        logger.error(f"Font registration error: {e}")

def create_summary_pdf(text: str, filename: str) -> str:
    """إنشاء ملف PDF ملخص مع خطوط عربية"""
    try:
        register_fonts()
        
        # إنشاء ملف PDF مؤقت
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        c = canvas.Canvas(temp_pdf.name, pagesize=letter)
        
        # إعداد الصفحة
        width, height = letter
        margin = inch
        current_height = height - margin
        
        # تقسيم النص إلى أسطر
        lines = []
        words = text.split()
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) < 70:  # عرض السطر
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # كتابة النص مع دعم العربية
        c.setFont("Arabic", 12)
        for line in lines:
            if current_height < margin:
                c.showPage()
                c.setFont("Arabic", 12)
                current_height = height - margin
            
            # معالجة النص العربي
            formatted_line = format_arabic(line)
            c.drawString(margin, current_height, formatted_line)
            current_height -= 20
        
        c.save()
        return temp_pdf.name
    except Exception as e:
        logger.error(f"PDF Creation Error: {e}")
        return None

# ==================== TELEGRAM BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت وإضافة المستخدم الجديد"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من وضع الصيانة
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "maintenance"')
    maintenance = cursor.fetchone()[0]
    
    if maintenance == '1':
        await update.message.reply_text("⛔ البوت تحت الصيانة حالياً. الرجاء المحاولة لاحقاً.")
        conn.close()
        return
    
    # التحقق إذا كان المستخدم جديداً
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        # منحة الترحيب
        welcome_bonus = int(cursor.execute('SELECT value FROM settings WHERE key = "welcome_bonus"').fetchone()[0])
        
        # التحقق من رابط الدعوة
        referral_id = None
        if context.args:
            ref_arg = context.args[0]
            if ref_arg.startswith('ref_'):
                try:
                    referral_id = int(ref_arg.split('_')[1])
                except:
                    pass
        
        # إضافة المستخدم
        cursor.execute('''INSERT INTO users (user_id, username, first_name, last_name, balance)
                          VALUES (?, ?, ?, ?, ?)''',
                       (user_id, user.username, user.first_name, user.last_name, welcome_bonus))
        
        # تسجيل منحة الترحيب
        cursor.execute('''INSERT INTO transactions (user_id, amount, type, description)
                          VALUES (?, ?, ?, ?)''',
                       (user_id, welcome_bonus, 'welcome_bonus', 'منحة ترحيبية'))
        
        # مكافأة الدعوة
        if referral_id:
            referral_bonus = int(cursor.execute('SELECT value FROM settings WHERE key = "referral_bonus"').fetchone()[0])
            
            # تسجيل الدعوة
            cursor.execute('''INSERT INTO referrals (inviter_id, invited_id)
                              VALUES (?, ?)''', (referral_id, user_id))
            
            # منح المكافأة للمدعو
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?',
                          (referral_bonus, user_id))
            
            # تسجيل العملية
            cursor.execute('''INSERT INTO transactions (user_id, amount, type, description)
                              VALUES (?, ?, ?, ?)''',
                          (referral_id, referral_bonus, 'referral_bonus', f'مكافأة دعوة للمستخدم {user_id}'))
        
        conn.commit()
        
        welcome_text = f"""
        🎉 أهلاً وسهلاً {user.first_name}!
        
        ✅ تم إضافتك بنجاح إلى بوت (يلا نتعلم)
        
        🎁 حصلت على منحة ترحيبية: {welcome_bonus} دينار
        
        💰 رصيدك الحالي: {welcome_bonus} دينار
        
        📚 يمكنك الآن استخدام خدمات البوت المميزة:
        1. حساب درجة الإعفاء الفردي
        2. تلخيص الملازم بالذكاء الاصطناعي
        3. أسئلة وأجوبة أي مادة
        4. ملازمي ومرشحاتي
        
        🔗 لدعوة الأصدقاء والحصول على مكافآت:
        /invite
        """
    else:
        welcome_text = f"""
        👋 أهلاً بعودتك {user.first_name}!
        
        📊 رصيدك الحالي: {existing_user[4]} دينار
        
        📚 اختر الخدمة التي تحتاجها من القائمة أدناه:
        """
    
    conn.close()
    
    # عرض القائمة الرئيسية
    keyboard = [
        [InlineKeyboardButton("🧮 حساب درجة الإعفاء", callback_data='service_exemption')],
        [InlineKeyboardButton("📄 تلخيص الملازم", callback_data='service_summarize')],
        [InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data='service_qna')],
        [InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data='service_materials')],
        [InlineKeyboardButton("💰 رصيدي", callback_data='balance'), 
         InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
        [InlineKeyboardButton("👤 لوحة التحكم", callback_data='admin_panel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(format_arabic(welcome_text), reply_markup=reply_markup)

async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الخدمة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    service = query.data.replace('service_', '')
    
    # التحقق من الرصيد
    price = SERVICE_PRICES.get(service, 1000)
    
    if not check_balance(user_id, price):
        await query.edit_message_text(
            format_arabic(f"💰 رصيدك غير كافي لهذه الخدمة.\nالسعر: {price} دينار\n\nلشحن الرصيد تواصل مع الدعم:\n{SUPPORT_USERNAME}"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        return
    
    # خصم المبلغ
    update_user_balance(user_id, -price, 'service_payment', f'دفع خدمة {service}')
    
    if service == 'exemption':
        await handle_exemption_calc(query, context)
    elif service == 'summarize':
        await query.edit_message_text(
            format_arabic("📤 أرسل ملف PDF الآن وسأقوم بتلخيصه لك..."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        context.user_data['awaiting_pdf'] = True
    elif service == 'qna':
        await query.edit_message_text(
            format_arabic("📤 أرسل سؤالك الآن أو صورة تحتوي على السؤال..."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        context.user_data['awaiting_question'] = True
    elif service == 'materials':
        await show_materials(query, context)

async def handle_exemption_calc(query, context):
    """حساب درجة الإعفاء"""
    await query.edit_message_text(
        format_arabic("""
        🧮 حساب درجة الإعفاء الفردي
        
        أدخل درجات الكورسات الثلاثة (بين 0-100)
        مثال: 85 90 95
        
        سيتم حساب المعدل وتحديد إذا كنت معفياً (المعدل ≥ 90)
        """),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ])
    )
    context.user_data['awaiting_grades'] = True

async def process_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجات الإعفاء"""
    try:
        grades = list(map(float, update.message.text.split()))
        
        if len(grades) != 3:
            await update.message.reply_text("⚠️ يرجى إدخال 3 درجات فقط")
            return
        
        if any(grade < 0 or grade > 100 for grade in grades):
            await update.message.reply_text("⚠️ الدرجات يجب أن تكون بين 0 و 100")
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
            
            ❌ معدلك أقل من 90، تحتاج إلى تحسين درجاتك.
            """
        
        await update.message.reply_text(format_arabic(result))
        context.user_data.pop('awaiting_grades', None)
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إدخال أرقام صحيحة")

async def process_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف PDF للتلخيص"""
    if not context.user_data.get('awaiting_pdf'):
        return
    
    if not update.message.document:
        await update.message.reply_text("⚠️ يرجى إرسال ملف PDF")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.pdf'):
        await update.message.reply_text("⚠️ الملف يجب أن يكون بصيغة PDF")
        return
    
    # تنزيل الملف
    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()
    
    # إعلام المستخدم بالمعالجة
    processing_msg = await update.message.reply_text("🔄 جاري معالجة الملف وتلخيصه...")
    
    try:
        # هنا يمكن إضافة كود قراءة PDF واستخراج النص
        # للتبسيط، سنستخدم نصاً تجريبياً
        sample_text = """
        هذا نموذج لملخص PDF. في النسخة الكاملة، سيتم:
        1. قراءة ملف PDF
        2. استخراج النص
        3. تلخيصه باستخدام الذكاء الاصطناعي
        4. إنشاء ملف PDF جديد منظم
        
        يتم دعم الخطوط العربية والإنجليزية بشكل كامل.
        """
        
        # إنشاء PDF ملخص
        pdf_path = create_summary_pdf(sample_text, "ملخص.pdf")
        
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=InputFile(f, filename="ملخص_ملزمتك.pdf"),
                    caption="📄 تم تلخيص ملفك بنجاح!"
                )
            os.remove(pdf_path)
        else:
            await update.message.reply_text("❌ حدث خطأ في إنشاء الملخص")
    
    except Exception as e:
        logger.error(f"PDF Processing Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة الملف")
    
    finally:
        await processing_msg.delete()
        context.user_data.pop('awaiting_pdf', None)

async def process_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأسئلة بالذكاء الاصطناعي"""
    if not context.user_data.get('awaiting_question'):
        return
    
    processing_msg = await update.message.reply_text("🤔 جاري البحث عن الإجابة...")
    
    try:
        if update.message.photo:
            # معالجة الصورة
            photo = update.message.photo[-1]
            file = await photo.get_file()
            image_bytes = await file.download_as_bytearray()
            
            prompt = "أجب عن السؤال في هذه الصورة بناءً على المنهج العراقي"
            answer = await process_image_with_ai(image_bytes, prompt)
            
        elif update.message.text:
            # معالجة النص
            question = update.message.text
            prompt = f"أجب عن هذا السؤال كطالب عراقي بناءً على المنهج العراقي: {question}"
            answer = await generate_ai_response(prompt)
        
        else:
            await update.message.reply_text("⚠️ يرجى إرسال نص أو صورة تحتوي على السؤال")
            return
        
        await update.message.reply_text(format_arabic(f"🧠 الإجابة:\n\n{answer}"))
    
    except Exception as e:
        logger.error(f"QnA Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة سؤالك")
    
    finally:
        await processing_msg.delete()
        context.user_data.pop('awaiting_question', None)

async def show_materials(query, context):
    """عرض الملازم والمرشحات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, description, grade FROM materials ORDER BY added_date DESC')
    materials = cursor.fetchall()
    conn.close()
    
    if not materials:
        await query.edit_message_text(
            format_arabic("📭 لا توجد ملازم متاحة حالياً."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        return
    
    keyboard = []
    for mat_id, name, desc, grade in materials[:10]:  # عرض أول 10
        btn_text = f"{name} ({grade})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'mat_{mat_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')])
    
    await query.edit_message_text(
        format_arabic("📚 الملازم والمرشحات المتاحة:\n\nاختر من القائمة:"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال ملف الملزمة"""
    query = update.callback_query
    await query.answer()
    
    mat_id = int(query.data.replace('mat_', ''))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name, file_id FROM materials WHERE id = ?', (mat_id,))
    material = cursor.fetchone()
    conn.close()
    
    if material:
        await query.message.reply_document(
            document=material[1],
            caption=f"📚 {material[0]}"
        )
    else:
        await query.message.reply_text("❌ الملف غير متوفر")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رصيد المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user_data(user_id)
    
    if user:
        balance_text = f"""
        💰 معلومات رصيدك:
        
        ⚖️ الرصيد الحالي: {user[4]} دينار
        
        📈 لشحن الرصيد:
        1. تواصل مع الدعم: {SUPPORT_USERNAME}
        2. أو ادعو أصدقاء: /invite
        
        💸 أسعار الخدمات:
        • حساب الإعفاء: {SERVICE_PRICES['exemption_calc']} دينار
        • تلخيص PDF: {SERVICE_PRICES['summarize_pdf']} دينار
        • أسئلة وأجوبة: {SERVICE_PRICES['qna']} دينار
        • الملازم: {SERVICE_PRICES['materials']} دينار
        """
        
        await query.edit_message_text(
            format_arabic(balance_text),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite'),
                 InlineKeyboardButton("💳 شحن رصيد", callback_data='charge_info')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )

async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الدعوة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    referral_link = create_referral_link(user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # عدد المدعوين
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE inviter_id = ?', (user_id,))
    invite_count = cursor.fetchone()[0]
    
    # المكافأة
    referral_bonus = int(cursor.execute('SELECT value FROM settings WHERE key = "referral_bonus"').fetchone()[0])
    
    conn.close()
    
    invite_text = f"""
    🔗 نظام الدعوة والمكافآت
    
    📊 عدد مدعويك: {invite_count} شخص
    
    💰 مكافأة لكل دعوة: {referral_bonus} دينار
    
    📎 رابط دعوتك الخاص:
    {referral_link}
    
    👥 شارك الرابط مع أصدقائك، عند انضمامهم تحصل على {referral_bonus} دينار!
    
    📢 التعليمات:
    1. أرسل الرابط لأصدقائك
    2. عند انضمامهم للبوت عبر الرابط
    3. تحصل على المكافأة تلقائياً
    4. يمكنهم بدورهم دعوة آخرين
    """
    
    await query.edit_message_text(
        format_arabic(invite_text),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 مشاركة الرابط", 
             url=f"https://t.me/share/url?url={referral_link}&text=انضم%20إلى%20بوت%20يلا%20نتعلم%20للطلاب%20")],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ]),
        disable_web_page_preview=True
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المدير"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.message.reply_text("⛔ ليس لديك صلاحية الوصول لهذه الصفحة.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # إحصائيات
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE("now")')
    today_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT value FROM settings WHERE key = "maintenance"')
    maintenance = cursor.fetchone()[0]
    
    conn.close()
    
    admin_text = f"""
    👑 لوحة تحكم المدير
    
    📊 الإحصائيات:
    • إجمالي المستخدمين: {total_users}
    • المستخدمين الجدد اليوم: {today_users}
    • إجمالي الأرصدة: {total_balance} دينار
    • وضع الصيانة: {'✅ مفعل' if maintenance == '1' else '❌ غير مفعل'}
    
    ⚙️ اختر الإجراء المناسب:
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("💰 شحن رصيد", callback_data='admin_charge')],
        [InlineKeyboardButton("⛔ حظر/فك حظر", callback_data='admin_ban')],
        [InlineKeyboardButton("⚙️ تغيير الأسعار", callback_data='admin_prices')],
        [InlineKeyboardButton("🛠️ وضع الصيانة", callback_data='admin_maintenance')],
        [InlineKeyboardButton("📈 الإحصائيات الكاملة", callback_data='admin_stats')],
        [InlineKeyboardButton("📚 إدارة الملازم", callback_data='admin_materials')],
        [InlineKeyboardButton("🎁 تعديل المكافآت", callback_data='admin_rewards')],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        format_arabic(admin_text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, balance FROM users ORDER BY user_id DESC LIMIT 50')
    users = cursor.fetchall()
    conn.close()
    
    users_text = "👥 آخر 50 مستخدم:\n\n"
    for user_id, username, first_name, balance in users:
        users_text += f"ID: {user_id} | {first_name or ''} | @{username or 'N/A'} | 💰 {balance}\n"
    
    # تقسيم النص إذا كان طويلاً
    if len(users_text) > 4000:
        chunks = [users_text[i:i+4000] for i in range(0, len(users_text), 4000)]
        for chunk in chunks:
            await query.message.reply_text(chunk)
    else:
        await query.message.reply_text(users_text)
    
    # عرض خيارات الإدارة
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data='admin_search_user')],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
    ]
    
    await query.message.reply_text(
        "اختر الإجراء:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شحن رصيد مستخدم"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        format_arabic("💰 شحن رصيد مستخدم\n\nأرسل أيدي المستخدم:"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
        ])
    )
    
    context.user_data['admin_action'] = 'charge_user'
    return 'AWAITING_USER_ID'

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إجراءات المدير"""
    user_id = update.message.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    action = context.user_data.get('admin_action')
    
    if action == 'charge_user' and 'charge_step' not in context.user_data:
        # الخطوة الأولى: أخذ أيدي المستخدم
        try:
            target_user_id = int(update.message.text)
            context.user_data['charge_user_id'] = target_user_id
            context.user_data['charge_step'] = 'amount'
            
            await update.message.reply_text("أرسل المبلغ بالدينار:")
            return 'AWAITING_AMOUNT'
        except ValueError:
            await update.message.reply_text("⚠️ أيدي المستخدم يجب أن يكون رقماً")
    
    elif action == 'charge_user' and context.user_data.get('charge_step') == 'amount':
        # الخطوة الثانية: أخذ المبلغ
        try:
            amount = int(update.message.text)
            target_user_id = context.user_data['charge_user_id']
            
            # تحديث الرصيد
            update_user_balance(target_user_id, amount, 'admin_charge', 
                              f'شحن من المدير {user_id}')
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=format_arabic(f"💰 تم شحن رصيدك بمبلغ {amount} دينار\n\nرصيدك الجديد: {get_user_data(target_user_id)[4]} دينار")
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ تم شحن {amount} دينار للمستخدم {target_user_id}")
            
            # تنظيف البيانات
            context.user_data.pop('admin_action', None)
            context.user_data.pop('charge_user_id', None)
            context.user_data.pop('charge_step', None)
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("⚠️ المبلغ يجب أن يكون رقماً")

async def admin_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير أسعار الخدمات"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    prices_text = "💰 أسعار الخدمات الحالية:\n\n"
    for service, price in SERVICE_PRICES.items():
        service_name = {
            'exemption_calc': 'حساب الإعفاء',
            'summarize_pdf': 'تلخيص PDF',
            'qna': 'أسئلة وأجوبة',
            'materials': 'الملازم'
        }.get(service, service)
        
        prices_text += f"• {service_name}: {price} دينار\n"
    
    keyboard = []
    for service in SERVICE_PRICES.keys():
        service_name = {
            'exemption_calc': 'الإعفاء',
            'summarize_pdf': 'التلخيص',
            'qna': 'الأسئلة',
            'materials': 'الملازم'
        }.get(service, service)
        
        keyboard.append([InlineKeyboardButton(f"تغيير سعر {service_name}", 
                       callback_data=f'change_price_{service}')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        format_arabic(prices_text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def change_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير سخدمة معينة"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    service = query.data.replace('change_price_', '')
    context.user_data['changing_price'] = service
    
    service_name = {
        'exemption_calc': 'حساب الإعفاء الفردي',
        'summarize_pdf': 'تلخيص الملازم',
        'qna': 'أسئلة وأجوبة',
        'materials': 'ملازمي ومرشحاتي'
    }.get(service, service)
    
    await query.edit_message_text(
        format_arabic(f"✏️ تغيير سعر خدمة {service_name}\n\nأرسل السعر الجديد بالدينار:"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_prices')]
        ])
    )
    
    return 'AWAITING_NEW_PRICE'

async def save_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ السعر الجديد"""
    try:
        new_price = int(update.message.text)
        service = context.user_data.get('changing_price')
        
        if service in SERVICE_PRICES:
            SERVICE_PRICES[service] = new_price
            
            await update.message.reply_text(f"✅ تم تغيير سعر {service} إلى {new_price} دينار")
            
            # تنظيف البيانات
            context.user_data.pop('changing_price', None)
            
            return ConversationHandler.END
        else:
            await update.message.reply_text("⚠️ خدمة غير صحيحة")
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح")

async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/إلغاء وضع الصيانة"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "maintenance"')
    current_status = cursor.fetchone()[0]
    
    new_status = '0' if current_status == '1' else '1'
    cursor.execute('UPDATE settings SET value = ? WHERE key = "maintenance"', (new_status,))
    conn.commit()
    conn.close()
    
    status_text = "✅ تم تفعيل وضع الصيانة" if new_status == '1' else "❌ تم إلغاء وضع الصيانة"
    
    await query.edit_message_text(
        format_arabic(status_text),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
        ])
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🧮 حساب درجة الإعفاء", callback_data='service_exemption')],
        [InlineKeyboardButton("📄 تلخيص الملازم", callback_data='service_summarize')],
        [InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data='service_qna')],
        [InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data='service_materials')],
        [InlineKeyboardButton("💰 رصيدي", callback_data='balance'), 
         InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
        [InlineKeyboardButton("👤 لوحة التحكم", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        format_arabic("🏠 القائمة الرئيسية\n\nاختر الخدمة التي تريدها:"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== MAIN FUNCTION ====================
def main():
    """تشغيل البوت"""
    # تهيئة قاعدة البيانات
    init_db()
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    
    # معالجة الاختيارات من Inline Keyboard
    application.add_handler(CallbackQueryHandler(handle_service_selection, pattern='^service_'))
    application.add_handler(CallbackQueryHandler(show_balance, pattern='^balance$'))
    application.add_handler(CallbackQueryHandler(show_invite, pattern='^invite$'))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_charge, pattern='^admin_charge$'))
    application.add_handler(CallbackQueryHandler(admin_prices, pattern='^admin_prices$'))
    application.add_handler(CallbackQueryHandler(change_price, pattern='^change_price_'))
    application.add_handler(CallbackQueryHandler(admin_maintenance, pattern='^admin_maintenance$'))
    application.add_handler(CallbackQueryHandler(send_material, pattern='^mat_'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))
    
    # معالجة المحادثات مع المدير
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_charge, pattern='^admin_charge$'),
                      CallbackQueryHandler(change_price, pattern='^change_price_')],
        states={
            'AWAITING_USER_ID': [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_actions)],
            'AWAITING_AMOUNT': [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_actions)],
            'AWAITING_NEW_PRICE': [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_price)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)
    
    # معالجة الرسائل المختلفة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_grades))
    application.add_handler(MessageHandler(filters.Document.ALL, process_pdf))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_question))
    application.add_handler(MessageHandler(filters.PHOTO, process_question))
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
