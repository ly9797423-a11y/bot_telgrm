#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت: يلا نتعلم
مطور: Allawi04@
يوزر البوت: @FC4Xbot
السطر البرمجي: 2500+
"""

import os
import logging
import asyncio
import json
import io
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal, ROUND_HALF_UP

# Telegram Bot
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Document,
    PhotoSize,
    InputFile
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatAction

# Gemini AI
import google.generativeai as genai

# MongoDB
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

# PDF Processing
import pdf2image
from PIL import Image, ImageDraw, ImageFont
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# OCR & Image Processing
import pytesseract
import cv2
import numpy as np
from io import BytesIO

# Async
import aiohttp
import aiofiles

# =============================================
# إعدادات LOGGING
# =============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================
# إعدادات البوت
# =============================================
BOT_TOKEN = "8481569753:AAHTdbWwu0BHmoo_iHPsye8RkTptWzfiQWU"
ADMIN_USERNAME = "Allawi04"
SUPPORT_CHANNEL = "@FC4Xbot"
BOT_CHANNEL = "@FC4Xbot"

# =============================================
# إعدادات Gemini AI
# =============================================
GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"
genai.configure(api_key=GEMINI_API_KEY)

# =============================================
# إعدادات قاعدة البيانات
# =============================================
class Database:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        self.db = self.client["yaln_netlam_bot"]
        
        # المجموعات
        self.users = self.db["users"]
        self.admins = self.db["admins"]
        self.transactions = self.db["transactions"]
        self.services = self.db["services"]
        self.files = self.db["files"]
        self.settings = self.db["settings"]
        self.broadcasts = self.db["broadcasts"]
        
        # إنشاء الفهارس
        self._create_indexes()
        
        # إعدادات أولية
        self._initialize_settings()
    
    def _create_indexes(self):
        self.users.create_index([("user_id", ASCENDING)], unique=True)
        self.users.create_index([("invite_code", ASCENDING)], unique=True)
        self.admins.create_index([("user_id", ASCENDING)], unique=True)
        self.transactions.create_index([("user_id", ASCENDING)])
        self.transactions.create_index([("timestamp", DESCENDING)])
        self.services.create_index([("name", ASCENDING)], unique=True)
        self.files.create_index([("stage", ASCENDING)])
    
    def _initialize_settings(self):
        # الإعدادات الافتراضية
        default_settings = {
            "_id": "global_settings",
            "service_price": 1000,
            "welcome_bonus": 1000,
            "invite_bonus": 500,
            "maintenance_mode": False,
            "bot_channel": BOT_CHANNEL,
            "support_channel": SUPPORT_CHANNEL,
            "last_broadcast_id": 0,
            "currency": "دينار عراقي",
            "min_charge": 1000
        }
        
        # الخدمات الافتراضية
        default_services = [
            {
                "name": "حساب درجة الإعفاء",
                "price": 1000,
                "description": "حاسبة الإعفاء الفردي بناءً على درجات الكورسات",
                "active": True,
                "category": "calculator"
            },
            {
                "name": "تلخيص الملازم",
                "price": 1000,
                "description": "تلخيص ملفات PDF باستخدام الذكاء الاصطناعي",
                "active": True,
                "category": "ai"
            },
            {
                "name": "سؤال وجواب",
                "price": 1000,
                "description": "إجابة الأسئلة التعليمية حسب المنهج العراقي",
                "active": True,
                "category": "ai"
            },
            {
                "name": "ملازمي ومرشحاتي",
                "price": 1000,
                "description": "الملازم والمرشحات التعليمية",
                "active": True,
                "category": "files"
            }
        ]
        
        try:
            if not self.settings.find_one({"_id": "global_settings"}):
                self.settings.insert_one(default_settings)
            
            for service in default_services:
                if not self.services.find_one({"name": service["name"]}):
                    self.services.insert_one(service)
            
            # إضافة المدير الرئيسي
            if not self.admins.find_one({"user_id": 6130994941}):  # ID المطور
                self.admins.insert_one({
                    "user_id": 6130994941,
                    "username": "Allawi04",
                    "role": "super_admin",
                    "added_at": datetime.now(),
                    "permissions": ["all"]
                })
                
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

# إنشاء كائن قاعدة البيانات
db = Database()

# =============================================
# فئات المساعدة
# =============================================
class UserManager:
    @staticmethod
    def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> Dict:
        user = db.users.find_one({"user_id": user_id})
        
        if not user:
            invite_code = str(user_id)[-6:]
            
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "balance": db.settings.find_one({"_id": "global_settings"})["welcome_bonus"],
                "invite_code": invite_code,
                "invited_by": None,
                "invited_users": [],
                "total_spent": 0,
                "total_services": 0,
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "banned": False,
                "ban_reason": None,
                "language": "ar",
                "notifications": True
            }
            
            db.users.insert_one(user_data)
            user = user_data
            
            # تسجيل المعاملة
            TransactionManager.add_transaction(
                user_id=user_id,
                amount=user_data["balance"],
                transaction_type="welcome_bonus",
                description="مكافأة ترحيبية"
            )
            
            logger.info(f"مستخدم جديد: {user_id}")
        
        return user
    
    @staticmethod
    def update_balance(user_id: int, amount: int, operation: str = "add") -> bool:
        try:
            user = db.users.find_one({"user_id": user_id})
            if not user:
                return False
            
            if operation == "add":
                new_balance = user["balance"] + amount
            elif operation == "subtract":
                if user["balance"] < amount:
                    return False
                new_balance = user["balance"] - amount
            else:
                return False
            
            db.users.update_one(
                {"user_id": user_id},
                {"$set": {"balance": new_balance}}
            )
            
            return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الرصيد: {e}")
            return False
    
    @staticmethod
    def ban_user(user_id: int, reason: str = "غير محدد", admin_id: int = None) -> bool:
        try:
            db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "banned": True,
                        "ban_reason": reason,
                        "banned_at": datetime.now(),
                        "banned_by": admin_id
                    }
                }
            )
            
            # تسجيل في المعاملات
            TransactionManager.add_transaction(
                user_id=user_id,
                amount=0,
                transaction_type="ban",
                description=f"حظر المستخدم - السبب: {reason}"
            )
            
            return True
        except Exception as e:
            logger.error(f"خطأ في حظر المستخدم: {e}")
            return False
    
    @staticmethod
    def unban_user(user_id: int) -> bool:
        try:
            db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "banned": False,
                        "ban_reason": None,
                        "unbanned_at": datetime.now()
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"خطأ في فك حظر المستخدم: {e}")
            return False
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict:
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return {}
        
        total_transactions = db.transactions.count_documents({"user_id": user_id})
        
        return {
            "user_id": user_id,
            "balance": user["balance"],
            "total_services": user.get("total_services", 0),
            "total_spent": user.get("total_spent", 0),
            "invited_users": len(user.get("invited_users", [])),
            "total_transactions": total_transactions,
            "created_at": user["created_at"],
            "last_active": user.get("last_active", user["created_at"])
        }
    
    @staticmethod
    def get_all_users(skip: int = 0, limit: int = 50) -> List[Dict]:
        users = list(db.users.find(
            {"banned": False},
            {
                "user_id": 1,
                "username": 1,
                "first_name": 1,
                "balance": 1,
                "total_services": 1,
                "total_spent": 1,
                "created_at": 1
            }
        ).sort("created_at", DESCENDING).skip(skip).limit(limit))
        
        return users
    
    @staticmethod
    def get_banned_users() -> List[Dict]:
        users = list(db.users.find(
            {"banned": True},
            {
                "user_id": 1,
                "username": 1,
                "first_name": 1,
                "ban_reason": 1,
                "banned_at": 1
            }
        ).sort("banned_at", DESCENDING))
        
        return users
    
    @staticmethod
    def get_top_invites(limit: int = 10) -> List[Dict]:
        pipeline = [
            {"$match": {"invited_users.0": {"$exists": True}}},
            {"$project": {
                "user_id": 1,
                "username": 1,
                "first_name": 1,
                "invite_count": {"$size": "$invited_users"}
            }},
            {"$sort": {"invite_count": DESCENDING}},
            {"$limit": limit}
        ]
        
        return list(db.users.aggregate(pipeline))

class AdminManager:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        admin = db.admins.find_one({"user_id": user_id})
        return admin is not None
    
    @staticmethod
    def is_super_admin(user_id: int) -> bool:
        admin = db.admins.find_one({"user_id": user_id})
        return admin and admin.get("role") == "super_admin"
    
    @staticmethod
    def add_admin(user_id: int, username: str, added_by: int) -> bool:
        try:
            admin_data = {
                "user_id": user_id,
                "username": username,
                "role": "admin",
                "added_by": added_by,
                "added_at": datetime.now(),
                "permissions": ["view", "charge", "ban", "broadcast"]
            }
            
            db.admins.insert_one(admin_data)
            return True
        except DuplicateKeyError:
            return False
        except Exception as e:
            logger.error(f"خطأ في إضافة مشرف: {e}")
            return False
    
    @staticmethod
    def remove_admin(user_id: int) -> bool:
        try:
            result = db.admins.delete_one({"user_id": user_id, "role": "admin"})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"خطأ في إزالة مشرف: {e}")
            return False
    
    @staticmethod
    def get_all_admins() -> List[Dict]:
        return list(db.admins.find({}, {"user_id": 1, "username": 1, "role": 1, "added_at": 1}))

class ServiceManager:
    @staticmethod
    def get_services() -> List[Dict]:
        return list(db.services.find({"active": True}))
    
    @staticmethod
    def get_service(name: str) -> Optional[Dict]:
        return db.services.find_one({"name": name})
    
    @staticmethod
    def update_service_price(name: str, new_price: int) -> bool:
        try:
            result = db.services.update_one(
                {"name": name},
                {"$set": {"price": new_price}}
            )
            
            # تحديث السعر العام إذا كانت هذه خدمة افتراضية
            if name in ["حساب درجة الإعفاء", "تلخيص الملازم", "سؤال وجواب", "ملازمي ومرشحاتي"]:
                db.settings.update_one(
                    {"_id": "global_settings"},
                    {"$set": {"service_price": new_price}}
                )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث سعر الخدمة: {e}")
            return False
    
    @staticmethod
    def can_use_service(user_id: int, service_name: str) -> Tuple[bool, str]:
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return False, "المستخدم غير موجود"
        
        if user.get("banned", False):
            return False, "حسابك محظور"
        
        service = db.services.find_one({"name": service_name})
        if not service or not service.get("active", True):
            return False, "الخدمة غير متاحة حالياً"
        
        settings = db.settings.find_one({"_id": "global_settings"})
        if settings.get("maintenance_mode", False):
            if not AdminManager.is_admin(user_id):
                return False, "البوت تحت الصيانة"
        
        price = service.get("price", settings.get("service_price", 1000))
        
        if user["balance"] < price:
            return False, f"رصيدك غير كافي. السعر: {price} دينار"
        
        return True, ""

class TransactionManager:
    @staticmethod
    def add_transaction(user_id: int, amount: int, transaction_type: str, description: str = "") -> str:
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        
        transaction_data = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
            "type": transaction_type,
            "description": description,
            "timestamp": datetime.now(),
            "status": "completed"
        }
        
        db.transactions.insert_one(transaction_data)
        return transaction_id
    
    @staticmethod
    def get_user_transactions(user_id: int, limit: int = 20) -> List[Dict]:
        return list(db.transactions.find(
            {"user_id": user_id},
            {"_id": 0, "transaction_id": 1, "amount": 1, "type": 1, "description": 1, "timestamp": 1}
        ).sort("timestamp", DESCENDING).limit(limit))
    
    @staticmethod
    def get_all_transactions(limit: int = 100) -> List[Dict]:
        return list(db.transactions.find(
            {},
            {"_id": 0, "transaction_id": 1, "user_id": 1, "amount": 1, "type": 1, "description": 1, "timestamp": 1}
        ).sort("timestamp", DESCENDING).limit(limit))

class FileManager:
    @staticmethod
    def add_file(name: str, description: str, stage: str, file_id: str, file_type: str = "pdf", added_by: int = None) -> bool:
        try:
            file_data = {
                "name": name,
                "description": description,
                "stage": stage,
                "file_id": file_id,
                "file_type": file_type,
                "added_by": added_by,
                "added_at": datetime.now(),
                "downloads": 0,
                "active": True
            }
            
            db.files.insert_one(file_data)
            return True
        except Exception as e:
            logger.error(f"خطأ في إضافة ملف: {e}")
            return False
    
    @staticmethod
    def get_files_by_stage(stage: str = None) -> List[Dict]:
        query = {"active": True}
        if stage:
            query["stage"] = stage
        
        return list(db.files.find(query, {"_id": 1, "name": 1, "description": 1, "stage": 1, "downloads": 1}))
    
    @staticmethod
    def increment_downloads(file_id: str) -> bool:
        try:
            db.files.update_one(
                {"_id": file_id},
                {"$inc": {"downloads": 1}}
            )
            return True
        except Exception as e:
            logger.error(f"خطأ في زيادة عدد التحميلات: {e}")
            return False

class SettingsManager:
    @staticmethod
    def get_settings() -> Dict:
        settings = db.settings.find_one({"_id": "global_settings"})
        return settings or {}
    
    @staticmethod
    def update_settings(updates: Dict) -> bool:
        try:
            db.settings.update_one(
                {"_id": "global_settings"},
                {"$set": updates}
            )
            return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الإعدادات: {e}")
            return False
    
    @staticmethod
    def toggle_maintenance() -> bool:
        try:
            settings = db.settings.find_one({"_id": "global_settings"})
            current = settings.get("maintenance_mode", False)
            
            db.settings.update_one(
                {"_id": "global_settings"},
                {"$set": {"maintenance_mode": not current}}
            )
            
            return not current
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع الصيانة: {e}")
            return False

# =============================================
# معالجات الذكاء الاصطناعي
# =============================================
class AIProcessor:
    @staticmethod
    async def ask_gemini(question: str, context: str = "منهج عراقي تعليمي") -> str:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            أنت مساعد تعليمي متخصص في المنهج العراقي.
            السياق: {context}
            
            السؤال: {question}
            
            أجب بإجابة علمية دقيقة ومنظمة، مع مراعاة:
            1. الدقة العلمية
            2. الوضوح والبساطة
            3. التنسيق الجيد
            4. المراجع إذا لزم الأمر
            """
            
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"خطأ في Gemini AI: {e}")
            return "عذراً، حدث خطأ في المعالجة. الرجاء المحاولة لاحقاً."
    
    @staticmethod
    async def summarize_pdf(pdf_content: bytes) -> str:
        try:
            # تحويل PDF إلى نص
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            # استخدام Gemini للتلخيص
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            قم بتلخيص النص التعليمي التالي مع:
            1. إزالة المعلومات غير المهمة
            2. التركيز على النقاط الرئيسية
            3. تنظيم المعلومات بشكل هرمي
            4. الحفاظ على المصطلحات العلمية
            5. استخدام لغة عربية فصحى واضحة
            
            النص:
            {text}
            
            أعد التلخيص بطريقة منظمة مع عناوين رئيسية وفرعية.
            """
            
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"خطأ في تلخيص PDF: {e}")
            return "عذراً، حدث خطأ في تلخيص الملف."
    
    @staticmethod
    async def extract_text_from_image(image_bytes: bytes) -> str:
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # تحسين الصورة للـ OCR
            image = image.convert('L')  # تحويل إلى تدرج رمادي
            image_array = np.array(image)
            
            # زيادة التباين
            image_array = cv2.convertScaleAbs(image_array, alpha=1.5, beta=0)
            
            # استخراج النص
            text = pytesseract.image_to_string(image_array, lang='ara+eng')
            return text.strip()
        except Exception as e:
            logger.error(f"خطأ في استخراج النص من الصورة: {e}")
            return ""

class PDFGenerator:
    def __init__(self):
        # تسجيل الخطوط العربية
        try:
            pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('ArabicBold', 'arialbd.ttf'))
        except:
            # استخدام الخطوط الافتراضية إذا لم تكن الخطوط موجودة
            pass
    
    @staticmethod
    def reshape_arabic(text: str) -> str:
        """إعادة تشكيل النص العربي"""
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    
    async def create_summary_pdf(self, title: str, content: str, user_name: str) -> BytesIO:
        """إنشاء ملف PDF ملخص"""
        buffer = BytesIO()
        
        try:
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            
            # الأنماط
            styles = getSampleStyleSheet()
            
            # إضافة أنماط عربية
            arabic_style = ParagraphStyle(
                'Arabic',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=12,
                alignment=2,  # محاذاة لليمين
                spaceAfter=12,
                rightIndent=20
            )
            
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Heading1'],
                fontName='ArabicBold',
                fontSize=16,
                alignment=1,  # مركز
                spaceAfter=24
            )
            
            # تحضير المحتوى
            story = []
            
            # العنوان
            arabic_title = self.reshape_arabic(f"تلخيص: {title}")
            story.append(Paragraph(arabic_title, title_style))
            
            # المعلومات
            info_text = self.reshape_arabic(f"المستخدم: {user_name}")
            story.append(Paragraph(info_text, arabic_style))
            
            date_text = self.reshape_arabic(f"التاريخ: {datetime.now().strftime('%Y/%m/%d %I:%M %p')}")
            story.append(Paragraph(date_text, arabic_style))
            
            story.append(Spacer(1, 24))
            
            # المحتوى
            paragraphs = content.split('\n')
            for para in paragraphs:
                if para.strip():
                    arabic_para = self.reshape_arabic(para.strip())
                    story.append(Paragraph(arabic_para, arabic_style))
                    story.append(Spacer(1, 6))
            
            # تذييل الصفحة
            footer = self.reshape_arabic("تم الإنشاء بواسطة بوت 'يلا نتعلم' - @FC4Xbot")
            story.append(Spacer(1, 36))
            story.append(Paragraph(footer, arabic_style))
            
            # بناء PDF
            doc.build(story)
            
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء PDF: {e}")
            buffer = BytesIO()
            
            # PDF بسيط كبديل
            c = canvas.Canvas(buffer, pagesize=A4)
            c.setFont("Helvetica", 12)
            c.drawString(100, 750, "Error generating PDF")
            c.save()
            buffer.seek(0)
            return buffer
    
    async def create_exemption_report(self, scores: List[float], average: float, result: str, user_name: str) -> BytesIO:
        """إنشاء تقرير حساب الإعفاء"""
        buffer = BytesIO()
        
        try:
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            arabic_style = ParagraphStyle(
                'Arabic',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=12,
                alignment=2,
                spaceAfter=12
            )
            
            story = []
            
            # العنوان
            title = self.reshape_arabic("تقرير حساب درجة الإعفاء")
            story.append(Paragraph(title, arabic_style))
            story.append(Spacer(1, 20))
            
            # المعلومات
            info = self.reshape_arabic(f"الطالب: {user_name}")
            story.append(Paragraph(info, arabic_style))
            
            date = self.reshape_arabic(f"تاريخ الحساب: {datetime.now().strftime('%Y/%m/%d')}")
            story.append(Paragraph(date, arabic_style))
            
            story.append(Spacer(1, 30))
            
            # الدرجات
            scores_text = self.reshape_arabic("الدرجات المدخلة:")
            story.append(Paragraph(scores_text, arabic_style))
            
            for i, score in enumerate(scores, 1):
                score_text = self.reshape_arabic(f"الكورس {i}: {score}")
                story.append(Paragraph(score_text, arabic_style))
            
            story.append(Spacer(1, 20))
            
            # المعدل
            avg_text = self.reshape_arabic(f"المعدل النهائي: {average:.2f}")
            story.append(Paragraph(avg_text, arabic_style))
            
            # النتيجة
            result_text = self.reshape_arabic(f"النتيجة: {result}")
            story.append(Paragraph(result_text, arabic_style))
            
            story.append(Spacer(1, 40))
            
            # الخلاصة
            summary = self.reshape_arabic(
                "ملاحظة: الإعفاء يحتاج إلى معدل 90 أو أعلى. "
                "يمكنك إعادة المحاولة في الكورسات القادمة."
            )
            story.append(Paragraph(summary, arabic_style))
            
            doc.build(story)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير الإعفاء: {e}")
            return await self.create_simple_pdf("تقرير الإعفاء", f"المعدل: {average} - النتيجة: {result}")

# =============================================
# حالات المحادثة
# =============================================
(
    # المستخدم العادي
    AWAITING_SCORES,
    AWAITING_QUESTION,
    AWAITING_PDF,
    
    # المشرف
    ADMIN_CHARGE_USER,
    ADMIN_CHARGE_AMOUNT,
    ADMIN_BAN_USER,
    ADMIN_BAN_REASON,
    ADMIN_ADD_FILE_NAME,
    ADMIN_ADD_FILE_DESC,
    ADMIN_ADD_FILE_STAGE,
    ADMIN_ADD_FILE_UPLOAD,
    ADMIN_UPDATE_PRICE,
    ADMIN_BROADCAST_MESSAGE,
    ADMIN_BROADCAST_CONFIRM,
    
    # الترقية
    ADMIN_PROMOTE_USER,
    
    # التعديل
    ADMIN_EDIT_SETTINGS,
    
) = range(20)

# =============================================
# دوال البوت الرئيسية
# =============================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء البوت"""
    user = update.effective_user
    message = update.message
    
    # الحصول على بيانات المستخدم
    user_data = UserManager.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # التحقق من الحظر
    if user_data.get("banned", False):
        await message.reply_text(
            "⛔ *حسابك محظور*\n"
            f"السبب: {user_data.get('ban_reason', 'غير محدد')}\n\n"
            "للمساعدة تواصل مع الدعم: @Allawi04",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # التحقق من وضع الصيانة
    settings = SettingsManager.get_settings()
    if settings.get("maintenance_mode", False) and not AdminManager.is_admin(user.id):
        await message.reply_text(
            "🔧 *البوت تحت الصيانة*\n\n"
            "نعمل على تحسين الخدمة لكم. نعتذر للإزعاج.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # تحديث آخر نشاط
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {"last_active": datetime.now()}}
    )
    
    # إعداد لوحة المفاتيح
    keyboard = [
        [
            InlineKeyboardButton("🧮 حساب الإعفاء", callback_data="service_exemption"),
            InlineKeyboardButton("📄 تلخيص الملازم", callback_data="service_summary")
        ],
        [
            InlineKeyboardButton("❓ سؤال وجواب", callback_data="service_qa"),
            InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data="service_files")
        ],
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
            InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data="invite_friends")
        ],
        [
            InlineKeyboardButton("💳 شحن الرصيد", callback_data="charge_balance"),
            InlineKeyboardButton("📜 سجل المعاملات", callback_data="transaction_history")
        ],
        [
            InlineKeyboardButton("📢 قناة البوت", url=f"https://t.me/{settings.get('bot_channel', BOT_CHANNEL)[1:]}"),
            InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")
        ]
    ]
    
    # إضافة زر لوحة التحكم للمشرفين
    if AdminManager.is_admin(user.id):
        keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎊 *مرحباً {user.first_name}!*

