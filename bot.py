#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - Telegram Bot متكامل للطلاب
المطور: Allawi04@
ID المطور: 6130994941
"""

import asyncio
import logging
import sqlite3
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import html

import aiohttp
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    InputFile, InputMediaDocument, ReplyKeyboardMarkup,
    KeyboardButton, Message, User
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from telegram.constants import ParseMode, ChatAction
import google.generativeai as genai
import arabic_reshaper
from bidi.algorithm import get_display

# ============== إعدادات البوت ==============
BOT_TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
BOT_USERNAME = "@FC4Xbot"
DEVELOPER_ID = 6130994941
DEVELOPER_USERNAME = "Allawi04@"
CHANNEL_LINK = "https://t.me/FCJCV"
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"

# إعداد الذكاء الاصطناعي
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# ============== إعداد قواعد البيانات ==============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('yalla_nt3lm.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_database()
    
    def init_database(self):
        # جدول المستخدمين
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER DEFAULT 1000,
                invite_code TEXT UNIQUE,
                invited_by INTEGER DEFAULT 0,
                invited_count INTEGER DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_expiry TIMESTAMP,
                free_trial_used INTEGER DEFAULT 0
            )
        ''')
        
        # جدول المعاملات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                transaction_type TEXT,
                description TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول الخدمات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price INTEGER DEFAULT 1000,
                is_active INTEGER DEFAULT 1,
                category TEXT
            )
        ''')
        
        # جدول الأسئلة والأجوبة
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                subject TEXT,
                status TEXT DEFAULT 'pending',
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answer TEXT,
                answered_by INTEGER,
                answer_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول المواد الدراسية
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                stage TEXT,
                file_id TEXT,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (added_by) REFERENCES users (user_id)
            )
        ''')
        
        # جدول محاضرات VIP
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_lectures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                title TEXT,
                description TEXT,
                file_id TEXT,
                price INTEGER DEFAULT 5000,
                approved INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول مشتريات محاضرات VIP
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lecture_id INTEGER,
                amount_paid INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (lecture_id) REFERENCES vip_lectures (id)
            )
        ''')
        
        # جدول أرباح المعلمين
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                lecture_id INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users (user_id),
                FOREIGN KEY (lecture_id) REFERENCES vip_lectures (id)
            )
        ''')
        
        # جدول إعدادات البوت
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # إدخال الخدمات الأساسية
        services = [
            ('exemption_calculator', 'حساب درجة الإعفاء', 1000, 'main'),
            ('pdf_summary', 'تلخيص الملازم', 1000, 'main'),
            ('qna', 'سؤال وجواب', 1000, 'main'),
            ('help_student', 'ساعدوني طالب', 1000, 'main'),
            ('vip_subscription', 'اشتراك VIP', 20000, 'vip'),
            ('vip_lecture_purchase', 'شراء محاضرة VIP', 5000, 'vip')
        ]
        
        for service_id, name, price, category in services:
            self.cursor.execute('''
                INSERT OR IGNORE INTO services (name, price, category)
                VALUES (?, ?, ?)
            ''', (name, price, category))
        
        # إدخال الإعدادات الأساسية
        settings = [
            ('invite_bonus', '1000'),
            ('min_withdrawal', '15000'),
            ('vip_monthly_price', '20000'),
            ('maintenance_mode', '0'),
            ('support_username', DEVELOPER_USERNAME),
            ('channel_link', CHANNEL_LINK)
        ]
        
        for key, value in settings:
            self.cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
        
        # إضافة المستخدم المطور
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, balance, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (DEVELOPER_ID, DEVELOPER_USERNAME, 'المطور', 1000000, 1))
        
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Dict:
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        cols = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        if row:
            return dict(zip(cols, row))
        return None
    
    def create_user(self, user: User, invite_code: str = None, invited_by: int = None):
        invite_bonus = int(self.get_setting('invite_bonus'))
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, invite_code, invited_by, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            invite_code or str(uuid.uuid4())[:8],
            invited_by,
            invite_bonus if not invited_by else 0
        ))
        
        if invited_by:
            # منح المكافأة للمدعو
            self.update_balance(user.id, invite_bonus, 'invite_bonus', 'مكافأة دعوة')
            # زيادة عدد الدعوات للمدعِي
            self.cursor.execute('''
                UPDATE users SET invited_count = invited_count + 1 
                WHERE user_id = ?
            ''', (invited_by,))
            # منح مكافأة للمدعِي
            self.update_balance(invited_by, 500, 'invite_reward', 'مكافأة لدعوة مستخدم جديد')
        
        self.conn.commit()
    
    def update_balance(self, user_id: int, amount: int, trans_type: str, description: str):
        self.cursor.execute('''
            UPDATE users SET balance = balance + ? WHERE user_id = ?
        ''', (amount, user_id))
        
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, trans_type, description))
        
        self.conn.commit()
    
    def get_setting(self, key: str) -> str:
        self.cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def update_setting(self, key: str, value: str):
        self.cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        self.conn.commit()
    
    def get_service_price(self, service_name: str) -> int:
        self.cursor.execute('SELECT price FROM services WHERE name = ? AND is_active = 1', (service_name,))
        result = self.cursor.fetchone()
        return int(result[0]) if result else 1000
    
    def get_active_services(self, category: str = None) -> List:
        if category:
            self.cursor.execute('SELECT * FROM services WHERE is_active = 1 AND category = ?', (category,))
        else:
            self.cursor.execute('SELECT * FROM services WHERE is_active = 1')
        return self.cursor.fetchall()
    
    def toggle_service(self, service_name: str, status: int):
        self.cursor.execute('UPDATE services SET is_active = ? WHERE name = ?', (status, service_name))
        self.conn.commit()
    
    def get_all_users(self) -> List:
        self.cursor.execute('SELECT * FROM users ORDER BY joined_date DESC')
        return self.cursor.fetchall()
    
    def get_vip_teachers(self) -> List:
        self.cursor.execute('''
            SELECT * FROM users 
            WHERE is_vip = 1 AND vip_expiry > datetime('now')
            ORDER BY vip_expiry DESC
        ''')
        return self.cursor.fetchall()
    
    def add_vip_lecture(self, teacher_id: int, title: str, description: str, file_id: str, price: int):
        self.cursor.execute('''
            INSERT INTO vip_lectures (teacher_id, title, description, file_id, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (teacher_id, title, description, file_id, price))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_lecture_earnings(self, teacher_id: int) -> int:
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM teacher_earnings 
            WHERE teacher_id = ? AND status = 'approved'
        ''', (teacher_id,))
        result = self.cursor.fetchone()
        return int(result[0]) if result else 0
    
    def withdraw_earnings(self, teacher_id: int, amount: int):
        current_earnings = self.get_lecture_earnings(teacher_id)
        if amount <= current_earnings:
            self.cursor.execute('''
                INSERT INTO teacher_earnings (teacher_id, amount, status)
                VALUES (?, ?, 'withdrawn')
            ''', (teacher_id, -amount))
            self.conn.commit()
            return True
        return False

# ============== تهيئة قاعدة البيانات ==============
db = Database()

# ============== إعداد الخطوط العربية ==============
def setup_arabic_fonts():
    try:
        # تحميل خطوط عربية (يجب تثبيتها على السيرفر)
        font_paths = {
            'arabic': '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'noto': '/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'
        }
        
        for name, path in font_paths.items():
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name
    except:
        pass
    
    # استخدام خط افتراضي
    return 'Helvetica'

ARABIC_FONT = setup_arabic_fonts()

# ============== وظائف مساعدة ==============
def format_arabic(text: str) -> str:
    """تهيئة النص العربي للعرض بشكل صحيح"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def format_number(number: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{number:,}"

