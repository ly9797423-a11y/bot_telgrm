import os
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
import pdfkit
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
import requests
from io import BytesIO
import aiofiles
import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import re

# ========== إعدادات البوت ==========
TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
BOT_USERNAME = "@FC4Xbot"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04@"
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"

# إعداد Google Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# ========== إعداد قاعدة البيانات ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER DEFAULT 1000,
                points INTEGER DEFAULT 0,
                invited_by INTEGER,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_expiry TIMESTAMP,
                is_teacher INTEGER DEFAULT 0,
                teacher_earnings INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول المعاملات المالية
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
        
        # جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # جدول المواد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                stage TEXT,
                file_id TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # جدول محاضرات VIP
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_lectures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                title TEXT,
                description TEXT,
                video_id TEXT,
                price INTEGER DEFAULT 1000,
                views INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                total_ratings INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # جدول مشتريات المحاضرات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecture_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lecture_id INTEGER,
                amount_paid INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تقييمات المحاضرات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecture_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lecture_id INTEGER,
                rating INTEGER,
                comment TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول أسئلة "ساعدوني طالب"
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS help_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                subject TEXT,
                price INTEGER DEFAULT 1000,
                status TEXT DEFAULT 'pending',
                answer TEXT,
                answered_by INTEGER,
                answer_date TIMESTAMP,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الخدمات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER DEFAULT 1000,
                is_active INTEGER DEFAULT 1,
                description TEXT
            )
        ''')
        
        # جدول الإشعارات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # إضافة الخدمات الأساسية إذا لم تكن موجودة
        default_services = [
            ('حساب درجة الاعفاء', 1000, 1, 'حساب درجة الإعفاء الفردي للطالب'),
            ('تلخيص الملازم', 1000, 1, 'تلخيص الملازم باستخدام الذكاء الاصطناعي'),
            ('سؤال وجواب', 1000, 1, 'أسئلة وأجوبة في أي مادة'),
            ('ساعدوني طالب', 1000, 1, 'مساعدة الطلاب في الأسئلة'),
            ('الملازم والمرشحات', 1000, 1, 'الوصول إلى المكتبة التعليمية'),
            ('محاضرات VIP', 1000, 1, 'الوصول إلى محاضرات VIP')
        ]
        
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO services (name, price, is_active, description) VALUES (?, ?, ?, ?)",
                default_services
            )
        
        # الإعدادات الافتراضية
        default_settings = [
            ('maintenance', '0'),
            ('invite_reward', '500'),
            ('teacher_subscription_price', '5000'),
            ('admin_revenue_percentage', '40'),
            ('min_withdrawal', '15000'),
            ('bot_channel', '@education_channel'),
            ('support_username', SUPPORT_USERNAME)
        ]
        
        for key, value in default_settings:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        
        self.conn.commit()
    
    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default
    
    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name, invited_by=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, invited_by, balance, join_date)
                VALUES (?, ?, ?, ?, ?, 1000, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name, invited_by))
            
            if invited_by:
                # منح مكافأة للمدعو
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (1000, user_id)
                )
                # منح مكافأة للمدعِي
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (500, invited_by)
                )
                # تسجيل المعاملة
                self.add_transaction(user_id, 1000, 'reward', 'مكافأة ترحيبية')
                self.add_transaction(invited_by, 500, 'reward', 'مكافأة دعوة')
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    
    def update_balance(self, user_id, amount, transaction_type='', description=''):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        if transaction_type:
            self.add_transaction(user_id, amount, transaction_type, description)
        self.conn.commit()
        return True
    
    def add_transaction(self, user_id, amount, transaction_type, description):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, transaction_type, description))
        self.conn.commit()
    
    def get_user_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE date(join_date) = date('now')")
        today_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(balance) FROM users")
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        vip_users = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'today_users': today_users,
            'total_balance': total_balance,
            'vip_users': vip_users
        }
    
    def get_all_users(self, limit=100, offset=0):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, balance, 
                   is_banned, is_vip, join_date 
            FROM users 
            ORDER BY join_date DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        return cursor.fetchall()
    
    def search_user(self, query):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, balance 
            FROM users 
            WHERE user_id = ? OR username LIKE ? OR first_name LIKE ? 
            OR last_name LIKE ?
            LIMIT 10
        ''', (query if query.isdigit() else -1, f'%{query}%', f'%{query}%', f'%{query}%'))
        return cursor.fetchall()
    
    def toggle_service(self, service_id, status):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE services SET is_active = ? WHERE id = ?",
            (1 if status else 0, service_id)
        )
        self.conn.commit()
    
    def get_services(self, active_only=False):
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY id")
        else:
            cursor.execute("SELECT * FROM services ORDER BY id")
        return cursor.fetchall()
    
    def update_service_price(self, service_id, price):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE services SET price = ? WHERE id = ?",
            (price, service_id)
        )
        self.conn.commit()
    
    def add_material(self, name, description, stage, file_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO materials (name, description, stage, file_id)
            VALUES (?, ?, ?, ?)
        ''', (name, description, stage, file_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_materials(self, stage=None):
        cursor = self.conn.cursor()
        if stage:
            cursor.execute(
                "SELECT * FROM materials WHERE stage = ? AND is_active = 1 ORDER BY added_date DESC",
                (stage,)
            )
        else:
            cursor.execute("SELECT * FROM materials WHERE is_active = 1 ORDER BY added_date DESC")
        return cursor.fetchall()
    
    def delete_material(self, material_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE materials SET is_active = 0 WHERE id = ?", (material_id,))
        self.conn.commit()
    
    def add_vip_lecture(self, teacher_id, title, description, video_id, price):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO vip_lectures (teacher_id, title, description, video_id, price, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (teacher_id, title, description, video_id, price))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_vip_lectures(self, status='approved', teacher_id=None):
        cursor = self.conn.cursor()
        if teacher_id:
            cursor.execute('''
                SELECT * FROM vip_lectures 
                WHERE teacher_id = ? AND status = ? AND is_active = 1 
                ORDER BY added_date DESC
            ''', (teacher_id, status))
        else:
            cursor.execute('''
                SELECT * FROM vip_lectures 
                WHERE status = ? AND is_active = 1 
                ORDER BY added_date DESC
            ''', (status,))
        return cursor.fetchall()
    
    def update_lecture_status(self, lecture_id, status):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE vip_lectures SET status = ? WHERE id = ?",
            (status, lecture_id)
        )
        self.conn.commit()
    
    def purchase_lecture(self, user_id, lecture_id, amount):
        cursor = self.conn.cursor()
        
        # الحصول على معلومات المحاضرة
        cursor.execute("SELECT teacher_id, price FROM vip_lectures WHERE id = ?", (lecture_id,))
        lecture = cursor.fetchone()
        
        if not lecture:
            return False
        
        teacher_id = lecture[0]
        price = lecture[1]
        
        # حساب النسب
        admin_percentage = int(self.get_setting('admin_revenue_percentage', 40))
        teacher_percentage = 100 - admin_percentage
        
        teacher_earnings = (price * teacher_percentage) // 100
        admin_earnings = price - teacher_earnings
        
        # تسجيل الشراء
        cursor.execute('''
            INSERT INTO lecture_purchases (user_id, lecture_id, amount_paid)
            VALUES (?, ?, ?)
        ''', (user_id, lecture_id, price))
        
        # تحديث أرباح المعلم
        cursor.execute('''
            UPDATE users SET teacher_earnings = teacher_earnings + ? 
            WHERE user_id = ?
        ''', (teacher_earnings, teacher_id))
        
        # تحديث عدد المشاهدات
        cursor.execute('''
            UPDATE vip_lectures SET views = views + 1 WHERE id = ?
        ''', (lecture_id,))
        
        self.conn.commit()
        return True
    
    def add_help_question(self, user_id, question, subject, price):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO help_questions (user_id, question, subject, price, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (user_id, question, subject, price))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_help_questions(self, status='pending'):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT hq.*, u.username, u.first_name 
            FROM help_questions hq
            LEFT JOIN users u ON hq.user_id = u.user_id
            WHERE hq.status = ?
            ORDER BY hq.added_date DESC
        ''', (status,))
        return cursor.fetchall()
    
    def answer_question(self, question_id, answer, answered_by):
        cursor = self.conn.cursor()
        
        # تحديث السؤال
        cursor.execute('''
            UPDATE help_questions 
            SET status = 'answered', answer = ?, answered_by = ?, answer_date = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (answer, answered_by, question_id))
        
        # منح مكافأة للمجيب
        cursor.execute(
            "UPDATE users SET balance = balance + 100 WHERE user_id = ?",
            (answered_by,)
        )
        
        self.conn.commit()
    
    def add_notification(self, user_id, message):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (user_id, message))
        self.conn.commit()
    
    def get_unread_notifications(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM notifications 
            WHERE user_id = ? AND is_read = 0 
            ORDER BY date DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def mark_notifications_read(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE notifications SET is_read = 1 
            WHERE user_id = ? AND is_read = 0
        ''', (user_id,))
        self.conn.commit()