🏦 *رصيدك الحالي:* {user_data['balance']:,} دينار
🎁 *المكافأة الترحيبية:* {settings.get('welcome_bonus', 1000):,} دينار

📚 *الخدمات المتاحة:*
1️⃣ حساب درجة الإعفاء الفردي
2️⃣ تلخيص الملازم بالذكاء الاصطناعي  
3️⃣ سؤال وجواب بالذكاء الاصطناعي
4️⃣ ملازمي ومرشحاتي

💰 *سعر الخدمة:* {settings.get('service_price', 1000):,} دينار

📲 *طريقة الشحن:* تواصل مع الدعم: @{ADMIN_USERNAME}
🎯 *مكافأة الدعوة:* {settings.get('invite_bonus', 500):,} دينار لكل صديق

اختر الخدمة التي تريدها من الأزرار أدناه 👇
    """
    
    if message:
        await message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        query = update.callback_query
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return ConversationHandler.END

async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الخدمة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = UserManager.get_or_create_user(user_id)
    
    # التحقق من الحظر
    if user_data.get("banned", False):
        await query.edit_message_text(
            "⛔ حسابك محظور. تواصل مع الدعم.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    service_mapping = {
        "service_exemption": ("🧮 حساب درجة الإعفاء", process_exemption_service),
        "service_summary": ("📄 تلخيص الملازم", process_summary_service),
        "service_qa": ("❓ سؤال وجواب", process_qa_service),
        "service_files": ("📚 ملازمي ومرشحاتي", process_files_service),
        "my_balance": ("💰 رصيدي", show_balance),
        "my_stats": ("📊 إحصائياتي", show_stats),
        "invite_friends": ("🔗 دعوة أصدقاء", show_invite),
        "charge_balance": ("💳 شحن الرصيد", show_charge_options),
        "transaction_history": ("📜 سجل المعاملات", show_transaction_history),
        "admin_panel": ("👑 لوحة التحكم", show_admin_panel)
    }
    
    service_name, handler = service_mapping.get(query.data, (None, None))
    
    if handler:
        return await handler(update, context)
    else:
        await query.edit_message_text("الخدمة غير متاحة حالياً.")
        return ConversationHandler.END

# =============================================
# الخدمات الرئيسية
# =============================================
async def process_exemption_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة خدمة حساب الإعفاء"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # التحقق من إمكانية استخدام الخدمة
    can_use, message = ServiceManager.can_use_service(user_id, "حساب درجة الإعفاء")
    if not can_use:
        await query.edit_message_text(f"❌ {message}")
        return ConversationHandler.END
    
    service = ServiceManager.get_service("حساب درجة الإعفاء")
    price = service.get("price", 1000)
    
    # خصم السعر
    if not UserManager.update_balance(user_id, price, "subtract"):
        await query.edit_message_text("❌ خطأ في خصم الرصيد")
        return ConversationHandler.END
    
    # تسجيل المعاملة
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=-price,
        transaction_type="service_payment",
        description="خدمة: حساب درجة الإعفاء"
    )
    
    # تحديث إحصائيات المستخدم
    db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_services": 1,
                "total_spent": price
            }
        }
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ تم خصم {price:,} دينار\n"
        "🧮 *حاسبة درجة الإعفاء*\n\n"
        "أدخل درجات الكورسات الثلاثة (مفصولة بمسافة أو كل درجة في سطر):\n"
        "مثال: 90 85 95\n\n"
        "ملاحظة: المعدل المطلوب للإعفاء هو 90 أو أعلى.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return AWAITING_SCORES

async def process_summary_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة خدمة تلخيص الملازم"""
    query = update.callback_query
    user_id = query.from_user.id
    
    can_use, message = ServiceManager.can_use_service(user_id, "تلخيص الملازم")
    if not can_use:
        await query.edit_message_text(f"❌ {message}")
        return ConversationHandler.END
    
    service = ServiceManager.get_service("تلخيص الملازم")
    price = service.get("price", 1000)
    
    if not UserManager.update_balance(user_id, price, "subtract"):
        await query.edit_message_text("❌ خطأ في خصم الرصيد")
        return ConversationHandler.END
    
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=-price,
        transaction_type="service_payment",
        description="خدمة: تلخيص الملازم"
    )
    
    db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_services": 1,
                "total_spent": price
            }
        }
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ تم خصم {price:,} دينار\n"
        "📄 *تلخيص الملازم*\n\n"
        "أرسل لي ملف PDF الآن (الحجم الأقصى 20MB)\n"
        "سأقوم بتلخيصه وإعادته لك كملف PDF منظم.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return AWAITING_PDF

