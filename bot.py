#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - النسخة النهائية المتكاملة
المطور: Allawi04@
ID المطور: 6130994941
قناة البوت: https://t.me/FCJCV
"""

import asyncio
import logging
import sqlite3
import json
import os
import re
import tempfile
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import html

import fitz  # PyMuPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    InputFile, Message, User
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from telegram.constants import ParseMode
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
model = genai.GenerativeModel('gemini-2.0-flash')

# ============== حالات المحادثة ==============
GRADE_1, GRADE_2, GRADE_3 = range(3)
UPLOAD_MATERIAL_NAME, UPLOAD_MATERIAL_DESC, UPLOAD_MATERIAL_STAGE, UPLOAD_MATERIAL_FILE = range(3, 7)
QUESTION_TEXT, QUESTION_SUBJECT = range(7, 9)
ADMIN_CHARGE_USER, ADMIN_CHARGE_AMOUNT = range(9, 11)
ADMIN_DEDUCT_USER, ADMIN_DEDUCT_AMOUNT = range(11, 13)
ADMIN_BAN_USER, ADMIN_UNBAN_USER = range(13, 15)
ADMIN_SERVICE_PRICE = range(15, 16)
ADMIN_BROADCAST = range(16, 17)
VIP_LECTURE_TITLE, VIP_LECTURE_DESC, VIP_LECTURE_PRICE, VIP_LECTURE_FILE = range(17, 21)
VIP_SUBSCRIBE = range(21, 22)
WITHDRAW_REQUEST = range(22, 23)
ANSWER_QUESTION = range(23, 24)

# ============== إعداد قواعد البيانات ==============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('yalla_nt3lm_v2.db', check_same_thread=False)
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
                balance INTEGER DEFAULT 0,
                vip_balance INTEGER DEFAULT 0,
                invite_code TEXT UNIQUE,
                invited_by INTEGER DEFAULT 0,
                invited_count INTEGER DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_expiry TIMESTAMP,
                vip_purchase_date TIMESTAMP
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
                display_name TEXT,
                price INTEGER DEFAULT 1000,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # جدول الأسئلة
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                subject TEXT,
                status TEXT DEFAULT 'pending',
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answer TEXT,
                answered_by INTEGER,
                answer_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (answered_by) REFERENCES users (user_id)
            )
        ''')
        
        # جدول المواد الدراسية
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                stage TEXT,
                file_id TEXT,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                price INTEGER DEFAULT 0,
                approved INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (teacher_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول مشتريات VIP
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                expiry_date TIMESTAMP,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول مشتريات المحاضرات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecture_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lecture_id INTEGER,
                amount INTEGER,
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
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users (user_id),
                FOREIGN KEY (lecture_id) REFERENCES vip_lectures (id)
            )
        ''')
        
        # جدول إعدادات البوت
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # إدخال الخدمات الأساسية
        services = [
            ('exemption', 'حساب درجة الإعفاء', 1000),
            ('pdf_summary', 'تلخيص الملازم', 1000),
            ('qna', 'سؤال وجواب', 1000),
            ('help_student', 'ساعدوني طالب', 1000)
        ]
        
        for service_id, display_name, price in services:
            self.cursor.execute('''
                INSERT OR IGNORE INTO services (name, display_name, price)
                VALUES (?, ?, ?)
            ''', (service_id, display_name, price))
        
        # إدخال الإعدادات الأساسية
        settings = [
            ('invite_bonus', '1000'),
            ('welcome_bonus', '1000'),
            ('vip_price', '20000'),
            ('teacher_percentage', '60'),
            ('admin_percentage', '40'),
            ('min_withdrawal', '15000'),
            ('support_username', DEVELOPER_USERNAME),
            ('channel_link', CHANNEL_LINK),
            ('maintenance', '0')
        ]
        
        for key, value in settings:
            self.cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
        
        # إضافة المستخدم المطور
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, balance, is_admin, is_vip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (DEVELOPER_ID, DEVELOPER_USERNAME, 'المطور', 1000000, 1, 1))
        
        self.conn.commit()
    
    # ============== وظائف المستخدمين ==============
    def get_user(self, user_id: int) -> Dict:
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        cols = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        return dict(zip(cols, row)) if row else None
    
    def create_user(self, user: User, invited_by: int = None):
        invite_code = str(uuid.uuid4())[:8]
        welcome_bonus = int(self.get_setting('welcome_bonus'))
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, invite_code, invited_by, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, user.last_name, 
              invite_code, invited_by, welcome_bonus if not invited_by else 0))
        
        if invited_by:
            # منح مكافأة للمدعو
            self.add_transaction(user.id, welcome_bonus, 'invite_bonus', 'مكافأة دعوة')
            # تحديث عدد دعوات المدعي
            self.cursor.execute('''
                UPDATE users SET invited_count = invited_count + 1 
                WHERE user_id = ?
            ''', (invited_by,))
            # منح مكافأة للمدعي
            self.add_transaction(invited_by, 500, 'invite_reward', 'مكافأة لدعوة مستخدم جديد')
        
        self.conn.commit()
        return self.get_user(user.id)
    
    def update_balance(self, user_id: int, amount: int):
        self.cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', 
                          (amount, user_id))
        self.conn.commit()
    
    def update_vip_balance(self, user_id: int, amount: int):
        self.cursor.execute('UPDATE users SET vip_balance = vip_balance + ? WHERE user_id = ?', 
                          (amount, user_id))
        self.conn.commit()
    
    def add_transaction(self, user_id: int, amount: int, trans_type: str, description: str):
        self.cursor.execute('''
            INSERT INTO transactions (user_id, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, trans_type, description))
        self.conn.commit()
    
    # ============== وظائف الإعدادات ==============
    def get_setting(self, key: str) -> str:
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def update_setting(self, key: str, value: str):
        self.cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        self.conn.commit()
    
    # ============== وظائف الخدمات ==============
    def get_services(self):
        self.cursor.execute('SELECT * FROM services ORDER BY id')
        return self.cursor.fetchall()
    
    def get_service(self, service_name: str):
        self.cursor.execute('SELECT * FROM services WHERE name = ?', (service_name,))
        cols = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        return dict(zip(cols, row)) if row else None
    
    def update_service_price(self, service_name: str, price: int):
        self.cursor.execute('UPDATE services SET price = ? WHERE name = ?', (price, service_name))
        self.conn.commit()
    
    def toggle_service(self, service_name: str, status: int):
        self.cursor.execute('UPDATE services SET is_active = ? WHERE name = ?', (status, service_name))
        self.conn.commit()
    
    # ============== وظائف الأسئلة ==============
    def add_question(self, user_id: int, question: str, subject: str = ''):
        self.cursor.execute('''
            INSERT INTO questions (user_id, question, subject)
            VALUES (?, ?, ?)
        ''', (user_id, question, subject))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_questions(self):
        self.cursor.execute('''
            SELECT q.*, u.username, u.first_name 
            FROM questions q
            JOIN users u ON q.user_id = u.user_id
            WHERE q.status = 'pending'
            ORDER BY q.date DESC
        ''')
        return self.cursor.fetchall()
    
    def get_answered_questions(self):
        self.cursor.execute('''
            SELECT q.*, u.username as asker_username, 
                   u2.username as answerer_username
            FROM questions q
            JOIN users u ON q.user_id = u.user_id
            LEFT JOIN users u2 ON q.answered_by = u2.user_id
            WHERE q.status = 'answered'
            ORDER BY q.answer_date DESC
            LIMIT 20
        ''')
        return self.cursor.fetchall()
    
    def approve_question(self, question_id: int):
        self.cursor.execute('UPDATE questions SET status = "approved" WHERE id = ?', (question_id,))
        self.conn.commit()
    
    def reject_question(self, question_id: int):
        self.cursor.execute('UPDATE questions SET status = "rejected" WHERE id = ?', (question_id,))
        self.conn.commit()
    
    def delete_question(self, question_id: int):
        self.cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        self.conn.commit()
    
    def answer_question(self, question_id: int, answer: str, answered_by: int):
        self.cursor.execute('''
            UPDATE questions 
            SET answer = ?, answered_by = ?, answer_date = CURRENT_TIMESTAMP, status = 'answered'
            WHERE id = ?
        ''', (answer, answered_by, question_id))
        self.conn.commit()
    
    # ============== وظائف المواد الدراسية ==============
    def add_material(self, name: str, description: str, stage: str, file_id: str, added_by: int):
        self.cursor.execute('''
            INSERT INTO materials (name, description, stage, file_id, added_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, stage, file_id, added_by))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_materials(self, stage: str = None):
        if stage:
            self.cursor.execute('SELECT * FROM materials WHERE stage = ? ORDER BY added_date DESC', (stage,))
        else:
            self.cursor.execute('SELECT * FROM materials ORDER BY added_date DESC')
        return self.cursor.fetchall()
    
    def delete_material(self, material_id: int):
        self.cursor.execute('DELETE FROM materials WHERE id = ?', (material_id,))
        self.conn.commit()
    
    # ============== وظائف VIP ==============
    def subscribe_vip(self, user_id: int, amount: int):
        expiry_date = datetime.now() + timedelta(days=30)
        self.cursor.execute('''
            INSERT INTO vip_subscriptions (user_id, amount, expiry_date)
            VALUES (?, ?, ?)
        ''', (user_id, amount, expiry_date))
        
        self.cursor.execute('''
            UPDATE users SET is_vip = 1, vip_expiry = ?, vip_purchase_date = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (expiry_date, user_id))
        
        self.conn.commit()
    
    def get_vip_subscriptions(self):
        self.cursor.execute('''
            SELECT vs.*, u.username, u.first_name 
            FROM vip_subscriptions vs
            JOIN users u ON vs.user_id = u.user_id
            WHERE vs.status = 'active'
            ORDER BY vs.purchase_date DESC
        ''')
        return self.cursor.fetchall()
    
    def cancel_vip_subscription(self, user_id: int):
        self.cursor.execute('UPDATE vip_subscriptions SET status = "cancelled" WHERE user_id = ?', (user_id,))
        self.cursor.execute('UPDATE users SET is_vip = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def extend_vip_subscription(self, user_id: int, days: int):
        self.cursor.execute('''
            UPDATE users 
            SET vip_expiry = datetime(vip_expiry, ?) 
            WHERE user_id = ?
        ''', (f'+{days} days', user_id))
        self.conn.commit()
    
    def add_vip_lecture(self, teacher_id: int, title: str, description: str, file_id: str, price: int):
        self.cursor.execute('''
            INSERT INTO vip_lectures (teacher_id, title, description, file_id, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (teacher_id, title, description, file_id, price))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_vip_lectures(self, approved: bool = True, teacher_id: int = None):
        if teacher_id:
            self.cursor.execute('''
                SELECT * FROM vip_lectures 
                WHERE teacher_id = ? AND approved = ? AND is_active = 1
                ORDER BY added_date DESC
            ''', (teacher_id, 1 if approved else 0))
        else:
            self.cursor.execute('''
                SELECT * FROM vip_lectures 
                WHERE approved = ? AND is_active = 1
                ORDER BY added_date DESC
            ''', (1 if approved else 0,))
        return self.cursor.fetchall()
    
    def get_vip_lecture(self, lecture_id: int):
        self.cursor.execute('SELECT * FROM vip_lectures WHERE id = ?', (lecture_id,))
        cols = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        return dict(zip(cols, row)) if row else None
    
    def approve_vip_lecture(self, lecture_id: int):
        self.cursor.execute('UPDATE vip_lectures SET approved = 1 WHERE id = ?', (lecture_id,))
        self.conn.commit()
    
    def reject_vip_lecture(self, lecture_id: int):
        self.cursor.execute('DELETE FROM vip_lectures WHERE id = ?', (lecture_id,))
        self.conn.commit()
    
    def delete_vip_lecture(self, lecture_id: int):
        self.cursor.execute('DELETE FROM vip_lectures WHERE id = ?', (lecture_id,))
        self.conn.commit()
    
    def purchase_vip_lecture(self, user_id: int, lecture_id: int):
        lecture = self.get_vip_lecture(lecture_id)
        if not lecture:
            return False
        
        # تسجيل الشراء
        self.cursor.execute('''
            INSERT INTO lecture_purchases (user_id, lecture_id, amount)
            VALUES (?, ?, ?)
        ''', (user_id, lecture_id, lecture['price']))
        
        # تحديث عدد المشتريات
        self.cursor.execute('''
            UPDATE vip_lectures SET purchases = purchases + 1 WHERE id = ?
        ''', (lecture_id,))
        
        # حساب أرباح المعلم
        teacher_percentage = int(self.get_setting('teacher_percentage'))
        teacher_earning = int(lecture['price'] * teacher_percentage / 100)
        
        # إضافة أرباح المعلم
        self.cursor.execute('''
            INSERT INTO teacher_earnings (teacher_id, lecture_id, amount)
            VALUES (?, ?, ?)
        ''', (lecture['teacher_id'], lecture_id, teacher_earning))
        
        # إضافة إلى رصيد المعلم
        self.update_vip_balance(lecture['teacher_id'], teacher_earning)
        
        self.conn.commit()
        return True
    
    def get_teacher_earnings(self, teacher_id: int):
        self.cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM teacher_earnings WHERE teacher_id = ?', (teacher_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def withdraw_earnings(self, teacher_id: int, amount: int):
        user = self.get_user(teacher_id)
        if not user or user['vip_balance'] < amount:
            return False
        
        self.update_vip_balance(teacher_id, -amount)
        self.add_transaction(teacher_id, amount, 'withdrawal', 'سحب أرباح VIP')
        return True
    
    # ============== وظائف الإدارة ==============
    def get_all_users(self):
        self.cursor.execute('SELECT * FROM users ORDER BY joined_date DESC')
        return self.cursor.fetchall()
    
    def ban_user(self, user_id: int):
        self.cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id: int):
        self.cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def make_admin(self, user_id: int):
        self.cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()

# ============== تهيئة قاعدة البيانات ==============
db = Database()

# ============== وظائف مساعدة ==============
def format_arabic(text: str) -> str:
    """تهيئة النص العربي"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except:
        return text