db = Database()

# ========== إعداد البوت ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ========== متغيرات حالة المستخدم ==========
user_states = {}
pending_payments = {}
pending_questions = {}

# ========== الدوال المساعدة ==========
async def send_notification(user_id, message, context):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📢 *إشعار جديد*\n\n{message}",
            parse_mode=ParseMode.MARKDOWN
        )
        db.add_notification(user_id, message)
    except Exception as e:
        print(f"Failed to send notification to {user_id}: {e}")

def format_currency(amount):
    return f"{amount:,} دينار عراقي"

def create_main_menu(user_id):
    keyboard = []
    
    # الحصول على الخدمات النشطة
    services = db.get_services(active_only=True)
    
    row = []
    for service in services:
        row.append(InlineKeyboardButton(
            f"{service[1]} ({format_currency(service[2])})",
            callback_data=f"service_{service[0]}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # إضافة أزرار إضافية
    keyboard.append([
        InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
        InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite")
    ])
    
    keyboard.append([
        InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
        InlineKeyboardButton("🎓 محاضرات VIP", callback_data="vip_lectures")
    ])
    
    # التحقق إذا كان المستخدم مدير
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
    
    # إضافة روابط الدعم والقناة
    bot_channel = db.get_setting('bot_channel', '@education_channel')
    support_user = db.get_setting('support_username', SUPPORT_USERNAME)
    
    keyboard.append([
        InlineKeyboardButton("📢 قناة البوت", url=bot_channel),
        InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"https://t.me/{support_user.replace('@', '')}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def check_balance(user_id, service_price, context):
    user = db.get_user(user_id)
    if not user:
        return False
    
    if user[5] < service_price:  # العمود 5 هو الرصيد
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ *رصيدك غير كافي*\n\nرصيدك الحالي: {format_currency(user[5])}\nسعر الخدمة: {format_currency(service_price)}\n\nيرجى شحن رصيدك أولاً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return False
    
    return True

async def deduct_balance(user_id, amount, service_name):
    db.update_balance(user_id, -amount, 'purchase', f"شراء خدمة: {service_name}")
    return True

# ========== معالجات الأوامر ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الصيانة
    if db.get_setting('maintenance') == '1' and user_id != ADMIN_ID:
        await update.message.reply_text(
            "🔧 *البوت تحت الصيانة*\n\nنعمل على تحسين الخدمة، يرجى المحاولة لاحقاً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # إضافة المستخدم إذا كان جديداً
    invited_by = None
    if context.args:
        try:
            invited_by = int(context.args[0])
        except:
            pass
    
    db.add_user(user_id, user.username, user.first_name, user.last_name, invited_by)
    
    # إرسال رسالة الترحيب
    welcome_text = f"""
    🎓 *مرحباً {user.first_name} في بوت "يلا نتعلم"*

    *خدماتنا التعليمية:*
    • حساب درجة الإعفاء الفردي
    • تلخيص الملازم بالذكاء الاصطناعي
    • أسئلة وأجوبة في أي مادة
    • مساعدة الطلاب (ساعدوني طالب)
    • المكتبة التعليمية (ملازم ومرشحات)
    • محاضرات VIP للمعلمين

    💰 *رصيدك الابتدائي:* {format_currency(1000)}
    
    اختر الخدمة التي تريدها من القائمة:
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_menu(user_id)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ المستخدم غير موجود!")
        return
    
    balance_text = f"""
    💰 *معلومات رصيدك*

    *الرصيد الحالي:* {format_currency(user[5])}
    *النقاط:* {user[6]}
    
    *لشحن الرصيد:* تواصل مع الدعم الفني
    @{db.get_setting('support_username', SUPPORT_USERNAME).replace('@', '')}
    
    أو احصل على نقاط مجانية عن طريق دعوة الأصدقاء!
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(
        balance_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== معالجة الخدمات ==========
async def handle_service_1(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """حساب درجة الإعفاء"""
    service = db.get_services()[0]  # الخدمة الأولى
    service_price = service[2]
    
    if not await check_balance(user_id, service_price, context):
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text="📊 *حساب درجة الإعفاء*\n\n"
             "أدخل درجات الكورسات الثلاثة (مفصولة بفاصلة):\n"
             "مثال: 85,90,92\n\n"
             "ملاحظة: المعدل يجب أن يكون 90 أو أكثر للإعفاء",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_states[user_id] = 'waiting_for_grades'

async def calculate_exemption(grades_str):
    try:
        grades = [float(g.strip()) for g in grades_str.split(',')]
        if len(grades) != 3:
            return "❌ يجب إدخال 3 درجات فقط"
        
        if any(g < 0 or g > 100 for g in grades):
            return "❌ الدرجات يجب أن تكون بين 0 و 100"
        
        average = sum(grades) / 3
        
        if average >= 90:
            return f"🎉 *مبروك! أنت معفى*\n\nالمعدل: {average:.2f}\nالدرجات: {grades}"
        else:
            return f"📚 *أنت غير معفى*\n\nالمعدل: {average:.2f}\nالدرجات: {grades}\n\nيجب أن يكون المعدل 90 أو أكثر للإعفاء"
    
    except ValueError:
        return "❌ خطأ في إدخال الدرجات، يرجى إدخال أرقام صحيحة"

async def handle_service_2(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """تلخيص الملازم"""
    service = db.get_services()[1]
    service_price = service[2]
    
    if not await check_balance(user_id, service_price, context):
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text="📄 *تلخيص الملازم*\n\n"
             "أرسل ملف PDF الذي تريد تلخيصه.\n\n"
             "ملاحظة:\n"
             "• سيتم تلخيص الملف باستخدام الذكاء الاصطناعي\n"
             "• التلخيص يشمل النقاط الرئيسية فقط\n"
             "• الملف الناتج سيكون مرتب ومنظم",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_states[user_id] = 'waiting_for_pdf'

async def summarize_pdf(pdf_file):
    try:
        # تحميل PDF
        response = requests.get(pdf_file)
        pdf_content = response.content
        
        # استخراج النص من PDF
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        text = ""
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        
        # استخدام Gemini AI للتلخيص
        prompt = f"""
        قم بتلخيص النص التالي مع التركيز على النقاط الرئيسية والمهمة فقط.
        حذف المعلومات الغير ضرورية وترتيب المحتوى بشكل منظم.
        يجب أن يكون التلخيص باللغة العربية الفصحى.
        
        النص:
        {text[:3000]}  # إرسال أول 3000 حرف فقط
        
        قدم التلخيص في نقاط رئيسية مع عناوين فرعية.
        """
        
        response = model.generate_content(prompt)
        summary = response.text
        
        # إنشاء PDF ملخص
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        
        # تسجيل الخط العربي
        try:
            pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
        except:
            pass
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # إنشاء نمط للعربية
        arabic_style = ParagraphStyle(
            'ArabicStyle',
            parent=styles['Normal'],
            fontName='Arabic',
            fontSize=12,
            alignment=2,  # محاذاة لليمين
            rightIndent=20,
            leftIndent=20
        )
        
        story = []
        
        # عنوان التلخيص
        title = Paragraph("<b>ملخص الملف التعليمي</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.25*inch))
        
        # إضافة التلخيص
        summary_paragraphs = summary.split('\n')
        for para in summary_paragraphs:
            if para.strip():
                p = Paragraph(para, arabic_style)
                story.append(p)
                story.append(Spacer(1, 0.1*inch))
        
        doc.build(story)
        buffer.seek(0)
        
        return buffer, "تم التلخيص بنجاح!"
    
    except Exception as e:
        print(f"PDF summarization error: {e}")
        return None, f"❌ حدث خطأ في معالجة الملف: {str(e)}"

async def handle_service_3(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """سؤال وجواب"""
    service = db.get_services()[2]
    service_price = service[2]
    
    if not await check_balance(user_id, service_price, context):
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text="❓ *سؤال وجواب*\n\n"
             "أرسل سؤالك أو صورة تحتوي على السؤال.\n\n"
             "سأجيبك باستخدام الذكاء الاصطناعي حسب المنهج العراقي.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_states[user_id] = 'waiting_for_question'

async def answer_question_with_ai(question_text, is_image=False, image_file=None):
    try:
        if is_image and image_file:
            # معالجة الصورة
            response = requests.get(image_file)
            image_content = response.content
            
            # تحليل الصورة باستخدام Gemini
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_content
                }
            ]
            
            prompt_parts = [
                "هذه صورة لسؤال تعليمي. اقرأ السؤال وأجب عليه حسب المنهج العراقي:",
                image_parts[0],
                "قدم إجابة علمية مفصلة ومنظمة."
            ]
        else:
            prompt_parts = [
                f"أجب على السؤال التالي حسب المنهج العراقي:\n\n{question_text}\n\n"
                "قدم إجابة علمية مفصلة ومنظمة مع أمثلة إذا لزم الأمر."
            ]
        
        response = model.generate_content(prompt_parts)
        return response.text
    
    except Exception as e:
        print(f"AI question answering error: {e}")
        return "❌ حدث خطأ في معالجة السؤال. يرجى المحاولة مرة أخرى."

async def handle_service_4(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """ساعدوني طالب"""
    service = db.get_services()[3]
    service_price = service[2]
    
    if not await check_balance(user_id, service_price, context):
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text="🙋‍♂️ *ساعدوني طالب*\n\n"
             "أرسل سؤالك وسيتم عرضه على الطلاب الآخرين للإجابة.\n\n"
             "سيحصل المجيب على مكافأة 100 دينار!\n\n"
             "أدخل المادة أولاً:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_states[user_id] = 'waiting_for_subject'
    pending_questions[user_id] = {'stage': 'subject'}

async def handle_service_5(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """الملازم والمرشحات"""
    service = db.get_services()[4]
    service_price = service[2]
    
    if not await check_balance(user_id, service_price, context):
        return
    
    # عرض المواد المتاحة
    materials = db.get_materials()
    
    if not materials:
        await context.bot.send_message(
            chat_id=user_id,
            text="📚 *الملازم والمرشحات*\n\n"
                 "لا توجد مواد متاحة حالياً.\n"
                 "سيتم إضافة مواد جديدة قريباً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    keyboard = []
    for material in materials[:10]:  # عرض أول 10 مواد
        keyboard.append([
            InlineKeyboardButton(
                f"{material[1]} - {material[3]}",
                callback_data=f"material_{material[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text="📚 *الملازم والمرشحات*\n\n"
             "اختر المادة التي تريدها:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_vip_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """محاضرات VIP"""
    service = db.get_services()[5]
    service_price = service[2]
    
    # عرض محاضرات VIP
    lectures = db.get_vip_lectures(status='approved')
    
    if not lectures:
        await context.bot.send_message(
            chat_id=user_id,
            text="🎥 *محاضرات VIP*\n\n"
                 "لا توجد محاضرات متاحة حالياً.\n\n"
                 "هل أنت معلم وتريد إضافة محاضرات؟\n"
                 "اشترك في باقة المعلمين!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # التحقق من الرصيد إذا كان المستخدم ليس معلم
    user = db.get_user(user_id)
    if not user[12]:  # ليس معلم
        if not await check_balance(user_id, service_price, context):
            return
    
    keyboard = []
    for lecture in lectures[:10]:
        price_text = format_currency(lecture[5])
        keyboard.append([
            InlineKeyboardButton(
                f"{lecture[2]} - {price_text}",
                callback_data=f"lecture_{lecture[0]}"
            )
        ])
    
    # إضافة خيار الاشتراك كمعلم
    keyboard.append([
        InlineKeyboardButton("👨‍🏫 اشترك كمعلم", callback_data="become_teacher")
    ])
    
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text="🎥 *محاضرات VIP*\n\n"
             "اختر المحاضرة التي تريدها:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== لوحة التحكم الإدارية ==========
def create_admin_panel():
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("💰 الشحن والخصم", callback_data="admin_finance")],
        [InlineKeyboardButton("⚙️ إدارة الخدمات", callback_data="admin_services")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 البث للمستخدمين", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎓 إدارة المواد", callback_data="admin_materials")],
        [InlineKeyboardButton("👨‍🏫 إدارة المعلمين", callback_data="admin_teachers")],
        [InlineKeyboardButton("❓ الأسئلة المعلقة", callback_data="admin_questions")],
        [InlineKeyboardButton("🔧 إعدادات النظام", callback_data="admin_settings")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    await query.edit_message_text(
        "👑 *لوحة التحكم الإدارية*\n\n"
        "اختر القسم الذي تريد إدارته:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_admin_panel()
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    
    # عرض خيارات إدارة المستخدمين
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user")],
        [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="admin_list_users")],
        [InlineKeyboardButton("🚫 حظر/فك حظر", callback_data="admin_ban_user")],
        [InlineKeyboardButton("👑 رفع/تنزيل مشرف", callback_data="admin_toggle_admin")],
        [InlineKeyboardButton("◀️ رجوع", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        "👥 *إدارة المستخدمين*\n\n"
        "اختر الإجراء الذي تريد تنفيذه:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")],
        [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct")],
        [InlineKeyboardButton("📊 المعاملات المالية", callback_data="admin_transactions")],
        [InlineKeyboardButton("👨‍🏫 سحب أرباح المعلمين", callback_data="admin_withdraw_teacher")],
        [InlineKeyboardButton("◀️ رجوع", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        "💰 *الإدارة المالية*\n\n"
        "اختر الإجراء المالي:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    
    services = db.get_services()
    
    keyboard = []
    for service in services:
        status = "🟢" if service[3] else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {service[1]} - {format_currency(service[2])}",
                callback_data=f"admin_service_{service[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ تغيير سعر خدمة", callback_data="admin_change_price")])
    keyboard.append([InlineKeyboardButton("◀️ رجوع", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "⚙️ *إدارة الخدمات*\n\n"
        "الخدمات:\n"
        "🟢 = مفعلة | 🔴 = معطلة\n\n"
        "اضغط على الخدمة لتفعيل/تعطيل:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    
    stats = db.get_user_stats()
    
    stats_text = f"""
    📊 *إحصائيات البوت*

    *إجمالي المستخدمين:* {stats['total_users']}
    *المستخدمين اليوم:* {stats['today_users']}
    *المستخدمين VIP:* {stats['vip_users']}
    *إجمالي الأرصدة:* {format_currency(stats['total_balance'])}

    *الخدمات:*
    """
    
    services = db.get_services()
    for service in services:
        status = "مفعلة" if service[3] else "معطلة"
        stats_text += f"\n• {service[1]}: {format_currency(service[2])} ({status})"
    
    keyboard = [[InlineKeyboardButton("◀️ رجوع", callback_data="admin_panel")]]
    
    await query.edit_message_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        "📢 *البث للمستخدمين*\n\n"
        "أرسل الرسالة التي تريد بثها لجميع المستخدمين:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    user_states[user_id] = 'waiting_for_broadcast'

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message_text):
    """إرسال رسالة لجميع المستخدمين"""
    cursor = db.conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=f"📢 *إشعار من الإدارة*\n\n{message_text}",
                parse_mode=ParseMode.MARKDOWN
            )
            success += 1
        except Exception as e:
            failed += 1
        
        await asyncio.sleep(0.1)  # تجنب حظر التلجرام
    
    return success, failed

# ========== معالجة الردود ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    # التحقق من الحظر
    user = db.get_user(user_id)
    if user and user[8] == 1:  # العمود 8 هو is_banned
        await message.reply_text("❌ لقد تم حظرك من استخدام البوت!")
        return
    
    # التحقق من الصيانة
    if db.get_setting('maintenance') == '1' and user_id != ADMIN_ID:
        await message.reply_text("🔧 البوت تحت الصيانة، يرجى المحاولة لاحقاً.")
        return
    
    # معالجة حالة المستخدم
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == 'waiting_for_grades':
            grades_str = message.text
            result = await calculate_exemption(grades_str)
            
            # خصم المبلغ
            service = db.get_services()[0]
            await deduct_balance(user_id, service[2], service[1])
            
            await message.reply_text(
                result,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_main_menu(user_id)
            )
            del user_states[user_id]
        
        elif state == 'waiting_for_pdf':
            if message.document and message.document.mime_type == 'application/pdf':
                await message.reply_text("📥 جاري معالجة الملف...")
                
                # خصم المبلغ
                service = db.get_services()[1]
                await deduct_balance(user_id, service[2], service[1])
                
                file_id = message.document.file_id
                file = await context.bot.get_file(file_id)
                file_url = file.file_path
                
                summary_pdf, result_message = await summarize_pdf(file_url)
                
                if summary_pdf:
                    await message.reply_document(
                        document=InputFile(summary_pdf, filename="ملخص_الملازم.pdf"),
                        caption="✅ تم تلخيص الملف بنجاح!"
                    )
                else:
                    await message.reply_text(result_message)
                
                del user_states[user_id]
            else:
                await message.reply_text("❌ يرجى إرسال ملف PDF فقط!")
        
        elif state == 'waiting_for_question':
            question_text = message.text
            
            if message.photo:
                # معالجة الصورة
                photo = message.photo[-1]
                file_id = photo.file_id
                file = await context.bot.get_file(file_id)
                file_url = file.file_path
                
                answer = await answer_question_with_ai(question_text, True, file_url)
            else:
                answer = await answer_question_with_ai(question_text)
            
            # خصم المبلغ
            service = db.get_services()[2]
            await deduct_balance(user_id, service[2], service[1])
            
            await message.reply_text(
                f"🤖 *الإجابة:*\n\n{answer}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_main_menu(user_id)
            )
            del user_states[user_id]
        
        elif state == 'waiting_for_broadcast' and user_id == ADMIN_ID:
            message_text = message.text
            await message.reply_text("📤 جاري إرسال الرسالة لجميع المستخدمين...")
            
            success, failed = await broadcast_message(context, message_text)
            
            await message.reply_text(
                f"✅ تم إرسال الرسالة بنجاح!\n\n"
                f"✅ تم الإرسال لـ: {success} مستخدم\n"
                f"❌ فشل الإرسال لـ: {failed} مستخدم",
                reply_markup=create_admin_panel()
            )
            del user_states[user_id]
        
        elif state == 'waiting_for_user_id':
            # معالجة شحن أو خصم رصيد
            try:
                target_user_id = int(message.text)
                pending_payments[user_id] = {'target_id': target_user_id}
                
                await message.reply_text(
                    f"👤 تم تحديد المستخدم: {target_user_id}\n\n"
                    f"أرسل المبلغ (رقم فقط):"
                )
                
                if 'action' in user_states:
                    if user_states[user_id + '_action'] == 'charge':
                        user_states[user_id] = 'waiting_for_amount_charge'
                    elif user_states[user_id + '_action'] == 'deduct':
                        user_states[user_id] = 'waiting_for_amount_deduct'
            
            except ValueError:
                await message.reply_text("❌ يرجى إرسال رقم ID صحيح!")
        
        elif state == 'waiting_for_amount_charge':
            try:
                amount = int(message.text)
                target_user_id = pending_payments[user_id]['target_id']
                
                # شحن الرصيد
                db.update_balance(target_user_id, amount, 'admin_charge', 'شحن من الإدارة')
                
                # إرسال إشعار للمستخدم
                await send_notification(
                    target_user_id,
                    f"💰 تم شحن رصيدك بمبلغ {format_currency(amount)} من الإدارة",
                    context
                )
                
                await message.reply_text(
                    f"✅ تم شحن {format_currency(amount)} للمستخدم {target_user_id}",
                    reply_markup=create_admin_panel()
                )
                
                del user_states[user_id]
                del pending_payments[user_id]
                if user_id + '_action' in user_states:
                    del user_states[user_id + '_action']
            
            except ValueError:
                await message.reply_text("❌ يرجى إرسال مبلغ صحيح!")
        
        elif state == 'waiting_for_amount_deduct':
            try:
                amount = int(message.text)
                target_user_id = pending_payments[user_id]['target_id']
                
                # التحقق من رصيد المستخدم
                target_user = db.get_user(target_user_id)
                if target_user and target_user[5] >= amount:
                    # خصم الرصيد
                    db.update_balance(target_user_id, -amount, 'admin_deduct', 'خصم من الإدارة')
                    
                    # إرسال إشعار للمستخدم
                    await send_notification(
                        target_user_id,
                        f"💸 تم خصم {format_currency(amount)} من رصيدك من قبل الإدارة",
                        context
                    )
                    
                    await message.reply_text(
                        f"✅ تم خصم {format_currency(amount)} من المستخدم {target_user_id}",
                        reply_markup=create_admin_panel()
                    )
                else:
                    await message.reply_text("❌ رصيد المستخدم غير كافي!")
                
                del user_states[user_id]
                del pending_payments[user_id]
                if user_id + '_action' in user_states:
                    del user_states[user_id + '_action']
            
            except ValueError:
                await message.reply_text("❌ يرجى إرسال مبلغ صحيح!")
        
        elif state == 'waiting_for_ban_user':
            try:
                target_user_id = int(message.text)
                target_user = db.get_user(target_user_id)
                
                if target_user:
                    # تبديل حالة الحظر
                    new_status = 0 if target_user[8] == 1 else 1
                    cursor = db.conn.cursor()
                    cursor.execute(
                        "UPDATE users SET is_banned = ? WHERE user_id = ?",
                        (new_status, target_user_id)
                    )
                    db.conn.commit()
                    
                    action = "حظر" if new_status == 1 else "فك حظر"
                    
                    # إرسال إشعار للمستخدم
                    if new_status == 1:
                        await send_notification(
                            target_user_id,
                            "🚫 تم حظرك من استخدام البوت من قبل الإدارة",
                            context
                        )
                    else:
                        await send_notification(
                            target_user_id,
                            "✅ تم فك حظرك من قبل الإدارة",
                            context
                        )
                    
                    await message.reply_text(
                        f"✅ تم {action} المستخدم {target_user_id}",
                        reply_markup=create_admin_panel()
                    )
                else:
                    await message.reply_text("❌ المستخدم غير موجود!")
                
                del user_states[user_id]
            
            except ValueError:
                await message.reply_text("❌ يرجى إرسال رقم ID صحيح!")
        
        elif state == 'waiting_for_service_price':
            try:
                service_id = pending_payments.get(user_id, {}).get('service_id')
                new_price = int(message.text)
                
                if service_id:
                    db.update_service_price(service_id, new_price)
                    
                    await message.reply_text(
                        f"✅ تم تحديث سعر الخدمة إلى {format_currency(new_price)}",
                        reply_markup=create_admin_panel()
                    )
                
                del user_states[user_id]
                if user_id in pending_payments:
                    del pending_payments[user_id]
            
            except ValueError:
                await message.reply_text("❌ يرجى إرسال سعر صحيح!")
        
        elif state == 'waiting_for_material_name':
            # إضافة مادة جديدة
            material_name = message.text
            pending_payments[user_id] = {'material_name': material_name}
            user_states[user_id] = 'waiting_for_material_stage'
            
            await message.reply_text("📝 أدخل المرحلة الدراسية:")
        
        elif state == 'waiting_for_material_stage':
            material_stage = message.text
            pending_payments[user_id]['material_stage'] = material_stage
            user_states[user_id] = 'waiting_for_material_description'
            
            await message.reply_text("📝 أدخل وصف المادة:")
        
        elif state == 'waiting_for_material_description':
            material_description = message.text
            pending_payments[user_id]['material_description'] = material_description
            user_states[user_id] = 'waiting_for_material_file'
            
            await message.reply_text("📎 أرسل ملف PDF للمادة:")
        
        elif state == 'waiting_for_material_file':
            if message.document and message.document.mime_type == 'application/pdf':
                file_id = message.document.file_id
                
                # حفظ المادة
                material_data = pending_payments[user_id]
                db.add_material(
                    material_data['material_name'],
                    material_data['material_description'],
                    material_data['material_stage'],
                    file_id
                )
                
                await message.reply_text(
                    "✅ تم إضافة المادة بنجاح!",
                    reply_markup=create_admin_panel()
                )
                
                del user_states[user_id]
                del pending_payments[user_id]
            else:
                await message.reply_text("❌ يرجى إرسال ملف PDF فقط!")
    
    else:
        # إذا لم يكن المستخدم في حالة خاصة
        if message.text:
            if message.text.startswith('/'):
                await update.message.reply_text(
                    "استخدم الأزرار للتنقل بين الخدمات!",
                    reply_markup=create_main_menu(user_id)
                )
            else:
                await update.message.reply_text(
                    "مرحباً! اختر خدمة من القائمة:",
                    reply_markup=create_main_menu(user_id)
                )

# ========== معالجة Callback Query ==========
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'main_menu':
        await query.edit_message_text(
            "🏠 *القائمة الرئيسية*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_menu(user_id)
        )
    
    elif data == 'balance':
        user = db.get_user(user_id)
        if user:
            await query.edit_message_text(
                f"💰 *رصيدك الحالي:* {format_currency(user[5])}\n\n"
                f"*النقاط:* {user[6]}\n\n"
                f"للشحن تواصل مع الدعم الفني: @{SUPPORT_USERNAME.replace('@', '')}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ])
            )
    
    elif data == 'invite':
        invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_id}"
        reward = db.get_setting('invite_reward', 500)
        
        await query.edit_message_text(
            f"👥 *دعوة الأصدقاء*\n\n"
            f"رابط دعوتك:\n`{invite_link}`\n\n"
            f"*مكافأة الدعوة:*\n"
            f"• أنت تحصل على {format_currency(int(reward))} لكل صديق\n"
            f"• صديقك يحصل على {format_currency(1000)} ترحيبية\n\n"
            f"انسخ الرابط وشاركه مع أصدقائك!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={invite_link}&text=انضم%20لبوت%20يلا%20نتعلم%20للخدمات%20التعليمية")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
            ])
        )
    
    elif data == 'admin_panel':
        if user_id == ADMIN_ID:
            await admin_panel(update, context)
        else:
            await query.edit_message_text("❌ ليس لديك صلاحية الوصول!")
    
    elif data.startswith('service_'):
        service_id = int(data.split('_')[1])
        services = db.get_services()
        service = next((s for s in services if s[0] == service_id), None)
        
        if service:
            if service[3]:  # إذا كانت الخدمة مفعلة
                if service_id == 1:
                    await handle_service_1(update, context, user_id)
                elif service_id == 2:
                    await handle_service_2(update, context, user_id)
                elif service_id == 3:
                    await handle_service_3(update, context, user_id)
                elif service_id == 4:
                    await handle_service_4(update, context, user_id)
                elif service_id == 5:
                    await handle_service_5(update, context, user_id)
                elif service_id == 6:
                    await handle_vip_lectures(update, context, user_id)
            else:
                await query.answer("❌ هذه الخدمة معطلة حالياً!", show_alert=True)
    
    elif data == 'admin_users':
        await admin_users(update, context)
    
    elif data == 'admin_finance':
        await admin_finance(update, context)
    
    elif data == 'admin_services':
        await admin_services(update, context)
    
    elif data == 'admin_stats':
        await admin_stats(update, context)
    
    elif data == 'admin_broadcast':
        await admin_broadcast(update, context)
    
    elif data == 'admin_charge':
        if user_id == ADMIN_ID:
            await query.edit_message_text(
                "💰 *شحن رصيد*\n\n"
                "أرسل ID المستخدم الذي تريد شحن رصيده:",
                parse_mode=ParseMode.MARKDOWN
            )
            user_states[user_id] = 'waiting_for_user_id'
            user_states[user_id + '_action'] = 'charge'
    
    elif data == 'admin_deduct':
        if user_id == ADMIN_ID:
            await query.edit_message_text(
                "💸 *خصم رصيد*\n\n"
                "أرسل ID المستخدم الذي تريد خصم رصيده:",
                parse_mode=ParseMode.MARKDOWN
            )
            user_states[user_id] = 'waiting_for_user_id'
            user_states[user_id + '_action'] = 'deduct'
    
    elif data == 'admin_ban_user':
        if user_id == ADMIN_ID:
            await query.edit_message_text(
                "🚫 *حظر/فك حظر مستخدم*\n\n"
                "أرسل ID المستخدم:",
                parse_mode=ParseMode.MARKDOWN
            )
            user_states[user_id] = 'waiting_for_ban_user'
    
    elif data.startswith('admin_service_'):
        service_id = int(data.split('_')[2])
        
        # تبديل حالة الخدمة
        cursor = db.conn.cursor()
        cursor.execute("SELECT is_active FROM services WHERE id = ?", (service_id,))
        current_status = cursor.fetchone()[0]
        
        new_status = 0 if current_status == 1 else 1
        db.toggle_service(service_id, new_status)
        
        status_text = "مفعلة" if new_status == 1 else "معطلة"
        await query.answer(f"✅ تم {status_text} الخدمة", show_alert=True)
        await admin_services(update, context)
    
    elif data == 'admin_change_price':
        if user_id == ADMIN_ID:
            services = db.get_services()
            
            keyboard = []
            for service in services:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{service[1]} - {format_currency(service[2])}",
                        callback_data=f"change_price_{service[0]}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("◀️ رجوع", callback_data="admin_services")])
            
            await query.edit_message_text(
                "💰 *تغيير سعر خدمة*\n\n"
                "اختر الخدمة التي تريد تغيير سعرها:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data.startswith('change_price_'):
        service_id = int(data.split('_')[2])
        pending_payments[user_id] = {'service_id': service_id}
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT name, price FROM services WHERE id = ?", (service_id,))
        service = cursor.fetchone()
        
        await query.edit_message_text(
            f"💰 *تغيير سعر خدمة*\n\n"
            f"الخدمة: {service[0]}\n"
            f"السعر الحالي: {format_currency(service[1])}\n\n"
            f"أرسل السعر الجديد (رقم فقط):",
            parse_mode=ParseMode.MARKDOWN
        )
        user_states[user_id] = 'waiting_for_service_price'
    
    elif data == 'admin_materials':
        if user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("➕ إضافة مادة جديدة", callback_data="add_material")],
                [InlineKeyboardButton("🗑️ حذف مادة", callback_data="delete_material")],
                [InlineKeyboardButton("📋 عرض المواد", callback_data="list_materials")],
                [InlineKeyboardButton("◀️ رجوع", callback_data="admin_panel")]
            ]
            
            await query.edit_message_text(
                "📚 *إدارة المواد التعليمية*\n\n"
                "اختر الإجراء الذي تريد تنفيذه:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data == 'add_material':
        if user_id == ADMIN_ID:
            await query.edit_message_text(
                "📝 *إضافة مادة جديدة*\n\n"
                "أرسل اسم المادة:",
                parse_mode=ParseMode.MARKDOWN
            )
            user_states[user_id] = 'waiting_for_material_name'
    
    # معالجة باقي Callback Queries
    elif data == 'vip_lectures':
        await handle_vip_lectures(update, context, user_id)
    
    elif data == 'become_teacher':
        teacher_price = int(db.get_setting('teacher_subscription_price', 5000))
        
        keyboard = [
            [InlineKeyboardButton(f"اشترك الآن ({format_currency(teacher_price)})", callback_data="purchase_teacher")],
            [InlineKeyboardButton("◀️ رجوع", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            f"👨‍🏫 *اشترك كمعلم*\n\n"
            f"*مزايا الاشتراك:*\n"
            f"• إضافة محاضرات VIP\n"
            f"• تحصيل 60% من أرباح المحاضرات\n"
            f"• لوحة تحكم خاصة\n"
            f"• سحب الأرباح عند وصولها لـ 15,000 دينار\n\n"
            f"*سعر الاشتراك الشهري:* {format_currency(teacher_price)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    else:
        await query.edit_message_text(
            "✅ تم تنفيذ الأمر بنجاح!",
            reply_markup=create_main_menu(user_id)
        )

# ========== الدالة الرئيسية ==========
def main():
    # إنشاء تطبيق البوت
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # إضافة معالجات Callback Query
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # إضافة معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    # بدء البوت
    print("🤖 بدأ تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