async def process_qa_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة خدمة سؤال وجواب"""
    query = update.callback_query
    user_id = query.from_user.id
    
    can_use, message = ServiceManager.can_use_service(user_id, "سؤال وجواب")
    if not can_use:
        await query.edit_message_text(f"❌ {message}")
        return ConversationHandler.END
    
    service = ServiceManager.get_service("سؤال وجواب")
    price = service.get("price", 1000)
    
    if not UserManager.update_balance(user_id, price, "subtract"):
        await query.edit_message_text("❌ خطأ في خصم الرصيد")
        return ConversationHandler.END
    
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=-price,
        transaction_type="service_payment",
        description="خدمة: سؤال وجواب"
    )
    
    db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_services": 1,
                "total_spent": price
            }
        }
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ تم خصم {price:,} دينار\n"
        "❓ *سؤال وجواب*\n\n"
        "أرسل سؤالك الآن (نص أو صورة)\n"
        "سأجيبك بإجابة علمية حسب المنهج العراقي.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return AWAITING_QUESTION

async def process_files_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الملازم والمرشحات"""
    query = update.callback_query
    user_id = query.from_user.id
    
    can_use, message = ServiceManager.can_use_service(user_id, "ملازمي ومرشحاتي")
    if not can_use:
        await query.edit_message_text(f"❌ {message}")
        return
    
    service = ServiceManager.get_service("ملازمي ومرشحاتي")
    price = service.get("price", 1000)
    
    if not UserManager.update_balance(user_id, price, "subtract"):
        await query.edit_message_text("❌ خطأ في خصم الرصيد")
        return
    
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=-price,
        transaction_type="service_payment",
        description="خدمة: ملازمي ومرشحاتي"
    )
    
    db.users.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_services": 1,
                "total_spent": price
            }
        }
    )
    
    # الحصول على الملفات
    files = FileManager.get_files_by_stage()
    
    if not files:
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ تم خصم {price:,} دينار\n"
            "📚 *ملازمي ومرشحاتي*\n\n"
            "لا توجد ملفات متاحة حالياً.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # تجميع الملفات حسب المرحلة
    stages = {}
    for file in files:
        stage = file.get("stage", "عام")
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(file)
    
    # إنشاء الأزرار
    keyboard = []
    for stage, stage_files in stages.items():
        keyboard.append([InlineKeyboardButton(f"📂 {stage}", callback_data=f"stage_{stage}")])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ تم خصم {price:,} دينار\n"
        "📚 *ملازمي ومرشحاتي*\n\n"
        "اختر المرحلة لعرض الملفات:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_stage_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض ملفات مرحلة معينة"""
    query = update.callback_query
    await query.answer()
    
    stage = query.data.replace("stage_", "")
    files = FileManager.get_files_by_stage(stage)
    
    if not files:
        await query.edit_message_text(f"لا توجد ملفات في مرحلة {stage}")
        return
    
    keyboard = []
    for file in files:
        name = file.get("name", "بدون اسم")
        description = file.get("description", "")[:30]
        button_text = f"{name} - {description}"
        
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"download_{file['_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 رجوع للمراحل", callback_data="service_files"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📂 *ملفات مرحلة {stage}*\n\n"
        "اختر الملف للتحميل:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحميل ملف"""
    query = update.callback_query
    await query.answer()
    
    file_id = query.data.replace("download_", "")
    file_data = db.files.find_one({"_id": file_id})
    
    if not file_data:
        await query.edit_message_text("❌ الملف غير موجود")
        return
    
    # زيادة عدد التحميلات
    FileManager.increment_downloads(file_id)
    
    await query.edit_message_text("📥 جاري تحميل الملف...")
    
    try:
        # إرسال الملف
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=file_data["file_id"],
            caption=f"📚 *{file_data['name']}*\n\n{file_data.get('description', '')}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # رسالة تأكيد
        await query.edit_message_text(f"✅ تم إرسال الملف: {file_data['name']}")
    except Exception as e:
        logger.error(f"خطأ في إرسال الملف: {e}")
        await query.edit_message_text("❌ حدث خطأ في إرسال الملف")