async def send_message(user_id: int, text: str, context: ContextTypes.DEFAULT_TYPE, 
                      reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.HTML):
    """إرسال رسالة مع معالجة الأخطاء"""
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        logging.error(f"Error sending message to {user_id}: {e}")

def check_balance(user_id: int, service_name: str) -> Tuple[bool, int]:
    """فحص رصيد المستخدم وتكلفة الخدمة"""
    user = db.get_user(user_id)
    price = db.get_service_price(service_name)
    
    if not user:
        return False, price
    
    if user['balance'] >= price:
        return True, price
    return False, price

async def deduct_balance(user_id: int, service_name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """خصم تكلفة الخدمة من رصيد المستخدم"""
    user = db.get_user(user_id)
    price = db.get_service_price(service_name)
    
    if user and user['balance'] >= price:
        db.update_balance(user_id, -price, 'service_payment', f'دفع مقابل خدمة {service_name}')
        
        # إرسال إشعار بالدفع
        notification = f"""
💳 <b>تم خصم مبلغ من حسابك</b>
━━━━━━━━━━━━━━
💰 المبلغ: <code>{format_number(price)} دينار</code>
📝 السبب: خدمة {service_name}
📊 الرصيد الجديد: <code>{format_number(user['balance'] - price)} دينار</code>
        """
        await send_message(user_id, notification, context)
        return True
    
    return False

# ============== واجهة المستخدم الرئيسية ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت والترحيب بالمستخدم"""
    user = update.effective_user
    
    # التحقق من وضع الصيانة
    if db.get_setting('maintenance_mode') == '1' and user.id != DEVELOPER_ID:
        maintenance_msg = """
🔧 <b>البوت قيد الصيانة</b>
━━━━━━━━━━━━━━
البوت حالياً تحت الصيانة والتطوير.
الرجاء المحاولة لاحقاً.
        """
        await update.message.reply_text(maintenance_msg, parse_mode=ParseMode.HTML)
        return
    
    # إنشاء المستخدم إذا لم يكن موجوداً
    if not db.get_user(user.id):
        invite_code = None
        invited_by = None
        
        if context.args:
            invite_code = context.args[0]
            # البحث عن المستخدم الذي دعاه
            db.cursor.execute('SELECT user_id FROM users WHERE invite_code = ?', (invite_code,))
            inviter = db.cursor.fetchone()
            if inviter:
                invited_by = inviter[0]
        
        db.create_user(user, invite_code, invited_by)
    
    # عرض واجهة المستخدم الرئيسية
    user_data = db.get_user(user.id)
    
    welcome_bonus = 1000 if not user_data.get('free_trial_used') else 0
    if welcome_bonus > 0 and user_data['balance'] < welcome_bonus:
        db.update_balance(user.id, welcome_bonus, 'welcome_bonus', 'هدية ترحيبية')
        db.cursor.execute('UPDATE users SET free_trial_used = 1 WHERE user_id = ?', (user.id,))
        db.conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("🧮 حساب درجة الإعفاء", callback_data='service_exemption_calculator')],
        [InlineKeyboardButton("📚 تلخيص الملازم", callback_data='service_pdf_summary')],
        [InlineKeyboardButton("❓ سؤال وجواب", callback_data='service_qna')],
        [InlineKeyboardButton("🙋‍♂️ ساعدوني طالب", callback_data='service_help_student')],
        [InlineKeyboardButton("🎓 ملازمي ومرشحاتي", callback_data='study_materials')],
        [InlineKeyboardButton("👑 محاضرات VIP", callback_data='vip_lectures')],
        [
            InlineKeyboardButton("💳 رصيدي", callback_data='my_balance'),
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data='invite_friends')
        ],
        [
            InlineKeyboardButton("📊 إحصائياتي", callback_data='my_stats'),
            InlineKeyboardButton("ℹ️ المساعدة", callback_data='help')
        ]
    ]
    
    # إضافة زر VIP إذا كان مشتركاً
    if user_data.get('is_vip') and user_data.get('vip_expiry') > datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
        keyboard.insert(5, [InlineKeyboardButton("👨‍🏫 رفع محاضرة VIP", callback_data='upload_vip_lecture')])
    
    # إضافة لوحة التحكم للمطور
    if user.id == DEVELOPER_ID or user_data.get('is_admin'):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""
