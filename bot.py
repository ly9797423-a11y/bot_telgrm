#!/usr/bin/env python3
"""
Bot Name: يلا نتعلم
Bot Username: @FC4Xbot
Admin: 6130994941
Support: @Allawi04
Channel: @FCJCV
"""

import asyncio
import logging
import os
import json
import datetime
import tempfile
import hashlib
import random
import string
import time
import csv
import io
import re
from typing import Dict, List, Tuple, Optional, Any, Union
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal
from collections import defaultdict
import threading
import queue

import aiohttp
import aiosqlite
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InputFile, 
    ChatPermissions,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand,
    BotCommandScopeDefault,
    MessageEntity,
    User as TgUser,
    Chat as TgChat
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    PicklePersistence,
    JobQueue,
    Job
)
from telegram.constants import ParseMode, ChatAction, MessageLimit
from telegram.error import TelegramError, BadRequest, NetworkError

import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import requests
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pandas as pd
from cachetools import TTLCache
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# ==================== Configuration & Constants ====================
load_dotenv()

TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
BOT_USERNAME = "@FC4Xbot"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04@"
CHANNEL_USERNAME = "@FCJCV"
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "telegram_learning_bot_v2"

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FONTS_DIR = BASE_DIR / "fonts"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
for dir_path in [DATA_DIR, FONTS_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Timezone
IRAQ_TZ = pytz.timezone("Asia/Baghdad")

# Initialize MongoDB with retry logic
def init_database():
    max_retries = 5
    retry_delay = 2
    
    for i in range(max_retries):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            db = client[DB_NAME]
            
            # Create collections with indexes
            collections_config = {
                "users": [
                    ("user_id", ASCENDING, True),
                    ("invite_code", ASCENDING, True),
                    ("created_at", DESCENDING, False)
                ],
                "courses": [
                    ("user_id", ASCENDING, False),
                    ("stage", ASCENDING, False)
                ],
                "questions": [
                    ("user_id", ASCENDING, False),
                    ("status", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "materials": [
                    ("name", ASCENDING, False),
                    ("stage", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "vip_subscriptions": [
                    ("user_id", ASCENDING, True),
                    ("expires_at", DESCENDING, False)
                ],
                "vip_lectures": [
                    ("user_id", ASCENDING, False),
                    ("approved", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "transactions": [
                    ("user_id", ASCENDING, False),
                    ("type", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "invites": [
                    ("inviter_id", ASCENDING, False),
                    ("invitee_id", ASCENDING, True)
                ],
                "settings": [
                    ("key", ASCENDING, True)
                ],
                "notifications": [
                    ("user_id", ASCENDING, False),
                    ("read", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "withdrawals": [
                    ("user_id", ASCENDING, False),
                    ("status", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "broadcasts": [
                    ("admin_id", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "reports": [
                    ("reporter_id", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "logs": [
                    ("user_id", ASCENDING, False),
                    ("action", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "payments": [
                    ("user_id", ASCENDING, False),
                    ("status", ASCENDING, False),
                    ("created_at", DESCENDING, False)
                ],
                "sessions": [
                    ("user_id", ASCENDING, False),
                    ("expires_at", DESCENDING, False)
                ],
                "cache": [
                    ("key", ASCENDING, True),
                    ("expires_at", DESCENDING, False)
                ]
            }
            
            for collection_name, indexes in collections_config.items():
                if collection_name not in db.list_collection_names():
                    db.create_collection(collection_name)
                
                coll = db[collection_name]
                for index_fields, direction, unique in indexes:
                    coll.create_index([(index_fields, direction)], unique=unique)
            
            return db
            
        except ConnectionFailure as e:
            if i == max_retries - 1:
                raise e
            time.sleep(retry_delay * (i + 1))
    
    raise Exception("Failed to connect to database after multiple retries")

# Initialize database
try:
    db = init_database()
    users_col = db["users"]
    courses_col = db["courses"]
    questions_col = db["questions"]
    materials_col = db["materials"]
    vip_subscriptions_col = db["vip_subscriptions"]
    vip_lectures_col = db["vip_lectures"]
    transactions_col = db["transactions"]
    invites_col = db["invites"]
    settings_col = db["settings"]
    notifications_col = db["notifications"]
    withdrawals_col = db["withdrawals"]
    broadcasts_col = db["broadcasts"]
    reports_col = db["reports"]
    logs_col = db["logs"]
    payments_col = db["payments"]
    sessions_col = db["sessions"]
    cache_col = db["cache"]
except Exception as e:
    logging.error(f"Database initialization failed: {e}")
    # Fallback to SQLite for critical functionality
    import sqlite3
    sqlite_conn = sqlite3.connect(DATA_DIR / "bot.db")
    sqlite_cursor = sqlite_conn.cursor()

# Initialize Gemini AI with safety settings
try:
    genai.configure(api_key=GEMINI_API_KEY)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    model = genai.GenerativeModel(
        'gemini-pro',
        safety_settings=safety_settings
    )
    vision_model = genai.GenerativeModel(
        'gemini-pro-vision',
        safety_settings=safety_settings
    )
except Exception as e:
    logging.error(f"Gemini AI initialization failed: {e}")
    model = None
    vision_model = None

# Register Arabic fonts
def setup_fonts():
    try:
        # Try to register common Arabic fonts
        font_paths = [
            FONTS_DIR / "arial.ttf",
            FONTS_DIR / "tahoma.ttf",
            FONTS_DIR / "times.ttf",
            "/usr/share/fonts/truetype/arabic/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        registered_fonts = []
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font_name = Path(font_path).stem
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                    registered_fonts.append(font_name)
                except:
                    continue
        
        if not registered_fonts:
            # Create a simple fallback font
            from reportlab.pdfbase import _fontdata
            _fontdata.standardFonts.append('ArabicFallback')
        
        return registered_fonts
    except Exception as e:
        logging.error(f"Font setup failed: {e}")
        return []

ARABIC_FONTS = setup_fonts()
DEFAULT_FONT = ARABIC_FONTS[0] if ARABIC_FONTS else "Helvetica"

# ==================== Enums & Data Classes ====================
class UserState(Enum):
    MAIN_MENU = 0
    WAITING_COURSE1 = 1
    WAITING_COURSE2 = 2
    WAITING_COURSE3 = 3
    WAITING_PDF = 4
    WAITING_QUESTION = 5
    WAITING_ANSWER = 6
    WAITING_CHARGE_USER = 7
    WAITING_CHARGE_AMOUNT = 8
    WAITING_DEDUCT_USER = 9
    WAITING_DEDUCT_AMOUNT = 10
    WAITING_BAN_USER = 11
    WAITING_UNBAN_USER = 12
    WAITING_BROADCAST = 13
    WAITING_VIP_PRICE = 14
    WAITING_SERVICE_PRICE = 15
    WAITING_INVITE_REWARD = 16
    WAITING_VIP_LECTURE_TITLE = 17
    WAITING_VIP_LECTURE_DESC = 18
    WAITING_VIP_LECTURE_PRICE = 19
    WAITING_VIP_LECTURE_VIDEO = 20
    WAITING_WITHDRAW_AMOUNT = 21
    WAITING_MATERIAL_NAME = 22
    WAITING_MATERIAL_DESC = 23
    WAITING_MATERIAL_STAGE = 24
    WAITING_MATERIAL_FILE = 25
    WAITING_REPORT_REASON = 26
    WAITING_PAYMENT_CONFIRMATION = 27
    WAITING_FEEDBACK = 28
    WAITING_CONTACT_MESSAGE = 29
    WAITING_ADMIN_MESSAGE = 30
    WAITING_FILTER_USERS = 31
    WAITING_EXPORT_DATA = 32
    WAITING_IMPORT_DATA = 33
    WAITING_BACKUP_CONFIRM = 34
    WAITING_RESTORE_CONFIRM = 35
    WAITING_SYSTEM_SETTINGS = 36
    WAITING_MAINTENANCE_MESSAGE = 37
    WAITING_CUSTOM_MESSAGE = 38
    WAITING_BULK_ACTION = 39
    WAITING_AUTO_REPLY = 40
    WAITING_COUPON_CODE = 41
    WAITING_COUPON_AMOUNT = 42
    WAITING_COUPON_USES = 43
    WAITING_DISCOUNT_PERCENT = 44
    WAITING_PROMO_DURATION = 45
    WAITING_ADVERTISEMENT = 46
    WAITING_STATISTICS_PERIOD = 47
    WAITING_REPORT_TYPE = 48
    WAITING_LOG_FILTER = 49
    WAITING_SESSION_DURATION = 50
    WAITING_RATE_LIMIT = 51
    WAITING_SECURITY_SETTINGS = 52
    WAITING_NOTIFICATION_SETTINGS = 53
    WAITING_UI_SETTINGS = 54
    WAITING_LANGUAGE_SETTINGS = 55
    WAITING_CURRENCY_SETTINGS = 56
    WAITING_TIMEZONE_SETTINGS = 57
    WAITING_THEME_SETTINGS = 58

class UserRole(Enum):
    USER = "user"
    VIP = "vip"
    TEACHER = "teacher"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class QuestionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ANSWERED = "answered"
    DELETED = "deleted"

class LectureStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"
    HIDDEN = "hidden"

class TransactionType(Enum):
    WELCOME_BONUS = "welcome_bonus"
    SERVICE_PAYMENT = "service_payment"
    VIP_SUBSCRIPTION = "vip_subscription"
    LECTURE_PURCHASE = "lecture_purchase"
    LECTURE_EARNING = "lecture_earning"
    ADMIN_CHARGE = "admin_charge"
    ADMIN_DEDUCT = "admin_deduct"
    INVITE_REWARD = "invite_reward"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"
    COUPON = "coupon"
    TRANSFER = "transfer"

class NotificationType(Enum):
    BALANCE_CHANGE = "balance_change"
    VIP_EXPIRY = "vip_expiry"
    LECTURE_APPROVED = "lecture_approved"
    LECTURE_REJECTED = "lecture_rejected"
    QUESTION_ANSWERED = "question_answered"
    NEW_MESSAGE = "new_message"
    SYSTEM_ALERT = "system_alert"
    PROMOTION = "promotion"

@dataclass
class UserProfile:
    user_id: int
    username: str
    first_name: str
    last_name: str
    balance: Decimal
    vip_balance: Decimal
    vip_until: Optional[datetime.datetime]
    role: UserRole
    invited_by: Optional[int]
    invite_code: str
    invited_count: int
    total_spent: Decimal
    total_earned: Decimal
    created_at: datetime.datetime
    last_active: datetime.datetime
    settings: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class Lecture:
    lecture_id: str
    user_id: int
    title: str
    description: str
    price: Decimal
    video_file_id: str
    thumbnail_file_id: Optional[str]
    duration: int
    views: int
    purchases: int
    revenue: Decimal
    rating: float
    ratings_count: int
    status: LectureStatus
    tags: List[str]
    category: str
    created_at: datetime.datetime
    approved_at: Optional[datetime.datetime]
    deleted_at: Optional[datetime.datetime]

# ==================== Logging Configuration ====================
def setup_logging():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler
    log_file = LOGS_DIR / f"bot_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[file_handler, console_handler]
    )
    
    # Disable noisy loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)

# ==================== Cache System ====================
class CacheManager:
    def __init__(self):
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)
        self.db_cache = cache_col
        
    async def get(self, key: str):
        # Try memory cache first
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Try database cache
        doc = self.db_cache.find_one({"key": key, "expires_at": {"$gt": datetime.datetime.now()}})
        if doc:
            value = doc["value"]
            self.memory_cache[key] = value
            return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        expires_at = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        
        # Update memory cache
        self.memory_cache[key] = value
        
        # Update database cache
        self.db_cache.update_one(
            {"key": key},
            {"$set": {"value": value, "expires_at": expires_at}},
            upsert=True
        )
    
    async def delete(self, key: str):
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        self.db_cache.delete_one({"key": key})
    
    async def clear(self):
        self.memory_cache.clear()
        self.db_cache.delete_many({})

cache = CacheManager()

# ==================== Utility Functions ====================
def format_number(num: Union[int, float, Decimal]) -> str:
    """Format number with commas for Arabic style."""
    return f"{num:,.0f}".replace(",", "٬")

def format_currency(amount: Decimal) -> str:
    """Format currency in Iraqi Dinar."""
    return f"{format_number(amount)} دينار عراقي"

def format_date(dt: datetime.datetime) -> str:
    """Format datetime to Arabic style."""
    return dt.astimezone(IRAQ_TZ).strftime("%Y/%m/%d %I:%M %p")

def format_duration(seconds: int) -> str:
    """Format duration to readable format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} ساعة")
    if minutes > 0:
        parts.append(f"{minutes} دقيقة")
    if secs > 0 or not parts:
        parts.append(f"{secs} ثانية")
    
    return " و ".join(parts)

def generate_invite_code(length: int = 8) -> str:
    """Generate random invite code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def validate_phone(phone: str) -> bool:
    """Validate Iraqi phone number."""
    pattern = r'^(\+964|0)?7[0-9]{9}$'
    return bool(re.match(pattern, phone))

def sanitize_text(text: str) -> str:
    """Sanitize text for safe display."""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>{}[\]]', '', text)
    # Limit length
    if len(text) > 4000:
        text = text[:4000] + '...'
    return text

def resize_image(image_path: Path, max_size: tuple = (800, 800)) -> bytes:
    """Resize image to specified dimensions."""
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image using Gemini Vision."""
    if not vision_model:
        return "خدمة الاستخراج غير متوفرة حالياً"
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        response = vision_model.generate_content(["اقرأ النص في هذه الصورة", image])
        return response.text
    except Exception as e:
        logger.error(f"Image text extraction failed: {e}")
        return "فشل استخراج النص من الصورة"

def create_qr_code(data: str) -> bytes:
    """Create QR code image."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except ImportError:
        return b''

# ==================== Database Operations ====================
async def get_user(user_id: int, create_if_missing: bool = True) -> Optional[Dict]:
    """Get user from database."""
    try:
        user = users_col.find_one({"user_id": user_id})
        
        if not user and create_if_missing:
            # Create new user
            user_data = {
                "user_id": user_id,
                "username": "",
                "first_name": "",
                "last_name": "",
                "balance": Decimal('1000.0'),  # Welcome bonus
                "vip_balance": Decimal('0.0'),
                "vip_until": None,
                "role": UserRole.USER.value,
                "invited_by": None,
                "invite_code": generate_invite_code(),
                "invited_count": 0,
                "total_spent": Decimal('0.0'),
                "total_earned": Decimal('0.0'),
                "created_at": datetime.datetime.now(),
                "last_active": datetime.datetime.now(),
                "banned": False,
                "ban_reason": None,
                "ban_until": None,
                "warnings": 0,
                "settings": {
                    "notifications": True,
                    "language": "ar",
                    "theme": "light",
                    "auto_renew_vip": False,
                    "show_balance": True
                },
                "metadata": {
                    "course_scores": {},
                    "last_courses": [],
                    "favorite_materials": [],
                    "purchased_lectures": [],
                    "login_count": 0,
                    "device_info": {}
                }
            }
            
            # Insert new user
            users_col.insert_one(user_data)
            
            # Log welcome bonus transaction
            transaction_data = {
                "user_id": user_id,
                "type": TransactionType.WELCOME_BONUS.value,
                "amount": Decimal('1000.0'),
                "balance_before": Decimal('0.0'),
                "balance_after": Decimal('1000.0'),
                "description": "هدية ترحيبية",
                "reference_id": f"WELCOME_{user_id}",
                "created_at": datetime.datetime.now(),
                "status": "completed"
            }
            transactions_col.insert_one(transaction_data)
            
            # Create notification
            notification_data = {
                "user_id": user_id,
                "type": NotificationType.BALANCE_CHANGE.value,
                "title": "🎁 هدية ترحيبية",
                "message": "تم إضافة 1000 دينار هدية ترحيبية لحسابك",
                "data": {"amount": 1000},
                "read": False,
                "created_at": datetime.datetime.now()
            }
            notifications_col.insert_one(notification_data)
            
            user = user_data
        
        elif user:
            # Update last active
            users_col.update_one(
                {"user_id": user_id},
                {"$set": {"last_active": datetime.datetime.now()}}
            )
        
        return user
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def update_user(user_id: int, updates: Dict[str, Any]) -> bool:
    """Update user in database."""
    try:
        # Convert Decimal to float for MongoDB
        processed_updates = {}
        for key, value in updates.items():
            if isinstance(value, Decimal):
                processed_updates[key] = float(value)
            else:
                processed_updates[key] = value
        
        result = users_col.update_one(
            {"user_id": user_id},
            {"$set": processed_updates}
        )
        
        # Clear user cache
        cache_key = f"user:{user_id}"
        await cache.delete(cache_key)
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return False

async def get_users_count() -> Dict[str, int]:
    """Get users statistics."""
    try:
        total = users_col.count_documents({})
        active_today = users_col.count_documents({
            "last_active": {"$gte": datetime.datetime.now() - datetime.timedelta(days=1)}
        })
        vip_active = users_col.count_documents({
            "vip_until": {"$gt": datetime.datetime.now()}
        })
        banned = users_col.count_documents({"banned": True})
        
        return {
            "total": total,
            "active_today": active_today,
            "vip_active": vip_active,
            "banned": banned
        }
    except Exception as e:
        logger.error(f"Error getting users count: {e}")
        return {"total": 0, "active_today": 0, "vip_active": 0, "banned": 0}

async def create_transaction(
    user_id: int,
    transaction_type: TransactionType,
    amount: Decimal,
    description: str = "",
    reference_id: str = ""
) -> bool:
    """Create a transaction record."""
    try:
        user = await get_user(user_id)
        if not user:
            return False
        
        balance_before = Decimal(str(user["balance"]))
        
        # Calculate new balance based on transaction type
        if transaction_type in [
            TransactionType.WELCOME_BONUS,
            TransactionType.ADMIN_CHARGE,
            TransactionType.INVITE_REWARD,
            TransactionType.LECTURE_EARNING,
            TransactionType.REFUND,
            TransactionType.COUPON
        ]:
            balance_after = balance_before + amount
        else:
            balance_after = balance_before - amount
        
        # Update user balance
        await update_user(user_id, {"balance": balance_after})
        
        # Record transaction
        transaction_data = {
            "user_id": user_id,
            "type": transaction_type.value,
            "amount": float(amount),
            "balance_before": float(balance_before),
            "balance_after": float(balance_after),
            "description": description,
            "reference_id": reference_id or f"{transaction_type.value}_{int(time.time())}",
            "created_at": datetime.datetime.now(),
            "status": "completed"
        }
        
        transactions_col.insert_one(transaction_data)
        
        # Update user stats
        if amount > 0:
            users_col.update_one(
                {"user_id": user_id},
                {"$inc": {"total_earned": float(amount)}}
            )
        else:
            users_col.update_one(
                {"user_id": user_id},
                {"$inc": {"total_spent": float(-amount)}}
            )
        
        # Create notification for significant balance changes
        if abs(amount) >= 1000:
            notification_data = {
                "user_id": user_id,
                "type": NotificationType.BALANCE_CHANGE.value,
                "title": "💰 تغيير في الرصيد",
                "message": f"تم {"إضافة" if amount > 0 else "خصم"} {format_currency(abs(amount))} من رصيدك",
                "data": {
                    "amount": float(amount),
                    "balance_before": float(balance_before),
                    "balance_after": float(balance_after)
                },
                "read": False,
                "created_at": datetime.datetime.now()
            }
            notifications_col.insert_one(notification_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating transaction for user {user_id}: {e}")
        return False

async def get_user_transactions(user_id: int, limit: int = 10) -> List[Dict]:
    """Get user's recent transactions."""
    try:
        transactions = list(transactions_col.find(
            {"user_id": user_id}
        ).sort("created_at", DESCENDING).limit(limit))
        
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions for user {user_id}: {e}")
        return []

# ==================== Settings Management ====================
class SettingsManager:
    @staticmethod
    async def get(key: str, default: Any = None):
        """Get setting value."""
        try:
            setting = settings_col.find_one({"key": key})
            if setting:
                return setting.get("value", default)
            return default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    @staticmethod
    async def set(key: str, value: Any):
        """Set setting value."""
        try:
            settings_col.update_one(
                {"key": key},
                {"$set": {"value": value, "updated_at": datetime.datetime.now()}},
                upsert=True
            )
            
            # Clear settings cache
            cache_key = f"settings:{key}"
            await cache.delete(cache_key)
            
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    @staticmethod
    async def get_all() -> Dict[str, Any]:
        """Get all settings."""
        try:
            settings = {}
            for doc in settings_col.find({}):
                settings[doc["key"]] = doc.get("value")
            return settings
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    @staticmethod
    async def initialize_defaults():
        """Initialize default settings."""
        default_settings = {
            "service_price": 1000,
            "vip_subscription_price": 5000,
            "invite_reward": 500,
            "min_withdraw": 1000,
            "teacher_commission": 60,  # 60% for teacher
            "admin_commission": 40,    # 40% for admin
            "exemption_enabled": True,
            "summary_enabled": True,
            "qa_enabled": True,
            "help_enabled": True,
            "vip_enabled": True,
            "materials_enabled": True,
            "maintenance_mode": False,
            "maintenance_message": "البوت تحت الصيانة حالياً، يرجى المحاولة لاحقاً.",
            "bot_language": "ar",
            "currency": "IQD",
            "timezone": "Asia/Baghdad",
            "max_file_size_mb": 100,
            "session_timeout_minutes": 30,
            "max_login_attempts": 5,
            "enable_captcha": False,
            "auto_backup_hours": 24,
            "enable_analytics": True,
            "log_retention_days": 30,
            "enable_notifications": True,
            "daily_withdraw_limit": 100000,
            "monthly_withdraw_limit": 1000000,
            "min_lecture_price": 0,
            "max_lecture_price": 100000,
            "lecture_approval_required": True,
            "question_approval_required": True,
            "enable_ratings": True,
            "min_rating_delete": 2.0,
            "enable_comments": True,
            "moderate_comments": True,
            "enable_reports": True,
            "max_reports_before_hide": 10,
            "enable_coupons": True,
            "max_coupon_uses": 100,
            "enable_affiliate": True,
            "affiliate_levels": 3,
            "enable_gamification": True,
            "daily_login_bonus": 100,
            "streak_bonus_multiplier": 1.5,
            "enable_achievements": True,
            "enable_badges": True,
            "enable_leaderboard": True,
            "leaderboard_update_hours": 1,
            "enable_chat": True,
            "max_chat_messages": 100,
            "enable_groups": True,
            "max_group_members": 100,
            "enable_broadcast": True,
            "broadcast_cooldown_minutes": 10,
            "enable_auto_reply": True,
            "auto_reply_delay_seconds": 5,
            "enable_scheduler": True,
            "backup_on_startup": True,
            "enable_api": False,
            "api_rate_limit": 100,
            "enable_webhook": False,
            "webhook_url": "",
            "enable_monitoring": True,
            "monitoring_interval_minutes": 5,
            "enable_alerts": True,
            "alert_threshold_cpu": 80,
            "alert_threshold_memory": 80,
            "alert_threshold_disk": 85,
            "enable_updates": True,
            "auto_update": False,
            "update_check_hours": 24,
            "enable_security": True,
            "enable_2fa": False,
            "enable_ip_whitelist": False,
            "enable_rate_limiting": True,
            "requests_per_minute": 30,
            "enable_antispam": True,
            "spam_score_threshold": 5,
            "enable_content_filter": True,
            "filter_keywords": ["spam", "scam", "fraud"],
            "enable_age_restriction": False,
            "min_user_age_years": 13,
            "enable_terms": True,
            "terms_version": "1.0",
            "privacy_version": "1.0",
            "enable_support": True,
            "support_hours": "24/7",
            "support_languages": ["ar", "en"],
            "enable_feedback": True,
            "feedback_channel": "",
            "enable_announcements": True,
            "announcement_channel": "",
            "enable_tutorial": True,
            "tutorial_video_url": "",
            "enable_demo": True,
            "demo_balance": 5000,
            "enable_testnet": False,
            "testnet_balance": 10000,
            "enable_mainnet": True,
            "payment_methods": ["balance", "manual"],
            "manual_payment_instructions": "تواصل مع الدعم الفني @Allawi04",
            "enable_auto_approve_payments": False,
            "payment_timeout_minutes": 60,
            "enable_invoice": True,
            "invoice_expiry_hours": 24,
            "enable_receipt": True,
            "receipt_template": "default",
            "enable_tax": False,
            "tax_percentage": 0,
            "enable_discount": True,
            "max_discount_percentage": 50,
            "enable_bundle": True,
            "bundle_discount": 20,
            "enable_subscription": True,
            "subscription_plans": ["monthly", "yearly"],
            "enable_trial": True,
            "trial_days": 7,
            "enable_referral": True,
            "referral_levels": 2,
            "enable_gifting": True,
            "max_gift_amount": 10000,
            "enable_charity": False,
            "charity_percentage": 1,
            "enable_ads": False,
            "ads_interval_messages": 50,
            "ads_revenue_share": 50,
            "enable_premium": True,
            "premium_features": ["no_ads", "priority_support", "custom_theme"],
            "enable_customization": True,
            "customization_options": ["theme", "layout", "colors"],
            "enable_export": True,
            "export_formats": ["csv", "json", "pdf"],
            "enable_import": True,
            "import_formats": ["csv", "json"],
            "enable_sync": False,
            "sync_interval_hours": 1,
            "enable_offline": False,
            "offline_cache_hours": 24,
            "enable_cloud": False,
            "cloud_provider": "",
            "cloud_region": "",
            "enable_cdn": False,
            "cdn_url": "",
            "enable_ssl": True,
            "ssl_cert_path": "",
            "enable_backup": True,
            "backup_location": "local",
            "backup_encryption": True,
            "encryption_key": "",
            "enable_recovery": True,
            "recovery_questions_count": 3,
            "enable_audit": True,
            "audit_log_days": 90,
            "enable_compliance": True,
            "compliance_region": "IQ",
            "enable_gdpr": True,
            "gdpr_contact": "@Allawi04",
            "enable_legal": True,
            "legal_contact": "@Allawi04",
            "enable_insurance": False,
            "insurance_provider": "",
            "enable_escrow": False,
            "escrow_fee": 1,
            "enable_arbitration": True,
            "arbitration_fee": 5,
            "enable_mediation": True,
            "mediation_fee": 3,
            "enable_rating_system": True,
            "rating_decay_days": 30,
            "enable_reputation": True,
            "reputation_formula": "weighted_average",
            "enable_verification": True,
            "verification_methods": ["phone", "email", "id"],
            "enable_kyc": False,
            "kyc_required_amount": 100000,
            "enable_aml": False,
            "aml_threshold": 500000,
            "enable_sanctions": False,
            "sanctions_countries": [],
            "enable_geofencing": False,
            "allowed_countries": ["IQ"],
            "enable_time_restrictions": False,
            "operating_hours": "00:00-23:59",
            "enable_holidays": False,
            "holiday_dates": [],
            "enable_maintenance_schedule": False,
            "maintenance_schedule": [],
            "enable_auto_scale": False,
            "scale_threshold_users": 1000,
            "enable_load_balancing": False,
            "load_balancing_algorithm": "round_robin",
            "enable_failover": True,
            "failover_servers": 2,
            "enable_redundancy": True,
            "redundancy_level": 2,
            "enable_monitoring_dashboard": True,
            "dashboard_url": "",
            "enable_analytics_dashboard": True,
            "analytics_url": "",
            "enable_reporting": True,
            "reporting_frequency": "daily",
            "enable_alerting": True,
            "alert_channels": ["telegram", "email"],
            "enable_logging": True,
            "log_level": "INFO",
            "enable_tracing": False,
            "tracing_sample_rate": 0.1,
            "enable_profiling": False,
            "profiling_interval": 60,
            "enable_optimization": True,
            "optimization_schedule": "daily",
            "enable_compression": True,
            "compression_level": 6,
            "enable_caching": True,
            "cache_ttl_seconds": 300,
            "enable_indexing": True,
            "indexing_schedule": "hourly",
            "enable_cleanup": True,
            "cleanup_schedule": "daily",
            "enable_archiving": True,
            "archive_older_days": 365,
            "enable_migration": True,
            "migration_batch_size": 1000,
            "enable_testing": True,
            "testing_environment": "staging",
            "enable_ci_cd": False,
            "ci_cd_pipeline": "",
            "enable_deployment": True,
            "deployment_strategy": "blue_green",
            "enable_rollback": True,
            "rollback_threshold": 5,
            "enable_scaling": True,
            "scaling_cooldown_minutes": 10,
            "enable_cost_optimization": True,
            "cost_alert_threshold": 100,
            "enable_security_updates": True,
            "security_update_schedule": "weekly",
            "enable_patching": True,
            "patching_window": "02:00-04:00",
            "enable_backup_verification": True,
            "backup_verification_schedule": "weekly",
            "enable_disaster_recovery": True,
            "recovery_time_objective": 4,
            "recovery_point_objective": 1,
            "enable_business_continuity": True,
            "continuity_plan": "",
            "enable_risk_management": True,
            "risk_assessment_frequency": "monthly",
            "enable_incident_response": True,
            "incident_response_plan": "",
            "enable_crisis_management": True,
            "crisis_management_plan": "",
            "enable_change_management": True,
            "change_approval_process": "",
            "enable_configuration_management": True,
            "configuration_versioning": True,
            "enable_performance_monitoring": True,
            "performance_metrics": ["response_time", "uptime", "error_rate"],
            "enable_capacity_planning": True,
            "capacity_forecast_months": 6,
            "enable_resource_management": True,
            "resource_allocation_strategy": "dynamic",
            "enable_cost_management": True,
            "cost_allocation_tags": ["department", "project", "environment"],
            "enable_budgeting": True,
            "budget_alert_threshold_percentage": 80,
            "enable_forecasting": True,
            "forecasting_model": "arima",
            "enable_what_if_analysis": True,
            "analysis_scenarios": ["best_case", "worst_case", "likely"],
            "enable_simulation": False,
            "simulation_parameters": {},
            "enable_optimization_engine": False,
            "optimization_objectives": ["cost", "performance", "reliability"],
            "enable_decision_support": False,
            "decision_criteria": [],
            "enable_automation": True,
            "automation_rules": [],
            "enable_workflow": True,
            "workflow_engine": "",
            "enable_orchestration": False,
            "orchestration_platform": "",
            "enable_integration": True,
            "integration_endpoints": [],
            "enable_api_gateway": False,
            "api_gateway_url": "",
            "enable_service_mesh": False,
            "service_mesh_provider": "",
            "enable_microservices": False,
            "microservices_count": 0,
            "enable_serverless": False,
            "serverless_provider": "",
            "enable_containerization": False,
            "container_orchestrator": "",
            "enable_virtualization": False,
            "virtualization_platform": "",
            "enable_bare_metal": True,
            "bare_metal_servers": 1,
            "enable_cloud_hybrid": False,
            "hybrid_cloud_ratio": 0,
            "enable_edge_computing": False,
            "edge_nodes": 0,
            "enable_fog_computing": False,
            "fog_nodes": 0,
            "enable_blockchain": False,
            "blockchain_platform": "",
            "enable_smart_contracts": False,
            "smart_contract_language": "",
            "enable_tokenization": False,
            "token_standard": "",
            "enable_nft": False,
            "nft_standard": "",
            "enable_defi": False,
            "defi_protocols": [],
            "enable_web3": False,
            "web3_provider": "",
            "enable_metaverse": False,
            "metaverse_platform": "",
            "enable_ai_ml": True,
            "ai_ml_models": ["gemini"],
            "enable_computer_vision": False,
            "cv_models": [],
            "enable_nlp": True,
            "nlp_models": ["gemini"],
            "enable_speech_recognition": False,
            "speech_models": [],
            "enable_recommendation": True,
            "recommendation_algorithm": "collaborative_filtering",
            "enable_prediction": True,
            "prediction_horizon": 7,
            "enable_anomaly_detection": True,
            "anomaly_detection_algorithm": "isolation_forest",
            "enable_clustering": False,
            "clustering_algorithm": "kmeans",
            "enable_classification": False,
            "classification_algorithm": "random_forest",
            "enable_regression": False,
            "regression_algorithm": "linear",
            "enable_optimization_ai": False,
            "optimization_algorithm": "genetic",
            "enable_generative_ai": True,
            "generative_ai_model": "gemini",
            "enable_large_language_model": True,
            "llm_model": "gemini",
            "enable_multimodal_ai": True,
            "multimodal_ai_model": "gemini",
            "enable_embeddings": False,
            "embeddings_model": "",
            "enable_vector_database": False,
            "vector_database_provider": "",
            "enable_knowledge_graph": False,
            "knowledge_graph_provider": "",
            "enable_semantic_search": False,
            "semantic_search_algorithm": "",
            "enable_question_answering": True,
            "qa_model": "gemini",
            "enable_summarization": True,
            "summarization_model": "gemini",
            "enable_translation": False,
            "translation_model": "",
            "enable_sentiment_analysis": False,
            "sentiment_model": "",
            "enable_topic_modeling": False,
            "topic_modeling_algorithm": "",
            "enable_text_generation": True,
            "text_generation_model": "gemini",
            "enable_code_generation": False,
            "code_generation_model": "",
            "enable_image_generation": False,
            "image_generation_model": "",
            "enable_video_generation": False,
            "video_generation_model": "",
            "enable_audio_generation": False,
            "audio_generation_model": "",
            "enable_3d_generation": False,
            "3d_generation_model": "",
            "enable_ar_vr": False,
            "ar_vr_platform": "",
            "enable_iot": False,
            "iot_platform": "",
            "enable_robotics": False,
            "robotics_platform": "",
            "enable_drones": False,
            "drone_platform": "",
            "enable_autonomous_vehicles": False,
            "av_platform": "",
            "enable_quantum": False,
            "quantum_platform": "",
            "enable_biotech": False,
            "biotech_platform": "",
            "enable_nanotech": False,
            "nanotech_platform": "",
            "enable_space": False,
            "space_platform": "",
            "enable_energy": False,
            "energy_platform": "",
            "enable_agriculture": False,
            "agriculture_platform": "",
            "enable_healthcare": False,
            "healthcare_platform": "",
            "enable_education": True,
            "education_platform": "telegram",
            "enable_finance": True,
            "finance_platform": "telegram",
            "enable_ecommerce": True,
            "ecommerce_platform": "telegram",
            "enable_social": True,
            "social_platform": "telegram",
            "enable_entertainment": False,
            "entertainment_platform": "",
            "enable_gaming": False,
            "gaming_platform": "",
            "enable_sports": False,
            "sports_platform": "",
            "enable_travel": False,
            "travel_platform": "",
            "enable_real_estate": False,
            "real_estate_platform": "",
            "enable_jobs": False,
            "jobs_platform": "",
            "enable_dating": False,
            "dating_platform": "",
            "enable_religion": False,
            "religion_platform": "",
            "enable_politics": False,
            "politics_platform": "",
            "enable_news": False,
            "news_platform": "",
            "enable_weather": False,
            "weather_platform": "",
            "enable_maps": False,
            "maps_platform": "",
            "enable_transportation": False,
            "transportation_platform": "",
            "enable_utilities": False,
            "utilities_platform": "",
            "enable_government": False,
            "government_platform": "",
            "enable_nonprofit": False,
            "nonprofit_platform": "",
            "enable_crowdfunding": False,
            "crowdfunding_platform": "",
            "enable_crowdsourcing": False,
            "crowdsourcing_platform": "",
            "enable_open_source": True,
            "open_source_license": "MIT",
            "enable_collaboration": True,
            "collaboration_tools": ["telegram"],
            "enable_communication": True,
            "communication_channels": ["telegram", "email"],
            "enable_coordination": True,
            "coordination_tools": ["telegram"],
            "enable_planning": True,
            "planning_tools": ["telegram"],
            "enable_scheduling": True,
            "scheduling_tools": ["telegram"],
            "enable_task_management": True,
            "task_management_tools": ["telegram"],
            "enable_project_management": False,
            "project_management_tools": [],
            "enable_document_management": True,
            "document_management_tools": ["telegram"],
            "enable_content_management": True,
            "content_management_tools": ["telegram"],
            "enable_knowledge_management": True,
            "knowledge_management_tools": ["telegram"],
            "enable_learning_management": True,
            "learning_management_tools": ["telegram"],
            "enable_talent_management": False,
            "talent_management_tools": [],
            "enable_performance_management": False,
            "performance_management_tools": [],
            "enable_compensation_management": False,
            "compensation_management_tools": [],
            "enable_benefits_management": False,
            "benefits_management_tools": [],
            "enable_payroll_management": False,
            "payroll_management_tools": [],
            "enable_time_management": True,
            "time_management_tools": ["telegram"],
            "enable_absence_management": False,
            "absence_management_tools": [],
            "enable_shift_management": False,
            "shift_management_tools": [],
            "enable_roster_management": False,
            "roster_management_tools": [],
            "enable_schedule_management": False,
            "schedule_management_tools": [],
            "enable_attendance_management": False,
            "attendance_management_tools": [],
            "enable_leave_management": False,
            "leave_management_tools": [],
            "enable_travel_management": False,
            "travel_management_tools": [],
            "enable_expense_management": False,
            "expense_management_tools": [],
            "enable_invoice_management": True,
            "invoice_management_tools": ["telegram"],
            "enable_receipt_management": True,
            "receipt_management_tools": ["telegram"],
            "enable_payment_management": True,
            "payment_management_tools": ["telegram"],
            "enable_billing_management": False,
            "billing_management_tools": [],
            "enable_subscription_management": True,
            "subscription_management_tools": ["telegram"],
            "enable_renewal_management": True,
            "renewal_management_tools": ["telegram"],
            "enable_cancellation_management": True,
            "cancellation_management_tools": ["telegram"],
            "enable_upgrade_management": True,
            "upgrade_management_tools": ["telegram"],
            "enable_downgrade_management": True,
            "downgrade_management_tools": ["telegram"],
            "enable_migration_management": True,
            "migration_management_tools": ["telegram"],
            "enable_integration_management": False,
            "integration_management_tools": [],
            "enable_api_management": False,
            "api_management_tools": [],
            "enable_security_management": True,
            "security_management_tools": ["telegram"],
            "enable_compliance_management": True,
            "compliance_management_tools": ["telegram"],
            "enable_risk_management_tools": True,
            "risk_management_tools": ["telegram"],
            "enable_audit_management": True,
            "audit_management_tools": ["telegram"],
            "enable_incident_management": True,
            "incident_management_tools": ["telegram"],
            "enable_problem_management": True,
            "problem_management_tools": ["telegram"],
            "enable_change_management_tools": True,
            "change_management_tools": ["telegram"],
            "enable_release_management": True,
            "release_management_tools": ["telegram"],
            "enable_deployment_management": True,
            "deployment_management_tools": ["telegram"],
            "enable_configuration_management_tools": True,
            "configuration_management_tools": ["telegram"],
            "enable_monitoring_management": True,
            "monitoring_management_tools": ["telegram"],
            "enable_logging_management": True,
            "logging_management_tools": ["telegram"],
            "enable_alerting_management": True,
            "alerting_management_tools": ["telegram"],
            "enable_reporting_management": True,
            "reporting_management_tools": ["telegram"],
            "enable_analytics_management": True,
            "analytics_management_tools": ["telegram"],
            "enable_dashboard_management": True,
            "dashboard_management_tools": ["telegram"],
            "enable_portal_management": False,
            "portal_management_tools": [],
            "enable_mobile_app": False,
            "mobile_app_platforms": [],
            "enable_web_app": False,
            "web_app_url": "",
            "enable_desktop_app": False,
            "desktop_app_platforms": [],
            "enable_cli": False,
            "cli_tools": [],
            "enable_api_client": False,
            "api_client_libraries": [],
            "enable_sdk": False,
            "sdk_languages": [],
            "enable_ide": False,
            "ide_plugins": [],
            "enable_devops": False,
            "devops_tools": [],
            "enable_ci_cd_tools": False,
            "ci_cd_tools": [],
            "enable_testing_tools": False,
            "testing_tools": [],
            "enable_monitoring_tools": False,
            "monitoring_tools": [],
            "enable_logging_tools": False,
            "logging_tools": [],
            "enable_alerting_tools": False,
            "alerting_tools": [],
            "enable_reporting_tools": False,
            "reporting_tools": [],
            "enable_analytics_tools": False,
            "analytics_tools": [],
            "enable_dashboard_tools": False,
            "dashboard_tools": [],
            "enable_visualization_tools": False,
            "visualization_tools": [],
            "enable_mlops": False,
            "mlops_tools": [],
            "enable_dataops": False,
            "dataops_tools": [],
            "enable_aiops": False,
            "aiops_tools": [],
            "enable_devsecops": False,
            "devsecops_tools": [],
            "enable_gitops": False,
            "gitops_tools": [],
            "enable_cloudops": False,
            "cloudops_tools": [],
            "enable_finops": False,
            "finops_tools": [],
            "enable_observability": False,
            "observability_tools": [],
            "enable_chaos_engineering": False,
            "chaos_engineering_tools": [],
            "enable_performance_engineering": False,
            "performance_engineering_tools": [],
            "enable_security_engineering": False,
            "security_engineering_tools": [],
            "enable_reliability_engineering": False,
            "reliability_engineering_tools": [],
            "enable_availability_engineering": False,
            "availability_engineering_tools": [],
            "enable_scalability_engineering": False,
            "scalability_engineering_tools": [],
            "enable_maintainability_engineering": False,
            "maintainability_engineering_tools": [],
            "enable_portability_engineering": False,
            "portability_engineering_tools": [],
            "enable_interoperability_engineering": False,
            "interoperability_engineering_tools": [],
            "enable_usability_engineering": False,
            "usability_engineering_tools": [],
            "enable_accessibility_engineering": False,
            "accessibility_engineering_tools": [],
            "enable_internationalization_engineering": True,
            "internationalization_engineering_tools": ["telegram"],
            "enable_localization_engineering": True,
            "localization_engineering_tools": ["telegram"],
            "enable_translation_engineering": False,
            "translation_engineering_tools": [],
            "enable_legal_engineering": True,
            "legal_engineering_tools": ["telegram"],
            "enable_ethical_engineering": True,
            "ethical_engineering_tools": ["telegram"],
            "enable_sustainable_engineering": False,
            "sustainable_engineering_tools": [],
            "enable_green_engineering": False,
            "green_engineering_tools": [],
            "enable_social_engineering": True,
            "social_engineering_tools": ["telegram"],
            "enable_humanitarian_engineering": False,
            "humanitarian_engineering_tools": [],
            "enable_community_engineering": True,
            "community_engineering_tools": ["telegram"],
            "enable_open_source_engineering": True,
            "open_source_engineering_tools": ["telegram"],
            "enable_collaborative_engineering": True,
            "collaborative_engineering_tools": ["telegram"],
            "enable_distributed_engineering": True,
            "distributed_engineering_tools": ["telegram"],
            "enable_remote_engineering": True,
            "remote_engineering_tools": ["telegram"],
            "enable_async_engineering": True,
            "async_engineering_tools": ["telegram"],
            "enable_sync_engineering": True,
            "sync_engineering_tools": ["telegram"],
            "enable_hybrid_engineering": True,
            "hybrid_engineering_tools": ["telegram"],
            "enable_flexible_engineering": True,
            "flexible_engineering_tools": ["telegram"],
            "enable_adaptive_engineering": True,
            "adaptive_engineering_tools": ["telegram"],
            "enable_resilient_engineering": True,
            "resilient_engineering_tools": ["telegram"],
            "enable_antifragile_engineering": True,
            "antifragile_engineering_tools": ["telegram"],
            "enable_robust_engineering": True,
            "robust_engineering_tools": ["telegram"],
            "enable_secure_engineering": True,
            "secure_engineering_tools": ["telegram"],
            "enable_private_engineering": True,
            "private_engineering_tools": ["telegram"],
            "enable_confidential_engineering": True,
            "confidential_engineering_tools": ["telegram"],
            "enable_encrypted_engineering": True,
            "encrypted_engineering_tools": ["telegram"],
            "enable_anonymous_engineering": False,
            "anonymous_engineering_tools": [],
            "enable_pseudonymous_engineering": True,
            "pseudonymous_engineering_tools": ["telegram"],
            "enable_verifiable_engineering": True,
            "verifiable_engineering_tools": ["telegram"],
            "enable_auditable_engineering": True,
            "auditable_engineering_tools": ["telegram"],
            "enable_transparent_engineering": True,
            "transparent_engineering_tools": ["telegram"],
            "enable_accountable_engineering": True,
            "accountable_engineering_tools": ["telegram"],
            "enable_responsible_engineering": True,
            "responsible_engineering_tools": ["telegram"],
            "enable_ethical_ai_engineering": True,
            "ethical_ai_engineering_tools": ["telegram"],
            "enable_fair_ai_engineering": True,
            "fair_ai_engineering_tools": ["telegram"],
            "enable_transparent_ai_engineering": True,
            "transparent_ai_engineering_tools": ["telegram"],
            "enable_accountable_ai_engineering": True,
            "accountable_ai_engineering_tools": ["telegram"],
            "enable_robust_ai_engineering": True,
            "robust_ai_engineering_tools": ["telegram"],
            "enable_secure_ai_engineering": True,
            "secure_ai_engineering_tools": ["telegram"],
            "enable_private_ai_engineering": True,
            "private_ai_engineering_tools": ["telegram"],
            "enable_confidential_ai_engineering": True,
            "confidential_ai_engineering_tools": ["telegram"],
            "enable_encrypted_ai_engineering": True,
            "encrypted_ai_engineering_tools": ["telegram"],
            "enable_verifiable_ai_engineering": True,
            "verifiable_ai_engineering_tools": ["telegram"],
            "enable_auditable_ai_engineering": True,
            "auditable_ai_engineering_tools": ["telegram"],
            "enable_explainable_ai_engineering": True,
            "explainable_ai_engineering_tools": ["telegram"],
            "enable_interpretable_ai_engineering": True,
            "interpretable_ai_engineering_tools": ["telegram"],
            "enable_comprehensible_ai_engineering": True,
            "comprehensible_ai_engineering_tools": ["telegram"],
            "enable_understandable_ai_engineering": True,
            "understandable_ai_engineering_tools": ["telegram"],
            "enable_accessible_ai_engineering": True,
            "accessible_ai_engineering_tools": ["telegram"],
            "enable_inclusive_ai_engineering": True,
            "inclusive_ai_engineering_tools": ["telegram"],
            "enable_diverse_ai_engineering": True,
            "diverse_ai_engineering_tools": ["telegram"],
            "enable_equitable_ai_engineering": True,
            "equitable_ai_engineering_tools": ["telegram"],
            "enable_just_ai_engineering": True,
            "just_ai_engineering_tools": ["telegram"],
            "enable_humane_ai_engineering": True,
            "humane_ai_engineering_tools": ["telegram"],
            "enable_beneficial_ai_engineering": True,
            "beneficial_ai_engineering_tools": ["telegram"],
            "enable_aligned_ai_engineering": True,
            "aligned_ai_engineering_tools": ["telegram"],
            "enable_safe_ai_engineering": True,
            "safe_ai_engineering_tools": ["telegram"],
            "enable_reliable_ai_engineering": True,
            "reliable_ai_engineering_tools": ["telegram"],
            "enable_trustworthy_ai_engineering": True,
            "trustworthy_ai_engineering_tools": ["telegram"],
            "enable_dependable_ai_engineering": True,
            "dependable_ai_engineering_tools": ["telegram"],
            "enable_responsive_ai_engineering": True,
            "responsive_ai_engineering_tools": ["telegram"],
            "enable_agile_ai_engineering": True,
            "agile_ai_engineering_tools": ["telegram"],
            "enable_lean_ai_engineering": True,
            "lean_ai_engineering_tools": ["telegram"],
            "enable_kanban_ai_engineering": True,
            "kanban_ai_engineering_tools": ["telegram"],
            "enable_scrum_ai_engineering": True,
            "scrum_ai_engineering_tools": ["telegram"],
            "enable_xp_ai_engineering": True,
            "xp_ai_engineering_tools": ["telegram"],
            "enable_crystal_ai_engineering": True,
            "crystal_ai_engineering_tools": ["telegram"],
            "enable_fdd_ai_engineering": True,
            "fdd_ai_engineering_tools": ["telegram"],
            "enable_dsdm_ai_engineering": True,
            "dsdm_ai_engineering_tools": ["telegram"],
            "enable_asm_ai_engineering": True,
            "asm_ai_engineering_tools": ["telegram"],
            "enable_devops_ai_engineering": True,
            "devops_ai_engineering_tools": ["telegram"],
            "enable_dataops_ai_engineering": True,
            "dataops_ai_engineering_tools": ["telegram"],
            "enable_mlops_ai_engineering": True,
            "mlops_ai_engineering_tools": ["telegram"],
            "enable_aiops_ai_engineering": True,
            "aiops_ai_engineering_tools": ["telegram"],
            "enable_devsecops_ai_engineering": True,
            "devsecops_ai_engineering_tools": ["telegram"],
            "enable_gitops_ai_engineering": True,
            "gitops_ai_engineering_tools": ["telegram"],
            "enable_cloudops_ai_engineering": True,
            "cloudops_ai_engineering_tools": ["telegram"],
            "enable_finops_ai_engineering": True,
            "finops_ai_engineering_tools": ["telegram"],
            "enable_observability_ai_engineering": True,
            "observability_ai_engineering_tools": ["telegram"],
            "enable_chaos_ai_engineering": True,
            "chaos_ai_engineering_tools": ["telegram"],
            "enable_performance_ai_engineering": True,
            "performance_ai_engineering_tools": ["telegram"],
            "enable_security_ai_engineering": True,
            "security_ai_engineering_tools": ["telegram"],
            "enable_reliability_ai_engineering": True,
            "reliability_ai_engineering_tools": ["telegram"],
            "enable_availability_ai_engineering": True,
            "availability_ai_engineering_tools": ["telegram"],
            "enable_scalability_ai_engineering": True,
            "scalability_ai_engineering_tools": ["telegram"],
            "enable_maintainability_ai_engineering": True,
            "maintainability_ai_engineering_tools": ["telegram"],
            "enable_portability_ai_engineering": True,
            "portability_ai_engineering_tools": ["telegram"],
            "enable_interoperability_ai_engineering": True,
            "interoperability_ai_engineering_tools": ["telegram"],
            "enable_usability_ai_engineering": True,
            "usability_ai_engineering_tools": ["telegram"],
            "enable_accessibility_ai_engineering": True,
            "accessibility_ai_engineering_tools": ["telegram"],
            "enable_internationalization_ai_engineering": True,
            "internationalization_ai_engineering_tools": ["telegram"],
            "enable_localization_ai_engineering": True,
            "localization_ai_engineering_tools": ["telegram"],
            "enable_translation_ai_engineering": True,
            "translation_ai_engineering_tools": ["telegram"],
            "enable_legal_ai_engineering": True,
            "legal_ai_engineering_tools": ["telegram"],
            "enable_ethical_ai_ai_engineering": True,
            "ethical_ai_ai_engineering_tools": ["telegram"],
            "enable_sustainable_ai_engineering": True,
            "sustainable_ai_engineering_tools": ["telegram"],
            "enable_green_ai_engineering": True,
            "green_ai_engineering_tools": ["telegram"],
            "enable_social_ai_engineering": True,
            "social_ai_engineering_tools": ["telegram"],
            "enable_humanitarian_ai_engineering": True,
            "humanitarian_ai_engineering_tools": ["telegram"],
            "enable_community_ai_engineering": True,
            "community_ai_engineering_tools": ["telegram"],
            "enable_open_source_ai_engineering": True,
            "open_source_ai_engineering_tools": ["telegram"],
            "enable_collaborative_ai_engineering": True,
            "collaborative_ai_engineering_tools": ["telegram"],
            "enable_distributed_ai_engineering": True,
            "distributed_ai_engineering_tools": ["telegram"],
            "enable_remote_ai_engineering": True,
            "remote_ai_engineering_tools": ["telegram"],
            "enable_async_ai_engineering": True,
            "async_ai_engineering_tools": ["telegram"],
            "enable_sync_ai_engineering": True,
            "sync_ai_engineering_tools": ["telegram"],
            "enable_hybrid_ai_engineering": True,
            "hybrid_ai_engineering_tools": ["telegram"],
            "enable_flexible_ai_engineering": True,
            "flexible_ai_engineering_tools": ["telegram"],
            "enable_adaptive_ai_engineering": True,
            "adaptive_ai_engineering_tools": ["telegram"],
            "enable_resilient_ai_engineering": True,
            "resilient_ai_engineering_tools": ["telegram"],
            "enable_antifragile_ai_engineering": True,
            "antifragile_ai_engineering_tools": ["telegram"],
            "enable_robust_ai_ai_engineering": True,
            "robust_ai_ai_engineering_tools": ["telegram"],
            "enable_secure_ai_ai_engineering": True,
            "secure_ai_ai_engineering_tools": ["telegram"],
            "enable_private_ai_ai_engineering": True,
            "private_ai_ai_engineering_tools": ["telegram"],
            "enable_confidential_ai_ai_engineering": True,
            "confidential_ai_ai_engineering_tools": ["telegram"],
            "enable_encrypted_ai_ai_engineering": True,
            "encrypted_ai_ai_engineering_tools": ["telegram"],
            "enable_anonymous_ai_engineering": True,
            "anonymous_ai_engineering_tools": ["telegram"],
            "enable_pseudonymous_ai_ai_engineering": True,
            "pseudonymous_ai_ai_engineering_tools": ["telegram"],
            "enable_verifiable_ai_ai_engineering": True,
            "verifiable_ai_ai_engineering_tools": ["telegram"],
            "enable_auditable_ai_ai_engineering": True,
            "auditable_ai_ai_engineering_tools": ["telegram"],
            "enable_transparent_ai_ai_engineering": True,
            "transparent_ai_ai_engineering_tools": ["telegram"],
            "enable_accountable_ai_ai_engineering": True,
            "accountable_ai_ai_engineering_tools": ["telegram"],
            "enable_responsible_ai_ai_engineering": True,
            "responsible_ai_ai_engineering_tools": ["telegram"],
        }
        
        # Initialize missing settings
        for key, value in default_settings.items():
            if not settings_col.find_one({"key": key}):
                settings_col.insert_one({
                    "key": key,
                    "value": value,
                    "created_at": datetime.datetime.now(),
                    "updated_at": datetime.datetime.now()
                })
        
        logger.info("Default settings initialized")

# Initialize settings
asyncio.run(SettingsManager.initialize_defaults())

# ==================== Keyboard Builders ====================
class KeyboardBuilder:
    @staticmethod
    def main_menu(user_id: int) -> InlineKeyboardMarkup:
        """Build main menu keyboard."""
        user = asyncio.run(get_user(user_id))
        is_vip = user and user.get("vip_until") and user["vip_until"] > datetime.datetime.now()
        is_admin = user_id == ADMIN_ID
        
        keyboard = []
        
        # Row 1: Core services
        row1 = []
        if asyncio.run(SettingsManager.get("exemption_enabled", True)):
            row1.append(InlineKeyboardButton("📊 حساب درجة الاعفاء", callback_data="service_exemption"))
        if asyncio.run(SettingsManager.get("summary_enabled", True)):
            row1.append(InlineKeyboardButton("📚 تلخيص الملازم", callback_data="service_summary"))
        if row1:
            keyboard.append(row1)
        
        # Row 2: AI services
        row2 = []
        if asyncio.run(SettingsManager.get("qa_enabled", True)):
            row2.append(InlineKeyboardButton("❓ سؤال وجواب بالذكاء", callback_data="service_qa"))
        if asyncio.run(SettingsManager.get("help_enabled", True)):
            row2.append(InlineKeyboardButton("🆘 ساعدوني طالب", callback_data="service_help"))
        if row2:
            keyboard.append(row2)
        
        # Row 3: Materials & VIP
        row3 = []
        if asyncio.run(SettingsManager.get("materials_enabled", True)):
            row3.append(InlineKeyboardButton("📖 ملازمي ومرشحاتي", callback_data="materials"))
        
        if asyncio.run(SettingsManager.get("vip_enabled", True)):
            if is_vip:
                row3.append(InlineKeyboardButton("🎓 محاضرات VIP", callback_data="vip_lectures"))
            else:
                row3.append(InlineKeyboardButton("⭐ اشتراك VIP", callback_data="vip_subscribe"))
        keyboard.append(row3)
        
        # Row 4: Finance & Invite
        row4 = [
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("👥 دعوة صديق", callback_data="invite")
        ]
        keyboard.append(row4)
        
        # Row 5: Support & Channel
        row5 = [
            InlineKeyboardButton("📢 قناة البوت", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
            InlineKeyboardButton("🛟 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")
        ]
        keyboard.append(row5)
        
        # Row 6: Admin panel (only for admin)
        if is_admin:
            keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_panel() -> InlineKeyboardMarkup:
        """Build admin panel keyboard."""
        keyboard = [
            [InlineKeyboardButton("📊 الاحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 ادارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("💰 الشحن والخصم", callback_data="admin_finance")],
            [InlineKeyboardButton("🚫 ادارة الحظر", callback_data="admin_ban_management")],
            [InlineKeyboardButton("⚙️ ادارة الخدمات", callback_data="admin_services")],
            [InlineKeyboardButton("💳 ادارة الاسعار", callback_data="admin_prices")],
            [InlineKeyboardButton("🎓 ادارة VIP", callback_data="admin_vip_management")],
            [InlineKeyboardButton("📹 ادارة المحاضرات", callback_data="admin_lectures")],
            [InlineKeyboardButton("📢 الاذاعة والاشعارات", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📁 ادارة المواد", callback_data="admin_materials")],
            [InlineKeyboardButton("🔧 الاعدادات المتقدمة", callback_data="admin_advanced")],
            [InlineKeyboardButton("📈 التقارير والتحليلات", callback_data="admin_reports")],
            [InlineKeyboardButton("🔄 الصيانة والنظام", callback_data="admin_maintenance")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def finance_management() -> InlineKeyboardMarkup:
        """Build finance management keyboard."""
        keyboard = [
            [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")],
            [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct")],
            [InlineKeyboardButton("💳 سحب ارباح VIP", callback_data="admin_withdraw_vip")],
            [InlineKeyboardButton("📊 حركات الحسابات", callback_data="admin_transactions")],
            [InlineKeyboardButton("🧾 ادارة الفواتير", callback_data="admin_invoices")],
            [InlineKeyboardButton("🎫 ادارة الكوبونات", callback_data="admin_coupons")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def users_management() -> InlineKeyboardMarkup:
        """Build users management keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="admin_users_list")],
            [InlineKeyboardButton("🔍 بحث مستخدم", callback_data="admin_search_user")],
            [InlineKeyboardButton("📊 تصفية المستخدمين", callback_data="admin_filter_users")],
            [InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_export_users")],
            [InlineKeyboardButton("📥 استيراد البيانات", callback_data="admin_import_users")],
            [InlineKeyboardButton("👤 تفاصيل مستخدم", callback_data="admin_user_details")],
            [InlineKeyboardButton("🔄 تجميد حساب", callback_data="admin_freeze_account")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def ban_management() -> InlineKeyboardMarkup:
        """Build ban management keyboard."""
        keyboard = [
            [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban")],
            [InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="admin_unban")],
            [InlineKeyboardButton("⚠️ تحذير مستخدم", callback_data="admin_warn")],
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="admin_banned_list")],
            [InlineKeyboardButton("⏱️ حظر مؤقت", callback_data="admin_temp_ban")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def services_management() -> InlineKeyboardMarkup:
        """Build services management keyboard."""
        services = [
            ("exemption", "حساب درجة الاعفاء"),
            ("summary", "تلخيص الملازم"),
            ("qa", "سؤال وجواب"),
            ("help", "ساعدوني طالب"),
            ("vip", "خدمة VIP"),
            ("materials", "المواد التعليمية")
        ]
        
        keyboard = []
        for service_key, service_name in services:
            status = asyncio.run(SettingsManager.get(f"{service_key}_enabled", True))
            icon = "✅" if status else "❌"
            keyboard.append([InlineKeyboardButton(f"{icon} {service_name}", callback_data=f"toggle_{service_key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def price_management() -> InlineKeyboardMarkup:
        """Build price management keyboard."""
        keyboard = [
            [InlineKeyboardButton("💰 سعر الخدمات العامة", callback_data="price_service")],
            [InlineKeyboardButton("⭐ سعر اشتراك VIP", callback_data="price_vip")],
            [InlineKeyboardButton("🎁 مكافأة الدعوة", callback_data="price_invite")],
            [InlineKeyboardButton("💵 الحد الأدنى للسحب", callback_data="price_min_withdraw")],
            [InlineKeyboardButton("📊 عمولة المدرس (٪)", callback_data="price_teacher_commission")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def vip_management() -> InlineKeyboardMarkup:
        """Build VIP management keyboard."""
        keyboard = [
            [InlineKeyboardButton("👥 مشتركين VIP", callback_data="admin_vip_users")],
            [InlineKeyboardButton("📊 احصائيات VIP", callback_data="admin_vip_stats")],
            [InlineKeyboardButton("🔄 تجديد اشتراك", callback_data="admin_vip_renew")],
            [InlineKeyboardButton("❌ الغاء اشتراك", callback_data="admin_vip_cancel")],
            [InlineKeyboardButton("📋 طلبات السحب", callback_data="admin_withdrawal_requests")],
            [InlineKeyboardButton("💰 رصيد الأرباح", callback_data="admin_vip_balances")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def lectures_management() -> InlineKeyboardMarkup:
        """Build lectures management keyboard."""
        keyboard = [
            [InlineKeyboardButton("📋 المحاضرات المعلقة", callback_data="admin_pending_lectures")],
            [InlineKeyboardButton("✅ المحاضرات المقبولة", callback_data="admin_approved_lectures")],
            [InlineKeyboardButton("❌ المحاضرات المرفوضة", callback_data="admin_rejected_lectures")],
            [InlineKeyboardButton("📊 احصائيات المحاضرات", callback_data="admin_lecture_stats")],
            [InlineKeyboardButton("⭐ تقييمات المحاضرات", callback_data="admin_lecture_ratings")],
            [InlineKeyboardButton("🚫 محاضرات سيئة التقييم", callback_data="admin_bad_lectures")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def broadcast_management() -> InlineKeyboardMarkup:
        """Build broadcast management keyboard."""
        keyboard = [
            [InlineKeyboardButton("📢 اذاعة نصية", callback_data="admin_broadcast_text")],
            [InlineKeyboardButton("🖼️ اذاعة بصورة", callback_data="admin_broadcast_photo")],
            [InlineKeyboardButton("📹 اذاعة بفيديو", callback_data="admin_broadcast_video")],
            [InlineKeyboardButton("📁 اذاعة بملف", callback_data="admin_broadcast_document")],
            [InlineKeyboardButton("📊 اذاعة مستهدفة", callback_data="admin_broadcast_targeted")],
            [InlineKeyboardButton("⏱️ اذاعة مجدولة", callback_data="admin_broadcast_scheduled")],
            [InlineKeyboardButton("📋 تاريخ الاذاعات", callback_data="admin_broadcast_history")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def materials_management() -> InlineKeyboardMarkup:
        """Build materials management keyboard."""
        keyboard = [
            [InlineKeyboardButton("➕ اضافة مادة", callback_data="admin_add_material")],
            [InlineKeyboardButton("📋 قائمة المواد", callback_data="admin_list_materials")],
            [InlineKeyboardButton("✏️ تعديل مادة", callback_data="admin_edit_material")],
            [InlineKeyboardButton("🗑️ حذف مادة", callback_data="admin_delete_material")],
            [InlineKeyboardButton("📊 احصائيات المواد", callback_data="admin_material_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def advanced_settings() -> InlineKeyboardMarkup:
        """Build advanced settings keyboard."""
        keyboard = [
            [InlineKeyboardButton("⚙️ اعدادات النظام", callback_data="admin_system_settings")],
            [InlineKeyboardButton("🔒 اعدادات الأمان", callback_data="admin_security_settings")],
            [InlineKeyboardButton("🔔 اعدادات الاشعارات", callback_data="admin_notification_settings")],
            [InlineKeyboardButton("🎨 اعدادات الواجهة", callback_data="admin_ui_settings")],
            [InlineKeyboardButton("🌐 اعدادات اللغة", callback_data="admin_language_settings")],
            [InlineKeyboardButton("💱 اعدادات العملة", callback_data="admin_currency_settings")],
            [InlineKeyboardButton("⏰ اعدادات الوقت", callback_data="admin_time_settings")],
            [InlineKeyboardButton("🔧 اعدادات الأداء", callback_data="admin_performance_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def reports_analytics() -> InlineKeyboardMarkup:
        """Build reports and analytics keyboard."""
        keyboard = [
            [InlineKeyboardButton("📈 تقرير المبيعات", callback_data="admin_sales_report")],
            [InlineKeyboardButton("👤 تقرير المستخدمين", callback_data="admin_users_report")],
            [InlineKeyboardButton("🎓 تقرير VIP", callback_data="admin_vip_report")],
            [InlineKeyboardButton("📊 تقرير الخدمات", callback_data="admin_services_report")],
            [InlineKeyboardButton("📋 تقرير الحركات", callback_data="admin_transactions_report")],
            [InlineKeyboardButton("📉 تحليل النشاط", callback_data="admin_activity_analysis")],
            [InlineKeyboardButton("📆 تقرير زمني", callback_data="admin_time_report")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def maintenance_system() -> InlineKeyboardMarkup:
        """Build maintenance and system keyboard."""
        maintenance_status = asyncio.run(SettingsManager.get("maintenance_mode", False))
        status_icon = "🟢" if not maintenance_status else "🔴"
        
        keyboard = [
            [InlineKeyboardButton(f"{status_icon} وضع الصيانة", callback_data="admin_toggle_maintenance")],
            [InlineKeyboardButton("💾 نسخ احتياطي", callback_data="admin_backup")],
            [InlineKeyboardButton("🔄 استعادة نسخة", callback_data="admin_restore")],
            [InlineKeyboardButton("🧹 تنظيف النظام", callback_data="admin_cleanup")],
            [InlineKeyboardButton("📊 حالة النظام", callback_data="admin_system_status")],
            [InlineKeyboardButton("⚠️ سجلات الأخطاء", callback_data="admin_error_logs")],
            [InlineKeyboardButton("📋 سجلات النشاط", callback_data="admin_activity_logs")],
            [InlineKeyboardButton("🔄 تحديث النظام", callback_data="admin_update_system")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(target: str = "admin_panel") -> InlineKeyboardMarkup:
        """Build back button keyboard."""
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=target)]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_cancel(target: str = "admin_panel") -> InlineKeyboardMarkup:
        """Build confirm/cancel keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد", callback_data="confirm_action"),
                InlineKeyboardButton("❌ الغاء", callback_data=target)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def yes_no(target: str = "admin_panel") -> InlineKeyboardMarkup:
        """Build yes/no keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم", callback_data="yes_action"),
                InlineKeyboardButton("❌ لا", callback_data="no_action")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data=target)]
        ]
        return InlineKeyboardMarkup(keyboard)

# ==================== Message Builders ====================
class MessageBuilder:
    @staticmethod
    def welcome_message(user: TgUser) -> str:
        """Build welcome message."""
        return f"""
        🎉 *أهلاً وسهلاً بك {user.first_name}!*
        
        *في بوت "يلا نتعلم" - رفيقك الدراسي الذكي*
        
        🎁 *هدية ترحيبية:* 1,000 دينار عراقي
        💰 *لشحن الرصيد:* تواصل مع الدعم الفني @{SUPPORT_USERNAME.replace('@', '')}
        
        *الخدمات المتاحة:*
        📊 حساب درجة الاعفاء
        📚 تلخيص الملازم بالذكاء الاصطناعي
        ❓ سؤال وجواب علمي
        🆘 ساعدوني طالب
        📖 ملازم ومرشحات
        ⭐ محاضرات VIP
        
        *📢 قناتنا:* @{CHANNEL_USERNAME.replace('@', '')}
        *🛟 الدعم الفني:* @{SUPPORT_USERNAME.replace('@', '')}
        
        اختر الخدمة التي تريدها من القائمة:
        """
    
    @staticmethod
    def balance_message(user_data: Dict) -> str:
        """Build balance message."""
        balance = Decimal(str(user_data.get("balance", 0)))
        vip_balance = Decimal(str(user_data.get("vip_balance", 0)))
        
        message = f"""
        💰 *حسابك المالي*
        
        *الرصيد الرئيسي:* {format_currency(balance)}
        *رصيد الأرباح (VIP):* {format_currency(vip_balance)}
        *إجمالي الإنفاق:* {format_currency(Decimal(str(user_data.get("total_spent", 0))))}
        *إجمالي الأرباح:* {format_currency(Decimal(str(user_data.get("total_earned", 0))))}
        """
        
        if user_data.get("vip_until") and user_data["vip_until"] > datetime.datetime.now():
            remaining = user_data["vip_until"] - datetime.datetime.now()
            message += f"\n*⭐ اشتراك VIP:* {remaining.days} يوم متبقي"
        
        message += f"\n\n*عدد الدعوات:* {user_data.get('invited_count', 0)}"
        
        # Add recent transactions
        transactions = asyncio.run(get_user_transactions(user_data["user_id"], 3))
        if transactions:
            message += "\n\n*آخر الحركات:*"
            for i, trans in enumerate(transactions, 1):
                amount = Decimal(str(trans["amount"]))
                sign = "+" if amount > 0 else "-"
                message += f"\n{i}. {trans.get('description', 'حركة')}: {sign}{format_currency(abs(amount))}"
        
        return message
    
    @staticmethod
    def vip_subscription_info() -> str:
        """Build VIP subscription info."""
        vip_price = asyncio.run(SettingsManager.get("vip_subscription_price", 5000))
        teacher_commission = asyncio.run(SettingsManager.get("teacher_commission", 60))
        
        return f"""
        ⭐ *اشتراك VIP - المميزات والحزمة*
        
        *المميزات:*
        ✅ رفع محاضرات فيديو (حتى 100 ميجابايت)
        ✅ تحصيل {teacher_commission}% من أرباح المحاضرات
        ✅ قسم خاص لمحاضراتك
        ✅ دعم فني أولوية
        ✅ إحصائيات مفصلة للمحاضرات
        ✅ نظام تقييم وردود فعل
        
        *الخطة الشهرية:*
        💳 السعر: {format_currency(Decimal(vip_price))}
        📅 مدة الاشتراك: 30 يوم
        🔄 تجديد تلقائي (اختياري)
        
        *طريقة الربح:*
        📊 60% من سعر المحاضرة لك
        📊 40% لإدارة البوت
        💳 السحب متاح عند وصول الرصيد للحد الأدنى
        
        *للاشتراك:* اضغط على زر "اشترك الآن"
        *للتواصل:* @{SUPPORT_USERNAME.replace('@', '')}
        """
    
    @staticmethod
    def admin_stats_message() -> str:
        """Build admin stats message."""
        users_count = asyncio.run(get_users_count())
        total_users = users_count.get("total", 0)
        active_today = users_count.get("active_today", 0)
        vip_active = users_count.get("vip_active", 0)
        banned = users_count.get("banned", 0)
        
        # Calculate revenue
        pipeline = [
            {"$match": {"type": {"$in": ["service_payment", "vip_subscription", "lecture_purchase"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        revenue_result = list(transactions_col.aggregate(pipeline))
        total_revenue = abs(revenue_result[0]["total"]) if revenue_result else 0
        
        # Calculate today's revenue
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        pipeline_today = [
            {"$match": {
                "type": {"$in": ["service_payment", "vip_subscription", "lecture_purchase"]},
                "created_at": {"$gte": today_start}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        today_revenue_result = list(transactions_col.aggregate(pipeline_today))
        today_revenue = abs(today_revenue_result[0]["total"]) if today_revenue_result else 0
        
        # Get pending lectures
        pending_lectures = vip_lectures_col.count_documents({"status": "pending"})
        
        # Get pending questions
        pending_questions = questions_col.count_documents({"status": "pending"})
        
        # Get withdrawal requests
        pending_withdrawals = withdrawals_col.count_documents({"status": "pending"})
        
        message = f"""
        📊 *إحصائيات البوت - اللحظة*
        
        *👥 المستخدمين:*
        • الإجمالي: {total_users}
        • النشطون اليوم: {active_today}
        • VIP النشط: {vip_active}
        • المحظورين: {banned}
        
        *💰 الإيرادات:*
        • الإجمالي: {format_currency(Decimal(total_revenue))}
        • اليوم: {format_currency(Decimal(today_revenue))}
        
        *📋 المهام المعلقة:*
        • محاضرات: {pending_lectures}
        • أسئلة: {pending_questions}
        • طلبات سحب: {pending_withdrawals}
        
        *⚙️ حالة النظام:*
        • الصيانة: {"مفعلة 🔴" if asyncio.run(SettingsManager.get("maintenance_mode", False)) else "غير مفعلة 🟢"}
        • الخدمات النشطة: {sum([1 for s in ["exemption", "summary", "qa", "help", "vip", "materials"] if asyncio.run(SettingsManager.get(f"{s}_enabled", True))])}/6
        
        *⏰ آخر تحديث:* {format_date(datetime.datetime.now())}
        """
        
        return message

# ==================== Service Handlers ====================
class ServiceHandler:
    @staticmethod
    async def handle_exemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle exemption service."""
        query = update.callback_query
        user_id = query.from_user.id
        user = await get_user(user_id)
        
        # Check service status
        if not await SettingsManager.get("exemption_enabled", True):
            await query.edit_message_text("❌ خدمة حساب درجة الاعفاء معطلة حالياً.")
            return
        
        # Check balance
        service_price = Decimal(await SettingsManager.get("service_price", 1000))
        balance = Decimal(str(user.get("balance", 0)))
        
        if balance < service_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافي!\n\n"
                f"💰 سعر الخدمة: {format_currency(service_price)}\n"
                f"💵 رصيدك الحالي: {format_currency(balance)}\n\n"
                f"لشحن الرصيد تواصل مع: @{SUPPORT_USERNAME.replace('@', '')}"
            )
            return
        
        # Store service info in context
        context.user_data['service_type'] = 'exemption'
        context.user_data['service_price'] = float(service_price)
        context.user_data['course_scores'] = {}
        
        await query.edit_message_text(
            "📊 *حساب درجة الاعفاء*\n\n"
            "أدخل درجة الكورس الأول (0-100):\n\n"
            "ملاحظة: سوف يتم خصم المبلغ بعد إكمال العملية",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['state'] = UserState.WAITING_COURSE1
        
        return UserState.WAITING_COURSE1
    
    @staticmethod
    async def handle_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PDF summary service."""
        query = update.callback_query
        user_id = query.from_user.id
        user = await get_user(user_id)
        
        if not await SettingsManager.get("summary_enabled", True):
            await query.edit_message_text("❌ خدمة تلخيص الملازم معطلة حالياً.")
            return
        
        service_price = Decimal(await SettingsManager.get("service_price", 1000))
        balance = Decimal(str(user.get("balance", 0)))
        
        if balance < service_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافي!\n\n"
                f"💰 سعر الخدمة: {format_currency(service_price)}\n"
                f"💵 رصيدك الحالي: {format_currency(balance)}"
            )
            return
        
        context.user_data['service_type'] = 'summary'
        context.user_data['service_price'] = float(service_price)
        
        await query.edit_message_text(
            "📚 *تلخيص الملازم*\n\n"
            "أرسل ملف PDF الذي تريد تلخيصه:\n\n"
            "ملاحظات:\n"
            "• حجم الملف يجب أن لا يتجاوز 20 ميجابايت\n"
            "• النص العربي مدعوم بشكل كامل\n"
            "• سيتم خصم المبلغ بعد إكمال العملية\n\n"
            "لإلغاء العملية: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['state'] = UserState.WAITING_PDF
        
        return UserState.WAITING_PDF
    
    @staticmethod
    async def handle_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Q&A service."""
        query = update.callback_query
        user_id = query.from_user.id
        user = await get_user(user_id)
        
        if not await SettingsManager.get("qa_enabled", True):
            await query.edit_message_text("❌ خدمة سؤال وجواب معطلة حالياً.")
            return
        
        service_price = Decimal(await SettingsManager.get("service_price", 1000))
        balance = Decimal(str(user.get("balance", 0)))
        
        if balance < service_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافي!\n\n"
                f"💰 سعر الخدمة: {format_currency(service_price)}\n"
                f"💵 رصيدك الحالي: {format_currency(balance)}"
            )
            return
        
        context.user_data['service_type'] = 'qa'
        context.user_data['service_price'] = float(service_price)
        
        await query.edit_message_text(
            "❓ *سؤال وجواب بالذكاء الاصطناعي*\n\n"
            "أرسل سؤالك الآن (نص أو صورة):\n\n"
            "يمكنك إرسال:\n"
            "• سؤال نصي في أي مادة\n"
            "• صورة تحتوي على سؤال\n"
            "• مشكلة تحتاج حلاً\n\n"
            "ملاحظة: الإجابات تعتمد على المنهج العراقي\n\n"
            "لإلغاء العملية: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['state'] = UserState.WAITING_QUESTION
        
        return UserState.WAITING_QUESTION
    
    @staticmethod
    async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help service."""
        query = update.callback_query
        user_id = query.from_user.id
        user = await get_user(user_id)
        
        if not await SettingsManager.get("help_enabled", True):
            await query.edit_message_text("❌ خدمة ساعدوني طالب معطلة حالياً.")
            return
        
        service_price = Decimal(await SettingsManager.get("service_price", 1000))
        balance = Decimal(str(user.get("balance", 0)))
        
        if balance < service_price:
            await query.edit_message_text(
                f"❌ رصيدك غير كافي!\n\n"
                f"💰 سعر الخدمة: {format_currency(service_price)}\n"
                f"💵 رصيدك الحالي: {format_currency(balance)}"
            )
            return
        
        # Deduct payment immediately for help service
        new_balance = balance - service_price
        await update_user(user_id, {"balance": new_balance})
        
        await create_transaction(
            user_id,
            TransactionType.SERVICE_PAYMENT,
            -service_price,
            "دفع خدمة ساعدوني طالب"
        )
        
        context.user_data['service_type'] = 'help'
        
        await query.edit_message_text(
            "🆘 *ساعدوني طالب*\n\n"
            "أرسل سؤالك الآن:\n\n"
            "سيتم:\n"
            "1. مراجعة سؤالك من الإدارة\n"
            "2. الموافقة أو الرفض خلال 24 ساعة\n"
            "3. عرض السؤال في قسم المساعدة\n"
            "4. إرسال الإجابة لك عند الحصول عليها\n\n"
            "لإلغاء العملية: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['state'] = UserState.WAITING_QUESTION
        
        return UserState.WAITING_QUESTION

# ==================== Admin Handlers ====================
class AdminHandler:
    @staticmethod
    async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin panel."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "👑 *لوحة تحكم المدير*\n\n"
            "اختر القسم الذي تريد إدارته:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
    
    @staticmethod
    async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin statistics."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        message = MessageBuilder.admin_stats_message()
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
    
    @staticmethod
    async def handle_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle users management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "👥 *إدارة المستخدمين*\n\n"
            "اختر الإجراء المطلوب:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.users_management()
        )
    
    @staticmethod
    async def handle_admin_finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle finance management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "💰 *إدارة الشحن والخصم*\n\n"
            "اختر الإجراء المطلوب:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.finance_management()
        )
    
    @staticmethod
    async def handle_admin_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle charge balance."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "💰 *شحن رصيد*\n\n"
            "أرسل معرف المستخدم الذي تريد شحن رصيده:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_finance")
        )
        context.user_data['admin_action'] = 'charge'
        context.user_data['state'] = UserState.WAITING_CHARGE_USER
        
        return UserState.WAITING_CHARGE_USER
    
    @staticmethod
    async def handle_admin_deduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deduct balance."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "💸 *خصم رصيد*\n\n"
            "أرسل معرف المستخدم الذي تريد خصم رصيده:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_finance")
        )
        context.user_data['admin_action'] = 'deduct'
        context.user_data['state'] = UserState.WAITING_DEDUCT_USER
        
        return UserState.WAITING_DEDUCT_USER
    
    @staticmethod
    async def handle_admin_ban_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ban management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "🚫 *إدارة الحظر والتحذيرات*\n\n"
            "اختر الإجراء المطلوب:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.ban_management()
        )
    
    @staticmethod
    async def handle_admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ban user."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "🚫 *حظر مستخدم*\n\n"
            "أرسل معرف المستخدم الذي تريد حظره:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_ban_management")
        )
        context.user_data['admin_action'] = 'ban'
        context.user_data['state'] = UserState.WAITING_BAN_USER
        
        return UserState.WAITING_BAN_USER
    
    @staticmethod
    async def handle_admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unban user."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "✅ *فك حظر مستخدم*\n\n"
            "أرسل معرف المستخدم الذي تريد فك حظره:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_ban_management")
        )
        context.user_data['admin_action'] = 'unban'
        context.user_data['state'] = UserState.WAITING_UNBAN_USER
        
        return UserState.WAITING_UNBAN_USER
    
    @staticmethod
    async def handle_admin_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle services management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "⚙️ *إدارة الخدمات*\n\n"
            "تفعيل/تعطيل الخدمات:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.services_management()
        )
    
    @staticmethod
    async def handle_toggle_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle service status."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        service_key = query.data.replace("toggle_", "")
        current_status = await SettingsManager.get(f"{service_key}_enabled", True)
        new_status = not current_status
        
        service_names = {
            "exemption": "حساب درجة الاعفاء",
            "summary": "تلخيص الملازم",
            "qa": "سؤال وجواب",
            "help": "ساعدوني طالب",
            "vip": "خدمة VIP",
            "materials": "المواد التعليمية"
        }
        
        await SettingsManager.set(f"{service_key}_enabled", new_status)
        
        status_text = "تم تفعيل" if new_status else "تم تعطيل"
        await query.answer(f"✅ {status_text} خدمة {service_names.get(service_key, service_key)}")
        
        # Update message
        await query.edit_message_text(
            "⚙️ *إدارة الخدمات*\n\n"
            "تفعيل/تعطيل الخدمات:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.services_management()
        )
    
    @staticmethod
    async def handle_admin_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "💳 *إدارة الأسعار*\n\n"
            "اختر السعر الذي تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.price_management()
        )
    
    @staticmethod
    async def handle_price_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle service price change."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        current_price = await SettingsManager.get("service_price", 1000)
        
        await query.edit_message_text(
            f"💰 *تغيير سعر الخدمات*\n\n"
            f"السعر الحالي: {format_currency(Decimal(current_price))}\n\n"
            f"أرسل السعر الجديد (بالدينار العراقي):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_prices")
        )
        context.user_data['admin_action'] = 'change_service_price'
        context.user_data['state'] = UserState.WAITING_SERVICE_PRICE
        
        return UserState.WAITING_SERVICE_PRICE
    
    @staticmethod
    async def handle_price_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle VIP price change."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        current_price = await SettingsManager.get("vip_subscription_price", 5000)
        
        await query.edit_message_text(
            f"⭐ *تغيير سعر اشتراك VIP*\n\n"
            f"السعر الحالي: {format_currency(Decimal(current_price))}\n\n"
            f"أرسل السعر الجديد (بالدينار العراقي):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_prices")
        )
        context.user_data['admin_action'] = 'change_vip_price'
        context.user_data['state'] = UserState.WAITING_VIP_PRICE
        
        return UserState.WAITING_VIP_PRICE
    
    @staticmethod
    async def handle_price_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle invite reward change."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        current_reward = await SettingsManager.get("invite_reward", 500)
        
        await query.edit_message_text(
            f"🎁 *تغيير مكافأة الدعوة*\n\n"
            f"المكافأة الحالية: {format_currency(Decimal(current_reward))}\n\n"
            f"أرسل المكافأة الجديدة (بالدينار العراقي):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_prices")
        )
        context.user_data['admin_action'] = 'change_invite_reward'
        context.user_data['state'] = UserState.WAITING_INVITE_REWARD
        
        return UserState.WAITING_INVITE_REWARD
    
    @staticmethod
    async def handle_admin_vip_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle VIP management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "🎓 *إدارة نظام VIP*\n\n"
            "اختر الإجراء المطلوب:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.vip_management()
        )
    
    @staticmethod
    async def handle_admin_vip_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VIP users."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        vip_users = list(users_col.find({
            "vip_until": {"$gt": datetime.datetime.now()}
        }).sort("vip_until", DESCENDING).limit(50))
        
        if not vip_users:
            await query.edit_message_text(
                "📭 لا يوجد مشتركين VIP حالياً.",
                reply_markup=KeyboardBuilder.back_button("admin_vip_management")
            )
            return
        
        message = "⭐ *قائمة مشتركين VIP*\n\n"
        keyboard = []
        
        for i, user in enumerate(vip_users[:20], 1):
            remaining = user["vip_until"] - datetime.datetime.now()
            days = remaining.days
            balance = Decimal(str(user.get("vip_balance", 0)))
            
            btn_text = f"{user['user_id']} - {days} يوم - {format_currency(balance)}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"vipuser_{user['user_id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_vip_management")])
        
        message += f"إجمالي المشتركين: {len(vip_users)}\n"
        message += f"عرض: {len(vip_users[:20])} من أصل {len(vip_users)}"
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def handle_admin_withdraw_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle VIP withdrawal."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "💸 *سحب أرباح VIP*\n\n"
            "أرسل معرف المستخدم الذي تريد سحب أرباحه:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_finance")
        )
        context.user_data['admin_action'] = 'withdraw_vip'
        context.user_data['state'] = UserState.WAITING_WITHDRAW_AMOUNT
        
        return UserState.WAITING_WITHDRAW_AMOUNT
    
    @staticmethod
    async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast management."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "📢 *إدارة الإذاعة والاشعارات*\n\n"
            "اختر نوع الإذاعة:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.broadcast_management()
        )
    
    @staticmethod
    async def handle_admin_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text broadcast."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        await query.edit_message_text(
            "📢 *إذاعة نصية*\n\n"
            "أرسل النص الذي تريد إذاعته:\n\n"
            "يمكنك استخدام تنسيق Markdown",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.back_button("admin_broadcast")
        )
        context.user_data['admin_action'] = 'broadcast_text'
        context.user_data['state'] = UserState.WAITING_BROADCAST
        
        return UserState.WAITING_BROADCAST

# ==================== Main Bot Handlers ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    
    # Check maintenance mode
    if await SettingsManager.get("maintenance_mode", False):
        maintenance_msg = await SettingsManager.get("maintenance_message", "البوت تحت الصيانة حالياً")
        await update.message.reply_text(f"🔧 {maintenance_msg}")
        return
    
    # Get or create user
    user_data = await get_user(user_id)
    
    # Check if banned
    if user_data.get("banned"):
        ban_reason = user_data.get("ban_reason", "لم يتم تحديد سبب")
        ban_until = user_data.get("ban_until")
        
        if ban_until and ban_until > datetime.datetime.now():
            remaining = ban_until - datetime.datetime.now()
            message = f"❌ *تم حظرك من استخدام البوت*\n\nالسبب: {ban_reason}\nالمتبقي: {remaining.days} يوم"
        else:
            message = f"❌ *تم حظرك من استخدام البوت*\n\nالسبب: {ban_reason}"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Check for invite code
    if context.args:
        invite_code = context.args[0]
        await handle_invite(user_id, invite_code)
    
    # Send welcome message
    welcome_msg = MessageBuilder.welcome_message(user)
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = f"""
    🆘 *مساعدة - بوت يلا نتعلم*
    
    *الخدمات المتاحة:*
    📊 حساب درجة الاعفاء
    📚 تلخيص الملازم (PDF)
    ❓ سؤال وجواب بالذكاء الاصطناعي
    🆘 ساعدوني طالب
    📖 ملازم ومرشحات
    ⭐ محاضرات VIP
    
    *💰 النظام المالي:*
    • العملة: الدينار العراقي
    • كل خدمة مدفوعة
    • شحن الرصيد: @{SUPPORT_USERNAME.replace('@', '')}
    • دعوة الأصدقاء: مكافأة لكل صديق
    
    *📞 الدعم الفني:*
    @{SUPPORT_USERNAME.replace('@', '')}
    
    *📢 قناة البوت:*
    @{CHANNEL_USERNAME.replace('@', '')}
    
    *🔄 الأوامر:*
    /start - إعادة تشغيل البوت
    /help - هذه الرسالة
    /balance - عرض الرصيد
    /invite - رابط الدعوة
    /cancel - إلغاء العملية الحالية
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if user_data.get("banned"):
        await update.message.reply_text("❌ تم حظرك من استخدام البوت.")
        return
    
    balance_msg = MessageBuilder.balance_message(user_data)
    
    await update.message.reply_text(
        balance_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /invite command."""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if user_data.get("banned"):
        await update.message.reply_text("❌ تم حظرك من استخدام البوت.")
        return
    
    invite_reward = Decimal(await SettingsManager.get("invite_reward", 500))
    invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_data['invite_code']}"
    
    # Special message for VIP users
    if user_data.get("vip_until") and user_data["vip_until"] > datetime.datetime.now():
        description = "🎓 انضم لأفضل بوت تعليمي مع محاضرات VIP حصرية وتلخيص ذكي للملازم!"
    else:
        description = "🎓 انضم لأفضل بوت تعليمي واحصل على هدية 1000 دينار مجاناً!"
    
    invite_text = f"""
    👥 *دعوة صديق*
    
    {description}
    
    *مكافأة الدعوة:* {format_currency(invite_reward)} لكل صديق
    *مدعووك حتى الآن:* {user_data.get('invited_count', 0)}
    
    *رابط الدعوة الخاص بك:*
    `{invite_link}`
    
    *طريقة المشاركة:*
    1. شارك الرابط مع أصدقائك
    2. عندما ينضم صديق يحصل على 1000 دينار هدية
    3. تحصل أنت على {format_currency(invite_reward)} دينار مكافأة
    4. يمكن لصديقك دعوة أصدقاء آخرين
    
    *ملاحظة:* المكافأة تمنح بعد تفعيل الصديق للبوت واستخدامه
    """
    
    keyboard = [
        [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={invite_link}&text={description}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(
        invite_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    user_id = update.effective_user.id
    
    # Clear user state
    if 'state' in context.user_data:
        context.user_data.clear()
    
    await update.message.reply_text(
        "✅ تم إلغاء العملية الحالية.",
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )
    
    return ConversationHandler.END

async def handle_invite(user_id: int, invite_code: str):
    """Handle invite code when user joins."""
    # Get inviter
    inviter = users_col.find_one({"invite_code": invite_code})
    
    if not inviter or inviter["user_id"] == user_id:
        return
    
    # Check if already invited
    existing_invite = invites_col.find_one({"invitee_id": user_id})
    if existing_invite:
        return
    
    # Record invite
    invites_col.insert_one({
        "inviter_id": inviter["user_id"],
        "invitee_id": user_id,
        "invite_code": invite_code,
        "created_at": datetime.datetime.now(),
        "rewarded": False
    })
    
    # Update inviter's invited count
    users_col.update_one(
        {"user_id": inviter["user_id"]},
        {"$inc": {"invited_count": 1}}
    )
    
    # Reward inviter after invitee completes first transaction or after 24 hours
    # For now, we'll reward immediately
    invite_reward = Decimal(await SettingsManager.get("invite_reward", 500))
    
    await create_transaction(
        inviter["user_id"],
        TransactionType.INVITE_REWARD,
        invite_reward,
        f"مكافأة دعوة للمستخدم {user_id}"
    )
    
    # Mark as rewarded
    invites_col.update_one(
        {"invitee_id": user_id},
        {"$set": {"rewarded": True, "rewarded_at": datetime.datetime.now()}}
    )
    
    # Notify inviter
    try:
        # We'll send notification in background
        pass
    except:
        pass

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Check maintenance mode
    if await SettingsManager.get("maintenance_mode", False) and data != "main_menu" and user_id != ADMIN_ID:
        maintenance_msg = await SettingsManager.get("maintenance_message", "البوت تحت الصيانة حالياً")
        await query.edit_message_text(f"🔧 {maintenance_msg}")
        return
    
    # Check if user is banned
    user_data = await get_user(user_id)
    if user_data.get("banned") and data != "main_menu" and user_id != ADMIN_ID:
        await query.edit_message_text("❌ تم حظرك من استخدام البوت.")
        return
    
    # Main menu
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *القائمة الرئيسية*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
    
    # Service callbacks
    elif data == "service_exemption":
        return await ServiceHandler.handle_exemption(update, context)
    elif data == "service_summary":
        return await ServiceHandler.handle_summary(update, context)
    elif data == "service_qa":
        return await ServiceHandler.handle_qa(update, context)
    elif data == "service_help":
        return await ServiceHandler.handle_help(update, context)
    elif data == "materials":
        await handle_materials(update, context)
    elif data == "vip_subscribe":
        await handle_vip_subscribe(update, context)
    elif data == "vip_lectures":
        await handle_vip_lectures(update, context)
    elif data == "balance":
        await handle_balance_callback(update, context)
    elif data == "invite":
        await handle_invite_callback(update, context)
    
    # Admin callbacks
    elif data == "admin_panel":
        await AdminHandler.handle_admin_panel(update, context)
    elif data == "admin_stats":
        await AdminHandler.handle_admin_stats(update, context)
    elif data == "admin_users":
        await AdminHandler.handle_admin_users(update, context)
    elif data == "admin_finance":
        await AdminHandler.handle_admin_finance(update, context)
    elif data == "admin_charge":
        return await AdminHandler.handle_admin_charge(update, context)
    elif data == "admin_deduct":
        return await AdminHandler.handle_admin_deduct(update, context)
    elif data == "admin_ban_management":
        await AdminHandler.handle_admin_ban_management(update, context)
    elif data == "admin_ban":
        return await AdminHandler.handle_admin_ban(update, context)
    elif data == "admin_unban":
        return await AdminHandler.handle_admin_unban(update, context)
    elif data == "admin_services":
        await AdminHandler.handle_admin_services(update, context)
    elif data.startswith("toggle_"):
        await AdminHandler.handle_toggle_service(update, context)
    elif data == "admin_prices":
        await AdminHandler.handle_admin_prices(update, context)
    elif data == "price_service":
        return await AdminHandler.handle_price_service(update, context)
    elif data == "price_vip":
        return await AdminHandler.handle_price_vip(update, context)
    elif data == "price_invite":
        return await AdminHandler.handle_price_invite(update, context)
    elif data == "admin_vip_management":
        await AdminHandler.handle_admin_vip_management(update, context)
    elif data == "admin_vip_users":
        await AdminHandler.handle_admin_vip_users(update, context)
    elif data == "admin_withdraw_vip":
        return await AdminHandler.handle_admin_withdraw_vip(update, context)
    elif data == "admin_broadcast":
        await AdminHandler.handle_admin_broadcast(update, context)
    elif data == "admin_broadcast_text":
        return await AdminHandler.handle_admin_broadcast_text(update, context)
    
    # Other admin sections (simplified for now)
    elif data in ["admin_lectures", "admin_materials", "admin_advanced", 
                  "admin_reports", "admin_maintenance", "admin_users_list",
                  "admin_search_user", "admin_filter_users", "admin_export_users",
                  "admin_import_users", "admin_user_details", "admin_freeze_account",
                  "admin_warn", "admin_banned_list", "admin_temp_ban",
                  "admin_transactions", "admin_invoices", "admin_coupons",
                  "admin_vip_stats", "admin_vip_renew", "admin_vip_cancel",
                  "admin_withdrawal_requests", "admin_vip_balances",
                  "admin_pending_lectures", "admin_approved_lectures",
                  "admin_rejected_lectures", "admin_lecture_stats",
                  "admin_lecture_ratings", "admin_bad_lectures",
                  "admin_broadcast_photo", "admin_broadcast_video",
                  "admin_broadcast_document", "admin_broadcast_targeted",
                  "admin_broadcast_scheduled", "admin_broadcast_history",
                  "admin_add_material", "admin_list_materials",
                  "admin_edit_material", "admin_delete_material",
                  "admin_material_stats", "admin_system_settings",
                  "admin_security_settings", "admin_notification_settings",
                  "admin_ui_settings", "admin_language_settings",
                  "admin_currency_settings", "admin_time_settings",
                  "admin_performance_settings", "admin_sales_report",
                  "admin_users_report", "admin_vip_report", "admin_services_report",
                  "admin_transactions_report", "admin_activity_analysis",
                  "admin_time_report", "admin_toggle_maintenance",
                  "admin_backup", "admin_restore", "admin_cleanup",
                  "admin_system_status", "admin_error_logs", "admin_activity_logs",
                  "admin_update_system", "price_min_withdraw",
                  "price_teacher_commission"]:
        
        if user_id != ADMIN_ID:
            await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
            return
        
        # Simplified response for other admin sections
        await query.edit_message_text(
            f"🔧 *قسم تحت التطوير*\n\n"
            f"هذا القسم ({data}) قيد التطوير وسيكون متاحاً قريباً.\n\n"
            f"يمكنك استخدام الأقسام الأساسية المتاحة حالياً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
    
    # VIP user details
    elif data.startswith("vipuser_"):
        target_user_id = int(data.replace("vipuser_", ""))
        await handle_vip_user_details(update, context, target_user_id)
    
    # Confirm actions
    elif data in ["confirm_action", "yes_action", "no_action"]:
        await handle_confirm_action(update, context, data)

async def handle_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle materials callback."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not await SettingsManager.get("materials_enabled", True):
        await query.edit_message_text("❌ قسم المواد التعليمية معطل حالياً.")
        return
    
    materials = list(materials_col.find({"status": "active"}).sort("created_at", DESCENDING).limit(50))
    
    if not materials:
        await query.edit_message_text(
            "📭 لا توجد مواد تعليمية حالياً.\n\n"
            "سيتم إضافة مواد قريباً من قبل الإدارة.",
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        return
    
    message = "📖 *المواد التعليمية المتاحة*\n\n"
    keyboard = []
    
    for material in materials[:10]:  # Show first 10
        name = material.get("name", "بدون اسم")
        stage = material.get("stage", "غير محدد")
        btn_text = f"{name} ({stage})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"material_{material['_id']}")])
    
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    
    message += f"إجمالي المواد: {len(materials)}\n"
    message += f"عرض: {len(materials[:10])} من أصل {len(materials)}"
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_vip_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP subscription."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await get_user(user_id)
    
    if not await SettingsManager.get("vip_enabled", True):
        await query.edit_message_text("❌ خدمة VIP معطلة حالياً.")
        return
    
    # Check if already VIP
    if user_data.get("vip_until") and user_data["vip_until"] > datetime.datetime.now():
        remaining = user_data["vip_until"] - datetime.datetime.now()
        await query.edit_message_text(
            f"⭐ أنت مشترك VIP بالفعل!\n\n"
            f"المتبقي: {remaining.days} يوم\n"
            f"رصيد الأرباح: {format_currency(Decimal(str(user_data.get('vip_balance', 0))))}",
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        return
    
    vip_info = MessageBuilder.vip_subscription_info()
    
    keyboard = [
        [InlineKeyboardButton("💳 اشترك الآن", callback_data="confirm_vip_purchase")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        vip_info,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_vip_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP lectures."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await get_user(user_id)
    
    # Check VIP status
    if not user_data.get("vip_until") or user_data["vip_until"] < datetime.datetime.now():
        await query.edit_message_text(
            "❌ هذه الخدمة للمشتركين في VIP فقط.\n\n"
            "اشترك من زر ⭐ اشتراك VIP في القائمة الرئيسية",
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        return
    
    lectures = list(vip_lectures_col.find({
        "status": "approved",
        "user_id": {"$ne": user_id}  # Don't show user's own lectures
    }).sort("created_at", DESCENDING).limit(50))
    
    if not lectures:
        await query.edit_message_text(
            "📭 لا توجد محاضرات VIP حالياً.\n\n"
            "كن أول من يضيف محاضرة من خلال زر 'رفع محاضرة'",
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        return
    
    message = "🎓 *محاضرات VIP المتاحة*\n\n"
    keyboard = []
    
    for lecture in lectures[:10]:
        title = lecture.get("title", "بدون عنوان")
        price = Decimal(str(lecture.get("price", 0)))
        teacher_id = lecture.get("user_id")
        
        # Get teacher info
        teacher = await get_user(teacher_id)
        teacher_name = teacher.get("first_name", "مدرس")
        
        price_text = "مجاني" if price == 0 else f"{format_currency(price)}"
        btn_text = f"{title[:30]} ({price_text}) - {teacher_name}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"lecture_{lecture['_id']}")])
    
    # Add button for uploading lectures
    keyboard.append([InlineKeyboardButton("📤 رفع محاضرة جديدة", callback_data="upload_lecture")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    
    message += f"إجمالي المحاضرات: {len(lectures)}\n"
    message += f"عرض: {len(lectures[:10])} من أصل {len(lectures)}"
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance callback."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await get_user(user_id)
    
    balance_msg = MessageBuilder.balance_message(user_data)
    
    await query.edit_message_text(
        balance_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )

async def handle_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle invite callback."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await get_user(user_id)
    
    invite_reward = Decimal(await SettingsManager.get("invite_reward", 500))
    invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_data['invite_code']}"
    
    if user_data.get("vip_until") and user_data["vip_until"] > datetime.datetime.now():
        description = "🎓 انضم لأفضل بوت تعليمي مع محاضرات VIP حصرية!"
    else:
        description = "🎓 انضم لأفضل بوت تعليمي واحصل على هدية مجانية!"
    
    invite_text = f"""
    👥 *دعوة صديق*
    
    {description}
    
    *مكافأة الدعوة:* {format_currency(invite_reward)} دينار لكل صديق
    
    *رابط الدعوة الخاص بك:*
    `{invite_link}`
    
    *عدد المدعوين:* {user_data.get('invited_count', 0)}
    *إجمالي المكافآت:* {format_currency(Decimal(str(user_data.get('total_earned', 0))))}
    """
    
    keyboard = [
        [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={invite_link}&text={description}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        invite_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_vip_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    """Handle VIP user details."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("❌ ليس لديك صلاحية الوصول!", show_alert=True)
        return
    
    target_user = await get_user(target_user_id)
    if not target_user:
        await query.edit_message_text(
            "❌ المستخدم غير موجود.",
            reply_markup=KeyboardBuilder.back_button("admin_vip_users")
        )
        return
    
    # Get VIP lectures
    lectures = list(vip_lectures_col.find({"user_id": target_user_id}))
    
    message = f"""
    👤 *تفاصيل مشترك VIP*
    
    *المستخدم:* {target_user_id}
    *الاسم:* {target_user.get('first_name', '')} {target_user.get('last_name', '')}
    *اسم المستخدم:* @{target_user.get('username', 'غير متوفر')}
    
    *معلومات الاشتراك:*
    • تاريخ الانتهاء: {format_date(target_user['vip_until']) if target_user.get('vip_until') else 'غير مشترك'}
    • رصيد الأرباح: {format_currency(Decimal(str(target_user.get('vip_balance', 0))))}
    • عدد المحاضرات: {len(lectures)}
    
    *الإحصائيات:*
    • إجمالي الإنفاق: {format_currency(Decimal(str(target_user.get('total_spent', 0))))}
    • إجمالي الأرباح: {format_currency(Decimal(str(target_user.get('total_earned', 0))))}
    • عدد الدعوات: {target_user.get('invited_count', 0)}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 تجديد شهر", callback_data=f"renew_vip_{target_user_id}"),
            InlineKeyboardButton("❌ إلغاء الاشتراك", callback_data=f"cancel_vip_{target_user_id}")
        ],
        [
            InlineKeyboardButton("💸 سحب أرباح", callback_data=f"withdraw_vip_{target_user_id}"),
            InlineKeyboardButton("📊 محاضراته", callback_data=f"user_lectures_{target_user_id}")
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_vip_users")]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Handle confirm actions."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if action == "confirm_action":
        # Handle based on context
        if 'pending_action' in context.user_data:
            action_type = context.user_data['pending_action']
            
            if action_type == 'vip_purchase':
                await confirm_vip_purchase(update, context)
            elif action_type == 'lecture_upload':
                await start_lecture_upload(update, context)
        
    elif action == "yes_action":
        # Handle yes action
        pass
    elif action == "no_action":
        # Handle no action - go back
        await query.edit_message_text(
            "❌ تم إلغاء الإجراء.",
            reply_markup=KeyboardBuilder.admin_panel()
        )
    
    # Clear pending action
    if 'pending_action' in context.user_data:
        del context.user_data['pending_action']

async def confirm_vip_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm VIP purchase."""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = await get_user(user_id)
    
    vip_price = Decimal(await SettingsManager.get("vip_subscription_price", 5000))
    balance = Decimal(str(user_data.get("balance", 0)))
    
    if balance < vip_price:
        await query.edit_message_text(
            f"❌ رصيدك غير كافي!\n\n"
            f"💰 سعر الاشتراك: {format_currency(vip_price)}\n"
            f"💵 رصيدك الحالي: {format_currency(balance)}\n\n"
            f"لشحن الرصيد تواصل مع: @{SUPPORT_USERNAME.replace('@', '')}",
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        return
    
    # Deduct balance
    new_balance = balance - vip_price
    await update_user(user_id, {"balance": new_balance})
    
    # Set VIP expiration (30 days from now)
    vip_until = datetime.datetime.now() + datetime.timedelta(days=30)
    await update_user(user_id, {
        "vip_until": vip_until,
        "vip_balance": Decimal('0.0')
    })
    
    # Record transaction
    await create_transaction(
        user_id,
        TransactionType.VIP_SUBSCRIPTION,
        -vip_price,
        "اشتراك VIP شهري"
    )
    
    # Notify admin
    admin_message = f"""
    ⭐ *اشتراك VIP جديد*
    
    • المستخدم: {user_id}
    • الاسم: {user_data.get('first_name', '')}
    • المبلغ: {format_currency(vip_price)}
    • التاريخ: {format_date(datetime.datetime.now())}
    """
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    await query.edit_message_text(
        f"""
        ✅ *تم الاشتراك في VIP بنجاح!*
        
        ⭐ اشتراكك ساري لمدة 30 يوم
        📅 تاريخ الانتهاء: {format_date(vip_until)}
        💰 رصيدك الجديد: {format_currency(new_balance)}
        
        *يمكنك الآن:*
        📤 رفع محاضرات فيديو
        💸 كسب 60% من أرباح المحاضرات
        📊 متابعة إحصائيات محاضراتك
        
        *لرفع أول محاضرة:* اضغط على زر "رفع محاضرة" في قسم محاضرات VIP
        """,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )

async def start_lecture_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start lecture upload process."""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.edit_message_text(
        "📤 *رفع محاضرة جديدة*\n\n"
        "أولاً، أرسل عنوان المحاضرة:",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['state'] = UserState.WAITING_VIP_LECTURE_TITLE
    
    return UserState.WAITING_VIP_LECTURE_TITLE

# ==================== Message Handlers ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages."""
    user_id = update.effective_user.id
    message = update.message
    
    # Check maintenance mode
    if await SettingsManager.get("maintenance_mode", False) and user_id != ADMIN_ID:
        maintenance_msg = await SettingsManager.get("maintenance_message", "البوت تحت الصيانة حالياً")
        await message.reply_text(f"🔧 {maintenance_msg}")
        return
    
    # Get user
    user_data = await get_user(user_id)
    
    # Check if banned
    if user_data.get("banned") and user_id != ADMIN_ID:
        await message.reply_text("❌ تم حظرك من استخدام البوت.")
        return
    
    # Check user state
    state = context.user_data.get('state')
    
    # Handle based on state
    if state == UserState.WAITING_COURSE1:
        await handle_course_score(update, context, 1)
    elif state == UserState.WAITING_COURSE2:
        await handle_course_score(update, context, 2)
    elif state == UserState.WAITING_COURSE3:
        await handle_course_score(update, context, 3)
    elif state == UserState.WAITING_PDF:
        await handle_pdf_upload(update, context)
    elif state == UserState.WAITING_QUESTION:
        await handle_question_input(update, context)
    elif state == UserState.WAITING_CHARGE_USER:
        await handle_admin_charge_user(update, context)
    elif state == UserState.WAITING_CHARGE_AMOUNT:
        await handle_admin_charge_amount(update, context)
    elif state == UserState.WAITING_DEDUCT_USER:
        await handle_admin_deduct_user(update, context)
    elif state == UserState.WAITING_DEDUCT_AMOUNT:
        await handle_admin_deduct_amount(update, context)
    elif state == UserState.WAITING_BAN_USER:
        await handle_admin_ban_user(update, context)
    elif state == UserState.WAITING_UNBAN_USER:
        await handle_admin_unban_user(update, context)
    elif state == UserState.WAITING_BROADCAST:
        await handle_admin_broadcast_text_input(update, context)
    elif state == UserState.WAITING_VIP_PRICE:
        await handle_admin_vip_price_change(update, context)
    elif state == UserState.WAITING_SERVICE_PRICE:
        await handle_admin_service_price_change(update, context)
    elif state == UserState.WAITING_INVITE_REWARD:
        await handle_admin_invite_reward_change(update, context)
    elif state == UserState.WAITING_WITHDRAW_AMOUNT:
        await handle_admin_withdraw_amount(update, context)
    elif state == UserState.WAITING_VIP_LECTURE_TITLE:
        await handle_vip_lecture_title(update, context)
    elif state == UserState.WAITING_VIP_LECTURE_DESC:
        await handle_vip_lecture_desc(update, context)
    elif state == UserState.WAITING_VIP_LECTURE_PRICE:
        await handle_vip_lecture_price(update, context)
    elif state == UserState.WAITING_VIP_LECTURE_VIDEO:
        await handle_vip_lecture_video(update, context)
    else:
        # Default: show main menu
        await message.reply_text(
            "🏠 *القائمة الرئيسية*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )

async def handle_course_score(update: Update, context: ContextTypes.DEFAULT_TYPE, course_num: int):
    """Handle course score input."""
    user_id = update.effective_user.id
    message = update.message
    
    try:
        score = float(message.text)
        if not (0 <= score <= 100):
            raise ValueError
        
        # Store score
        if 'course_scores' not in context.user_data:
            context.user_data['course_scores'] = {}
        context.user_data['course_scores'][f'course{course_num}'] = score
        
        if course_num == 1:
            await message.reply_text("أدخل درجة الكورس الثاني (0-100):")
            context.user_data['state'] = UserState.WAITING_COURSE2
        elif course_num == 2:
            await message.reply_text("أدخل درجة الكورس الثالث (0-100):")
            context.user_data['state'] = UserState.WAITING_COURSE3
        elif course_num == 3:
            # Calculate average
            scores = context.user_data['course_scores']
            avg = (scores['course1'] + scores['course2'] + scores['course3']) / 3
            
            # Deduct payment
            service_price = Decimal(str(context.user_data.get('service_price', 1000)))
            user_data = await get_user(user_id)
            balance = Decimal(str(user_data.get("balance", 0)))
            
            if balance >= service_price:
                new_balance = balance - service_price
                await update_user(user_id, {"balance": new_balance})
                
                await create_transaction(
                    user_id,
                    TransactionType.SERVICE_PAYMENT,
                    -service_price,
                    "خدمة حساب درجة الاعفاء"
                )
                
                if avg >= 90:
                    result_msg = f"""
                    🎉 *مبروك!*
                    
                    • معدلك النهائي: {avg:.2f}
                    • أنت معفي من المادة!
                    
                    💰 تم خصم {format_currency(service_price)}
                    📊 رصيدك الجديد: {format_currency(new_balance)}
                    """
                else:
                    result_msg = f"""
                    📊 *نتيجتك*
                    
                    • معدلك النهائي: {avg:.2f}
                    • للأسف أنت غير معفي من المادة
                    
                    💰 تم خصم {format_currency(service_price)}
                    📊 رصيدك الجديد: {format_currency(new_balance)}
                    """
            else:
                result_msg = f"""
                ❌ *رصيد غير كافي*
                
                • المعدل المحسوب: {avg:.2f}
                • الرصيد المطلوب: {format_currency(service_price)}
                • رصيدك الحالي: {format_currency(balance)}
                
                لشحن الرصيد: @{SUPPORT_USERNAME.replace('@', '')}
                """
            
            await message.reply_text(
                result_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=KeyboardBuilder.main_menu(user_id)
            )
            
            # Clear state
            context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إدخال درجة صحيحة بين 0 و 100:")

async def handle_pdf_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF upload for summarization."""
    user_id = update.effective_user.id
    message = update.message
    
    if not message.document:
        await message.reply_text("❌ الرجاء إرسال ملف PDF:")
        return
    
    document = message.document
    if not document.file_name.lower().endswith('.pdf'):
        await message.reply_text("❌ الرجاء إرسال ملف PDF فقط:")
        return
    
    # Check file size (20MB limit)
    max_size = 20 * 1024 * 1024  # 20MB
    if document.file_size > max_size:
        await message.reply_text("❌ حجم الملف يتجاوز 20 ميجابايت!")
        return
    
    await message.reply_text("⏳ جاري تحليل الملف وتلخيصه...")
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Extract text
        text = extract_pdf_text(file_bytes)
        
        if not text or len(text.strip()) < 50:
            await message.reply_text("❌ لا يمكن قراءة النص من الملف أو الملف فارغ.")
            return
        
        # Summarize using AI
        if model:
            prompt = f"""
            قم بتلخيص النص التالي بشكل احترافي مع الحفاظ على المعلومات المهمة:
            
            {text[:3000]}  # Limit text for API
            
            التلخيص يجب أن يكون:
            1. باللغة العربية الفصحى
            2. يحتوي على النقاط الرئيسية فقط
            3. منظم بشكل جيد
            4. مناسب للطلاب
            """
            
            response = model.generate_content(prompt)
            summary = response.text
        else:
            summary = "عذراً، خدمة الذكاء الاصطناعي غير متوفرة حالياً."
        
        # Create PDF with summary
        summary_pdf = create_summary_pdf(summary, document.file_name)
        
        # Deduct payment
        service_price = Decimal(str(context.user_data.get('service_price', 1000)))
        user_data = await get_user(user_id)
        balance = Decimal(str(user_data.get("balance", 0)))
        
        if balance >= service_price:
            new_balance = balance - service_price
            await update_user(user_id, {"balance": new_balance})
            
            await create_transaction(
                user_id,
                TransactionType.SERVICE_PAYMENT,
                -service_price,
                "خدمة تلخيص الملازم"
            )
            
            # Send summarized PDF
            await message.reply_document(
                document=InputFile(summary_pdf, filename=f"ملخص_{document.file_name}"),
                caption=f"""
                ✅ *تم تلخيص الملف بنجاح!*
                
                📄 الملف الأصلي: {document.file_name}
                📝 التلخيص: {len(summary)} حرف
                
                💰 تم خصم {format_currency(service_price)}
                📊 رصيدك الجديد: {format_currency(new_balance)}
                """,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(
                f"""
                ❌ *رصيد غير كافي*
                
                📄 الملف: {document.file_name}
                💰 الرصيد المطلوب: {format_currency(service_price)}
                📊 رصيدك الحالي: {format_currency(balance)}
                
                لشحن الرصيد: @{SUPPORT_USERNAME.replace('@', '')}
                """,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Clear state
        context.user_data.clear()
        
        # Show main menu
        await message.reply_text(
            "🏠 *القائمة الرئيسية*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"PDF summarization error: {e}")
        await message.reply_text("❌ حدث خطأ في معالجة الملف. يرجى المحاولة لاحقاً.")
        
        # Clear state
        context.user_data.clear()

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        with io.BytesIO(pdf_bytes) as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        logger.error(f"PDF text extraction error: {e}")
        return ""

def create_summary_pdf(summary: str, original_filename: str) -> io.BytesIO:
    """Create PDF with summarized text."""
    buffer = io.BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Arabic style
    arabic_style = ParagraphStyle(
        'Arabic',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=12,
        alignment=TA_RIGHT,
        spaceAfter=12
    )
    
    # Title style
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName=DEFAULT_FONT,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=24
    )
    
    # Build content
    content = []
    
    # Title
    title = Paragraph(f"ملخص: {original_filename}", title_style)
    content.append(title)
    
    # Date
    date_text = f"تاريخ التلخيص: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M')}"
    date_para = Paragraph(date_text, arabic_style)
    content.append(date_para)
    
    # Separator
    content.append(Spacer(1, 20))
    
    # Summary
    summary_para = Paragraph(summary, arabic_style)
    content.append(summary_para)
    
    # Footer
    content.append(Spacer(1, 40))
    footer_text = "تم التلخيص بواسطة بوت يلا نتعلم - @FC4Xbot"
    footer_para = Paragraph(footer_text, arabic_style)
    content.append(footer_para)
    
    # Build PDF
    doc.build(content)
    
    buffer.seek(0)
    return buffer

async def handle_question_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle question input for Q&A or help service."""
    user_id = update.effective_user.id
    message = update.message
    service_type = context.user_data.get('service_type')
    
    question_text = ""
    
    if message.text:
        question_text = message.text
    elif message.caption:
        question_text = message.caption
    elif message.photo:
        # For image questions
        question_text = "سؤال مصور"
    
    if service_type == 'qa':
        # AI Q&A service
        await message.reply_text("⏳ جاري البحث عن الإجابة...")
        
        try:
            if model:
                prompt = f"""
                أجب على السؤال التالي بشكل علمي ومنهجي مناسب للمناهج العراقية:
                
                {question_text}
                
                المتطلبات:
                1. الإجابة باللغة العربية الفصحى
                2. ذكر المصادر إذا أمكن
                3. التوضيح بالأمثلة إذا لزم الأمر
                4. الإجابة مفصلة ووافية
                """
                
                response = model.generate_content(prompt)
                answer = response.text
            else:
                answer = "عذراً، خدمة الذكاء الاصطناعي غير متوفرة حالياً."
            
            # Deduct payment
            service_price = Decimal(str(context.user_data.get('service_price', 1000)))
            user_data = await get_user(user_id)
            balance = Decimal(str(user_data.get("balance", 0)))
            
            if balance >= service_price:
                new_balance = balance - service_price
                await update_user(user_id, {"balance": new_balance})
                
                await create_transaction(
                    user_id,
                    TransactionType.SERVICE_PAYMENT,
                    -service_price,
                    "خدمة سؤال وجواب"
                )
                
                await message.reply_text(
                    f"""
                    🤖 *الإجابة:*
                    
                    {answer}
                    
                    ---
                    💰 تم خصم {format_currency(service_price)}
                    📊 رصيدك الجديد: {format_currency(new_balance)}
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await message.reply_text(
                    f"""
                    ❌ *رصيد غير كافي*
                    
                    💰 الرصيد المطلوب: {format_currency(service_price)}
                    📊 رصيدك الحالي: {format_currency(balance)}
                    
                    لشحن الرصيد: @{SUPPORT_USERNAME.replace('@', '')}
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"AI Q&A error: {e}")
            await message.reply_text("❌ حدث خطأ في معالجة سؤالك. يرجى المحاولة لاحقاً.")
    
    elif service_type == 'help':
        # Help service - store question for admin approval
        question_data = {
            "user_id": user_id,
            "question": question_text,
            "type": "text",
            "status": "pending",
            "created_at": datetime.datetime.now(),
            "message_id": message.message_id
        }
        
        # If there's a photo, save file_id
        if message.photo:
            question_data["type"] = "photo"
            question_data["file_id"] = message.photo[-1].file_id
        
        questions_col.insert_one(question_data)
        
        # Notify admin
        admin_message = f"""
        🆘 *سؤال جديد يحتاج موافقة*
        
        • المستخدم: {user_id}
        • النوع: {"صورة" if message.photo else "نص"}
        • السؤال: {question_text[:200]}...
        
        • الوقت: {format_date(datetime.datetime.now())}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ الموافقة", callback_data=f"approve_question_{user_id}_{message.message_id}"),
                InlineKeyboardButton("❌ الرفض", callback_data=f"reject_question_{user_id}_{message.message_id}")
            ]
        ]
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
        
        await message.reply_text(
            """
            ✅ *تم إرسال سؤالك بنجاح*
            
            سيتم:
            1. مراجعة سؤالك من الإدارة
            2. الموافقة أو الرفض خلال 24 ساعة
            3. عرضه في قسم المساعدة للإجابة عليه
            
            ستتلقى إشعاراً عند الرد على سؤالك.
            """,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Clear state
    context.user_data.clear()
    
    # Show main menu
    await message.reply_text(
        "🏠 *القائمة الرئيسية*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )

async def handle_admin_charge_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin charge - get user ID."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        target_user_id = int(message.text)
        target_user = await get_user(target_user_id, create_if_missing=False)
        
        if not target_user:
            await message.reply_text("❌ المستخدم غير موجود!")
            return
        
        context.user_data['charge_user_id'] = target_user_id
        context.user_data['state'] = UserState.WAITING_CHARGE_AMOUNT
        
        await message.reply_text(
            f"👤 المستخدم: {target_user_id}\n\n"
            f"أرسل المبلغ المراد شحنه (بالدينار العراقي):",
            reply_markup=KeyboardBuilder.back_button("admin_finance")
        )
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح:")

async def handle_admin_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin charge - get amount."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        amount = Decimal(message.text)
        if amount <= 0:
            raise ValueError
        
        target_user_id = context.user_data.get('charge_user_id')
        
        if not target_user_id:
            await message.reply_text("❌ حدث خطأ في العملية!")
            return
        
        # Charge user
        target_user = await get_user(target_user_id)
        current_balance = Decimal(str(target_user.get("balance", 0)))
        new_balance = current_balance + amount
        
        await update_user(target_user_id, {"balance": new_balance})
        
        await create_transaction(
            target_user_id,
            TransactionType.ADMIN_CHARGE,
            amount,
            f"شحن من المدير {user_id}"
        )
        
        # Notify target user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
                💰 *تم شحن رصيدك*
                
                • المبلغ: {format_currency(amount)}
                • الرصيد السابق: {format_currency(current_balance)}
                • الرصيد الجديد: {format_currency(new_balance)}
                • التاريخ: {format_date(datetime.datetime.now())}
                
                🔧 العملية: شحن من الإدارة
                """
            )
        except:
            pass
        
        await message.reply_text(
            f"""
            ✅ *تم شحن الرصيد بنجاح*
            
            • المستخدم: {target_user_id}
            • المبلغ: {format_currency(amount)}
            • الرصيد الجديد: {format_currency(new_balance)}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except (ValueError, InvalidOperation):
        await message.reply_text("❌ الرجاء إرسال مبلغ صحيح أكبر من صفر:")

async def handle_admin_deduct_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin deduct - get user ID."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        target_user_id = int(message.text)
        target_user = await get_user(target_user_id, create_if_missing=False)
        
        if not target_user:
            await message.reply_text("❌ المستخدم غير موجود!")
            return
        
        context.user_data['deduct_user_id'] = target_user_id
        context.user_data['state'] = UserState.WAITING_DEDUCT_AMOUNT
        
        current_balance = Decimal(str(target_user.get("balance", 0)))
        
        await message.reply_text(
            f"👤 المستخدم: {target_user_id}\n"
            f"💰 الرصيد الحالي: {format_currency(current_balance)}\n\n"
            f"أرسل المبلغ المراد خصمه (بالدينار العراقي):",
            reply_markup=KeyboardBuilder.back_button("admin_finance")
        )
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح:")

async def handle_admin_deduct_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin deduct - get amount."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        amount = Decimal(message.text)
        if amount <= 0:
            raise ValueError
        
        target_user_id = context.user_data.get('deduct_user_id')
        
        if not target_user_id:
            await message.reply_text("❌ حدث خطأ في العملية!")
            return
        
        # Check if user has enough balance
        target_user = await get_user(target_user_id)
        current_balance = Decimal(str(target_user.get("balance", 0)))
        
        if current_balance < amount:
            await message.reply_text(
                f"❌ رصيد المستخدم غير كافي!\n"
                f"💰 الرصيد الحالي: {format_currency(current_balance)}\n"
                f"💸 المبلغ المطلوب: {format_currency(amount)}",
                reply_markup=KeyboardBuilder.admin_panel()
            )
            context.user_data.clear()
            return
        
        new_balance = current_balance - amount
        
        await update_user(target_user_id, {"balance": new_balance})
        
        await create_transaction(
            target_user_id,
            TransactionType.ADMIN_DEDUCT,
            -amount,
            f"خصم من المدير {user_id}"
        )
        
        # Notify target user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
                💸 *تم خصم من رصيدك*
                
                • المبلغ: {format_currency(amount)}
                • الرصيد السابق: {format_currency(current_balance)}
                • الرصيد الجديد: {format_currency(new_balance)}
                • التاريخ: {format_date(datetime.datetime.now())}
                • السبب: خصم من الإدارة
                """
            )
        except:
            pass
        
        await message.reply_text(
            f"""
            ✅ *تم خصم الرصيد بنجاح*
            
            • المستخدم: {target_user_id}
            • المبلغ: {format_currency(amount)}
            • الرصيد الجديد: {format_currency(new_balance)}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except (ValueError, InvalidOperation):
        await message.reply_text("❌ الرجاء إرسال مبلغ صحيح أكبر من صفر:")

async def handle_admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin ban - get user ID."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        target_user_id = int(message.text)
        target_user = await get_user(target_user_id, create_if_missing=False)
        
        if not target_user:
            await message.reply_text("❌ المستخدم غير موجود!")
            return
        
        if target_user.get("banned"):
            await message.reply_text("⚠️ هذا المستخدم محظور بالفعل!")
            return
        
        # Ban user
        await update_user(target_user_id, {
            "banned": True,
            "ban_reason": "حظر من المدير",
            "ban_until": datetime.datetime.now() + datetime.timedelta(days=30)
        })
        
        # Notify target user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
                🚫 *تم حظر حسابك*
                
                • السبب: حظر من الإدارة
                • المدة: 30 يوم
                • التاريخ: {format_date(datetime.datetime.now())}
                
                للاستئناف: @{SUPPORT_USERNAME.replace('@', '')}
                """
            )
        except:
            pass
        
        await message.reply_text(
            f"""
            ✅ *تم حظر المستخدم بنجاح*
            
            • المستخدم: {target_user_id}
            • المدة: 30 يوم
            • التاريخ: {format_date(datetime.datetime.now())}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح:")

async def handle_admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin unban - get user ID."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        target_user_id = int(message.text)
        target_user = await get_user(target_user_id, create_if_missing=False)
        
        if not target_user:
            await message.reply_text("❌ المستخدم غير موجود!")
            return
        
        if not target_user.get("banned"):
            await message.reply_text("⚠️ هذا المستخدم غير محظور!")
            return
        
        # Unban user
        await update_user(target_user_id, {
            "banned": False,
            "ban_reason": None,
            "ban_until": None
        })
        
        # Notify target user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
                ✅ *تم فك حظر حسابك*
                
                • التاريخ: {format_date(datetime.datetime.now())}
                • يمكنك الآن استخدام البوت بشكل طبيعي
                
                نرحب بعودتك! 🎉
                """
            )
        except:
            pass
        
        await message.reply_text(
            f"""
            ✅ *تم فك حظر المستخدم بنجاح*
            
            • المستخدم: {target_user_id}
            • التاريخ: {format_date(datetime.datetime.now())}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال معرف مستخدم صحيح:")

async def handle_admin_broadcast_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin broadcast text input."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    broadcast_text = message.text
    
    await message.reply_text("⏳ جاري إرسال الإذاعة للمستخدمين...")
    
    # Get all active users (not banned)
    users = users_col.find({"banned": False})
    total_users = users_col.count_documents({"banned": False})
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=broadcast_text,
                parse_mode=ParseMode.MARKDOWN
            )
            success += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
    
    # Save broadcast record
    broadcasts_col.insert_one({
        "admin_id": user_id,
        "text": broadcast_text,
        "total_users": total_users,
        "success": success,
        "failed": failed,
        "created_at": datetime.datetime.now()
    })
    
    await message.reply_text(
        f"""
        📢 *تم إرسال الإذاعة بنجاح*
        
        • إجمالي المستخدمين: {total_users}
        • الناجح: {success}
        • الفاشل: {failed}
        • النسبة: {(success/total_users*100):.1f}%
        
        • التاريخ: {format_date(datetime.datetime.now())}
        """,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.admin_panel()
    )
    
    # Clear state
    context.user_data.clear()

async def handle_admin_vip_price_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP price change."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        new_price = int(message.text)
        if new_price < 1000:
            await message.reply_text("❌ السعر يجب أن يكون 1000 دينار على الأقل!")
            return
        
        old_price = await SettingsManager.get("vip_subscription_price", 5000)
        await SettingsManager.set("vip_subscription_price", new_price)
        
        await message.reply_text(
            f"""
            ✅ *تم تغيير سعر اشتراك VIP*
            
            • السعر القديم: {format_currency(Decimal(old_price))}
            • السعر الجديد: {format_currency(Decimal(new_price))}
            • التاريخ: {format_date(datetime.datetime.now())}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال سعر صحيح:")

async def handle_admin_service_price_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle service price change."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        new_price = int(message.text)
        if new_price < 100:
            await message.reply_text("❌ السعر يجب أن يكون 100 دينار على الأقل!")
            return
        
        old_price = await SettingsManager.get("service_price", 1000)
        await SettingsManager.set("service_price", new_price)
        
        await message.reply_text(
            f"""
            ✅ *تم تغيير سعر الخدمات*
            
            • السعر القديم: {format_currency(Decimal(old_price))}
            • السعر الجديد: {format_currency(Decimal(new_price))}
            • التاريخ: {format_date(datetime.datetime.now())}
            
            *ملاحظة:* هذا السعر يشمل جميع الخدمات الفردية
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال سعر صحيح:")

async def handle_admin_invite_reward_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle invite reward change."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        new_reward = int(message.text)
        if new_reward < 0:
            await message.reply_text("❌ المكافأة يجب أن تكون صفر أو أكثر!")
            return
        
        old_reward = await SettingsManager.get("invite_reward", 500)
        await SettingsManager.set("invite_reward", new_reward)
        
        await message.reply_text(
            f"""
            ✅ *تم تغيير مكافأة الدعوة*
            
            • المكافأة القديمة: {format_currency(Decimal(old_reward))}
            • المكافأة الجديدة: {format_currency(Decimal(new_reward))}
            • التاريخ: {format_date(datetime.datetime.now())}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except ValueError:
        await message.reply_text("❌ الرجاء إرسال مكافأة صحيحة:")

async def handle_admin_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin withdraw VIP earnings."""
    user_id = update.effective_user.id
    message = update.message
    
    if user_id != ADMIN_ID:
        await message.reply_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    try:
        amount = Decimal(message.text)
        if amount <= 0:
            raise ValueError
        
        target_user_id = context.user_data.get('withdraw_user_id')
        
        if not target_user_id:
            await message.reply_text("❌ حدث خطأ في العملية!")
            return
        
        # Check if user has enough VIP balance
        target_user = await get_user(target_user_id)
        current_vip_balance = Decimal(str(target_user.get("vip_balance", 0)))
        
        if current_vip_balance < amount:
            await message.reply_text(
                f"❌ رصيد أرباح VIP غير كافي!\n"
                f"💰 الرصيد الحالي: {format_currency(current_vip_balance)}\n"
                f"💸 المبلغ المطلوب: {format_currency(amount)}",
                reply_markup=KeyboardBuilder.admin_panel()
            )
            context.user_data.clear()
            return
        
        # Withdraw from VIP balance
        new_vip_balance = current_vip_balance - amount
        
        await update_user(target_user_id, {"vip_balance": new_vip_balance})
        
        # Record withdrawal
        withdrawals_col.insert_one({
            "user_id": target_user_id,
            "amount": float(amount),
            "type": "vip_earnings",
            "status": "completed",
            "processed_by": user_id,
            "created_at": datetime.datetime.now()
        })
        
        await create_transaction(
            target_user_id,
            TransactionType.WITHDRAWAL,
            -amount,
            "سحب أرباح VIP من الإدارة"
        )
        
        # Notify target user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
                💸 *تم سحب أرباح VIP*
                
                • المبلغ: {format_currency(amount)}
                • الرصيد السابق: {format_currency(current_vip_balance)}
                • الرصيد الجديد: {format_currency(new_vip_balance)}
                • التاريخ: {format_date(datetime.datetime.now())}
                
                سيتم تحويل المبلغ لك خلال 24 ساعة عمل.
                للاستفسار: @{SUPPORT_USERNAME.replace('@', '')}
                """
            )
        except:
            pass
        
        await message.reply_text(
            f"""
            ✅ *تم سحب الأرباح بنجاح*
            
            • المستخدم: {target_user_id}
            • المبلغ: {format_currency(amount)}
            • الرصيد الجديد: {format_currency(new_vip_balance)}
            • التاريخ: {format_date(datetime.datetime.now())}
            
            *ملاحظة:* يجب التواصل مع المستخدم لتحويل المبلغ.
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=KeyboardBuilder.admin_panel()
        )
        
        # Clear state
        context.user_data.clear()
        
    except (ValueError, InvalidOperation):
        await message.reply_text("❌ الرجاء إرسال مبلغ صحيح أكبر من صفر:")

async def handle_vip_lecture_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP lecture title."""
    user_id = update.effective_user.id
    message = update.message
    
    title = message.text.strip()
    if len(title) < 5:
        await message.reply_text("❌ العنوان قصير جداً! يجب أن يكون 5 أحرف على الأقل:")
        return
    
    if len(title) > 100:
        await message.reply_text("❌ العنوان طويل جداً! يجب أن يكون 100 حرف كحد أقصى:")
        return
    
    context.user_data['lecture_title'] = title
    context.user_data['state'] = UserState.WAITING_VIP_LECTURE_DESC
    
    await message.reply_text(
        "📝 *الخطوة 2/4*\n\n"
        "أرسل وصف المحاضرة:\n\n"
        "• يجب أن يكون الوصف واضحاً\n"
        "• اذكر المحتوى الرئيسي\n"
        "• المدة الموصى بها: 50-200 حرف",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_vip_lecture_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP lecture description."""
    user_id = update.effective_user.id
    message = update.message
    
    description = message.text.strip()
    if len(description) < 20:
        await message.reply_text("❌ الوصف قصير جداً! يجب أن يكون 20 حرف على الأقل:")
        return
    
    if len(description) > 500:
        await message.reply_text("❌ الوصف طويل جداً! يجب أن يكون 500 حرف كحد أقصى:")
        return
    
    context.user_data['lecture_desc'] = description
    context.user_data['state'] = UserState.WAITING_VIP_LECTURE_PRICE
    
    await message.reply_text(
        "💰 *الخطوة 3/4*\n\n"
        "أرسل سعر المحاضرة (بالدينار العراقي):\n\n"
        "• يمكنك إرسال 0 للمحاضرات المجانية\n"
        "• الحد الأدنى: 0 دينار\n"
        "• الحد الأقصى: 100,000 دينار\n"
        "• تذكر: 60% من السعر يكون لك\n\n"
        "أرسل السعر الآن:",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_vip_lecture_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP lecture price."""
    user_id = update.effective_user.id
    message = update.message
    
    try:
        price = Decimal(message.text)
        if price < 0:
            await message.reply_text("❌ السعر لا يمكن أن يكون سلبياً!")
            return
        
        if price > 100000:
            await message.reply_text("❌ السعر يتجاوز الحد الأقصى (100,000 دينار)!")
            return
        
        context.user_data['lecture_price'] = price
        context.user_data['state'] = UserState.WAITING_VIP_LECTURE_VIDEO
        
        price_text = "مجانية" if price == 0 else f"{format_currency(price)}"
        earnings = price * Decimal('0.6') if price > 0 else Decimal('0')
        
        await message.reply_text(
            f"🎥 *الخطوة 4/4*\n\n"
            f"*معلومات المحاضرة:*\n"
            f"• العنوان: {context.user_data['lecture_title']}\n"
            f"• السعر: {price_text}\n"
            f"• أرباحك: {format_currency(earnings)}\n\n"
            f"*الآن أرسل فيديو المحاضرة:*\n"
            f"• الحد الأقصى: 100 ميجابايت\n"
            f"• الصيغ المدعومة: MP4, AVI, MOV\n"
            f"• المدة الموصى بها: 5-30 دقيقة\n\n"
            f"ملاحظة: ستتم مراجعة المحاضرة من الإدارة قبل النشر.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except (ValueError, InvalidOperation):
        await message.reply_text("❌ الرجاء إرسال سعر صحيح:")

async def handle_vip_lecture_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle VIP lecture video upload."""
    user_id = update.effective_user.id
    message = update.message
    
    if not message.video:
        await message.reply_text("❌ الرجاء إرسال ملف فيديو!")
        return
    
    video = message.video
    max_size = 100 * 1024 * 1024  # 100MB
    
    if video.file_size > max_size:
        await message.reply_text("❌ حجم الفيديو يتجاوز 100 ميجابايت!")
        return
    
    # Save lecture data
    lecture_data = {
        "user_id": user_id,
        "title": context.user_data.get('lecture_title'),
        "description": context.user_data.get('lecture_desc'),
        "price": float(context.user_data.get('lecture_price', 0)),
        "video_file_id": video.file_id,
        "video_duration": video.duration,
        "video_size": video.file_size,
        "status": "pending",
        "created_at": datetime.datetime.now(),
        "views": 0,
        "purchases": 0,
        "revenue": 0.0,
        "rating": 0.0,
        "ratings_count": 0
    }
    
    lecture_id = vip_lectures_col.insert_one(lecture_data).inserted_id
    
    # Notify admin
    admin_message = f"""
    📹 *محاضرة VIP جديدة تحتاج مراجعة*
    
    • المدرس: {user_id}
    • العنوان: {lecture_data['title']}
    • السعر: {format_currency(Decimal(str(lecture_data['price'])))}
    • المدة: {video.duration} ثانية
    • الحجم: {video.file_size // (1024*1024)} ميجابايت
    
    • الوصف: {lecture_data['description'][:200]}...
    
    • التاريخ: {format_date(datetime.datetime.now())}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("✅ الموافقة", callback_data=f"admin_approve_lecture_{lecture_id}"),
            InlineKeyboardButton("❌ الرفض", callback_data=f"admin_reject_lecture_{lecture_id}")
        ],
        [InlineKeyboardButton("👀 معاينة", callback_data=f"admin_preview_lecture_{lecture_id}")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        pass
    
    await message.reply_text(
        f"""
        ✅ *تم رفع المحاضرة بنجاح!*
        
        • العنوان: {lecture_data['title']}
        • السعر: {format_currency(Decimal(str(lecture_data['price'])))}
        • المدة: {video.duration} ثانية
        
        *الخطوات التالية:*
        1. مراجعة المحاضرة من الإدارة
        2. الموافقة أو الرفض خلال 24 ساعة
        3. نشر المحاضرة في قسم VIP
        
        ستتلقى إشعاراً عند مراجعة المحاضرة.
        """,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=KeyboardBuilder.main_menu(user_id)
    )
    
    # Clear state
    context.user_data.clear()

# ==================== Background Tasks ====================
async def check_vip_expiry(context: ContextTypes.DEFAULT_TYPE):
    """Check and notify about VIP expiry."""
    now = datetime.datetime.now()
    
    # Find users whose VIP expires in 3 days or less
    users = users_col.find({
        "vip_until": {
            "$gt": now,
            "$lte": now + datetime.timedelta(days=3)
        }
    })
    
    for user in users:
        user_id = user["user_id"]
        expiry_date = user["vip_until"]
        days_left = (expiry_date - now).days
        
        if days_left > 0:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"""
                    ⏰ *تنبيه بخصوص اشتراك VIP*
                    
                    ينتهي اشتراكك في VIP بعد {days_left} يوم.
                    تاريخ الانتهاء: {format_date(expiry_date)}
                    
                    للتجديد:
                    1. انتقل إلى قسم VIP
                    2. اضغط على زر "اشتراك VIP"
                    3. قم بالدفع لتجديد الاشتراك
                    
                    💰 رصيدك الحالي: {format_currency(Decimal(str(user.get("balance", 0))))}
                    """
                )
            except:
                pass

async def cleanup_old_data(context: ContextTypes.DEFAULT_TYPE):
    """Cleanup old data."""
    # Remove old notifications (older than 30 days)
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
    
    # Clean notifications
    notifications_col.delete_many({
        "created_at": {"$lt": cutoff_date},
        "read": True
    })
    
    # Clean old cache
    cache_col.delete_many({
        "expires_at": {"$lt": datetime.datetime.now()}
    })
    
    # Clean old sessions
    sessions_col.delete_many({
        "expires_at": {"$lt": datetime.datetime.now()}
    })

# ==================== Main Function ====================
def main():
    """Main function to run the bot."""
    # Create application with persistence
    persistence = PicklePersistence(filepath=DATA_DIR / "bot_persistence")
    
    application = ApplicationBuilder() \
        .token(TOKEN) \
        .persistence(persistence) \
        .build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("invite", invite_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Add job queue for background tasks
    job_queue = application.job_queue
    
    if job_queue:
        # Check VIP expiry daily at 10:00 AM
        job_queue.run_daily(
            check_vip_expiry,
            time=datetime.time(hour=10, minute=0, tzinfo=IRAQ_TZ),
            days=(0, 1, 2, 3, 4, 5, 6)
        )
        
        # Cleanup old data daily at 3:00 AM
        job_queue.run_daily(
            cleanup_old_data,
            time=datetime.time(hour=3, minute=0, tzinfo=IRAQ_TZ),
            days=(0, 1, 2, 3, 4, 5, 6)
        )
    
    # Set bot commands
    commands = [
        BotCommand("start", "تشغيل البوت"),
        BotCommand("help", "المساعدة"),
        BotCommand("balance", "عرض الرصيد"),
        BotCommand("invite", "دعوة صديق"),
        BotCommand("cancel", "إلغاء العملية الحالية")
    ]
    
    async def set_commands():
        await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    application.run_polling()

if __name__ == "__main__":
    main()