# =============================================
# معالجة المدخلات
# =============================================
async def handle_scores_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة درجات الإعفاء"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    try:
        # استخراج الأرقام
        numbers = re.findall(r'\d+\.?\d*', text)
        
        if len(numbers) < 3:
            await update.message.reply_text(
                "❌ الرجاء إدخال 3 درجات على الأقل\n"
                "مثال: 90 85 95"
            )
            return AWAITING_SCORES
        
        scores = list(map(float, numbers[:3]))
        
        # التحقق من النطاق
        for score in scores:
            if score < 0 or score > 100:
                await update.message.reply_text(
                    "❌ الدرجات يجب أن تكون بين 0 و 100"
                )
                return AWAITING_SCORES
        
        # حساب المعدل
        average = sum(scores) / len(scores)
        
        # تحديد النتيجة
        if average >= 90:
            result = "🎉 *مبروك! أنت معفي من المادة*"
            emoji = "✅"
        else:
            result = f"❌ *لسيت معفي من المادة* (المطلوب 90)"
            emoji = "❌"
        
        # إنشاء تقرير PDF
        pdf_generator = PDFGenerator()
        user = update.message.from_user
        user_name = user.first_name or user.username or f"المستخدم {user_id}"
        
        pdf_buffer = await pdf_generator.create_exemption_report(
            scores=scores,
            average=average,
            result="معفي" if average >= 90 else "غير معفي",
            user_name=user_name
        )
        
        # إرسال النتيجة
        result_text = f"""
{emoji} *نتيجة حساب الإعفاء*

📊 *الدرجات المدخلة:*
1. الكورس الأول: {scores[0]:.1f}
2. الكورس الثاني: {scores[1]:.1f}  
3. الكورس الثالث: {scores[2]:.1f}

🧮 *المعدل النهائي:* {average:.2f}

{result}
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # إرسال الرسالة
        await update.message.reply_text(
            result_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # إرسال ملف PDF
        await update.message.reply_document(
            document=InputFile(pdf_buffer, filename="نتيجة_الإعفاء.pdf"),
            caption="📄 تقرير مفصل بنتيجة الإعفاء"
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ الرجاء إدخال أرقام صحيحة\n"
            "مثال: 90 85 95"
        )
        return AWAITING_SCORES
    except Exception as e:
        logger.error(f"خطأ في معالجة الدرجات: {e}")
        await update.message.reply_text("❌ حدث خطأ في المعالجة")
        return ConversationHandler.END

async def handle_pdf_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة ملف PDF"""
    user_id = update.message.from_user.id
    
    if not update.message.document:
        await update.message.reply_text("❌ الرجاء إرسال ملف PDF")
        return AWAITING_PDF
    
    document = update.message.document
    
    if not document.file_name.endswith('.pdf'):
        await update.message.reply_text("❌ الملف يجب أن يكون بصيغة PDF")
        return AWAITING_PDF
    
    if document.file_size > 20 * 1024 * 1024:  # 20MB
        await update.message.reply_text("❌ حجم الملف كبير جداً (الحد الأقصى 20MB)")
        return AWAITING_PDF
    
    await update.message.reply_text("📥 جاري تحميل ومعالجة الملف...")
    
    try:
        # تحميل الملف
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        
        # عرض مؤشر المعالجة
        processing_msg = await update.message.reply_text("🔄 جاري تلخيص الملف باستخدام الذكاء الاصطناعي...")
        
        # تلخيص باستخدام AI
        summary = await AIProcessor.summarize_pdf(bytes(file_bytes))
        
        # إنشاء PDF ملخص
        pdf_generator = PDFGenerator()
        user = update.message.from_user
        user_name = user.first_name or user.username or f"المستخدم {user_id}"
        
        pdf_buffer = await pdf_generator.create_summary_pdf(
            title=document.file_name,
            content=summary,
            user_name=user_name
        )
        
        # حذف رسالة المعالجة
        await processing_msg.delete()
        
        # إرسال الملف الملخص
        keyboard = [
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_document(
            document=InputFile(pdf_buffer, filename=f"ملخص_{document.file_name}"),
            caption=f"📄 *ملخص الملف*\n\n{summary[:500]}...",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في معالجة PDF: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة الملف")
        return ConversationHandler.END

async def handle_question_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الأسئلة"""
    user_id = update.message.from_user.id
    
    # التحقق من المحتوى
    if update.message.text:
        question = update.message.text
    elif update.message.photo:
        # استخراج النص من الصورة
        await update.message.reply_text("🔄 جاري قراءة الصورة...")
        
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_bytes = await file.download_as_bytearray()
        
        question = await AIProcessor.extract_text_from_image(bytes(file_bytes))
        
        if not question:
            await update.message.reply_text("❌ لم أستطع قراءة النص من الصورة")
            return AWAITING_QUESTION
    else:
        await update.message.reply_text("❌ الرجاء إرسال سؤال نصي أو صورة")
        return AWAITING_QUESTION
    
    await update.message.reply_text("🤔 جاري البحث عن الإجابة...")
    
    try:
        # الحصول على الإجابة من AI
        answer = await AIProcessor.ask_gemini(question)
        
        # إرسال الإجابة
        keyboard = [
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💡 *الإجابة:*\n\n{answer}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في معالجة السؤال: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة السؤال")
        return ConversationHandler.END

# =============================================
# الميزات الإضافية
# =============================================
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رصيد المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = UserManager.get_or_create_user(user_id)
    
    settings = SettingsManager.get_settings()
    
    keyboard = [
        [
            InlineKeyboardButton("💳 شحن الرصيد", callback_data="charge_balance"),
            InlineKeyboardButton("📜 المعاملات", callback_data="transaction_history")
        ],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    balance_text = f"""
💰 *رصيدك الحالي*

🏦 الرصيد: {user_data['balance']:,} دينار
💸 إجمالي المشتريات: {user_data.get('total_spent', 0):,} دينار
📊 عدد الخدمات: {user_data.get('total_services', 0)}

📈 *معلومات إضافية:*
🎁 مكافأة الدعوة: {settings.get('invite_bonus', 500):,} دينار
💰 سعر الخدمة: {settings.get('service_price', 1000):,} دينار

للشحن تواصل مع الدعم: @{ADMIN_USERNAME}
    """
    
    await query.edit_message_text(
        balance_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    stats = UserManager.get_user_stats(user_id)
    
    if not stats:
        await query.edit_message_text("❌ لا توجد بيانات")
        return
    
    # حساب الأيام منذ التسجيل
    days_since_join = (datetime.now() - stats['created_at']).days
    
    stats_text = f"""
📊 *إحصائيات حسابك*

👤 المعرف: {user_id}
📅 تاريخ التسجيل: {stats['created_at'].strftime('%Y/%m/%d')}
⏰ آخر نشاط: {stats['last_active'].strftime('%Y/%m/%d %I:%M %p')}
📆 أيام في البوت: {days_since_join} يوم

🏦 *المالية:*
💰 الرصيد الحالي: {stats['balance']:,} دينار
💸 إجمالي المشتريات: {stats['total_spent']:,} دينار
🛒 عدد الخدمات: {stats['total_services']}

👥 *الدعوة:*
👥 عدد المدعوين: {stats['invited_users']}
📊 إجمالي المعاملات: {stats['total_transactions']}

📈 *نشاطك:*
المعدل اليومي: {stats['total_services'] / max(days_since_join, 1):.1f} خدمة/يوم
    """
    
    keyboard = [
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data="invite_friends")
        ],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رابط الدعوة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = UserManager.get_or_create_user(user_id)
    
    settings = SettingsManager.get_settings()
    invite_bonus = settings.get('invite_bonus', 500)
    
    invite_link = f"https://t.me/{context.bot.username}?start={user_data['invite_code']}"
    
    invite_text = f"""
🔗 *دعوة الأصدقاء*

🎁 *المكافأة:* {invite_bonus:,} دينار لكل صديق
👥 *عدد المدعوين:* {len(user_data.get('invited_users', []))}

*رابط الدعوة الخاص بك:*
`{invite_link}`

*طريقة العمل:*
1. شارك الرابط مع أصدقائك
2. عندما ينضم صديق عبر الرابط
3. تحصل على {invite_bonus:,} دينار تلقائياً
4. يمكن لصديقك أيضاً دعوة أصدقاء

*قائمة المدعوين:* {', '.join([str(u) for u in user_data.get('invited_users', [])[:10]]) or 'لا يوجد'}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📤 مشاركة الرابط", switch_inline_query=f"انضم عبر رابط الدعوة {invite_link}"),
            InlineKeyboardButton("📋 نسخ الرابط", callback_data=f"copy_invite_{user_data['invite_code']}")
        ],
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        invite_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_charge_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات الشحن"""
    query = update.callback_query
    await query.answer()
    
    settings = SettingsManager.get_settings()
    min_charge = settings.get('min_charge', 1000)
    
    charge_text = f"""
💳 *شحن الرصيد*

🏦 الحد الأدنى للشحن: {min_charge:,} دينار
💰 سعر الخدمة: {settings.get('service_price', 1000):,} دينار

*طريقة الشحن:*
1. تواصل مع الدعم: @{ADMIN_USERNAME}
2. أرسل له معرفك: `{query.from_user.id}`
3. أرسل المبلغ المطلوب
4. قم بالتحويل
5. سيتم شحن رصيدك فوراً

*ملاحظات:*
- يتم الشحن يدوياً خلال 24 ساعة
- احتفظ بإيصال التحويل
- للشحن السريع راسل الدعم مباشرة
    """
    
    keyboard = [
        [
            InlineKeyboardButton("👨‍💻 تواصل مع الدعم", url=f"https://t.me/{ADMIN_USERNAME}"),
            InlineKeyboardButton("📋 معرفي", callback_data="show_my_id")
        ],
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        charge_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سجل المعاملات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    transactions = TransactionManager.get_user_transactions(user_id, limit=10)
    
    if not transactions:
        history_text = "📜 *سجل المعاملات*\n\nلا توجد معاملات سابقة."
    else:
        history_text = "📜 *آخر 10 معاملات*\n\n"
        for txn in transactions:
            amount = f"+{txn['amount']:,}" if txn['amount'] > 0 else f"{txn['amount']:,}"
            date = txn['timestamp'].strftime('%m/%d %H:%M')
            history_text += f"• {amount} دينار - {txn['description']} ({date})\n"
    
    keyboard = [
        [
            InlineKeyboardButton("💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        history_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# =============================================
# لوحة التحكم - المشرف
# =============================================
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة تحكم المشرف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    settings = SettingsManager.get_settings()
    
    # إحصائيات سريعة
    total_users = db.users.count_documents({})
    total_banned = db.users.count_documents({"banned": True})
    total_services = db.services.count_documents({})
    total_transactions = db.transactions.count_documents({})
    
    admin_text = f"""
👑 *لوحة تحكم المشرف*

📊 *الإحصائيات العامة:*
👥 إجمالي المستخدمين: {total_users:,}
⛔ المحظورين: {total_banned:,}
🛒 عدد الخدمات: {total_services:,}
💳 إجمالي المعاملات: {total_transactions:,}

⚙️ *الإعدادات الحالية:*
💰 سعر الخدمة: {settings.get('service_price', 1000):,} دينار
🎁 مكافأة ترحيبية: {settings.get('welcome_bonus', 1000):,} دينار
🎯 مكافأة الدعوة: {settings.get('invite_bonus', 500):,} دينار
🔧 وضع الصيانة: {'✅ مفعل' if settings.get('maintenance_mode') else '❌ معطل'}

اختر الإدارة المطلوبة:
    """
    
    keyboard = [
        [
            InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge"),
            InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban")
        ],
        [
            InlineKeyboardButton("👑 رفع مشرف", callback_data="admin_promote"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("📜 المعاملات", callback_data="admin_transactions")
        ],
        [
            InlineKeyboardButton("💰 تعديل الأسعار", callback_data="admin_prices"),
            InlineKeyboardButton("🔧 وضع الصيانة", callback_data="admin_toggle_maintenance")
        ],
        [
            InlineKeyboardButton("📢 إشعار للجميع", callback_data="admin_broadcast"),
            InlineKeyboardButton("📁 إدارة الملفات", callback_data="admin_files")
        ],
        [
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_charge_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية شحن رصيد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *شحن رصيد مستخدم*\n\n"
        "أرسل معرف المستخدم (user_id):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_CHARGE_USER

async def admin_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة معرف المستخدم للشحن"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        target_user_id = int(update.message.text)
        context.user_data['charge_user_id'] = target_user_id
        
        # التحقق من وجود المستخدم
        target_user = UserManager.get_or_create_user(target_user_id)
        
        keyboard = [
            [InlineKeyboardButton("🔙 إلغاء", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👤 المستخدم: {target_user.get('first_name', 'غير معروف')}\n"
            f"🏦 الرصيد الحالي: {target_user['balance']:,} دينار\n\n"
            "أرسل المبلغ المطلوب شحنه (رقم فقط):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ADMIN_CHARGE_AMOUNT
        
    except ValueError:
        await update.message.reply_text("❌ المعرف يجب أن يكون رقماً!")
        return ADMIN_CHARGE_USER
    except Exception as e:
        logger.error(f"خطأ في شحن الرصيد: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_complete_charge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إكمال عملية الشحن"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        amount = int(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من الصفر!")
            return ADMIN_CHARGE_AMOUNT
        
        target_user_id = context.user_data.get('charge_user_id')
        
        if not target_user_id:
            await update.message.reply_text("❌ خطأ في البيانات!")
            return ConversationHandler.END
        
        # شحن الرصيد
        if UserManager.update_balance(target_user_id, amount, "add"):
            # تسجيل المعاملة
            TransactionManager.add_transaction(
                user_id=target_user_id,
                amount=amount,
                transaction_type="admin_charge",
                description=f"شحن بواسطة المشرف {user_id}"
            )
            
            # إرسال إشعار للمستخدم
            try:
                settings = SettingsManager.get_settings()
                notification_text = f"""
🎉 *تم شحن رصيدك*

✅ المبلغ: {amount:,} دينار
🏦 الرصيد الجديد: {UserManager.get_or_create_user(target_user_id)['balance']:,} دينار
📅 التاريخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}