🎉 <b>مرحباً {user.first_name}!</b>
━━━━━━━━━━━━━━
<b>👤 معلومات حسابك:</b>
💰 الرصيد: <code>{format_number(user_data['balance'])} دينار</code>
👥 عدد الدعوات: <code>{user_data['invited_count']}</code>
📅 تاريخ الانضمام: {user_data['joined_date'][:10]}
    """
    
    # إضافة حالة VIP إذا كان مشتركاً
    if user_data.get('is_vip'):
        expiry = datetime.strptime(user_data['vip_expiry'], '%Y-%m-%d %H:%M:%S')
        days_left = (expiry - datetime.now()).days
        welcome_message += f"\n👑 حالة VIP: <b>مفعل</b> ({days_left} يوم متبقي)"
    
    welcome_message += f"""

📚 <b>الخدمات المتاحة:</b>
• حساب درجة الإعفاء
• تلخيص الملازم بالذكاء الاصطناعي
• سؤال وجواب لأي مادة
• مساعدة الطلاب والإجابة على أسئلتهم
• ملازم ومرشحات متنوعة
• محاضرات VIP حصرية
    """
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# ============== خدمات البوت ==============
async def service_exemption_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة حساب درجة الإعفاء"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    has_balance, price = check_balance(user_id, 'exemption_calculator')
    
    if not has_balance:
        await query.edit_message_text(
            f"💰 <b>رصيدك غير كافي</b>\n"
            f"سعر الخدمة: <code>{format_number(price)} دينار</code>\n"
            f"الرجاء شحن رصيدك أولاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # خصم المبلغ
    if await deduct_balance(user_id, 'exemption_calculator', context):
        instruction = """
📊 <b>حساب درجة الإعفاء</b>
━━━━━━━━━━━━━━
<code>أدخل درجات الكورسات الثلاثة (من 100)</code>

<blockquote>مثال:
90
85
95</blockquote>

<b>ملاحظة:</b> يجب أن يكون المعدل 90 أو أكثر للإعفاء
        """
        
        await query.edit_message_text(
            instruction,
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['waiting_for_grades'] = True
        return ConversationHandler.END

async def handle_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجات الإعفاء"""
    if not context.user_data.get('waiting_for_grades'):
        return
    
    text = update.message.text
    grades = []
    
    # استخراج الدرجات من النص
    for line in text.split('\n'):
        line = line.strip()
        if line and line.replace('.', '').isdigit():
            try:
                grade = float(line)
                if 0 <= grade <= 100:
                    grades.append(grade)
            except:
                pass
    
    if len(grades) != 3:
        await update.message.reply_text(
            "❌ <b>الرجاء إدخال 3 درجات صحيحة (من 0 إلى 100)</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # حساب المعدل
    average = sum(grades) / 3
    
    if average >= 90:
        result = f"""
🎉 <b>مبروك! أنت معفي من المادة</b>
━━━━━━━━━━━━━━
📊 <b>الدرجات:</b>
الكورس الأول: <code>{grades[0]}</code>
الكورس الثاني: <code>{grades[1]}</code>
الكورس الثالث: <code>{grades[2]}</code>

📈 <b>المعدل:</b> <code>{average:.2f}</code>
✅ <b>الحالة:</b> <b>معفي</b> 🎊
        """
    else:
        result = f"""
😔 <b>أنت غير معفي من المادة</b>
━━━━━━━━━━━━━━
📊 <b>الدرجات:</b>
الكورس الأول: <code>{grades[0]}</code>
الكورس الثاني: <code>{grades[1]}</code>
الكورس الثالث: <code>{grades[2]}</code>

📈 <b>المعدل:</b> <code>{average:.2f}</code>
❌ <b>الحالة:</b> <b>غير معفي</b>

💡 <b>نصيحة:</b> ركز على المادة وحاول تحسين درجاتك
        """
    
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)
    context.user_data['waiting_for_grades'] = False

