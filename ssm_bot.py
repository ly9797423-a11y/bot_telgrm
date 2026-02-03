#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام "يلا نتعلم"
الإصدار: 3.0
المطور: Allawi04@
التوكن الجديد: 8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI
تاريخ الإصدار: 2024
"""

import os
import sys
import json
import logging
import asyncio
import datetime
import random
import string
import re
import hashlib
import math
import time
import io
import csv
import html
import urllib.parse
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, OrderedDict
from contextlib import contextmanager
from functools import wraps
from threading import Lock, Timer
from queue import Queue
import threading

# ========== المكتبات الأساسية ==========
try:
    # مكتبات تليجرام
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup, 
        ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
        Message, Chat, User, CallbackQuery, ChatMember,
        InputFile, InputMediaDocument, Document, PhotoSize,
        BotCommand, BotCommandScopeDefault
    )
    from telegram.ext import (
        Application, ApplicationBuilder, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, ConversationHandler,
        filters, PicklePersistence, JobQueue, TypeHandler,
        CallbackContext
    )
    from telegram.constants import (
        ParseMode, ChatAction, ChatType, MessageLimit,
        MessageEntityType, ChatMemberStatus
    )
    from telegram.error import (
        TelegramError, BadRequest, ChatMigrated, NetworkError,
        RetryAfter, TimedOut, Forbidden, Unauthorized
    )
    
    # مكتبات الذكاء الاصطناعي
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    from google.api_core.exceptions import GoogleAPIError
    
    # مكتبات معالجة الصور والمستندات
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    import PyPDF2
    from PyPDF2 import PdfReader, PdfWriter
    import pdfkit
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import (
        black, white, red, blue, green, yellow,
        Color, HexColor, CMYKColor, PCMYKColor
    )
    from reportlab.lib.units import inch, cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak, KeepTogether, Flowable
    )
    from reportlab.lib.styles import (
        getSampleStyleSheet, ParagraphStyle, StyleSheet1
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib import utils
    import arabic_reshaper
    from bidi.algorithm import get_display
    
    # مكتبات قاعدة البيانات
    import sqlite3
    from sqlite3 import Error as SQLiteError
    
    # مكتبات الشبكة والطلبات
    import requests
    from requests.exceptions import (
        RequestException, Timeout, ConnectionError,
        HTTPError, TooManyRedirects
    )
    import aiohttp
    import urllib3
    
    # مكتبات إضافية
    import numpy as np
    from uuid import uuid4
    import hashlib
    import base64
    import mimetypes
    import tempfile
    import shutil
    from pathlib import Path
    import textwrap
    import inspect
    import traceback
    import pprint
    import statistics
    
except ImportError as e:
    print(f"❌ خطأ في تحميل المكتبات: {e}")
    print("⏳ جاري تثبيت المكتبات المطلوبة...")
    os.system("pip install python-telegram-bot google-generativeai Pillow PyPDF2 pdfkit reportlab arabic-reshaper python-bidi requests aiohttp numpy -q")
    print("✅ تم تثبيت المكتبات بنجاح!")
    os.execv(sys.executable, ['python'] + sys.argv)

# ========== إعدادات التسجيل ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== ثوابت البوت ==========
class Constants:
    """فئة للثوابت والإعدادات"""
    
    # إعدادات البوت
    TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"  # التوكن الجديد
    BOT_USERNAME = "@FC4Xbot"
    ADMIN_ID = 6130994941
    SUPPORT_USERNAME = "Allawi04@"
    GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"
    
    # مسارات الملفات
    DB_NAME = "yalla_nt3lem_v3.db"
    LOGS_DIR = "logs"
    FONTS_DIR = "fonts"
    MATERIALS_DIR = "materials"
    TEMP_DIR = "temp"
    
    # إعدادات قاعدة البيانات
    DB_TIMEOUT = 30
    DB_PRAGMAS = {
        'journal_mode': 'WAL',
        'cache_size': 10000,
        'foreign_keys': 1,
        'synchronous': 'NORMAL'
    }
    
    # الألوان
    COLORS = {
        'primary': '#2E86C1',
        'secondary': '#17A589',
        'success': '#28B463',
        'danger': '#E74C3C',
        'warning': '#F39C12',
        'info': '#3498DB',
        'dark': '#1C2833',
        'light': '#F8F9F9'
    }
    
    # الرموز التعبيرية
    EMOJIS = {
        'money': '💰',
        'book': '📚',
        'brain': '🧠',
        'chart': '📊',
        'user': '👤',
        'users': '👥',
        'admin': '👑',
        'lock': '🔒',
        'unlock': '🔓',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅',
        'info': 'ℹ️',
        'question': '❓',
        'star': '⭐',
        'fire': '🔥',
        'rocket': '🚀',
        'trophy': '🏆',
        'medal': '🎖️',
        'crown': '👑',
        'shield': '🛡️',
        'gear': '⚙️',
        'wrench': '🛠️',
        'bell': '🔔',
        'megaphone': '📢',
        'inbox': '📥',
        'outbox': '📤',
        'clock': '⏰',
        'calendar': '📅',
        'document': '📄',
        'folder': '📁',
        'search': '🔍',
        'filter': '🔎',
        'download': '📥',
        'upload': '📤',
        'link': '🔗',
        'hashtag': '#️⃣',
        'at': '@️⃣',
        'phone': '📱',
        'computer': '💻',
        'globe': '🌐',
        'flag': '🏁',
        'target': '🎯',
        'key': '🔑',
        'lock_with_key': '🔐',
        'unlocked': '🔓',
        'mail': '✉️',
        'envelope': '📧',
        'incoming_envelope': '📨',
        'paperclip': '📎',
        'scissors': '✂️',
        'pencil': '✏️',
        'paintbrush': '🖌️',
        'hammer': '🔨',
        'nut_and_bolt': '🔩',
        'chains': '⛓️',
        'magnet': '🧲',
        'test_tube': '🧪',
        'microscope': '🔬',
        'telescope': '🔭',
        'satellite': '🛰️',
        'bulb': '💡',
        'battery': '🔋',
        'electric_plug': '🔌',
        'money_bag': '💰',
        'credit_card': '💳',
        'bank': '🏦',
        'receipt': '🧾',
        'chart_increasing': '📈',
        'chart_decreasing': '📉',
        'bar_chart': '📊',
        'clipboard': '📋',
        'pushpin': '📌',
        'round_pushpin': '📍',
        'paper': '📝',
        'newspaper': '📰',
        'bookmark': '🔖',
        'label': '🏷️',
        'package': '📦',
        'mailbox': '📫',
        'postbox': '📮',
        'pencil2': '✒️',
        'black_nib': '✒️',
        'fountain_pen': '🖋️',
        'pen': '🖊️',
        'paintbrush2': '🖌️',
        'crayon': '🖍️',
        'memo': '📝',
        'briefcase': '💼',
        'file_folder': '📁',
        'open_file_folder': '📂',
        'card_index': '📇',
        'date': '📅',
        'calendar2': '📆',
        'spiral_calendar': '🗓️',
        'card_index_dividers': '🗂️',
        'printer': '🖨️',
        'fax': '📠',
        'tv': '📺',
        'radio': '📻',
        'video_camera': '📹',
        'movie_camera': '🎥',
        'film_projector': '📽️',
        'telephone': '☎️',
        'telephone_receiver': '📞',
        'pager': '📟',
        'satellite_antenna': '📡',
        'loudspeaker': '📢',
        'megaphone2': '📣',
        'bell2': '🔔',
        'no_bell': '🔕',
        'musical_score': '🎼',
        'musical_note': '🎵',
        'notes': '🎶',
        'studio_microphone': '🎙️',
        'level_slider': '🎚️',
        'control_knobs': '🎛️',
        'microphone': '🎤',
        'headphone': '🎧',
        'radio2': '📻',
        'saxophone': '🎷',
        'guitar': '🎸',
        'musical_keyboard': '🎹',
        'trumpet': '🎺',
        'violin': '🎻',
        'drum': '🥁'
    }
    
    # أوامر البوت للقائمة
    BOT_COMMANDS = [
        ("start", "بدء استخدام البوت"),
        ("menu", "عرض القائمة الرئيسية"),
        ("balance", "عرض رصيدك"),
        ("materials", "عرض الملازم"),
        ("help", "عرض المساعدة"),
        ("support", "الاتصال بالدعم")
    ]

# ========== إعدادات الذكاء الاصطناعي ==========
class AIConfig:
    """فئة إعدادات الذكاء الاصطناعي"""
    
    # مفاتيح API
    GEMINI_API_KEY = Constants.GEMINI_API_KEY
    
    # نماذج الذكاء الاصطناعي
    MODELS = {
        'gemini_pro': 'gemini-pro',
        'gemini_pro_vision': 'gemini-pro-vision',
        'gemini_1_5_pro': 'gemini-1.5-pro',
        'gemini_1_5_flash': 'gemini-1.5-flash'
    }
    
    # إعدادات التوليد
    GENERATION_CONFIG = {
        'temperature': 0.7,
        'top_p': 0.8,
        'top_k': 40,
        'max_output_tokens': 2048,
        'stop_sequences': None
    }
    
    # إعدادات السلامة
    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        }
    ]
    
    # الأوامر المخصصة
    PROMPTS = {
        'summary': """
        أنت مساعد تعليمي عراقي متخصص في تلخيص المواد الدراسية.
        
        قم بتلخيص النص التالي مع مراعاة:
        1. التركيز على النقاط الرئيسية والأفكار المهمة
        2. استخدام لغة عربية فصحى واضحة
        3. تنظيم المحتوى في نقاط مرتبة
        4. تضمين المصطلحات العلمية المهمة
        5. إضافة أمثلة توضيحية عند الحاجة
        6. الإشارة إلى المنهج العراقي
        
        قدم التلخيص بشكل احترافي ومناسب للطلاب.
        """,
        
        'qa': """
        أنت مدرس عراقي متخصص في المناهج الدراسية العراقية.
        
        أجب على السؤال التالي باتباع التعليمات:
        1. قدم الإجابة بلغة عربية واضحة وسلسة
        2. ركز على الجوانب العلمية والتعليمية
        3. اذكر المصادر إذا كانت متوفرة
        4. قدم أمثلة من المنهج العراقي
        5. إذا كان السؤال معقداً، قسم الإجابة إلى نقاط
        6. تأكد من دقة المعلومات
        7. تجنب المعلومات غير المؤكدة
        
        كن مفيداً ودقيقاً في إجاباتك.
        """,
        
        'excuse_calc': """
        أنت مساعد لحساب درجات الطلاب العراقيين.
        
        احسب المعدل بناءً على الدرجات المدخلة وقرر إذا كان الطالب معفى.
        
        شروط الإعفاء في العراق:
        1. المعدل 90% أو أعلى: معفى
        2. المعدل أقل من 90%: غير معفى
        3. يجب أن تكون جميع الدرجات بين 0 و 100
        
        قدم النتيجة مع شرح مفصل.
        """,
        
        'material_analysis': """
        أنت محلل مواد دراسية عراقي.
        
        قم بتحليل المادة التعليمية وتقديم:
        1. ملخص شامل للمحتوى
        2. النقاط الرئيسية
        3. المفاهيم الصعبة
        4. نصائح للدراسة
        5. أسئلة مراجعة
        
        ركز على احتياجات الطالب العراقي.
        """
    }

# ========== فئات البيانات ==========
@dataclass
class UserData:
    """فئة بيانات المستخدم"""
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    balance: int = 0
    referral_code: str = ""
    referred_by: Optional[str] = None
    join_date: str = ""
    is_banned: bool = False
    is_premium: bool = False
    total_spent: int = 0
    total_earned: int = 0
    last_active: str = ""
    language: str = "ar"
    notifications: bool = True
    session_count: int = 0
    total_messages: int = 0
    
    @classmethod
    def from_db_row(cls, row):
        """إنشاء كائن من صف قاعدة البيانات"""
        return cls(
            user_id=row[0],
            username=row[1],
            first_name=row[2],
            last_name=row[3],
            balance=row[4],
            referral_code=row[5],
            referred_by=row[6],
            join_date=row[7],
            is_banned=bool(row[8]),
            is_premium=bool(row[9]),
            total_spent=row[10],
            total_earned=row[11] if len(row) > 11 else 0,
            last_active=row[12] if len(row) > 12 else "",
            language=row[13] if len(row) > 13 else "ar",
            notifications=bool(row[14]) if len(row) > 14 else True,
            session_count=row[15] if len(row) > 15 else 0,
            total_messages=row[16] if len(row) > 16 else 0
        )

@dataclass
class Transaction:
    """فئة المعاملة"""
    id: int
    user_id: int
    amount: int
    type: str
    description: str
    date: str
    status: str = "completed"
    reference: Optional[str] = None
    
    @classmethod
    def from_db_row(cls, row):
        """إنشاء كائن من صف قاعدة البيانات"""
        return cls(
            id=row[0],
            user_id=row[1],
            amount=row[2],
            type=row[3],
            description=row[4],
            date=row[5],
            status=row[6] if len(row) > 6 else "completed",
            reference=row[7] if len(row) > 7 else None
        )

@dataclass
class Material:
    """فئة المادة التعليمية"""
    id: int
    name: str
    description: str
    file_id: str
    stage: str
    subject: str
    file_size: int
    downloads: int = 0
    added_date: str = ""
    added_by: Optional[int] = None
    is_active: bool = True
    
    @classmethod
    def from_db_row(cls, row):
        """إنشاء كائن من صف قاعدة البيانات"""
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            file_id=row[3],
            stage=row[4],
            subject=row[5],
            file_size=row[6],
            downloads=row[7] if len(row) > 7 else 0,
            added_date=row[8] if len(row) > 8 else "",
            added_by=row[9] if len(row) > 9 else None,
            is_active=bool(row[10]) if len(row) > 10 else True
        )

@dataclass
class Service:
    """فئة الخدمة"""
    id: int
    name: str
    description: str
    price: int
    category: str
    is_active: bool = True
    ai_enabled: bool = False
    min_balance: int = 0
    max_uses_per_day: int = 10
    cooldown_seconds: int = 0
    
    @classmethod
    def from_db_row(cls, row):
        """إنشاء كائن من صف قاعدة البيانات"""
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            price=row[3],
            category=row[4],
            is_active=bool(row[5]) if len(row) > 5 else True,
            ai_enabled=bool(row[6]) if len(row) > 6 else False,
            min_balance=row[7] if len(row) > 7 else 0,
            max_uses_per_day=row[8] if len(row) > 8 else 10,
            cooldown_seconds=row[9] if len(row) > 9 else 0
        )

@dataclass
class AdminLog:
    """فئة سجل المدير"""
    id: int
    admin_id: int
    action: str
    details: str
    target_id: Optional[int] = None
    ip_address: Optional[str] = None
    timestamp: str = ""
    
    @classmethod
    def from_db_row(cls, row):
        """إنشاء كائن من صف قاعدة البيانات"""
        return cls(
            id=row[0],
            admin_id=row[1],
            action=row[2],
            details=row[3],
            target_id=row[4] if len(row) > 4 else None,
            ip_address=row[5] if len(row) > 5 else None,
            timestamp=row[6] if len(row) > 6 else ""
        )

# ========== مدير قاعدة البيانات ==========
class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """نمط Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db_name = Constants.DB_NAME
            self.connection = None
            self.cursor = None
            self.connect()
            self.init_database()
    
    def connect(self):
        """الاتصال بقاعدة البيانات"""
        try:
            self.connection = sqlite3.connect(
                self.db_name,
                timeout=Constants.DB_TIMEOUT,
                check_same_thread=False
            )
            self.cursor = self.connection.cursor()
            
            # تطبيق إعدادات PRAGMA
            for pragma, value in Constants.DB_PRAGMAS.items():
                self.cursor.execute(f"PRAGMA {pragma} = {value}")
            
            logger.info("✅ تم الاتصال بقاعدة البيانات")
            
        except SQLiteError as e:
            logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
            raise
    
    def init_database(self):
        """تهيئة قاعدة البيانات"""
        try:
            # جدول المستخدمين
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    balance INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned INTEGER DEFAULT 0,
                    is_premium INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    last_active TIMESTAMP,
                    language TEXT DEFAULT 'ar',
                    notifications INTEGER DEFAULT 1,
                    session_count INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0
                )
            ''')
            
            # جدول المعاملات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed',
                    reference TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول الخدمات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER DEFAULT 1000,
                    category TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    ai_enabled INTEGER DEFAULT 0,
                    min_balance INTEGER DEFAULT 0,
                    max_uses_per_day INTEGER DEFAULT 10,
                    cooldown_seconds INTEGER DEFAULT 0
                )
            ''')
            
            # جدول الملازم
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    file_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    subject TEXT,
                    file_size INTEGER,
                    downloads INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by INTEGER,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (added_by) REFERENCES users (user_id)
                )
            ''')
            
            # جدول استخدام الخدمات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    use_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cost INTEGER,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (service_id) REFERENCES services (id)
                )
            ''')
            
            # جدول الإعدادات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول سجلات المدير
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    target_id INTEGER,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الجلسات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    service_type TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول الإحصائيات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0,
                    total_transactions INTEGER DEFAULT 0,
                    total_income INTEGER DEFAULT 0,
                    total_expenses INTEGER DEFAULT 0,
                    service_usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # إدراج الخدمات الافتراضية
            default_services = [
                ('حساب درجة العفو', 'حساب المعدل للإعفاء من المادة', 1000, 'education', 1, 0, 0, 10, 0),
                ('تلخيص الملازم', 'تلخيص الملفات التعليمية باستخدام الذكاء الاصطناعي', 1000, 'ai', 1, 1, 0, 5, 60),
                ('سؤال وجواب', 'الإجابة على الأسئلة العلمية باستخدام الذكاء الاصطناعي', 1000, 'ai', 1, 1, 0, 20, 30),
                ('الملازم والمرشحات', 'المواد التعليمية المجانية', 0, 'education', 1, 0, 0, 100, 0)
            ]
            
            self.cursor.executemany('''
                INSERT OR IGNORE INTO services 
                (name, description, price, category, is_active, ai_enabled, min_balance, max_uses_per_day, cooldown_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', default_services)
            
            # الإعدادات الافتراضية
            default_settings = [
                ('maintenance_mode', 'false', 'وضع الصيانة'),
                ('bot_channel', '', 'قناة البوت'),
                ('support_username', Constants.SUPPORT_USERNAME, 'اسم مستخدم الدعم'),
                ('referral_bonus', '500', 'مكافأة الإحالة'),
                ('welcome_bonus', '1000', 'الهدية الترحيبية'),
                ('min_charge_amount', '1000', 'أقل مبلغ للشحن'),
                ('max_charge_amount', '1000000', 'أعلى مبلغ للشحن'),
                ('currency', 'دينار عراقي', 'العملة'),
                ('currency_symbol', 'د.ع', 'رمز العملة'),
                ('bot_language', 'ar', 'لغة البوت'),
                ('ai_model', 'gemini-pro', 'نموذج الذكاء الاصطناعي'),
                ('pdf_quality', 'high', 'جودة ملفات PDF'),
                ('max_file_size_mb', '20', 'أقصى حجم للملف'),
                ('daily_free_uses', '3', 'الاستخدامات المجانية اليومية'),
                ('admin_notifications', 'true', 'إشعارات المدير')
            ]
            
            self.cursor.executemany('''
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', default_settings)
            
            self.connection.commit()
            logger.info("✅ تم تهيئة قاعدة البيانات")
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            self.connection.rollback()
            raise
    
    # ========== دوال المستخدمين ==========
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = None) -> str:
        """إضافة مستخدم جديد"""
        try:
            referral_code = self.generate_referral_code()
            
            self.cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, referral_code, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name, referral_code))
            
            if self.cursor.rowcount > 0:
                # منح الهدية الترحيبية
                welcome_bonus = int(self.get_setting('welcome_bonus', '1000'))
                self.update_user_balance(user_id, welcome_bonus)
                self.add_transaction(
                    user_id, welcome_bonus, 'welcome_bonus',
                    'هدية ترحيبية للمستخدم الجديد'
                )
                
                self.log_admin_action(
                    Constants.ADMIN_ID, 'user_registered',
                    f'مستخدم جديد: {user_id} - {first_name}'
                )
            
            self.connection.commit()
            return referral_code
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
            self.connection.rollback()
            return ""
    
    def get_user(self, user_id: int) -> Optional[UserData]:
        """الحصول على بيانات المستخدم"""
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            
            if row:
                return UserData.from_db_row(row)
            return None
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs):
        """تحديث بيانات المستخدم"""
        try:
            if not kwargs:
                return
            
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            self.cursor.execute(f'''
                UPDATE users SET {set_clause}
                WHERE user_id = ?
            ''', values)
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تحديث بيانات المستخدم: {e}")
            self.connection.rollback()
    
    def update_user_balance(self, user_id: int, amount: int):
        """تحديث رصيد المستخدم"""
        try:
            self.cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, 
                    total_earned = total_earned + ?
                WHERE user_id = ? AND ? > 0
            ''', (amount, max(amount, 0), user_id, amount))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تحديث رصيد المستخدم: {e}")
            self.connection.rollback()
    
    def get_user_count(self) -> int:
        """عدد المستخدمين"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0] or 0
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب عدد المستخدمين: {e}")
            return 0
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[UserData]:
        """الحصول على جميع المستخدمين"""
        try:
            self.cursor.execute('''
                SELECT * FROM users 
                ORDER BY join_date DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = self.cursor.fetchall()
            return [UserData.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب جميع المستخدمين: {e}")
            return []
    
    def search_users(self, query: str) -> List[UserData]:
        """بحث عن المستخدمين"""
        try:
            search_query = f"%{query}%"
            self.cursor.execute('''
                SELECT * FROM users 
                WHERE user_id LIKE ? 
                   OR username LIKE ? 
                   OR first_name LIKE ? 
                   OR last_name LIKE ?
                ORDER BY user_id
                LIMIT 50
            ''', (search_query, search_query, search_query, search_query))
            
            rows = self.cursor.fetchall()
            return [UserData.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في البحث عن المستخدمين: {e}")
            return []
    
    def ban_user(self, user_id: int, reason: str = ""):
        """حظر مستخدم"""
        try:
            self.cursor.execute('''
                UPDATE users SET is_banned = 1
                WHERE user_id = ?
            ''', (user_id,))
            
            self.connection.commit()
            self.log_admin_action(
                Constants.ADMIN_ID, 'user_banned',
                f'تم حظر المستخدم {user_id} - السبب: {reason}'
            )
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في حظر المستخدم: {e}")
            self.connection.rollback()
    
    def unban_user(self, user_id: int):
        """فك حظر مستخدم"""
        try:
            self.cursor.execute('''
                UPDATE users SET is_banned = 0
                WHERE user_id = ?
            ''', (user_id,))
            
            self.connection.commit()
            self.log_admin_action(
                Constants.ADMIN_ID, 'user_unbanned',
                f'تم فك حظر المستخدم {user_id}'
            )
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في فك حظر المستخدم: {e}")
            self.connection.rollback()
    
    # ========== دوال المعاملات ==========
    def add_transaction(self, user_id: int, amount: int, trans_type: str, 
                       description: str = "", status: str = "completed", 
                       reference: str = None):
        """إضافة معاملة"""
        try:
            self.cursor.execute('''
                INSERT INTO transactions 
                (user_id, amount, type, description, status, reference)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, trans_type, description, status, reference))
            
            # تحديث إجمالي الإنفاق إذا كان المبلغ سالباً
            if amount < 0:
                self.cursor.execute('''
                    UPDATE users 
                    SET total_spent = total_spent + ?
                    WHERE user_id = ?
                ''', (abs(amount), user_id))
            
            self.connection.commit()
            return self.cursor.lastrowid
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في إضافة المعاملة: {e}")
            self.connection.rollback()
            return None
    
    def get_user_transactions(self, user_id: int, limit: int = 20) -> List[Transaction]:
        """الحصول على معاملات المستخدم"""
        try:
            self.cursor.execute('''
                SELECT * FROM transactions 
                WHERE user_id = ?
                ORDER BY date DESC
                LIMIT ?
            ''', (user_id, limit))
            
            rows = self.cursor.fetchall()
            return [Transaction.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب معاملات المستخدم: {e}")
            return []
    
    def get_total_balance(self) -> int:
        """إجمالي الأرصدة"""
        try:
            self.cursor.execute('SELECT SUM(balance) FROM users')
            result = self.cursor.fetchone()[0]
            return int(result) if result else 0
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب إجمالي الأرصدة: {e}")
            return 0
    
    def get_total_income(self) -> int:
        """إجمالي الدخل"""
        try:
            self.cursor.execute('''
                SELECT SUM(amount) FROM transactions 
                WHERE amount > 0 AND status = 'completed'
            ''')
            result = self.cursor.fetchone()[0]
            return abs(int(result)) if result else 0
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب إجمالي الدخل: {e}")
            return 0
    
    # ========== دوال الخدمات ==========
    def get_services(self, active_only: bool = True) -> List[Service]:
        """الحصول على الخدمات"""
        try:
            query = 'SELECT * FROM services'
            if active_only:
                query += ' WHERE is_active = 1'
            query += ' ORDER BY category, name'
            
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [Service.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الخدمات: {e}")
            return []
    
    def get_service(self, service_id: int) -> Optional[Service]:
        """الحصول على خدمة معينة"""
        try:
            self.cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
            row = self.cursor.fetchone()
            
            if row:
                return Service.from_db_row(row)
            return None
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الخدمة: {e}")
            return None
    
    def get_service_by_name(self, name: str) -> Optional[Service]:
        """الحصول على خدمة بالاسم"""
        try:
            self.cursor.execute('SELECT * FROM services WHERE name = ?', (name,))
            row = self.cursor.fetchone()
            
            if row:
                return Service.from_db_row(row)
            return None
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الخدمة بالاسم: {e}")
            return None
    
    def update_service_price(self, service_id: int, new_price: int):
        """تحديث سعر الخدمة"""
        try:
            self.cursor.execute('''
                UPDATE services SET price = ?
                WHERE id = ?
            ''', (new_price, service_id))
            
            self.connection.commit()
            self.log_admin_action(
                Constants.ADMIN_ID, 'service_price_updated',
                f'تم تحديث سعر الخدمة {service_id} إلى {new_price}'
            )
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تحديث سعر الخدمة: {e}")
            self.connection.rollback()
    
    def log_service_usage(self, user_id: int, service_id: int, cost: int = 0, 
                         details: str = ""):
        """تسجيل استخدام الخدمة"""
        try:
            self.cursor.execute('''
                INSERT INTO service_usage 
                (user_id, service_id, cost, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, service_id, cost, details))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تسجيل استخدام الخدمة: {e}")
            self.connection.rollback()
    
    def get_user_service_usage(self, user_id: int, service_id: int, 
                              days: int = 1) -> int:
        """الحصول على عدد استخدامات الخدمة للمستخدم"""
        try:
            self.cursor.execute('''
                SELECT COUNT(*) FROM service_usage
                WHERE user_id = ? AND service_id = ?
                  AND date(use_date) >= date('now', ?)
            ''', (user_id, service_id, f'-{days} days'))
            
            return self.cursor.fetchone()[0] or 0
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب استخدامات الخدمة: {e}")
            return 0
    
    # ========== دوال الملازم ==========
    def add_material(self, name: str, description: str, file_id: str, 
                    stage: str, subject: str, file_size: int, 
                    added_by: int = None) -> int:
        """إضافة مادة جديدة"""
        try:
            self.cursor.execute('''
                INSERT INTO materials 
                (name, description, file_id, stage, subject, file_size, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, file_id, stage, subject, file_size, added_by))
            
            self.connection.commit()
            material_id = self.cursor.lastrowid
            
            self.log_admin_action(
                added_by or Constants.ADMIN_ID, 'material_added',
                f'تم إضافة مادة: {name} - {stage}'
            )
            
            return material_id
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في إضافة المادة: {e}")
            self.connection.rollback()
            return 0
    
    def get_materials(self, stage: str = None, subject: str = None, 
                     limit: int = 50) -> List[Material]:
        """الحصول على الملازم"""
        try:
            query = 'SELECT * FROM materials WHERE is_active = 1'
            params = []
            
            if stage:
                query += ' AND stage = ?'
                params.append(stage)
            
            if subject:
                query += ' AND subject = ?'
                params.append(subject)
            
            query += ' ORDER BY stage, subject, name LIMIT ?'
            params.append(limit)
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            return [Material.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الملازم: {e}")
            return []
    
    def get_material(self, material_id: int) -> Optional[Material]:
        """الحصول على مادة معينة"""
        try:
            self.cursor.execute('SELECT * FROM materials WHERE id = ?', (material_id,))
            row = self.cursor.fetchone()
            
            if row:
                return Material.from_db_row(row)
            return None
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب المادة: {e}")
            return None
    
    def increment_material_downloads(self, material_id: int):
        """زيادة عدد تحميلات المادة"""
        try:
            self.cursor.execute('''
                UPDATE materials SET downloads = downloads + 1
                WHERE id = ?
            ''', (material_id,))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في زيادة تحميلات المادة: {e}")
            self.connection.rollback()
    
    def delete_material(self, material_id: int):
        """حذف مادة"""
        try:
            self.cursor.execute('DELETE FROM materials WHERE id = ?', (material_id,))
            self.connection.commit()
            
            self.log_admin_action(
                Constants.ADMIN_ID, 'material_deleted',
                f'تم حذف المادة {material_id}'
            )
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في حذف المادة: {e}")
            self.connection.rollback()
    
    # ========== دوال الإعدادات ==========
    def get_setting(self, key: str, default: str = "") -> str:
        """الحصول على إعداد"""
        try:
            self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = self.cursor.fetchone()
            
            if row:
                return row[0]
            return default
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الإعداد: {e}")
            return default
    
    def update_setting(self, key: str, value: str):
        """تحديث إعداد"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تحديث الإعداد: {e}")
            self.connection.rollback()
    
    def get_all_settings(self) -> Dict[str, str]:
        """الحصول على جميع الإعدادات"""
        try:
            self.cursor.execute('SELECT key, value FROM settings')
            rows = self.cursor.fetchall()
            
            return {row[0]: row[1] for row in rows}
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب جميع الإعدادات: {e}")
            return {}
    
    # ========== دوال المساعدة ==========
    def generate_referral_code(self) -> str:
        """إنشاء رمز إحالة فريد"""
        import time
        
        while True:
            # توليد رمز عشوائي
            timestamp = int(time.time() * 1000)
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"REF{timestamp % 10000:04d}{random_part}"
            
            # التحقق من التكرار
            self.cursor.execute('SELECT COUNT(*) FROM users WHERE referral_code = ?', (code,))
            if self.cursor.fetchone()[0] == 0:
                return code
    
    def check_referral_code(self, code: str) -> bool:
        """التحقق من صحة رمز الإحالة"""
        try:
            self.cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
            return self.cursor.fetchone() is not None
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في التحقق من رمز الإحالة: {e}")
            return False
    
    def process_referral(self, user_id: int, referrer_code: str) -> bool:
        """معالجة الإحالة"""
        try:
            # الحصول على بيانات المحيل
            self.cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referrer_code,))
            referrer = self.cursor.fetchone()
            
            if not referrer or referrer[0] == user_id:
                return False
            
            referrer_id = referrer[0]
            
            # تحديث بيانات المستخدم الجديد
            self.cursor.execute('''
                UPDATE users SET referred_by = ?
                WHERE user_id = ?
            ''', (referrer_code, user_id))
            
            # منح مكافأة المحيل
            referral_bonus = int(self.get_setting('referral_bonus', '500'))
            self.update_user_balance(referrer_id, referral_bonus)
            self.add_transaction(
                referrer_id, referral_bonus, 'referral_bonus',
                f'مكافأة إحالة للمستخدم {user_id}'
            )
            
            # منح الهدية الترحيبية للمستخدم الجديد
            welcome_bonus = int(self.get_setting('welcome_bonus', '1000'))
            self.update_user_balance(user_id, welcome_bonus)
            self.add_transaction(
                user_id, welcome_bonus, 'welcome_bonus',
                'هدية ترحيبية'
            )
            
            self.connection.commit()
            return True
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في معالجة الإحالة: {e}")
            self.connection.rollback()
            return False
    
    def log_admin_action(self, admin_id: int, action: str, details: str, 
                        target_id: int = None, ip_address: str = None):
        """تسجيل إجراء المدير"""
        try:
            self.cursor.execute('''
                INSERT INTO admin_logs 
                (admin_id, action, details, target_id, ip_address)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_id, action, details, target_id, ip_address))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تسجيل إجراء المدير: {e}")
            self.connection.rollback()
    
    def get_admin_logs(self, limit: int = 50) -> List[AdminLog]:
        """الحصول على سجلات المدير"""
        try:
            self.cursor.execute('''
                SELECT * FROM admin_logs 
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = self.cursor.fetchall()
            return [AdminLog.from_db_row(row) for row in rows]
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب سجلات المدير: {e}")
            return []
    
    def update_statistics(self):
        """تحديث الإحصائيات"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # الحصول على إحصائيات اليوم
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN date(join_date) = date('now') THEN 1 ELSE 0 END) as new_users,
                    SUM(CASE WHEN date(last_active) = date('now') THEN 1 ELSE 0 END) as active_users
                FROM users
            ''')
            user_stats = self.cursor.fetchone()
            
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses
                FROM transactions
                WHERE date(date) = date('now')
            ''')
            transaction_stats = self.cursor.fetchone()
            
            self.cursor.execute('''
                SELECT COUNT(*) as service_usage_count
                FROM service_usage
                WHERE date(use_date) = date('now')
            ''')
            service_stats = self.cursor.fetchone()
            
            # تحديث أو إدراج الإحصائيات
            self.cursor.execute('''
                INSERT OR REPLACE INTO statistics 
                (date, total_users, new_users, active_users, 
                 total_transactions, total_income, total_expenses, service_usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today,
                user_stats[0] or 0,
                user_stats[1] or 0,
                user_stats[2] or 0,
                transaction_stats[0] or 0,
                transaction_stats[1] or 0,
                transaction_stats[2] or 0,
                service_stats[0] or 0
            ))
            
            self.connection.commit()
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في تحديث الإحصائيات: {e}")
            self.connection.rollback()
    
    def get_statistics(self, days: int = 7) -> Dict:
        """الحصول على الإحصائيات"""
        try:
            self.cursor.execute('''
                SELECT * FROM statistics 
                WHERE date >= date('now', ?)
                ORDER BY date DESC
            ''', (f'-{days} days',))
            
            rows = self.cursor.fetchall()
            
            stats = {
                'total_users': self.get_user_count(),
                'total_balance': self.get_total_balance(),
                'total_income': self.get_total_income(),
                'daily_stats': []
            }
            
            for row in rows:
                stats['daily_stats'].append({
                    'date': row[1],
                    'total_users': row[2],
                    'new_users': row[3],
                    'active_users': row[4],
                    'total_transactions': row[5],
                    'total_income': row[6],
                    'total_expenses': row[7],
                    'service_usage_count': row[8]
                })
            
            return stats
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في جلب الإحصائيات: {e}")
            return {}
    
    def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("✅ تم إغلاق اتصال قاعدة البيانات")
            
        except SQLiteError as e:
            logger.error(f"❌ خطأ في إغلاق اتصال قاعدة البيانات: {e}")