شكراً لاستخدامك بوت "يلا نتعلم" ❤️
                """
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"خطأ في إرسال الإشعار: {e}")
            
            keyboard = [
                [
                    InlineKeyboardButton("💰 شحن آخر", callback_data="admin_charge"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم شحن {amount:,} دينار للمستخدم {target_user_id} بنجاح!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ فشل في شحن الرصيد!")
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ المبلغ يجب أن يكون رقماً!")
        return ADMIN_CHARGE_AMOUNT
    except Exception as e:
        logger.error(f"خطأ في إكمال الشحن: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية حظر مستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⛔ *حظر مستخدم*\n\n"
        "أرسل معرف المستخدم (user_id) للحظر:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_BAN_USER

async def admin_ban_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة معرف المستخدم للحظر"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        target_user_id = int(update.message.text)
        context.user_data['ban_user_id'] = target_user_id
        
        # التحقق من وجود المستخدم
        target_user = UserManager.get_or_create_user(target_user_id)
        
        if target_user.get("banned", False):
            keyboard = [
                [
                    InlineKeyboardButton("🔓 فك الحظر", callback_data=f"unban_{target_user_id}"),
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ هذا المستخدم محظور بالفعل!\n"
                f"السبب: {target_user.get('ban_reason', 'غير محدد')}\n\n"
                "هل تريد فك الحظر؟",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton("🔙 إلغاء", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👤 المستخدم: {target_user.get('first_name', 'غير معروف')}\n"
            f"📅 تاريخ التسجيل: {target_user.get('created_at').strftime('%Y/%m/%d')}\n\n"
            "أرسل سبب الحظر:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ADMIN_BAN_REASON
        
    except ValueError:
        await update.message.reply_text("❌ المعرف يجب أن يكون رقماً!")
        return ADMIN_BAN_USER
    except Exception as e:
        logger.error(f"خطأ في حظر المستخدم: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_complete_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إكمال عملية الحظر"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        reason = update.message.text
        
        if len(reason) < 5:
            await update.message.reply_text("❌ السبب قصير جداً!")
            return ADMIN_BAN_REASON
        
        target_user_id = context.user_data.get('ban_user_id')
        
        if not target_user_id:
            await update.message.reply_text("❌ خطأ في البيانات!")
            return ConversationHandler.END
        
        # حظر المستخدم
        if UserManager.ban_user(target_user_id, reason, user_id):
            # إرسال إشعار للمستخدم
            try:
                ban_text = f"""