async def service_pdf_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة تلخيص الملازم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    has_balance, price = check_balance(user_id, 'pdf_summary')
    
    if not has_balance:
        await query.edit_message_text(
            f"💰 <b>رصيدك غير كافي</b>\n"
            f"سعر الخدمة: <code>{format_number(price)} دينار</code>\n"
            f"الرجاء شحن رصيدك أولاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    if await deduct_balance(user_id, 'pdf_summary', context):
        instruction = """
📚 <b>تلخيص الملازم</b>
━━━━━━━━━━━━━━
<code>أرسل ملف PDF ليتم تلخيصه</code>

<b>ملاحظات:</b>
• الملف يجب أن يكون بصيغة PDF
• الحد الأقصى للحجم: 20MB
• سأقوم باستخراج النصوص وتلخيصها باستخدام الذكاء الاصطناعي
• ستحصل على ملف PDF جديد مرتب ومنسق
        """
        
        await query.edit_message_text(instruction, parse_mode=ParseMode.HTML)
        context.user_data['waiting_for_pdf'] = True

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف PDF للتلخيص"""
    if not context.user_data.get('waiting_for_pdf'):
        return
    
    user_id = update.message.from_user.id
    
    if not update.message.document or not update.message.document.file_name.endswith('.pdf'):
        await update.message.reply_text("❌ الرجاء إرسال ملف PDF فقط")
        return
    
    # إشعار ببدء المعالجة
    processing_msg = await update.message.reply_text("⏳ جاري معالجة الملف وتلخيصه...")
    
    try:
        # تحميل الملف
        file = await update.message.document.get_file()
        temp_input = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        await file.download_to_drive(temp_input.name)
        
        # استخراج النصوص من PDF
        doc = fitz.open(temp_input.name)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if not text.strip():
            await processing_msg.edit_text("❌ لم أتمكن من استخراج النصوص من الملف")
            return
        
        # تلخيص النص باستخدام Gemini
        prompt = f"""
        قم بتلخيص النص التعليمي التالي مع الحفاظ على المعلومات المهمة:
        
        {text[:3000]}...
        
        التلخيص يجب أن يكون:
        1. مرتب ومنظم
        2. باللغة العربية الفصحى
        3. يحوي النقاط الرئيسية فقط
        4. مناسب للطلاب
        5. مع عناوين رئيسية وفرعية
        
        قدم التلخيص في شكل مناسب للطباعة.
        """
        
        response = model.generate_content(prompt)
        summary = response.text if response else "عذراً، لم أتمكن من تلخيص النص"
        
        # إنشاء PDF جديد
        temp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        c = canvas.Canvas(temp_output.name, pagesize=letter)
        width, height = letter
        
        # إضافة العنوان
        c.setFont(ARABIC_FONT, 16)
        c.drawString(50, height - 50, format_arabic("ملخص المادة"))
        
        # إضافة النص الملخص
        c.setFont(ARABIC_FONT, 12)
        y = height - 100
        for line in summary.split('\n'):
            if y < 50:
                c.showPage()
                c.setFont(ARABIC_FONT, 12)
                y = height - 50
            
            c.drawString(50, y, format_arabic(line[:80]))
            y -= 20
        
        c.save()
        
        # إرسال الملف للمستخدم
        with open(temp_output.name, 'rb') as f:
            await update.message.reply_document(
                document=InputFile(f, filename='ملخص_المادة.pdf'),
                caption="✅ <b>تم تلخيص الملف بنجاح</b>\n"
                       "📄 الملف يحتوي على الملخص المنظم والمفيد",
                parse_mode=ParseMode.HTML
            )
        
        await processing_msg.delete()
        
        # تنظيف الملفات المؤقتة
        os.unlink(temp_input.name)
        os.unlink(temp_output.name)
        
    except Exception as e:
        logging.error(f"PDF processing error: {e}")
        await processing_msg.edit_text("❌ حدث خطأ في معالجة الملف")
    
    context.user_data['waiting_for_pdf'] = False

async def service_qna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة سؤال وجواب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    has_balance, price = check_balance(user_id, 'qna')
    
    if not has_balance:
        await query.edit_message_text(
            f"💰 <b>رصيدك غير كافي</b>\n"
            f"سعر الخدمة: <code>{format_number(price)} دينار</code>\n"
            f"الرجاء شحن رصيدك أولاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    if await deduct_balance(user_id, 'qna', context):
        instruction = """
❓ <b>سؤال وجواب</b>
━━━━━━━━━━━━━━
<code>أرسل سؤالك في أي مادة دراسية</code>

<b>ملاحظات:</b>
• يمكنك إرسال نص السؤال أو صورة تحتوي على السؤال
• الإجابات مبنية على المنهج العراقي
• الدقة والوضوح في الإجابة مضمونة
• يمكنك السؤال في أي تخصص
        """
        
        await query.edit_message_text(instruction, parse_mode=ParseMode.HTML)
        context.user_data['waiting_for_question'] = True

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأسئلة بالإجابة الذكية"""
    if not context.user_data.get('waiting_for_question'):
        return
    
    user_id = update.message.from_user.id
    question = ""
    
    if update.message.text:
        question = update.message.text
    elif update.message.caption:
        question = update.message.caption
    elif update.message.photo:
        # إذا كانت صورة، نطلب وصف نصي
        await update.message.reply_text("📝 الرجاء كتابة السؤال الموجود في الصورة")
        return
    
    if not question.strip():
        await update.message.reply_text("❌ الرجاء إدخال سؤال واضح")
        return
    
    processing_msg = await update.message.reply_text("🤔 جاري البحث عن الإجابة...")
    
    try:
        # استخدام Gemini للإجابة
        prompt = f"""
        أجب على السؤال التعليمي التالي بناءً على المنهج العراقي:
        
        السؤال: {question}
        
        اشتراطات الإجابة:
        1. يجب أن تكون الإجابة دقيقة وعلمية
        2. استخدم اللغة العربية الفصحى
        3. قدم الإجابة بشكل منظم وواضح
        4. إذا كان السؤال في مادة محددة، ركز على مفاهيمها
        5. قدم أمثلة إذا لزم الأمر
        6. أذكر المصادر أو المفاهيم الأساسية
        """
        
        response = model.generate_content(prompt)
        answer = response.text if response else "عذراً، لم أتمكن من الإجابة على السؤال حالياً"
        
        # تنسيق الإجابة
        formatted_answer = f"""
🧠 <b>إجابة على سؤالك:</b>
━━━━━━━━━━━━━━
<b>❓ السؤال:</b>
{question}

<b>💡 الإجابة:</b>
{answer}

<b>📚 ملاحظة:</b>
هذه الإجابة مبنية على المنهج التعليمي العراقي.
        """
        
        await update.message.reply_text(formatted_answer, parse_mode=ParseMode.HTML)
        await processing_msg.delete()
        
    except Exception as e:
        logging.error(f"Q&A error: {e}")
        await processing_msg.edit_text("❌ حدث خطأ في معالجة السؤال")
    
    context.user_data['waiting_for_question'] = False

async def service_help_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة ساعدوني طالب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    has_balance, price = check_balance(user_id, 'help_student')
    
    if not has_balance:
        await query.edit_message_text(
            f"💰 <b>رصيدك غير كافي</b>\n"
            f"سعر الخدمة: <code>{format_number(price)} دينار</code>\n"
            f"الرجاء شحن رصيدك أولاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    if await deduct_balance(user_id, 'help_student', context):
        instruction = """
🙋‍♂️ <b>ساعدوني طالب</b>
━━━━━━━━━━━━━━
<code>أرسل سؤالك وسيتم نشره للطلاب الآخرين للإجابة</code>

<b>معلومات الخدمة:</b>
• سؤالك سينشر في قسم خاص
• الطلاب الآخرون يمكنهم الإجابة
• أفضل إجابة تحصل على مكافأة 100 دينار
• يمكنك الموافقة على الإجابة أو رفضها
• السؤال يحذف بعد الإجابة عليه

<b>أرسل سؤالك الآن:</b>
        """
        
        await query.edit_message_text(instruction, parse_mode=ParseMode.HTML)
        context.user_data['waiting_for_student_question'] = True

async def handle_student_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أسئلة الطلاب"""
    if not context.user_data.get('waiting_for_student_question'):
        return
    
    user_id = update.message.from_user.id
    question = update.message.text
    
    if not question.strip():
        await update.message.reply_text("❌ الرجاء إدخال سؤال واضح")
        return
    
    # حفظ السؤال في قاعدة البيانات
    db.cursor.execute('''
        INSERT INTO student_questions (user_id, question, status)
        VALUES (?, ?, 'pending')
    ''', (user_id, question))
    db.conn.commit()
    
    question_id = db.cursor.lastrowid
    
    # إرسال إشعار للمطور للموافقة
    developer_msg = f"""
❓ <b>سؤال جديد يحتاج موافقة</b>
━━━━━━━━━━━━━━
<b>👤 المستخدم:</b> {update.message.from_user.mention_html()}
<b>🆔 رقم السؤال:</b> {question_id}
    
<b>📝 السؤال:</b>
{question}

<b>⏰ الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("✅ الموافقة", callback_data=f'approve_question_{question_id}'),
            InlineKeyboardButton("❌ الرفض", callback_data=f'reject_question_{question_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_message(DEVELOPER_ID, developer_msg, context, reply_markup)
    
    await update.message.reply_text(
        "✅ <b>تم استلام سؤالك</b>\n"
        "سيتم مراجعته ونشره قريباً للإجابة عليه.",
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['waiting_for_student_question'] = False

# ============== نظام VIP ==============
async def vip_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض محاضرات VIP"""
    query = update.callback_query
    await query.answer()
    
    db.cursor.execute('''
        SELECT vl.*, u.username 
        FROM vip_lectures vl
        LEFT JOIN users u ON vl.teacher_id = u.user_id
        WHERE vl.approved = 1
        ORDER BY vl.added_date DESC
    ''')
    lectures = db.cursor.fetchall()
    
    if not lectures:
        keyboard = [
            [InlineKeyboardButton("👑 اشتراك VIP", callback_data='vip_subscription')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
        ]
        
        await query.edit_message_text(
            "👑 <b>محاضرات VIP</b>\n"
            "━━━━━━━━━━━━━━\n"
            "لا توجد محاضرات VIP متاحة حالياً.\n"
            "كن أول من يضيف محاضرات VIP باشتراك VIP.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return
    
    # عرض أول محاضرة مع خيارات التنقل
    cols = [col[0] for col in db.cursor.description]
    lecture = dict(zip(cols, lectures[0]))
    
    message = f"""
👑 <b>محاضرة VIP</b>
━━━━━━━━━━━━━━
<b>📚 العنوان:</b> {lecture['title']}
<b>👨‍🏫 المعلم:</b> @{lecture['username'] or 'غير معروف'}
<b>📖 الوصف:</b> {lecture['description'][:100]}...
<b>💰 السعر:</b> {format_number(lecture['price'])} دينار
<b>⭐ التقييم:</b> {lecture['rating']:.1f}/5 ({lecture['rating_count']} تقييم)
<b>👁️ المشاهدات:</b> {format_number(lecture['views'])}
<b>🛒 المشتريات:</b> {format_number(lecture['purchases'])}
    """
    
    keyboard = []
    
    # زر الشراء
    keyboard.append([InlineKeyboardButton("🛒 شراء المحاضرة", callback_data=f'buy_lecture_{lecture["id"]}')])
    
    # أزرار التنقل إذا كان هناك أكثر من محاضرة
    if len(lectures) > 1:
        nav_buttons = []
        if len(lectures) > 1:
            nav_buttons.append(InlineKeyboardButton("التالي →", callback_data=f'next_lecture_0'))
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("👑 اشتراك VIP", callback_data='vip_subscription')])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['current_lecture_index'] = 0
    context.user_data['lectures_list'] = lectures

async def vip_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    monthly_price = int(db.get_setting('vip_monthly_price'))
    
    is_vip = user.get('is_vip') and user.get('vip_expiry') > datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if is_vip:
        expiry = datetime.strptime(user['vip_expiry'], '%Y-%m-%d %H:%M:%S')
        days_left = (expiry - datetime.now()).days
        
        message = f"""
👑 <b>اشتراك VIP - مفعل</b>
━━━━━━━━━━━━━━
<b>✨ المميزات:</b>
• رفع محاضرات VIP
• أرباح 60% من مبيعات محاضراتك
• لوحة تحكم خاصة
• سحب الأرباح عند وصولها 15,000 دينار
• أولوية في الدعم الفني

<b>📅 تاريخ الانتهاء:</b> {expiry.strftime('%Y-%m-%d')}
<b>⏳ الأيام المتبقية:</b> {days_left} يوم

<b>💼 أرباحك الحالية:</b> {format_number(db.get_lecture_earnings(user_id))} دينار
        """
        
        keyboard = [
            [InlineKeyboardButton("📤 رفع محاضرة", callback_data='upload_vip_lecture')],
            [InlineKeyboardButton("💰 أرباحي", callback_data='my_earnings')],
            [InlineKeyboardButton("🔄 تجديد الاشتراك", callback_data='renew_vip')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
        ]
    else:
        message = f"""
👑 <b>اشتراك VIP</b>
━━━━━━━━━━━━━━
<b>✨ المميزات:</b>
• رفع محاضرات VIP
• أرباح 60% من مبيعات محاضراتك
• لوحة تحكم خاصة
• سحب الأرباح عند وصولها 15,000 دينار
• أولوية في الدعم الفني

<b>💰 السعر الشهري:</b> {format_number(monthly_price)} دينار

<b>📋 الشروط:</b>
1. المحاضرات تخضع للمراجعة
2. يجب أن تكون المحاضرات ذات جودة عالية
3. يحق للإدارة حذف المحاضرات غير المناسبة
4. الأرباح تصل بعد 24 ساعة من البيع
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 اشتراك الآن", callback_data='subscribe_vip_now')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
        ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============== لوحة التحكم ==============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المطور"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if user_id != DEVELOPER_ID and not user.get('is_admin'):
        await query.answer("⛔ ليس لديك صلاحية الوصول", show_alert=True)
        return
    
    # إحصائيات البوت
    db.cursor.execute('SELECT COUNT(*) FROM users')
    total_users = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1')
    vip_users = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
    total_balance = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM transactions')
    total_transactions = db.cursor.fetchone()[0]
    
    maintenance_mode = db.get_setting('maintenance_mode') == '1'
    
    message = f"""
⚙️ <b>لوحة التحكم - الإدارة</b>
━━━━━━━━━━━━━━
<b>📊 إحصائيات البوت:</b>
👥 المستخدمين: {format_number(total_users)}
👑 مستخدمين VIP: {format_number(vip_users)}
💰 إجمالي الرصيد: {format_number(total_balance)} دينار
💳 المعاملات: {format_number(total_transactions)}

<b>🔧 حالة البوت:</b> {'🛑 تحت الصيانة' if maintenance_mode else '✅ يعمل بشكل طبيعي'}
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("💳 الشحن والخصم", callback_data='admin_balance')],
        [InlineKeyboardButton("🚫 الحظر والإلغاء", callback_data='admin_ban')],
        [InlineKeyboardButton("📊 الإحصائيات المفصلة", callback_data='admin_stats')],
        [InlineKeyboardButton("⚙️ إعدادات الخدمات", callback_data='admin_services')],
        [InlineKeyboardButton("👑 إدارة VIP", callback_data='admin_vip')],
        [InlineKeyboardButton("📣 إذاعة عامة", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔧 وضع الصيانة", callback_data='toggle_maintenance')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        await query.answer("⛔ ليس لديك صلاحية الوصول", show_alert=True)
        return
    
    db.cursor.execute('SELECT * FROM users ORDER BY joined_date DESC LIMIT 10')
    users = db.cursor.fetchall()
    
    if not users:
        message = "لا يوجد مستخدمين حالياً."
    else:
        cols = [col[0] for col in db.cursor.description]
        message = "👥 <b>آخر 10 مستخدمين</b>\n━━━━━━━━━━━━━━\n"
        
        for user in users:
            user_dict = dict(zip(cols, user))
            status = "👑 VIP" if user_dict['is_vip'] else ("🚫 محظور" if user_dict['is_banned'] else "✅ نشط")
            message += f"\n👤 {user_dict['first_name']} (@{user_dict['username'] or 'لا يوجد'})"
            message += f"\n🆔: {user_dict['user_id']} | 💰: {format_number(user_dict['balance'])}"
            message += f"\n📅: {user_dict['joined_date'][:10]} | {status}"
            message += "\n" + "─" * 30
    
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data='admin_search_user')],
        [InlineKeyboardButton("📋 جميع المستخدمين", callback_data='admin_all_users')],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الرصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        await query.answer("⛔ ليس لديك صلاحية الوصول", show_alert=True)
        return
    
    message = """
💳 <b>إدارة الرصيد</b>
━━━━━━━━━━━━━━
<b>اختر العملية:</b>
• الشحن: إضافة رصيد لمستخدم
• الخصم: خصم رصيد من مستخدم
• التحويل: نقل رصيد بين مستخدمين

<b>أرسل:</b>
1. لشحن: <code>ايدي_المستخدم المبلغ</code>
2. لخصم: <code>خصم ايدي_المستخدم المبلغ</code>
3. للتحويل: <code>تحويل من_ايدي الى_ايدي المبلغ</code>

<blockquote>مثال للشحن:
123456789 5000

مثال للخصم:
خصم 123456789 3000

مثال للتحويل:
تحويل 123456789 987654321 2000</blockquote>
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 عرض المعاملات", callback_data='admin_transactions')],
        [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['admin_action'] = 'balance_management'

# ============== معالجة الأوامر الإدارية ==============
async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأوامر الإدارية"""
    user_id = update.message.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        return
    
    text = update.message.text.strip()
    
    if context.user_data.get('admin_action') == 'balance_management':
        # معالجة أوامر الرصيد
        if text.startswith('خصم '):
            try:
                parts = text[4:].split()
                target_id = int(parts[0])
                amount = int(parts[1])
                
                target_user = db.get_user(target_id)
                if not target_user:
                    await update.message.reply_text("❌ المستخدم غير موجود")
                    return
                
                if target_user['balance'] < amount:
                    await update.message.reply_text("❌ رصيد المستخدم غير كافي للخصم")
                    return
                
                db.update_balance(target_id, -amount, 'admin_deduction', f'خصم إداري بواسطة {user_id}')
                
                # إشعار للمستخدم
                user_notification = f"""
⚠️ <b>تم خصم مبلغ من حسابك</b>
━━━━━━━━━━━━━━
💰 المبلغ: <code>{format_number(amount)} دينار</code>
📝 السبب: خصم إداري
📊 الرصيد الجديد: <code>{format_number(target_user['balance'] - amount)} دينار</code>
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                await send_message(target_id, user_notification, context)
                
                await update.message.reply_text(
                    f"✅ تم خصم <code>{format_number(amount)}</code> دينار من المستخدم {target_id}",
                    parse_mode=ParseMode.HTML
                )
                
            except Exception as e:
                await update.message.reply_text("❌ صيغة الأمر غير صحيحة")
        
        elif text.startswith('تحويل '):
            try:
                parts = text[6:].split()
                from_id = int(parts[0])
                to_id = int(parts[1])
                amount = int(parts[2])
                
                from_user = db.get_user(from_id)
                to_user = db.get_user(to_id)
                
                if not from_user or not to_user:
                    await update.message.reply_text("❌ أحد المستخدمين غير موجود")
                    return
                
                if from_user['balance'] < amount:
                    await update.message.reply_text("❌ رصيد المستخدم المرسل غير كافي")
                    return
                
                # خصم من المرسل
                db.update_balance(from_id, -amount, 'transfer_out', f'تحويل إلى {to_id}')
                # إضافة للمستلم
                db.update_balance(to_id, amount, 'transfer_in', f'تحويل من {from_id}')
                
                # إشعارات للمستخدمين
                notification_from = f"""
💸 <b>تحويل مبلغ</b>
━━━━━━━━━━━━━━
💰 المبلغ المحول: <code>{format_number(amount)} دينار</code>
👤 إلى المستخدم: {to_id}
📊 رصيدك الجديد: <code>{format_number(from_user['balance'] - amount)} دينار</code>
                """
                
                notification_to = f"""
🎁 <b>استلام مبلغ</b>
━━━━━━━━━━━━━━
💰 المبلغ المستلم: <code>{format_number(amount)} دينار</code>
👤 من المستخدم: {from_id}
📊 رصيدك الجديد: <code>{format_number(to_user['balance'] + amount)} دينار</code>
                """
                
                await send_message(from_id, notification_from, context)
                await send_message(to_id, notification_to, context)
                
                await update.message.reply_text(
                    f"✅ تم تحويل <code>{format_number(amount)}</code> دينار من {from_id} إلى {to_id}",
                    parse_mode=ParseMode.HTML
                )
                
            except Exception as e:
                await update.message.reply_text("❌ صيغة الأمر غير صحيحة")
        
        else:
            try:
                parts = text.split()
                if len(parts) == 2:
                    target_id = int(parts[0])
                    amount = int(parts[1])
                    
                    target_user = db.get_user(target_id)
                    if not target_user:
                        await update.message.reply_text("❌ المستخدم غير موجود")
                        return
                    
                    db.update_balance(target_id, amount, 'admin_charge', f'شحن إداري بواسطة {user_id}')
                    
                    # إشعار للمستخدم
                    user_notification = f"""
🎉 <b>تم شحن حسابك</b>
━━━━━━━━━━━━━━
💰 المبلغ: <code>{format_number(amount)} دينار</code>
📝 السبب: شحن إداري
📊 الرصيد الجديد: <code>{format_number(target_user['balance'] + amount)} دينار</code>
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    """
                    await send_message(target_id, user_notification, context)
                    
                    await update.message.reply_text(
                        f"✅ تم شحن <code>{format_number(amount)}</code> دينار للمستخدم {target_id}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.message.reply_text("❌ صيغة الأمر غير صحيحة")
                    
            except Exception as e:
                await update.message.reply_text("❌ صيغة الأمر غير صحيحة")

# ============== وظائف الإذاعة ==============
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إذاعة رسالة لجميع المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        await query.answer("⛔ ليس لديك صلاحية الوصول", show_alert=True)
        return
    
    message = """
📣 <b>الإذاعة العامة</b>
━━━━━━━━━━━━━━
<code>أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين</code>

<b>ملاحظات:</b>
• يمكنك استخدام HTML للتنسيق
• الرسالة سترسل لجميع المستخدمين النشطين
• العملية قد تستغرق بعض الوقت
• لا يمكن التراجع عن الإذاعة
    """
    
    await query.edit_message_text(message, parse_mode=ParseMode.HTML)
    context.user_data['admin_action'] = 'broadcast'

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسالة للإذاعة"""
    user_id = update.message.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        return
    
    if context.user_data.get('admin_action') != 'broadcast':
        return
    
    broadcast_text = update.message.text_html or update.message.text
    
    if not broadcast_text.strip():
        await update.message.reply_text("❌ الرسالة فارغة")
        return
    
    # تأكيد الإذاعة
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، قم بالإذاعة", callback_data=f'confirm_broadcast_{hash(broadcast_text)}'),
            InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')
        ]
    ]
    
    preview = broadcast_text[:200] + ("..." if len(broadcast_text) > 200 else "")
    
    await update.message.reply_text(
        f"📣 <b>تأكيد الإذاعة</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>معاينة الرسالة:</b>\n{preview}\n\n"
        f"سيتم إرسال هذه الرسالة لجميع المستخدمين.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ الإذاعة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != DEVELOPER_ID and not db.get_user(user_id).get('is_admin'):
        return
    
    # جلب جميع المستخدمين
    db.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
    all_users = db.cursor.fetchall()
    
    total_users = len(all_users)
    successful = 0
    failed = 0
    
    progress_msg = await query.edit_message_text(
        f"📤 جاري الإذاعة...\n"
        f"━━━━━━━━━━━━━━\n"
        f"✅ تم إرسال: 0\n"
        f"❌ فشل: 0\n"
        f"📊 الإجمالي: {total_users}\n"
        f"⏳ المتبقي: {total_users}",
        parse_mode=ParseMode.HTML
    )
    
    broadcast_text = context.user_data.get('broadcast_text', '')
    
    for index, (user_id,) in enumerate(all_users, 1):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode=ParseMode.HTML
            )
            successful += 1
        except Exception as e:
            failed += 1
        
        # تحديث الرسالة كل 10 مستخدمين
        if index % 10 == 0 or index == total_users:
            await progress_msg.edit_text(
                f"📤 جاري الإذاعة...\n"
                f"━━━━━━━━━━━━━━\n"
                f"✅ تم إرسال: {successful}\n"
                f"❌ فشل: {failed}\n"
                f"📊 الإجمالي: {total_users}\n"
                f"⏳ المتبقي: {total_users - index}\n"
                f"📈 النسبة: {(index/total_users)*100:.1f}%",
                parse_mode=ParseMode.HTML
            )
    
    # نتيجة الإذاعة
    result_message = f"""
🎉 <b>تمت الإذاعة بنجاح</b>
━━━━━━━━━━━━━━
<b>📊 النتائج:</b>
✅ تم إرسال بنجاح: {successful}
❌ فشل في الإرسال: {failed}
📊 الإجمالي: {total_users}
📈 نسبة النجاح: {(successful/total_users)*100:.1f}%
    """
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]]
    
    await progress_msg.edit_text(
        result_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['admin_action'] = None

# ============== وظائف إضافية ==============
async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رصيد المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    # جلب آخر 5 معاملات
    db.cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT 5
    ''', (user_id,))
    transactions = db.cursor.fetchall()
    
    message = f"""
💰 <b>رصيدك الحالي</b>
━━━━━━━━━━━━━━
<b>💵 المبلغ:</b> <code>{format_number(user['balance'])} دينار عراقي</code>

<b>📨 رابط الدعوة:</b>
<code>https://t.me/{BOT_USERNAME[1:]}?start={user['invite_code']}</code>

<b>🎁 مكافأة الدعوة:</b> 1000 دينار لكل صديق
<b>👥 عدد الدعوات:</b> {user['invited_count']}
    """
    
    if transactions:
        cols = [col[0] for col in db.cursor.description]
        message += "\n\n<b>📝 آخر المعاملات:</b>\n"
        for trans in transactions:
            trans_dict = dict(zip(cols, trans))
            amount = trans_dict['amount']
            sign = "+" if amount > 0 else ""
            message += f"\n{sign}{format_number(amount)} - {trans_dict['description']}"
    
    keyboard = [
        [
            InlineKeyboardButton("💳 شحن الرصيد", url=f"https://t.me/{DEVELOPER_USERNAME[1:]}"),
            InlineKeyboardButton("📤 مشاركة الرابط", callback_data='share_invite')
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def share_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مشاركة رابط الدعوة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        return
    
    invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={user['invite_code']}"
    
    share_text = f"""
🎉 <b>انضم إلى بوت "يلا نتعلم" التعليمي!</b>

✨ <b>المميزات:</b>
• حساب درجة الإعفاء
• تلخيص الملازم بالذكاء الاصطناعي
• سؤال وجواب لأي مادة
• مساعدة الطلاب والإجابة على أسئلتهم
• محاضرات VIP حصرية
• هدية ترحيبية 1000 دينار

🔗 <b>رابط الانضمام:</b>
{invite_link}

🎁 <b>احصل على 1000 دينار مجاناً عند الانضمام!</b>
    """
    
    keyboard = [
        [InlineKeyboardButton("📲 مشاركة", url=f"https://t.me/share/url?url={invite_link}&text={html.escape(share_text)}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data='my_balance')]
    ]
    
    await query.edit_message_text(
        "📤 <b>مشاركة رابط الدعوة</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اضغط على الزر أدناه لمشاركة الرابط مع أصدقائك.\n"
        "ستحصل على 1000 دينار لكل صديق ينضم عبر رابطك!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة المساعدة"""
    query = update.callback_query
    await query.answer()
    
    support_username = db.get_setting('support_username') or DEVELOPER_USERNAME
    channel_link = db.get_setting('channel_link') or CHANNEL_LINK
    
    message = f"""
ℹ️ <b>مركز المساعدة</b>
━━━━━━━━━━━━━━
<b>📞 الدعم الفني:</b> @{support_username[1:] if support_username.startswith('@') else support_username}
<b>📢 قناة البوت:</b> {channel_link}

<b>❓ الأسئلة الشائعة:</b>

<b>Q: كيف أشحن رصيدي؟</b>
A: تواصل مع الدعم الفني @{support_username[1:] if support_username.startswith('@') else support_username}

<b>Q: كيف أحصل على رصيد مجاني؟</b>
A: ادعُ أصدقائك عبر رابط الدعوة في قسم "رصيدي"

<b>Q: الخدمة لا تعمل، ماذا أفعل؟</b>
A: تأكد من أن رصيدك كافٍ، إذا استمرت المشكلة تواصل مع الدعم

<b>Q: كيف أصبح معلم VIP؟</b>
A: اشترك في خدمة VIP من قسم "محاضرات VIP"

<b>⚠️ ملاحظة:</b>
جميع الخدمات مدفوعة، وأقل سعر للخدمة هو 1000 دينار عراقي.
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📞 الدعم الفني", url=f"https://t.me/{support_username[1:] if support_username.startswith('@') else support_username}"),
            InlineKeyboardButton("📢 القناة", url=channel_link)
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    if query:
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للواجهة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    keyboard = [
        [InlineKeyboardButton("🧮 حساب درجة الإعفاء", callback_data='service_exemption_calculator')],
        [InlineKeyboardButton("📚 تلخيص الملازم", callback_data='service_pdf_summary')],
        [InlineKeyboardButton("❓ سؤال وجواب", callback_data='service_qna')],
        [InlineKeyboardButton("🙋‍♂️ ساعدوني طالب", callback_data='service_help_student')],
        [InlineKeyboardButton("🎓 ملازمي ومرشحاتي", callback_data='study_materials')],
        [InlineKeyboardButton("👑 محاضرات VIP", callback_data='vip_lectures')],
        [
            InlineKeyboardButton("💳 رصيدي", callback_data='my_balance'),
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data='invite_friends')
        ],
        [
            InlineKeyboardButton("📊 إحصائياتي", callback_data='my_stats'),
            InlineKeyboardButton("ℹ️ المساعدة", callback_data='help')
        ]
    ]
    
    user_data = db.get_user(user.id)
    if user_data.get('is_vip') and user_data.get('vip_expiry') > datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
        keyboard.insert(5, [InlineKeyboardButton("👨‍🏫 رفع محاضرة VIP", callback_data='upload_vip_lecture')])
    
    if user.id == DEVELOPER_ID or user_data.get('is_admin'):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎉 <b>مرحباً بعودتك {user.first_name}!</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>💰 رصيدك:</b> <code>{format_number(user_data['balance'])} دينار</code>\n\n"
        f"<b>📚 اختر الخدمة المطلوبة:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# ============== معالجة استدعاءات الأزرار ==============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع استدعاءات الأزرار"""
    query = update.callback_query
    data = query.data
    
    # معالجة أزرار الخدمات
    if data.startswith('service_'):
        service_name = data[8:]
        if service_name == 'exemption_calculator':
            await service_exemption_calculator(update, context)
        elif service_name == 'pdf_summary':
            await service_pdf_summary(update, context)
        elif service_name == 'qna':
            await service_qna(update, context)
        elif service_name == 'help_student':
            await service_help_student(update, context)
    
    # معالجة أزرار أخرى
    elif data == 'my_balance':
        await my_balance(update, context)
    elif data == 'help':
        await help_command(update, context)
    elif data == 'admin_panel':
        await admin_panel(update, context)
    elif data == 'admin_users':
        await admin_users(update, context)
    elif data == 'admin_balance':
        await admin_balance(update, context)
    elif data == 'admin_broadcast':
        await admin_broadcast(update, context)
    elif data == 'back_to_main':
        await back_to_main(update, context)
    elif data == 'vip_lectures':
        await vip_lectures(update, context)
    elif data == 'vip_subscription':
        await vip_subscription(update, context)
    elif data == 'share_invite':
        await share_invite(update, context)
    
    # يمكن إضافة المزيد من معالجات الأزرار هنا

# ============== الوظيفة الرئيسية ==============
def main():
    """تشغيل البوت"""
    # إعداد التسجيل
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # معالجة الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handle_admin_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handle_grades))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handle_question))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                         handle_student_question))
    
    # معالجة الملفات
    application.add_handler(MessageHandler(filters.Document.PDF, 
                                         handle_pdf))
    
    # معالجة استدعاءات الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # بدء البوت
    print("✅ البوت يعمل بنجاح!")
    print(f"👤 المطور: {DEVELOPER_USERNAME}")
    print(f"🤖 البوت: {BOT_USERNAME}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