def format_number(num: int) -> str:
    """تنسيق الأرقام"""
    return f"{num:,}"

async def send_message(user_id: int, text: str, context: ContextTypes.DEFAULT_TYPE, 
                      reply_markup=None, parse_mode=ParseMode.HTML):
    """إرسال رسالة"""
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except:
        return False

async def is_admin(user_id: int) -> bool:
    """التحقق من صلاحية الأدمن"""
    if user_id == DEVELOPER_ID:
        return True
    
    user = db.get_user(user_id)
    return user and user.get('is_admin') == 1

async def has_sufficient_balance(user_id: int, amount: int) -> bool:
    """التحقق من كفاية الرصيد"""
    user = db.get_user(user_id)
    return user and user['balance'] >= amount

async def deduct_after_service(user_id: int, service_name: str, context: ContextTypes.DEFAULT_TYPE):
    """خصم المبلغ بعد الخدمة"""
    service = db.get_service(service_name)
    if not service:
        return False
    
    amount = service['price']
    user = db.get_user(user_id)
    
    if user['balance'] >= amount:
        db.update_balance(user_id, -amount)
        db.add_transaction(user_id, -amount, 'service_payment', f'خدمة {service_name}')
        
        await send_message(user_id, 
            f"💸 <b>تم خصم المبلغ</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📝 الخدمة: {service['display_name']}\n"
            f"📊 الرصيد الجديد: {format_number(user['balance'] - amount)} دينار",
            context
        )
        return True
    return False