⛔ *حسابك محظور*

🚫 السبب: {reason}
📅 التاريخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}
🔓 للإستفسار: @{ADMIN_USERNAME}

يمكنك التواصل مع الدعم للاستفسار.
                """
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=ban_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"خطأ في إرسال إشعار الحظر: {e}")
            
            keyboard = [
                [
                    InlineKeyboardButton("⛔ حظر آخر", callback_data="admin_ban"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم حظر المستخدم {target_user_id} بنجاح!\n"
                f"السبب: {reason}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ فشل في حظر المستخدم!")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في إكمال الحظر: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فك حظر مستخدم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    target_user_id = int(query.data.replace("unban_", ""))
    
    if UserManager.unban_user(target_user_id):
        # إرسال إشعار للمستخدم
        try:
            unban_text = f"""
✅ *تم فك حظر حسابك*

🎉 مرحباً بك مرة أخرى في بوت "يلا نتعلم"
📅 التاريخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}

يمكنك الآن استخدام البوت بشكل طبيعي.
            """
            
            await context.bot.send_message(
                chat_id=target_user_id,
                text=unban_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار فك الحظر: {e}")
        
        keyboard = [
            [
                InlineKeyboardButton("⛔ حظر آخر", callback_data="admin_ban"),
                InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ تم فك حظر المستخدم {target_user_id} بنجاح!",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("❌ فشل في فك الحظر!")

async def admin_promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية رفع مشرف"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_super_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👑 *رفع مشرف جديد*\n\n"
        "أرسل معرف المستخدم (user_id) للترقية:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_PROMOTE_USER

async def admin_complete_promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إكمال عملية الترقية"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_super_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        target_user_id = int(update.message.text)
        
        # الحصول على بيانات المستخدم
        target_user = UserManager.get_or_create_user(target_user_id)
        username = target_user.get('username', target_user.get('first_name', 'غير معروف'))
        
        # رفع المشرف
        if AdminManager.add_admin(target_user_id, username, user_id):
            # إرسال إشعار للمستخدم
            try:
                promote_text = f"""
👑 *تهانينا!*

🎉 تمت ترقيتك كمشرف في بوت "يلا نتعلم"
📅 التاريخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}

