#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام متكامل للتعليم - "يلا نتعلم"
تم التطوير بواسطة: Allawi
الدعم الفني: @Allawi04
أيدي المشرف: 6130994941
"""

# ============================================
# المكتبات الأساسية
# ============================================
import os
import sys
import logging
import json
import asyncio
import sqlite3
import threading
import time
import random
import string
import hashlib
import re
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from functools import wraps
from collections import defaultdict
import base64
import io
import urllib.parse
import csv
from enum import Enum

# مكتبات تليجرام
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo,
    InputFile,
    Document,
    PhotoSize,
    InputMediaDocument,
    InputMediaPhoto,
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChatAdministrators,
    ChatPermissions
)
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    PicklePersistence,
    JobQueue
)
from telegram.error import TelegramError, BadRequest, NetworkError

# مكتبات الذكاء الاصطناعي وPDF
import google.generativeai as genai
from PyPDF2 import PdfReader, PdfWriter
import pdfkit
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from deep_translator import GoogleTranslator

# مكتبات إضافية
import requests
from bs4 import BeautifulSoup
import aiohttp
import qrcode
from io import BytesIO
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# إعدادات التكوين الأساسية
# ============================================

# توكن البوت - ضع التوكن الخاص بك هنا
TELEGRAM_BOT_TOKEN = "8481569753:AAHTdbWwu0BHmoo_iHPsye8RkTptWzfiQWU"

# مفتاح API لـ Gemini AI - ضع المفتاح الخاص بك هنا
GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"

# إعدادات المطور
ADMIN_USER_ID = 6130994941  # أيدي المطور
ADMIN_USERNAME = "@Allawi04"  # يوزر المطور

# إعدادات البوت
BOT_USERNAME = "@FC4Xbot"
BOT_NAME = "يلا نتعلم"
BOT_DESCRIPTION = "بوت تعليمي ذكي للطلاب العراقيين"

# إعدادات العملة
CURRENCY_NAME = "دينار عراقي"
CURRENCY_SYMBOL = "د.ع"
MINIMUM_SERVICE_PRICE = 1000
WELCOME_BONUS_AMOUNT = 1000

# إعدادات قاعدة البيانات
DATABASE_NAME = "learning_bot.db"
BACKUP_INTERVAL = 3600  # ساعة واحدة بالثواني

# إعدادات الملفات
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.txt'}
TEMP_DIR = "temp_files"
LOG_DIR = "logs"

# إعدادات الترجمة
TRANSLATION_LANGUAGES = {
    'ar': 'العربية',
    'en': 'الإنجليزية',
    'ku': 'الكردية'
}

# ============================================
# إعدادات التسجيل (Logging)
# ============================================

def setup_logging():
    """إعداد نظام التسجيل"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    log_filename = os.path.join(LOG_DIR, f"bot_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================
# نظام قاعدة البيانات المتقدم
# ============================================