# ========== نظام الذكاء الاصطناعي ==========
class AISystem:
    """نظام الذكاء الاصطناعي"""
    
    def __init__(self):
        self.api_key = AIConfig.GEMINI_API_KEY
        self.models = AIConfig.MODELS
        self.config = AIConfig.GENERATION_CONFIG
        self.safety_settings = AIConfig.SAFETY_SETTINGS
        self.prompts = AIConfig.PROMPTS
        
        # تهيئة الذكاء الاصطناعي
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.models['gemini_pro'],
                generation_config=GenerationConfig(**self.config),
                safety_settings=self.safety_settings
            )
            self.vision_model = genai.GenerativeModel(
                self.models['gemini_pro_vision'],
                generation_config=GenerationConfig(**self.config),
                safety_settings=self.safety_settings
            )
            logger.info("✅ تم تهيئة نظام الذكاء الاصطناعي")
        except Exception as e:
            logger.error(f"❌ فشل تهيئة الذكاء الاصطناعي: {e}")
            raise
    
    async def generate_text(self, prompt: str, max_tokens: int = 2000) -> str:
        """توليد نص باستخدام الذكاء الاصطناعي"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7
                )
            )
            
            if response and response.text:
                return response.text.strip()
            return "⚠️ لم أتمكن من توليد إجابة مناسبة. الرجاء المحاولة مرة أخرى."
            
        except Exception as e:
            logger.error(f"❌ خطأ في توليد النص: {e}")
            return f"⚠️ حدث خطأ في الذكاء الاصطناعي: {str(e)}"
    
    async def summarize_pdf(self, pdf_text: str, filename: str = "") -> str:
        """تلخيص نص PDF"""
        try:
            prompt = self.prompts['summary'] + f"\n\nالنص المراد تلخيصه:\n{pdf_text[:15000]}"
            
            if filename:
                prompt += f"\n\nاسم الملف: {filename}"
            
            response = await self.generate_text(prompt, max_tokens=3000)
            
            # تحسين التنسيق
            if "ملخص" not in response and "تلخيص" not in response:
                response = "📋 **ملخص الملف:**\n\n" + response
            
            return response
            
        except Exception as e:
            logger.error(f"❌ خطأ في تلخيص PDF: {e}")
            return f"⚠️ حدث خطأ في تلخيص الملف: {str(e)}"
    
    async def answer_question(self, question: str, is_image: bool = False, 
                            image_data: bytes = None) -> str:
        """الإجابة على سؤال"""
        try:
            if is_image and image_data:
                # معالجة الصورة
                prompt = self.prompts['qa'] + "\n\nما هو السؤال أو النص في هذه الصورة؟ أجب بشكل مفصل."
                
                image = Image.open(io.BytesIO(image_data))
                response = await asyncio.to_thread(
                    self.vision_model.generate_content,
                    [prompt, image]
                )
                
                if response and response.text:
                    return response.text.strip()
            else:
                # معالجة النص
                prompt = self.prompts['qa'] + f"\n\nالسؤال:\n{question}"
                response = await self.generate_text(prompt)
                return response
            
            return "⚠️ لم أتمكن من فهم السؤال. الرجاء إعادة المحاولة."
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإجابة على السؤال: {e}")
            return f"⚠️ حدث خطأ في معالجة السؤال: {str(e)}"
    
    async def calculate_excuse(self, scores: List[float]) -> Dict:
        """حساب درجة العفو"""
        try:
            if len(scores) != 3:
                return {"error": "الرجاء إدخال 3 درجات"}
            
            # التحقق من صحة الدرجات
            for score in scores:
                if score < 0 or score > 100:
                    return {"error": "الدرجات يجب أن تكون بين 0 و 100"}
            
            # حساب المعدل
            average = sum(scores) / 3
            
            # تحديد النتيجة
            result = {
                "average": average,
                "is_excused": average >= 90,
                "scores": scores,
                "message": "",
                "details": ""
            }
            
            if result["is_excused"]:
                result["message"] = "🎉 **مبروك! أنت معفى من المادة!**"
                result["details"] = (
                    f"المعدل النهائي: {average:.2f}%\n"
                    f"شروط الإعفاء: 90% أو أعلى ✅\n"
                    f"الدرجات المدخلة: {scores[0]}, {scores[1]}, {scores[2]}\n"
                    f"المعدل الحسابي: {average:.2f}%\n\n"
                    f"تهانينا على هذا الإنجاز! 🏆"
                )
            else:
                needed = 90 - average
                result["message"] = "⚠️ **للأسف، أنت غير معفى من المادة.**"
                result["details"] = (
                    f"المعدل النهائي: {average:.2f}%\n"
                    f"شروط الإعفاء: 90% أو أعلى ❌\n"
                    f"الدرجات المدخلة: {scores[0]}, {scores[1]}, {scores[2]}\n"
                    f"المعدل الحسابي: {average:.2f}%\n"
                    f"تحتاج إلى: {needed:.2f}% إضافية للإعفاء\n\n"
                    f"لا تيأس! استمر في المذاكرة وحاول مرة أخرى. 💪"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ خطأ في حساب درجة العفو: {e}")
            return {"error": f"حدث خطأ في الحساب: {str(e)}"}
    
    async def analyze_material(self, content: str) -> str:
        """تحليل المادة التعليمية"""
        try:
            prompt = self.prompts['material_analysis'] + f"\n\nالمحتوى:\n{content[:10000]}"
            response = await self.generate_text(prompt, max_tokens=2500)
            return response
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل المادة: {e}")
            return f"⚠️ حدث خطأ في تحليل المادة: {str(e)}"

# ========== نظام PDF ==========
class PDFSystem:
    """نظام معالجة ملفات PDF"""
    
    def __init__(self):
        self.fonts_dir = Constants.FONTS_DIR
        self.setup_fonts()
    
    def setup_fonts(self):
        """إعداد الخطوط"""
        try:
            # إنشاء مجلد الخطوط إذا لم يكن موجوداً
            os.makedirs(self.fonts_dir, exist_ok=True)
            
            # تسجيل الخطوط العربية
            arabic_fonts = ['arial.ttf', 'tahoma.ttf', 'times.ttf']
            
            for font_name in arabic_fonts:
                font_path = os.path.join(self.fonts_dir, font_name)
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Arabic_' + font_name[:-4], font_path))
                        logger.info(f"✅ تم تسجيل الخط: {font_name}")
                    except:
                        pass
            
            # استخدام خط افتراضي إذا فشل تسجيل الخطوط العربية
            if not pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
            
        except Exception as e:
            logger.error(f"❌ خطأ في إعداد الخطوط: {e}")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """استخراج النص من ملف PDF"""
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    # تحسين النص العربي
                    page_text = self._fix_arabic_text(page_text)
                    text += page_text + "\n\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ خطأ في استخراج النص من PDF: {e}")
            return ""
    
    def _fix_arabic_text(self, text: str) -> str:
        """إصلاح النص العربي"""
        try:
            # إعادة تشكيل النص العربي
            reshaped_text = arabic_reshaper.reshape(text)
            fixed_text = get_display(reshaped_text)
            return fixed_text
            
        except:
            return text
    
    def create_summary_pdf(self, summary_text: str, original_filename: str, 
                          user_data: UserData) -> bytes:
        """إنشاء ملف PDF للتلخيص"""
        try:
            buffer = io.BytesIO()
            
            # إنشاء مستند PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # الأنماط
            styles = getSampleStyleSheet()
            
            # أنماط مخصصة للغة العربية
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Title'],
                fontName='Arabic',
                fontSize=16,
                alignment=TA_CENTER,
                textColor=HexColor('#2E86C1'),
                spaceAfter=20
            )
            
            subtitle_style = ParagraphStyle(
                'ArabicSubtitle',
                parent=styles['Heading2'],
                fontName='Arabic',
                fontSize=14,
                alignment=TA_CENTER,
                textColor=HexColor('#17A589'),
                spaceAfter=15
            )
            
            normal_style = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=12,
                alignment=TA_JUSTIFY,
                textColor=black,
                spaceAfter=10
            )
            
            header_style = ParagraphStyle(
                'ArabicHeader',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_RIGHT,
                textColor=HexColor('#7F8C8D'),
                spaceAfter=5
            )
            
            # المحتوى
            content = []
            
            # العنوان الرئيسي
            title = Paragraph("📋 ملخص الملف التعليمي", title_style)
            content.append(title)
            
            # معلومات الملف
            file_info = Paragraph(
                f"📄 الملف الأصلي: {original_filename}",
                subtitle_style
            )
            content.append(file_info)
            
            # معلومات المستخدم والتاريخ
            user_info = Paragraph(
                f"👤 المستخدم: {user_data.first_name} {user_data.last_name or ''}<br/>"
                f"🆔 المعرف: {user_data.user_id}<br/>"
                f"📅 تاريخ التلخيص: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                header_style
            )
            content.append(user_info)
            
            content.append(Spacer(1, 20))
            
            # إضافة خط فاصل
            content.append(self._create_divider())
            
            content.append(Spacer(1, 20))
            
            # النص الملخص
            summary_paragraphs = summary_text.split('\n')
            for para in summary_paragraphs:
                if para.strip():
                    # تنظيف الفقرات
                    clean_para = para.strip()
                    # إعادة تشكيل النص العربي
                    clean_para = self._fix_arabic_text(clean_para)
                    
                    paragraph = Paragraph(clean_para, normal_style)
                    content.append(paragraph)
                    content.append(Spacer(1, 8))
            
            content.append(Spacer(1, 30))
            
            # تذييل الصفحة
            footer = Paragraph(
                "📌 تم إنشاء هذا الملخص بواسطة بوت 'يلا نتعلم'<br/>"
                "🎓 البوت التعليمي الأول للطلاب العراقيين<br/>"
                "📞 للتواصل: @Allawi04@",
                header_style
            )
            content.append(footer)
            
            # إنشاء PDF
            doc.build(content)
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء ملف PDF: {e}")
            return None
    
    def _create_divider(self) -> Flowable:
        """إنشاء خط فاصل"""
        from reportlab.platypus.flowables import HRFlowable
        return HRFlowable(
            width="100%",
            thickness=2,
            color=HexColor('#3498DB'),
            spaceBefore=10,
            spaceAfter=10
        )
    
    def create_excuse_certificate(self, result: Dict, user_data: UserData) -> bytes:
        """إنشاء شهادة الإعفاء"""
        try:
            buffer = io.BytesIO()
            
            # إنشاء صفحة أفقية
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                rightMargin=3*cm,
                leftMargin=3*cm,
                topMargin=3*cm,
                bottomMargin=3*cm
            )
            
            # الأنماط
            styles = getSampleStyleSheet()
            
            cert_style = ParagraphStyle(
                'CertificateStyle',
                parent=styles['Title'],
                fontName='Arabic',
                fontSize=24,
                alignment=TA_CENTER,
                textColor=HexColor('#2C3E50'),
                spaceAfter=30
            )
            
            name_style = ParagraphStyle(
                'NameStyle',
                parent=styles['Heading1'],
                fontName='Arabic',
                fontSize=32,
                alignment=TA_CENTER,
                textColor=HexColor('#E74C3C'),
                spaceAfter=20
            )
            
            result_style = ParagraphStyle(
                'ResultStyle',
                parent=styles['Heading2'],
                fontName='Arabic',
                fontSize=20,
                alignment=TA_CENTER,
                textColor=HexColor('#27AE60'),
                spaceAfter=15
            )
            
            details_style = ParagraphStyle(
                'DetailsStyle',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=14,
                alignment=TA_CENTER,
                textColor=HexColor('#7F8C8D'),
                spaceAfter=10
            )
            
            # المحتوى
            content = []
            
            # العنوان
            title = Paragraph("🏆 شهادة حساب المعدل", cert_style)
            content.append(title)
            
            content.append(Spacer(1, 40))
            
            # اسم المستخدم
            name = Paragraph(
                f"الطالب: {user_data.first_name} {user_data.last_name or ''}",
                name_style
            )
            content.append(name)
            
            content.append(Spacer(1, 30))
            
            # النتيجة
            if result.get('is_excused'):
                result_text = "🎉 نتيجتك: معفى من المادة ✅"
                result_color = HexColor('#27AE60')
            else:
                result_text = "📊 نتيجتك: غير معفى من المادة"
                result_color = HexColor('#E74C3C')
            
            result_style.textColor = result_color
            result_para = Paragraph(result_text, result_style)
            content.append(result_para)
            
            content.append(Spacer(1, 25))
            
            # التفاصيل
            details = Paragraph(
                f"📈 المعدل النهائي: {result.get('average', 0):.2f}%<br/>"
                f"🎯 الدرجات: {', '.join(map(str, result.get('scores', [])))}<br/>"
                f"📅 تاريخ الحساب: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                details_style
            )
            content.append(details)
            
            content.append(Spacer(1, 40))
            
            # الرسالة
            message = Paragraph(
                result.get('message', ''),
                ParagraphStyle(
                    'MessageStyle',
                    parent=styles['Normal'],
                    fontName='Arabic',
                    fontSize=16,
                    alignment=TA_CENTER,
                    textColor=HexColor('#2C3E50'),
                    spaceAfter=20
                )
            )
            content.append(message)
            
            content.append(Spacer(1, 50))
            
            # التذييل
            footer = Paragraph(
                "📌 تم إنشاء هذه الشهادة بواسطة بوت 'يلا نتعلم'<br/>"
                "🎓 البوت التعليمي الأول للطلاب العراقيين",
                details_style
            )
            content.append(footer)
            
            # إنشاء PDF
            doc.build(content)
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء شهادة الإعفاء: {e}")
            return None

# ========== مدير البوت الرئيسي ==========
class YallaNt3lemBot:
    """الفئة الرئيسية للبوت"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ai = AISystem()
        self.pdf = PDFSystem()
        
        # إعدادات البوت
        self.token = Constants.TOKEN
        self.bot_username = Constants.BOT_USERNAME
        self.admin_id = Constants.ADMIN_ID
        self.support_username = Constants.SUPPORT_USERNAME
        
        # جلسات المستخدمين
        self.user_sessions = {}
        self.admin_commands = {}
        self.user_states = {}
        
        # لوحة المفاتيح الرئيسية
        self.main_keyboard = self.create_main_keyboard()
        
        # إعدادات التطبيق
        self.application = None
        self.job_queue = None
        
        # إنشاء المجلدات
        self._create_directories()
        
        logger.info("✅ تم تهيئة البوت بنجاح")
    
    def _create_directories(self):
        """إنشاء المجلدات المطلوبة"""
        directories = [
            Constants.LOGS_DIR,
            Constants.FONTS_DIR,
            Constants.MATERIALS_DIR,
            Constants.TEMP_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    # ========== لوحة المفاتيح الرئيسية ==========
    def create_main_keyboard(self) -> ReplyKeyboardMarkup:
        """إنشاء لوحة المفاتيح الرئيسية فوق الرسائل"""
        keyboard = [
            ["🎓 خدمات البوت", "💰 رصيدي"],
            ["📚 الملازم", "👥 دعوة أصدقاء"],
            ["🛠 الدعم الفني", "ℹ️ المساعدة"],
            ["🏠 القائمة الرئيسية"]
        ]
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_admin_keyboard(self) -> ReplyKeyboardMarkup:
        """إنشاء لوحة مفاتيح المدير"""
        keyboard = [
            ["👑 لوحة التحكم", "📊 الإحصائيات"],
            ["👥 إدارة المستخدمين", "💰 إدارة الشحن"],
            ["⚙️ إدارة الخدمات", "📚 إدارة الملازم"],
            ["🏠 القائمة الرئيسية"]
        ]
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_services_keyboard(self) -> ReplyKeyboardMarkup:
        """إنشاء لوحة مفاتيح الخدمات"""
        keyboard = [
            ["📊 حساب درجة العفو", "📝 تلخيص الملازم"],
            ["❓ سؤال وجواب", "📚 الملازم المجانية"],
            ["🔙 رجوع"]
        ]
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_materials_keyboard(self) -> ReplyKeyboardMarkup:
        """إنشاء لوحة مفاتيح الملازم"""
        keyboard = [
            ["📚 المرحلة الابتدائية", "📚 المرحلة المتوسطة"],
            ["📚 المرحلة الإعدادية", "📚 المرحلة الثانوية"],
            ["🔍 بحث عن مادة", "🔙 رجوع"]
        ]
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # ========== دوال المساعدة ==========
    def is_admin(self, user_id: int) -> bool:
        """التحقق إذا كان المستخدم مديراً"""
        return user_id == self.admin_id
    
    def get_emoji(self, key: str) -> str:
        """الحصول على رمز تعبيري"""
        return Constants.EMOJIS.get(key, '')
    
    def format_arabic_text(self, text: str) -> str:
        """تنسيق النص العربي"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            formatted_text = get_display(reshaped_text)
            return formatted_text
        except:
            return text
    
    def format_currency(self, amount: int) -> str:
        """تنسيق المبلغ"""
        currency = self.db.get_setting('currency_symbol', 'د.ع')
        return f"{amount:,} {currency}"
    
    async def send_typing(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """إرسال مؤشر الكتابة"""
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING
            )
        except:
            pass
    
    async def check_user_balance(self, user_id: int, service_price: int) -> Tuple[bool, int]:
        """التحقق من رصيد المستخدم"""
        user = self.db.get_user(user_id)
        if not user:
            return False, 0
        
        return user.balance >= service_price, user.balance
    
    async def deduct_service_cost(self, user_id: int, service_id: int, 
                                 service_name: str) -> bool:
        """خصم تكلفة الخدمة"""
        try:
            service = self.db.get_service(service_id)
            if not service or service.price <= 0:
                return True
            
            user = self.db.get_user(user_id)
            if not user or user.balance < service.price:
                return False
            
            # خصم المبلغ
            self.db.update_user_balance(user_id, -service.price)
            
            # تسجيل المعاملة
            self.db.add_transaction(
                user_id, -service.price, 'service_payment',
                f'دفع مقابل خدمة: {service_name}'
            )
            
            # تسجيل استخدام الخدمة
            self.db.log_service_usage(
                user_id, service_id, service.price,
                f'استخدام خدمة: {service_name}'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في خصم تكلفة الخدمة: {e}")
            return False
    
    # ========== دوال البداية والترحيب ==========
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دالة البداية"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # التحقق من وضع الصيانة
        maintenance_mode = self.db.get_setting('maintenance_mode', 'false') == 'true'
        if maintenance_mode and not self.is_admin(user_id):
            text = self.format_arabic_text(
                "⛔ **البوت تحت الصيانة حالياً**\n\n"
                "نعمل على تحسين الخدمات وإضافة ميزات جديدة.\n"
                "الرجاء المحاولة مرة أخرى لاحقاً.\n\n"
                "🛠 للاستفسار: @Allawi04@"
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.main_keyboard
            )
            return
        
        # التحقق من الحظر
        user_data = self.db.get_user(user_id)
        if user_data and user_data.is_banned:
            text = self.format_arabic_text(
                "⛔ **حسابك محظور**\n\n"
                "لا يمكنك استخدام البوت حالياً.\n"
                "للتواصل مع الدعم: @Allawi04@"
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.main_keyboard
            )
            return
        
        # إضافة المستخدم الجديد
        if not user_data:
            referral_code = ""
            if context.args and len(context.args) > 0:
                referral_code = context.args[0]
            
            # إضافة المستخدم
            new_referral_code = self.db.add_user(
                user_id, user.username, user.first_name, user.last_name
            )
            
            # معالجة الإحالة
            if referral_code and referral_code != new_referral_code:
                success = self.db.process_referral(user_id, referral_code)
                if success:
                    # إرسال إشعار للمحيل
                    referrer = self.db.get_user_by_referral_code(referral_code)
                    if referrer:
                        try:
                            await context.bot.send_message(
                                chat_id=referrer.user_id,
                                text=self.format_arabic_text(
                                    f"🎉 **تمت إحالة مستخدم جديد!**\n\n"
                                    f"👤 المستخدم: {user.first_name}\n"
                                    f"🆔 المعرف: {user_id}\n"
                                    f"💰 المكافأة: {self.db.get_setting('referral_bonus', '500')} دينار\n\n"
                                    f"شكراً لدعمك البوت! 🤝"
                                ),
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except:
                            pass
        
        # تحديث آخر نشاط
        self.db.update_user(user_id, last_active=datetime.datetime.now().isoformat())
        
        # اختيار لوحة المفاتيح المناسبة
        keyboard = self.main_keyboard
        if self.is_admin(user_id):
            keyboard = self.create_admin_keyboard()
        
        # النص الترحيبي
        user_data = self.db.get_user(user_id)
        welcome_text = self.format_arabic_text(
            f"🎓 **مرحباً بك في بوت 'يلا نتعلم'**\n\n"
            f"👤 **أهلاً {user_data.first_name if user_data else user.first_name}!**\n"
            f"💰 **رصيدك:** {self.format_currency(user_data.balance) if user_data else '0 د.ع'}\n\n"
            f"**الخدمات المتاحة:**\n"
            f"• 📊 حساب درجة العفو\n"
            f"• 📝 تلخيص الملازم بالذكاء الاصطناعي\n"
            f"• ❓ سؤال وجواب دراسي\n"
            f"• 📚 ملازم ومرشحات مجانية\n\n"
            f"اختر الخدمة التي تريدها من الأزرار أدناه 👇"
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض القائمة الرئيسية"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # التحقق من وضع الصيانة والحظر
        maintenance_mode = self.db.get_setting('maintenance_mode', 'false') == 'true'
        user_data = self.db.get_user(user_id)
        
        if maintenance_mode and not self.is_admin(user_id):
            await update.message.reply_text(
                self.format_arabic_text("⛔ البوت تحت الصيانة حالياً."),
                reply_markup=self.main_keyboard
            )
            return
        
        if user_data and user_data.is_banned:
            await update.message.reply_text(
                self.format_arabic_text("⛔ حسابك محظور."),
                reply_markup=self.main_keyboard
            )
            return
        
        # تحديث آخر نشاط
        if user_data:
            self.db.update_user(user_id, last_active=datetime.datetime.now().isoformat())
        
        # اختيار لوحة المفاتيح المناسبة
        keyboard = self.main_keyboard
        if self.is_admin(user_id):
            keyboard = self.create_admin_keyboard()
        
        # النص الرئيسي
        menu_text = self.format_arabic_text(
            f"🏠 **القائمة الرئيسية**\n\n"
            f"اختر الخدمة التي تريدها من الأزرار أدناه:\n\n"
            f"🎓 **خدمات البوت:**\n"
            f"• حساب درجة العفو\n"
            f"• تلخيص الملازم\n"
            f"• سؤال وجواب\n\n"
            f"💰 **الحساب:**\n"
            f"• رصيدي\n"
            f"• دعوة أصدقاء\n\n"
            f"📚 **المواد التعليمية:**\n"
            f"• الملازم والمرشحات\n\n"
            f"🛠 **الدعم:**\n"
            f"• الدعم الفني\n"
            f"• المساعدة"
        )
        
        await update.message.reply_text(
            menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # ========== معالجة الأزرار فوق الرسائل ==========
    async def handle_text_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية والأزرار"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text
        
        await self.send_typing(user_id, context)
        
        # التحقق من وضع الصيانة والحظر
        maintenance_mode = self.db.get_setting('maintenance_mode', 'false') == 'true'
        user_data = self.db.get_user(user_id)
        
        if maintenance_mode and not self.is_admin(user_id):
            await update.message.reply_text(
                self.format_arabic_text("⛔ البوت تحت الصيانة حالياً."),
                reply_markup=self.main_keyboard
            )
            return
        
        if user_data and user_data.is_banned:
            await update.message.reply_text(
                self.format_arabic_text("⛔ حسابك محظور."),
                reply_markup=self.main_keyboard
            )
            return
        
        # تحديث آخر نشاط
        if user_data:
            self.db.update_user(user_id, last_active=datetime.datetime.now().isoformat())
        
        # معالجة الأزرار بناءً على النص
        if text == "🏠 القائمة الرئيسية":
            await self.menu_command(update, context)
        
        elif text == "🎓 خدمات البوت":
            await self.show_services_menu(update, context)
        
        elif text == "💰 رصيدي":
            await self.show_balance_info(update, context)
        
        elif text == "📚 الملازم":
            await self.show_materials_menu(update, context)
        
        elif text == "👥 دعوة أصدقاء":
            await self.show_invite_friends(update, context)
        
        elif text == "🛠 الدعم الفني":
            await self.show_support_info(update, context)
        
        elif text == "ℹ️ المساعدة":
            await self.show_help_info(update, context)
        
        elif text == "🔙 رجوع":
            await self.menu_command(update, context)
        
        # خدمات البوت
        elif text == "📊 حساب درجة العفو":
            await self.handle_excuse_service_button(update, context)
        
        elif text == "📝 تلخيص الملازم":
            await self.handle_summary_service_button(update, context)
        
        elif text == "❓ سؤال وجواب":
            await self.handle_qa_service_button(update, context)
        
        elif text == "📚 الملازم المجانية":
            await self.show_materials_menu(update, context)
        
        # لوحة تحكم المدير
        elif text == "👑 لوحة التحكم" and self.is_admin(user_id):
            await self.show_admin_panel(update, context)
        
        elif text == "📊 الإحصائيات" and self.is_admin(user_id):
            await self.show_admin_stats(update, context)
        
        elif text == "👥 إدارة المستخدمين" and self.is_admin(user_id):
            await self.show_admin_users_menu(update, context)
        
        elif text == "💰 إدارة الشحن" and self.is_admin(user_id):
            await self.show_admin_charge_menu(update, context)
        
        elif text == "⚙️ إدارة الخدمات" and self.is_admin(user_id):
            await self.show_admin_services_menu(update, context)
        
        elif text == "📚 إدارة الملازم" and self.is_admin(user_id):
            await self.show_admin_materials_menu(update, context)
        
        # معالجة الملازم
        elif text in ["📚 المرحلة الابتدائية", "📚 المرحلة المتوسطة", 
                     "📚 المرحلة الإعدادية", "📚 المرحلة الثانوية"]:
            stage = text.replace("📚 ", "")
            await self.show_materials_by_stage_button(update, context, stage)
        
        elif text == "🔍 بحث عن مادة":
            await self.show_search_material(update, context)
        
        # معالجة جلسات المستخدمين
        elif user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            
            if session['service'] == 'excuse' and session.get('waiting_for_score'):
                await self.handle_excuse_score_input(update, context)
                return
            
            elif session['service'] == 'qa' and session.get('waiting_for_question'):
                await self.handle_qa_question_input(update, context)
                return
            
            elif session['service'] == 'summary' and session.get('waiting_for_file'):
                # يتم التعامل معه في handle_document_messages
                pass
        
        # إذا كان النص غير معروف، عرض القائمة
        else:
            await self.menu_command(update, context)
    
    # ========== دوال الخدمات ==========
    async def show_services_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الخدمات"""
        user = update.effective_user
        user_id = user.id
        
        # الحصول على خدمات البوت
        services = self.db.get_services(active_only=True)
        
        services_text = ""
        for service in services:
            price_text = "مجاناً" if service.price == 0 else f"{self.format_currency(service.price)}"
            services_text += f"• **{service.name}:** {price_text}\n"
            if service.description:
                services_text += f"  _{service.description}_\n"
        
        text = self.format_arabic_text(
            f"🎓 **خدمات البوت التعليمية**\n\n"
            f"اختر الخدمة التي تريدها:\n\n"
            f"{services_text}\n"
            f"💡 **ملاحظة:** بعض الخدمات مدفوعة وتحتاج إلى رصيد كافٍ."
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.create_services_keyboard()
        )
    
    async def handle_excuse_service_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة زر خدمة حساب درجة العفو"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على الخدمة
        service = self.db.get_service_by_name('حساب درجة العفو')
        if not service:
            await update.message.reply_text(
                self.format_arabic_text("⚠️ الخدمة غير متاحة حالياً."),
                reply_markup=self.create_services_keyboard()
            )
            return
        
        # التحقق من الرصيد
        has_balance, current_balance = await self.check_user_balance(user_id, service.price)
        if not has_balance:
            text = self.format_arabic_text(
                f"💰 **رصيدك غير كافٍ**\n\n"
                f"سعر الخدمة: {self.format_currency(service.price)}\n"
                f"رصيدك الحالي: {self.format_currency(current_balance)}\n\n"
                f"الرجاء شحن رصيدك أولاً."
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=ReplyKeyboardMarkup([
                    ["💰 شحن الرصيد", "🔙 رجوع"]
                ], resize_keyboard=True)
            )
            return
        
        # بدء جلسة الخدمة
        self.user_sessions[user_id] = {
            'service': 'excuse',
            'service_id': service.id,
            'scores': [],
            'step': 1,
            'waiting_for_score': True
        }
        
        text = self.format_arabic_text(
            f"📊 **حساب درجة العفو الفردي**\n\n"
            f"💰 السعر: {self.format_currency(service.price)}\n"
            f"📝 ستقوم بإدخال 3 درجات (الكورسات الثلاثة)\n\n"
            f"**الخطوة 1/3:**\n"
            f"أدخل درجة الكورس الأول (من 0 إلى 100):"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_excuse_score_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال درجات العفو"""
        user = update.effective_user
        user_id = user.id
        
        # التحقق من الجلسة
        if user_id not in self.user_sessions or self.user_sessions[user_id]['service'] != 'excuse':
            await self.menu_command(update, context)
            return
        
        session = self.user_sessions[user_id]
        text = update.message.text.strip()
        
        # التحقق من صحة الدرجة
        try:
            score = float(text)
            if score < 0 or score > 100:
                raise ValueError
        except:
            await update.message.reply_text(
                self.format_arabic_text(
                    "⚠️ **الرجاء إدخال درجة صحيحة بين 0 و 100:**"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # حفظ الدرجة
        session['scores'].append(score)
        session['step'] += 1
        
        if session['step'] <= 3:
            # طلب الدرجة التالية
            await update.message.reply_text(
                self.format_arabic_text(
                    f"**الخطوة {session['step']}/3:**\n"
                    f"أدخل درجة الكورس {session['step']} (من 0 إلى 100):"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # حساب النتيجة
            await self.send_typing(user_id, context)
            
            result = await self.ai.calculate_excuse(session['scores'])
            
            if 'error' in result:
                await update.message.reply_text(
                    self.format_arabic_text(f"⚠️ {result['error']}"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.create_services_keyboard()
                )
                del self.user_sessions[user_id]
                return
            
            # خصم تكلفة الخدمة
            success = await self.deduct_service_cost(
                user_id, session['service_id'], 'حساب درجة العفو'
            )
            
            if not success:
                await update.message.reply_text(
                    self.format_arabic_text("⚠️ حدث خطأ في معالجة الدفع."),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.create_services_keyboard()
                )
                del self.user_sessions[user_id]
                return
            
            # عرض النتيجة
            user_data = self.db.get_user(user_id)
            result_text = self.format_arabic_text(
                f"{result['message']}\n\n"
                f"{result['details']}\n\n"
                f"💰 **تم خصم:** {self.format_currency(self.db.get_service(session['service_id']).price)}\n"
                f"💳 **الرصيد المتبقي:** {self.format_currency(user_data.balance)}"
            )
            
            # إنشاء شهادة PDF
            pdf_bytes = self.pdf.create_excuse_certificate(result, user_data)
            
            if pdf_bytes:
                # إرسال الشهادة كملف
                pdf_file = io.BytesIO(pdf_bytes)
                pdf_file.name = f"شهادة_العفو_{user_id}_{int(time.time())}.pdf"
                
                await update.message.reply_document(
                    document=pdf_file,
                    caption=result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # إرسال النتيجة فقط
                await update.message.reply_text(
                    result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # حذف الجلسة
            del self.user_sessions[user_id]
            
            # عرض لوحة المفاتيح
            await update.message.reply_text(
                self.format_arabic_text("اختر خدمة أخرى:"),
                reply_markup=self.create_services_keyboard()
            )
    
    async def handle_summary_service_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة زر خدمة تلخيص الملازم"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على الخدمة
        service = self.db.get_service_by_name('تلخيص الملازم')
        if not service:
            await update.message.reply_text(
                self.format_arabic_text("⚠️ الخدمة غير متاحة حالياً."),
                reply_markup=self.create_services_keyboard()
            )
            return
        
        # التحقق من الرصيد
        has_balance, current_balance = await self.check_user_balance(user_id, service.price)
        if not has_balance:
            text = self.format_arabic_text(
                f"💰 **رصيدك غير كافٍ**\n\n"
                f"سعر الخدمة: {self.format_currency(service.price)}\n"
                f"رصيدك الحالي: {self.format_currency(current_balance)}\n\n"
                f"الرجاء شحن رصيدك أولاً."
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=ReplyKeyboardMarkup([
                    ["💰 شحن الرصيد", "🔙 رجوع"]
                ], resize_keyboard=True)
            )
            return
        
        # بدء جلسة الخدمة
        self.user_sessions[user_id] = {
            'service': 'summary',
            'service_id': service.id,
            'waiting_for_file': True
        }
        
        text = self.format_arabic_text(
            f"📝 **خدمة تلخيص الملازم**\n\n"
            f"💰 السعر: {self.format_currency(service.price)}\n"
            f"🤖 يتم التلخيص باستخدام الذكاء الاصطناعي المتقدم\n\n"
            f"**أرسل الآن ملف PDF المراد تلخيصه:**\n\n"
            f"📎 **الحد الأقصى لحجم الملف:** 20 ميجابايت\n"
            f"⏱️ **الوقت المتوقع:** 1-3 دقائق\n\n"
            f"للإلغاء، اضغط على زر '🔙 رجوع'"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    async def handle_qa_service_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة زر خدمة سؤال وجواب"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على الخدمة
        service = self.db.get_service_by_name('سؤال وجواب')
        if not service:
            await update.message.reply_text(
                self.format_arabic_text("⚠️ الخدمة غير متاحة حالياً."),
                reply_markup=self.create_services_keyboard()
            )
            return
        
        # التحقق من الرصيد
        has_balance, current_balance = await self.check_user_balance(user_id, service.price)
        if not has_balance:
            text = self.format_arabic_text(
                f"💰 **رصيدك غير كافٍ**\n\n"
                f"سعر الخدمة: {self.format_currency(service.price)}\n"
                f"رصيدك الحالي: {self.format_currency(current_balance)}\n\n"
                f"الرجاء شحن رصيدك أولاً."
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=ReplyKeyboardMarkup([
                    ["💰 شحن الرصيد", "🔙 رجوع"]
                ], resize_keyboard=True)
            )
            return
        
        # بدء جلسة الخدمة
        self.user_sessions[user_id] = {
            'service': 'qa',
            'service_id': service.id,
            'waiting_for_question': True
        }
        
        text = self.format_arabic_text(
            f"❓ **خدمة سؤال وجواب**\n\n"
            f"💰 السعر: {self.format_currency(service.price)}\n"
            f"🤖 يتم الإجابة باستخدام الذكاء الاصطناعي المتقدم\n\n"
            f"**أرسل الآن سؤالك نصياً أو كصورة:**\n\n"
            f"🎯 **التخصص:** المنهج العراقي والمواد الدراسية\n"
            f"⏱️ **الوقت المتوقع:** 30-60 ثانية\n\n"
            f"للإلغاء، اضغط على زر '🔙 رجوع'"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    async def handle_qa_question_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال سؤال وجواب"""
        user = update.effective_user
        user_id = user.id
        
        # التحقق من الجلسة
        if user_id not in self.user_sessions or not self.user_sessions[user_id].get('waiting_for_question'):
            await self.menu_command(update, context)
            return
        
        session = self.user_sessions[user_id]
        
        await self.send_typing(user_id, context)
        
        # إرسال رسالة الانتظار
        processing_msg = await update.message.reply_text(
            self.format_arabic_text("🤖 **جاري معالجة سؤالك...**"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            question = update.message.text.strip()
            
            # الحصول على الإجابة من الذكاء الاصطناعي
            answer = await self.ai.answer_question(question, is_image=False)
            
            # خصم تكلفة الخدمة
            success = await self.deduct_service_cost(
                user_id, session['service_id'], 'سؤال وجواب'
            )
            
            if not success:
                await processing_msg.edit_text(
                    self.format_arabic_text("⚠️ **حدث خطأ في معالجة الدفع.**"),
                    parse_mode=ParseMode.MARKDOWN
                )
                del self.user_sessions[user_id]
                await self.menu_command(update, context)
                return
            
            await processing_msg.edit_text(
                self.format_arabic_text("📝 **جاري إعداد الإجابة...**"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # إرسال الإجابة
            user_data = self.db.get_user(user_id)
            
            # تقسيم الإجابة إذا كانت طويلة
            if len(answer) > 4000:
                parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                
                for i, part in enumerate(parts, 1):
                    if i == 1:
                        header = self.format_arabic_text(
                            f"🧠 **إجابتي على سؤالك:**\n\n"
                            f"{part}\n\n"
                            f"📄 الصفحة {i}/{len(parts)}"
                        )
                        await processing_msg.delete()
                        await update.message.reply_text(
                            header,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await update.message.reply_text(
                            self.format_arabic_text(
                                f"{part}\n\n"
                                f"📄 الصفحة {i}/{len(parts)}"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
            else:
                full_answer = self.format_arabic_text(
                    f"🧠 **إجابتي على سؤالك:**\n\n"
                    f"{answer}\n\n"
                    f"💰 **تم خصم:** {self.format_currency(self.db.get_service(session['service_id']).price)}\n"
                    f"💳 **الرصيد المتبقي:** {self.format_currency(user_data.balance)}\n\n"
                    f"🎓 **بوت 'يلا نتعلم'**"
                )
                
                await processing_msg.delete()
                await update.message.reply_text(
                    full_answer,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # حذف الجلسة
            del self.user_sessions[user_id]
            
            # عرض لوحة المفاتيح
            await update.message.reply_text(
                self.format_arabic_text("اختر خدمة أخرى:"),
                reply_markup=self.create_services_keyboard()
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة سؤال وجواب: {e}")
            await processing_msg.edit_text(
                self.format_arabic_text(
                    f"⚠️ **حدث خطأ أثناء معالجة سؤالك:**\n{str(e)[:200]}"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            del self.user_sessions[user_id]
            await self.menu_command(update, context)
    
    # ========== دوال الملازم ==========
    async def show_materials_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الملازم"""
        text = self.format_arabic_text(
            "📚 **الملازم والمرشحات**\n\n"
            "اختر المرحلة الدراسية أو ابحث عن مادة محددة:\n\n"
            "يمكنك البحث عن مواد دراسية في جميع المراحل."
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.create_materials_keyboard()
        )
    
    async def show_materials_by_stage_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, stage: str):
        """عرض مواد مرحلة معينة"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على مواد المرحلة
        materials = self.db.get_materials(stage=stage)
        
        if not materials:
            text = self.format_arabic_text(
                f"📚 **الملازم - {stage}**\n\n"
                "⚠️ **لا توجد مواد متاحة لهذه المرحلة حالياً.**\n\n"
                "سيتم إضافة مواد قريباً."
            )
            
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.create_materials_keyboard()
            )
            return
        
        # عرض المواد
        materials_text = ""
        for i, material in enumerate(materials[:10], 1):  # عرض أول 10 مواد فقط
            materials_text += f"{i}. **{material.name}**\n"
            if material.description:
                materials_text += f"   _{material.description[:50]}..._\n"
            materials_text += f"   📊 {material.subject} | ⬇️ {material.downloads}\n\n"
        
        if len(materials) > 10:
            materials_text += f"*و {len(materials) - 10} مواد أخرى*\n\n"
        
        text = self.format_arabic_text(
            f"📚 **الملازم - {stage}**\n\n"
            f"عدد المواد المتاحة: {len(materials)}\n\n"
            f"{materials_text}"
            f"لتحميل مادة، أرسل اسمها أو رقمها."
        )
        
        # حفظ المرحلة الحالية في سياق المستخدم
        context.user_data['current_stage'] = stage
        context.user_data['current_materials'] = [m.id for m in materials]
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🔍 بحث عن مادة", "🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    async def show_search_material(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض بحث عن مادة"""
        text = self.format_arabic_text(
            "🔍 **بحث عن مادة**\n\n"
            "أرسل اسم المادة أو جزء منه للبحث:\n\n"
            "مثال: 'رياضيات' أو 'فيزياء'"
        )
        
        # حفظ حالة البحث
        context.user_data['searching_material'] = True
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    # ========== دوال الرصيد والإحالة ==========
    async def show_balance_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض معلومات الرصيد"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على بيانات المستخدم
        user_data = self.db.get_user(user_id)
        if not user_data:
            await self.start_command(update, context)
            return
        
        # الحصول على آخر المعاملات
        transactions = self.db.get_user_transactions(user_id, limit=5)
        
        # تنسيق المعاملات
        transactions_text = ""
        if transactions:
            for trans in transactions:
                amount_text = f"+{abs(trans.amount)}" if trans.amount > 0 else f"-{abs(trans.amount)}"
                date_text = trans.date[:10] if trans.date else "غير معروف"
                trans_type = {
                    'welcome_bonus': '🎁 هدية ترحيبية',
                    'referral_bonus': '👥 مكافأة إحالة',
                    'service_payment': '💸 دفع خدمة',
                    'admin_charge': '👑 شحن من مدير'
                }.get(trans.type, trans.type)
                
                transactions_text += f"• {amount_text} - {trans_type} ({date_text})\n"
        else:
            transactions_text = "لا توجد معاملات سابقة.\n"
        
        text = self.format_arabic_text(
            f"💰 **رصيدك الحالي**\n\n"
            f"💳 **المبلغ:** {self.format_currency(user_data.balance)}\n"
            f"👤 **المستخدم:** {user_data.first_name} {user_data.last_name or ''}\n"
            f"🆔 **المعرف:** {user_data.user_id}\n"
            f"📅 **تاريخ الانضمام:** {user_data.join_date[:10]}\n\n"
            f"📊 **آخر المعاملات:**\n{transactions_text}\n"
            f"💡 **لشحن الرصيد:** تواصل مع الدعم @Allawi04@"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["👥 دعوة أصدقاء", "💰 شحن الرصيد"],
                ["🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    async def show_invite_friends(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض دعوة الأصدقاء"""
        user = update.effective_user
        user_id = user.id
        
        await self.send_typing(user_id, context)
        
        # الحصول على بيانات المستخدم
        user_data = self.db.get_user(user_id)
        if not user_data:
            await self.menu_command(update, context)
            return
        
        # إنشاء رابط الدعوة
        invite_link = f"https://t.me/{self.bot_username.replace('@', '')}?start={user_data.referral_code}"
        
        # الحصول على عدد الإحالات
        self.db.cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_data.referral_code,))
        referral_count = self.db.cursor.fetchone()[0] or 0
        
        text = self.format_arabic_text(
            f"👥 **دعوة الأصدقاء**\n\n"
            f"💰 **مكافأة الإحالة:** {self.db.get_setting('referral_bonus', '500')} دينار\n"
            f"🎁 **هدية الصديق:** {self.db.get_setting('welcome_bonus', '1000')} دينار\n"
            f"📊 **عدد الإحالات:** {referral_count}\n\n"
            f"**كيفية الدعوة:**\n"
            f"1. أرسل الرابط لأصدقائك\n"
            f"2. عندما ينضم صديقك\n"
            f"3. تحصل على {self.db.get_setting('referral_bonus', '500')} دينار\n"
            f"4. صديقك يحصل على {self.db.get_setting('welcome_bonus', '1000')} دينار\n\n"
            f"🔗 **رابط الدعوة:**\n`{invite_link}`"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🔗 مشاركة الرابط", "🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    # ========== دوال الدعم والمساعدة ==========
    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض معلومات الدعم"""
        # الحصول على إعدادات القناة
        bot_channel = self.db.get_setting('bot_channel', '')
        
        channel_text = ""
        if bot_channel:
            channel_text = f"📢 **قناة البوت:** {bot_channel}\n\n"
        
        text = self.format_arabic_text(
            f"🛠 **الدعم الفني**\n\n"
            f"📞 **للشحن أو الاستفسارات أو المشاكل الفنية:**\n"
            f"• **الدعم:** @Allawi04@\n\n"
            f"{channel_text}"
            f"⏰ **وقت الاستجابة:**\n"
            f"• **أيام الأسبوع:** 9 صباحاً - 10 مساءً\n"
            f"• **الجمعة:** 2 ظهراً - 10 مساءً\n\n"
            f"💡 **نصائح للتواصل:**\n"
            f"1. تأكد من إرسال إيديك عند التواصل\n"
            f"2. اشرح مشكلتك بوضوح\n"
            f"3. أرفق صوراً إذا لزم الأمر\n"
            f"4. تحلى بالصبر أثناء الرد"
        )
        
        keyboard_buttons = []
        if bot_channel:
            keyboard_buttons.append(["📢 قناة البوت"])
        
        keyboard_buttons.append(["🔙 رجوع"])
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup(keyboard_buttons, resize_keyboard=True)
        )
    
    async def show_help_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض معلومات المساعدة"""
        # الحصول على أسعار الخدمات
        services = self.db.get_services()
        services_text = ""
        for service in services:
            if service.price > 0:
                services_text += f"• **{service.name}:** {self.format_currency(service.price)}\n"
            else:
                services_text += f"• **{service.name}:** مجاناً\n"
        
        text = self.format_arabic_text(
            f"ℹ️ **المساعدة والاستفسارات**\n\n"
            f"🎓 **عن البوت:**\n"
            f"بوت 'يلا نتعلم' هو بوت تعليمي للطلاب العراقيين.\n\n"
            f"💰 **أسعار الخدمات:**\n{services_text}\n"
            f"🔗 **رابط البوت:** @{self.bot_username.replace('@', '')}\n\n"
            f"📞 **الدعم الفني:**\n"
            f"• **الدعم:** @Allawi04@\n"
            f"• **وقت الاستجابة:** 9 صباحاً - 10 مساءً\n\n"
            f"⚙️ **كيفية الاستخدام:**\n"
            f"1. اختر الخدمة من الأزرار\n"
            f"2. اتبع التعليمات الظاهرة\n"
            f"3. تأكد من وجود رصيد كافٍ\n"
            f"4. استمتع بالخدمات التعليمية"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup([
                ["🛠 الدعم الفني", "🔙 رجوع"]
            ], resize_keyboard=True)
        )
    
    # ========== دوال المدير ==========
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة تحكم المدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text(
                self.format_arabic_text("⛔ غير مصرح لك بالدخول."),
                reply_markup=self.main_keyboard
            )
            return
        
        await self.send_typing(user_id, context)
        
        # الحصول على إحصائيات البوت
        stats = self.db.get_statistics(1)
        
        total_users = self.db.get_user_count()
        total_balance = self.db.get_total_balance()
        maintenance_mode = self.db.get_setting('maintenance_mode', 'false') == 'true'
        
        text = self.format_arabic_text(
            f"👑 **لوحة التحكم**\n\n"
            f"📊 **إحصائيات البوت:**\n"
            f"• **إجمالي المستخدمين:** {total_users}\n"
            f"• **إجمالي الأرصدة:** {self.format_currency(total_balance)}\n"
            f"• **وضع الصيانة:** {'✅ مفعل' if maintenance_mode else '❌ غير مفعل'}\n\n"
            f"📈 **إحصائيات اليوم:**\n"
            f"• **المستخدمين الجدد:** {stats.get('daily_stats', [{}])[0].get('new_users', 0) if stats.get('daily_stats') else 0}\n"
            f"• **المستخدمين النشطين:** {stats.get('daily_stats', [{}])[0].get('active_users', 0) if stats.get('daily_stats') else 0}\n"
            f"• **الدخل اليومي:** {self.format_currency(stats.get('daily_stats', [{}])[0].get('total_income', 0) if stats.get('daily_stats') else 0)}\n\n"
            f"اختر القسم المطلوب:"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.create_admin_keyboard()
        )
    
    async def show_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات المدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            return
        
        await self.send_typing(user_id, context)
        
        # تحديث الإحصائيات أولاً
        self.db.update_statistics()
        
        # الحصول على إحصائيات مفصلة
        stats = self.db.get_statistics(7)
        
        # تنسيق إحصائيات الأيام
        daily_stats_text = ""
        if stats.get('daily_stats'):
            for day_stat in stats['daily_stats']:
                daily_stats_text += (
                    f"📅 **{day_stat['date']}:**\n"
                    f"  👥 جديد: {day_stat['new_users']} | نشيط: {day_stat['active_users']}\n"
                    f"  💰 دخل: {self.format_currency(day_stat['total_income'])}\n"
                    f"  📊 استخدام: {day_stat['service_usage_count']}\n\n"
                )
        else:
            daily_stats_text = "لا توجد بيانات كافية.\n"
        
        text = self.format_arabic_text(
            f"📈 **إحصائيات مفصلة**\n\n"
            f"📊 **إحصائيات عامة:**\n"
            f"• **إجمالي المستخدمين:** {stats.get('total_users', 0)}\n"
            f"• **إجمالي الأرصدة:** {self.format_currency(stats.get('total_balance', 0))}\n"
            f"• **إجمالي الدخل:** {self.format_currency(stats.get('total_income', 0))}\n\n"
            f"📅 **إحصائيات آخر 7 أيام:**\n{daily_stats_text}"
            f"📋 **ملاحظة:** يتم تحديث الإحصائيات تلقائياً كل 24 ساعة."
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.create_admin_keyboard()
        )
    
    async def show_admin_users_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة إدارة المستخدمين للمدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            return
        
        text = self.format_arabic_text(
            "👥 **إدارة المستخدمين**\n\n"
            "اختر الإجراء المطلوب:"
        )
        
        keyboard = [
            ["📋 عرض المستخدمين", "🔍 بحث عن مستخدم"],
            ["💰 شحن رصيد", "⛔ حظر مستخدم"],
            ["✅ فك حظر", "🔙 رجوع"]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def show_admin_charge_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة إدارة الشحن للمدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            return
        
        text = self.format_arabic_text(
            "💰 **إدارة الشحن**\n\n"
            "اختر الإجراء المطلوب:"
        )
        
        keyboard = [
            ["➕ شحن رصيد", "➖ خصم رصيد"],
            ["🎁 تعديل مكافأة الإحالة", "🎊 تعديل الهدية الترحيبية"],
            ["🔙 رجوع"]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def show_admin_services_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة إدارة الخدمات للمدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            return
        
        # الحصول على أسعار الخدمات
        services = self.db.get_services()
        services_text = ""
        for service in services:
            services_text += f"• **{service.name}:** {self.format_currency(service.price)}\n"
        
        text = self.format_arabic_text(
            f"⚙️ **إدارة الخدمات**\n\n"
            f"💰 **الأسعار الحالية:**\n{services_text}\n"
            f"اختر الخدمة المراد تعديل سعرها:"
        )
        
        # إنشاء أزرار الخدمات
        keyboard = []
        for service in services:
            if service.price > 0:
                keyboard.append([f"💰 {service.name}"])
        
        keyboard.append(["🔙 رجوع"])
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def show_admin_materials_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة إدارة الملازم للمدير"""
        user = update.effective_user
        user_id = user.id
        
        if not self.is_admin(user_id):
            return
        
        text = self.format_arabic_text(
            "📚 **إدارة الملازم**\n\n"
            "اختر الإجراء المطلوب:"
        )
        
        keyboard = [
            ["➕ إضافة مادة", "🗑 حذف مادة"],
            ["📋 عرض المواد", "🔙 رجوع"]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    # ========== معالجة الملفات والصور ==========
    async def handle_document_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الملفات المرسلة"""
        user = update.effective_user
        user_id = user.id
        
        # التحقق من الجلسة
        if user_id not in self.user_sessions or not self.user_sessions[user_id].get('waiting_for_file'):
            return
        
        session = self.user_sessions[user_id]
        
        if not update.message.document or not update.message.document.file_name.endswith('.pdf'):
            await update.message.reply_text(
                self.format_arabic_text("⚠️ **الرجاء إرسال ملف PDF صالح فقط.**"),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # التحقق من حجم الملف
        max_size = int(self.db.get_setting('max_file_size_mb', '20')) * 1024 * 1024
        if update.message.document.file_size > max_size:
            await update.message.reply_text(
                self.format_arabic_text(
                    f"⚠️ **حجم الملف كبير جداً**\n\n"
                    f"الحد الأقصى: {self.db.get_setting('max_file_size_mb', '20')} ميجابايت\n"
                    f"حجم ملفك: {update.message.document.file_size / (1024*1024):.1f} ميجابايت"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            del self.user_sessions[user_id]
            await self.menu_command(update, context)
            return
        
        await self.send_typing(user_id, context)
        
        # إرسال رسالة الانتظار
        processing_msg = await update.message.reply_text(
            self.format_arabic_text("🔄 **جاري معالجة الملف...**"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # تحميل الملف
            file = await update.message.document.get_file()
            pdf_bytes = await file.download_as_bytearray()
            
            # استخراج النص من PDF
            text = self.pdf.extract_text_from_pdf(pdf_bytes)
            
            if not text or len(text) < 100:
                await processing_msg.edit_text(
                    self.format_arabic_text(
                        "⚠️ **لم يتم العثور على نص كافٍ في الملف.**\n"
                        "قد يكون الملف ممسوحاً ضوئياً أو يحتوي على صور فقط."
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                del self.user_sessions[user_id]
                return
            
            await processing_msg.edit_text(
                self.format_arabic_text("🤖 **جاري تلخيص المحتوى باستخدام الذكاء الاصطناعي...**"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تلخيص النص باستخدام الذكاء الاصطناعي
            summary = await self.ai.summarize_pdf(
                text, 
                update.message.document.file_name
            )
            
            await processing_msg.edit_text(
                self.format_arabic_text("📄 **جاري إنشاء ملف PDF ملخص...**"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # خصم تكلفة الخدمة
            success = await self.deduct_service_cost(
                user_id, session['service_id'], 'تلخيص الملازم'
            )
            
            if not success:
                await processing_msg.edit_text(
                    self.format_arabic_text("⚠️ **حدث خطأ في معالجة الدفع.**"),
                    parse_mode=ParseMode.MARKDOWN
                )
                del self.user_sessions[user_id]
                await self.menu_command(update, context)
                return
            
            # إنشاء ملف PDF ملخص
            user_data = self.db.get_user(user_id)
            pdf_bytes = self.pdf.create_summary_pdf(
                summary, 
                update.message.document.file_name, 
                user_data
            )
            
            if not pdf_bytes:
                await processing_msg.edit_text(
                    self.format_arabic_text("⚠️ **حدث خطأ في إنشاء ملف PDF.**"),
                    parse_mode=ParseMode.MARKDOWN
                )
                del self.user_sessions[user_id]
                await self.menu_command(update, context)
                return
            
            # إرسال الملف الملخص
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_file.name = f"ملخص_{update.message.document.file_name}"
            
            user_data = self.db.get_user(user_id)
            caption = self.format_arabic_text(
                f"✅ **تم تلخيص الملف بنجاح!**\n\n"
                f"📄 **الملف الأصلي:** {update.message.document.file_name}\n"
                f"🤖 **طريقة التلخيص:** الذكاء الاصطناعي المتقدم\n\n"
                f"💰 **تم خصم:** {self.format_currency(self.db.get_service(session['service_id']).price)}\n"
                f"💳 **الرصيد المتبقي:** {self.format_currency(user_data.balance)}\n\n"
                f"🎓 **بوت 'يلا نتعلم'**"
            )
            
            await processing_msg.delete()
            
            await update.message.reply_document(
                document=pdf_file,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # حذف الجلسة
            del self.user_sessions[user_id]
            
            # عرض لوحة المفاتيح
            await update.message.reply_text(
                self.format_arabic_text("اختر خدمة أخرى:"),
                reply_markup=self.create_services_keyboard()
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة PDF: {e}")
            await processing_msg.edit_text(
                self.format_arabic_text(
                    f"⚠️ **حدث خطأ أثناء معالجة الملف:**\n{str(e)[:200]}"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            del self.user_sessions[user_id]
            await self.menu_command(update, context)
    
    async def handle_photo_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الصور المرسلة"""
        user = update.effective_user
        user_id = user.id
        
        # التحقق من الجلسة
        if user_id not in self.user_sessions or not self.user_sessions[user_id].get('waiting_for_question'):
            return
        
        session = self.user_sessions[user_id]
        
        await self.send_typing(user_id, context)
        
        # إرسال رسالة الانتظار
        processing_msg = await update.message.reply_text(
            self.format_arabic_text("🤖 **جاري معالجة صورتك...**"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # استخدام أعلى دقة للصورة
            photo = update.message.photo[-1]
            file = await photo.get_file()
            image_data = await file.download_as_bytearray()
            
            # الحصول على الإجابة من الذكاء الاصطناعي
            answer = await self.ai.answer_question("", is_image=True, image_data=image_data)
            
            # خصم تكلفة الخدمة
            success = await self.deduct_service_cost(
                user_id, session['service_id'], 'سؤال وجواب'
            )
            
            if not success:
                await processing_msg.edit_text(
                    self.format_arabic_text("⚠️ **حدث خطأ في معالجة الدفع.**"),
                    parse_mode=ParseMode.MARKDOWN
                )
                del self.user_sessions[user_id]
                await self.menu_command(update, context)
                return
            
            await processing_msg.edit_text(
                self.format_arabic_text("📝 **جاري إعداد الإجابة...**"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # إرسال الإجابة
            user_data = self.db.get_user(user_id)
            
            # تقسيم الإجابة إذا كانت طويلة
            if len(answer) > 4000:
                parts = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                
                for i, part in enumerate(parts, 1):
                    if i == 1:
                        header = self.format_arabic_text(
                            f"🧠 **إجابتي على صورتك:**\n\n"
                            f"{part}\n\n"
                            f"📄 الصفحة {i}/{len(parts)}"
                        )
                        await processing_msg.delete()
                        await update.message.reply_text(
                            header,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await update.message.reply_text(
                            self.format_arabic_text(
                                f"{part}\n\n"
                                f"📄 الصفحة {i}/{len(parts)}"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
            else:
                full_answer = self.format_arabic_text(
                    f"🧠 **إجابتي على صورتك:**\n\n"
                    f"{answer}\n\n"
                    f"💰 **تم خصم:** {self.format_currency(self.db.get_service(session['service_id']).price)}\n"
                    f"💳 **الرصيد المتبقي:** {self.format_currency(user_data.balance)}\n\n"
                    f"🎓 **بوت 'يلا نتعلم'**"
                )
                
                await processing_msg.delete()
                await update.message.reply_text(
                    full_answer,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # حذف الجلسة
            del self.user_sessions[user_id]
            
            # عرض لوحة المفاتيح
            await update.message.reply_text(
                self.format_arabic_text("اختر خدمة أخرى:"),
                reply_markup=self.create_services_keyboard()
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الصورة: {e}")
            await processing_msg.edit_text(
                self.format_arabic_text(
                    f"⚠️ **حدث خطأ أثناء معالجة صورتك:**\n{str(e)[:200]}"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            del self.user_sessions[user_id]
            await self.menu_command(update, context)
    
    # ========== دوال التشغيل والإغلاق ==========
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأخطاء"""
        try:
            raise context.error
        except (Unauthorized, BadRequest, Forbidden) as e:
            logger.error(f"❌ خطأ في البروتوكول: {e}")
        except TimedOut as e:
            logger.error(f"⏰ خطأ في المهلة: {e}")
        except NetworkError as e:
            logger.error(f"🌐 خطأ في الشبكة: {e}")
        except TelegramError as e:
            logger.error(f"🤖 خطأ في تليجرام: {e}")
        except Exception as e:
            logger.error(f"🔥 خطأ غير متوقع: {e}", exc_info=True)
            
            # محاولة إرسال رسالة خطأ للمستخدم
            try:
                if update and update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=self.format_arabic_text(
                            "⚠️ **حدث خطأ غير متوقع**\n\n"
                            "نعتذر عن هذا الخطأ. الرجاء المحاولة مرة أخرى لاحقاً.\n"
                            "إذا تكرر الخطأ، يرجى التواصل مع الدعم: @Allawi04@"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=self.main_keyboard
                    )
            except:
                pass
    
    async def daily_tasks(self, context: ContextTypes.DEFAULT_TYPE):
        """المهام اليومية"""
        try:
            # تحديث الإحصائيات
            self.db.update_statistics()
            logger.info("✅ تم تحديث الإحصائيات اليومية")
            
            # تنظيف الجلسات القديمة
            current_time = datetime.datetime.now()
            old_sessions = []
            
            for user_id, session in list(self.user_sessions.items()):
                if 'created_at' in session:
                    session_time = datetime.datetime.fromisoformat(session['created_at'])
                    if (current_time - session_time).total_seconds() > 3600:  # ساعة واحدة
                        old_sessions.append(user_id)
            
            for user_id in old_sessions:
                del self.user_sessions[user_id]
            
            if old_sessions:
                logger.info(f"✅ تم تنظيف {len(old_sessions)} جلسة قديمة")
            
        except Exception as e:
            logger.error(f"❌ خطأ في المهام اليومية: {e}")
    
    async def setup_jobs(self):
        """إعداد المهام المجدولة"""
        # مهمة يومية تحديث الإحصائيات
        self.job_queue.run_daily(
            self.daily_tasks,
            time=datetime.time(hour=0, minute=0, second=0),  # منتصف الليل
            name="daily_tasks"
        )
        
        logger.info("✅ تم إعداد المهام المجدولة")
    
    async def setup_bot_commands(self):
        """إعداد أوامر البوت"""
        commands = []
        for cmd, description in Constants.BOT_COMMANDS:
            commands.append(BotCommand(cmd, description))
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ تم إعداد أوامر البوت")
    
    async def run(self):
        """تشغيل البوت"""
        try:
            # إنشاء تطبيق البوت
            self.application = ApplicationBuilder() \
                .token(self.token) \
                .concurrent_updates(True) \
                .build()
            
            self.job_queue = self.application.job_queue
            
            # إعداد أوامر البوت
            await self.setup_bot_commands()
            
            # إضافة المعالجات
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("menu", self.menu_command))
            self.application.add_handler(CommandHandler("balance", self.show_balance_info))
            self.application.add_handler(CommandHandler("materials", self.show_materials_menu))
            self.application.add_handler(CommandHandler("help", self.show_help_info))
            self.application.add_handler(CommandHandler("support", self.show_support_info))
            
            # معالجة الرسائل النصية (بما في ذلك الأزرار)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_messages))
            
            # معالجة الملفات والصور
            self.application.add_handler(MessageHandler(filters.Document.PDF, self.handle_document_messages))
            self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_messages))
            
            # معالجة الأخطاء
            self.application.add_error_handler(self.error_handler)
            
            # إعداد المهام المجدولة
            await self.setup_jobs()
            
            # بدء البوت
            logger.info("✅ بدأ تشغيل البوت...")
            print("=" * 60)
            print("🎓 بوت 'يلا نتعلم' يعمل بنجاح!")
            print(f"🤖 يوزر البوت: {self.bot_username}")
            print(f"🔑 التوكن الجديد: {self.token[:20]}...")
            print(f"👑 المدير: {self.admin_id}")
            print(f"🛠 الدعم: {self.support_username}")
            print(f"📊 المستخدمين: {self.db.get_user_count()}")
            print(f"💰 إجمالي الأرصدة: {self.format_currency(self.db.get_total_balance())}")
            print("=" * 60)
            print("📱 الأزرار فوق الرسائل مفعلة بالكامل!")
            print("🎯 يمكن للمستخدمين استخدام الأزرار بسهولة!")
            print("=" * 60)
            
            # التشغيل
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # الحفاظ على البوت قيد التشغيل
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"❌ فشل تشغيل البوت: {e}")
            raise
    
    async def shutdown(self):
        """إيقاف البوت"""
        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
            
            if self.db:
                self.db.close()
            
            logger.info("✅ تم إيقاف البوت بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف البوت: {e}")

# ========== الدالة الرئيسية ==========
async def main():
    """الدالة الرئيسية"""
    bot = None
    
    try:
        bot = YallaNt3lemBot()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("⏹ إيقاف البوت...")
        
    except Exception as e:
        logger.error(f"❌ خطأ رئيسي: {e}")
        
    finally:
        if bot:
            await bot.shutdown()

if __name__ == "__main__":
    # تشغيل البوت
    asyncio.run(main())