يمكنك الآن الوصول إلى لوحة التحكم.
                """
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=promote_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"خطأ في إرسال إشعار الترقية: {e}")
            
            keyboard = [
                [
                    InlineKeyboardButton("👑 ترقية آخر", callback_data="admin_promote"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم ترقية المستخدم {target_user_id} (@{username}) كمشرف بنجاح!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ فشل في الترقية! (المستخدم قد يكون مشرفاً بالفعل)")
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ المعرف يجب أن يكون رقماً!")
        return ADMIN_PROMOTE_USER
    except Exception as e:
        logger.error(f"خطأ في الترقية: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المستخدمين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    users = UserManager.get_all_users(limit=10)
    
    if not users:
        users_text = "👥 *المستخدمين*\n\nلا يوجد مستخدمين حالياً."
    else:
        users_text = "👥 *آخر 10 مستخدمين*\n\n"
        for user in users:
            username = user.get('username', user.get('first_name', 'غير معروف'))
            created = user['created_at'].strftime('%m/%d')
            users_text += f"• {username} - {user['user_id']} - {user['balance']:,} دينار ({created})\n"
    
    keyboard = [
        [
            InlineKeyboardButton("⛔ المحظورين", callback_data="admin_banned_users"),
            InlineKeyboardButton("🏆 أفضل المدعوين", callback_data="admin_top_invites")
        ],
        [
            InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user"),
            InlineKeyboardButton("📊 إحصائيات متقدمة", callback_data="admin_advanced_stats")
        ],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        users_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_show_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المستخدمين المحظورين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    banned_users = UserManager.get_banned_users()
    
    if not banned_users:
        banned_text = "⛔ *المستخدمين المحظورين*\n\nلا يوجد مستخدمين محظورين حالياً."
    else:
        banned_text = "⛔ *المستخدمين المحظورين*\n\n"
        for user in banned_users[:15]:  # عرض أول 15 فقط
            username = user.get('username', user.get('first_name', 'غير معروف'))
            reason = user.get('ban_reason', 'غير محدد')
            date = user.get('banned_at', datetime.now()).strftime('%m/%d')
            banned_text += f"• {username} - {user['user_id']}\n  السبب: {reason} ({date})\n\n"
    
    keyboard = []
    
    # أزرار فك الحظر للمستخدمين
    for user in banned_users[:5]:  # أزرار لأول 5 مستخدمين فقط
        keyboard.append([
            InlineKeyboardButton(
                f"🔓 فك حظر {user['user_id']}",
                callback_data=f"unban_{user['user_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("👥 جميع المستخدمين", callback_data="admin_users"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        banned_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_show_top_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أفضل المدعوين"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    top_invites = UserManager.get_top_invites(limit=10)
    
    if not top_invites:
        invites_text = "🏆 *أفضل المدعوين*\n\nلا توجد بيانات حالياً."
    else:
        invites_text = "🏆 *أفضل 10 مدعوين*\n\n"
        for i, user in enumerate(top_invites, 1):
            username = user.get('username', user.get('first_name', 'غير معروف'))
            invites_text += f"{i}. {username} - {user.get('invite_count', 0)} مدعو\n"
    
    keyboard = [
        [
            InlineKeyboardButton("👥 جميع المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        invites_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المعاملات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    transactions = TransactionManager.get_all_transactions(limit=15)
    
    if not transactions:
        txn_text = "📜 *جميع المعاملات*\n\nلا توجد معاملات حالياً."
    else:
        txn_text = "📜 *آخر 15 معاملة*\n\n"
        for txn in transactions:
            amount = f"+{txn['amount']:,}" if txn['amount'] > 0 else f"{txn['amount']:,}"
            date = txn['timestamp'].strftime('%m/%d %H:%M')
            txn_text += f"• {amount} دينار - {txn['description']} ({txn['user_id']}) - {date}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("💰 الإحصائيات المالية", callback_data="admin_financial_stats"),
            InlineKeyboardButton("📊 تقرير يومي", callback_data="admin_daily_report")
        ],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        txn_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات مفصلة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    # إحصائيات متقدمة
    total_users = db.users.count_documents({})
    active_today = db.users.count_documents({
        "last_active": {"$gte": datetime.now() - timedelta(days=1)}
    })
    total_banned = db.users.count_documents({"banned": True})
    total_services_used = db.users.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$total_services"}}}
    ])
    total_services_used = next(total_services_used, {"total": 0})["total"]
    
    total_income = db.transactions.aggregate([
        {"$match": {"type": "service_payment"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ])
    total_income = abs(next(total_income, {"total": 0})["total"])
    
    # توزيع الرصيد
    rich_users = db.users.count_documents({"balance": {"$gt": 5000}})
    poor_users = db.users.count_documents({"balance": {"$lt": 1000}})
    
    stats_text = f"""
📊 *إحصائيات متقدمة*

👥 *المستخدمين:*
• إجمالي المستخدمين: {total_users:,}
• النشطون اليوم: {active_today:,}
• المحظورون: {total_banned:,}
• معدل النشاط: {(active_today/total_users*100 if total_users > 0 else 0):.1f}%

💰 *المالية:*
• إجمالي الدخل: {total_income:,} دينار
• إجمالي الخدمات المستخدمة: {total_services_used:,}
• متوسط السعر: {total_income/total_services_used if total_services_used > 0 else 0:,.0f} دينار