# ============== الواجهة الرئيسية ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت"""
    user = update.effective_user
    
    # التحقق من وضع الصيانة
    if db.get_setting('maintenance') == '1' and not await is_admin(user.id):
        await update.message.reply_text(
            "🔧 <b>البوت قيد الصيانة</b>\n"
            "━━━━━━━━━━━━━━\n"
            "البوت حالياً تحت الصيانة والتطوير.\n"
            "الرجاء المحاولة لاحقاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # إنشاء المستخدم إذا لم يكن موجوداً
    if not db.get_user(user.id):
        invited_by = None
        if context.args:
            invite_code = context.args[0]
            db.cursor.execute('SELECT user_id FROM users WHERE invite_code = ?', (invite_code,))
            inviter = db.cursor.fetchone()
            if inviter:
                invited_by = inviter[0]
        
        db.create_user(user, invited_by)
    
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية"""
    user = update.effective_user if update.message else update.callback_query.from_user
    user_data = db.get_user(user.id)
    
    # التحقق من الحظر
    if user_data.get('is_banned'):
        await (update.message or update.callback_query.message).reply_text(
            "🚫 <b>حسابك محظور</b>\n"
            "━━━━━━━━━━━━━━\n"
            "لا يمكنك استخدام البوت.\n"
            "للتواصل مع الدعم: @Allawi04@",
            parse_mode=ParseMode.HTML
        )
        return
    
    services = db.get_services()
    active_services = [s for s in services if s[4] == 1]  # s[4] = is_active
    
    keyboard = []
    
    # إضافة الخدمات النشطة
    for service in active_services:
        _, name, display_name, price, _ = service
        keyboard.append([InlineKeyboardButton(
            f"{display_name} - {format_number(price)} دينار",
            callback_data=f'service_{name}'
        )])
    
    # إضافة الأقسام الخاصة
    keyboard.append([InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data='materials')])
    keyboard.append([InlineKeyboardButton("👑 محاضرات VIP", callback_data='vip_lectures')])
    
    # إضافة أزرار المساعدة
    keyboard.append([
        InlineKeyboardButton("💳 رصيدي", callback_data='balance'),
        InlineKeyboardButton("👥 دعوة صديق", callback_data='invite')
    ])
    
    # إضافة زر VIP إذا كان مشتركاً
    if user_data.get('is_vip'):
        expiry = datetime.strptime(user_data['vip_expiry'], '%Y-%m-%d %H:%M:%S')
        if expiry > datetime.now():
            keyboard.insert(2, [InlineKeyboardButton("📤 رفع محاضرة VIP", callback_data='upload_vip_lecture')])
    
    # إضافة لوحة التحكم للأدمن
    if await is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"""
🎉 <b>مرحباً {user.first_name}!</b>
━━━━━━━━━━━━━━
<b>💰 رصيدك:</b> {format_number(user_data['balance'])} دينار
<b>👥 دعواتك:</b> {user_data['invited_count']}
    """
    
    if user_data.get('is_vip'):
        expiry = datetime.strptime(user_data['vip_expiry'], '%Y-%m-%d %H:%M:%S')
        days_left = (expiry - datetime.now()).days
        if days_left > 0:
            message += f"\n<b>👑 VIP:</b> مفعل ({days_left} يوم متبقي)"
        else:
            message += "\n<b>👑 VIP:</b> منتهي"
    
    message += "\n\n📚 <b>اختر الخدمة:</b>"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# ============== حساب درجة الإعفاء ==============
async def exemption_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة حساب درجة الإعفاء"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    service = db.get_service('exemption')
    
    if not await has_sufficient_balance(user_id, service['price']):
        await query.edit_message_text(
            f"❌ <b>رصيدك غير كافي</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 سعر الخدمة: {format_number(service['price'])} دينار\n"
            f"💵 رصيدك الحالي: {format_number(user_data['balance'])} دينار\n\n"
            f"الرجاء شحن رصيدك أولاً.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # حجز المبلغ مؤقتاً
    context.user_data['pending_payment'] = {
        'service': 'exemption',
        'amount': service['price'],
        'user_id': user_id
    }
    
    await query.edit_message_text(
        "🧮 <b>حساب درجة الإعفاء</b>\n"
        "━━━━━━━━━━━━━━\n"
        "<b>الخطوة 1/3:</b>\n"
        "أدخل درجة الكورس الأول (من 100):",
        parse_mode=ParseMode.HTML
    )
    
    return GRADE_1

async def handle_grade_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الأولى"""
    try:
        grade = float(update.message.text)
        if not 0 <= grade <= 100:
            await update.message.reply_text("❌ الرجاء إدخال درجة بين 0 و 100")
            return GRADE_1
        
        context.user_data['grade1'] = grade
        
        await update.message.reply_text(
            "<b>الخطوة 2/3:</b>\n"
            "أدخل درجة الكورس الثاني (من 100):",
            parse_mode=ParseMode.HTML
        )
        
        return GRADE_2
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return GRADE_1

async def handle_grade_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الثانية"""
    try:
        grade = float(update.message.text)
        if not 0 <= grade <= 100:
            await update.message.reply_text("❌ الرجاء إدخال درجة بين 0 و 100")
            return GRADE_2
        
        context.user_data['grade2'] = grade
        
        await update.message.reply_text(
            "<b>الخطوة 3/3:</b>\n"
            "أدخل درجة الكورس الثالث (من 100):",
            parse_mode=ParseMode.HTML
        )
        
        return GRADE_3
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return GRADE_2

async def handle_grade_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الثالثة"""
    try:
        grade = float(update.message.text)
        if not 0 <= grade <= 100:
            await update.message.reply_text("❌ الرجاء إدخال درجة بين 0 و 100")
            return GRADE_3
        
        context.user_data['grade3'] = grade
        
        # حساب المعدل
        grade1 = context.user_data['grade1']
        grade2 = context.user_data['grade2']
        grade3 = context.user_data['grade3']
        
        average = (grade1 + grade2 + grade3) / 3
        
        # خصم المبلغ بعد الخدمة
        if await deduct_after_service(update.message.from_user.id, 'exemption', context):
            if average >= 90:
                result = f"""
🎉 <b>مبروك! أنت معفي من المادة</b>
━━━━━━━━━━━━━━
📊 <b>الدرجات:</b>
الكورس الأول: <code>{grade1}</code>
الكورس الثاني: <code>{grade2}</code>
الكورس الثالث: <code>{grade3}</code>

📈 <b>المعدل:</b> <code>{average:.2f}</code>
✅ <b>الحالة:</b> <b>معفي</b> 🎊
                """
            else:
                result = f"""
😔 <b>أنت غير معفي من المادة</b>
━━━━━━━━━━━━━━
📊 <b>الدرجات:</b>
الكورس الأول: <code>{grade1}</code>
الكورس الثاني: <code>{grade2}</code>
الكورس الثالث: <code>{grade3}</code>

📈 <b>المعدل:</b> <code>{average:.2f}</code>
❌ <b>الحالة:</b> <b>غير معفي</b>
                """
            
            keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data='back_to_main')]]
            
            await update.message.reply_text(
                result,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        # تنظيف البيانات
        for key in ['grade1', 'grade2', 'grade3', 'pending_payment']:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return GRADE_3

# ============== إدارة المواد الدراسية ==============
async def materials_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قسم الملازم والمرشحات"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🏫 الابتدائية", callback_data='stage_primary')],
        [InlineKeyboardButton("🏫 المتوسطة", callback_data='stage_middle')],
        [InlineKeyboardButton("🏫 الإعدادية", callback_data='stage_preparatory')],
        [InlineKeyboardButton("🎓 الجامعية", callback_data='stage_university')],
    ]
    
    if await is_admin(query.from_user.id):
        keyboard.append([InlineKeyboardButton("➕ إضافة مادة", callback_data='add_material')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')])
    
    await query.edit_message_text(
        "📚 <b>ملازمي ومرشحاتي</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اختر المرحلة الدراسية:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def show_stage_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مواد مرحلة معينة"""
    query = update.callback_query
    await query.answer()
    
    stage_map = {
        'stage_primary': 'ابتدائية',
        'stage_middle': 'متوسطة', 
        'stage_preparatory': 'إعدادية',
        'stage_university': 'جامعية'
    }
    
    stage = stage_map.get(query.data)
    materials = db.get_materials(stage)
    
    if not materials:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='materials')]]
        await query.edit_message_text(
            f"📭 <b>لا توجد مواد لمرحلة {stage}</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return
    
    message = f"📚 <b>مواد مرحلة {stage}</b>\n━━━━━━━━━━━━━━\n"
    
    keyboard = []
    for mat in materials:
        message += f"\n📖 <b>{mat[1]}</b>\n{mat[2]}\n"
        keyboard.append([InlineKeyboardButton(
            f"📥 تحميل {mat[1]}",
            callback_data=f'download_{mat[0]}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='materials')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def add_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة مادة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.answer("⛔ ليس لديك صلاحية", show_alert=True)
        return
    
    await query.edit_message_text(
        "📝 <b>إضافة مادة جديدة</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل اسم المادة:",
        parse_mode=ParseMode.HTML
    )
    
    return UPLOAD_MATERIAL_NAME

async def handle_material_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اسم المادة"""
    name = update.message.text
    context.user_data['material_name'] = name
    
    await update.message.reply_text(
        "📝 أدخل وصف المادة:",
        parse_mode=ParseMode.HTML
    )
    
    return UPLOAD_MATERIAL_DESC

async def handle_material_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة وصف المادة"""
    description = update.message.text
    context.user_data['material_desc'] = description
    
    keyboard = [
        [InlineKeyboardButton("🏫 الابتدائية", callback_data='stage_primary_add')],
        [InlineKeyboardButton("🏫 المتوسطة", callback_data='stage_middle_add')],
        [InlineKeyboardButton("🏫 الإعدادية", callback_data='stage_preparatory_add')],
        [InlineKeyboardButton("🎓 الجامعية", callback_data='stage_university_add')],
    ]
    
    await update.message.reply_text(
        "📚 اختر المرحلة الدراسية:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return UPLOAD_MATERIAL_STAGE

async def handle_material_stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مرحلة المادة"""
    query = update.callback_query
    await query.answer()
    
    stage_map = {
        'stage_primary_add': 'ابتدائية',
        'stage_middle_add': 'متوسطة',
        'stage_preparatory_add': 'إعدادية',
        'stage_university_add': 'جامعية'
    }
    
    stage = stage_map.get(query.data)
    context.user_data['material_stage'] = stage
    
    await query.edit_message_text(
        "📎 أرسل ملف PDF للمادة:",
        parse_mode=ParseMode.HTML
    )
    
    return UPLOAD_MATERIAL_FILE

async def handle_material_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف المادة"""
    if not update.message.document:
        await update.message.reply_text("❌ الرجاء إرسال ملف PDF")
        return UPLOAD_MATERIAL_FILE
    
    file_id = update.message.document.file_id
    name = context.user_data['material_name']
    description = context.user_data['material_desc']
    stage = context.user_data['material_stage']
    user_id = update.message.from_user.id
    
    # حفظ المادة في قاعدة البيانات
    db.add_material(name, description, stage, file_id, user_id)
    
    await update.message.reply_text(
        f"✅ <b>تمت إضافة المادة بنجاح</b>\n"
        f"📖 {name}\n"
        f"📚 {stage}",
        parse_mode=ParseMode.HTML
    )
    
    # تنظيف البيانات
    for key in ['material_name', 'material_desc', 'material_stage']:
        context.user_data.pop(key, None)
    
    await show_main_menu(update, context)
    return ConversationHandler.END

# ============== قسم سؤال وجواب ==============
async def qna_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة سؤال وجواب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    service = db.get_service('qna')
    
    if not await has_sufficient_balance(user_id, service['price']):
        await query.edit_message_text(
            f"❌ <b>رصيدك غير كافي</b>\n"
            f"💰 سعر الخدمة: {format_number(service['price'])} دينار\n"
            f"💵 رصيدك الحالي: {format_number(user_data['balance'])} دينار",
            parse_mode=ParseMode.HTML
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("❓ طرح سؤال", callback_data='ask_question')],
        [InlineKeyboardButton("💡 الإجابة على سؤال", callback_data='answer_question_list')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        "❓ <b>سؤال وجواب</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اختر الخيار المناسب:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def ask_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء طرح سؤال"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    service = db.get_service('qna')
    
    # حجز المبلغ مؤقتاً
    context.user_data['pending_payment'] = {
        'service': 'qna',
        'amount': service['price'],
        'user_id': user_id
    }
    
    await query.edit_message_text(
        "❓ <b>طرح سؤال جديد</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اكتب سؤالك الآن:\n\n"
        "<i>ملاحظة: السؤال سيتم مراجعته قبل النشر</i>",
        parse_mode=ParseMode.HTML
    )
    
    return QUESTION_TEXT

async def handle_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص السؤال"""
    question = update.message.text
    context.user_data['question_text'] = question
    
    await update.message.reply_text(
        "📚 أدخل المادة أو التخصص (اختياري):\n"
        "<i>مثال: رياضيات، فيزياء، لغة عربية</i>",
        parse_mode=ParseMode.HTML
    )
    
    return QUESTION_SUBJECT

async def handle_question_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تخصص السؤال"""
    subject = update.message.text
    question = context.user_data['question_text']
    user_id = update.message.from_user.id
    
    # حفظ السؤال
    question_id = db.add_question(user_id, question, subject)
    
    # خصم المبلغ بعد الخدمة
    if await deduct_after_service(user_id, 'qna', context):
        # إرسال إشعار للمطور للموافقة
        user_data = db.get_user(user_id)
        
        approval_msg = f"""
❓ <b>سؤال جديد يحتاج موافقة</b>
━━━━━━━━━━━━━━
<b>🆔 رقم السؤال:</b> {question_id}
<b>👤 الطالب:</b> {user_data['first_name']} (@{user_data['username'] or 'لا يوجد'})
<b>📚 المادة:</b> {subject}

<b>📝 السؤال:</b>
{question}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ الموافقة", callback_data=f'approve_q_{question_id}'),
                InlineKeyboardButton("❌ الرفض", callback_data=f'reject_q_{question_id}')
            ]
        ]
        
        await send_message(DEVELOPER_ID, approval_msg, context, InlineKeyboardMarkup(keyboard))
        
        # إرسال إشعارات للمشرفين
        db.cursor.execute('SELECT user_id FROM users WHERE is_admin = 1')
        admins = db.cursor.fetchall()
        for admin in admins:
            if admin[0] != DEVELOPER_ID:
                await send_message(admin[0], approval_msg, context, InlineKeyboardMarkup(keyboard))
    
    await update.message.reply_text(
        "✅ <b>تم استلام سؤالك</b>\n"
        "━━━━━━━━━━━━━━\n"
        "سؤالك قيد المراجعة.\n"
        "سيتم إعلامك عند الموافقة عليه.",
        parse_mode=ParseMode.HTML
    )
    
    # تنظيف البيانات
    context.user_data.pop('question_text', None)
    context.user_data.pop('pending_payment', None)
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def answer_question_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الأسئلة للإجابة"""
    query = update.callback_query
    await query.answer()
    
    questions = db.get_pending_questions()
    
    if not questions:
        await query.edit_message_text(
            "📭 <b>لا توجد أسئلة للإجابة حالياً</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    keyboard = []
    for q in questions[:10]:  # عرض أول 10 أسئلة
        question_preview = q[2][:50] + "..." if len(q[2]) > 50 else q[2]
        keyboard.append([InlineKeyboardButton(
            f"سؤال #{q[0]} - {question_preview}",
            callback_data=f'answer_q_{q[0]}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='service_qna')])
    
    await query.edit_message_text(
        "💡 <b>اختر سؤالاً للإجابة</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"عدد الأسئلة المتاحة: {len(questions)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def answer_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء الإجابة على سؤال"""
    query = update.callback_query
    await query.answer()
    
    question_id = int(query.data.replace('answer_q_', ''))
    context.user_data['answering_question'] = question_id
    
    # الحصول على تفاصيل السؤال
    db.cursor.execute('SELECT question FROM questions WHERE id = ?', (question_id,))
    question = db.cursor.fetchone()
    
    if question:
        await query.edit_message_text(
            f"💡 <b>الإجابة على السؤال #{question_id}</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"<b>السؤال:</b>\n{question[0]}\n\n"
            f"<b>اكتب إجابتك الآن:</b>",
            parse_mode=ParseMode.HTML
        )
        
        return ANSWER_QUESTION

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الإجابة"""
    answer = update.message.text
    question_id = context.user_data.get('answering_question')
    user_id = update.message.from_user.id
    
    if not question_id:
        return ConversationHandler.END
    
    # حفظ الإجابة
    db.answer_question(question_id, answer, user_id)
    
    # الحصول على معلومات السؤال
    db.cursor.execute('SELECT user_id, question FROM questions WHERE id = ?', (question_id,))
    question_data = db.cursor.fetchone()
    
    if question_data:
        asker_id = question_data[0]
        question_text = question_data[1]
        
        # إرسال الإجابة لصاحب السؤال
        answer_msg = f"""
💡 <b>تمت الإجابة على سؤالك</b>
━━━━━━━━━━━━━━
<b>🆔 رقم السؤال:</b> {question_id}
<b>📝 السؤال:</b> {question_text}

<b>💡 الإجابة:</b>
{answer}
        """
        
        await send_message(asker_id, answer_msg, context)
        
        # منح مكافأة للمجيب
        db.update_balance(user_id, 100)
        db.add_transaction(user_id, 100, 'answer_reward', f'مكافأة إجابة على سؤال #{question_id}')
        
        await update.message.reply_text(
            "✅ <b>تم إرسال إجابتك بنجاح</b>\n"
            f"🎁 حصلت على 100 دينار مكافأة!",
            parse_mode=ParseMode.HTML
        )
    
    # تنظيف البيانات
    context.user_data.pop('answering_question', None)
    
    await show_main_menu(update, context)
    return ConversationHandler.END

# ============== نظام VIP المتكامل ==============
async def vip_lectures_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قسم محاضرات VIP"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👀 عرض المحاضرات", callback_data='view_vip_lectures')],
        [InlineKeyboardButton("👑 اشتراك VIP", callback_data='vip_subscription_info')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        "👑 <b>محاضرات VIP</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اختر الخيار المناسب:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def view_vip_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض محاضرات VIP"""
    query = update.callback_query
    await query.answer()
    
    lectures = db.get_vip_lectures(approved=True)
    
    if not lectures:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='vip_lectures')]]
        await query.edit_message_text(
            "📭 <b>لا توجد محاضرات VIP متاحة حالياً</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return
    
    message = "👑 <b>محاضرات VIP المتاحة</b>\n━━━━━━━━━━━━━━\n"
    
    keyboard = []
    for lecture in lectures[:10]:  # عرض أول 10 محاضرات
        title = lecture[2]
        price = format_number(lecture[5])
        teacher = db.get_user(lecture[1])
        teacher_name = teacher['first_name'] if teacher else "مجهول"
        
        message += f"\n📚 <b>{title}</b>\n"
        message += f"👨‍🏫 {teacher_name} | 💰 {price} دينار\n"
        
        keyboard.append([InlineKeyboardButton(
            f"🛒 شراء: {title}",
            callback_data=f'buy_lecture_{lecture[0]}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='vip_lectures')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def vip_subscription_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    vip_price = int(db.get_setting('vip_price'))
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    is_vip = False
    days_left = 0
    
    if user_data.get('is_vip'):
        expiry = datetime.strptime(user_data['vip_expiry'], '%Y-%m-%d %H:%M:%S')
        if expiry > datetime.now():
            is_vip = True
            days_left = (expiry - datetime.now()).days
    
    if is_vip:
        message = f"""
👑 <b>اشتراك VIP - مفعل</b>
━━━━━━━━━━━━━━
<b>✨ المميزات:</b>
• رفع محاضرات VIP غير محدود
• أرباح 60% من مبيعات محاضراتك
• رصيد أرباح منفصل للسحب
• أولوية في الدعم الفني

<b>📅 معلومات اشتراكك:</b>
• تاريخ الانتهاء: {expiry.strftime('%Y-%m-%d')}
• الأيام المتبقية: {days_left} يوم
• أرباحك الحالية: {format_number(user_data['vip_balance'])} دينار
        """
        
        keyboard = [
            [InlineKeyboardButton("📤 رفع محاضرة", callback_data='upload_vip_lecture')],
            [InlineKeyboardButton("💰 أرباحي", callback_data='vip_earnings')],
            [InlineKeyboardButton("🔄 تجديد الاشتراك", callback_data=f'renew_vip_{vip_price}')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='vip_lectures')]
        ]
    else:
        message = f"""
👑 <b>اشتراك VIP للمعلمين</b>
━━━━━━━━━━━━━━
<b>✨ المميزات:</b>
• رفع محاضرات VIP غير محدود
• أرباح 60% من مبيعات محاضراتك
• رصيد أرباح منفصل للسحب
• أولوية في الدعم الفني

<b>💰 السعر الشهري:</b> {format_number(vip_price)} دينار

<b>📋 شروط الاشتراك:</b>
1. المحاضرات تخضع للمراجعة والموافقة
2. يمكنك تحديد سعر المحاضرة (0 للمجانية)
3. أرباحك تصل إلى رصيد الأرباح الخاص بك
4. الحد الأدنى للسحب: {format_number(int(db.get_setting('min_withdrawal')))} دينار
        """
        
        keyboard = [
            [InlineKeyboardButton(f"💳 اشتراك الآن - {format_number(vip_price)} دينار", 
                                 callback_data=f'subscribe_vip_{vip_price}')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='vip_lectures')]
        ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def subscribe_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    vip_price = int(query.data.replace('subscribe_vip_', ''))
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if not await has_sufficient_balance(user_id, vip_price):
        await query.answer(f"❌ رصيدك غير كافي. تحتاج {format_number(vip_price)} دينار", show_alert=True)
        return
    
    # خصم المبلغ
    db.update_balance(user_id, -vip_price)
    db.add_transaction(user_id, -vip_price, 'vip_subscription', 'اشتراك VIP شهري')
    
    # تفعيل الاشتراك
    db.subscribe_vip(user_id, vip_price)
    
    # إشعار للمطور
    notification = f"""
👑 <b>اشتراك VIP جديد</b>
━━━━━━━━━━━━━━
<b>👤 المستخدم:</b> {user_data['first_name']} (@{user_data['username'] or 'لا يوجد'})
<b>🆔 الايدي:</b> <code>{user_id}</code>
<b>💰 المبلغ:</b> {format_number(vip_price)} دينار
<b>⏰ الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    await send_message(DEVELOPER_ID, notification, context)
    
    await query.edit_message_text(
        f"✅ <b>تم الاشتراك في VIP بنجاح</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 تم خصم: {format_number(vip_price)} دينار\n"
        f"📅 تاريخ الانتهاء: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}\n\n"
        f"يمكنك الآن رفع محاضرات VIP وكسب الأرباح!",
        parse_mode=ParseMode.HTML
    )

async def upload_vip_lecture_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء رفع محاضرة VIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data.get('is_vip'):
        await query.answer("❌ تحتاج إلى اشتراك VIP", show_alert=True)
        return
    
    expiry = datetime.strptime(user_data['vip_expiry'], '%Y-%m-%d %H:%M:%S')
    if expiry <= datetime.now():
        await query.answer("❌ اشتراك VIP منتهي", show_alert=True)
        return
    
    await query.edit_message_text(
        "📤 <b>رفع محاضرة VIP</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل عنوان المحاضرة:",
        parse_mode=ParseMode.HTML
    )
    
    return VIP_LECTURE_TITLE

async def handle_vip_lecture_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة عنوان المحاضرة"""
    title = update.message.text
    context.user_data['vip_lecture_title'] = title
    
    await update.message.reply_text(
        "📝 أدخل وصف المحاضرة:",
        parse_mode=ParseMode.HTML
    )
    
    return VIP_LECTURE_DESC

async def handle_vip_lecture_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة وصف المحاضرة"""
    description = update.message.text
    context.user_data['vip_lecture_desc'] = description
    
    await update.message.reply_text(
        "💰 أدخل سعر المحاضرة (0 للمجانية):\n"
        "<i>ملاحظة: ستحصل على 60% من السعر</i>",
        parse_mode=ParseMode.HTML
    )
    
    return VIP_LECTURE_PRICE

async def handle_vip_lecture_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة سعر المحاضرة"""
    try:
        price = int(update.message.text)
        if price < 0:
            await update.message.reply_text("❌ السعر لا يمكن أن يكون سالباً")
            return VIP_LECTURE_PRICE
        
        context.user_data['vip_lecture_price'] = price
        
        await update.message.reply_text(
            "📎 أرسل ملف المحاضرة (فيديو أو مستند):\n"
            "<i>الحد الأقصى: 100 ميجابايت</i>",
            parse_mode=ParseMode.HTML
        )
        
        return VIP_LECTURE_FILE
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return VIP_LECTURE_PRICE

async def handle_vip_lecture_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف المحاضرة"""
    if not (update.message.video or update.message.document):
        await update.message.reply_text("❌ الرجاء إرسال ملف فيديو أو مستند")
        return VIP_LECTURE_FILE
    
    # التحقق من الحجم (100MB)
    file_size = 0
    if update.message.video:
        file_size = update.message.video.file_size
    elif update.message.document:
        file_size = update.message.document.file_size
    
    if file_size and file_size > 100 * 1024 * 1024:  # 100MB
        await update.message.reply_text("❌ حجم الملف كبير جداً. الحد الأقصى 100MB")
        return VIP_LECTURE_FILE
    
    file_id = update.message.video.file_id if update.message.video else update.message.document.file_id
    user_id = update.message.from_user.id
    
    # حفظ المحاضرة
    lecture_id = db.add_vip_lecture(
        user_id,
        context.user_data['vip_lecture_title'],
        context.user_data['vip_lecture_desc'],
        file_id,
        context.user_data['vip_lecture_price']
    )
    
    # إشعار للمطور للموافقة
    user_data = db.get_user(user_id)
    
    approval_msg = f"""
📤 <b>محاضرة VIP جديدة</b>
━━━━━━━━━━━━━━
<b>🆔 رقم المحاضرة:</b> {lecture_id}
<b>👨‍🏫 المعلم:</b> {user_data['first_name']} (@{user_data['username'] or 'لا يوجد'})
<b>💰 السعر:</b> {format_number(context.user_data['vip_lecture_price'])} دينار

<b>📚 العنوان:</b>
{context.user_data['vip_lecture_title']}

<b>📝 الوصف:</b>
{context.user_data['vip_lecture_desc']}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("✅ الموافقة", callback_data=f'approve_lecture_{lecture_id}'),
            InlineKeyboardButton("❌ الرفض", callback_data=f'reject_lecture_{lecture_id}')
        ]
    ]
    
    await send_message(DEVELOPER_ID, approval_msg, context, InlineKeyboardMarkup(keyboard))
    
    await update.message.reply_text(
        f"✅ <b>تم رفع المحاضرة بنجاح</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>🆔 رقم المحاضرة:</b> {lecture_id}\n"
        f"<b>📚 العنوان:</b> {context.user_data['vip_lecture_title']}\n\n"
        f"المحاضرة قيد المراجعة. سيتم إعلامك عند الموافقة.",
        parse_mode=ParseMode.HTML
    )
    
    # تنظيف البيانات
    for key in ['vip_lecture_title', 'vip_lecture_desc', 'vip_lecture_price']:
        context.user_data.pop(key, None)
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def vip_earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أرباح VIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    earnings = db.get_teacher_earnings(user_id)
    min_withdrawal = int(db.get_setting('min_withdrawal'))
    
    keyboard = []
    
    if user_data['vip_balance'] >= min_withdrawal:
        keyboard.append([InlineKeyboardButton(
            f"💰 سحب {format_number(user_data['vip_balance'])} دينار",
            callback_data='withdraw_earnings'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='vip_subscription_info')])
    
    await query.edit_message_text(
        f"💰 <b>أرباحك من VIP</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>💵 الرصيد القابل للسحب:</b> {format_number(user_data['vip_balance'])} دينار\n"
        f"<b>📊 إجمالي الأرباح:</b> {format_number(earnings)} دينار\n"
        f"<b>📈 الحد الأدنى للسحب:</b> {format_number(min_withdrawal)} دينار\n\n"
        f"<i>للسحب، تواصل مع الدعم الفني @Allawi04@</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============== نظام الدعوة ==============
async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دعوة صديق"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    invite_link = f"https://t.me/{BOT_USERNAME[1:]}?start={user_data['invite_code']}"
    invite_bonus = int(db.get_setting('invite_bonus'))
    
    # نص دعوي للمعلمين إذا كان مستخدم VIP
    if user_data.get('is_vip'):
        invite_text = f"""
👑 <b>انضم إلى منصة "يلا نتعلم" التعليمية!</b>

🎯 <b>خاص للمعلمين:</b>
• ارفع محاضراتك VIP
• احصل على 60% من الأرباح
• سحب أرباحك بسهولة
• منصة متكاملة للتعليم الإلكتروني

💰 <b>مميزات إضافية:</b>
• تلخيص الملازم بالذكاء الاصطناعي
• سؤال وجواب متخصص
• مواد دراسية متنوعة
• مجتمع تعليمي تفاعلي

🔗 <b>رابط الانضمام:</b>
{invite_link}

🎁 <b>احصل على {format_number(invite_bonus)} دينار مجاناً!</b>
        """
    else:
        invite_text = f"""
🎓 <b>انضم إلى بوت "يلا نتعلم" التعليمي!</b>

✨ <b>المميزات:</b>
• حساب درجة الإعفاء
• تلخيص الملازم بالذكاء الاصطناعي
• سؤال وجواب متخصص
• مواد دراسية متنوعة
• محاضرات VIP حصرية

🔗 <b>رابط الانضمام:</b>
{invite_link}

🎁 <b>احصل على {format_number(invite_bonus)} دينار مجاناً!</b>
        """
    
    keyboard = [
        [InlineKeyboardButton("📲 مشاركة الرابط", 
         url=f"https://t.me/share/url?url={invite_link}&text={html.escape(invite_text)}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        "👥 <b>دعوة صديق</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"<b>🔗 رابط الدعوة:</b>\n<code>{invite_link}</code>\n\n"
        f"<b>🎁 المكافأة:</b>\n"
        f"• أنت وصديقك: {format_number(invite_bonus)} دينار لكل واحد\n"
        f"• عدد دعواتك: {user_data['invited_count']}\n\n"
        f"<b>📤 اضغط على الزر أدناه للمشاركة:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============== لوحة التحكم المتكاملة ==============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.answer("⛔ ليس لديك صلاحية", show_alert=True)
        return
    
    # إحصائيات
    db.cursor.execute('SELECT COUNT(*) FROM users')
    total_users = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1')
    vip_users = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
    total_balance = db.cursor.fetchone()[0]
    
    message = f"""
⚙️ <b>لوحة التحكم</b>
━━━━━━━━━━━━━━
<b>📊 الإحصائيات:</b>
👥 المستخدمين: {format_number(total_users)}
👑 مستخدمين VIP: {format_number(vip_users)}
💰 إجمالي الرصيد: {format_number(total_balance)} دينار
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("💳 الشحن والخصم", callback_data='admin_balance')],
        [InlineKeyboardButton("🚫 الحظر والإلغاء", callback_data='admin_ban')],
        [InlineKeyboardButton("⚙️ إدارة الخدمات", callback_data='admin_services')],
        [InlineKeyboardButton("👑 إدارة VIP", callback_data='admin_vip')],
        [InlineKeyboardButton("❓ إدارة الأسئلة", callback_data='admin_questions')],
        [InlineKeyboardButton("📚 إدارة المواد", callback_data='admin_materials')],
        [InlineKeyboardButton("📣 إذاعة", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_users_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    users = db.get_all_users()[:10]  # أول 10 مستخدمين
    
    message = "👥 <b>آخر 10 مستخدمين</b>\n━━━━━━━━━━━━━━\n"
    
    for user in users:
        status = "👑 VIP" if user[12] else ("🚫 محظور" if user[10] else "✅ نشط")
        message += f"\n👤 {user[2]} (@{user[1] or 'لا يوجد'})\n"
        message += f"🆔: <code>{user[0]}</code> | 💰: {format_number(user[4])}\n"
        message += f"📅: {user[9][:10]} | {status}\n"
        message += "─" * 30
    
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data='admin_search_user')],
        [InlineKeyboardButton("👑 رفع مشرف", callback_data='admin_add_admin')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_balance_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الرصيد"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ شحن رصيد", callback_data='admin_charge')],
        [InlineKeyboardButton("➖ خصم رصيد", callback_data='admin_deduct')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        "💳 <b>إدارة الرصيد</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اختر العملية:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء شحن رصيد"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "➕ <b>شحن رصيد</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل ايدي المستخدم:",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_CHARGE_USER

async def handle_admin_charge_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ايدي المستخدم للشحن"""
    try:
        user_id = int(update.message.text)
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return ADMIN_CHARGE_USER
        
        context.user_data['charge_user_id'] = user_id
        
        await update.message.reply_text(
            f"👤 المستخدم: {user['first_name']}\n"
            f"💰 الرصيد الحالي: {format_number(user['balance'])} دينار\n\n"
            "أدخل المبلغ للشحن:",
            parse_mode=ParseMode.HTML
        )
        
        return ADMIN_CHARGE_AMOUNT
    except:
        await update.message.reply_text("❌ الرجاء إدخال ايدي صحيح")
        return ADMIN_CHARGE_USER

async def handle_admin_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ الشحن"""
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return ADMIN_CHARGE_AMOUNT
        
        user_id = context.user_data['charge_user_id']
        user = db.get_user(user_id)
        
        # شحن الرصيد
        db.update_balance(user_id, amount)
        db.add_transaction(user_id, amount, 'admin_charge', f'شحن إداري بواسطة {update.message.from_user.id}')
        
        # إشعار للمستخدم
        await send_message(user_id,
            f"🎉 <b>تم شحن حسابك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الرصيد الجديد: {format_number(user['balance'] + amount)} دينار",
            context
        )
        
        await update.message.reply_text(
            f"✅ <b>تم الشحن بنجاح</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: {user['first_name']}\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الرصيد الجديد: {format_number(user['balance'] + amount)} دينار",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data.pop('charge_user_id', None)
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return ADMIN_CHARGE_AMOUNT

async def admin_deduct_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء خصم رصيد"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "➖ <b>خصم رصيد</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل ايدي المستخدم:",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_DEDUCT_USER

async def handle_admin_deduct_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ايدي المستخدم للخصم"""
    try:
        user_id = int(update.message.text)
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return ADMIN_DEDUCT_USER
        
        context.user_data['deduct_user_id'] = user_id
        
        await update.message.reply_text(
            f"👤 المستخدم: {user['first_name']}\n"
            f"💰 الرصيد الحالي: {format_number(user['balance'])} دينار\n\n"
            "أدخل المبلغ للخصم:",
            parse_mode=ParseMode.HTML
        )
        
        return ADMIN_DEDUCT_AMOUNT
    except:
        await update.message.reply_text("❌ الرجاء إدخال ايدي صحيح")
        return ADMIN_DEDUCT_USER

async def handle_admin_deduct_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ الخصم"""
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return ADMIN_DEDUCT_AMOUNT
        
        user_id = context.user_data['deduct_user_id']
        user = db.get_user(user_id)
        
        if user['balance'] < amount:
            await update.message.reply_text("❌ رصيد المستخدم غير كافي")
            return ADMIN_DEDUCT_AMOUNT
        
        # خصم الرصيد
        db.update_balance(user_id, -amount)
        db.add_transaction(user_id, -amount, 'admin_deduction', f'خصم إداري بواسطة {update.message.from_user.id}')
        
        # إشعار للمستخدم
        await send_message(user_id,
            f"⚠️ <b>تم خصم من حسابك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الرصيد الجديد: {format_number(user['balance'] - amount)} دينار",
            context
        )
        
        await update.message.reply_text(
            f"✅ <b>تم الخصم بنجاح</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: {user['first_name']}\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الرصيد الجديد: {format_number(user['balance'] - amount)} دينار",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data.pop('deduct_user_id', None)
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return ADMIN_DEDUCT_AMOUNT

async def admin_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الحظر"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data='admin_ban')],
        [InlineKeyboardButton("✅ إلغاء حظر", callback_data='admin_unban')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
    ]
    
    await query.edit_message_text(
        "🚫 <b>إدارة الحظر</b>\n"
        "━━━━━━━━━━━━━━\n"
        "اختر العملية:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء حظر مستخدم"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "🚫 <b>حظر مستخدم</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل ايدي المستخدم:",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_BAN_USER

async def handle_admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة حظر مستخدم"""
    try:
        user_id = int(update.message.text)
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return ADMIN_BAN_USER
        
        if user['is_banned']:
            await update.message.reply_text("⚠️ المستخدم محظور بالفعل")
            return ADMIN_BAN_USER
        
        # حظر المستخدم
        db.ban_user(user_id)
        
        await update.message.reply_text(
            f"✅ <b>تم حظر المستخدم</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: {user['first_name']}\n"
            f"🆔 الايدي: <code>{user_id}</code>",
            parse_mode=ParseMode.HTML
        )
        
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال ايدي صحيح")
        return ADMIN_BAN_USER

async def admin_unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إلغاء حظر"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "✅ <b>إلغاء حظر</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل ايدي المستخدم:",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_UNBAN_USER

async def handle_admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إلغاء حظر"""
    try:
        user_id = int(update.message.text)
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return ADMIN_UNBAN_USER
        
        if not user['is_banned']:
            await update.message.reply_text("⚠️ المستخدم غير محظور")
            return ADMIN_UNBAN_USER
        
        # إلغاء حظر المستخدم
        db.unban_user(user_id)
        
        await update.message.reply_text(
            f"✅ <b>تم إلغاء حظر المستخدم</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 المستخدم: {user['first_name']}\n"
            f"🆔 الايدي: <code>{user_id}</code>",
            parse_mode=ParseMode.HTML
        )
        
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال ايدي صحيح")
        return ADMIN_UNBAN_USER

async def admin_services_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الخدمات"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    services = db.get_services()
    
    message = "⚙️ <b>إدارة الخدمات</b>\n━━━━━━━━━━━━━━\n"
    keyboard = []
    
    for service in services:
        name, display_name, price, is_active = service[1], service[2], service[3], service[4]
        status = "✅ مفعل" if is_active else "❌ معطل"
        
        message += f"\n<b>{display_name}</b>\n"
        message += f"💰 السعر: {format_number(price)} دينار | {status}\n"
        message += "─" * 30 + "\n"
        
        row = []
        row.append(InlineKeyboardButton(
            f"{'❌' if is_active else '✅'} {display_name}",
            callback_data=f'toggle_{name}'
        ))
        row.append(InlineKeyboardButton(
            "💰 تغيير",
            callback_data=f'price_{name}'
        ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def toggle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/تعطيل خدمة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    service_name = query.data.replace('toggle_', '')
    service = db.get_service(service_name)
    
    new_status = 0 if service['is_active'] == 1 else 1
    db.toggle_service(service_name, new_status)
    
    status_text = "مفعلة" if new_status == 1 else "معطلة"
    await query.answer(f"✅ تم {status_text} الخدمة", show_alert=True)
    
    await admin_services_management(update, context)

async def change_service_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير سعر خدمة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    service_name = query.data.replace('price_', '')
    service = db.get_service(service_name)
    
    context.user_data['changing_service'] = service_name
    
    await query.edit_message_text(
        f"💰 <b>تغيير سعر الخدمة</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>الخدمة:</b> {service['display_name']}\n"
        f"<b>السعر الحالي:</b> {format_number(service['price'])} دينار\n\n"
        f"أدخل السعر الجديد:",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_SERVICE_PRICE

async def handle_service_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة السعر الجديد"""
    try:
        new_price = int(update.message.text)
        if new_price < 0:
            await update.message.reply_text("❌ السعر لا يمكن أن يكون سالباً")
            return ADMIN_SERVICE_PRICE
        
        service_name = context.user_data['changing_service']
        service = db.get_service(service_name)
        
        # تحديث السعر
        db.update_service_price(service_name, new_price)
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير السعر</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"<b>الخدمة:</b> {service['display_name']}\n"
            f"<b>السعر الجديد:</b> {format_number(new_price)} دينار",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data.pop('changing_service', None)
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return ADMIN_SERVICE_PRICE

async def admin_vip_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    subscriptions = db.get_vip_subscriptions()
    
    message = "👑 <b>مشتركي VIP</b>\n━━━━━━━━━━━━━━\n"
    
    keyboard = []
    for sub in subscriptions[:10]:  # أول 10 اشتراكات
        user_id, _, amount, expiry_date, purchase_date, _, username, first_name = sub
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d %H:%M:%S')
        days_left = (expiry - datetime.now()).days
        
        message += f"\n👤 {first_name} (@{username or 'لا يوجد'})\n"
        message += f"🆔: <code>{user_id}</code> | 💰: {format_number(amount)} دينار\n"
        message += f"📅 الشراء: {purchase_date[:10]} | ⏳ متبقي: {days_left} يوم\n"
        message += "─" * 30 + "\n"
        
        keyboard.append([InlineKeyboardButton(
            f"👤 {first_name}",
            callback_data=f'vip_user_{user_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("💰 سحب أرباح مدرس", callback_data='withdraw_teacher')])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def vip_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفاصيل مستخدم VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace('vip_user_', ''))
    user = db.get_user(user_id)
    
    if not user or not user['is_vip']:
        await query.answer("❌ هذا المستخدم ليس مشتركاً في VIP", show_alert=True)
        return
    
    expiry = datetime.strptime(user['vip_expiry'], '%Y-%m-%d %H:%M:%S')
    days_left = (expiry - datetime.now()).days
    
    message = f"""
👑 <b>تفاصيل مشترك VIP</b>
━━━━━━━━━━━━━━
<b>👤 الاسم:</b> {user['first_name']} (@{user['username'] or 'لا يوجد'})
<b>🆔 الايدي:</b> <code>{user_id}</code>
<b>💰 رصيد الأرباح:</b> {format_number(user['vip_balance'])} دينار
<b>📅 تاريخ الانتهاء:</b> {expiry.strftime('%Y-%m-%d')}
<b>⏳ الأيام المتبقية:</b> {days_left} يوم
<b>🛒 عدد محاضراته:</b> {len(db.get_vip_lectures(teacher_id=user_id))}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("➕ تجديد شهر", callback_data=f'extend_vip_{user_id}_30'),
            InlineKeyboardButton("➖ إلغاء الاشتراك", callback_data=f'cancel_vip_{user_id}')
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data='admin_vip')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def extend_vip_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تجديد اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    _, user_id, days = query.data.split('_')
    user_id = int(user_id)
    days = int(days)
    
    db.extend_vip_subscription(user_id, days)
    
    user = db.get_user(user_id)
    expiry = datetime.strptime(user['vip_expiry'], '%Y-%m-%d %H:%M:%S')
    
    await query.answer(f"✅ تم تجديد الاشتراك لـ {days} يوم", show_alert=True)
    
    # إشعار للمستخدم
    await send_message(user_id,
        f"🔄 <b>تم تجديد اشتراكك VIP</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📅 تاريخ الانتهاء الجديد: {expiry.strftime('%Y-%m-%d')}\n"
        f"⏳ المدة المضافة: {days} يوم",
        context
    )
    
    await admin_vip_management(update, context)

async def cancel_vip_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    user_id = int(query.data.replace('cancel_vip_', ''))
    
    db.cancel_vip_subscription(user_id)
    
    await query.answer("✅ تم إلغاء الاشتراك", show_alert=True)
    
    # إشعار للمستخدم
    await send_message(user_id,
        "🚫 <b>تم إلغاء اشتراكك VIP</b>\n"
        "━━━━━━━━━━━━━━\n"
        "لقد تم إلغاء اشتراكك في VIP.\n"
        "يمكنك التجديد في أي وقت.",
        context
    )
    
    await admin_vip_management(update, context)

async def withdraw_teacher_earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سحب أرباح مدرس"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "💰 <b>سحب أرباح مدرس</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أدخل ايدي المدرس:",
        parse_mode=ParseMode.HTML
    )
    
    context.user_data['withdraw_action'] = 'teacher'
    return WITHDRAW_REQUEST

async def handle_withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب السحب"""
    try:
        user_id = int(update.message.text)
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return WITHDRAW_REQUEST
        
        if context.user_data.get('withdraw_action') == 'teacher':
            if user['vip_balance'] <= 0:
                await update.message.reply_text("❌ هذا المدرس ليس لديه أرباح")
                return WITHDRAW_REQUEST
            
            context.user_data['withdraw_user_id'] = user_id
            
            await update.message.reply_text(
                f"👨‍🏫 المدرس: {user['first_name']}\n"
                f"💰 الأرباح المتاحة: {format_number(user['vip_balance'])} دينار\n\n"
                f"أدخل المبلغ للسحب:",
                parse_mode=ParseMode.HTML
            )
            
            return WITHDRAW_REQUEST
        
    except:
        await update.message.reply_text("❌ الرجاء إدخال ايدي صحيح")
        return WITHDRAW_REQUEST

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ السحب"""
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return WITHDRAW_REQUEST
        
        user_id = context.user_data['withdraw_user_id']
        user = db.get_user(user_id)
        
        if user['vip_balance'] < amount:
            await update.message.reply_text(f"❌ الأرباح غير كافية. المتاح: {format_number(user['vip_balance'])} دينار")
            return WITHDRAW_REQUEST
        
        # سحب الأرباح
        db.withdraw_earnings(user_id, amount)
        
        await update.message.reply_text(
            f"✅ <b>تم سحب الأرباح</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍🏫 المدرس: {user['first_name']}\n"
            f"💰 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الأرباح المتبقية: {format_number(user['vip_balance'] - amount)} دينار",
            parse_mode=ParseMode.HTML
        )
        
        # إشعار للمدرس
        await send_message(user_id,
            f"💰 <b>تم سحب أرباحك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 المبلغ: {format_number(amount)} دينار\n"
            f"📊 الأرباح المتبقية: {format_number(user['vip_balance'] - amount)} دينار\n\n"
            f"للسحب، تواصل مع الدعم الفني @Allawi04@",
            context
        )
        
        # تنظيف البيانات
        context.user_data.pop('withdraw_user_id', None)
        context.user_data.pop('withdraw_action', None)
        
        await admin_panel(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
        return WITHDRAW_REQUEST

async def admin_questions_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الأسئلة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    pending_questions = db.get_pending_questions()
    
    if not pending_questions:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]
        await query.edit_message_text(
            "📭 <b>لا توجد أسئلة قيد المراجعة</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return
    
    message = "❓ <b>الأسئلة قيد المراجعة</b>\n━━━━━━━━━━━━━━\n"
    
    keyboard = []
    for q in pending_questions[:5]:  # أول 5 أسئلة
        question_id, _, question, subject, _, date, _, _, _, _, username, first_name = q
        question_preview = question[:50] + "..." if len(question) > 50 else question
        
        message += f"\n🆔 <b>#{question_id}</b> - {first_name}\n"
        message += f"📚 {subject or 'غير محدد'}\n"
        message += f"📝 {question_preview}\n"
        message += f"⏰ {date[:16]}\n"
        message += "─" * 30 + "\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ #{question_id}", callback_data=f'approve_q_{question_id}'),
            InlineKeyboardButton(f"❌ #{question_id}", callback_data=f'reject_q_{question_id}')
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def approve_question_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """موافقة على سؤال"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    question_id = int(query.data.replace('approve_q_', ''))
    
    db.approve_question(question_id)
    
    # إشعار لصاحب السؤال
    db.cursor.execute('SELECT user_id, question FROM questions WHERE id = ?', (question_id,))
    question_data = db.cursor.fetchone()
    
    if question_data:
        user_id = question_data[0]
        await send_message(user_id,
            f"✅ <b>تمت الموافقة على سؤالك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 رقم السؤال: {question_id}\n"
            f"📝 السؤال: {question_data[1][:100]}...\n\n"
            f"يمكن للطلاب الآن الإجابة على سؤالك.",
            context
        )
    
    await query.answer("✅ تمت الموافقة على السؤال", show_alert=True)
    await admin_questions_management(update, context)

async def reject_question_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض سؤال"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    question_id = int(query.data.replace('reject_q_', ''))
    
    # إشعار لصاحب السؤال
    db.cursor.execute('SELECT user_id, question FROM questions WHERE id = ?', (question_id,))
    question_data = db.cursor.fetchone()
    
    if question_data:
        user_id = question_data[0]
        await send_message(user_id,
            f"❌ <b>تم رفض سؤالك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 رقم السؤال: {question_id}\n"
            f"📝 السؤال: {question_data[1][:100]}...\n\n"
            f"الرجاء التأكد من:\n"
            f"1. وضوح السؤال\n"
            f"2. مناسبته للمنصة التعليمية\n"
            f"3. عدم وجود محتوى غير لائق",
            context
        )
    
    db.reject_question(question_id)
    
    await query.answer("❌ تم رفض السؤال", show_alert=True)
    await admin_questions_management(update, context)

async def admin_materials_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المواد"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    materials = db.get_materials()
    
    if not materials:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]
        await query.edit_message_text(
            "📭 <b>لا توجد مواد مضافة</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return
    
    message = "📚 <b>المواد المضافة</b>\n━━━━━━━━━━━━━━\n"
    
    keyboard = []
    for mat in materials[:10]:  # أول 10 مواد
        message += f"\n📖 <b>{mat[1]}</b>\n"
        message += f"📝 {mat[2]}\n"
        message += f"📚 {mat[3]} | 📅 {mat[6][:10]}\n"
        message += "─" * 30 + "\n"
        
        keyboard.append([InlineKeyboardButton(
            f"🗑️ حذف {mat[1]}",
            callback_data=f'delete_material_{mat[0]}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف مادة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    material_id = int(query.data.replace('delete_material_', ''))
    
    db.delete_material(material_id)
    
    await query.answer("🗑️ تم حذف المادة", show_alert=True)
    await admin_materials_management(update, context)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إذاعة رسالة"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "📣 <b>الإذاعة العامة</b>\n"
        "━━━━━━━━━━━━━━\n"
        "أرسل الرسالة التي تريد إذاعتها:\n\n"
        "<i>يمكنك استخدام HTML للتنسيق</i>",
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_BROADCAST

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسالة للإذاعة"""
    broadcast_text = update.message.text
    
    # جلب جميع المستخدمين
    users = db.get_all_users()
    
    success = 0
    failed = 0
    
    progress_msg = await update.message.reply_text(
        "📤 <b>جاري الإذاعة...</b>\n"
        "━━━━━━━━━━━━━━\n"
        "✅ تم إرسال: 0\n"
        "❌ فشل: 0\n"
        f"📊 الإجمالي: {len(users)}",
        parse_mode=ParseMode.HTML
    )
    
    for i, user in enumerate(users, 1):
        user_id = user[0]
        
        try:
            await send_message(user_id, broadcast_text, context)
            success += 1
        except:
            failed += 1
        
        # تحديث الرسالة كل 20 مستخدم
        if i % 20 == 0:
            await progress_msg.edit_text(
                f"📤 <b>جاري الإذاعة...</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"✅ تم إرسال: {success}\n"
                f"❌ فشل: {failed}\n"
                f"📊 الإجمالي: {len(users)}\n"
                f"📈 النسبة: {(i/len(users))*100:.1f}%",
                parse_mode=ParseMode.HTML
            )
    
    await progress_msg.edit_text(
        f"🎉 <b>تمت الإذاعة بنجاح</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"✅ تم إرسال بنجاح: {success}\n"
        f"❌ فشل في الإرسال: {failed}\n"
        f"📊 الإجمالي: {len(users)}\n"
        f"📈 نسبة النجاح: {(success/len(users))*100:.1f}%",
        parse_mode=ParseMode.HTML
    )
    
    await admin_panel(update, context)
    return ConversationHandler.END

async def approve_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """موافقة على محاضرة VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    lecture_id = int(query.data.replace('approve_lecture_', ''))
    
    db.approve_vip_lecture(lecture_id)
    
    # إشعار للمعلم
    lecture = db.get_vip_lecture(lecture_id)
    if lecture:
        teacher_id = lecture['teacher_id']
        await send_message(teacher_id,
            f"✅ <b>تمت الموافقة على محاضرتك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📚 العنوان: {lecture['title']}\n"
            f"💰 السعر: {format_number(lecture['price'])} دينار\n\n"
            f"المحاضرة متاحة الآن للشراء.",
            context
        )
    
    await query.answer("✅ تمت الموافقة على المحاضرة", show_alert=True)

async def reject_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض محاضرة VIP"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        return
    
    lecture_id = int(query.data.replace('reject_lecture_', ''))
    
    # إشعار للمعلم
    lecture = db.get_vip_lecture(lecture_id)
    if lecture:
        teacher_id = lecture['teacher_id']
        await send_message(teacher_id,
            f"❌ <b>تم رفض محاضرتك</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📚 العنوان: {lecture['title']}\n\n"
            f"الرجاء التأكد من:\n"
            f"1. جودة المحتوى\n"
            f"2. ملاءمته للمنصة التعليمية\n"
            f"3. عدم وجود حقوق نشر\n"
            f"4. الوضوح والصوت الجيد",
            context
        )
    
    db.reject_vip_lecture(lecture_id)
    
    await query.answer("❌ تم رفض المحاضرة", show_alert=True)

# ============== معالجة الأزرار العامة ==============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع استدعاءات الأزرار"""
    query = update.callback_query
    data = query.data
    
    try:
        # الخدمات
        if data == 'service_exemption':
            await exemption_service(update, context)
        elif data == 'service_qna':
            await qna_service(update, context)
        elif data.startswith('service_'):
            await query.answer("⏳ قيد التطوير...", show_alert=True)
        
        # الأقسام الرئيسية
        elif data == 'back_to_main':
            await show_main_menu(update, context)
        elif data == 'materials':
            await materials_section(update, context)
        elif data.startswith('stage_'):
            await show_stage_materials(update, context)
        
        # VIP
        elif data == 'vip_lectures':
            await vip_lectures_section(update, context)
        elif data == 'view_vip_lectures':
            await view_vip_lectures(update, context)
        elif data == 'vip_subscription_info':
            await vip_subscription_info(update, context)
        elif data.startswith('subscribe_vip_'):
            await subscribe_vip(update, context)
        elif data == 'upload_vip_lecture':
            await upload_vip_lecture_start(update, context)
        elif data == 'vip_earnings':
            await vip_earnings(update, context)
        elif data.startswith('approve_lecture_'):
            await approve_lecture(update, context)
        elif data.startswith('reject_lecture_'):
            await reject_lecture(update, context)
        
        # الدعوة والرصيد
        elif data == 'invite':
            await invite_friend(update, context)
        elif data == 'balance':
            await query.answer("⏳ قيد التطوير...", show_alert=True)
        
        # إدارة الأسئلة
        elif data == 'ask_question':
            await ask_question_start(update, context)
        elif data == 'answer_question_list':
            await answer_question_list(update, context)
        elif data.startswith('answer_q_'):
            await answer_question_start(update, context)
        elif data.startswith('approve_q_'):
            await approve_question_admin(update, context)
        elif data.startswith('reject_q_'):
            await reject_question_admin(update, context)
        
        # لوحة التحكم
        elif data == 'admin_panel':
            await admin_panel(update, context)
        elif data == 'admin_users':
            await admin_users_management(update, context)
        elif data == 'admin_balance':
            await admin_balance_management(update, context)
        elif data == 'admin_charge':
            await admin_charge_start(update, context)
        elif data == 'admin_deduct':
            await admin_deduct_start(update, context)
        elif data == 'admin_ban':
            await admin_ban_management(update, context)
        elif data == 'admin_services':
            await admin_services_management(update, context)
        elif data.startswith('toggle_'):
            await toggle_service(update, context)
        elif data.startswith('price_'):
            await change_service_price(update, context)
        elif data == 'admin_vip':
            await admin_vip_management(update, context)
        elif data.startswith('vip_user_'):
            await vip_user_details(update, context)
        elif data.startswith('extend_vip_'):
            await extend_vip_subscription(update, context)
        elif data.startswith('cancel_vip_'):
            await cancel_vip_subscription(update, context)
        elif data == 'withdraw_teacher':
            await withdraw_teacher_earnings(update, context)
        elif data == 'admin_questions':
            await admin_questions_management(update, context)
        elif data == 'admin_materials':
            await admin_materials_management(update, context)
        elif data.startswith('delete_material_'):
            await delete_material(update, context)
        elif data == 'admin_broadcast':
            await admin_broadcast(update, context)
        
        else:
            await query.answer("⏳ قيد التطوير...", show_alert=True)
    
    except Exception as e:
        logging.error(f"Callback error: {e}")
        await query.answer("❌ حدث خطأ", show_alert=True)

# ============== الوظيفة الرئيسية ==============
def main():
    """تشغيل البوت"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    
    # Conversation Handlers
    exemption_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(exemption_service, pattern='^service_exemption$')],
        states={
            GRADE_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grade_1)],
            GRADE_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grade_2)],
            GRADE_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_grade_3)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^back_to_main$')]
    )
    
    material_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_material_start, pattern='^add_material$')],
        states={
            UPLOAD_MATERIAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_material_name)],
            UPLOAD_MATERIAL_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_material_desc)],
            UPLOAD_MATERIAL_STAGE: [CallbackQueryHandler(handle_material_stage, pattern='^stage_.*_add$')],
            UPLOAD_MATERIAL_FILE: [MessageHandler(filters.Document.ALL, handle_material_file)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^back_to_main$')]
    )
    
    question_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_question_start, pattern='^ask_question$')],
        states={
            QUESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question_text)],
            QUESTION_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question_subject)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^back_to_main$')]
    )
    
    answer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(answer_question_start, pattern='^answer_q_')],
        states={
            ANSWER_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^back_to_main$')]
    )
    
    vip_lecture_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(upload_vip_lecture_start, pattern='^upload_vip_lecture$')],
        states={
            VIP_LECTURE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vip_lecture_title)],
            VIP_LECTURE_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vip_lecture_desc)],
            VIP_LECTURE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vip_lecture_price)],
            VIP_LECTURE_FILE: [MessageHandler(filters.VIDEO | filters.Document.ALL, handle_vip_lecture_file)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^back_to_main$')]
    )
    
    admin_charge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_charge_start, pattern='^admin_charge$')],
        states={
            ADMIN_CHARGE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_charge_user)],
            ADMIN_CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_charge_amount)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    admin_deduct_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_deduct_start, pattern='^admin_deduct$')],
        states={
            ADMIN_DEDUCT_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_deduct_user)],
            ADMIN_DEDUCT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_deduct_amount)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    admin_ban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_ban_start, pattern='^admin_ban$')],
        states={
            ADMIN_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_ban)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    admin_unban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_unban_start, pattern='^admin_unban$')],
        states={
            ADMIN_UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_unban)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    service_price_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(change_service_price, pattern='^price_')],
        states={
            ADMIN_SERVICE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service_price)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast, pattern='^admin_broadcast$')],
        states={
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_teacher_earnings, pattern='^withdraw_teacher$')],
        states={
            WITHDRAW_REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_request),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount),
            ],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')]
    )
    
    # إضافة جميع الـ Conversation Handlers
    application.add_handler(exemption_conv)
    application.add_handler(material_conv)
    application.add_handler(question_conv)
    application.add_handler(answer_conv)
    application.add_handler(vip_lecture_conv)
    application.add_handler(admin_charge_conv)
    application.add_handler(admin_deduct_conv)
    application.add_handler(admin_ban_conv)
    application.add_handler(admin_unban_conv)
    application.add_handler(service_price_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(withdraw_conv)
    
    # معالجة استدعاءات الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("=" * 50)
    print("✅ البوت يعمل بنجاح!")
    print(f"🤖 البوت: {BOT_USERNAME}")
    print(f"👤 المطور: {DEVELOPER_USERNAME}")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