class AdvancedDatabase:
    """نظام قاعدة بيانات متقدم مع نسخ احتياطي تلقائي"""
    
    def __init__(self, db_name: str = DATABASE_NAME):
        self.db_name = db_name
        self.connection = None
        self.cursor = None
        self.lock = threading.Lock()
        self.init_database()
        self.start_backup_scheduler()
    
    def init_database(self):
        """تهيئة جميع جداول قاعدة البيانات"""
        with self.lock:
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            
            # جدول المستخدمين
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone_number TEXT,
                    balance INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    invite_code TEXT UNIQUE,
                    invited_by INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    language_code TEXT DEFAULT 'ar',
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_premium INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    settings TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # جدول العمليات المالية
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    transaction_type TEXT,
                    description TEXT,
                    reference_id TEXT,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول استخدام الخدمات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_name TEXT,
                    service_type TEXT,
                    cost INTEGER,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول المواد التعليمية
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS educational_materials (
                    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    file_id TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    category TEXT,
                    subcategory TEXT,
                    stage TEXT,
                    subject TEXT,
                    uploaded_by INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    download_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    is_approved INTEGER DEFAULT 1,
                    tags TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (uploaded_by) REFERENCES users (user_id) ON DELETE SET NULL
                )
            ''')
            
            # جدول الإعدادات العامة
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER
                )
            ''')
            
            # جدول أسعار الخدمات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_prices (
                    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT UNIQUE,
                    service_code TEXT UNIQUE,
                    base_price INTEGER,
                    current_price INTEGER,
                    is_active INTEGER DEFAULT 1,
                    min_price INTEGER,
                    max_price INTEGER,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الإشعارات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    notification_type TEXT,
                    title TEXT,
                    message TEXT,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول الدعوات والإحالات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER,
                    invited_id INTEGER UNIQUE,
                    invite_code_used TEXT,
                    bonus_amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (inviter_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (invited_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول سجل الأخطاء
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    error_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL
                )
            ''')
            
            # جدول الإحصائيات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    stat_date DATE PRIMARY KEY,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0,
                    total_transactions INTEGER DEFAULT 0,
                    transaction_amount INTEGER DEFAULT 0,
                    service_usage_count INTEGER DEFAULT 0,
                    materials_downloaded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # إضافة الفهارس لتحسين الأداء
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_invite_code ON users(invite_code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_category ON educational_materials(category)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_stage ON educational_materials(stage)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)')
            
            # إضافة الإعدادات الافتراضية
            self.add_default_settings()
            self.add_default_service_prices()
            
            self.connection.commit()
            logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
    
    def add_default_settings(self):
        """إضافة الإعدادات الافتراضية للبوت"""
        default_settings = [
            ('bot_name', BOT_NAME, 'اسم البوت'),
            ('bot_username', BOT_USERNAME, 'يوزر البوت'),
            ('admin_user_id', str(ADMIN_USER_ID), 'أيدي المشرف الرئيسي'),
            ('admin_username', ADMIN_USERNAME, 'يوزر المشرف'),
            ('welcome_bonus', str(WELCOME_BONUS_AMOUNT), 'مكافأة الترحيب'),
            ('invite_bonus', '500', 'مكافأة دعوة صديق'),
            ('min_service_price', str(MINIMUM_SERVICE_PRICE), 'أقل سعر للخدمة'),
            ('currency_name', CURRENCY_NAME, 'اسم العملة'),
            ('currency_symbol', CURRENCY_SYMBOL, 'رمز العملة'),
            ('maintenance_mode', '0', 'وضع الصيانة (0=معطل, 1=مفعل)'),
            ('broadcast_enabled', '1', 'تفعيل البث'),
            ('auto_backup', '1', 'النسخ الاحتياطي التلقائي'),
            ('support_channel', 'https://t.me/+channel', 'رابط القناة الرسمية'),
            ('support_group', 'https://t.me/+group', 'رابط مجموعة الدعم'),
            ('payment_methods', 'دعم فني', 'طرق الدفع المتاحة'),
            ('terms_url', 'https://example.com/terms', 'رابط الشروط والأحكام'),
            ('privacy_url', 'https://example.com/privacy', 'رابط سياسة الخصوصية'),
            ('max_file_size', str(MAX_FILE_SIZE), 'الحجم الأقصى للملف'),
            ('daily_limit', '10', 'الحد اليومي للاستخدام'),
            ('language', 'ar', 'اللغة الافتراضية'),
            ('timezone', 'Asia/Baghdad', 'المنطقة الزمنية')
        ]
        
        for key, value, description in default_settings:
            self.cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, description)
                VALUES (?, ?, ?)
            ''', (key, value, description))
        
        self.connection.commit()
    
    def add_default_service_prices(self):
        """إضافة أسعار الخدمات الافتراضية"""
        default_services = [
            ('عفوية', 'exemption_calc', 1000, 1000, 500, 5000, 'حساب درجة العفوية'),
            ('تلخيص', 'pdf_summary', 1000, 1000, 500, 5000, 'تلخيص الملازم بالذكاء الاصطناعي'),
            ('أسئلة', 'qa_ai', 1000, 1000, 500, 5000, 'أسئلة وأجوبة بالذكاء الاصطناعي'),
            ('ملازم', 'materials', 1000, 1000, 500, 5000, 'ملازمي ومرشحاتي'),
            ('ترجمة', 'translation', 500, 500, 200, 2000, 'ترجمة النصوص'),
            ('تحويل', 'conversion', 300, 300, 100, 1000, 'تحويل الملفات'),
            ('شرح', 'explanation', 1500, 1500, 800, 8000, 'شرح الدروس')
        ]
        
        for name, code, base_price, current_price, min_price, max_price, description in default_services:
            self.cursor.execute('''
                INSERT OR IGNORE INTO service_prices 
                (service_name, service_code, base_price, current_price, min_price, max_price, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, code, base_price, current_price, min_price, max_price, description))
        
        self.connection.commit()
    
    def start_backup_scheduler(self):
        """بدء جدولة النسخ الاحتياطي التلقائي"""
        def backup_job():
            while True:
                time.sleep(BACKUP_INTERVAL)
                self.create_backup()
        
        backup_thread = threading.Thread(target=backup_job, daemon=True)
        backup_thread.start()
        logger.info("✅ تم تشغيل نظام النسخ الاحتياطي التلقائي")
    
    def create_backup(self):
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = "database_backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")
            
            # إنشاء نسخة من قاعدة البيانات
            with sqlite3.connect(backup_file) as backup_conn:
                self.connection.backup(backup_conn)
            
            # الاحتفاظ فقط بـ 7 نسخ احتياطية
            backups = sorted(Path(backup_dir).glob("backup_*.db"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
            
            logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"❌ فشل في إنشاء نسخة احتياطية: {e}")
            return None
    
    # ============ إدارة المستخدمين ============
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, language_code: str = 'ar') -> dict:
        """إضافة مستخدم جديد"""
        with self.lock:
            try:
                # إنشاء كود دعوة فريد
                invite_code = self.generate_invite_code()
                
                # إضافة المستخدم
                self.cursor.execute('''
                    INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, last_name, language_code, invite_code, balance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, language_code, invite_code, WELCOME_BONUS_AMOUNT))
                
                if self.cursor.rowcount > 0:
                    # تسجيل المكافأة الترحيبية
                    self.add_transaction(
                        user_id=user_id,
                        amount=WELCOME_BONUS_AMOUNT,
                        transaction_type='welcome_bonus',
                        description='مكافأة ترحيبية'
                    )
                    
                    # تحديث الإحصائيات
                    self.update_statistics('new_users', increment=1)
                    
                    logger.info(f"✅ تم إضافة مستخدم جديد: {user_id}")
                
                return self.get_user(user_id)
            except Exception as e:
                logger.error(f"❌ فشل في إضافة مستخدم: {e}")
                self.log_error(user_id, 'add_user', str(e))
                return None
    
    def get_user(self, user_id: int) -> dict:
        """الحصول على بيانات مستخدم"""
        with self.lock:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = self.cursor.fetchone()
            return dict(user) if user else None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """تحديث بيانات مستخدم"""
        with self.lock:
            try:
                if not kwargs:
                    return False
                
                set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [user_id]
                
                query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
                self.cursor.execute(query, values)
                
                self.connection.commit()
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في تحديث المستخدم: {e}")
                return False
    
    def update_balance(self, user_id: int, amount: int, transaction_type: str, description: str = "") -> bool:
        """تحديث رصيد المستخدم"""
        with self.lock:
            try:
                # تحديث الرصيد
                if amount > 0:
                    self.cursor.execute(
                        'UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?',
                        (amount, amount, user_id)
                    )
                else:
                    self.cursor.execute(
                        'UPDATE users SET balance = balance + ?, total_spent = total_spent + ABS(?) WHERE user_id = ?',
                        (amount, amount, user_id)
                    )
                
                # إضافة العملية
                self.add_transaction(user_id, amount, transaction_type, description)
                
                self.connection.commit()
                return True
            except Exception as e:
                logger.error(f"❌ فشل في تحديث الرصيد: {e}")
                return False
    
    def get_balance(self, user_id: int) -> int:
        """الحصول على رصيد المستخدم"""
        with self.lock:
            self.cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
    
    def get_all_users(self, limit: int = 100, offset: int = 0, filters: dict = None) -> list:
        """الحصول على جميع المستخدمين مع فلترة"""
        with self.lock:
            query = "SELECT * FROM users WHERE 1=1"
            params = []
            
            if filters:
                if 'is_banned' in filters:
                    query += " AND is_banned = ?"
                    params.append(filters['is_banned'])
                
                if 'is_premium' in filters:
                    query += " AND is_premium = ?"
                    params.append(filters['is_premium'])
                
                if 'min_balance' in filters:
                    query += " AND balance >= ?"
                    params.append(filters['min_balance'])
            
            query += " ORDER BY join_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            self.cursor.execute(query, params)
            users = self.cursor.fetchall()
            return [dict(user) for user in users]
    
    def search_users(self, search_term: str) -> list:
        """بحث عن مستخدمين"""
        with self.lock:
            search_term = f"%{search_term}%"
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE user_id LIKE ? OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                LIMIT 50
            ''', (search_term, search_term, search_term, search_term))
            
            users = self.cursor.fetchall()
            return [dict(user) for user in users]
    
    def ban_user(self, user_id: int, reason: str = "انتهاك القواعد") -> bool:
        """حظر مستخدم"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?
                ''', (reason, user_id))
                
                self.connection.commit()
                
                if self.cursor.rowcount > 0:
                    logger.info(f"🚫 تم حظر المستخدم: {user_id}")
                    return True
                return False
            except Exception as e:
                logger.error(f"❌ فشل في حظر المستخدم: {e}")
                return False
    
    def unban_user(self, user_id: int) -> bool:
        """إلغاء حظر مستخدم"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?
                ''', (user_id,))
                
                self.connection.commit()
                
                if self.cursor.rowcount > 0:
                    logger.info(f"✅ تم إلغاء حظر المستخدم: {user_id}")
                    return True
                return False
            except Exception as e:
                logger.error(f"❌ فشل في إلغاء حظر المستخدم: {e}")
                return False
    
    # ============ إدارة العمليات المالية ============
    
    def add_transaction(self, user_id: int, amount: int, transaction_type: str, 
                       description: str = "", reference_id: str = None) -> int:
        """إضافة عملية مالية"""
        with self.lock:
            try:
                reference_id = reference_id or self.generate_reference_id()
                
                self.cursor.execute('''
                    INSERT INTO transactions 
                    (user_id, amount, transaction_type, description, reference_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, amount, transaction_type, description, reference_id))
                
                transaction_id = self.cursor.lastrowid
                self.connection.commit()
                
                # تحديث الإحصائيات
                if transaction_type != 'internal':
                    self.update_statistics('total_transactions', increment=1)
                    self.update_statistics('transaction_amount', increment=amount)
                
                return transaction_id
            except Exception as e:
                logger.error(f"❌ فشل في إضافة عملية: {e}")
                self.log_error(user_id, 'add_transaction', str(e))
                return None
    
    def get_transactions(self, user_id: int = None, limit: int = 50, offset: int = 0) -> list:
        """الحصول على العمليات المالية"""
        with self.lock:
            if user_id:
                self.cursor.execute('''
                    SELECT * FROM transactions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (user_id, limit, offset))
            else:
                self.cursor.execute('''
                    SELECT * FROM transactions 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            transactions = self.cursor.fetchall()
            return [dict(t) for t in transactions]
    
    def get_daily_stats(self, date: datetime = None) -> dict:
        """الحصول على إحصائيات يومية"""
        with self.lock:
            date = date or datetime.now()
            date_str = date.strftime('%Y-%m-%d')
            
            stats = {
                'date': date_str,
                'total_users': 0,
                'new_users': 0,
                'active_users': 0,
                'total_transactions': 0,
                'transaction_amount': 0,
                'service_usage': 0,
                'materials_downloaded': 0
            }
            
            # إحصائيات المستخدمين
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?', (date_str,))
            stats['new_users'] = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(last_active) = ?', (date_str,))
            stats['active_users'] = self.cursor.fetchone()[0]
            
            # إحصائيات العمليات
            self.cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(amount), 0) 
                FROM transactions 
                WHERE DATE(created_at) = ? AND transaction_type != 'internal'
            ''', (date_str,))
            result = self.cursor.fetchone()
            stats['total_transactions'] = result[0]
            stats['transaction_amount'] = result[1]
            
            # إحصائيات الخدمات
            self.cursor.execute('SELECT COUNT(*) FROM service_usage WHERE DATE(created_at) = ?', (date_str,))
            stats['service_usage'] = self.cursor.fetchone()[0]
            
            return stats
    
    # ============ إدارة الخدمات ============
    
    def add_service_usage(self, user_id: int, service_name: str, service_type: str, 
                         cost: int, details: str = "") -> int:
        """تسجيل استخدام خدمة"""
        with self.lock:
            try:
                self.cursor.execute('''
                    INSERT INTO service_usage 
                    (user_id, service_name, service_type, cost, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, service_name, service_type, cost, details))
                
                usage_id = self.cursor.lastrowid
                self.connection.commit()
                
                # تحديث الإحصائيات
                self.update_statistics('service_usage_count', increment=1)
                
                return usage_id
            except Exception as e:
                logger.error(f"❌ فشل في تسجيل استخدام الخدمة: {e}")
                self.log_error(user_id, 'add_service_usage', str(e))
                return None
    
    def get_service_stats(self, period: str = 'daily') -> dict:
        """الحصول على إحصائيات الخدمات"""
        with self.lock:
            stats = {}
            
            if period == 'daily':
                self.cursor.execute('''
                    SELECT service_name, COUNT(*) as count, SUM(cost) as revenue
                    FROM service_usage 
                    WHERE DATE(created_at) = DATE('now')
                    GROUP BY service_name
                    ORDER BY count DESC
                ''')
            elif period == 'weekly':
                self.cursor.execute('''
                    SELECT service_name, COUNT(*) as count, SUM(cost) as revenue
                    FROM service_usage 
                    WHERE created_at >= DATE('now', '-7 days')
                    GROUP BY service_name
                    ORDER BY count DESC
                ''')
            else:  # الشهري
                self.cursor.execute('''
                    SELECT service_name, COUNT(*) as count, SUM(cost) as revenue
                    FROM service_usage 
                    WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                    GROUP BY service_name
                    ORDER BY count DESC
                ''')
            
            results = self.cursor.fetchall()
            
            for row in results:
                stats[row['service_name']] = {
                    'count': row['count'],
                    'revenue': row['revenue'],
                    'average_price': row['revenue'] / row['count'] if row['count'] > 0 else 0
                }
            
            return stats
    
    def get_service_price(self, service_code: str) -> int:
        """الحصول على سعر الخدمة"""
        with self.lock:
            self.cursor.execute('SELECT current_price FROM service_prices WHERE service_code = ?', (service_code,))
            result = self.cursor.fetchone()
            return result[0] if result else MINIMUM_SERVICE_PRICE
    
    def update_service_price(self, service_code: str, new_price: int) -> bool:
        """تحديث سعر الخدمة"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE service_prices 
                    SET current_price = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE service_code = ? AND ? BETWEEN min_price AND max_price
                ''', (new_price, service_code, new_price))
                
                self.connection.commit()
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في تحديث سعر الخدمة: {e}")
                return False
    
    # ============ إدارة المواد التعليمية ============
    
    def add_material(self, title: str, description: str, file_id: str, file_type: str,
                    category: str, stage: str, uploaded_by: int, **kwargs) -> int:
        """إضافة مادة تعليمية"""
        with self.lock:
            try:
                tags = kwargs.get('tags', '')
                metadata = json.dumps(kwargs.get('metadata', {}))
                
                self.cursor.execute('''
                    INSERT INTO educational_materials 
                    (title, description, file_id, file_type, category, stage, 
                     uploaded_by, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (title, description, file_id, file_type, category, stage, 
                      uploaded_by, tags, metadata))
                
                material_id = self.cursor.lastrowid
                self.connection.commit()
                
                logger.info(f"📚 تم إضافة مادة جديدة: {title}")
                return material_id
            except Exception as e:
                logger.error(f"❌ فشل في إضافة مادة: {e}")
                self.log_error(uploaded_by, 'add_material', str(e))
                return None
    
    def get_materials(self, filters: dict = None, limit: int = 20, offset: int = 0) -> list:
        """الحصول على المواد التعليمية مع فلترة"""
        with self.lock:
            query = "SELECT * FROM educational_materials WHERE is_approved = 1"
            params = []
            
            if filters:
                if 'category' in filters:
                    query += " AND category = ?"
                    params.append(filters['category'])
                
                if 'stage' in filters:
                    query += " AND stage = ?"
                    params.append(filters['stage'])
                
                if 'subject' in filters:
                    query += " AND subject = ?"
                    params.append(filters['subject'])
                
                if 'search' in filters:
                    query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term, search_term])
                
                if 'uploaded_by' in filters:
                    query += " AND uploaded_by = ?"
                    params.append(filters['uploaded_by'])
            
            query += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            self.cursor.execute(query, params)
            materials = self.cursor.fetchall()
            return [dict(m) for m in materials]
    
    def increment_download_count(self, material_id: int) -> bool:
        """زيادة عداد التنزيلات للمادة"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE educational_materials 
                    SET download_count = download_count + 1 
                    WHERE material_id = ?
                ''', (material_id,))
                
                self.connection.commit()
                
                # تحديث الإحصائيات
                self.update_statistics('materials_downloaded', increment=1)
                
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في تحديث عداد التنزيلات: {e}")
                return False
    
    def delete_material(self, material_id: int) -> bool:
        """حذف مادة تعليمية"""
        with self.lock:
            try:
                self.cursor.execute('DELETE FROM educational_materials WHERE material_id = ?', (material_id,))
                self.connection.commit()
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في حذف المادة: {e}")
                return False
    
    # ============ إدارة الإشعارات ============
    
    def add_notification(self, user_id: int, notification_type: str, 
                        title: str, message: str) -> int:
        """إضافة إشعار للمستخدم"""
        with self.lock:
            try:
                self.cursor.execute('''
                    INSERT INTO notifications 
                    (user_id, notification_type, title, message)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, notification_type, title, message))
                
                notification_id = self.cursor.lastrowid
                self.connection.commit()
                
                return notification_id
            except Exception as e:
                logger.error(f"❌ فشل في إضافة إشعار: {e}")
                return None
    
    def get_unread_notifications(self, user_id: int, limit: int = 10) -> list:
        """الحصول على الإشعارات غير المقروءة"""
        with self.lock:
            self.cursor.execute('''
                SELECT * FROM notifications 
                WHERE user_id = ? AND is_read = 0 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            notifications = self.cursor.fetchall()
            return [dict(n) for n in notifications]
    
    def mark_as_read(self, notification_id: int) -> bool:
        """تحديد إشعار كمقروء"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE notifications 
                    SET is_read = 1, read_at = CURRENT_TIMESTAMP 
                    WHERE notification_id = ?
                ''', (notification_id,))
                
                self.connection.commit()
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في تحديث حالة الإشعار: {e}")
                return False
    
    # ============ إدارة الإحالات ============
    
    def add_referral(self, inviter_id: int, invited_id: int, invite_code: str) -> int:
        """إضافة إحالة جديدة"""
        with self.lock:
            try:
                # التحقق من عدم تكرار الإحالة
                self.cursor.execute('SELECT * FROM referrals WHERE invited_id = ?', (invited_id,))
                if self.cursor.fetchone():
                    return None
                
                # الحصول على مكافأة الدعوة
                invite_bonus = self.get_setting('invite_bonus')
                bonus_amount = int(invite_bonus) if invite_bonus else 500
                
                # إضافة الإحالة
                self.cursor.execute('''
                    INSERT INTO referrals 
                    (inviter_id, invited_id, invite_code_used, bonus_amount)
                    VALUES (?, ?, ?, ?)
                ''', (inviter_id, invited_id, invite_code, bonus_amount))
                
                referral_id = self.cursor.lastrowid
                
                # تحديث عداد الإحالات للمدعو
                self.cursor.execute('''
                    UPDATE users 
                    SET referral_count = referral_count + 1 
                    WHERE user_id = ?
                ''', (inviter_id,))
                
                self.connection.commit()
                
                logger.info(f"👥 تم إضافة إحالة جديدة: {inviter_id} -> {invited_id}")
                return referral_id
            except Exception as e:
                logger.error(f"❌ فشل في إضافة إحالة: {e}")
                return None
    
    def complete_referral(self, invited_id: int) -> bool:
        """إكمال عملية الإحالة"""
        with self.lock:
            try:
                # العثور على الإحالة
                self.cursor.execute('''
                    SELECT * FROM referrals 
                    WHERE invited_id = ? AND status = 'pending'
                ''', (invited_id,))
                
                referral = self.cursor.fetchone()
                if not referral:
                    return False
                
                # تحديث حالة الإحالة
                self.cursor.execute('''
                    UPDATE referrals 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP 
                    WHERE referral_id = ?
                ''', (referral['referral_id'],))
                
                # منح المكافأة للمدعو
                self.update_balance(
                    user_id=invited_id,
                    amount=referral['bonus_amount'],
                    transaction_type='referral_bonus',
                    description=f'مكافأة دعوة من {referral["inviter_id"]}'
                )
                
                # منح المكافأة للمدعو إليه
                self.update_balance(
                    user_id=referral['inviter_id'],
                    amount=referral['bonus_amount'],
                    transaction_type='referral_bonus',
                    description=f'مكافأة لدعوة {invited_id}'
                )
                
                self.connection.commit()
                return True
            except Exception as e:
                logger.error(f"❌ فشل في إكمال الإحالة: {e}")
                return False
    
    # ============ إدارة الإعدادات ============
    
    def get_setting(self, key: str) -> str:
        """الحصول على إعداد"""
        with self.lock:
            self.cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = ?', (key,))
            result = self.cursor.fetchone()
            return result[0] if result else None
    
    def update_setting(self, key: str, value: str, updated_by: int = None) -> bool:
        """تحديث إعداد"""
        with self.lock:
            try:
                self.cursor.execute('''
                    UPDATE bot_settings 
                    SET setting_value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                    WHERE setting_key = ?
                ''', (value, updated_by, key))
                
                self.connection.commit()
                return self.cursor.rowcount > 0
            except Exception as e:
                logger.error(f"❌ فشل في تحديث الإعداد: {e}")
                return False
    
    def get_all_settings(self) -> dict:
        """الحصول على جميع الإعدادات"""
        with self.lock:
            self.cursor.execute('SELECT setting_key, setting_value FROM bot_settings')
            settings = self.cursor.fetchall()
            return {s['setting_key']: s['setting_value'] for s in settings}
    
    # ============ إدارة الأخطاء ============
    
    def log_error(self, user_id: int = None, error_type: str = None, 
                 error_message: str = None, error_details: str = None) -> int:
        """تسجيل خطأ"""
        with self.lock:
            try:
                self.cursor.execute('''
                    INSERT INTO error_logs 
                    (user_id, error_type, error_message, error_details)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, error_type, error_message, error_details))
                
                error_id = self.cursor.lastrowid
                self.connection.commit()
                
                return error_id
            except Exception as e:
                logger.error(f"❌ فشل في تسجيل الخطأ: {e}")
                return None
    
    # ============ إدارة الإحصائيات ============
    
    def update_statistics(self, stat_type: str, increment: int = 1) -> bool:
        """تحديث الإحصائيات"""
        with self.lock:
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                
                # التحقق من وجود إحصائية لهذا اليوم
                self.cursor.execute('SELECT * FROM statistics WHERE stat_date = ?', (today,))
                if not self.cursor.fetchone():
                    # إنشاء إحصائية جديدة لهذا اليوم
                    self.cursor.execute('''
                        INSERT INTO statistics (stat_date)
                        VALUES (?)
                    ''', (today,))
                
                # تحديث الإحصائية
                if hasattr(self, f'update_{stat_type}'):
                    getattr(self, f'update_{stat_type}')(today, increment)
                else:
                    # تحديث عام
                    self.cursor.execute(f'''
                        UPDATE statistics 
                        SET {stat_type} = {stat_type} + ? 
                        WHERE stat_date = ?
                    ''', (increment, today))
                
                self.connection.commit()
                return True
            except Exception as e:
                logger.error(f"❌ فشل في تحديث الإحصائيات: {e}")
                return False
    
    # ============ أدوات مساعدة ============
    
    def generate_invite_code(self, length: int = 8) -> str:
        """إنشاء كود دعوة فريد"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            
            # التحقق من عدم تكرار الكود
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE invite_code = ?', (code,))
            if self.cursor.fetchone()[0] == 0:
                return code
    
    def generate_reference_id(self, length: int = 12) -> str:
        """إنشاء رقم مرجعي فريد"""
        timestamp = int(time.time())
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"REF{timestamp}{random_part}"
    
    def get_user_count(self) -> int:
        """الحصول على عدد المستخدمين"""
        with self.lock:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0]
    
    def get_active_users_count(self, days: int = 7) -> int:
        """الحصول على عدد المستخدمين النشطين"""
        with self.lock:
            self.cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM service_usage 
                WHERE created_at >= DATE('now', ?)
            ''', (f'-{days} days',))
            return self.cursor.fetchone()[0]
    
    def get_total_revenue(self, period: str = 'monthly') -> int:
        """الحصول على إجمالي الإيرادات"""
        with self.lock:
            if period == 'daily':
                self.cursor.execute('''
                    SELECT COALESCE(SUM(cost), 0) 
                    FROM service_usage 
                    WHERE DATE(created_at) = DATE('now')
                ''')
            elif period == 'weekly':
                self.cursor.execute('''
                    SELECT COALESCE(SUM(cost), 0) 
                    FROM service_usage 
                    WHERE created_at >= DATE('now', '-7 days')
                ''')
            else:  # الشهري
                self.cursor.execute('''
                    SELECT COALESCE(SUM(cost), 0) 
                    FROM service_usage 
                    WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                ''')
            
            return self.cursor.fetchone()[0]
    
    def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        if self.connection:
            self.connection.close()
            logger.info("🔒 تم إغلاق قاعدة البيانات")

# إنشاء كائن قاعدة البيانات
db = AdvancedDatabase()

# ============================================
# نظام الذكاء الاصطناعي
# ============================================

class AISystem:
    """نظام الذكاء الاصطناعي المتكامل"""
    
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.model = None
        self.chat_sessions = {}
        self.init_ai()
    
    def init_ai(self):
        """تهيئة نظام الذكاء الاصطناعي"""
        try:
            genai.configure(api_key=self.api_key)
            
            # إنشاء نموذج الذكاء الاصطناعي
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "text/plain",
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                },
            ]
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info("✅ تم تهيئة نظام الذكاء الاصطناعي بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة الذكاء الاصطناعي: {e}")
            return False
    
    async def summarize_pdf(self, pdf_path: str, user_id: int) -> dict:
        """تلخيص ملف PDF باستخدام الذكاء الاصطناعي"""
        try:
            # قراءة ملف PDF
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                for page_num in range(min(total_pages, 50)):  # حد أقصى 50 صفحة
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n\n"
            
            if not text_content.strip():
                return {
                    'success': False,
                    'error': 'لا يمكن قراءة النص من ملف PDF'
                }
            
            # تقليل حجم النص إذا كان كبيراً
            if len(text_content) > 15000:
                text_content = text_content[:15000] + "..."
            
            # إنشاء تلميح للتلخيص
            prompt = f"""
            أنت معلم عراقي متخصص في المناهج التعليمية.
            قم بتلخيص النص التعليمي التالي بأسلوب أكاديمي مع التركيز على:
            
            1. النقاط الرئيسية والأفكار الأساسية
            2. التعريفات والمصطلحات المهمة
            3. القوانين والمعادلات الرياضية
            4. الاستنتاجات والتوصيات
            
            المطلوب:
            - التلخيص باللغة العربية الفصحى
            - تقسيم المحتوى إلى أقسام واضحة
            - استخدام العناوين الرئيسية والفرعية
            - تضمين الأمثلة التوضيحية إن وجدت
            - كتابة النقاط المهمة بشكل مرتب
            
            النص المراد تلخيصه:
            {text_content}
            
            قدم التلخيص بشكل منظم ومنسق مع مراعاة التسلسل المنطقي.
            """
            
            # استخدام الذكاء الاصطناعي للتلخيص
            response = await self.generate_text(prompt)
            
            if not response['success']:
                return response
            
            return {
                'success': True,
                'summary': response['text'],
                'original_length': len(text_content),
                'summary_length': len(response['text'])
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في تلخيص PDF: {e}")
            return {
                'success': False,
                'error': f'خطأ في معالجة الملف: {str(e)}'
            }
    
    async def answer_question(self, question: str, context: str = "", user_id: int = None) -> dict:
        """الإجابة على الأسئلة باستخدام الذكاء الاصطناعي"""
        try:
            # إنشاء تلميح للإجابة
            prompt = f"""
            أنت مساعد تعليمي ذكي للطلاب العراقيين.
            مهمتك الإجابة على الأسئلة التعليمية بدقة وبشكل مفصل.
            
            توجيهات:
            1. أجب باللغة العربية الفصحى
            2. ركز على المنهج العراقي إن أمكن
            3. قدم إجابة شاملة ومفصلة
            4. رتب الإجابة بشكل منطقي
            5. استخدم الأمثلة التوضيحية
            6. اذكر المصادر إن كنت تعرفها
            
            السؤال: {question}
            
            {f'السياق: {context}' if context else ''}
            
            قدم الإجابة بشكل منظم مع العناوين الفرعية إذا لزم الأمر.
            """
            
            # استخدام الذكاء الاصطناعي للإجابة
            response = await self.generate_text(prompt)
            
            if not response['success']:
                return response
            
            # تحسين تنسيق الإجابة
            formatted_answer = self.format_answer(response['text'])
            
            return {
                'success': True,
                'answer': formatted_answer,
                'sources': [],
                'confidence': 0.85
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإجابة على السؤال: {e}")
            return {
                'success': False,
                'error': f'خطأ في معالجة السؤال: {str(e)}'
            }
    
    async def analyze_image_question(self, image_path: str, question: str = None) -> dict:
        """تحليل صورة تحتوي على سؤال"""
        try:
            # قراءة الصورة
            image = Image.open(image_path)
            
            # استخدام OCR لاستخراج النص
            text = pytesseract.image_to_string(image, lang='ara+eng')
            
            if not text.strip():
                return {
                    'success': False,
                    'error': 'لا يمكن قراءة النص من الصورة'
                }
            
            # استخدام الذكاء الاصطناعي للإجابة
            prompt = f"""
            هذا نص تم استخراجه من صورة لسؤال تعليمي:
            
            النص: {text}
            
            {'السؤال الإضافي: ' + question if question else ''}
            
            قم بتحليل النص والإجابة على السؤال بشكل تعليمي دقيق.
            """
            
            response = await self.generate_text(prompt)
            
            if not response['success']:
                return response
            
            return {
                'success': True,
                'extracted_text': text,
                'answer': response['text']
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل صورة السؤال: {e}")
            return {
                'success': False,
                'error': f'خطأ في معالجة الصورة: {str(e)}'
            }
    
    async def generate_text(self, prompt: str, max_retries: int = 3) -> dict:
        """إنشاء نص باستخدام الذكاء الاصطناعي"""
        for attempt in range(max_retries):
            try:
                if not self.model:
                    self.init_ai()
                    if not self.model:
                        return {
                            'success': False,
                            'error': 'نظام الذكاء الاصطناعي غير متاح'
                        }
                
                # إنشاء المحتوى
                response = self.model.generate_content(prompt)
                
                if not response or not response.text:
                    return {
                        'success': False,
                        'error': 'لا توجد استجابة من الذكاء الاصطناعي'
                    }
                
                return {
                    'success': True,
                    'text': response.text,
                    'model': 'gemini-1.5-pro',
                    'attempt': attempt + 1
                }
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"❌ فشل في إنشاء النص بعد {max_retries} محاولات: {e}")
                    return {
                        'success': False,
                        'error': f'فشل في الاتصال بالذكاء الاصطناعي: {str(e)}'
                    }
                
                await asyncio.sleep(1)  # انتظار قبل إعادة المحاولة
    
    def format_answer(self, answer: str) -> str:
        """تنسيق الإجابة بشكل جميل"""
        # إضافة تنسيقات تحسين العرض
        formatted = answer.strip()
        
        # إضافة فواصل بين الأقسام
        formatted = re.sub(r'\n\s*\n\s*\n+', '\n\n', formatted)
        
        # تحسين العناوين
        formatted = re.sub(r'^(#+\s*.+)$', r'🔹 \1', formatted, flags=re.MULTILINE)
        
        # إضافة تنسيق للنقاط
        formatted = re.sub(r'^\d+[\.\)]\s*', '• ', formatted, flags=re.MULTILINE)
        
        return formatted
    
    def get_chat_session(self, user_id: int):
        """الحصول على جلسة محادثة للمستخدم"""
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = self.model.start_chat(history=[])
        
        return self.chat_sessions[user_id]

# إنشاء كائن الذكاء الاصطناعي
ai_system = AISystem()

# ============================================
# نظام ملفات PDF المتقدم
# ============================================

class PDFSystem:
    """نظام معالجة وإنشاء ملفات PDF"""
    
    def __init__(self):
        self.setup_fonts()
        self.temp_dir = TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def setup_fonts(self):
        """إعداد الخطوط العربية والإنجليزية"""
        try:
            # محاولة تسجيل خطوط عربية (يجب تثبيتها على النظام)
            font_paths = [
                '/usr/share/fonts/truetype/arabic/arial.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/System/Library/Fonts/Supplemental/Arial.ttf',
                'C:/Windows/Fonts/arial.ttf'
            ]
            
            arabic_font_found = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Arabic', font_path))
                        arabic_font_found = True
                        logger.info(f"✅ تم تسجيل الخط العربي: {font_path}")
                        break
                    except:
                        continue
            
            if not arabic_font_found:
                # استخدام خط افتراضي
                pdfmetrics.registerFont(TTFont('Arabic', 'Helvetica'))
                logger.warning("⚠️ استخدام خط افتراضي للعربية")
            
            # تسجيل خط إنجليزي
            pdfmetrics.registerFont(TTFont('English', 'Helvetica'))
            
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إعداد الخطوط: {e}")
            return False
    
    def create_summary_pdf(self, summary_text: str, original_filename: str, 
                          user_id: int, metadata: dict = None) -> str:
        """إنشاء ملف PDF مخرص"""
        try:
            # إنشاء اسم ملف فريد
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = re.sub(r'[^\w\-_]', '', original_filename.replace('.pdf', ''))
            output_filename = f"ملخص_{safe_filename}_{timestamp}.pdf"
            output_path = os.path.join(self.temp_dir, output_filename)
            
            # إعداد أنماط النص
            styles = getSampleStyleSheet()
            
            # أنماط مخصصة للعربية
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName='Arabic',
                fontSize=16,
                textColor=colors.HexColor('#2C3E50'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontName='Arabic',
                fontSize=14,
                textColor=colors.HexColor('#34495E'),
                spaceAfter=15,
                alignment=TA_RIGHT
            )
            
            arabic_style = ParagraphStyle(
                'ArabicText',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=12,
                textColor=colors.HexColor('#2C3E50'),
                spaceAfter=10,
                alignment=TA_RIGHT,
                leading=18
            )
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                textColor=colors.HexColor('#7F8C8D'),
                alignment=TA_CENTER
            )
            
            # إنشاء مستند PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50,
                title=f"ملخص: {original_filename}"
            )
            
            # بناء محتوى PDF
            story = []
            
            # العنوان الرئيسي
            title_text = f"<b>📚 ملخص: {original_filename}</b>"
            story.append(Paragraph(format_arabic_text(title_text), title_style))
            story.append(Spacer(1, 10))
            
            # معلومات المستند
            info_text = f"""
            <b>تاريخ التلخيص:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
            <b>أداة التلخيص:</b> بوت {BOT_NAME}<br/>
            <b>التقنية المستخدمة:</b> الذكاء الاصطناعي المتقدم<br/>
            <b>رقم المرجع:</b> REF{timestamp}{user_id}
            """
            story.append(Paragraph(format_arabic_text(info_text), subtitle_style))
            story.append(Spacer(1, 30))
            
            # المحتوى المخرص
            content_title = "<b>📝 المحتوى المخرص:</b>"
            story.append(Paragraph(format_arabic_text(content_title), subtitle_style))
            story.append(Spacer(1, 10))
            
            # تقسيم النص إلى فقرات
            paragraphs = summary_text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # تحسين تنسيق الفقرات
                    formatted_para = para.strip()
                    
                    # إضافة تنسيق للعناوين الفرعية
                    if formatted_para.startswith('###'):
                        formatted_para = formatted_para.replace('###', '').strip()
                        story.append(Paragraph(f"<b>🔸 {format_arabic_text(formatted_para)}</b>", subtitle_style))
                    elif formatted_para.startswith('##'):
                        formatted_para = formatted_para.replace('##', '').strip()
                        story.append(Paragraph(f"<b>🔹 {format_arabic_text(formatted_para)}</b>", subtitle_style))
                    elif formatted_para.startswith('#'):
                        formatted_para = formatted_para.replace('#', '').strip()
                        story.append(Paragraph(f"<b>📌 {format_arabic_text(formatted_para)}</b>", subtitle_style))
                    else:
                        story.append(Paragraph(format_arabic_text(formatted_para), arabic_style))
                    
                    story.append(Spacer(1, 8))
            
            # إضافة فواصل بين الأقسام
            story.append(PageBreak())
            
            # قسم المعلومات الإضافية
            if metadata:
                metadata_title = "<b>📊 معلومات إضافية:</b>"
                story.append(Paragraph(format_arabic_text(metadata_title), subtitle_style))
                story.append(Spacer(1, 15))
                
                metadata_items = []
                for key, value in metadata.items():
                    if value:
                        metadata_items.append([
                            Paragraph(format_arabic_text(str(key)), arabic_style),
                            Paragraph(format_arabic_text(str(value)), arabic_style)
                        ])
                
                if metadata_items:
                    metadata_table = Table(metadata_items, colWidths=[100, 300])
                    metadata_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
                        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Arabic'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7'))
                    ]))
                    story.append(metadata_table)
            
            story.append(Spacer(1, 40))
            
            # تذييل الصفحة
            footer_text = f"""
            <i>تم إنشاء هذا الملخص تلقائياً بواسطة بوت {BOT_NAME}<br/>
            للاستفسارات والدعم: {db.get_setting('support_username') or ADMIN_USERNAME}<br/>
            جميع الحقوق محفوظة © {datetime.now().year}</i>
            """
            story.append(Paragraph(format_arabic_text(footer_text), footer_style))
            
            # بناء ملف PDF
            doc.build(story)
            
            logger.info(f"✅ تم إنشاء ملف PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء PDF: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """استخراج النص من ملف PDF"""
        try:
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n\n"
            
            return text_content.strip()
        except Exception as e:
            logger.error(f"❌ خطأ في استخراج النص من PDF: {e}")
            return ""
    
    def create_simple_pdf(self, content: str, filename: str = "document.pdf") -> str:
        """إنشاء ملف PDF بسيط"""
        try:
            output_path = os.path.join(self.temp_dir, filename)
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )
            
            styles = getSampleStyleSheet()
            arabic_style = ParagraphStyle(
                'SimpleArabic',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=12,
                alignment=TA_RIGHT
            )
            
            story = []
            story.append(Paragraph(format_arabic_text(content), arabic_style))
            
            doc.build(story)
            return output_path
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء PDF بسيط: {e}")
            return None
    
    def cleanup_temp_files(self, hours_old: int = 24):
        """تنظيف الملفات المؤقتة القديمة"""
        try:
            cutoff_time = time.time() - (hours_old * 3600)
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    if os.path.getctime(file_path) < cutoff_time:
                        os.remove(file_path)
                        logger.debug(f"🗑️ تم حذف الملف المؤقت: {filename}")
            
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الملفات المؤقتة: {e}")
            return False

# إنشاء كائن نظام PDF
pdf_system = PDFSystem()

# ============================================
# أدوات مساعدة
# ============================================

def format_arabic_text(text: str) -> str:
    """تنسيق النص العربي للعرض"""
    try:
        if not text:
            return ""
        
        # إعادة تشكيل النص العربي
        reshaped_text = arabic_reshaper.reshape(text)
        
        # معالجة النص ثنائي الاتجاه
        bidi_text = get_display(reshaped_text)
        
        return bidi_text
    except Exception as e:
        logger.warning(f"⚠️ خطأ في تنسيق النص العربي: {e}")
        return text

def format_number(number: int) -> str:
    """تنسيق الأرقام بفواصل"""
    try:
        return f"{number:,}"
    except:
        return str(number)

def format_currency(amount: int) -> str:
    """تنسيق المبالغ المالية"""
    return f"{format_number(amount)} {CURRENCY_SYMBOL}"

def format_date(date_str: str, format_type: str = "full") -> str:
    """تنسيق التواريخ"""
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        
        if format_type == "full":
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "date":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time":
            return dt.strftime("%H:%M")
        elif format_type == "relative":
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 365:
                return f"قبل {diff.days // 365} سنة"
            elif diff.days > 30:
                return f"قبل {diff.days // 30} شهر"
            elif diff.days > 0:
                return f"قبل {diff.days} يوم"
            elif diff.seconds > 3600:
                return f"قبل {diff.seconds // 3600} ساعة"
            elif diff.seconds > 60:
                return f"قبل {diff.seconds // 60} دقيقة"
            else:
                return "الآن"
        else:
            return str(dt)
    except Exception as e:
        logger.warning(f"⚠️ خطأ في تنسيق التاريخ: {e}")
        return date_str

def is_admin(user_id: int) -> bool:
    """التحقق إذا كان المستخدم مشرفاً"""
    return user_id == ADMIN_USER_ID

def admin_only(func):
    """ديكوراتور للتحقق من صلاحيات المشرف"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("⛔ هذا الأمر للمشرفين فقط!", show_alert=True)
            else:
                await update.message.reply_text(
                    "⛔ هذا الأمر للمشرفين فقط!",
                    reply_markup=main_menu_keyboard(user_id)
                )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def check_balance(service_code: str):
    """ديكوراتور للتحقق من رصيد المستخدم"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # التحقق إذا كان المشرف
            if is_admin(user_id):
                return await func(update, context, *args, **kwargs)
            
            # الحصول على سعر الخدمة
            service_price = db.get_service_price(service_code)
            
            # الحصول على رصيد المستخدم
            user_balance = db.get_balance(user_id)
            
            if user_balance < service_price:
                await update.message.reply_text(
                    format_arabic_text(f"""
                    ⚠️ **رصيدك غير كاف!**
                    
                    **سعر الخدمة:** {format_currency(service_price)}
                    **رصيدك الحالي:** {format_currency(user_balance)}
                    **النقص:** {format_currency(service_price - user_balance)}
                    
                    📥 **لشحن الرصيد:**
                    1. تواصل مع الدعم الفني: {db.get_setting('support_username') or ADMIN_USERNAME}
                    2. أو استخدم رابط الدعوة لدعوة أصدقاء
                    
                    💰 **رابط الدعوة الخاص بك:**
                    `https://t.me/{BOT_USERNAME.replace("@", "")}?start={db.get_user(user_id)['invite_code']}`
                    """),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_keyboard(user_id)
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def check_maintenance(func):
    """ديكوراتور للتحقق من وضع الصيانة"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # المشرف يمكنه استخدام البوت دائماً
        if is_admin(user_id):
            return await func(update, context, *args, **kwargs)
        
        # التحقق من وضع الصيانة
        maintenance_mode = db.get_setting('maintenance_mode')
        if maintenance_mode == '1':
            await update.message.reply_text(
                format_arabic_text("""
                🔧 **البوت قيد الصيانة حالياً**
                
                نعمل على تحسين الخدمة وتطويرها.
                سنعود قريباً بخدمات أفضل!
                
                **⏰ الوقت المقدر:** 1-2 ساعة
                **📞 للاستفسارات:** {support}
                """.format(support=db.get_setting('support_username') or ADMIN_USERNAME)),
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_activity(activity_type: str):
    """ديكوراتور لتسجيل نشاط المستخدم"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # تحديث وقت النشاط الأخير
            db.update_user(user_id, last_active=datetime.now().isoformat())
            
            # تسجيل النشاط
            logger.info(f"📝 نشاط: {activity_type} - المستخدم: {user_id}")
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

# ============================================
# لوحات المفاتيح
# ============================================

def main_menu_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    """لوحة المفاتيح الرئيسية"""
    keyboard = [
        ["📊 حساب درجة العفوية", "📄 تلخيص الملازم"],
        ["❓ أسئلة وأجوبة", "📚 ملازمي ومرشحاتي"],
        ["💰 رصيدي", "📤 دعوة أصدقاء"],
        ["ℹ️ معلومات البوت", "👨‍💻 الدعم الفني"]
    ]
    
    # إضافة زر لوحة التحكم للمشرف
    if user_id and is_admin(user_id):
        keyboard.append(["👑 لوحة التحكم"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, selective=True)

def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح لوحة التحكم"""
    keyboard = [
        ["📊 الإحصائيات", "👥 إدارة المستخدمين"],
        ["💰 الشحن والإيرادات", "⚙️ إعدادات الخدمات"],
        ["📚 إدارة المواد", "🎁 برنامج الدعوة"],
        ["🔧 إعدادات البوت", "📢 البث للمستخدمين"],
        ["🏠 القائمة الرئيسية"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def back_to_main_keyboard() -> ReplyKeyboardMarkup:
    """زر العودة للقائمة الرئيسية"""
    return ReplyKeyboardMarkup([["🏠 القائمة الرئيسية"]], resize_keyboard=True)

def cancel_keyboard() -> ReplyKeyboardMarkup:
    """زر الإلغاء"""
    return ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)

def stages_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح المراحل الدراسية"""
    keyboard = [
        ["المرحلة الأولى", "المرحلة الثانية"],
        ["المرحلة الثالثة", "المرحلة الرابعة"],
        ["🏠 القائمة الرئيسية"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def confirmation_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح التأكيد"""
    keyboard = [
        ["✅ نعم، متأكد", "❌ لا، إلغاء"],
        ["🏠 القائمة الرئيسية"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def payment_methods_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح طرق الدفع"""
    keyboard = [
        ["💳 شحن عبر الدعم", "👥 دعوة أصدقاء"],
        ["🏠 القائمة الرئيسية"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================
# معالجات الأوامر الأساسية
# ============================================

@check_maintenance
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # إرسال رسالة الترحيب
    welcome_text = format_arabic_text(f"""
    🎓 **مرحباً بك في {BOT_NAME}!**
    
    **📚 البوت التعليمي الذكي للطلاب العراقيين**
    
    🎁 **مكافأة ترحيبية:** {format_currency(WELCOME_BONUS_AMOUNT)}
    
    **الخدمات المتاحة:**
    
    📊 **حساب درجة العفوية** - {format_currency(db.get_service_price('exemption_calc'))}
    • حساب معدل الكورسات ومعرفة إذا كنت معفياً
    
    📄 **تلخيص الملازم بالذكاء الاصطناعي** - {format_currency(db.get_service_price('pdf_summary'))}
    • تلخيص الكتب والملازم تلقائياً
    
    ❓ **أسئلة وأجوبة بالذكاء الاصطناعي** - {format_currency(db.get_service_price('qa_ai'))}
    • الإجابة على أسئلتك التعليمية
    
    📚 **ملازمي ومرشحاتي** - {format_currency(db.get_service_price('materials'))}
    • مكتبة المواد التعليمية
    
    💰 **الرصيد الحالي:** {format_currency(db.get_balance(user_id))}
    
    📤 **دعوة أصدقاء:** احصل على {format_currency(int(db.get_setting('invite_bonus') or 500))} لكل صديق!
    
    👨‍💻 **الدعم الفني:** {db.get_setting('support_username') or ADMIN_USERNAME}
    """)
    
    # إضافة المستخدم إذا كان جديداً
    user_data = db.add_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    # التحقق من رابط الدعوة
    if context.args:
        invite_code = context.args[0]
        
        # البحث عن صاحب كود الدعوة
        db.cursor.execute('SELECT user_id FROM users WHERE invite_code = ?', (invite_code,))
        inviter = db.cursor.fetchone()
        
        if inviter and inviter['user_id'] != user_id:
            # إضافة الإحالة
            referral_id = db.add_referral(inviter['user_id'], user_id, invite_code)
            
            if referral_id:
                # إكمال عملية الإحالة
                db.complete_referral(user_id)
                
                # إرسال إشعار للمدعو إليه
                try:
                    inviter_balance = db.get_balance(inviter['user_id'])
                    bonus = int(db.get_setting('invite_bonus') or 500)
                    
                    await context.bot.send_message(
                        inviter['user_id'],
                        format_arabic_text(f"""
                        🎉 **تم تسجيل صديقك عن طريق رابط دعوتك!**
                        
                        👤 **الصديق:** {user.first_name or ''} {user.last_name or ''}
                        💰 **المكافأة:** {format_currency(bonus)}
                        💵 **رصيدك الجديد:** {format_currency(inviter_balance + bonus)}
                        
                        📊 **إجمالي الأصدقاء المدعوين:** {db.get_user(inviter['user_id'])['referral_count']}
                        """),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"❌ فشل في إرسال إشعار للمدعو إليه: {e}")
    
    # إرسال رسالة الترحيب
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )
    
    # تسجيل النشاط
    logger.info(f"👋 مستخدم جديد: {user_id} - {user.username}")

@check_maintenance
@log_activity("balance_check")
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رصيد المستخدم"""
    user_id = update.effective_user.id
    user_balance = db.get_balance(user_id)
    user_data = db.get_user(user_id)
    
    # الحصول على الإحصائيات
    total_earned = user_data.get('total_earned', 0)
    total_spent = user_data.get('total_spent', 0)
    
    # الحصول على رابط الدعوة
    invite_code = user_data.get('invite_code', '')
    invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={invite_code}"
    invite_bonus = int(db.get_setting('invite_bonus') or 500)
    
    balance_text = format_arabic_text(f"""
    💰 **الرصيد والعمليات المالية**
    
    **💵 الرصيد الحالي:** {format_currency(user_balance)}
    
    **📊 الإحصائيات:**
    • إجمالي الإيداعات: {format_currency(total_earned)}
    • إجمالي المصروفات: {format_currency(total_spent)}
    • صافي الربح: {format_currency(total_earned - total_spent)}
    
    **📤 برنامج الدعوة:**
    • مكافأة الدعوة: {format_currency(invite_bonus)}
    • عدد الأصدقاء المدعوين: {user_data.get('referral_count', 0)}
    • إجمالي مكافآت الدعوة: {format_currency(user_data.get('referral_count', 0) * invite_bonus)}
    
    **🔗 رابط دعوتك:**
    `{invite_link}`
    
    **💳 طرق شحن الرصيد:**
    1. التواصل مع الدعم الفني: {db.get_setting('support_username') or ADMIN_USERNAME}
    2. دعوة الأصدقاء عبر الرابط أعلاه
    3. المكافآت والهدايا الدورية
    
    **📝 آخر 5 عمليات:**
    """)
    
    # الحصول على آخر العمليات
    transactions = db.get_transactions(user_id=user_id, limit=5)
    
    if transactions:
        for i, trans in enumerate(transactions, 1):
            amount = trans['amount']
            amount_str = f"+{format_currency(amount)}" if amount > 0 else format_currency(amount)
            
            balance_text += f"\n{i}. {trans['description']}: {amount_str}"
    else:
        balance_text += "\n📭 لا توجد عمليات سابقة"
    
    await update.message.reply_text(
        balance_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )

@check_maintenance
@log_activity("invite_info")
async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات برنامج الدعوة"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    invite_code = user_data.get('invite_code', '')
    invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={invite_code}"
    invite_bonus = int(db.get_setting('invite_bonus') or 500)
    
    # الحصول على الإحالات
    db.cursor.execute('''
        SELECT u.user_id, u.first_name, u.last_name, r.created_at 
        FROM referrals r
        JOIN users u ON r.invited_id = u.user_id
        WHERE r.inviter_id = ? AND r.status = 'completed'
        ORDER BY r.created_at DESC
        LIMIT 10
    ''', (user_id,))
    
    referrals = db.cursor.fetchall()
    
    invite_text = format_arabic_text(f"""
    📤 **برنامج دعوة الأصدقاء**
    
    **🎁 المكافأة:** {format_currency(invite_bonus)} لكل صديق
    **👥 عدد الأصدقاء المدعوين:** {user_data.get('referral_count', 0)}
    **💰 إجمالي المكافآت:** {format_currency(user_data.get('referral_count', 0) * invite_bonus)}
    
    **🔗 رابط دعوتك:**
    `{invite_link}`
    
    **📝 كيفية الاستخدام:**
    1. أرسل الرابط لصديقك
    2. ينقر صديقك على الرابط ويبدأ استخدام البوت
    3. تحصل أنت وصديقك على المكافأة تلقائياً!
    
    **⚡ المميزات:**
    • المكافأة فورية
    • لا حد أقصى لعدد الأصدقاء
    • يمكنك تتبع جميع دعواتك
    • دعم جميع أنواع المستخدمين
    
    **📊 آخر الأصدقاء المدعوين:**
    """)
    
    if referrals:
        for i, referral in enumerate(referrals, 1):
            name = f"{referral['first_name'] or ''} {referral['last_name'] or ''}".strip()
            if not name:
                name = f"المستخدم {referral['user_id']}"
            
            date = format_date(referral['created_at'], "relative")
            invite_text += f"\n{i}. {name} - {date}"
    else:
        invite_text += "\n📭 لم تدعُ أي أصدقاء بعد"
    
    invite_text += f"""
    
    **📞 للاستفسارات:** {db.get_setting('support_username') or ADMIN_USERNAME}
    """
    
    await update.message.reply_text(
        invite_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )

@check_maintenance
@log_activity("info")
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات عن البوت"""
    user_id = update.effective_user.id
    
    # إحصائيات البوت
    total_users = db.get_user_count()
    active_users = db.get_active_users_count(days=7)
    total_revenue = db.get_total_revenue('monthly')
    
    info_text = format_arabic_text(f"""
    ℹ️ **معلومات عن {BOT_NAME}**
    
    **🤖 وصف البوت:**
    بوت تعليمي ذكي مصمم خصيصاً للطلاب العراقيين، 
    يوفر خدمات تعليمية متقدمة باستخدام الذكاء الاصطناعي.
    
    **📊 إحصائيات البوت:**
    • إجمالي المستخدمين: {format_number(total_users)}
    • المستخدمين النشطين (أسبوع): {format_number(active_users)}
    • الإيرادات الشهرية: {format_currency(total_revenue)}
    
    **💎 المميزات:**
    ✅ حساب درجة العفوية
    ✅ تلخيص الملازم بالذكاء الاصطناعي
    ✅ أسئلة وأجوبة ذكية
    ✅ مكتبة المواد التعليمية
    ✅ نظام الدعوة والمكافآت
    ✅ دعم متعدد اللغات
    
    **🔧 التقنيات المستخدمة:**
    • الذكاء الاصطناعي المتقدم (Gemini)
    • معالجة اللغة الطبيعية
    • معالجة ملفات PDF
    • نظام قاعدة بيانات متكامل
    
    **📞 قنوات التواصل:**
    • البوت الرسمي: {BOT_USERNAME}
    • قناة البوت: {db.get_setting('support_channel') or 'غير متاح'}
    • مجموعة الدعم: {db.get_setting('support_group') or 'غير متاح'}
    • الدعم الفني: {db.get_setting('support_username') or ADMIN_USERNAME}
    
    **👑 فريق التطوير:**
    • المطور الرئيسي: {ADMIN_USERNAME}
    • أيدي المطور: {ADMIN_USER_ID}
    
    **📜 الشروط والأحكام:**
    • شروط الاستخدام: {db.get_setting('terms_url') or 'غير متاح'}
    • سياسة الخصوصية: {db.get_setting('privacy_url') or 'غير متاح'}
    
    **🔄 آخر تحديث:** {datetime.now().strftime('%Y-%m-%d')}
    **⚙️ الإصدار:** 3.0.0
    """)
    
    await update.message.reply_text(
        info_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )

@check_maintenance
@log_activity("support")
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الاتصال بالدعم الفني"""
    user_id = update.effective_user.id
    
    support_text = format_arabic_text(f"""
    👨‍💻 **الدعم الفني والاتصال**
    
    **📞 معلومات الاتصال:**
    • يوزر الدعم: {db.get_setting('support_username') or ADMIN_USERNAME}
    • أيدي المطور: `{ADMIN_USER_ID}`
    
    **⏰ ساعات العمل:**
    • الأحد - الخميس: 9:00 صباحاً - 5:00 مساءً
    • الجمعة - السبت: 10:00 صباحاً - 2:00 مساءً
    • توقيت بغداد (UTC+3)
    
    **📋 خدمات الدعم:**
    1. المساعدة الفنية في استخدام البوت
    2. حل المشاكل والتقارير عن الأخطاء
    3. استفسارات الدفع والشحن
    4. اقتراحات التطوير والتحسين
    5. الشكاوى والبلاغات
    
    **🚨 حالات الطوارئ:**
    للقضايا العاجلة، يمكنك مراسلة المطور مباشرة.
    
    **📝 نصائح قبل التواصل:**
    • تأكد من قراءة التعليمات أولاً
    • احتفظ برقم المستخدم الخاص بك: `{user_id}`
    • صف مشكلتك بشكل واضح ومفصل
    • أرفض لقطات شاشة إذا أمكن
    
    **⏱️ وقت الاستجابة المتوقع:**
    • خلال 24 ساعة للاستفسارات العادية
    • خلال 2-4 ساعات للقضايا العاجلة
    
    **شكراً لثقتك بـ {BOT_NAME}!** 🤝
    """)
    
    await update.message.reply_text(
        support_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )

# ============================================
# الخدمة 1: حساب درجة العفوية
# ============================================

@check_maintenance
@check_balance('exemption_calc')
@log_activity("exemption_calculation")
async def exemption_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية حساب درجة العفوية"""
    user_id = update.effective_user.id
    
    # التحقق من الرصيد
    service_price = db.get_service_price('exemption_calc')
    user_balance = db.get_balance(user_id)
    
    if user_balance < service_price and not is_admin(user_id):
        await update.message.reply_text(
            format_arabic_text(f"""
            ⚠️ **رصيدك غير كاف!**
            
            سعر الخدمة: {format_currency(service_price)}
            رصيدك الحالي: {format_currency(user_balance)}
            
            الرجاء شحن رصيدك أولاً.
            """),
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # تسجيل استخدام الخدمة
    db.add_service_usage(
        user_id=user_id,
        service_name='حساب درجة العفوية',
        service_type='exemption_calc',
        cost=service_price,
        details='بدء عملية الحساب'
    )
    
    # خصم المبلغ
    if not is_admin(user_id):
        db.update_balance(
            user_id=user_id,
            amount=-service_price,
            transaction_type='service_payment',
            description='حساب درجة العفوية'
        )
    
    # بدء المحادثة
    await update.message.reply_text(
        format_arabic_text("""
        📊 **حساب درجة العفوية**
        
        **🎯 الشرط:** المعدل ≥ 90
        
        **📝 التعليمات:**
        1. أدخل درجات الكورسات الثلاثة (0-100)
        2. سيتم حساب المعدل تلقائياً
        3. ستعرف إذا كنت معفياً أم لا
        
        **أرسل درجة الكورس الأول:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    # حفظ حالة المحادثة
    context.user_data['exemption_stage'] = 'course1'
    context.user_data['exemption_data'] = {}
    
    return 'WAITING_COURSE1'

async def process_course1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجة الكورس الأول"""
    user_id = update.effective_user.id
    
    try:
        grade = float(update.message.text.strip())
        
        if 0 <= grade <= 100:
            context.user_data['exemption_data']['course1'] = grade
            
            await update.message.reply_text(
                format_arabic_text(f"""
                ✅ **تم حفظ درجة الكورس الأول:** {grade:.2f}
                
                **أرسل درجة الكورس الثاني:**
                """),
                reply_markup=back_to_main_keyboard()
            )
            
            context.user_data['exemption_stage'] = 'course2'
            return 'WAITING_COURSE2'
        else:
            await update.message.reply_text(
                format_arabic_text("""
                ⚠️ **درجة غير صحيحة!**
                
                الرجاء إدخال درجة بين 0 و 100:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_COURSE1'
            
    except ValueError:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **قيمة غير صحيحة!**
            
            الرجاء إدخال رقم فقط (مثال: 85.5):
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_COURSE1'

async def process_course2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجة الكورس الثاني"""
    try:
        grade = float(update.message.text.strip())
        
        if 0 <= grade <= 100:
            context.user_data['exemption_data']['course2'] = grade
            
            await update.message.reply_text(
                format_arabic_text(f"""
                ✅ **تم حفظ درجة الكورس الثاني:** {grade:.2f}
                
                **أرسل درجة الكورس الثالث:**
                """),
                reply_markup=back_to_main_keyboard()
            )
            
            context.user_data['exemption_stage'] = 'course3'
            return 'WAITING_COURSE3'
        else:
            await update.message.reply_text(
                format_arabic_text("""
                ⚠️ **درجة غير صحيحة!**
                
                الرجاء إدخال درجة بين 0 و 100:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_COURSE2'
            
    except ValueError:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **قيمة غير صحيحة!**
            
            الرجاء إدخال رقم فقط (مثال: 90.0):
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_COURSE2'

async def process_course3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجة الكورس الثالث وحساب النتيجة"""
    user_id = update.effective_user.id
    
    try:
        grade = float(update.message.text.strip())
        
        if 0 <= grade <= 100:
            # الحصول على جميع الدرجات
            course1 = context.user_data['exemption_data']['course1']
            course2 = context.user_data['exemption_data']['course2']
            course3 = grade
            
            # حساب المعدل
            average = (course1 + course2 + course3) / 3
            
            # تحديد النتيجة
            if average >= 90:
                result = "🎉 **مبروك! أنت معفي من المادة** 🎉"
                result_emoji = "✅"
                is_exempt = True
            else:
                result = "❌ **للأسف، أنت غير معفي من المادة**"
                result_emoji = "❌"
                is_exempt = False
            
            # حساب النسبة المئوية
            percentage = (average / 100) * 100
            
            # إنشاء نص النتيجة
            result_text = format_arabic_text(f"""
            {result_emoji} **نتيجة حساب درجة العفوية**
            
            **📊 الدرجات المدخلة:**
            • الكورس الأول: {course1:.2f}
            • الكورس الثاني: {course2:.2f}
            • الكورس الثالث: {course3:.2f}
            
            **🧮 الحسابات:**
            • مجموع الدرجات: {course1 + course2 + course3:.2f}
            • المعدل النهائي: **{average:.2f}**
            • النسبة المئوية: **{percentage:.1f}%**
            
            **📈 النتيجة:** {result}
            
            **📝 التوصيات:**
            {f'• يمكنك التقدم بطلب الإعفاء' if is_exempt else '• تحتاج إلى تحسين درجاتك'}
            {f'• المعدل المطلوب: 90 أو أعلى' if not is_exempt else '• احتفظ بنسخة من النتيجة'}
            {f'• النقص: {90 - average:.2f} درجة' if not is_exempt else '• تهانينا على هذا الإنجاز!'}
            
            **🔄 ملاحظة:** الحد الأدنى للإعفاء هو 90 درجة
            """)
            
            # إرسال النتيجة
            await update.message.reply_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(user_id)
            )
            
            # مسح البيانات المؤقتة
            context.user_data.clear()
            
            return ConversationHandler.END
            
        else:
            await update.message.reply_text(
                format_arabic_text("""
                ⚠️ **درجة غير صحيحة!**
                
                الرجاء إدخال درجة بين 0 و 100:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_COURSE3'
            
    except ValueError:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **قيمة غير صحيحة!**
            
            الرجاء إدخال رقم فقط (مثال: 95.0):
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_COURSE3'

# ============================================
# الخدمة 2: تلخيص الملازم بالذكاء الاصطناعي
# ============================================

@check_maintenance
@check_balance('pdf_summary')
@log_activity("pdf_summary")
async def pdf_summary_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تلخيص PDF"""
    user_id = update.effective_user.id
    
    # التحقق من الرصيد
    service_price = db.get_service_price('pdf_summary')
    user_balance = db.get_balance(user_id)
    
    if user_balance < service_price and not is_admin(user_id):
        await update.message.reply_text(
            format_arabic_text(f"""
            ⚠️ **رصيدك غير كاف!**
            
            سعر الخدمة: {format_currency(service_price)}
            رصيدك الحالي: {format_currency(user_balance)}
            
            الرجاء شحن رصيدك أولاً.
            """),
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # تسجيل استخدام الخدمة
    db.add_service_usage(
        user_id=user_id,
        service_name='تلخيص الملازم',
        service_type='pdf_summary',
        cost=service_price,
        details='بدء عملية التلخيص'
    )
    
    # خصم المبلغ
    if not is_admin(user_id):
        db.update_balance(
            user_id=user_id,
            amount=-service_price,
            transaction_type='service_payment',
            description='تلخيص الملازم'
        )
    
    await update.message.reply_text(
        format_arabic_text("""
        📄 **تلخيص الملازم بالذكاء الاصطناعي**
        
        **📝 التعليمات:**
        1. أرسل ملف PDF المراد تلخيصه
        2. انتظر قليلاً لمعالجة الملف
        3. ستحصل على ملف PDF مخرص
        
        **⚡ المميزات:**
        • تلخيص ذكي باستخدام الذكاء الاصطناعي
        • حفظ الهيكل الأصلي للمستند
        • التركيز على النقاط المهمة
        • تنسيق احترافي وجاهز للطباعة
        
        **📦 المتطلبات:**
        • الملف يجب أن يكون بصيغة PDF
        • الحجم الأقصى: 20 ميجابايت
        • يجب أن يحتوي على نص قابل للقراءة
        
        **⏳ الوقت المتوقع:** 1-3 دقائق
        
        **📤 أرسل ملف PDF الآن:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'WAITING_PDF'

async def process_pdf_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف PDF"""
    user_id = update.effective_user.id
    
    if not update.message.document:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **لم يتم إرسال ملف!**
            
            الرجاء إرسال ملف PDF:
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_PDF'
    
    document = update.message.document
    
    # التحقق من نوع الملف
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **نوع ملف غير مدعوم!**
            
            الرجاء إرسال ملف PDF فقط:
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_PDF'
    
    # التحقق من حجم الملف
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            format_arabic_text(f"""
            ⚠️ **حجم الملف كبير جداً!**
            
            الحجم الأقصى المسموح: {MAX_FILE_SIZE // (1024*1024)} ميجابايت
            حجم ملفك: {document.file_size // (1024*1024)} ميجابايت
            
            الرجاء إرسال ملف أصغر:
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'WAITING_PDF'
    
    # بدء المعالجة
    processing_msg = await update.message.reply_text(
        format_arabic_text("""
        ⏳ **جاري معالجة الملف...**
        
        📥 تحميل الملف...
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    try:
        # تحميل الملف
        file = await context.bot.get_file(document.file_id)
        
        # إنشاء اسم ملف مؤقت
        temp_filename = f"pdf_{user_id}_{int(time.time())}.pdf"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري معالجة الملف...**
            
            ✅ تم التحميل
            🔍 قراءة المحتوى...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # تنزيل الملف
        await file.download_to_drive(temp_path)
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري معالجة الملف...**
            
            ✅ تم التحميل
            ✅ تم قراءة المحتوى
            🤖 جاري التلخيص بالذكاء الاصطناعي...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # استخدام الذكاء الاصطناعي للتلخيص
        result = await ai_system.summarize_pdf(temp_path, user_id)
        
        if not result['success']:
            await processing_msg.edit_text(
                format_arabic_text(f"""
                ❌ **فشل في معالجة الملف!**
                
                **الخطأ:** {result['error']}
                
                **🔄 المحاولات:**
                1. تأكد أن الملف يحتوي على نص
                2. حاول باستخدام ملف آخر
                3. تأكد من جودة الملف
                
                الرجاء إرسال ملف آخر:
                """),
                reply_markup=back_to_main_keyboard()
            )
            
            # حذف الملف المؤقت
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return 'WAITING_PDF'
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري معالجة الملف...**
            
            ✅ تم التحميل
            ✅ تم قراءة المحتوى
            ✅ تم التلخيص بالذكاء الاصطناعي
            📝 جاري إنشاء ملف PDF مخرص...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # إنشاء ملف PDF مخرص
        summary_pdf_path = pdf_system.create_summary_pdf(
            summary_text=result['summary'],
            original_filename=document.file_name,
            user_id=user_id,
            metadata={
                'original_size': document.file_size,
                'original_pages': 'غير معروف',
                'summary_length': result['summary_length'],
                'processing_time': f'{int(time.time())}',
                'ai_model': 'Gemini 1.5 Pro'
            }
        )
        
        if not summary_pdf_path or not os.path.exists(summary_pdf_path):
            await processing_msg.edit_text(
                format_arabic_text("""
                ❌ **فشل في إنشاء الملف المخرص!**
                
                **🔄 المحاولات:**
                1. حاول مرة أخرى
                2. تأكد من صلاحية الملف الأصلي
                3. تواصل مع الدعم الفني
                
                الرجاء إرسال ملف آخر:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_PDF'
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري معالجة الملف...**
            
            ✅ تم التحميل
            ✅ تم قراءة المحتوى
            ✅ تم التلخيص بالذكاء الاصطناعي
            ✅ تم إنشاء ملف PDF مخرص
            📤 جاري إرسال الملف...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # إرسال الملف المخرص
        with open(summary_pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                caption=format_arabic_text(f"""
                ✅ **تم تلخيص الملف بنجاح!**
                
                **📄 الملف الأصلي:** {document.file_name}
                **📊 الملف المخرص:** ملخص_{document.file_name}
                **📅 تاريخ الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
                
                **📈 إحصائيات التلخيص:**
                • طول النص الأصلي: {result['original_length']} حرف
                • طول النص المخرص: {result['summary_length']} حرف
                • نسبة التخفيض: {((result['original_length'] - result['summary_length']) / result['original_length'] * 100):.1f}%
                
                **🤖 التقنية المستخدمة:** الذكاء الاصطناعي المتقدم
                **⚡ وقت المعالجة:** {int(time.time() - context.user_data.get('start_time', time.time()))} ثانية
                
                **📝 ملاحظة:** تم إنشاء الملف تلقائياً بواسطة {BOT_NAME}
                """),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(user_id)
            )
        
        # حذف الملفات المؤقتة
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(summary_pdf_path):
            os.remove(summary_pdf_path)
        
        await processing_msg.delete()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة PDF: {e}")
        
        await processing_msg.edit_text(
            format_arabic_text(f"""
            ❌ **حدث خطأ غير متوقع!**
            
            **الخطأ:** {str(e)}
            
            **🔄 المحاولات:**
            1. حاول مرة أخرى
            2. تأكد من صلاحية الملف
            3. تواصل مع الدعم الفني
            
            الرجاء إرسال ملف آخر:
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        return 'WAITING_PDF'

# ============================================
# الخدمة 3: أسئلة وأجوبة بالذكاء الاصطناعي
# ============================================

@check_maintenance
@check_balance('qa_ai')
@log_activity("qa_ai")
async def qa_ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء خدمة الأسئلة والأجوبة"""
    user_id = update.effective_user.id
    
    # التحقق من الرصيد
    service_price = db.get_service_price('qa_ai')
    user_balance = db.get_balance(user_id)
    
    if user_balance < service_price and not is_admin(user_id):
        await update.message.reply_text(
            format_arabic_text(f"""
            ⚠️ **رصيدك غير كاف!**
            
            سعر الخدمة: {format_currency(service_price)}
            رصيدك الحالي: {format_currency(user_balance)}
            
            الرجاء شحن رصيدك أولاً.
            """),
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # تسجيل استخدام الخدمة
    db.add_service_usage(
        user_id=user_id,
        service_name='أسئلة وأجوبة',
        service_type='qa_ai',
        cost=service_price,
        details='بدء خدمة الأسئلة'
    )
    
    # خصم المبلغ
    if not is_admin(user_id):
        db.update_balance(
            user_id=user_id,
            amount=-service_price,
            transaction_type='service_payment',
            description='أسئلة وأجوبة بالذكاء الاصطناعي'
        )
    
    await update.message.reply_text(
        format_arabic_text("""
        ❓ **أسئلة وأجوبة بالذكاء الاصطناعي**
        
        **🎯 كيفية الاستخدام:**
        1. أرسل سؤالك نصياً
        2. أو أرسل صورة تحتوي على سؤال
        3. انتظر قليلاً للإجابة
        
        **📚 المجالات المدعومة:**
        • جميع المواد الدراسية العراقية
        • المسائل الرياضية والعلمية
        • شرح النظريات والمفاهيم
        • التحليل والاستنتاج
        
        **⚡ المميزات:**
        • إجابات دقيقة وشاملة
        • شرح مفصل خطوة بخطوة
        • أمثلة توضيحية
        • دعم الصور والنصوص
        
        **⏳ وقت الاستجابة:** 10-30 ثانية
        
        **📝 أرسل سؤالك الآن:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'WAITING_QUESTION'

async def process_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة السؤال"""
    user_id = update.effective_user.id
    
    # رسالة الانتظار
    processing_msg = await update.message.reply_text(
        format_arabic_text("""
        ⏳ **جاري البحث عن الإجابة...**
        
        🤖 تحليل السؤال...
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    try:
        question_text = ""
        is_image = False
        
        # التحقق من نوع المحتوى
        if update.message.text:
            question_text = update.message.text
            
        elif update.message.photo:
            is_image = True
            
            await processing_msg.edit_text(
                format_arabic_text("""
                ⏳ **جاري البحث عن الإجابة...**
                
                🤖 تحليل السؤال...
                📷 قراءة الصورة...
                """),
                reply_markup=back_to_main_keyboard()
            )
            
            # تحميل الصورة
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # حفظ الصورة مؤقتاً
            temp_image = f"question_{user_id}_{int(time.time())}.jpg"
            temp_path = os.path.join(TEMP_DIR, temp_image)
            
            await file.download_to_drive(temp_path)
            
            # استخدام الذكاء الاصطناعي لتحليل الصورة
            result = await ai_system.analyze_image_question(temp_path)
            
            if not result['success']:
                await processing_msg.edit_text(
                    format_arabic_text(f"""
                    ❌ **فشل في قراءة الصورة!**
                    
                    **الخطأ:** {result['error']}
                    
                    **🔄 المحاولات:**
                    1. تأكد من وضوح الصورة
                    2. حاول كتابة السؤال نصياً
                    3. استخدم صورة بدقة أعلى
                    
                    الرجاء إعادة إرسال السؤال:
                    """),
                    reply_markup=back_to_main_keyboard()
                )
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return 'WAITING_QUESTION'
            
            question_text = result['extracted_text']
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        else:
            await processing_msg.edit_text(
                format_arabic_text("""
                ⚠️ **نوع محتوى غير مدعوم!**
                
                **📝 المدعوم:**
                1. النصوص
                2. الصور
                
                الرجاء إرسال سؤال نصي أو صورة:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_QUESTION'
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري البحث عن الإجابة...**
            
            ✅ تم تحليل السؤال
            🔍 جاري البحث في قاعدة المعرفة...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # استخدام الذكاء الاصطناعي للإجابة
        result = await ai_system.answer_question(question_text, user_id=user_id)
        
        if not result['success']:
            await processing_msg.edit_text(
                format_arabic_text(f"""
                ❌ **فشل في الحصول على إجابة!**
                
                **الخطأ:** {result['error']}
                
                **🔄 المحاولات:**
                1. حاول صياغة السؤال بشكل أوضح
                2. تأكد من اتصال الإنترنت
                3. حاول مرة أخرى لاحقاً
                
                الرجاء إعادة إرسال السؤال:
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'WAITING_QUESTION'
        
        await processing_msg.edit_text(
            format_arabic_text("""
            ⏳ **جاري البحث عن الإجابة...**
            
            ✅ تم تحليل السؤال
            ✅ تم العثور على إجابة
            📝 جاري تحسين التنسيق...
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        # إرسال الإجابة
        answer_text = format_arabic_text(f"""
        🤖 **إجابة على سؤالك:**
        
        **❓ السؤال:**
        {question_text[:500]}{'...' if len(question_text) > 500 else ''}
        
        **✅ الإجابة:**
        {result['answer']}
        
        **📊 معلومات الإجابة:**
        • الثقة: {result['confidence'] * 100:.1f}%
        • المصادر: {'، '.join(result['sources']) if result['sources'] else 'معرفة عامة'}
        • الطول: {len(result['answer'])} حرف
        
        **💡 نصائح:**
        1. يمكنك طرح أسئلة متابعة
        2. للإجابة على صور جديدة، أرسلها مباشرة
        3. لأسئلة معقدة، قسمها إلى أجزاء
        
        **📝 ملاحظة:** تمت الإجابة باستخدام الذكاء الاصطناعي المتقدم
        """)
        
        # تقسيم الإجابة إذا كانت طويلة
        if len(answer_text) > 4000:
            parts = []
            current_part = ""
            
            for line in answer_text.split('\n'):
                if len(current_part) + len(line) + 1 > 4000:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += '\n' + line if current_part else line
            
            if current_part:
                parts.append(current_part)
            
            for i, part in enumerate(parts):
                if i == 0:
                    await processing_msg.edit_text(
                        part[:4000],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard(user_id)
                    )
                else:
                    await update.message.reply_text(
                        part[:4000],
                        parse_mode=ParseMode.MARKDOWN
                    )
        else:
            await processing_msg.edit_text(
                answer_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(user_id)
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة السؤال: {e}")
        
        await processing_msg.edit_text(
            format_arabic_text(f"""
            ❌ **حدث خطأ غير متوقع!**
            
            **الخطأ:** {str(e)}
            
            **🔄 المحاولات:**
            1. حاول مرة أخرى
            2. صغ سؤالك بشكل مختلف
            3. تواصل مع الدعم الفني
            
            الرجاء إعادة إرسال السؤال:
            """),
            reply_markup=back_to_main_keyboard()
        )
        
        return 'WAITING_QUESTION'

# ============================================
# الخدمة 4: ملازمي ومرشحاتي
# ============================================

@check_maintenance
@check_balance('materials')
@log_activity("materials_library")
async def materials_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مكتبة المواد التعليمية"""
    user_id = update.effective_user.id
    
    # التحقق من الرصيد
    service_price = db.get_service_price('materials')
    user_balance = db.get_balance(user_id)
    
    if user_balance < service_price and not is_admin(user_id):
        await update.message.reply_text(
            format_arabic_text(f"""
            ⚠️ **رصيدك غير كاف!**
            
            سعر الخدمة: {format_currency(service_price)}
            رصيدك الحالي: {format_currency(user_balance)}
            
            الرجاء شحن رصيدك أولاً.
            """),
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # تسجيل استخدام الخدمة
    db.add_service_usage(
        user_id=user_id,
        service_name='ملازمي ومرشحاتي',
        service_type='materials',
        cost=service_price,
        details='تصفح المكتبة'
    )
    
    # خصم المبلغ
    if not is_admin(user_id):
        db.update_balance(
            user_id=user_id,
            amount=-service_price,
            transaction_type='service_payment',
            description='ملازمي ومرشحاتي'
        )
    
    await update.message.reply_text(
        format_arabic_text("""
        📚 **ملازمي ومرشحاتي**
        
        **🎯 مكتبة المواد التعليمية الشاملة**
        
        **📂 التصنيفات المتاحة:**
        • المرحلة الدراسية
        • المادة التعليمية
        • نوع الملف
        • التصنيف الموضوعي
        
        **⚡ المميزات:**
        • آلاف المواد التعليمية
        • تحديث مستمر للمحتوى
        • جودة عالية ومراجعة
        • تنزيل مباشر وسريع
        
        **🔍 اختر طريقة التصفح:**
        """),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 حسب المرحلة", callback_data="materials_by_stage"),
                InlineKeyboardButton("🔍 بحث مباشر", callback_data="materials_search")
            ],
            [
                InlineKeyboardButton("📈 الأكثر تنزيلاً", callback_data="materials_popular"),
                InlineKeyboardButton("🆕 الأحدث", callback_data="materials_new")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ]
        ])
    )

async def materials_by_stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المواد حسب المرحلة"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text=format_arabic_text("""
        📚 **المواد حسب المرحلة الدراسية**
        
        **اختر المرحلة:**
        """),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("المرحلة الأولى", callback_data="stage_first"),
                InlineKeyboardButton("المرحلة الثانية", callback_data="stage_second")
            ],
            [
                InlineKeyboardButton("المرحلة الثالثة", callback_data="stage_third"),
                InlineKeyboardButton("المرحلة الرابعة", callback_data="stage_fourth")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="materials_library")
            ]
        ])
    )

async def show_stage_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مواد مرحلة محددة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    stage_map = {
        'stage_first': 'المرحلة الأولى',
        'stage_second': 'المرحلة الثانية',
        'stage_third': 'المرحلة الثالثة',
        'stage_fourth': 'المرحلة الرابعة'
    }
    
    stage_name = stage_map.get(query.data)
    if not stage_name:
        return
    
    # الحصول على مواد المرحلة
    materials = db.get_materials(filters={'stage': stage_name}, limit=10)
    
    if not materials:
        await query.edit_message_text(
            text=format_arabic_text(f"""
            📭 **لا توجد مواد متاحة للمرحلة {stage_name}**
            
            **📝 يمكنك:**
            1. تصفح مراحل أخرى
            2. استخدام البحث المباشر
            3. العودة لاحقاً
            
            **🔄 سيتم إضافة مواد جديدة قريباً!**
            """),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="materials_by_stage")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
            ])
        )
        return
    
    # عرض المواد
    materials_text = format_arabic_text(f"""
    📚 **المواد التعليمية - {stage_name}**
    
    **📊 إجمالي المواد:** {len(materials)}
    
    **📝 قائمة المواد:**
    """)
    
    keyboard = []
    
    for i, material in enumerate(materials, 1):
        title = material['title'][:30] + ('...' if len(material['title']) > 30 else '')
        downloads = material['download_count']
        
        materials_text += f"\n{i}. **{title}**"
        materials_text += f"\n   📥 {downloads} تنزيل • 📅 {format_date(material['upload_date'], 'date')}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {title}",
                callback_data=f"material_{material['material_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="materials_by_stage")])
    
    await query.edit_message_text(
        text=materials_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_material_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل مادة محددة"""
    query = update.callback_query
    await query.answer()
    
    material_id = int(query.data.split('_')[1])
    
    # الحصول على تفاصيل المادة
    db.cursor.execute('SELECT * FROM educational_materials WHERE material_id = ?', (material_id,))
    material = db.cursor.fetchone()
    
    if not material:
        await query.answer("❌ المادة غير موجودة!", show_alert=True)
        return
    
    material = dict(material)
    
    # زيادة عداد المشاهدات
    db.increment_download_count(material_id)
    
    # إنشاء نص التفاصيل
    details_text = format_arabic_text(f"""
    📄 **تفاصيل المادة**
    
    **📌 العنوان:** {material['title']}
    **📝 الوصف:** {material['description'] or 'لا يوجد وصف'}
    
    **📊 المعلومات:**
    • التصنيف: {material['category'] or 'غير محدد'}
    • المرحلة: {material['stage'] or 'غير محدد'}
    • المادة: {material['subject'] or 'غير محدد'}
    • نوع الملف: {material['file_type'] or 'غير محدد'}
    
    **📈 الإحصائيات:**
    • عدد التنزيلات: {material['download_count']}
    • التقييم: {'★' * int(material['rating'])} ({material['rating']}/5)
    • تاريخ الإضافة: {format_date(material['upload_date'], 'full')}
    
    **🏷️ الوسوم:** {material['tags'] or 'لا توجد وسوم'}
    
    **📥 يمكنك تنزيل المادة الآن:**
    """)
    
    await query.edit_message_text(
        text=details_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 تنزيل المادة", callback_data=f"download_{material_id}"),
                InlineKeyboardButton("⭐ تقييم", callback_data=f"rate_{material_id}")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="materials_library"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            ]
        ])
    )

async def download_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنزيل مادة"""
    query = update.callback_query
    await query.answer()
    
    material_id = int(query.data.split('_')[1])
    
    # الحصول على تفاصيل المادة
    db.cursor.execute('SELECT * FROM educational_materials WHERE material_id = ?', (material_id,))
    material = db.cursor.fetchone()
    
    if not material:
        await query.answer("❌ المادة غير موجودة!", show_alert=True)
        return
    
    material = dict(material)
    
    # إرسال الملف
    try:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=material['file_id'],
            caption=format_arabic_text(f"""
            📥 **تم تنزيل المادة بنجاح!**
            
            **📌 العنوان:** {material['title']}
            **📝 الوصف:** {material['description'] or 'لا يوجد وصف'}
            
            **📊 المعلومات:**
            • المرحلة: {material['stage']}
            • المادة: {material['subject']}
            • تاريخ الإضافة: {format_date(material['upload_date'], 'date')}
            
            **💡 نصائح:**
            1. احفظ الملف في مكان آمن
            2. شاركه مع زملائك
            3. يمكنك البحث عن مواد أخرى
            
            **📞 للاستفسارات:** {db.get_setting('support_username') or ADMIN_USERNAME}
            """),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(query.from_user.id)
        )
        
        await query.answer("✅ تم إرسال الملف!", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الملف: {e}")
        await query.answer("❌ فشل في إرسال الملف!", show_alert=True)

# ============================================
# لوحة التحكم للمشرف
# ============================================

@admin_only
@log_activity("admin_panel")
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المشرف"""
    user_id = update.effective_user.id
    
    # إحصائيات سريعة
    total_users = db.get_user_count()
    active_users = db.get_active_users_count(days=1)
    daily_revenue = db.get_total_revenue('daily')
    total_materials = len(db.get_materials())
    
    admin_text = format_arabic_text(f"""
    👑 **لوحة تحكم المشرف**
    
    **📊 نظرة سريعة:**
    • إجمالي المستخدمين: {format_number(total_users)}
    • المستخدمين النشطين اليوم: {format_number(active_users)}
    • الإيرادات اليومية: {format_currency(daily_revenue)}
    • عدد المواد: {format_number(total_materials)}
    
    **⚡ الإجراءات السريعة:**
    1. عرض الإحصائيات التفصيلية
    2. إدارة المستخدمين
    3. الشحن والإيرادات
    4. إعدادات الخدمات
    
    **🔧 أدوات التحكم:**
    • إعدادات البوت
    • إدارة المواد التعليمية
    • برنامج الدعوة
    • البث للمستخدمين
    
    **📈 آخر التحديثات:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
    """)
    
    await update.message.reply_text(
        admin_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )

@admin_only
async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات مفصلة"""
    user_id = update.effective_user.id
    
    # إحصائيات المستخدمين
    total_users = db.get_user_count()
    new_today = db.get_daily_stats()['new_users']
    active_today = db.get_daily_stats()['active_users']
    banned_users = len(db.get_all_users(filters={'is_banned': 1}))
    
    # إحصائيات مالية
    daily_revenue = db.get_total_revenue('daily')
    weekly_revenue = db.get_total_revenue('weekly')
    monthly_revenue = db.get_total_revenue('monthly')
    total_balance = sum(user['balance'] for user in db.get_all_users())
    
    # إحصائيات الخدمات
    service_stats = db.get_service_stats('daily')
    
    # إحصائيات المواد
    total_materials = len(db.get_materials())
    materials_today = db.get_daily_stats()['materials_downloaded']
    
    stats_text = format_arabic_text(f"""
    📊 **الإحصائيات التفصيلية**
    
    **👥 المستخدمين:**
    • إجمالي المستخدمين: {format_number(total_users)}
    • مسجلين اليوم: {format_number(new_today)}
    • نشطين اليوم: {format_number(active_today)}
    • محظورين: {format_number(banned_users)}
    
    **💰 المالية:**
    • الإيرادات اليومية: {format_currency(daily_revenue)}
    • الإيرادات الأسبوعية: {format_currency(weekly_revenue)}
    • الإيرادات الشهرية: {format_currency(monthly_revenue)}
    • إجمالي الأرصدة: {format_currency(total_balance)}
    
    **📊 الخدمات (اليوم):**
    """)
    
    for service, data in service_stats.items():
        stats_text += f"\n• {service}: {data['count']} استخدام ({format_currency(data['revenue'])})"
    
    stats_text += f"""
    
    **📚 المواد التعليمية:**
    • إجمالي المواد: {format_number(total_materials)}
    • تم تنزيلها اليوم: {format_number(materials_today)}
    
    **📈 النمو:**
    • معدل النمو اليومي: {((new_today / total_users) * 100) if total_users > 0 else 0:.1f}%
    • متوسط الإيرادات/يوم: {format_currency(daily_revenue)}
    • متوسط الاستخدام/مستخدم: {active_today / total_users if total_users > 0 else 0:.1f}
    
    **⏱️ آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )

@admin_only
async def admin_users_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المستخدمين"""
    await update.message.reply_text(
        format_arabic_text("""
        👥 **إدارة المستخدمين**
        
        **اختر الإجراء المطلوب:**
        """),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user"),
                InlineKeyboardButton("📋 عرض جميع المستخدمين", callback_data="admin_list_users")
            ],
            [
                InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user"),
                InlineKeyboardButton("✅ إلغاء حظر", callback_data="admin_unban_user")
            ],
            [
                InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge_user"),
                InlineKeyboardButton("📊 إحصائيات مستخدم", callback_data="admin_user_stats")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")
            ]
        ])
    )

@admin_only
async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بحث عن مستخدم"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text=format_arabic_text("""
        🔍 **بحث عن مستخدم**
        
        **يمكنك البحث بـ:**
        • أيدي المستخدم
        • اسم المستخدم
        • الاسم الأول
        • الاسم الأخير
        
        **أرسل كلمة البحث:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'ADMIN_SEARCH_USER'

async def process_admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة بحث المشرف"""
    search_term = update.message.text
    
    # البحث عن المستخدمين
    users = db.search_users(search_term)
    
    if not users:
        await update.message.reply_text(
            format_arabic_text(f"""
            📭 **لا توجد نتائج لـ "{search_term}"**
            
            **🔄 المحاولات:**
            1. تحقق من صحة البحث
            2. استخدم أجزاء من الاسم
            3. استخدم أيدي المستخدم
            
            **أرسل بحث جديد:**
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'ADMIN_SEARCH_USER'
    
    # عرض النتائج
    results_text = format_arabic_text(f"""
    🔍 **نتائج البحث لـ "{search_term}"**
    
    **📊 عدد النتائج:** {len(users)}
    
    **📝 النتائج:**
    """)
    
    keyboard = []
    
    for i, user in enumerate(users[:10], 1):
        name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        if not name:
            name = f"المستخدم {user['user_id']}"
        
        status = "🚫 محظور" if user['is_banned'] else "✅ نشط"
        balance = format_currency(user['balance'])
        
        results_text += f"\n{i}. **{name}**"
        results_text += f"\n   • الأيدي: `{user['user_id']}`"
        results_text += f"\n   • اليوزر: @{user['username'] or 'بدون'}"
        results_text += f"\n   • الرصيد: {balance}"
        results_text += f"\n   • الحالة: {status}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {name[:15]}...",
                callback_data=f"admin_view_user_{user['user_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_management")])
    
    await update.message.reply_text(
        results_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

@admin_only
async def admin_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تفاصيل مستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[-1])
    user = db.get_user(user_id)
    
    if not user:
        await query.answer("❌ المستخدم غير موجود!", show_alert=True)
        return
    
    # الحصول على آخر العمليات
    transactions = db.get_transactions(user_id=user_id, limit=5)
    
    # إنشاء نص التفاصيل
    details_text = format_arabic_text(f"""
    👤 **تفاصيل المستخدم**
    
    **🆔 الأيدي:** `{user['user_id']}`
    **👤 الاسم:** {user['first_name'] or ''} {user['last_name'] or ''}
    **📧 اليوزر:** @{user['username'] or 'بدون'}
    
    **📊 المعلومات:**
    • الرصيد: {format_currency(user['balance'])}
    • تاريخ التسجيل: {format_date(user['join_date'], 'full')}
    • آخر نشاط: {format_date(user['last_active'], 'relative')}
    • اللغة: {user['language_code'] or 'ar'}
    
    **💰 الإحصائيات المالية:**
    • إجمالي الإيداعات: {format_currency(user['total_earned'])}
    • إجمالي المصروفات: {format_currency(user['total_spent'])}
    • صافي الربح: {format_currency(user['total_earned'] - user['total_spent'])}
    
    **👥 الإحالات:**
    • عدد المدعوين: {user['referral_count']}
    • كود الدعوة: `{user['invite_code']}`
    
    **🚫 حالة الحظر:** {"محظور" if user['is_banned'] else "نشط"}
    {f"• سبب الحظر: {user['ban_reason']}" if user['is_banned'] else ""}
    
    **📝 آخر العمليات:**
    """)
    
    if transactions:
        for trans in transactions:
            amount = trans['amount']
            amount_str = f"+{format_currency(amount)}" if amount > 0 else format_currency(amount)
            details_text += f"\n• {trans['description']}: {amount_str} ({format_date(trans['created_at'], 'relative')})"
    else:
        details_text += "\n📭 لا توجد عمليات سابقة"
    
    # إنشاء أزرار الإجراءات
    keyboard = []
    
    if user['is_banned']:
        keyboard.append([InlineKeyboardButton("✅ إلغاء حظر", callback_data=f"admin_unban_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_{user_id}")])
    
    keyboard.append([
        InlineKeyboardButton("💰 شحن رصيد", callback_data=f"admin_charge_{user_id}"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data=f"admin_stats_{user_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_management"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    ])
    
    await query.edit_message_text(
        text=details_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def admin_charge_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية شحن رصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[-1])
    context.user_data['charge_user_id'] = user_id
    
    user = db.get_user(user_id)
    user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
    if not user_name:
        user_name = f"المستخدم {user_id}"
    
    await query.edit_message_text(
        text=format_arabic_text(f"""
        💰 **شحن رصيد للمستخدم**
        
        **👤 المستخدم:** {user_name}
        **🆔 الأيدي:** `{user_id}`
        **💵 الرصيد الحالي:** {format_currency(user['balance'])}
        
        **أرسل المبلغ للشحن:**
        (يمكن أن يكون موجباً للإضافة أو سالباً للخصم)
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'ADMIN_CHARGE_AMOUNT'

async def process_admin_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة شحن الرصيد"""
    try:
        amount = int(update.message.text)
        user_id = context.user_data.get('charge_user_id')
        
        if not user_id:
            await update.message.reply_text(
                format_arabic_text("""
                ⚠️ **انتهت الجلسة!**
                
                الرجاء إعادة العملية من البداية.
                """),
                reply_markup=admin_panel_keyboard()
            )
            return ConversationHandler.END
        
        user = db.get_user(user_id)
        old_balance = user['balance']
        new_balance = old_balance + amount
        
        # شحن الرصيد
        db.update_balance(
            user_id=user_id,
            amount=amount,
            transaction_type='admin_charge',
            description=f'شحن بواسطة المشرف: {amount} {CURRENCY_SYMBOL}'
        )
        
        # إرسال إشعار للمستخدم
        try:
            await context.bot.send_message(
                user_id,
                format_arabic_text(f"""
                💰 **تم تحديث رصيدك!**
                
                **📝 التفاصيل:**
                • المبلغ: {format_currency(amount)}
                • الرصيد السابق: {format_currency(old_balance)}
                • الرصيد الجديد: {format_currency(new_balance)}
                • التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                • بواسطة: المشرف
                
                **📞 للاستفسارات:** {db.get_setting('support_username') or ADMIN_USERNAME}
                """),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"⚠️ فشل في إرسال إشعار للمستخدم {user_id}: {e}")
        
        user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        if not user_name:
            user_name = f"المستخدم {user_id}"
        
        await update.message.reply_text(
            format_arabic_text(f"""
            ✅ **تم الشحن بنجاح!**
            
            **👤 المستخدم:** {user_name}
            **🆔 الأيدي:** `{user_id}`
            **💰 المبلغ:** {format_currency(amount)}
            **💵 الرصيد السابق:** {format_currency(old_balance)}
            **💳 الرصيد الجديد:** {format_currency(new_balance)}
            **📅 التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            
            **📝 تم إرسال إشعار للمستخدم.**
            """),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        
        # مسح البيانات المؤقتة
        context.user_data.pop('charge_user_id', None)
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **قيمة غير صحيحة!**
            
            الرجاء إرسال رقم صحيح فقط:
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'ADMIN_CHARGE_AMOUNT'

@admin_only
async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حظر مستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[-1])
    
    # حظر المستخدم
    success = db.ban_user(user_id)
    
    if success:
        await query.answer("✅ تم حظر المستخدم!", show_alert=True)
        
        # تحديث الرسالة
        user = db.get_user(user_id)
        user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        if not user_name:
            user_name = f"المستخدم {user_id}"
        
        await query.edit_message_text(
            text=format_arabic_text(f"""
            ✅ **تم حظر المستخدم بنجاح!**
            
            **👤 المستخدم:** {user_name}
            **🆔 الأيدي:** `{user_id}`
            **📅 التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            
            **📝 يمكنك إلغاء الحظر في أي وقت.**
            """),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ إلغاء حظر", callback_data=f"admin_unban_{user_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_management")]
            ])
        )
    else:
        await query.answer("❌ فشل في حظر المستخدم!", show_alert=True)

@admin_only
async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء حظر مستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[-1])
    
    # إلغاء حظر المستخدم
    success = db.unban_user(user_id)
    
    if success:
        await query.answer("✅ تم إلغاء حظر المستخدم!", show_alert=True)
        
        # تحديث الرسالة
        user = db.get_user(user_id)
        user_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        if not user_name:
            user_name = f"المستخدم {user_id}"
        
        await query.edit_message_text(
            text=format_arabic_text(f"""
            ✅ **تم إلغاء حظر المستخدم بنجاح!**
            
            **👤 المستخدم:** {user_name}
            **🆔 الأيدي:** `{user_id}`
            **📅 التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            
            **📝 يمكن إعادة حظره في أي وقت.**
            """),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_{user_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_management")]
            ])
        )
    else:
        await query.answer("❌ فشل في إلغاء حظر المستخدم!", show_alert=True)

@admin_only
async def admin_service_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعدادات الخدمات"""
    # الحصول على أسعار الخدمات
    db.cursor.execute('SELECT * FROM service_prices WHERE is_active = 1')
    services = db.cursor.fetchall()
    
    services_text = format_arabic_text("""
    ⚙️ **إعدادات الخدمات والأسعار**
    
    **📝 قائمة الخدمات:**
    """)
    
    keyboard = []
    
    for service in services:
        service = dict(service)
        services_text += f"\n• **{service['service_name']}**"
        services_text += f"\n  الكود: `{service['service_code']}`"
        services_text += f"\n  السعر الحالي: {format_currency(service['current_price'])}"
        services_text += f"\n  المدى: {format_currency(service['min_price'])} - {format_currency(service['max_price'])}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {service['service_name']}",
                callback_data=f"admin_service_{service['service_code']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ إضافة خدمة", callback_data="admin_add_service")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
    
    await update.message.reply_text(
        services_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def admin_edit_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل خدمة"""
    query = update.callback_query
    await query.answer()
    
    service_code = query.data.split('_')[-1]
    
    # الحصول على تفاصيل الخدمة
    db.cursor.execute('SELECT * FROM service_prices WHERE service_code = ?', (service_code,))
    service = db.cursor.fetchone()
    
    if not service:
        await query.answer("❌ الخدمة غير موجودة!", show_alert=True)
        return
    
    service = dict(service)
    
    details_text = format_arabic_text(f"""
    ⚙️ **تعديل الخدمة**
    
    **📌 الاسم:** {service['service_name']}
    **🔤 الكود:** `{service['service_code']}`
    
    **💰 الأسعار:**
    • السعر الحالي: {format_currency(service['current_price'])}
    • السعر الأساسي: {format_currency(service['base_price'])}
    • الحد الأدنى: {format_currency(service['min_price'])}
    • الحد الأقصى: {format_currency(service['max_price'])}
    
    **📝 الوصف:** {service['description'] or 'لا يوجد وصف'}
    **🔧 الحالة:** {'✅ نشطة' if service['is_active'] else '❌ معطلة'}
    
    **📅 آخر تحديث:** {format_date(service['updated_at'], 'full')}
    """)
    
    await query.edit_message_text(
        text=details_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💰 تغيير السعر", callback_data=f"admin_change_price_{service_code}"),
                InlineKeyboardButton("🔧 تغيير الحالة", callback_data=f"admin_toggle_service_{service_code}")
            ],
            [
                InlineKeyboardButton("📝 تعديل الوصف", callback_data=f"admin_edit_desc_{service_code}"),
                InlineKeyboardButton("🗑️ حذف الخدمة", callback_data=f"admin_delete_service_{service_code}")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_service_settings")]
        ])
    )

@admin_only
async def admin_change_service_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير سعر الخدمة"""
    query = update.callback_query
    await query.answer()
    
    service_code = query.data.split('_')[-1]
    context.user_data['edit_service_code'] = service_code
    
    await query.edit_message_text(
        text=format_arabic_text(f"""
        💰 **تغيير سعر الخدمة**
        
        **🔤 كود الخدمة:** `{service_code}`
        
        **أرسل السعر الجديد:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'ADMIN_SET_PRICE'

async def process_admin_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تعيين السعر الجديد"""
    try:
        new_price = int(update.message.text)
        service_code = context.user_data.get('edit_service_code')
        
        if not service_code:
            await update.message.reply_text(
                format_arabic_text("""
                ⚠️ **انتهت الجلسة!**
                
                الرجاء إعادة العملية من البداية.
                """),
                reply_markup=admin_panel_keyboard()
            )
            return ConversationHandler.END
        
        # تحديث السعر
        success = db.update_service_price(service_code, new_price)
        
        if success:
            # الحصول على تفاصيل الخدمة
            db.cursor.execute('SELECT * FROM service_prices WHERE service_code = ?', (service_code,))
            service = db.cursor.fetchone()
            service = dict(service)
            
            await update.message.reply_text(
                format_arabic_text(f"""
                ✅ **تم تحديث السعر بنجاح!**
                
                **📌 الخدمة:** {service['service_name']}
                **🔤 الكود:** `{service_code}`
                **💰 السعر السابق:** {format_currency(service['current_price'])}
                **💵 السعر الجديد:** {format_currency(new_price)}
                **📅 التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
                
                **📝 سيتم تطبيق السعر الجديد فوراً.**
                """),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_panel_keyboard()
            )
        else:
            await update.message.reply_text(
                format_arabic_text(f"""
                ❌ **فشل في تحديث السعر!**
                
                **🔄 المحاولات:**
                1. تأكد أن السعر ضمن المدى المسموح
                2. تأكد من صحة كود الخدمة
                3. حاول مرة أخرى
                
                **أرسل السعر الجديد:**
                """),
                reply_markup=back_to_main_keyboard()
            )
            return 'ADMIN_SET_PRICE'
        
        # مسح البيانات المؤقتة
        context.user_data.pop('edit_service_code', None)
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            format_arabic_text("""
            ⚠️ **قيمة غير صحيحة!**
            
            الرجاء إرسال رقم صحيح فقط:
            """),
            reply_markup=back_to_main_keyboard()
        )
        return 'ADMIN_SET_PRICE'

@admin_only
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية البث"""
    await update.message.reply_text(
        format_arabic_text("""
        📢 **البث للمستخدمين**
        
        **📝 التعليمات:**
        1. أرسل الرسالة التي تريد بثها
        2. يمكن أن تحتوي على نص، صور، أو ملفات
        3. سيتم إرسالها لجميع المستخدمين
        
        **⚡ المميزات:**
        • إرسال لجميع المستخدمين
        • دعم جميع أنواع المحتوى
        • تتبع النتائج
        • إحصاءات مفصلة
        
        **⚠️ تحذير:** هذه العملية قد تستغرق وقتاً
        
        **أرسل الرسالة الآن:**
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    return 'ADMIN_BROADCAST'

async def process_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة البث"""
    user_id = update.effective_user.id
    
    # الحصول على جميع المستخدمين
    users = db.get_all_users()
    total_users = len(users)
    
    # رسالة التقدم
    progress_msg = await update.message.reply_text(
        format_arabic_text(f"""
        📤 **جاري إرسال البث...**
        
        **📊 الإحصائيات:**
        • إجمالي المستخدمين: {format_number(total_users)}
        • تم الإرسال: 0
        • فشل الإرسال: 0
        • النسبة: 0%
        
        **⏳ الوقت المقدر:** {total_users * 0.5:.0f} ثانية
        """),
        reply_markup=back_to_main_keyboard()
    )
    
    successful = 0
    failed = 0
    
    # إرسال الرسالة لكل مستخدم
    for i, user in enumerate(users):
        try:
            # محاولة إرسال الرسالة
            if update.message.text:
                await context.bot.send_message(
                    user['user_id'],
                    format_arabic_text(f"""
                    📢 **إشعار من إدارة البوت**
                    
                    {update.message.text}
                    
                    ---
                    *هذا إشعام عام لجميع المستخدمين*
                    """),
                    parse_mode=ParseMode.MARKDOWN
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    user['user_id'],
                    update.message.photo[-1].file_id,
                    caption=format_arabic_text("📢 إشعار من إدارة البوت")
                )
            elif update.message.document:
                await context.bot.send_document(
                    user['user_id'],
                    update.message.document.file_id,
                    caption=format_arabic_text("📢 إشعار من إدارة البوت")
                )
            
            successful += 1
            
            # تحديث رسالة التقدم كل 10 مستخدمين
            if i % 10 == 0:
                percentage = (i + 1) / total_users * 100
                
                await progress_msg.edit_text(
                    format_arabic_text(f"""
                    📤 **جاري إرسال البث...**
                    
                    **📊 الإحصائيات:**
                    • إجمالي المستخدمين: {format_number(total_users)}
                    • تم الإرسال: {format_number(i + 1)}
                    • فشل الإرسال: {format_number(failed)}
                    • النسبة: {percentage:.1f}%
                    
                    **⏳ الوقت المتبقي:** {(total_users - i - 1) * 0.5:.0f} ثانية
                    """),
                    reply_markup=back_to_main_keyboard()
                )
            
            # تأخير لتجنب حظر تليجرام
            await asyncio.sleep(0.1)
            
        except Exception as e:
            failed += 1
            logger.warning(f"⚠️ فشل في إرسال للمستخدم {user['user_id']}: {e}")
            continue
    
    # إرسال النتيجة النهائية
    percentage = successful / total_users * 100
    
    result_text = format_arabic_text(f"""
    ✅ **تم الانتهاء من البث!**
    
    **📊 النتائج النهائية:**
    • إجمالي المستخدمين: {format_number(total_users)}
    • تم الإرسال بنجاح: {format_number(successful)}
    • فشل الإرسال: {format_number(failed)}
    • نسبة النجاح: {percentage:.1f}%
    
    **⏱️ وقت التنفيذ:** {total_users * 0.5:.0f} ثانية
    **📅 التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    **📝 ملاحظات:**
    1. المستخدمون المحظورون لن تصلهم الرسائل
    2. المستخدمون الذين حذفوا المحادثة لن تصلهم الرسائل
    3. يمكن تكرار العملية في أي وقت
    
    **📞 للاستفسارات:** {db.get_setting('support_username') or ADMIN_USERNAME}
    """)
    
    await progress_msg.edit_text(
        result_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    
    return ConversationHandler.END

# ============================================
# معالجات الأزرار
# ============================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الاستدعاء"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        await query.edit_message_text(
            text=format_arabic_text("🏠 **القائمة الرئيسية**"),
            reply_markup=main_menu_keyboard(query.from_user.id)
        )
    
    elif data == "admin_back":
        await admin_panel_command(update, context)
    
    elif data.startswith("admin_view_user_"):
        await admin_view_user(update, context)
    
    elif data.startswith("admin_charge_"):
        await admin_charge_user_start(update, context)
    
    elif data.startswith("admin_ban_"):
        await admin_ban_user(update, context)
    
    elif data.startswith("admin_unban_"):
        await admin_unban_user(update, context)
    
    elif data == "admin_service_settings":
        await admin_service_settings(update, context)
    
    elif data.startswith("admin_service_"):
        await admin_edit_service(update, context)
    
    elif data.startswith("admin_change_price_"):
        await admin_change_service_price(update, context)
    
    elif data == "materials_library":
        await materials_library(update, context)
    
    elif data == "materials_by_stage":
        await materials_by_stage(update, context)
    
    elif data.startswith("stage_"):
        await show_stage_materials(update, context)
    
    elif data.startswith("material_"):
        await show_material_details(update, context)
    
    elif data.startswith("download_"):
        await download_material(update, context)
    
    else:
        await query.answer("❌ هذا الزر غير مدعوم!", show_alert=True)

# ============================================
# معالجات الرسائل العامة
# ============================================

@check_maintenance
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # الأوامر من لوحة المفاتيح
    if message_text == "🏠 القائمة الرئيسية":
        await update.message.reply_text(
            format_arabic_text("🏠 **القائمة الرئيسية**"),
            reply_markup=main_menu_keyboard(user_id)
        )
    
    elif message_text == "📊 حساب درجة العفوية":
        await exemption_calculation(update, context)
    
    elif message_text == "📄 تلخيص الملازم":
        await pdf_summary_start(update, context)
    
    elif message_text == "❓ أسئلة وأجوبة":
        await qa_ai_start(update, context)
    
    elif message_text == "📚 ملازمي ومرشحاتي":
        await materials_library(update, context)
    
    elif message_text == "💰 رصيدي":
        await balance_command(update, context)
    
    elif message_text == "📤 دعوة أصدقاء":
        await invite_command(update, context)
    
    elif message_text == "ℹ️ معلومات البوت":
        await info_command(update, context)
    
    elif message_text == "👨‍💻 الدعم الفني":
        await support_command(update, context)
    
    elif message_text == "👑 لوحة التحكم":
        await admin_panel_command(update, context)
    
    # أوامر لوحة التحكم
    elif message_text == "📊 الإحصائيات":
        await admin_statistics(update, context)
    
    elif message_text == "👥 إدارة المستخدمين":
        await admin_users_management(update, context)
    
    elif message_text == "💰 الشحن والإيرادات":
        await update.message.reply_text(
            format_arabic_text("""
            💰 **الشحن والإيرادات**
            
            **اختر الإجراء المطلوب:**
            """),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 الإيرادات", callback_data="admin_revenue_stats"),
                    InlineKeyboardButton("💳 شحن يدوي", callback_data="admin_manual_charge")
                ],
                [
                    InlineKeyboardButton("📈 الرسوم البيانية", callback_data="admin_charts"),
                    InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export_data")
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
            ])
        )
    
    elif message_text == "⚙️ إعدادات الخدمات":
        await admin_service_settings(update, context)
    
    elif message_text == "📚 إدارة المواد":
        await update.message.reply_text(
            format_arabic_text("""
            📚 **إدارة المواد التعليمية**
            
            **اختر الإجراء المطلوب:**
            """),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ إضافة مادة", callback_data="admin_add_material"),
                    InlineKeyboardButton("🗑️ حذف مادة", callback_data="admin_delete_material")
                ],
                [
                    InlineKeyboardButton("📋 عرض جميع المواد", callback_data="admin_list_materials"),
                    InlineKeyboardButton("📊 إحصائيات المواد", callback_data="admin_materials_stats")
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
            ])
        )
    
    elif message_text == "🎁 برنامج الدعوة":
        await update.message.reply_text(
            format_arabic_text(f"""
            🎁 **برنامج الدعوة**
            
            **📊 الإحصائيات الحالية:**
            • مكافأة الدعوة: {format_currency(int(db.get_setting('invite_bonus') or 500))}
            • إجمالي الإحالات: {sum(user['referral_count'] for user in db.get_all_users())}
            
            **اختر الإجراء المطلوب:**
            """),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💰 تغيير المكافأة", callback_data="admin_change_bonus"),
                    InlineKeyboardButton("📊 إحصائيات الإحالات", callback_data="admin_referral_stats")
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
            ])
        )
    
    elif message_text == "🔧 إعدادات البوت":
        settings = db.get_all_settings()
        
        settings_text = format_arabic_text("""
        🔧 **إعدادات البوت**
        
        **📝 قائمة الإعدادات:**
        """)
        
        for key, value in settings.items():
            if len(str(value)) < 50:  # عرض فقط الإعدادات القصيرة
                settings_text += f"\n• **{key}:** {value}"
        
        settings_text += f"""
        
        **📅 آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        **🔍 للبحث عن إعداد محدد، أرسل:** `/setting اسم_الإعداد`
        **✏️ لتعديل إعداد، أرسل:** `/set اسم_الإعداد القيمة`
        """
        
        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
    
    elif message_text == "📢 البث للمستخدمين":
        await admin_broadcast_start(update, context)
    
    else:
        # إذا لم يكن الأمر معروفاً
        await update.message.reply_text(
            format_arabic_text("""
            🤔 **لم أفهم طلبك!**
            
            **📝 التعليمات:**
            1. استخدم الأزرار في القائمة الرئيسية
            2. أو اكتب الأمر مباشرة
            
            **⚡ الأوامر السريعة:**
            • `/start` - بدء استخدام البوت
            • `/balance` - عرض الرصيد
            • `/invite` - معلومات الدعوة
            • `/help` - المساعدة
            
            **📞 للاستفسارات:** {support}
            """.format(support=db.get_setting('support_username') or ADMIN_USERNAME)),
            reply_markup=main_menu_keyboard(user_id)
        )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة الحالية"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        format_arabic_text("""
        ❌ **تم الإلغاء**
        
        **🏠 العودة للقائمة الرئيسية**
        """),
        reply_markup=main_menu_keyboard(user_id)
    )
    
    # مسح البيانات المؤقتة
    context.user_data.clear()
    
    return ConversationHandler.END

# ============================================
# الأوامر الإضافية
# ============================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة المساعدة"""
    user_id = update.effective_user.id
    
    help_text = format_arabic_text(f"""
    🆘 **مركز المساعدة - {BOT_NAME}**
    
    **📝 الأوامر الأساسية:**
    • `/start` - بدء استخدام البوت
    • `/balance` - عرض الرصيد والعمليات
    • `/invite` - برنامج دعوة الأصدقاء
    • `/info` - معلومات عن البوت
    • `/support` - الاتصال بالدعم الفني
    • `/help` - عرض هذه الرسالة
    
    **🎯 الخدمات المتاحة:**
    1. **حساب درجة العفوية** - حساب المعدل ومعرفة الإعفاء
    2. **تلخيص الملازم** - تلخيص الكتب بالذكاء الاصطناعي
    3. **أسئلة وأجوبة** - الإجابة على أسئلتك التعليمية
    4. **ملازمي ومرشحاتي** - مكتبة المواد التعليمية
    
    **💰 نظام الدفع:**
    • جميع الخدمات مدفوعة
    • العملة: {CURRENCY_NAME}
    • أقل سعر: {format_currency(MINIMUM_SERVICE_PRICE)}
    • طرق الشحن: الدعم الفني أو دعوة الأصدقاء
    
    **📞 الدعم الفني:**
    • اليوزر: {db.get_setting('support_username') or ADMIN_USERNAME}
    • الوقت: 9:00 ص - 5:00 م (توقيت بغداد)
    • الاستجابة: خلال 24 ساعة
    
    **🔧 المشاكل الشائعة:**
    1. **الرصيد غير كاف** - شحن عبر الدعم أو الدعوة
    2. **ملف PDF لا يعمل** - تأكد من صحة الملف
    3. **لا توجد إجابة** - حاول صياغة السؤال بشكل أوضح
    4. **مشاكل تقنية** - تواصل مع الدعم الفني
    
    **📱 كيفية الاستخدام:**
    1. ابدأ بالأمر `/start`
    2. استخدم الأزرار للتنقل
    3. اختر الخدمة المطلوبة
    4. اتبع التعليمات
    
    **⚡ نصائح سريعة:**
    • احفظ رقم مستخدمك: `{user_id}`
    • استخدم رابط الدعوة لكسب المال
    • اقرأ التعليمات قبل كل خدمة
    • بلغ عن المشاكل فوراً
    
    **📚 للاستفسارات التعليمية:** استخدم خدمة الأسئلة والأجوبة
    **💼 للاستفسارات المالية:** تواصل مع الدعم الفني
    **🔨 للإبلاغ عن أخطاء:** أرسل تفاصيل المشكلة للدعم
    
    **شكراً لاستخدامك {BOT_NAME}!** 🌟
    """)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id)
    )

# ============================================
# وظائف الخلفية
# ============================================

async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة تنظيف الملفات المؤقتة"""
    try:
        # تنظيف الملفات المؤقتة
        pdf_system.cleanup_temp_files(hours_old=24)
        
        # تنظيف سجل الأخطاء القديمة
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        db.cursor.execute('DELETE FROM error_logs WHERE DATE(created_at) < ?', (cutoff_date,))
        db.connection.commit()
        
        logger.info("✅ تم تنظيف الملفات المؤقتة والسجلات القديمة")
    except Exception as e:
        logger.error(f"❌ خطأ في وظيفة التنظيف: {e}")

async def backup_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة النسخ الاحتياطي"""
    try:
        backup_file = db.create_backup()
        if backup_file:
            logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
    except Exception as e:
        logger.error(f"❌ خطأ في وظيفة النسخ الاحتياطي: {e}")

async def stats_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة تحديث الإحصائيات"""
    try:
        # تحديث إحصائيات اليوم
        today = datetime.now().strftime('%Y-%m-%d')
        
        db.cursor.execute('''
            INSERT OR REPLACE INTO statistics (stat_date, total_users, new_users, active_users)
            SELECT 
                DATE('now'),
                (SELECT COUNT(*) FROM users),
                (SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')),
                (SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now'))
        ''')
        
        db.connection.commit()
        logger.debug("✅ تم تحديث الإحصائيات اليومية")
    except Exception as e:
        logger.error(f"❌ خطأ في وظيفة الإحصائيات: {e}")

# ============================================
# الدالة الرئيسية لتشغيل البوت
# ============================================

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    # التحقق من وجود التوكن
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "8481569753:AAHTdbWwu0BHmoo_iHPsye8RkTptWzfiQWU":
        logger.error("❌ لم تقم بتعيين توكن البوت! الرجاء تعديل ملف الكود وإضافة التوكن الصحيح.")
        return
    
    # التحقق من وجود مفتاح API
    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY":
        logger.error("❌ لم تقم بتعيين مفتاح API للذكاء الاصطناعي! الرجاء تعديل ملف الكود.")
        return
    
    # إنشاء التطبيق
    application = ApplicationBuilder() \
        .token(TELEGRAM_BOT_TOKEN) \
        .concurrent_updates(True) \
        .pool_timeout(30) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .build()
    
    # ============ محادثات الخدمات ============
    
    # محادثة حساب درجة العفوية
    exemption_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 حساب درجة العفوية$"), exemption_calculation)],
        states={
            'WAITING_COURSE1': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_course1)],
            'WAITING_COURSE2': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_course2)],
            'WAITING_COURSE3': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_course3)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^❌ إلغاء$"), cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(exemption_conv)
    
    # محادثة تلخيص PDF
    pdf_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📄 تلخيص الملازم$"), pdf_summary_start)],
        states={
            'WAITING_PDF': [
                MessageHandler(filters.Document.PDF, process_pdf_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                             lambda u, c: u.message.reply_text("⚠️ الرجاء إرسال ملف PDF فقط!"))
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^❌ إلغاء$"), cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(pdf_conv)
    
    # محادثة الأسئلة والأجوبة
    qa_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ أسئلة وأجوبة$"), qa_ai_start)],
        states={
            'WAITING_QUESTION': [
                MessageHandler(filters.TEXT | filters.PHOTO, process_question)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^❌ إلغاء$"), cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(qa_conv)
    
    # محادثة بحث المشرف
    admin_search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_search_user, pattern="^admin_search_user$")],
        states={
            'ADMIN_SEARCH_USER': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_search)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(admin_search_conv)
    
    # محادثة شحن المشرف
    admin_charge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_charge_user_start, pattern="^admin_charge_\\d+$")],
        states={
            'ADMIN_CHARGE_AMOUNT': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_charge)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(admin_charge_conv)
    
    # محادثة تغيير سعر الخدمة
    admin_price_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_change_service_price, pattern="^admin_change_price_")],
        states={
            'ADMIN_SET_PRICE': [MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_set_price)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(admin_price_conv)
    
    # محادثة البث للمستخدمين
    admin_broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 البث للمستخدمين$"), admin_broadcast_start)],
        states={
            'ADMIN_BROADCAST': [
                MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, process_admin_broadcast)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^🏠 القائمة الرئيسية$"), cancel_conversation)
        ]
    )
    application.add_handler(admin_broadcast_conv)
    
    # ============ معالجات الأوامر ============
    
    # الأوامر الأساسية
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("invite", invite_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel_command))
    
    # معالج أزرار الاستدعاء
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ============ وظائف الخلفية ============
    
    # إضافة وظائف مجدولة
    job_queue = application.job_queue
    
    if job_queue:
        # تنظيف الملفات المؤقتة كل ساعة
        job_queue.run_repeating(cleanup_job, interval=3600, first=10)
        
        # النسخ الاحتياطي كل 6 ساعات
        job_queue.run_repeating(backup_job, interval=21600, first=30)
        
        # تحديث الإحصائيات كل ساعة
        job_queue.run_repeating(stats_job, interval=3600, first=60)
    
    # ============ تشغيل البوت ============
    
    # معلومات بدء التشغيل
    logger.info("=" * 50)
    logger.info(f"🚀 بدأ تشغيل بوت {BOT_NAME}")
    logger.info(f"🤖 يوزر البوت: {BOT_USERNAME}")
    logger.info(f"👑 أيدي المشرف: {ADMIN_USER_ID}")
    logger.info(f"👤 يوزر المشرف: {ADMIN_USERNAME}")
    logger.info(f"💰 العملة: {CURRENCY_NAME}")
    logger.info(f"💳 أقل سعر خدمة: {format_currency(MINIMUM_SERVICE_PRICE)}")
    logger.info(f"📊 عدد المستخدمين: {db.get_user_count()}")
    logger.info("=" * 50)
    
    # تشغيل البوت
    application.run_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    # إنشاء المجلدات المطلوبة
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # إغلاق قاعدة البيانات
        db.close()
        logger.info("🔒 تم إغلاق جميع الاتصالات")