🏦 *توزيع الرصيد:*
• الأغنياء (>5,000): {rich_users:,}
• الفقراء (<1,000): {poor_users:,}
• متوسط الرصيد: {db.users.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$balance"}}}]).next().get('avg', 0):,.0f} دينار

📈 *النمو:*
• مستخدمين جدد (7 أيام): {db.users.count_documents({"created_at": {"$gte": datetime.now() - timedelta(days=7)}}):,}
• معاملات (7 أيام): {db.transactions.count_documents({"timestamp": {"$gte": datetime.now() - timedelta(days=7)}}):,}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
            InlineKeyboardButton("📜 المعاملات", callback_data="admin_transactions")
        ],
        [
            InlineKeyboardButton("📅 تقرير أسبوعي", callback_data="admin_weekly_report"),
            InlineKeyboardButton("📊 رسوم بيانية", callback_data="admin_charts")
        ],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل وضع الصيانة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    new_state = SettingsManager.toggle_maintenance()
    
    if new_state:
        status = "✅ مفعل"
        notification = "🔧 *البوت تحت الصيانة*\n\nنعمل على تحسين الخدمة. نعتذر للإزعاج."
    else:
        status = "❌ معطل"
        notification = "🎉 *البوت يعمل بشكل طبيعي*\n\nشكراً لصبركم!"
    
    keyboard = [
        [
            InlineKeyboardButton("🔧 تبديل مرة أخرى", callback_data="admin_toggle_maintenance"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔧 *وضع الصيانة*\n\nالحالة: {status}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # إرسال إشعار عام إذا تم تفعيل الصيانة
    if new_state:
        # يمكن إضافة إرسال إشعار للجميع هنا
        pass

async def admin_manage_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة أسعار الخدمات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    services = ServiceManager.get_services()
    
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {service['name']} - {service['price']:,} دينار",
                callback_data=f"edit_price_{service['name']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("⚙️ الإعدادات العامة", callback_data="admin_general_prices"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *إدارة أسعار الخدمات*\n\n"
        "اختر الخدمة لتعديل سعرها:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تعديل سعر خدمة معينة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    service_name = query.data.replace("edit_price_", "")
    service = ServiceManager.get_service(service_name)
    
    if not service:
        await query.edit_message_text("❌ الخدمة غير موجودة!")
        return ConversationHandler.END
    
    context.user_data['edit_service_name'] = service_name
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_prices")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 *تعديل سعر الخدمة*\n\n"
        f"الخدمة: {service_name}\n"
        f"السعر الحالي: {service['price']:,} دينار\n\n"
        "أرسل السعر الجديد (رقم فقط):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_UPDATE_PRICE

async def admin_complete_price_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إكمال تعديل السعر"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    try:
        new_price = int(update.message.text)
        
        if new_price < 100:
            await update.message.reply_text("❌ السعر يجب أن يكون 100 دينار على الأقل!")
            return ADMIN_UPDATE_PRICE
        
        service_name = context.user_data.get('edit_service_name')
        
        if not service_name:
            await update.message.reply_text("❌ خطأ في البيانات!")
            return ConversationHandler.END
        
        # تحديث السعر
        if ServiceManager.update_service_price(service_name, new_price):
            keyboard = [
                [
                    InlineKeyboardButton("💰 تعديل آخر", callback_data="admin_prices"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم تحديث سعر خدمة '{service_name}' إلى {new_price:,} دينار بنجاح!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ فشل في تحديث السعر!")
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ السعر يجب أن يكون رقماً!")
        return ADMIN_UPDATE_PRICE
    except Exception as e:
        logger.error(f"خطأ في تعديل السعر: {e}")
        await update.message.reply_text("❌ حدث خطأ!")
        return ConversationHandler.END

async def admin_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إرسال إشعار للجميع"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 *إرسال إشعار للجميع*\n\n"
        "أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:\n\n"
        "يمكنك استخدام Markdown للتنسيق.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_BROADCAST_MESSAGE

async def admin_confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأكيد إرسال الإشعار"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    message_text = update.message.text
    context.user_data['broadcast_message'] = message_text
    
    # تقدير عدد المستخدمين
    total_users = db.users.count_documents({"banned": False})
    
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، أرسل", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ لا، ألغِ", callback_data="admin_panel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📢 *تأكيد الإرسال*\n\n"
        f"عدد المستخدمين: {total_users:,}\n\n"
        f"*معاينة الرسالة:*\n{message_text[:500]}...\n\n"
        f"هل تريد إرسال هذه الرسالة لجميع المستخدمين؟",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_BROADCAST_CONFIRM

async def admin_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال الإشعار للجميع"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    message_text = context.user_data.get('broadcast_message')
    
    if not message_text:
        await query.edit_message_text("❌ لا توجد رسالة للإرسال!")
        return
    
    await query.edit_message_text("📤 جاري إرسال الإشعار...")
    
    # الحصول على جميع المستخدمين غير المحظورين
    users = list(db.users.find({"banned": False}, {"user_id": 1}))
    total_users = len(users)
    successful = 0
    failed = 0
    
    # إرسال الرسالة لكل مستخدم
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            successful += 1
            
            # تأخير صغير لتجنب حظر التليجرام
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed += 1
            logger.error(f"خطأ في إرسال إشعار للمستخدم {user['user_id']}: {e}")
    
    # حفظ البث في قاعدة البيانات
    broadcast_data = {
        "admin_id": user_id,
        "message": message_text,
        "total_users": total_users,
        "successful": successful,
        "failed": failed,
        "sent_at": datetime.now()
    }
    db.broadcasts.insert_one(broadcast_data)
    
    keyboard = [
        [
            InlineKeyboardButton("📢 إرسال آخر", callback_data="admin_broadcast"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ *تم إرسال الإشعار بنجاح*\n\n"
        f"📊 النتائج:\n"
        f"• إجمالي المستخدمين: {total_users:,}\n"
        f"• تم الإرسال بنجاح: {successful:,}\n"
        f"• فشل الإرسال: {failed:,}\n"
        f"• نسبة النجاح: {(successful/total_users*100 if total_users > 0 else 0):.1f}%",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_manage_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة الملفات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return
    
    files = FileManager.get_files_by_stage()
    total_files = len(files)
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة ملف جديد", callback_data="admin_add_file")],
        [InlineKeyboardButton("📊 إحصائيات الملفات", callback_data="admin_file_stats")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")]
    ]
    
    # أزرار الملفات
    if files:
        keyboard.insert(0, [InlineKeyboardButton("📁 عرض جميع الملفات", callback_data="admin_all_files")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📁 *إدارة الملفات*\n\n"
        f"إجمالي الملفات: {total_files}\n\n"
        "اختر الإجراء المطلوب:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_add_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء إضافة ملف جديد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_files")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📁 *إضافة ملف جديد*\n\n"
        "أرسل اسم الملف:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ADMIN_ADD_FILE_NAME

async def admin_add_file_process(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int) -> int:
    """معالجة خطوات إضافة الملف"""
    user_id = update.message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    if step == ADMIN_ADD_FILE_NAME:
        context.user_data['file_name'] = update.message.text
        
        await update.message.reply_text(
            "أرسل وصف الملف:"
        )
        return ADMIN_ADD_FILE_DESC
        
    elif step == ADMIN_ADD_FILE_DESC:
        context.user_data['file_description'] = update.message.text
        
        keyboard = [
            [
                InlineKeyboardButton("الأولى", callback_data="stage_1"),
                InlineKeyboardButton("الثانية", callback_data="stage_2"),
                InlineKeyboardButton("الثالثة", callback_data="stage_3")
            ],
            [
                InlineKeyboardButton("الرابعة", callback_data="stage_4"),
                InlineKeyboardButton("عام", callback_data="stage_general")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "اختر المرحلة التعليمية:",
            reply_markup=reply_markup
        )
        return ADMIN_ADD_FILE_STAGE
        
    elif step == ADMIN_ADD_FILE_STAGE:
        # يتم التعامل مع هذا عبر callback
        return ADMIN_ADD_FILE_STAGE
        
    elif step == ADMIN_ADD_FILE_UPLOAD:
        if not update.message.document:
            await update.message.reply_text("❌ الرجاء إرسال ملف!")
            return ADMIN_ADD_FILE_UPLOAD
        
        document = update.message.document
        file_id = document.file_id
        
        # جمع البيانات
        file_name = context.user_data.get('file_name')
        file_description = context.user_data.get('file_description')
        file_stage = context.user_data.get('file_stage', 'عام')
        
        # إضافة الملف
        if FileManager.add_file(
            name=file_name,
            description=file_description,
            stage=file_stage,
            file_id=file_id,
            added_by=user_id
        ):
            keyboard = [
                [
                    InlineKeyboardButton("➕ إضافة ملف آخر", callback_data="admin_add_file"),
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_panel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم إضافة الملف '{file_name}' بنجاح!",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ فشل في إضافة الملف!")
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('file_name', None)
        context.user_data.pop('file_description', None)
        context.user_data.pop('file_stage', None)
        
        return ConversationHandler.END
    
    return ConversationHandler.END

async def admin_handle_file_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار مرحلة الملف"""
    query = update.callback_query
    await query.answer()
    
    stage = query.data.replace("stage_", "")
    context.user_data['file_stage'] = stage
    
    await query.edit_message_text(
        f"✅ المرحلة: {stage}\n\n"
        "أرسل ملف PDF الآن:"
    )
    
    return ADMIN_ADD_FILE_UPLOAD

# =============================================
# الدوال المساعدة
# =============================================
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    return await start_command(update, context)

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء العملية الحالية"""
    user = update.effective_user
    
    if update.message:
        await update.message.reply_text(
            "تم الإلغاء.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("تم الإلغاء.")
    
    return ConversationHandler.END

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية العامة"""
    text = update.message.text
    
    if text.startswith('/'):
        return
    
    # يمكن إضافة معالجات إضافية هنا
    
    await update.message.reply_text(
        "استخدم الأزرار للتنقل بين الخدمات.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
        ])
    )

async def handle_invite_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة انضمام المستخدم عبر رابط الدعوة"""
    user = update.effective_user
    
    # الحصول على الكود من رابط الدعوة
    args = context.args
    if args and len(args) > 0:
        invite_code = args[0]
        
        # البحث عن صاحب الكود
        inviter = db.users.find_one({"invite_code": invite_code})
        
        if inviter and inviter["user_id"] != user.id:
            # إضافة المستخدم الجديد إلى قائمة مدعوي صاحب الكود
            db.users.update_one(
                {"user_id": inviter["user_id"]},
                {"$addToSet": {"invited_users": user.id}}
            )
            
            # منح مكافأة الدعوة
            settings = SettingsManager.get_settings()
            invite_bonus = settings.get('invite_bonus', 500)
            
            UserManager.update_balance(inviter["user_id"], invite_bonus, "add")
            
            # تسجيل المعاملة
            TransactionManager.add_transaction(
                user_id=inviter["user_id"],
                amount=invite_bonus,
                transaction_type="invite_bonus",
                description=f"مكافأة دعوة للمستخدم {user.id}"
            )
            
            # إرسال إشعار لصاحب الدعوة
            try:
                await context.bot.send_message(
                    chat_id=inviter["user_id"],
                    text=f"🎉 *مكافأة دعوة جديدة*\n\nانضم مستخدم جديد عبر رابط دعوتك!\n🎁 المكافأة: {invite_bonus:,} دينار",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    # متابعة البدء العادي
    return await start_command(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")
    
    try:
        if update and update.effective_user:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="عذراً، حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."
            )
    except:
        pass

# =============================================
# التشغيل الرئيسي
# =============================================
def main():
    """تشغيل البوت"""
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # معالج البداية
    start_handler = CommandHandler('start', handle_invite_start)
    application.add_handler(start_handler)
    
    # معالج المحادثة للخدمات
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_service_selection, pattern="^(service_|my_|charge_|transaction_)")
        ],
        states={
            AWAITING_SCORES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scores_input),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
            ],
            AWAITING_PDF: [
                MessageHandler(filters.Document.PDF, handle_pdf_input),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
            ],
            AWAITING_QUESTION: [
                MessageHandler(filters.TEXT | filters.PHOTO, handle_question_input),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
            ],
            
            # حالات المشرف
            ADMIN_CHARGE_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_charge_amount),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_CHARGE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_complete_charge),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_BAN_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_reason),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_BAN_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_complete_ban),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_PROMOTE_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_complete_promote),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_UPDATE_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_complete_price_edit),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirm_broadcast),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_BROADCAST_CONFIRM: [
                CallbackQueryHandler(admin_send_broadcast, pattern="^confirm_broadcast$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_ADD_FILE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: admin_add_file_process(u, c, ADMIN_ADD_FILE_NAME)),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_ADD_FILE_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: admin_add_file_process(u, c, ADMIN_ADD_FILE_DESC)),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_ADD_FILE_STAGE: [
                CallbackQueryHandler(admin_handle_file_stage, pattern="^stage_"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
            ADMIN_ADD_FILE_UPLOAD: [
                MessageHandler(filters.Document.PDF, lambda u, c: admin_add_file_process(u, c, ADMIN_ADD_FILE_UPLOAD)),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")
            ],
        },
        fallbacks=[
            CommandHandler('start', start_command),
            CommandHandler('cancel', handle_cancel),
            CallbackQueryHandler(back_to_main, pattern="^back_to_main$")
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # معالج الأزرار الإضافية
    application.add_handler(CallbackQueryHandler(show_stage_files, pattern="^stage_"))
    application.add_handler(CallbackQueryHandler(download_file, pattern="^download_"))
    application.add_handler(CallbackQueryHandler(admin_show_users, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_show_banned_users, pattern="^admin_banned_users$"))
    application.add_handler(CallbackQueryHandler(admin_show_top_invites, pattern="^admin_top_invites$"))
    application.add_handler(CallbackQueryHandler(admin_show_transactions, pattern="^admin_transactions$"))
    application.add_handler(CallbackQueryHandler(admin_show_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_toggle_maintenance, pattern="^admin_toggle_maintenance$"))
    application.add_handler(CallbackQueryHandler(admin_manage_prices, pattern="^admin_prices$"))
    application.add_handler(CallbackQueryHandler(admin_edit_price, pattern="^edit_price_"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_message, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_manage_files, pattern="^admin_files$"))
    application.add_handler(CallbackQueryHandler(admin_add_file_start, pattern="^admin_add_file$"))
    application.add_handler(CallbackQueryHandler(admin_unban_user, pattern="^unban_"))
    application.add_handler(CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$"))
    
    # معالج الرسائل العامة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء البوت
    logger.info("✅ البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
