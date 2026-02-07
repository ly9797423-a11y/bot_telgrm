#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام: يلا نتعلم - الإصدار المصحح
مطور البوت: @Allawi04
ايدي المطور: 6130994941
توكن البوت الجديد: 8279341291:AAGet-xHKrmSg1RuBYaaNuzmaqv1LgwUM6E
"""

# ====================== المكتبات المطلوبة ======================
import os
import sys
import json
import sqlite3
import logging
import tempfile
import hashlib
import time
import datetime
import re
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import requests
from io import BytesIO
import base64

# مكتبات تليجرام
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, InputFile,
    InputMediaDocument
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from telegram.constants import ParseMode, ChatAction

# مكتبات معالجة PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    import arabic_reshaper
    from bidi.algorithm import get_display
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  مكتبات PDF غير مثبتة، سيتم تعطيل ميزة تلخيص PDF")

# مكتبات معالجة النصوص والصور
try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False

try:
    import PyPDF2
    PYPDF2_SUPPORT = True
except ImportError:
    PYPDF2_SUPPORT = False

import io
import textwrap

# إعدادات التسعير
PRICE_CONFIG = {
    'exemption_calc': 1000,
    'pdf_summary': 1000,
    'qna': 1000,
    'help_student': 1000,
    'vip_subscription': 5000,  # سعر الاشتراك الشهري VIP
}

# إعدادات API
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# إعدادات البوت
BOT_TOKEN = "8279341291:AAGet-xHKrmSg1RuBYaaNuzmaqv1LgwUM6E"  # توكن جديد
ADMIN_ID = 6130994941
BOT_USERNAME = "@FC4Xbot"
SUPPORT_USERNAME = "@Allawi04"
CHANNEL_USERNAME = "@FCJCV"

# إعدادات الخطوط
FONT_PATHS = {
    'arabic': 'fonts/arabic.ttf',
    'english': 'fonts/english.ttf'
}

# إعدادات المحادثة
CALC_GRADE1, CALC_GRADE2, CALC_GRADE3 = range(3)
PDF_SUMMARY = 1
ASK_QUESTION, ANSWER_QUESTION = range(2, 4)
VIP_LECTURE_TITLE, VIP_LECTURE_DESC, VIP_LECTURE_PRICE, VIP_LECTURE_FILE = range(4, 8)
ADMIN_CHARGE_USER, ADMIN_CHARGE_AMOUNT = range(8, 10)
ADMIN_DEDUCT_USER, ADMIN_DEDUCT_AMOUNT = range(10, 12)
ADMIN_VIP_DEDUCT_USER, ADMIN_VIP_DEDUCT_AMOUNT = range(12, 14)
ADMIN_CHANGE_PRICE = 14
ADMIN_BROADCAST = 15
ADMIN_ADD_MATERIAL_TITLE, ADMIN_ADD_MATERIAL_DESC, ADMIN_ADD_MATERIAL_STAGE, ADMIN_ADD_MATERIAL_FILE = range(16, 20)

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== قاعدة البيانات ======================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('yalla_nt3lm.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
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
            balance INTEGER DEFAULT 1000, -- هدية ترحيبية 1000 دينار
            invited_by INTEGER DEFAULT 0,
            invite_code TEXT UNIQUE,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول العمليات المالية
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT, -- charge, deduct, payment, refund, vip_purchase, lecture_sale
            service TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول درجات الإعفاء
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS exemption_grades (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            grade1 REAL,
            grade2 REAL,
            grade3 REAL,
            average REAL,
            is_exempt INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول الأسئلة (ساعدوني طالب)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_text TEXT,
            question_image TEXT,
            price_paid INTEGER,
            is_approved INTEGER DEFAULT 0,
            is_answered INTEGER DEFAULT 0,
            answer_text TEXT,
            answered_by INTEGER,
            answered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول المواد التعليمية
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_materials (
            material_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            stage TEXT,
            file_id TEXT,
            file_type TEXT,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        ''')
        
        # جدول المشتركين VIP
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vip_subscribers (
            vip_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expiry_date TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            auto_renew INTEGER DEFAULT 0
        )
        ''')
        
        # جدول محاضرات VIP
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vip_lectures (
            lecture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            file_id TEXT,
            title TEXT,
            description TEXT,
            price INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected, deleted
            views INTEGER DEFAULT 0,
            purchases INTEGER DEFAULT 0,
            rating_total REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_by INTEGER,
            approved_at TIMESTAMP
        )
        ''')
        
        # جدول مبيعات محاضرات VIP
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vip_sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER,
            student_id INTEGER,
            teacher_id INTEGER,
            price INTEGER,
            teacher_earnings INTEGER, -- 60% من السعر
            admin_earnings INTEGER, -- 40% من السعر
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول أرباح المدرسين
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vip_earnings (
            teacher_id INTEGER PRIMARY KEY,
            total_earnings INTEGER DEFAULT 0,
            available_balance INTEGER DEFAULT 0,
            withdrawn_balance INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول أرباح الإدارة
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_earnings (
            earning_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            amount INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول تقييم المحاضرات
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lecture_ratings (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER,
            user_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول إعدادات البوت
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
        ''')
        
        # جدول خدمات البوت (لتحديد ما إذا كانت مفعلة أم لا)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_services (
            service_id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT UNIQUE,
            display_name TEXT,
            is_active INTEGER DEFAULT 1,
            price INTEGER DEFAULT 1000
        )
        ''')
        
        # إدخال الإعدادات الافتراضية
        default_settings = [
            ('invite_reward', '500'),
            ('maintenance_mode', '0'),
            ('welcome_message', 'مرحباً بك في بوت "يلا نتعلم"! 🎓\nاحصل على 1000 دينار هدية ترحيبية!'),
            ('support_text', f'للتواصل والدعم الفني: {SUPPORT_USERNAME}'),
            ('channel_text', f'قناة البوت: {CHANNEL_USERNAME}')
        ]
        
        for key, value in default_settings:
            cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)
            ''', (key, value))
        
        # إدخال الخدمات الافتراضية
        default_services = [
            ('exemption_calc', '🎓 حساب درجة الإعفاء', 1, 1000),
            ('pdf_summary', '📚 تلخيص الملازم', 1, 1000),
            ('qna', '❓ سؤال وجواب بالذكاء الاصطناعي', 1, 1000),
            ('help_student', '👨‍🎓 ساعدوني طالب', 1, 1000),
            ('study_materials', '📖 ملازمي ومرشحاتي', 1, 0),
            ('vip_lectures', '🎬 محاضرات VIP', 1, 0),
            ('vip_subscribe', '👨‍🏫 اشتراك VIP', 1, 5000)
        ]
        
        for service_name, display_name, is_active, price in default_services:
            cursor.execute('''
            INSERT OR IGNORE INTO bot_services (service_name, display_name, is_active, price)
            VALUES (?, ?, ?, ?)
            ''', (service_name, display_name, is_active, price))
        
        self.conn.commit()
    
    # =============== دوال المستخدمين ===============
    def add_user(self, user_id, username, first_name, last_name, invited_by=0):
        """إضافة مستخدم جديد مع إصلاح مشكلة NoneType"""
        cursor = self.conn.cursor()
        invite_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
        
        # إصلاح: التحقق من قيمة invited_by
        invited_by_value = invited_by if invited_by is not None else 0
        
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, invited_by, invite_code, balance)
        VALUES (?, ?, ?, ?, ?, ?, 1000)
        ''', (user_id, username, first_name, last_name, invited_by_value, invite_code))
        
        # منح مكافأة للمدعو إذا كان هناك مدعٍ
        if invited_by_value > 0:
            invite_reward = self.get_setting('invite_reward')
            if invite_reward:
                reward_amount = int(invite_reward)
                self.add_balance(invited_by_value, reward_amount)
                cursor.execute('''
                INSERT INTO transactions (user_id, amount, type, service, description)
                VALUES (?, ?, ?, ?, ?)
                ''', (invited_by_value, reward_amount, 'charge', 'invite', f'مكافأة دعوة للمستخدم {user_id}'))
        
        self.conn.commit()
        return invite_code
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def update_user_activity(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_user_balance(self, user_id):
        user = self.get_user(user_id)
        return user['balance'] if user else 0
    
    def add_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def deduct_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?', 
                      (amount, user_id, amount))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def ban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def unban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_all_users(self, limit=100):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT ?', (limit,))
        return cursor.fetchall()
    
    def get_user_count(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM users')
        return cursor.fetchone()['count']
    
    def get_active_users_count(self):
        cursor = self.conn.cursor()
        cursor.execute('''SELECT COUNT(*) as count FROM users 
                         WHERE last_active > datetime('now', '-7 days')''')
        return cursor.fetchone()['count']
    
    # =============== دوال العمليات المالية ===============
    def add_transaction(self, user_id, amount, type_, service, description=""):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO transactions (user_id, amount, type, service, description)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, type_, service, description))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_user_transactions(self, user_id, limit=20):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()
    
    # =============== دوال درجات الإعفاء ===============
    def save_exemption_grade(self, user_id, grade1, grade2, grade3):
        cursor = self.conn.cursor()
        average = (grade1 + grade2 + grade3) / 3
        is_exempt = 1 if average >= 90 else 0
        
        cursor.execute('''
        INSERT INTO exemption_grades (user_id, grade1, grade2, grade3, average, is_exempt)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, grade1, grade2, grade3, average, is_exempt))
        self.conn.commit()
        return average, is_exempt
    
    def get_user_exemptions(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM exemption_grades 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    # =============== دوال الأسئلة (ساعدوني طالب) ===============
    def add_student_question(self, user_id, question_text, question_image, price_paid):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO student_questions (user_id, question_text, question_image, price_paid)
        VALUES (?, ?, ?, ?)
        ''', (user_id, question_text, question_image, price_paid))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_questions(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT sq.*, u.username, u.first_name 
        FROM student_questions sq
        JOIN users u ON sq.user_id = u.user_id
        WHERE sq.is_approved = 0 AND sq.is_answered = 0
        ORDER BY sq.created_at DESC
        ''')
        return cursor.fetchall()
    
    def get_approved_questions(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT sq.*, u.username, u.first_name 
        FROM student_questions sq
        JOIN users u ON sq.user_id = u.user_id
        WHERE sq.is_approved = 1 AND sq.is_answered = 0
        ORDER BY sq.created_at DESC
        ''')
        return cursor.fetchall()
    
    def approve_question(self, question_id, admin_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE student_questions 
        SET is_approved = 1 
        WHERE question_id = ?
        ''', (question_id,))
        self.conn.commit()
    
    def reject_question(self, question_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        DELETE FROM student_questions 
        WHERE question_id = ?
        ''', (question_id,))
        self.conn.commit()
    
    def answer_question(self, question_id, answer_text, answered_by):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE student_questions 
        SET is_answered = 1, answer_text = ?, answered_by = ?, answered_at = CURRENT_TIMESTAMP
        WHERE question_id = ?
        ''', (answer_text, answered_by, question_id))
        self.conn.commit()
    
    def get_question_by_id(self, question_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM student_questions WHERE question_id = ?', (question_id,))
        return cursor.fetchone()
    
    # =============== دوال المواد التعليمية ===============
    def add_study_material(self, title, description, stage, file_id, file_type, added_by):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO study_materials (title, description, stage, file_id, file_type, added_by)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, stage, file_id, file_type, added_by))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_study_materials(self, stage=None):
        cursor = self.conn.cursor()
        if stage:
            cursor.execute('''
            SELECT * FROM study_materials 
            WHERE stage = ? AND is_active = 1
            ORDER BY added_at DESC
            ''', (stage,))
        else:
            cursor.execute('SELECT * FROM study_materials WHERE is_active = 1 ORDER BY added_at DESC')
        return cursor.fetchall()
    
    def delete_study_material(self, material_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM study_materials WHERE material_id = ?', (material_id,))
        self.conn.commit()
    
    def toggle_study_material(self, material_id, is_active):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE study_materials SET is_active = ? WHERE material_id = ?', 
                      (is_active, material_id))
        self.conn.commit()
    
    # =============== دوال الخدمات ===============
    def get_service(self, service_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bot_services WHERE service_name = ?', (service_name,))
        return cursor.fetchone()
    
    def get_active_services(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bot_services WHERE is_active = 1 ORDER BY service_id')
        return cursor.fetchall()
    
    def toggle_service(self, service_name, is_active):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE bot_services SET is_active = ? WHERE service_name = ?', 
                      (is_active, service_name))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_service_price(self, service_name, price):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE bot_services SET price = ? WHERE service_name = ?', 
                      (price, service_name))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_service_price(self, service_name):
        service = self.get_service(service_name)
        if service:
            return service['price']
        return PRICE_CONFIG.get(service_name, 1000)
    
    def is_service_active(self, service_name):
        service = self.get_service(service_name)
        if service:
            return service['is_active'] == 1
        return True
    
    # =============== دوال VIP ===============
    def add_vip_subscriber(self, user_id, duration_days=30):
        cursor = self.conn.cursor()
        subscription_date = datetime.datetime.now()
        expiry_date = subscription_date + datetime.timedelta(days=duration_days)
        
        cursor.execute('''
        INSERT OR REPLACE INTO vip_subscribers (user_id, subscription_date, expiry_date, is_active)
        VALUES (?, ?, ?, 1)
        ''', (user_id, subscription_date, expiry_date))
        self.conn.commit()
    
    def is_vip_subscriber(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM vip_subscribers 
        WHERE user_id = ? AND is_active = 1 AND expiry_date > CURRENT_TIMESTAMP
        ''', (user_id,))
        return cursor.fetchone() is not None
    
    def get_vip_subscriber(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM vip_subscribers WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def cancel_vip_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE vip_subscribers SET is_active = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def renew_vip_subscription(self, user_id, duration_days=30):
        cursor = self.conn.cursor()
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
        cursor.execute('''
        UPDATE vip_subscribers 
        SET is_active = 1, expiry_date = ?, subscription_date = CURRENT_TIMESTAMP
        WHERE user_id = ?
        ''', (expiry_date, user_id))
        self.conn.commit()
    
    def get_all_vip_subscribers(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT vs.*, u.username, u.first_name 
        FROM vip_subscribers vs
        JOIN users u ON vs.user_id = u.user_id
        WHERE vs.is_active = 1
        ORDER BY vs.expiry_date DESC
        ''')
        return cursor.fetchall()
    
    def get_expiring_vip_subscriptions(self, days=3):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT vs.*, u.username, u.first_name 
        FROM vip_subscribers vs
        JOIN users u ON vs.user_id = u.user_id
        WHERE vs.is_active = 1 
        AND vs.expiry_date BETWEEN CURRENT_TIMESTAMP AND datetime(CURRENT_TIMESTAMP, ?)
        ''', (f'+{days} days',))
        return cursor.fetchall()
    
    # =============== دوال محاضرات VIP ===============
    def add_vip_lecture(self, teacher_id, file_id, title, description, price):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO vip_lectures (teacher_id, file_id, title, description, price, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (teacher_id, file_id, title, description, price))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_lectures(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT vl.*, u.username, u.first_name 
        FROM vip_lectures vl
        JOIN users u ON vl.teacher_id = u.user_id
        WHERE vl.status = 'pending'
        ORDER BY vl.created_at DESC
        ''')
        return cursor.fetchall()
    
    def get_approved_lectures(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT vl.*, u.username, u.first_name,
               (vl.rating_total / NULLIF(vl.rating_count, 0)) as avg_rating
        FROM vip_lectures vl
        JOIN users u ON vl.teacher_id = u.user_id
        WHERE vl.status = 'approved'
        ORDER BY vl.created_at DESC
        LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_teacher_lectures(self, teacher_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM vip_lectures 
        WHERE teacher_id = ? AND status != 'deleted'
        ORDER BY created_at DESC
        ''', (teacher_id,))
        return cursor.fetchall()
    
    def get_lecture_by_id(self, lecture_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT vl.*, u.username, u.first_name 
        FROM vip_lectures vl
        JOIN users u ON vl.teacher_id = u.user_id
        WHERE vl.lecture_id = ?
        ''', (lecture_id,))
        return cursor.fetchone()
    
    def approve_lecture(self, lecture_id, admin_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE vip_lectures 
        SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP
        WHERE lecture_id = ?
        ''', (admin_id, lecture_id))
        self.conn.commit()
    
    def reject_lecture(self, lecture_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE vip_lectures 
        SET status = 'rejected' 
        WHERE lecture_id = ?
        ''', (lecture_id,))
        self.conn.commit()
    
    def delete_lecture(self, lecture_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE vip_lectures 
        SET status = 'deleted' 
        WHERE lecture_id = ?
        ''', (lecture_id,))
        self.conn.commit()
    
    def update_lecture_stats(self, lecture_id):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE vip_lectures 
        SET views = views + 1 
        WHERE lecture_id = ?
        ''', (lecture_id,))
        self.conn.commit()
    
    # =============== دوال مبيعات VIP ===============
    def add_vip_sale(self, lecture_id, student_id, price):
        cursor = self.conn.cursor()
        
        # الحصول على معلومات المحاضرة
        lecture = self.get_lecture_by_id(lecture_id)
        if not lecture:
            return False
        
        teacher_id = lecture['teacher_id']
        teacher_earnings = int(price * 0.6)  # 60% للمدرس
        admin_earnings = int(price * 0.4)    # 40% للإدارة
        
        # تسجيل عملية البيع
        cursor.execute('''
        INSERT INTO vip_sales (lecture_id, student_id, teacher_id, price, teacher_earnings, admin_earnings)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (lecture_id, student_id, teacher_id, price, teacher_earnings, admin_earnings))
        
        # تحديث إحصائيات المحاضرة
        cursor.execute('''
        UPDATE vip_lectures 
        SET purchases = purchases + 1 
        WHERE lecture_id = ?
        ''', (lecture_id,))
        
        # تحديث أرباح المدرس
        cursor.execute('''
        INSERT OR REPLACE INTO vip_earnings (teacher_id, total_earnings, available_balance, withdrawn_balance)
        VALUES (?, 
                COALESCE((SELECT total_earnings FROM vip_earnings WHERE teacher_id = ?), 0) + ?,
                COALESCE((SELECT available_balance FROM vip_earnings WHERE teacher_id = ?), 0) + ?,
                COALESCE((SELECT withdrawn_balance FROM vip_earnings WHERE teacher_id = ?), 0))
        ''', (teacher_id, teacher_id, teacher_earnings, teacher_id, teacher_earnings, teacher_id, 0))
        
        # تحديث أرباح الإدارة
        cursor.execute('''
        INSERT INTO admin_earnings (source, amount, description)
        VALUES (?, ?, ?)
        ''', ('vip_lecture', admin_earnings, f'بيع محاضرة #{lecture_id} للمستخدم #{student_id}'))
        
        self.conn.commit()
        return True
    
    def get_vip_earnings(self, teacher_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM vip_earnings WHERE teacher_id = ?', (teacher_id,))
        return cursor.fetchone()
    
    def deduct_vip_earnings(self, teacher_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE vip_earnings 
        SET available_balance = available_balance - ?, withdrawn_balance = withdrawn_balance + ?
        WHERE teacher_id = ? AND available_balance >= ?
        ''', (amount, amount, teacher_id, amount))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_admin_earnings_stats(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT 
            SUM(CASE WHEN source = 'vip_lecture' THEN amount ELSE 0 END) as vip_earnings,
            SUM(CASE WHEN source != 'vip_lecture' THEN amount ELSE 0 END) as other_earnings,
            SUM(amount) as total_earnings
        FROM admin_earnings
        ''')
        return cursor.fetchone()
    
    # =============== دوال التقييمات ===============
    def add_lecture_rating(self, lecture_id, user_id, rating, comment=""):
        cursor = self.conn.cursor()
        
        # التحقق من عدم التقييم مسبقاً
        cursor.execute('SELECT * FROM lecture_ratings WHERE lecture_id = ? AND user_id = ?', 
                      (lecture_id, user_id))
        if cursor.fetchone():
            return False
        
        # إضافة التقييم
        cursor.execute('''
        INSERT INTO lecture_ratings (lecture_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?)
        ''', (lecture_id, user_id, rating, comment))
        
        # تحديث متوسط التقييم في المحاضرة
        cursor.execute('''
        UPDATE vip_lectures 
        SET rating_total = rating_total + ?, rating_count = rating_count + 1
        WHERE lecture_id = ?
        ''', (rating, lecture_id))
        
        self.conn.commit()
        return True
    
    def get_lecture_ratings(self, lecture_id, limit=20):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT lr.*, u.username, u.first_name 
        FROM lecture_ratings lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.lecture_id = ?
        ORDER BY lr.created_at DESC
        LIMIT ?
        ''', (lecture_id, limit))
        return cursor.fetchall()
    
    # =============== دوال الإعدادات ===============
    def get_setting(self, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = ?', (key,))
        result = cursor.fetchone()
        return result['setting_value'] if result else None
    
    def update_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO bot_settings (setting_key, setting_value)
        VALUES (?, ?)
        ''', (key, value))
        self.conn.commit()
    
    def get_maintenance_mode(self):
        mode = self.get_setting('maintenance_mode')
        return mode == '1' if mode else False
    
    def set_maintenance_mode(self, enabled):
        self.update_setting('maintenance_mode', '1' if enabled else '0')
    
    def get_invite_reward(self):
        reward = self.get_setting('invite_reward')
        return int(reward) if reward else 500
    
    def set_invite_reward(self, amount):
        self.update_setting('invite_reward', str(amount))
    
    def get_vip_subscription_price(self):
        price = self.get_setting('vip_subscription_price')
        return int(price) if price else PRICE_CONFIG['vip_subscription']
    
    def set_vip_subscription_price(self, price):
        self.update_setting('vip_subscription_price', str(price))

# ====================== تهيئة قاعدة البيانات ======================
db = Database()

# ====================== دوال المساعدة ======================
def format_currency(amount):
    """تنسيق العملة العراقية"""
    return f"{amount:,} دينار عراقي"

def format_date(dt):
    """تنسيق التاريخ"""
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %H:%M")

def is_admin(user_id):
    """التحقق إذا كان المستخدم مشرف"""
    return user_id == ADMIN_ID

def get_user_display_name(user):
    """الحصول على اسم العرض للمستخدم"""
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"المستخدم #{user.id}"

def format_arabic_text(text):
    """تنسيق النص العربي للعرض في التليجرام"""
    if not text:
        return ""
    
    # إعادة تشكيل النص العربي
    try:
        if PDF_SUPPORT:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        return text
    except:
        return text

# ====================== دوال الذكاء الاصطناعي ======================
async def generate_gemini_response(prompt):
    """استدعاء واجهة Gemini API"""
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "عذراً، لم أتمكن من توليد إجابة مناسبة."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "عذراً، حدث خطأ في الخادم. يرجى المحاولة لاحقاً."

async def summarize_pdf_with_gemini(pdf_text):
    """تلخيص PDF باستخدام Gemini"""
    prompt = f"""
    قم بتلخيص النص التالي مع الحفاظ على الأفكار الرئيسية:
    - احذف المعلومات غير المهمة
    - احتفظ بالمفاهيم الأساسية
    - نظم المعلومات بطريقة منطقية
    - استخدم لغة عربية سليمة وواضحة
    
    النص:
    {pdf_text[:4000]}  # تقليل النص لتفادي تجاوز الحدود
    """
    
    return await generate_gemini_response(prompt)

async def answer_question_with_gemini(question, context=""):
    """الإجابة على الأسئلة باستخدام Gemini"""
    prompt = f"""
    أنت مساعد تعليمي متخصص في المناهج العراقية.
    أجب على السؤال التالي بطريقة علمية ومنهجية ومناسبة للمستوى التعليمي:
    
    السؤال: {question}
    
    {f'السياق: {context}' if context else ''}
    
    قدم إجابة شاملة وواضحة مع أمثلة إذا لزم الأمر.
    """
    
    return await generate_gemini_response(prompt)

# ====================== دوال معالجة PDF ======================
def create_pdf_with_arabic_fonts(text, title="ملخص"):
    """إنشاء ملف PDF مع دعم الخطوط العربية"""
    if not PDF_SUPPORT:
        raise Exception("مكتبات PDF غير مثبتة")
    
    buffer = BytesIO()
    
    # إنشاء مستند PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    
    # إضافة أنماط للعربية
    arabic_style = ParagraphStyle(
        'ArabicStyle',
        parent=styles['Normal'],
        fontName='Arabic',
        fontSize=12,
        alignment=2,  # محاذاة لليمين للعربية
        rightIndent=0,
        wordWrap='RTL',
        spaceAfter=12
    )
    
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Heading1'],
        fontName='Arabic',
        fontSize=16,
        alignment=1,  # محاذاة وسط
        spaceAfter=24
    )
    
    # جمع المحتوى
    story = []
    
    # العنوان
    arabic_title = format_arabic_text(title)
    story.append(Paragraph(arabic_title, title_style))
    story.append(Spacer(1, 12))
    
    # النص
    paragraphs = text.split('\n')
    for para in paragraphs:
        if para.strip():
            arabic_para = format_arabic_text(para.strip())
            story.append(Paragraph(arabic_para, arabic_style))
            story.append(Spacer(1, 6))
    
    # بناء PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def extract_text_from_pdf(file_bytes):
    """استخراج النص من ملف PDF"""
    if not PYPDF2_SUPPORT:
        return "مكتبة PyPDF2 غير مثبتة. يرجى تثبيتها لتلخيص PDF."
    
    try:
        pdf_file = BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return f"حدث خطأ في استخراج النص من PDF: {str(e)}"

# ====================== دوال لوحة التحكم ======================
def get_admin_keyboard():
    """لوحة تحكم المشرف"""
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("💰 الشحن والخصم", callback_data="admin_finance")],
        [InlineKeyboardButton("⚙️ إدارة الخدمات", callback_data="admin_services")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🎬 إدارة VIP", callback_data="admin_vip")],
        [InlineKeyboardButton("📢 الإذاعة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔧 الإعدادات", callback_data="admin_settings")],
        [InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="start")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_users_management_keyboard():
    """إدارة المستخدمين"""
    keyboard = [
        [InlineKeyboardButton("👁️ عرض المستخدمين", callback_data="admin_users_list")],
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user")],
        [InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="admin_unban_user")],
        [InlineKeyboardButton("👑 رفع مشرف", callback_data="admin_promote_user")],
        [InlineKeyboardButton("📋 سجل المعاملات", callback_data="admin_transactions")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_finance_management_keyboard():
    """إدارة الشحن والخصم"""
    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")],
        [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct")],
        [InlineKeyboardButton("💳 خصم أرباح مدرس", callback_data="admin_deduct_vip")],
        [InlineKeyboardButton("📈 إحصائيات مالية", callback_data="admin_finance_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_vip_management_keyboard():
    """إدارة نظام VIP"""
    keyboard = [
        [InlineKeyboardButton("👥 المشتركون VIP", callback_data="admin_vip_subscribers")],
        [InlineKeyboardButton("⏳ المشتركون المنتهية", callback_data="admin_vip_expiring")],
        [InlineKeyboardButton("🎬 المحاضرات المنتظرة", callback_data="admin_vip_pending")],
        [InlineKeyboardButton("📊 إحصائيات VIP", callback_data="admin_vip_stats")],
        [InlineKeyboardButton("💰 أرباح المدرسين", callback_data="admin_vip_earnings")],
        [InlineKeyboardButton("🔧 إعدادات VIP", callback_data="admin_vip_settings")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_services_management_keyboard():
    """إدارة الخدمات"""
    keyboard = [
        [InlineKeyboardButton("🎓 حساب الإعفاء", callback_data="admin_service_exemption")],
        [InlineKeyboardButton("📚 تلخيص الملازم", callback_data="admin_service_summary")],
        [InlineKeyboardButton("❓ سؤال وجواب", callback_data="admin_service_qna")],
        [InlineKeyboardButton("👨‍🎓 ساعدوني طالب", callback_data="admin_service_help")],
        [InlineKeyboardButton("📖 ملازمي ومرشحاتي", callback_data="admin_service_materials")],
        [InlineKeyboardButton("🎬 محاضرات VIP", callback_data="admin_service_vip_lectures")],
        [InlineKeyboardButton("👨‍🏫 اشتراك VIP", callback_data="admin_service_vip_subscribe")],
        [InlineKeyboardButton("🔄 تفعيل/تعطيل خدمات", callback_data="admin_toggle_services")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(user_id):
    """القائمة الرئيسية - تعرض فقط الخدمات المفعلة"""
    keyboard = []
    
    # الحصول على الخدمات المفعلة فقط
    active_services = db.get_active_services()
    
    for service in active_services:
        service_name = service['service_name']
        display_name = service['display_name']
        
        if service_name == 'exemption_calc':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="service_exemption")])
        elif service_name == 'pdf_summary':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="service_summary")])
        elif service_name == 'qna':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="service_qna")])
        elif service_name == 'help_student':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="service_help")])
        elif service_name == 'study_materials':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="service_materials")])
        elif service_name == 'vip_lectures':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="vip_lectures")])
        elif service_name == 'vip_subscribe':
            keyboard.append([InlineKeyboardButton(display_name, callback_data="vip_subscribe")])
    
    # إضافة أزرار خاصة بـ VIP (إذا كان مشتركاً)
    if db.is_vip_subscriber(user_id):
        vip_services = [
            ("💰 رصيد أرباحي", "vip_my_earnings"),
            ("📤 رفع محاضرة", "vip_upload_lecture"),
            ("🎓 محاضراتي", "vip_my_lectures"),
        ]
        for display, callback in vip_services:
            keyboard.append([InlineKeyboardButton(display, callback_data=callback)])
    
    # أزرار المساعدة (دائماً تظهر)
    help_keyboard = [
        [InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
         InlineKeyboardButton("👥 دعوة صديق", callback_data="invite_friend")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
         InlineKeyboardButton("📞 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📢 قناة البوت", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")]
    ]
    keyboard.extend(help_keyboard)
    
    # زر لوحة التحكم للمشرف فقط
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("🛠️ لوحة التحكم", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# ====================== معالجات الأوامر ======================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start - مصحح"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # التحقق من وضع الصيانة
    if db.get_maintenance_mode() and not is_admin(user.id):
        maintenance_msg = "⚙️ البوت في وضع الصيانة حالياً. يرجى المحاولة لاحقاً."
        await update.message.reply_text(maintenance_msg)
        return
    
    # إضافة/تحديث المستخدم - مع إصلاح مشكلة NoneType
    invited_by = 0  # القيمة الافتراضية
    if context.args and len(context.args) > 0:
        try:
            invited_by = int(context.args[0])
        except (ValueError, TypeError):
            invited_by = 0  # في حالة خطأ في التحويل
    
    invite_code = db.add_user(user.id, user.username, user.first_name, user.last_name, invited_by)
    
    # التحقق إذا كان محظور
    user_data = db.get_user(user.id)
    if user_data and user_data['is_banned']:
        await update.message.reply_text("🚫 حسابك محظور. يرجى التواصل مع الدعم الفني.")
        return
    
    # تحديث آخر نشاط
    db.update_user_activity(user.id)
    
    # رسالة الترحيب
    welcome_msg = db.get_setting('welcome_message') or "مرحباً بك في بوت 'يلا نتعلم'! 🎓"
    support_text = db.get_setting('support_text') or f"للتواصل والدعم الفني: {SUPPORT_USERNAME}"
    channel_text = db.get_setting('channel_text') or f"قناة البوت: {CHANNEL_USERNAME}"
    
    full_message = f"""
    {welcome_msg}
    
    👤 أهلاً {user.first_name}!
    🎁 رصيدك الحالي: {format_currency(user_data['balance'])}
    
    📌 {support_text}
    📢 {channel_text}
    
    🔗 رابط الدعوة الخاص بك:
    https://t.me/{BOT_USERNAME.replace('@', '')}?start={user.id}
    
    📝 مكافأة الدعوة: {format_currency(db.get_invite_reward())}
    """
    
    await update.message.reply_text(
        full_message,
        reply_markup=get_main_menu_keyboard(user.id),
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    help_text = """
    📚 *دليل استخدام بوت "يلا نتعلم"*
    
    *الخدمات المتاحة:*
    
    🎓 *حساب درجة الإعفاء*
    - احسب معدلك ومعرفة إذا كنت معفياً
    
    📚 *تلخيص الملازم*
    - أرسل ملف PDF وسألخصه لك
    
    ❓ *سؤال وجواب بالذكاء الاصطناعي*
    - اسأل أي سؤال في أي مادة
    
    👨‍🎓 *ساعدوني طالب*
    - ادفع لطرح سوال ويتم الرد عليه من قبل الطلاب
    
    📖 *ملازمي ومرشحاتي*
    - مجموعة من الملازم والمرشحات المجانية
    
    🎬 *محاضرات VIP*
    - محاضرات مدفوعة من مدرسين متميزين
    
    *معلومات الدفع:*
    - كل خدمة بسعر محدد
    - العملة: الدينار العراقي
    - أقل سعر: 1000 دينار
    
    *للشحن:* راسل الدعم الفني @Allawi04
    
    *روابط مهمة:*
    - الدعم الفني: @Allawi04
    - قناة البوت: @FCJCV
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(update.effective_user.id)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رصيد المستخدم"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ حسابك غير مسجل. استخدم /start للتسجيل.")
        return
    
    balance_msg = f"""
    💰 *رصيدك الحالي*
    
    🏦 الرصيد: {format_currency(user_data['balance'])}
    
    🔗 رابط الدعوة الخاص بك:
    `https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_id}`
    
    🎁 مكافأة الدعوة: {format_currency(db.get_invite_reward())}
    
    📞 للشحن: {SUPPORT_USERNAME}
    """
    
    await update.message.reply_text(
        balance_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id)
    )

# ====================== معالجات الخدمات ======================
async def service_exemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة حساب درجة الإعفاء"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('exemption_calc'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من الرصيد
    service_price = db.get_service_price('exemption_calc')
    if user_data['balance'] < service_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي. سعر الخدمة: {format_currency(service_price)}\nرصيدك الحالي: {format_currency(user_data['balance'])}\n\nللشحن راسل: {SUPPORT_USERNAME}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # بدء عملية إدخال الدرجات
    context.user_data['exemption_service'] = True
    context.user_data['exemption_price'] = service_price
    
    instructions = """
    🎓 *حساب درجة الإعفاء*
    
    سأطلب منك إدخال 3 درجات (كل درجة على حدة):
    
    1. درجة الكورس الأول
    2. درجة الكورس الثاني  
    3. درجة الكورس الأخير
    
    *المعدل المطلوب للإعفاء:* 90 فأعلى
    
    ⚠️ *ملاحظة:* سيتم خصم {price} عند اكتمال العملية
    
    *أرسل الآن درجة الكورس الأول (رقم فقط):*
    """.format(price=format_currency(service_price))
    
    await query.edit_message_text(
        instructions,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return CALC_GRADE1

async def process_grade1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الأولى"""
    try:
        grade1 = float(update.message.text)
        if grade1 < 0 or grade1 > 100:
            await update.message.reply_text("❌ الدرجة يجب أن تكون بين 0 و 100. أعد إرسال الدرجة:")
            return CALC_GRADE1
        
        context.user_data['grade1'] = grade1
        await update.message.reply_text("✅ تم حفظ درجة الكورس الأول.\n\n*أرسل درجة الكورس الثاني:*", parse_mode=ParseMode.MARKDOWN)
        return CALC_GRADE2
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح. أعد إرسال الدرجة:")
        return CALC_GRADE1

async def process_grade2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الثانية"""
    try:
        grade2 = float(update.message.text)
        if grade2 < 0 or grade2 > 100:
            await update.message.reply_text("❌ الدرجة يجب أن تكون بين 0 و 100. أعد إرسال الدرجة:")
            return CALC_GRADE2
        
        context.user_data['grade2'] = grade2
        await update.message.reply_text("✅ تم حفظ درجة الكورس الثاني.\n\n*أرسل درجة الكورس الأخير:*", parse_mode=ParseMode.MARKDOWN)
        return CALC_GRADE3
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح. أعد إرسال الدرجة:")
        return CALC_GRADE2

async def process_grade3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الدرجة الثالثة وحساب النتيجة"""
    try:
        grade3 = float(update.message.text)
        if grade3 < 0 or grade3 > 100:
            await update.message.reply_text("❌ الدرجة يجب أن تكون بين 0 و 100. أعد إرسال الدرجة:")
            return CALC_GRADE3
        
        user_id = update.effective_user.id
        grade1 = context.user_data.get('grade1')
        grade2 = context.user_data.get('grade2')
        service_price = context.user_data.get('exemption_price')
        
        # خصم المبلغ
        if db.deduct_balance(user_id, service_price):
            db.add_transaction(user_id, -service_price, 'payment', 'exemption_calc', 'حساب درجة الإعفاء')
            
            # حساب المعدل والحفظ
            average, is_exempt = db.save_exemption_grade(user_id, grade1, grade2, grade3)
            
            # إعداد الرسالة
            if is_exempt:
                result_msg = "🎉 *مبروك! أنت معفي من المادة* 🎉"
                emoji = "✅"
            else:
                result_msg = "❌ *للأسف، لست معفياً من المادة*"
                emoji = "❌"
            
            final_msg = f"""
            {result_msg}
            
            {emoji} *النتيجة:*
            • درجة الكورس الأول: {grade1}
            • درجة الكورس الثاني: {grade2}
            • درجة الكورس الأخير: {grade3}
            • *المعدل النهائي:* {average:.2f}
            
            💰 *تم خصم:* {format_currency(service_price)}
            🏦 *رصيدك المتبقي:* {format_currency(db.get_user_balance(user_id))}
            
            📊 *الحد الأدنى للإعفاء:* 90
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 حساب مرة أخرى", callback_data="service_exemption")],
                [InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="start")]
            ]
            
            await update.message.reply_text(
                final_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # إرسال إشعار للمشرف
            if is_admin(ADMIN_ID):
                try:
                    admin_msg = f"""
                    📊 *عملية حساب إعفاء جديدة*
                    
                    👤 المستخدم: {update.effective_user.first_name} (ID: {user_id})
                    📈 المعدل: {average:.2f}
                    🎯 النتيجة: {'معفي' if is_exempt else 'غير معفي'}
                    💰 السعر: {format_currency(service_price)}
                    """
                    context.bot.send_message(ADMIN_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
                except:
                    pass
        else:
            await update.message.reply_text("❌ فشل في عملية الخصم. يرجى المحاولة لاحقاً.")
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('grade1', None)
        context.user_data.pop('grade2', None)
        context.user_data.pop('exemption_service', None)
        context.user_data.pop('exemption_price', None)
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح. أعد إرسال الدرجة:")
        return CALC_GRADE3

async def service_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة تلخيص الملازم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('pdf_summary'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من دعم PDF
    if not PDF_SUPPORT or not PYPDF2_SUPPORT:
        await query.edit_message_text(
            "❌ هذه الخدمة غير متاحة حالياً. المكتبات المطلوبة غير مثبتة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من الرصيد
    service_price = db.get_service_price('pdf_summary')
    if user_data['balance'] < service_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي. سعر الخدمة: {format_currency(service_price)}\nرصيدك الحالي: {format_currency(user_data['balance'])}\n\nللشحن راسل: {SUPPORT_USERNAME}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    instructions = f"""
    📚 *تلخيص الملازم*
    
    أرسل لي ملف PDF وسأقوم بتلخيصه لك باستخدام الذكاء الاصطناعي.
    
    ⚠️ *ملاحظات مهمة:*
    1. الملف يجب أن يكون بصيغة PDF
    2. الحد الأقصى للحجم: 20MB
    3. سأحذف المعلومات غير المهمة وأرتب النص
    4. سأعيده لك كملف PDF منظم
    
    💰 *سعر الخدمة:* {format_currency(service_price)}
    
    *أرسل ملف PDF الآن:*
    """
    
    context.user_data['summary_service'] = True
    context.user_data['summary_price'] = service_price
    
    await query.edit_message_text(
        instructions,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return PDF_SUMMARY

async def process_pdf_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف PDF للتلخيص"""
    user_id = update.effective_user.id
    
    # التحقق من وجود مستند PDF
    if not update.message.document or 'pdf' not in update.message.document.mime_type.lower():
        await update.message.reply_text("❌ يرجى إرسال ملف PDF فقط. حاول مرة أخرى:")
        return PDF_SUMMARY
    
    try:
        # تحميل الملف
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        
        await update.message.reply_text("⏳ جارٍ معالجة الملف واستخراج النص...")
        
        # استخراج النص من PDF
        pdf_text = extract_text_from_pdf(file_bytes)
        
        if not pdf_text or len(pdf_text.strip()) < 50:
            await update.message.reply_text("❌ لم أتمكن من استخراج نص كافٍ من الملف. يرجى إرسال ملف PDF يحتوي على نص.")
            return PDF_SUMMARY
        
        await update.message.reply_text("✅ تم استخراج النص. جارٍ التلخيص باستخدام الذكاء الاصطناعي...")
        
        # التحقق من الرصيد قبل الخصم
        service_price = context.user_data.get('summary_price', db.get_service_price('pdf_summary'))
        
        if not db.deduct_balance(user_id, service_price):
            await update.message.reply_text("❌ رصيدك غير كافي. يرجى الشحن وحاول مرة أخرى.")
            return ConversationHandler.END
        
        # خصم المبلغ
        db.add_transaction(user_id, -service_price, 'payment', 'pdf_summary', 'تلخيص PDF')
        
        # استخدام الذكاء الاصطناعي للتلخيص
        summary = await summarize_pdf_with_gemini(pdf_text)
        
        await update.message.reply_text("✅ تم التلخيص. جارٍ إنشاء ملف PDF منظم...")
        
        # إنشاء ملف PDF جديد
        try:
            pdf_buffer = create_pdf_with_arabic_fonts(summary, "ملخص المادة")
            
            # إرسال الملف
            await update.message.reply_document(
                document=InputFile(pdf_buffer, filename="ملخص_المادة.pdf"),
                caption=f"""
                ✅ *تم إنشاء الملخص بنجاح*
                
                📄 *تفاصيل:*
                • الملف الأصلي: {update.message.document.file_name}
                • سعر الخدمة: {format_currency(service_price)}
                • رصيدك المتبقي: {format_currency(db.get_user_balance(user_id))}
                
                📝 *ملاحظة:* تم استخدام الذكاء الاصطناعي لتحليل وتلخيص المحتوى.
                """,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as pdf_error:
            logger.error(f"PDF creation error: {pdf_error}")
            # إرسال الملخص كنص إذا فشل إنشاء PDF
            await update.message.reply_text(f"""
            ✅ *تم تلخيص الملف*
            
            📄 *تفاصيل:*
            • الملف الأصلي: {update.message.document.file_name}
            • سعر الخدمة: {format_currency(service_price)}
            • رصيدك المتبقي: {format_currency(db.get_user_balance(user_id))}
            
            📝 *الملخص:*
            {summary[:3000]}...
            """, parse_mode=ParseMode.MARKDOWN)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('summary_service', None)
        context.user_data.pop('summary_price', None)
        
        # إرسال إشعار للمشرف
        if is_admin(ADMIN_ID):
            try:
                admin_msg = f"""
                📚 *عملية تلخيص PDF جديدة*
                
                👤 المستخدم: {update.effective_user.first_name} (ID: {user_id})
                📄 الملف: {update.message.document.file_name}
                💰 السعر: {format_currency(service_price)}
                """
                context.bot.send_message(ADMIN_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"PDF summary error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def service_qna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة سؤال وجواب بالذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('qna'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من الرصيد
    service_price = db.get_service_price('qna')
    if user_data['balance'] < service_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي. سعر الخدمة: {format_currency(service_price)}\nرصيدك الحالي: {format_currency(user_data['balance'])}\n\nللشحن راسل: {SUPPORT_USERNAME}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    instructions = f"""
    ❓ *سؤال وجواب بالذكاء الاصطناعي*
    
    اسألني أي سؤال في أي مادة وسأجيبك باستخدام الذكاء الاصطناعي المتخصص في المناهج العراقية.
    
    *يمكنك إرسال:*
    1. سؤال نصي
    2. صورة تحتوي على سؤال
    3. أي استفسار دراسي
    
    ⚠️ *ملاحظة:* سيتم خصم {format_currency(service_price)} عند إرسال السؤال
    
    *أرسل سؤالك الآن:*
    """
    
    context.user_data['qna_service'] = True
    context.user_data['qna_price'] = service_price
    
    await query.edit_message_text(
        instructions,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ASK_QUESTION

async def process_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة السؤال"""
    user_id = update.effective_user.id
    service_price = context.user_data.get('qna_price', db.get_service_price('qna'))
    
    # التحقق من الرصيد
    if not db.deduct_balance(user_id, service_price):
        await update.message.reply_text("❌ رصيدك غير كافي. يرجى الشحن وحاول مرة أخرى.")
        return ConversationHandler.END
    
    # خصم المبلغ
    db.add_transaction(user_id, -service_price, 'payment', 'qna', 'سؤال وجواب بالذكاء الاصطناعي')
    
    # معالجة السؤال
    question_text = ""
    if update.message.text:
        question_text = update.message.text
    elif update.message.caption:
        question_text = update.message.caption
    
    await update.message.reply_text("🤔 جارٍ تحليل سؤالك والبحث عن إجابة مناسبة...")
    
    try:
        # استخدام الذكاء الاصطناعي للإجابة
        answer = await answer_question_with_gemini(question_text)
        
        # إرسال الإجابة
        response_msg = f"""
        ✅ *تمت الإجابة على سؤالك*
        
        ❓ *سؤالك:* {question_text[:200]}...
        
        💡 *الإجابة:*
        {answer}
        
        💰 *تم خصم:* {format_currency(service_price)}
        🏦 *رصيدك المتبقي:* {format_currency(db.get_user_balance(user_id))}
        
        📌 *ملاحظة:* الإجابة مبنية على الذكاء الاصطناعي المتخصص في المناهج التعليمية.
        """
        
        # تقسيم الإجابة إذا كانت طويلة
        if len(response_msg) > 4096:
            parts = textwrap.wrap(response_msg, width=4000)
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(part)
        else:
            await update.message.reply_text(response_msg, parse_mode=ParseMode.MARKDOWN)
        
        # إرسال إشعار للمشرف
        if is_admin(ADMIN_ID):
            try:
                admin_msg = f"""
                ❓ *عملية سؤال وجواب جديدة*
                
                👤 المستخدم: {update.effective_user.first_name} (ID: {user_id})
                📝 السؤال: {question_text[:100]}...
                💰 السعر: {format_currency(service_price)}
                """
                context.bot.send_message(ADMIN_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
        
    except Exception as e:
        logger.error(f"QnA error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى.")
        # إعادة الرصيد في حالة الخطأ
        db.add_balance(user_id, service_price)
        db.add_transaction(user_id, service_price, 'refund', 'qna', 'استرجاع رصيد بسبب خطأ')
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('qna_service', None)
    context.user_data.pop('qna_price', None)
    
    return ConversationHandler.END

async def service_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خدمة ساعدوني طالب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('help_student'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من الرصيد
    service_price = db.get_service_price('help_student')
    if user_data['balance'] < service_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي. سعر الخدمة: {format_currency(service_price)}\nرصيدك الحالي: {format_currency(user_data['balance'])}\n\nللشحن راسل: {SUPPORT_USERNAME}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    instructions = f"""
    👨‍🎓 *ساعدوني طالب*
    
    ادفع لطرح سؤال وسيتم نشره في قسم الأسئلة للإجابة عليه من قبل الطلاب الآخرين.
    
    *خطوات العملية:*
    1. تدفع سعر الخدمة
    2. ترسل سؤالك (نص أو صورة)
    3. أنا أوافق على السؤال
    4. ينشر في قسم الأسئلة
    5. الطلاب الآخرين يجيبون
    6. تحصل على الإجابة
    
    ⚠️ *ملاحظة:* سيتم خصم {format_currency(service_price)} عند إرسال السؤال
    
    *أرسل سؤالك الآن (نص أو صورة):*
    """
    
    context.user_data['help_service'] = True
    context.user_data['help_price'] = service_price
    
    await query.edit_message_text(
        instructions,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ASK_QUESTION

async def process_help_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة سؤال ساعدوني طالب"""
    user_id = update.effective_user.id
    service_price = context.user_data.get('help_price', db.get_service_price('help_student'))
    
    # التحقق من الرصيد
    if not db.deduct_balance(user_id, service_price):
        await update.message.reply_text("❌ رصيدك غير كافي. يرجى الشحن وحاول مرة أخرى.")
        return ConversationHandler.END
    
    # خصم المبلغ
    db.add_transaction(user_id, -service_price, 'payment', 'help_student', 'سؤال ساعدوني طالب')
    
    # معالجة السؤال
    question_text = ""
    question_image = None
    
    if update.message.text:
        question_text = update.message.text
    elif update.message.caption:
        question_text = update.message.caption
    
    if update.message.photo:
        question_image = update.message.photo[-1].file_id
    elif update.message.document:
        question_image = update.message.document.file_id
    
    # حفظ السؤال في قاعدة البيانات
    question_id = db.add_student_question(user_id, question_text, question_image, service_price)
    
    # إرسال تأكيد للمستخدم
    await update.message.reply_text(f"""
    ✅ *تم استلام سؤالك بنجاح*
    
    📝 *رقم سؤالك:* #{question_id}
    💰 *تم خصم:* {format_currency(service_price)}
    🏦 *رصيدك المتبقي:* {format_currency(db.get_user_balance(user_id))}
    
    ⏳ *جاري مراجعة السؤال من قبل الإدارة...*
    📌 ستتم إشعارتك عند الموافقة والنشر.
    """, parse_mode=ParseMode.MARKDOWN)
    
    # إرسال إشعار للمشرف للموافقة
    if is_admin(ADMIN_ID):
        try:
            approve_keyboard = [
                [
                    InlineKeyboardButton("✅ الموافقة", callback_data=f"approve_question_{question_id}"),
                    InlineKeyboardButton("❌ الرفض", callback_data=f"reject_question_{question_id}")
                ]
            ]
            
            admin_msg = f"""
            ❓ *سؤال جديد يحتاج موافقة*
            
            👤 المستخدم: {update.effective_user.first_name} (ID: {user_id})
            📝 السؤال: {question_text[:200]}...
            💰 السعر المدفوع: {format_currency(service_price)}
            
            #سؤال_{question_id}
            """
            
            if question_image:
                await context.bot.send_photo(
                    ADMIN_ID,
                    photo=question_image,
                    caption=admin_msg,
                    reply_markup=InlineKeyboardMarkup(approve_keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await context.bot.send_message(
                    ADMIN_ID,
                    admin_msg,
                    reply_markup=InlineKeyboardMarkup(approve_keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
    
    # تنظيف البيانات المؤقتة
    context.user_data.pop('help_service', None)
    context.user_data.pop('help_price', None)
    
    return ConversationHandler.END

async def service_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الملازم والمرشحات"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('study_materials'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(query.from_user.id)
        )
        return
    
    # الحصول على جميع المواد
    materials = db.get_study_materials()
    
    if not materials:
        await query.edit_message_text(
            "📭 لا توجد مواد متاحة حالياً.\n\nسيتم إضافة مواد جديدة قريباً.",
            reply_markup=get_main_menu_keyboard(query.from_user.id)
        )
        return
    
    # عرض المواد حسب المرحلة
    stages = {}
    for material in materials:
        stage = material['stage']
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(material)
    
    # إنشاء لوحة المفاتيح
    keyboard = []
    for stage in sorted(stages.keys()):
        keyboard.append([InlineKeyboardButton(f"📚 {stage}", callback_data=f"materials_stage_{stage}")])
    
    keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data="start")])
    
    await query.edit_message_text(
        "📖 *ملازمي ومرشحاتي*\n\nاختر المرحلة التعليمية:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ====================== دوال VIP ======================
async def vip_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض محاضرات VIP"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('vip_lectures'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(query.from_user.id)
        )
        return
    
    # الحصول على المحاضرات المعتمدة
    lectures = db.get_approved_lectures(limit=50)
    
    if not lectures:
        await query.edit_message_text(
            "🎬 *محاضرات VIP*\n\n📭 لا توجد محاضرات متاحة حالياً.\n\nيمكنك الاشتراك في VIP لرفع محاضراتك الخاصة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(query.from_user.id)
        )
        return
    
    # عرض أول محاضرة مع خيارات التنقل
    if 'lecture_index' not in context.user_data:
        context.user_data['lecture_index'] = 0
        context.user_data['current_lectures'] = [dict(l) for l in lectures]
    
    idx = context.user_data['lecture_index']
    lecture = context.user_data['current_lectures'][idx]
    
    # إنشاء لوحة المفاتيح
    keyboard = []
    
    # أزرار التنقل
    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="lecture_prev"))
    
    nav_buttons.append(InlineKeyboardButton(f"{idx+1}/{len(lectures)}", callback_data="noop"))
    
    if idx < len(lectures) - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="lecture_next"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # زر شراء المحاضرة
    if lecture['price'] > 0:
        price_text = f"💵 {format_currency(lecture['price'])}"
        keyboard.append([InlineKeyboardButton(f"🛒 شراء المحاضرة ({price_text})", callback_data=f"buy_lecture_{lecture['lecture_id']}")])
    else:
        keyboard.append([InlineKeyboardButton("📥 تحميل مجاني", callback_data=f"download_lecture_{lecture['lecture_id']}")])
    
    # زر تقييم المحاضرة
    keyboard.append([InlineKeyboardButton("⭐ تقييم المحاضرة", callback_data=f"rate_lecture_{lecture['lecture_id']}")])
    
    # زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="start")])
    
    # حساب متوسط التقييم
    avg_rating = 0
    if lecture['rating_count'] > 0:
        avg_rating = lecture['rating_total'] / lecture['rating_count']
    
    # عرض تفاصيل المحاضرة
    lecture_text = f"""
    🎬 *{lecture['title']}*
    
    👨‍🏫 *المدرس:* {lecture['first_name']} ({lecture['username'] or 'بدون يوزر'})
    
    📝 *الوصف:*
    {lecture['description']}
    
    💰 *السعر:* {format_currency(lecture['price']) if lecture['price'] > 0 else 'مجاني'}
    👁️ *المشاهدات:* {lecture['views']}
    🛒 *عمليات الشراء:* {lecture['purchases']}
    ⭐ *التقييم:* {avg_rating:.1f}/5 ({lecture['rating_count']} تقييم)
    📅 *تاريخ النشر:* {format_date(lecture['created_at'])}
    """
    
    await query.edit_message_text(
        lecture_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def vip_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # التحقق من تفعيل الخدمة
    if not db.is_service_active('vip_subscribe'):
        await query.edit_message_text(
            "⏸️ هذه الخدمة معطلة مؤقتاً من قبل الإدارة.",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # التحقق إذا كان مشترك بالفعل
    if db.is_vip_subscriber(user_id):
        vip_info = db.get_vip_subscriber(user_id)
        expiry_date = datetime.datetime.fromisoformat(vip_info['expiry_date'])
        
        await query.edit_message_text(
            f"""
            👑 *أنت مشترك في VIP بالفعل*
            
            📅 تاريخ الاشتراك: {format_date(vip_info['subscription_date'])}
            ⏳ تاريخ الانتهاء: {format_date(expiry_date)}
            
            🎬 يمكنك الآن:
            1. رفع محاضرات
            2. كسب الأرباح (60% من مبيعات محاضراتك)
            3. إدارة محاضراتك
            4. سحب أرباحك
            
            📞 للاستفسار: {SUPPORT_USERNAME}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # عرض معلومات الاشتراك
    subscription_price = db.get_service_price('vip_subscribe')
    
    keyboard = [
        [InlineKeyboardButton(f"💳 اشتراك شهري ({format_currency(subscription_price)})", callback_data="confirm_vip_subscription")],
        [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="vip_faq")],
        [InlineKeyboardButton("🔙 الرجوع", callback_data="start")]
    ]
    
    subscription_text = f"""
    👑 *اشتراك VIP للمدرسين*
    
    *المميزات:*
    ✅ رفع محاضرات فيديو (حد 100MB لكل محاضرة)
    ✅ تحديد سعر المحاضرة (أو مجانية)
    ✅ كسب 60% من مبيعات كل محاضرة
    ✅ إدارة محاضراتك (حذف/تعديل)
    ✅ سحب أرباحك عبر الدعم الفني
    ✅ تقييمات وتحليل أداء المحاضرات
    
    *الشروط:*
    1. المحتوى تعليمي ومناسب
    2. جودة مقبولة للفيديو
    3. عدم انتهاك حقوق النشر
    4. موافقة الإدارة على كل محاضرة
    
    *معلومات الدفع:*
    💰 السعر الشهري: {format_currency(subscription_price)}
    ⏳ المدة: 30 يوم
    🔄 تجديد تلقائي: غير مفعل
    
    📞 للاستفسار: {SUPPORT_USERNAME}
    """
    
    await query.edit_message_text(
        subscription_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_vip_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد اشتراك VIP"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    subscription_price = db.get_service_price('vip_subscribe')
    
    # التحقق من الرصيد
    user_balance = db.get_user_balance(user_id)
    if user_balance < subscription_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي.\n\nسعر الاشتراك: {format_currency(subscription_price)}\nرصيدك الحالي: {format_currency(user_balance)}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        return
    
    # خصم المبلغ
    if not db.deduct_balance(user_id, subscription_price):
        await query.edit_message_text("❌ فشل في عملية الاشتراك. يرجى المحاولة لاحقاً.")
        return
    
    # إضافة اشتراك VIP
    db.add_vip_subscriber(user_id, 30)
    db.add_transaction(user_id, -subscription_price, 'payment', 'vip_subscription', 'اشتراك VIP شهري')
    
    # تحديث رسالة الأصلية
    await query.edit_message_text(
        f"""
        ✅ *تم الاشتراك في VIP بنجاح*
        
        👑 *مبروك! أنت الآن مدرس VIP*
        
        📅 تاريخ الاشتراك: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
        ⏳ تاريخ الانتهاء: {(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M')}
        💰 السعر: {format_currency(subscription_price)}
        🏦 رصيدك المتبقي: {format_currency(db.get_user_balance(user_id))}
        
        🎬 *يمكنك الآن:*
        1. 📤 رفع محاضرة (زر "رفع محاضرة")
        2. 💰 كسب الأرباح (60% من المبيعات)
        3. 🎓 إدارة محاضراتك (زر "محاضراتي")
        4. 💸 سحب أرباحك (زر "رصيد أرباحي")
        
        📞 للاستفسار أو سحب الأرباح: {SUPPORT_USERNAME}
        """,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id)
    )
    
    # إرسال إشعار للمشرف
    if is_admin(ADMIN_ID):
        admin_msg = f"""
        👑 *اشتراك VIP جديد*
        
        👤 المستخدم: {query.from_user.first_name} (ID: {user_id})
        📅 تاريخ الاشتراك: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
        💰 السعر: {format_currency(subscription_price)}
        """
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode=ParseMode.MARKDOWN)

# ====================== لوحة التحكم - الإدارة المتقدمة ======================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المشرف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية للوصول إلى لوحة التحكم.")
        return
    
    admin_text = """
    🛠️ *لوحة التحكم - المشرف*
    
    *الإحصائيات السريعة:*
    """
    
    # إحصائيات سريعة
    total_users = db.get_user_count()
    active_users = db.get_active_users_count()
    
    # الحصول على إحصائيات VIP
    vip_subscribers = len(db.get_all_vip_subscribers())
    pending_lectures = len(db.get_pending_lectures())
    pending_questions = len(db.get_pending_questions())
    
    admin_text += f"""
    👥 المستخدمين: {total_users}
    📱 النشطين: {active_users}
    👑 مشتركي VIP: {vip_subscribers}
    ⏳ محاضرات منتظرة: {pending_lectures}
    ❓ أسئلة منتظرة: {pending_questions}
    
    *اختر القسم الذي تريد إدارته:*
    """
    
    await query.edit_message_text(
        admin_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )

async def admin_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الخدمات"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "⚙️ *إدارة الخدمات*\n\nاختر الخدمة التي تريد إدارتها:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_services_management_keyboard()
    )

async def admin_toggle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/تعطيل الخدمات"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    # الحصول على جميع الخدمات
    services = db.get_active_services()
    
    keyboard = []
    for service in services:
        service_name = service['service_name']
        display_name = service['display_name']
        is_active = service['is_active'] == 1
        
        status_icon = "✅" if is_active else "⏸️"
        callback_data = f"toggle_service_{service_name}_{0 if is_active else 1}"
        button_text = f"{status_icon} {display_name}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_services")])
    
    await query.edit_message_text(
        "🔄 *تفعيل/تعطيل الخدمات*\n\nاضغط على الخدمة لتفعيلها أو تعطيلها:\n\n✅ = مفعلة\n⏸️ = معطلة",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تفعيل/تعطيل الخدمة"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    # استخراج البيانات من callback_data
    data = query.data.replace("toggle_service_", "")
    parts = data.split("_")
    
    if len(parts) >= 2:
        service_name = parts[0]
        new_status = int(parts[1])
        
        # تحديث حالة الخدمة
        if db.toggle_service(service_name, new_status):
            status_text = "مفعلة" if new_status == 1 else "معطلة"
            await query.edit_message_text(
                f"✅ تم {status_text} الخدمة بنجاح.",
                reply_markup=get_admin_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ فشل في تحديث حالة الخدمة.",
                reply_markup=get_admin_keyboard()
            )
    else:
        await query.edit_message_text(
            "❌ بيانات غير صالحة.",
            reply_markup=get_admin_keyboard()
        )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال إذاعة للمستخدمين"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    await query.edit_message_text(
        "📢 *الإذاعة للمستخدمين*\n\nأرسل النص الذي تريد إرساله لجميع المستخدمين:",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_BROADCAST

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الإذاعة"""
    broadcast_text = update.message.text
    
    # الحصول على جميع المستخدمين
    users = db.get_all_users()
    
    await update.message.reply_text(f"📤 جارٍ إرسال الإذاعة لـ {len(users)} مستخدم...")
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                user['user_id'],
                f"📢 *إشعار من الإدارة:*\n\n{broadcast_text}",
                parse_mode=ParseMode.MARKDOWN
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ *تم إرسال الإذاعة*\n\n✅ الناجحة: {success_count}\n❌ الفاشلة: {fail_count}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )
    
    return ConversationHandler.END

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات البوت"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    keyboard = [
        [InlineKeyboardButton("🔧 وضع الصيانة", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("💰 تحديث مكافأة الدعوة", callback_data="update_invite_reward")],
        [InlineKeyboardButton("📊 عرض إحصائيات متقدمة", callback_data="admin_advanced_stats")],
        [InlineKeyboardButton("🗑️ تنظيف قاعدة البيانات", callback_data="admin_cleanup_db")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    
    # الحصول على حالة الصيانة الحالية
    maintenance_mode = db.get_maintenance_mode()
    maintenance_status = "✅ مفعل" if maintenance_mode else "❌ معطل"
    
    invite_reward = db.get_invite_reward()
    
    settings_text = f"""
    🔧 *إعدادات البوت*
    
    *الإعدادات الحالية:*
    ⚙️ وضع الصيانة: {maintenance_status}
    🎁 مكافأة الدعوة: {format_currency(invite_reward)}
    💰 سعر اشتراك VIP: {format_currency(db.get_vip_subscription_price())}
    
    *اختر الإعداد الذي تريد تعديله:*
    """
    
    await query.edit_message_text(
        settings_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفعيل/تعطيل وضع الصيانة"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    current_mode = db.get_maintenance_mode()
    new_mode = not current_mode
    
    db.set_maintenance_mode(new_mode)
    
    status_text = "مفعل" if new_mode else "معطل"
    
    await query.edit_message_text(
        f"✅ تم {status_text} وضع الصيانة.",
        reply_markup=get_admin_keyboard()
    )

# ====================== دوال إضافية ======================
async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دعوة صديق"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    invite_reward = db.get_invite_reward()
    invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_id}"
    
    invite_text = f"""
    👥 *دعوة صديق*
    
    🔗 *رابط الدعوة الخاص بك:*
    `{invite_link}`
    
    🎁 *مكافأة الدعوة:*
    • أنت: {format_currency(invite_reward)} لكل صديق يسجل
    • صديقك: 1000 دينار هدية ترحيبية
    
    *كيفية الدعوة:*
    1. أرسل الرابط لصديقك
    2. صديقك يضغط على الرابط
    3. يسجل في البوت باستخدام /start
    4. تحصل على {format_currency(invite_reward)} تلقائياً
    
    📊 *عدد المدعوين:* {db.get_user_count() - 1} مستخدم
    
    *ملاحظة:* المكافأة تمنح مرة واحدة لكل صديق.
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 نسخ الرابط", callback_data="copy_invite_link")],
        [InlineKeyboardButton("🔙 الرجوع", callback_data="start")]
    ]
    
    await query.edit_message_text(
        invite_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    # الحصول على إحصائيات إضافية
    transactions = db.get_user_transactions(user_id, limit=5)
    exemptions = db.get_user_exemptions(user_id)
    
    stats_text = f"""
    📊 *إحصائياتي*
    
    👤 *المعلومات الشخصية:*
    • الاسم: {user_data['first_name']} {user_data['last_name'] or ''}
    • اليوزر: {user_data['username'] or 'غير متوفر'}
    • الرصيد: {format_currency(user_data['balance'])}
    • تاريخ التسجيل: {format_date(user_data['created_at'])}
    
    📈 *النشاط:*
    • عدد عمليات حساب الإعفاء: {len(exemptions)}
    • آخر نشاط: {format_date(user_data['last_active'])}
    
    💰 *آخر العمليات:*
    """
    
    if transactions:
        for trans in transactions:
            emoji = "➕" if trans['amount'] > 0 else "➖"
            stats_text += f"\n{emoji} {format_currency(abs(trans['amount']))} - {trans['description']}"
    else:
        stats_text += "\n📭 لا توجد عمليات سابقة."
    
    if db.is_vip_subscriber(user_id):
        vip_info = db.get_vip_subscriber(user_id)
        expiry_date = datetime.datetime.fromisoformat(vip_info['expiry_date'])
        
        stats_text += f"""
        
        👑 *عضوية VIP:*
        • حالة: ✅ مفعل
        • تاريخ الانتهاء: {format_date(expiry_date)}
        """
        
        # إضافة إحصائيات VIP إذا كان مدرساً
        earnings = db.get_vip_earnings(user_id)
        if earnings:
            stats_text += f"""
            • إجمالي الأرباح: {format_currency(earnings['total_earnings'])}
            • رصيد قابل للسحب: {format_currency(earnings['available_balance'])}
            """
    
    stats_text += f"\n\n📞 الدعم الفني: {SUPPORT_USERNAME}"
    
    await query.edit_message_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(user_id)
    )

# ====================== معالجات كاليد باك ======================
async def approve_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على سؤال"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    question_id = int(query.data.replace("approve_question_", ""))
    
    # الموافقة على السؤال
    db.approve_question(question_id, query.from_user.id)
    
    await query.edit_message_text(
        f"✅ تمت الموافقة على السؤال #{question_id}",
        reply_markup=get_admin_keyboard()
    )

async def reject_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض سؤال"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    question_id = int(query.data.replace("reject_question_", ""))
    
    # رفض السؤال
    db.reject_question(question_id)
    
    await query.edit_message_text(
        f"❌ تم رفض السؤال #{question_id}",
        reply_markup=get_admin_keyboard()
    )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=get_main_menu_keyboard(user_id)
    )
    return ConversationHandler.END

# ====================== الدوال الرئيسية ======================
def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    print("🚀 بدء تشغيل بوت 'يلا نتعلم'...")
    print(f"🔑 توكن البوت: {BOT_TOKEN[:15]}...")
    print(f"👤 المطور: @Allawi04")
    print(f"🆔 ايدي المطور: {ADMIN_ID}")
    print(f"🔗 يوزر البوت: {BOT_USERNAME}")
    print(f"💬 الدعم الفني: {SUPPORT_USERNAME}")
    print(f"📢 قناة البوت: {CHANNEL_USERNAME}")
    
    # حذف Webhook السابق لمنع التعارض
    try:
        import asyncio
        import telegram
        
        # إنشاء تطبيق مؤقت لحذف Webhook
        temp_app = telegram.Bot(token=BOT_TOKEN)
        
        # محاولة حذف Webhook
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(temp_app.delete_webhook())
        print("✅ تم حذف Webhook السابق بنجاح")
    except Exception as e:
        print(f"⚠️  لم يتمكن من حذف Webhook: {e}")
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # معالج المحادثة لحساب الإعفاء
    exemption_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(service_exemption, pattern='^service_exemption$')],
        states={
            CALC_GRADE1: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_grade1)],
            CALC_GRADE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_grade2)],
            CALC_GRADE3: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_grade3)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # معالج المحادثة لتلخيص PDF
    pdf_summary_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(service_summary, pattern='^service_summary$')],
        states={
            PDF_SUMMARY: [MessageHandler(filters.Document.PDF, process_pdf_summary)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # معالج المحادثة لسؤال وجواب
    qna_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(service_qna, pattern='^service_qna$')],
        states={
            ASK_QUESTION: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, process_question)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # معالج المحادثة لساعدوني طالب
    help_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(service_help, pattern='^service_help$')],
        states={
            ASK_QUESTION: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, process_help_question)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # معالجات لوحة التحكم
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast, pattern='^admin_broadcast$')],
        states={
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    
    # إضافة معالجات المحادثة
    application.add_handler(exemption_conv_handler)
    application.add_handler(pdf_summary_conv_handler)
    application.add_handler(qna_conv_handler)
    application.add_handler(help_conv_handler)
    application.add_handler(broadcast_conv_handler)
    
    # إضافة معالجات الكاليد باك العامة
    application.add_handler(CallbackQueryHandler(service_materials, pattern='^service_materials$'))
    application.add_handler(CallbackQueryHandler(vip_lectures, pattern='^vip_lectures$'))
    application.add_handler(CallbackQueryHandler(vip_subscribe, pattern='^vip_subscribe$'))
    application.add_handler(CallbackQueryHandler(confirm_vip_subscription, pattern='^confirm_vip_subscription$'))
    
    application.add_handler(CallbackQueryHandler(invite_friend, pattern='^invite_friend$'))
    application.add_handler(CallbackQueryHandler(my_stats, pattern='^my_stats$'))
    
    # معالجات لوحة التحكم
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_services, pattern='^admin_services$'))
    application.add_handler(CallbackQueryHandler(admin_toggle_services, pattern='^admin_toggle_services$'))
    application.add_handler(CallbackQueryHandler(toggle_service_callback, pattern='^toggle_service_'))
    application.add_handler(CallbackQueryHandler(admin_settings, pattern='^admin_settings$'))
    application.add_handler(CallbackQueryHandler(toggle_maintenance, pattern='^toggle_maintenance$'))
    
    application.add_handler(CallbackQueryHandler(approve_question_callback, pattern='^approve_question_'))
    application.add_handler(CallbackQueryHandler(reject_question_callback, pattern='^reject_question_'))
    
    # معالج للعودة إلى القائمة الرئيسية
    application.add_handler(CallbackQueryHandler(start_command, pattern='^start$'))
    
    # معالج للرسائل النصية الأخرى
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_command))
    
    # إضافة معالج الأخطاء
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"حدث خطأ: {context.error}")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
                )
        except:
            pass
    
    application.add_error_handler(error_handler)
    
    # بدء البوت
    print("\n" + "="*50)
    print("🤖 البوت يعمل الآن! اضغط Ctrl+C لإيقافه")
    print("="*50 + "\n")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # حذف التحديثات القديمة
    )

if __name__ == '__main__':
    # إنشاء دليل للخطوط إذا لم يكن موجوداً
    os.makedirs('fonts', exist_ok=True)
    
    # التحقق من المكتبات
    if not PDF_SUPPORT:
        print("⚠️  تحذير: مكتبات PDF غير مثبتة. سيتم تعطيل ميزة تلخيص PDF.")
        print("📦 قم بتثبيت المكتبات المطلوبة:")
        print("   pip install reportlab arabic-reshaper python-bidi Pillow PyPDF2")
    
    # تشغيل البوت
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف البوت.")
    except Exception as e:
        print(f"\n\n❌ حدث خطأ: {e}")
        logger.error(f"خطأ في التشغيل: {e}")
