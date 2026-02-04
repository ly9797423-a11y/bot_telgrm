#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - البوت التعليمي للطلاب العراقيين
الإصدار المحسن - الإصدار 3.0
المطور: Allawi04@
"""

import logging
import json
import os
import re
import uuid
import asyncio
import html
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import tempfile
import traceback
from urllib.parse import urlparse

# ============= تحميل المكتبات مع معالجة الأخطاء =============
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SUPPORT = True
except ImportError:
    HAS_ARABIC_SUPPORT = False
    print("⚠️  تحذير: المكتبات العربية غير مثبتة، سيتم استخدام نص عادي")

try:
    import PyPDF2
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False
    print("⚠️  تحذير: PyPDF2 غير مثبت، بعض الميزات لن تعمل")

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("⚠️  تحذير: ReportLab غير مثبت، PDF generation لن يعمل")

try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup, 
        InputFile, InputMediaDocument, InputMediaVideo,
        ReplyKeyboardMarkup, ReplyKeyboardRemove
    )
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        CallbackQueryHandler, ContextTypes, filters,
        ConversationHandler, PicklePersistence
    )
    from telegram.constants import ParseMode, ChatAction
    HAS_TELEGRAM = True
except ImportError as e:
    print(f"❌ خطأ: python-telegram-bot غير مثبت: {e}")
    print("🔧 قم بتثبيته: pip install python-telegram-bot")
    sys.exit(1)

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("⚠️  تحذير: google-generativeai غير مثبت، الذكاء الاصطناعي لن يعمل")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  تحذير: requests غير مثبت، بعض الميزات لن تعمل")

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False
    print("⚠️  تحذير: aiofiles غير مثبت")

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False
    print("⚠️  تحذير: pytz غير مثبت")

# ============= إعدادات البوت =============
TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
BOT_USERNAME = "@FC4Xbot"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04"
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"

# ============= مسارات الملفات =============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
TEMP_DIR = BASE_DIR / "temp"

# إنشاء المجلدات إذا لم تكن موجودة
for directory in [DATA_DIR, BACKUP_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

# ============= ملفات البيانات =============
DATA_FILE = DATA_DIR / "users_data.json"
MATERIALS_FILE = DATA_DIR / "materials_data.json"
ADMIN_FILE = DATA_DIR / "admin_settings.json"
QUESTIONS_FILE = DATA_DIR / "questions_data.json"
BANNED_FILE = DATA_DIR / "banned_users.json"
CHANNEL_FILE = DATA_DIR / "channel_info.json"
SERVICES_FILE = DATA_DIR / "services_status.json"
VIP_FILE = DATA_DIR / "vip_data.json"
VIP_LECTURES_FILE = DATA_DIR / "vip_lectures.json"
VIP_PURCHASES_FILE = DATA_DIR / "vip_purchases.json"
REFERRALS_FILE = DATA_DIR / "referrals.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"

# ============= حالات المحادثة =============
(
    # الحالات الأساسية
    ADMIN_MENU, CHARGE_USER, CHARGE_AMOUNT, PRICE_CHANGE, CHANGE_PRICE_SERVICE,
    MATERIAL_FILE, MATERIAL_DESC, MATERIAL_STAGE, QUESTION_DETAILS, 
    QUESTION_ANSWER, BAN_USER, CHANGE_CHANNEL, DELETE_MATERIAL, 
    ADD_MATERIAL, VIEW_USER, TOGGLE_SERVICE,
    
    # نظام الإعفاء
    EXEMPTION_COURSE1, EXEMPTION_COURSE2, EXEMPTION_COURSE3,
    
    # نظام VIP
    VIP_MANAGEMENT, VIP_ADD_LECTURE, VIP_LECTURE_TITLE, VIP_LECTURE_DESC,
    VIP_LECTURE_FILE, VIP_LECTURE_PRICE, VIP_SUBSCRIPTION_MANAGE,
    VIP_CHANGE_SUBSCRIPTION_PRICE, VIP_APPROVE_LECTURE, 
    VIP_BAN_TEACHER, VIP_VIEW_LECTURES, VIP_BUY_LECTURE,
    VIP_VIEW_LECTURE_DETAIL, VIP_REVIEW_LECTURE, VIP_REJECT_REASON,
    
    # الذكاء الاصطناعي
    SUMMARIZE_PDF, QA_QUESTION,
    
    # ساعدوني طلاب
    HELP_STUDENT_QUESTION, HELP_STUDENT_ANSWER,
    
    # المواد التعليمية
    MATERIALS_SELECT_STAGE, MATERIALS_VIEW,
    
    # نظام الإحالة
    REFERRAL_SETTINGS, REFERRAL_BONUS_CHANGE,
    
    # مراجعة المحاضرات
    LECTURE_PREVIEW, LECTURE_APPROVAL,
    
    # إعدادات عامة
    WELCOME_BONUS_CHANGE, ANSWER_REWARD_CHANGE
) = range(46)

# ============= إعداد التسعير الافتراضي =============
DEFAULT_PRICES = {
    "exemption": 1000,
    "summarize": 1000,
    "qa": 1000,
    "materials": 1000,
    "help_student": 250,
    "vip_subscription": 5000
}

# ============= إعداد الخدمات النشطة =============
DEFAULT_SERVICES = {
    "exemption": {"active": True, "name": "🧮 حساب درجة الإعفاء", "description": "حساب متوسط الدرجات للإعفاء"},
    "summarize": {"active": True, "name": "📚 تلخيص الملازم", "description": "تلخيص الملفات التعليمية باستخدام الذكاء الاصطناعي"},
    "qa": {"active": True, "name": "❓ سؤال وجواب بالذكاء", "description": "إجابة على أسئلتك باستخدام الذكاء الاصطناعي"},
    "materials": {"active": True, "name": "📖 ملازمي ومرشحاتي", "description": "مكتبة المواد التعليمية"},
    "help_student": {"active": True, "name": "🤝 ساعدوني طلاب", "description": "اطرح سؤالاً واحصل على إجابة من الطلاب"},
    "vip_lectures": {"active": True, "name": "👑 محاضرات VIP", "description": "محاضرات تعليمية متخصصة"}
}

WELCOME_BONUS = 1000
REFERRAL_BONUS = 500
ANSWER_REWARD = 100

# ============= إعداد التسجيل =============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(DATA_DIR / 'bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============= فئة معالجة الأخطاء =============
class BotError(Exception):
    """فئة مخصصة لأخطاء البوت"""
    pass

class ValidationError(BotError):
    """خطأ في التحقق من البيانات"""
    pass

# ============= إدارة البيانات المحسنة =============
class EnhancedDataManager:
    """مدير بيانات محسن مع نسخ احتياطي"""
    
    @staticmethod
    def load_data(filename: Path, default=None):
        """تحميل البيانات مع معالجة الأخطاء"""
        if default is None:
            default = {}
        
        try:
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # التحقق من صحة البيانات الأساسية
                if isinstance(data, dict):
                    # تنظيف البيانات الفارغة
                    data = {k: v for k, v in data.items() if v is not None}
                elif isinstance(data, list):
                    data = [item for item in data if item is not None]
                
                return data
            else:
                # إنشاء ملف جديد بالبيانات الافتراضية
                EnhancedDataManager.save_data(filename, default)
                return default
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ خطأ في قراءة JSON في {filename}: {e}")
            # إنشاء نسخة احتياطية للملف التالف
            if filename.exists():
                backup_path = BACKUP_DIR / f"{filename.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filename.rename(backup_path)
                logger.info(f"📦 تم إنشاء نسخة احتياطية للملف التالف: {backup_path}")
            
            EnhancedDataManager.save_data(filename, default)
            return default
            
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في تحميل {filename}: {e}")
            return default
    
    @staticmethod
    def save_data(filename: Path, data):
        """حفظ البيانات مع نسخة احتياطية"""
        try:
            # إنشاء نسخة احتياطية قبل الحفظ
            if filename.exists():
                backup_path = BACKUP_DIR / f"{filename.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                import shutil
                shutil.copy2(filename, backup_path)
            
            # تأكد من أن الدليل موجود
            filename.parent.mkdir(exist_ok=True)
            
            # تحضير البيانات للتخزين
            def prepare_for_json(obj):
                if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
                    return obj
                elif isinstance(obj, datetime):
                    return obj.strftime("%Y-%m-%d %H:%M:%S")
                elif hasattr(obj, '__dict__'):
                    return obj.__dict__
                else:
                    return str(obj)
            
            # تطبيق التحضير على جميع البيانات
            if isinstance(data, dict):
                data = {k: prepare_for_json(v) for k, v in data.items()}
            elif isinstance(data, list):
                data = [prepare_for_json(item) for item in data]
            
            # الحفظ مع تنسيق مقروء
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, default=str)
            
            logger.info(f"✅ تم حفظ البيانات في {filename}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ {filename}: {e}")
            raise
    
    @staticmethod
    def create_backup():
        """إنشاء نسخة احتياطية شاملة"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_folder = BACKUP_DIR / f"full_backup_{timestamp}"
            backup_folder.mkdir(exist_ok=True)
            
            # نسخ جميع ملفات البيانات
            for data_file in DATA_DIR.glob("*.json"):
                shutil.copy2(data_file, backup_folder / data_file.name)
            
            logger.info(f"📦 تم إنشاء نسخة احتياطية كاملة في: {backup_folder}")
            return backup_folder
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
            return None

# ============= خدمة الذكاء الاصطناعي المحسنة =============
class EnhancedAIService:
    """خدمة ذكاء اصطناعي محسنة مع معالجة الأخطاء"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.is_initialized = False
        
        if HAS_GEMINI:
            try:
                genai.configure(api_key=api_key)
                # استخدام نموذج مناسب
                self.model = genai.GenerativeModel('gemini-pro')
                self.is_initialized = True
                logger.info("✅ تم تهيئة خدمة الذكاء الاصطناعي بنجاح")
            except Exception as e:
                logger.error(f"❌ فشل تهيئة Gemini: {e}")
                self.is_initialized = False
        else:
            logger.warning("⚠️  مكتبة Google Gemini غير مثبتة")
    
    async def call_gemini_api(self, prompt: str, max_retries: int = 3) -> str:
        """استدعاء API Gemini مع إعادة المحاولة"""
        if not self.is_initialized:
            return "❌ خدمة الذكاء الاصطناعي غير متاحة حالياً. يرجى المحاولة لاحقاً."
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                
                if response and response.text:
                    return response.text
                else:
                    return "❌ لم أتمكن من إجابة على سؤالك. يرجى إعادة الصياغة."
                    
            except Exception as e:
                logger.error(f"❌ محاولة {attempt + 1} فشلت: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return f"❌ حدث خطأ في خدمة الذكاء الاصطناعي بعد {max_retries} محاولات. الرجاء المحاولة لاحقاً."
    
    async def summarize_pdf(self, pdf_path: Path) -> str:
        """تلخيص ملف PDF"""
        if not HAS_PDF_SUPPORT:
            return "❌ خدمة تلخيص PDF غير متاحة حالياً."
        
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if len(reader.pages) == 0:
                    return "❌ الملف فارغ أو تالف"
                
                # قراءة أول 10 صفحات كحد أقصى
                max_pages = min(10, len(reader.pages))
                for i in range(max_pages):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                
                if len(text) < 100:
                    return "❌ النص قصير جداً للتلخيص أو الملف لا يحتوي على نص قابل للقراءة"
            
            # إذا كان النص طويلاً، نأخذ أول 3000 حرف
            if len(text) > 3000:
                text = text[:3000] + "..."
            
            prompt = f"""
            أنت مساعد تعليمي للطلاب العراقيين. قم بتلخيص النص التعليمي التالي:
            
            {text}
            
            المتطلبات:
            1. استخدم اللغة العربية الفصحى
            2. ركز على النقاط الرئيسية
            3. حذف المعلومات غير الأساسية
            4. نظم النقاط بشكل منطقي
            5. اجعل التلخيص مفيداً للدراسة
            
            قدم التلخيص في فقرات واضحة.
            """
            
            return await self.call_gemini_api(prompt)
            
        except PyPDF2.errors.PdfReadError:
            return "❌ الملف غير صالح أو تالف"
        except Exception as e:
            logger.error(f"❌ خطأ في تلخيص PDF: {e}")
            return f"❌ حدث خطأ في التلخيص: {str(e)[:100]}"
    
    async def answer_question(self, question: str) -> str:
        """الإجابة على سؤال"""
        try:
            prompt = f"""
            أنت مساعد تعليمي متخصص للمناهج العراقية.
            أجب على السؤال التالي بدقة ووضوح:
            
            السؤال: {question}
            
            المتطلبات:
            1. قدم إجابة شاملة ودقيقة
            2. استخدم أمثلة توضيحية إذا لزم الأمر
            3. كن واضحاً ومنظماً
            4. استخدم اللغة العربية الفصحى
            5. ركز على المعلومات المهمة للدراسة
            
            إذا كان السؤال غير واضح، اطلب توضيحاً.
            """
            
            return await self.call_gemini_api(prompt)
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإجابة على السؤال: {e}")
            return f"❌ حدث خطأ في الإجابة: {str(e)[:100]}"
    
    def create_summary_pdf(self, original_text: str, summary: str, output_path: Path) -> bool:
        """إنشاء ملف PDF للتلخيص"""
        if not HAS_REPORTLAB:
            logger.error("❌ ReportLab غير مثبت، لا يمكن إنشاء PDF")
            return False
        
        try:
            c = canvas.Canvas(str(output_path), pagesize=letter)
            width, height = letter
            
            # العنوان
            c.setFont("Helvetica-Bold", 18)
            if HAS_ARABIC_SUPPORT:
                title = arabic_reshaper.reshape("تلخيص الملزمة التعليمية")
                title = get_display(title)
            else:
                title = "تلخيص الملزمة التعليمية"
            c.drawString(50, height - 50, title)
            c.line(50, height - 65, width - 50, height - 65)
            
            # التاريخ
            c.setFont("Helvetica", 12)
            date_text = f"تاريخ التلخيص: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            c.drawString(50, height - 90, date_text)
            
            # التلخيص
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 120, "التلخيص:")
            c.setFont("Helvetica", 12)
            
            y_position = height - 150
            lines = summary.split('\n')
            
            for line in lines:
                if y_position < 100:
                    c.showPage()
                    y_position = height - 50
                    c.setFont("Helvetica", 12)
                
                # معالجة النص العربي
                if HAS_ARABIC_SUPPORT:
                    reshaped_text = arabic_reshaper.reshape(line)
                    display_text = get_display(reshaped_text)
                else:
                    display_text = line
                
                # تقسيم النص الطويل
                max_width = 80
                if len(display_text) > max_width:
                    words = display_text.split()
                    current_line = ""
                    for word in words:
                        if len(current_line) + len(word) + 1 <= max_width:
                            current_line += word + " "
                        else:
                            c.drawString(50, y_position, current_line.strip())
                            y_position -= 20
                            current_line = word + " "
                    
                    if current_line:
                        c.drawString(50, y_position, current_line.strip())
                        y_position -= 20
                else:
                    c.drawString(50, y_position, display_text)
                    y_position -= 20
                
                if y_position < 100 and line != lines[-1]:
                    c.showPage()
                    y_position = height - 50
            
            c.save()
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء PDF: {e}")
            return False

# ============= نظام الإحالة المحسن =============
class ReferralSystem:
    """نظام إحالة محسن مع الإشعارات"""
    
    def __init__(self, data_manager, user_manager):
        self.data_manager = data_manager
        self.user_manager = user_manager
        self.referrals = EnhancedDataManager.load_data(REFERRALS_FILE, {})
    
    def generate_referral_code(self, user_id: int) -> str:
        """إنشاء كود إحالة فريد"""
        import hashlib
        import time
        
        timestamp = str(int(time.time()))
        unique_string = f"{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        referral_code = hashlib.md5(unique_string.encode()).hexdigest()[:8].upper()
        
        return referral_code
    
    def register_referral(self, referrer_id: int, new_user_id: int) -> Tuple[bool, str]:
        """تسجيل إحالة جديدة"""
        try:
            referrer_data = self.user_manager.get_user(referrer_id)
            new_user_data = self.user_manager.get_user(new_user_id)
            
            # منع الإحالة الذاتية
            if referrer_id == new_user_id:
                return False, "لا يمكن الإحالة إلى نفسك"
            
            # التحقق إذا كان المستخدم الجديد قد استخدم كود إحالة سابقاً
            if new_user_data.get("invited_by"):
                return False, "المستخدم قد استخدم كود إحالة مسبقاً"
            
            # تسجيل الإحالة
            new_user_data["invited_by"] = referrer_id
            new_user_data["referral_code_used"] = referrer_data.get("referral_code", "")
            
            # إضافة المستخدم الجديد إلى قائمة المحالين
            if "invited_users" not in referrer_data:
                referrer_data["invited_users"] = []
            
            if new_user_id not in referrer_data["invited_users"]:
                referrer_data["invited_users"].append(new_user_id)
            
            # منح مكافأة الإحالة
            referral_bonus = self.user_manager.settings_manager.get_referral_bonus()
            if referral_bonus > 0:
                # مكافأة للمحيل
                referrer_new_balance, _ = self.user_manager.update_balance(
                    referrer_id, 
                    referral_bonus, 
                    f"مكافأة إحالة للمستخدم {new_user_id}"
                )
                
                # تحديث إحصائيات الإحالة
                referrer_data.setdefault("referral_stats", {
                    "total_referrals": 0,
                    "total_earned": 0,
                    "last_referral": None
                })
                
                referrer_data["referral_stats"]["total_referrals"] += 1
                referrer_data["referral_stats"]["total_earned"] += referral_bonus
                referrer_data["referral_stats"]["last_referral"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # حفظ البيانات
            self.user_manager.save_users()
            
            # تسجيل في نظام الإحالة
            referral_id = str(uuid.uuid4())[:8]
            self.referrals[referral_id] = {
                "referrer_id": referrer_id,
                "new_user_id": new_user_id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bonus_given": referral_bonus,
                "status": "completed"
            }
            
            EnhancedDataManager.save_data(REFERRALS_FILE, self.referrals)
            
            logger.info(f"✅ تم تسجيل إحالة: {referrer_id} -> {new_user_id} (+{referral_bonus} دينار)")
            return True, "تم تسجيل الإحالة بنجاح"
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الإحالة: {e}")
            return False, f"حدث خطأ في تسجيل الإحالة: {str(e)}"
    
    def get_referral_stats(self, user_id: int) -> Dict:
        """الحصول على إحصائيات الإحالة للمستخدم"""
        user_data = self.user_manager.get_user(user_id)
        
        stats = user_data.get("referral_stats", {
            "total_referrals": 0,
            "total_earned": 0,
            "last_referral": None
        })
        
        # الحصول على قائمة المحالين
        invited_users = user_data.get("invited_users", [])
        recent_referrals = []
        
        for invited_id in invited_users[-10:]:  # آخر 10 محالين
            invited_data = self.user_manager.get_user(invited_id)
            recent_referrals.append({
                "user_id": invited_id,
                "name": invited_data.get("first_name", "مستخدم"),
                "join_date": invited_data.get("joined_date", "غير معروف")
            })
        
        return {
            **stats,
            "total_invited": len(invited_users),
            "recent_referrals": recent_referrals,
            "referral_code": user_data.get("referral_code", ""),
            "referral_link": f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        }
    
    def get_top_referrers(self, limit: int = 10) -> List[Dict]:
        """الحصول على أفضل المحالين"""
        all_users = self.user_manager.users
        
        referrers = []
        for user_id_str, user_data in all_users.items():
            invited_count = len(user_data.get("invited_users", []))
            if invited_count > 0:
                referrers.append({
                    "user_id": int(user_id_str),
                    "name": user_data.get("first_name", "مجهول"),
                    "total_referrals": invited_count,
                    "total_earned": user_data.get("referral_stats", {}).get("total_earned", 0)
                })
        
        # الترتيب حسب عدد المحالين
        referrers.sort(key=lambda x: x["total_referrals"], reverse=True)
        return referrers[:limit]

# ============= نظام الإشعارات المحسن =============
class NotificationSystem:
    """نظام إشعارات محسن"""
    
    def __init__(self, data_manager, user_manager):
        self.data_manager = data_manager
        self.user_manager = user_manager
        self.notifications = EnhancedDataManager.load_data(NOTIFICATIONS_FILE, {})
    
    async def send_notification(self, user_id: int, message: str, context: ContextTypes.DEFAULT_TYPE, 
                              notification_type: str = "info") -> bool:
        """إرسال إشعار لمستخدم"""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # تسجيل الإشعار
            self.log_notification(user_id, notification_type, message[:100])
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال إشعار لـ {user_id}: {e}")
            return False
    
    def log_notification(self, user_id: int, notification_type: str, content: str):
        """تسجيل الإشعار في السجل"""
        notification_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if str(user_id) not in self.notifications:
            self.notifications[str(user_id)] = []
        
        self.notifications[str(user_id)].append({
            "id": notification_id,
            "type": notification_type,
            "content": content,
            "timestamp": timestamp,
            "read": False
        })
        
        # حفظ آخر 100 إشعار فقط
        if len(self.notifications[str(user_id)]) > 100:
            self.notifications[str(user_id)] = self.notifications[str(user_id)][-100:]
        
        EnhancedDataManager.save_data(NOTIFICATIONS_FILE, self.notifications)
    
    async def send_bulk_notification(self, user_ids: List[int], message: str, 
                                   context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """إرسال إشعار جماعي"""
        results = {
            "success": 0,
            "failed": 0,
            "failed_ids": []
        }
        
        for user_id in user_ids:
            try:
                success = await self.send_notification(user_id, message, context, "broadcast")
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["failed_ids"].append(user_id)
                
                # تأخير قصير لتجنب حظر Telegram
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال إشعار جماعي لـ {user_id}: {e}")
                results["failed"] += 1
                results["failed_ids"].append(user_id)
        
        return results
    
    def get_unread_notifications(self, user_id: int) -> List[Dict]:
        """الحصول على الإشعارات غير المقروءة"""
        user_notifications = self.notifications.get(str(user_id), [])
        unread = [n for n in user_notifications if not n.get("read", False)]
        return unread
    
    def mark_as_read(self, user_id: int, notification_id: str = None):
        """تحديد الإشعارات كمقروءة"""
        if str(user_id) in self.notifications:
            if notification_id:
                # تحديد إشعار محدد كمقروء
                for notification in self.notifications[str(user_id)]:
                    if notification["id"] == notification_id:
                        notification["read"] = True
                        break
            else:
                # تحديد جميع الإشعارات كمقروءة
                for notification in self.notifications[str(user_id)]:
                    notification["read"] = True
        
        EnhancedDataManager.save_data(NOTIFICATIONS_FILE, self.notifications)
    
    async def send_vip_expiry_notifications(self, context: ContextTypes.DEFAULT_TYPE):
        """إرسال إشعارات انتهاء اشتراك VIP"""
        vip_users = []
        
        for user_id_str, user_data in self.user_manager.users.items():
            if self.user_manager.is_vip(int(user_id_str)):
                vip_users.append((int(user_id_str), user_data))
        
        for user_id, user_data in vip_users:
            expiry_date = user_data.get("vip_expiry")
            if expiry_date:
                try:
                    expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                    days_left = (expiry - datetime.now()).days
                    
                    # إرسال إشعار قبل 7 أيام، 3 أيام، ويوم واحد
                    if days_left in [7, 3, 1]:
                        message = f"""
⚠️ <b>تنبيه انتهاء اشتراك VIP</b>

⏳ <b>المتبقي:</b> {days_left} يوم
📅 <b>تاريخ الانتهاء:</b> {expiry_date}

💡 <b>لتجديد الاشتراك:</b>
1. انتقل إلى قسم 👑 اشتراك VIP
2. اضغط على زر التجديد
3. تأكد من وجود رصيد كافي

📞 <b>للاستفسار:</b> @{SUPPORT_USERNAME}
"""
                        await self.send_notification(user_id, message, context, "vip_expiry")
                        
                except Exception as e:
                    logger.error(f"❌ خطأ في إرسال إشعار انتهاء VIP لـ {user_id}: {e}")

# ============= إدارة المستخدمين المحسنة =============
class EnhancedUserManager:
    """مدير مستخدمين محسن"""
    
    def __init__(self):
        self.users = EnhancedDataManager.load_data(DATA_FILE, {})
        self.banned_users = EnhancedDataManager.load_data(BANNED_FILE, {})
        self.settings_manager = SettingsManager()
        
        # تأكد من وجود بيانات لكل مستخدم
        self._initialize_users_data()
    
    def _initialize_users_data(self):
        """تهيئة بيانات المستخدمين المفقودة"""
        needs_save = False
        
        for user_id_str, user_data in self.users.items():
            # التأكد من وجود جميع الحقول الأساسية
            required_fields = {
                "balance": WELCOME_BONUS,
                "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "first_name": "",
                "username": "",
                "referral_code": user_id_str,
                "invited_by": None,
                "invited_users": [],
                "transactions": [],
                "exemption_scores": [],
                "used_services": [],
                "pending_scores": [],
                "questions_asked": 0,
                "questions_answered": 0,
                "total_earned": 0,
                "last_question_time": None,
                "pending_purchase": None,
                "total_spent": 0,
                "vip_subscription": False,
                "vip_expiry": None,
                "is_teacher": False,
                "vip_lectures": [],
                "teacher_status": "pending",
                "vip_purchases": [],
                "vip_earnings": 0,
                "vip_sales": 0,
                "notifications_enabled": True
            }
            
            for field, default_value in required_fields.items():
                if field not in user_data:
                    user_data[field] = default_value
                    needs_save = True
        
        if needs_save:
            self.save_users()
    
    def get_user(self, user_id: int) -> Dict:
        """الحصول على بيانات مستخدم"""
        user_id_str = str(user_id)
        
        # التحقق إذا كان المستخدم محظوراً
        if user_id_str in self.banned_users:
            banned_data = self.banned_users[user_id_str]
            banned_data["banned"] = True
            return banned_data
        
        # إنشاء مستخدم جديد إذا لم يكن موجوداً
        if user_id_str not in self.users:
            self.users[user_id_str] = {
                "balance": self.settings_manager.get_welcome_bonus(),
                "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "first_name": "",
                "username": "",
                "referral_code": user_id_str,
                "invited_by": None,
                "invited_users": [],
                "transactions": [],
                "exemption_scores": [],
                "used_services": [],
                "pending_scores": [],
                "questions_asked": 0,
                "questions_answered": 0,
                "total_earned": 0,
                "last_question_time": None,
                "pending_purchase": None,
                "total_spent": 0,
                "vip_subscription": False,
                "vip_expiry": None,
                "is_teacher": False,
                "vip_lectures": [],
                "teacher_status": "pending",
                "vip_purchases": [],
                "vip_earnings": 0,
                "vip_sales": 0,
                "notifications_enabled": True
            }
            self.save_users()
            logger.info(f"✅ تم إنشاء مستخدم جديد: {user_id}")
        
        return self.users[user_id_str]
    
    def is_vip(self, user_id: int) -> bool:
        """التحقق إذا كان المستخدم مشترك VIP"""
        user = self.get_user(user_id)
        
        if not user.get("vip_subscription"):
            return False
        
        expiry = user.get("vip_expiry")
        if not expiry:
            return False
        
        try:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            return datetime.now() < expiry_date
        except:
            return False
    
    def add_vip_subscription(self, user_id: int, months: int = 1) -> bool:
        """إضافة اشتراك VIP"""
        try:
            user = self.get_user(user_id)
            
            now = datetime.now()
            current_expiry = user.get("vip_expiry")
            
            if current_expiry:
                try:
                    expiry_date = datetime.strptime(current_expiry, "%Y-%m-%d %H:%M:%S")
                    if expiry_date > now:
                        new_expiry = expiry_date + timedelta(days=30 * months)
                    else:
                        new_expiry = now + timedelta(days=30 * months)
                except:
                    new_expiry = now + timedelta(days=30 * months)
            else:
                new_expiry = now + timedelta(days=30 * months)
            
            user["vip_subscription"] = True
            user["vip_expiry"] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            user["is_teacher"] = True
            user["teacher_status"] = "approved"
            
            transaction = {
                "date": now.strftime("%Y-%m-%d %H:%M:%S"),
                "type": "vip_subscription",
                "months": months,
                "expiry_date": user["vip_expiry"],
                "amount": -self.settings_manager.vip_manager.get_subscription_price()
            }
            
            user.setdefault("vip_transactions", []).append(transaction)
            
            self.save_users()
            logger.info(f"✅ تم إضافة اشتراك VIP للمستخدم {user_id} حتى {user['vip_expiry']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة اشتراك VIP: {e}")
            return False
    
    def update_user_info(self, user_id: int, first_name: str, username: str = ""):
        """تحديث معلومات المستخدم"""
        user = self.get_user(user_id)
        user["first_name"] = first_name
        if username:
            user["username"] = username
        self.save_users()
    
    def can_ask_question(self, user_id: int) -> Tuple[bool, str]:
        """التحقق إذا كان المستخدم يمكنه طرح سؤال"""
        user = self.get_user(user_id)
        last_question = user.get("last_question_time")
        
        if not last_question:
            return True, ""
        
        try:
            last_time = datetime.strptime(last_question, "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_time
            
            if time_diff.total_seconds() < 86400:  # 24 ساعة
                remaining = 86400 - time_diff.total_seconds()
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)
                
                return False, f"⏳ يمكنك طرح سؤال جديد بعد: {hours:02d}:{minutes:02d}:{seconds:02d}"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من وقت السؤال: {e}")
            return True, ""
    
    def update_balance(self, user_id: int, amount: int, description: str = "") -> Tuple[int, bool]:
        """تحديث رصيد المستخدم"""
        try:
            user = self.get_user(user_id)
            old_balance = user.get("balance", 0)
            
            # التحقق من الرصيد الكافي للخصم
            if amount < 0 and old_balance + amount < 0:
                raise ValidationError(f"رصيد غير كافي: {old_balance}، محاولة خصم: {abs(amount)}")
            
            user["balance"] = old_balance + amount
            
            # تسجيل المعاملة
            transaction = {
                "id": str(uuid.uuid4())[:8],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "amount": amount,
                "description": description,
                "balance_before": old_balance,
                "balance_after": user["balance"],
                "type": "credit" if amount > 0 else "debit"
            }
            
            if "transactions" not in user:
                user["transactions"] = []
            
            user["transactions"].append(transaction)
            
            # تحديث الإحصائيات
            if amount > 0:
                user["total_earned"] = user.get("total_earned", 0) + amount
            else:
                user["total_spent"] = user.get("total_spent", 0) + abs(amount)
            
            self.save_users()
            
            logger.info(f"💰 تم تحديث رصيد {user_id}: {old_balance} -> {user['balance']} ({amount:+d})")
            
            # إشعار المستخدم إذا كان المبلغ موجباً
            notify_user = amount > 0 and user.get("notifications_enabled", True)
            return user["balance"], notify_user
            
        except ValidationError as e:
            logger.error(f"❌ خطأ في التحقق: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الرصيد: {e}")
            raise
    
    def set_pending_purchase(self, user_id: int, service: str, price: int):
        """تعيين عملية شراء معلقة"""
        user = self.get_user(user_id)
        user["pending_purchase"] = {
            "service": service,
            "price": price,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }
        self.save_users()
    
    def complete_purchase(self, user_id: int) -> bool:
        """إكمال عملية الشراء"""
        user = self.get_user(user_id)
        
        if not user.get("pending_purchase"):
            return False
        
        purchase = user["pending_purchase"]
        
        # تسجيل الخدمة المستخدمة
        user.setdefault("used_services", []).append({
            "service": purchase["service"],
            "date": purchase["timestamp"],
            "cost": purchase["price"],
            "status": "completed"
        })
        
        # تحديث عملية الشراء
        user["pending_purchase"]["status"] = "completed"
        user["pending_purchase"]["completed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.save_users()
        return True
    
    def cancel_purchase(self, user_id: int) -> bool:
        """إلغاء عملية الشراء"""
        user = self.get_user(user_id)
        
        if not user.get("pending_purchase"):
            return False
        
        purchase = user["pending_purchase"]
        
        # استرجاع الرصيد إذا تم الخصم
        if purchase.get("status") == "completed":
            self.update_balance(user_id, purchase["price"], f"استرجاع رصيد لخدمة: {purchase['service']}")
        
        # تحديث حالة الشراء
        user["pending_purchase"]["status"] = "cancelled"
        user["pending_purchase"]["cancelled_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.save_users()
        return True
    
    def get_all_users(self) -> List[Tuple[str, Dict]]:
        """الحصول على جميع المستخدمين"""
        return list(self.users.items())
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بواسطة الـ ID"""
        return self.users.get(str(user_id))
    
    def get_top_users(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """الحصول على أفضل المستخدمين حسب الرصيد"""
        users_list = list(self.users.items())
        users_list.sort(key=lambda x: x[1].get("balance", 0), reverse=True)
        return users_list[:limit]
    
    def save_users(self):
        """حفظ بيانات المستخدمين"""
        EnhancedDataManager.save_data(DATA_FILE, self.users)
    
    def save_banned(self):
        """حفظ المستخدمين المحظورين"""
        EnhancedDataManager.save_data(BANNED_FILE, self.banned_users)
    
    def ban_user(self, user_id: int, reason: str = "") -> bool:
        """حظر مستخدم"""
        try:
            user_data = self.get_user(user_id)
            user_data["banned"] = True
            user_data["ban_reason"] = reason
            user_data["ban_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.banned_users[str(user_id)] = user_data
            
            # إزالة من المستخدمين النشطين
            if str(user_id) in self.users:
                del self.users[str(user_id)]
            
            self.save_banned()
            self.save_users()
            
            logger.info(f"🚫 تم حظر المستخدم {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في حظر المستخدم: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """رفع الحظر عن مستخدم"""
        try:
            if str(user_id) in self.banned_users:
                user_data = self.banned_users[str(user_id)]
                user_data["banned"] = False
                user_data["unban_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # إعادة إلى المستخدمين النشطين
                self.users[str(user_id)] = user_data
                del self.banned_users[str(user_id)]
                
                self.save_banned()
                self.save_users()
                
                logger.info(f"✅ تم رفع الحظر عن المستخدم {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في رفع الحظر: {e}")
            return False

# ============= إدارة المواد التعليمية المحسنة =============
class EnhancedMaterialsManager:
    """مدير مواد تعليمية محسن"""
    
    def __init__(self):
        self.materials = EnhancedDataManager.load_data(MATERIALS_FILE, [])
        self._cleanup_materials()
    
    def _cleanup_materials(self):
        """تنظيف البيانات القديمة أو التالفة"""
        cleaned_materials = []
        
        for material in self.materials:
            if isinstance(material, dict) and material.get("id"):
                # تأكد من وجود جميع الحقول الأساسية
                required_fields = ["name", "description", "stage", "file_id", "added_date"]
                for field in required_fields:
                    if field not in material:
                        material[field] = ""
                
                cleaned_materials.append(material)
        
        if len(cleaned_materials) != len(self.materials):
            self.materials = cleaned_materials
            self.save_materials()
            logger.info(f"🧹 تم تنظيف {len(self.materials) - len(cleaned_materials)} مادة تالفة")
    
    def get_materials_by_stage(self, stage: str) -> List[Dict]:
        """الحصول على مواد حسب المرحلة"""
        return [m for m in self.materials if m.get("stage", "").lower() == stage.lower()]
    
    def get_all_stages(self) -> List[str]:
        """الحصول على جميع المراحل"""
        stages = set()
        for m in self.materials:
            stage = m.get("stage", "")
            if stage and stage not in ["", "غير محدد"]:
                stages.add(stage)
        
        return sorted(list(stages))
    
    def add_material(self, material_data: Dict) -> int:
        """إضافة مادة جديدة"""
        try:
            # توليد ID فريد
            material_id = max([m.get("id", 0) for m in self.materials] + [0]) + 1
            
            material_data["id"] = material_id
            material_data["added_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            material_data["downloads"] = 0
            material_data["views"] = 0
            
            # التأكد من وجود اسم
            if "name" not in material_data or not material_data["name"]:
                material_data["name"] = f"مادة {material_id}"
            
            self.materials.append(material_data)
            self.save_materials()
            
            logger.info(f"✅ تم إضافة مادة: {material_data.get('name')} (ID: {material_id})")
            return material_id
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة مادة: {e}")
            return -1
    
    def delete_material(self, material_id: int) -> bool:
        """حذف مادة"""
        try:
            original_count = len(self.materials)
            
            # البحث عن المادة وحذفها
            for i, material in enumerate(self.materials):
                if material.get("id") == material_id:
                    del self.materials[i]
                    self.save_materials()
                    
                    logger.info(f"🗑️ تم حذف مادة ID: {material_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف مادة: {e}")
            return False
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """الحصول على مادة بواسطة الـ ID"""
        for material in self.materials:
            if material.get("id") == material_id:
                return material
        return None
    
    def increment_downloads(self, material_id: int) -> bool:
        """زيادة عدد مرات التحميل"""
        for material in self.materials:
            if material.get("id") == material_id:
                material["downloads"] = material.get("downloads", 0) + 1
                self.save_materials()
                return True
        return False
    
    def save_materials(self):
        """حفظ المواد"""
        EnhancedDataManager.save_data(MATERIALS_FILE, self.materials)

# ============= إدارة الأسئلة المحسنة =============
class EnhancedQuestionsManager:
    """مدير أسئلة محسن"""
    
    def __init__(self):
        self.questions = EnhancedDataManager.load_data(QUESTIONS_FILE, [])
        self._cleanup_questions()
    
    def _cleanup_questions(self):
        """تنظيف الأسئلة القديمة"""
        cutoff_date = datetime.now() - timedelta(days=30)  # 30 يوم
        cleaned_questions = []
        
        for question in self.questions:
            try:
                if isinstance(question, dict) and question.get("id"):
                    # تحقق من تاريخ السؤال
                    question_date = datetime.strptime(question.get("date", "2000-01-01"), "%Y-%m-%d %H:%M:%S")
                    
                    if question_date > cutoff_date:
                        cleaned_questions.append(question)
            except:
                continue
        
        if len(cleaned_questions) != len(self.questions):
            self.questions = cleaned_questions
            self.save_questions()
            logger.info(f"🧹 تم تنظيف {len(self.questions) - len(cleaned_questions)} سؤال قديم")
    
    def add_question(self, user_id: int, question_text: str) -> str:
        """إضافة سؤال جديد"""
        try:
            # توليد ID فريد
            question_id = str(uuid.uuid4())[:8].upper()
            
            question_data = {
                "id": question_id,
                "user_id": user_id,
                "question": question_text[:1000],  # حد 1000 حرف
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "answers": [],
                "answered": False,
                "views": 0,
                "status": "active",
                "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.questions.append(question_data)
            self.save_questions()
            
            logger.info(f"❓ تم إضافة سؤال {question_id} بواسطة المستخدم {user_id}")
            return question_id
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة سؤال: {e}")
            return ""
    
    def add_answer(self, question_id: str, answerer_id: int, answer_text: str) -> Tuple[bool, Optional[int]]:
        """إضافة إجابة لسؤال"""
        try:
            for question in self.questions:
                if question["id"] == question_id and question.get("status") == "active":
                    answer_data = {
                        "answerer_id": answerer_id,
                        "answer": answer_text[:2000],  # حد 2000 حرف
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "helpful": 0,
                        "not_helpful": 0
                    }
                    
                    question["answers"].append(answer_data)
                    question["answered"] = True
                    question["status"] = "answered"
                    question["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    self.save_questions()
                    
                    logger.info(f"💡 تمت الإجابة على السؤال {question_id} بواسطة {answerer_id}")
                    return True, question["user_id"]
            
            return False, None
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة إجابة: {e}")
            return False, None
    
    def get_active_questions(self, exclude_user_id: int = None) -> List[Dict]:
        """الحصول على الأسئلة النشطة"""
        active_questions = []
        
        for question in self.questions:
            if question.get("status") == "active" and not question.get("answered", False):
                if exclude_user_id and question.get("user_id") == exclude_user_id:
                    continue
                
                active_questions.append(question)
                
                # تحديث عدد المشاهدات
                question["views"] = question.get("views", 0) + 1
        
        # الحفظ بعد تحديث المشاهدات
        if active_questions:
            self.save_questions()
        
        # ترتيب حسب الأحدث
        active_questions.sort(key=lambda x: x.get("date", ""), reverse=True)
        return active_questions[:20]  # حد 20 سؤال
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """الحصول على سؤال بواسطة الـ ID"""
        for question in self.questions:
            if question["id"] == question_id:
                return question
        return None
    
    def remove_old_questions(self, days: int = 30):
        """إزالة الأسئلة القديمة"""
        cutoff_date = datetime.now() - timedelta(days=days)
        original_count = len(self.questions)
        
        self.questions = [
            q for q in self.questions 
            if datetime.strptime(q.get("date", "2000-01-01"), "%Y-%m-%d %H:%M:%S") > cutoff_date
        ]
        
        if len(self.questions) < original_count:
            self.save_questions()
            logger.info(f"🧹 تم إزالة {original_count - len(self.questions)} سؤال قديم")
    
    def mark_as_helpful(self, question_id: str, answer_index: int, helpful: bool = True) -> bool:
        """تقييم الإجابة كمفيدة"""
        for question in self.questions:
            if question["id"] == question_id and answer_index < len(question.get("answers", [])):
                if helpful:
                    question["answers"][answer_index]["helpful"] = question["answers"][answer_index].get("helpful", 0) + 1
                else:
                    question["answers"][answer_index]["not_helpful"] = question["answers"][answer_index].get("not_helpful", 0) + 1
                
                self.save_questions()
                return True
        
        return False
    
    def save_questions(self):
        """حفظ الأسئلة"""
        EnhancedDataManager.save_data(QUESTIONS_FILE, self.questions)

# ============= إدارة نظام VIP المحسن =============
class EnhancedVIPManager:
    """مدير نظام VIP محسن"""
    
    def __init__(self):
        self.vip_data = EnhancedDataManager.load_data(VIP_FILE, {
            "subscription_price": 5000,
            "teachers": [],
            "pending_lectures": [],
            "approved_lectures": [],
            "banned_teachers": [],
            "settings": {
                "min_lecture_price": 0,
                "max_lecture_price": 100000,
                "teacher_share_percentage": 50,
                "admin_share_percentage": 50,
                "auto_approve": False
            }
        })
        
        self.lectures = EnhancedDataManager.load_data(VIP_LECTURES_FILE, [])
        self.purchases = EnhancedDataManager.load_data(VIP_PURCHASES_FILE, [])
        
        self._cleanup_data()
    
    def _cleanup_data(self):
        """تنظيف البيانات التالفة"""
        # تنظيف المحاضرات
        cleaned_lectures = []
        for lecture in self.lectures:
            if isinstance(lecture, dict) and lecture.get("id"):
                # التأكد من وجود جميع الحقول
                required_fields = ["title", "description", "teacher_id", "price", "status"]
                for field in required_fields:
                    if field not in lecture:
                        if field == "price":
                            lecture[field] = 0
                        elif field == "status":
                            lecture[field] = "pending"
                        else:
                            lecture[field] = ""
                
                cleaned_lectures.append(lecture)
        
        if len(cleaned_lectures) != len(self.lectures):
            self.lectures = cleaned_lectures
            EnhancedDataManager.save_data(VIP_LECTURES_FILE, self.lectures)
        
        # تنظيف عمليات الشراء
        cleaned_purchases = []
        for purchase in self.purchases:
            if isinstance(purchase, dict) and purchase.get("id"):
                cleaned_purchases.append(purchase)
        
        if len(cleaned_purchases) != len(self.purchases):
            self.purchases = cleaned_purchases
            EnhancedDataManager.save_data(VIP_PURCHASES_FILE, self.purchases)
    
    def add_lecture(self, teacher_id: int, title: str, description: str, file_info: Dict, price: int = 0) -> str:
        """إضافة محاضرة جديدة"""
        try:
            # التحقق من البيانات
            if not title or len(title) < 3:
                raise ValidationError("عنوان المحاضرة قصير جداً")
            
            if price < 0:
                raise ValidationError("السعر لا يمكن أن يكون سالباً")
            
            # توليد ID فريد
            lecture_id = str(uuid.uuid4())[:8].upper()
            
            lecture_data = {
                "id": lecture_id,
                "teacher_id": teacher_id,
                "title": title[:200],  # حد 200 حرف
                "description": description[:1000],  # حد 1000 حرف
                "file_info": file_info,
                "price": price,
                "status": "pending",
                "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "approved_date": None,
                "rejection_reason": None,
                "views": 0,
                "downloads": 0,
                "sales": 0,
                "earnings": 0,
                "rating": 0,
                "reviews": [],
                "tags": [],
                "category": "عام"
            }
            
            self.lectures.append(lecture_data)
            
            # إضافة إلى قائمة الانتظار
            if lecture_id not in self.vip_data["pending_lectures"]:
                self.vip_data["pending_lectures"].append(lecture_id)
            
            # الموافقة التلقائية إذا مفعلة
            if self.vip_data["settings"].get("auto_approve", False):
                self.approve_lecture(lecture_id, "موافقة تلقائية")
            else:
                self.save_all_data()
            
            logger.info(f"📤 تم إضافة محاضرة {lecture_id} بواسطة المعلم {teacher_id}")
            return lecture_id
            
        except ValidationError as e:
            logger.error(f"❌ خطأ في التحقق: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة محاضرة: {e}")
            return ""
    
    def approve_lecture(self, lecture_id: str, approval_note: str = "") -> bool:
        """الموافقة على محاضرة"""
        for lecture in self.lectures:
            if lecture["id"] == lecture_id and lecture["status"] == "pending":
                lecture["status"] = "approved"
                lecture["approved_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lecture["approval_note"] = approval_note
                
                # تحديث القوائم
                if lecture_id in self.vip_data["pending_lectures"]:
                    self.vip_data["pending_lectures"].remove(lecture_id)
                
                if lecture_id not in self.vip_data["approved_lectures"]:
                    self.vip_data["approved_lectures"].append(lecture_id)
                
                self.save_all_data()
                
                logger.info(f"✅ تمت الموافقة على المحاضرة {lecture_id}")
                return True
        
        return False
    
    def reject_lecture(self, lecture_id: str, rejection_reason: str) -> bool:
        """رفض محاضرة"""
        for lecture in self.lectures:
            if lecture["id"] == lecture_id and lecture["status"] == "pending":
                lecture["status"] = "rejected"
                lecture["rejection_reason"] = rejection_reason
                lecture["rejected_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # تحديث القوائم
                if lecture_id in self.vip_data["pending_lectures"]:
                    self.vip_data["pending_lectures"].remove(lecture_id)
                
                self.save_all_data()
                
                logger.info(f"❌ تم رفض المحاضرة {lecture_id}: {rejection_reason}")
                return True
        
        return False
    
    def delete_lecture(self, lecture_id: str, deleter_id: int, is_admin: bool = False) -> bool:
        """حذف محاضرة"""
        for i, lecture in enumerate(self.lectures):
            if lecture["id"] == lecture_id:
                # التحقق من الصلاحية
                if not is_admin and lecture["teacher_id"] != deleter_id:
                    return False
                
                # تسجيل عملية الحذف
                lecture["deleted"] = True
                lecture["deleted_by"] = deleter_id
                lecture["deleted_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # إزالة من القوائم
                for key in ["pending_lectures", "approved_lectures"]:
                    if lecture_id in self.vip_data[key]:
                        self.vip_data[key].remove(lecture_id)
                
                self.save_all_data()
                
                logger.info(f"🗑️ تم حذف المحاضرة {lecture_id} بواسطة {deleter_id}")
                return True
        
        return False
    
    def get_pending_lectures(self) -> List[Dict]:
        """الحصول على المحاضرات قيد المراجعة"""
        return [lecture for lecture in self.lectures if lecture.get("status") == "pending" and not lecture.get("deleted")]
    
    def get_approved_lectures(self) -> List[Dict]:
        """الحصول على المحاضرات المعتمدة"""
        return [lecture for lecture in self.lectures if lecture.get("status") == "approved" and not lecture.get("deleted")]
    
    def get_teacher_lectures(self, teacher_id: int, include_deleted: bool = False) -> List[Dict]:
        """الحصول على محاضرات معلم"""
        lectures = []
        for lecture in self.lectures:
            if lecture["teacher_id"] == teacher_id:
                if not lecture.get("deleted") or include_deleted:
                    lectures.append(lecture)
        
        return lectures
    
    def get_lecture_by_id(self, lecture_id: str) -> Optional[Dict]:
        """الحصول على محاضرة بواسطة الـ ID"""
        for lecture in self.lectures:
            if lecture["id"] == lecture_id and not lecture.get("deleted"):
                return lecture
        return None
    
    def ban_teacher(self, teacher_id: int, reason: str = "") -> bool:
        """حظر معلم"""
        if teacher_id not in self.vip_data["banned_teachers"]:
            self.vip_data["banned_teachers"].append({
                "teacher_id": teacher_id,
                "ban_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reason": reason,
                "banned_by": ADMIN_ID
            })
            
            self.save_all_data()
            logger.info(f"🚫 تم حظر المعلم {teacher_id}: {reason}")
            return True
        
        return False
    
    def unban_teacher(self, teacher_id: int) -> bool:
        """رفع الحظر عن معلم"""
        for i, banned_teacher in enumerate(self.vip_data["banned_teachers"]):
            if banned_teacher["teacher_id"] == teacher_id:
                self.vip_data["banned_teachers"].pop(i)
                self.save_all_data()
                logger.info(f"✅ تم رفع الحظر عن المعلم {teacher_id}")
                return True
        
        return False
    
    def purchase_lecture(self, student_id: int, lecture_id: str, price: int) -> Tuple[bool, Optional[int]]:
        """شراء محاضرة"""
        lecture = self.get_lecture_by_id(lecture_id)
        if not lecture or lecture["status"] != "approved":
            return False, None
        
        teacher_id = lecture["teacher_id"]
        
        # تسجيل عملية الشراء
        purchase_id = str(uuid.uuid4())[:8].upper()
        purchase_data = {
            "id": purchase_id,
            "lecture_id": lecture_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "price": price,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "teacher_share": int(price * (self.vip_data["settings"]["teacher_share_percentage"] / 100)),
            "admin_share": int(price * (self.vip_data["settings"]["admin_share_percentage"] / 100)),
            "status": "completed"
        }
        
        self.purchases.append(purchase_data)
        
        # تحديث إحصائيات المحاضرة
        lecture["sales"] = lecture.get("sales", 0) + 1
        lecture["earnings"] = lecture.get("earnings", 0) + price
        lecture["downloads"] = lecture.get("downloads", 0) + 1
        
        self.save_all_data()
        logger.info(f"🛒 تم شراء المحاضرة {lecture_id} بواسطة الطالب {student_id} مقابل {price} دينار")
        
        return True, teacher_id
    
    def get_student_purchases(self, student_id: int) -> List[Dict]:
        """الحصول على مشتريات طالب"""
        return [purchase for purchase in self.purchases if purchase["student_id"] == student_id]
    
    def update_subscription_price(self, price: int):
        """تحديث سعر الاشتراك"""
        if price < 0:
            raise ValidationError("السعر لا يمكن أن يكون سالباً")
        
        self.vip_data["subscription_price"] = price
        self.save_all_data()
    
    def get_subscription_price(self) -> int:
        """الحصول على سعر الاشتراك"""
        return self.vip_data.get("subscription_price", 5000)
    
    def save_all_data(self):
        """حفظ جميع البيانات"""
        EnhancedDataManager.save_data(VIP_FILE, self.vip_data)
        EnhancedDataManager.save_data(VIP_LECTURES_FILE, self.lectures)
        EnhancedDataManager.save_data(VIP_PURCHASES_FILE, self.purchases)

# ============= إدارة القناة والخدمات المحسنة =============
class EnhancedSettingsManager:
    """مدير إعدادات محسن"""
    
    def __init__(self):
        self.channel_info = EnhancedDataManager.load_data(CHANNEL_FILE, {
            "channel_link": "https://t.me/FCJCV",
            "channel_id": None,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "join_required": True
        })
        
        self.services_status = EnhancedDataManager.load_data(SERVICES_FILE, DEFAULT_SERVICES.copy())
        
        self.admin_settings = EnhancedDataManager.load_data(ADMIN_FILE, {
            "maintenance": False,
            "maintenance_message": "البوت قيد الصيانة حالياً. الرجاء المحاولة لاحقاً.",
            "prices": DEFAULT_PRICES.copy(),
            "welcome_bonus": WELCOME_BONUS,
            "referral_bonus": REFERRAL_BONUS,
            "answer_reward": ANSWER_REWARD,
            "notify_new_users": True,
            "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "auto_backup": True,
            "backup_interval_hours": 24
        })
    
    def get_channel_link(self) -> str:
        """الحصول على رابط القناة"""
        return self.channel_info.get("channel_link", "https://t.me/FCJCV")
    
    def update_channel_link(self, new_link: str):
        """تحديث رابط القناة"""
        if not new_link.startswith("https://t.me/"):
            raise ValidationError("رابط القناة يجب أن يبدأ بـ https://t.me/")
        
        self.channel_info["channel_link"] = new_link
        self.channel_info["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_channel_info()
    
    def is_service_active(self, service: str) -> bool:
        """التحقق من نشاط خدمة"""
        service_data = self.services_status.get(service, {})
        return service_data.get("active", True)
    
    def toggle_service(self, service: str) -> bool:
        """تبديل حالة الخدمة"""
        if service in self.services_status:
            current_status = self.services_status[service].get("active", True)
            self.services_status[service]["active"] = not current_status
            self.save_services_status()
            return not current_status
        return False
    
    def add_service(self, service_key: str, service_name: str, description: str, price: int = 1000) -> bool:
        """إضافة خدمة جديدة"""
        if service_key in self.services_status:
            return False
        
        self.services_status[service_key] = {
            "active": True,
            "name": service_name,
            "description": description,
            "price": price
        }
        
        # إضافة السعر الافتراضي
        self.admin_settings["prices"][service_key] = price
        
        self.save_services_status()
        self.save_admin_settings()
        
        logger.info(f"➕ تم إضافة خدمة جديدة: {service_name}")
        return True
    
    def remove_service(self, service_key: str) -> bool:
        """إزالة خدمة"""
        if service_key in self.services_status:
            del self.services_status[service_key]
            
            # إزالة السعر
            if service_key in self.admin_settings.get("prices", {}):
                del self.admin_settings["prices"][service_key]
            
            self.save_services_status()
            self.save_admin_settings()
            
            logger.info(f"➖ تم إزالة خدمة: {service_key}")
            return True
        
        return False
    
    def get_active_services(self) -> Dict[str, Dict]:
        """الحصول على الخدمات النشطة"""
        return {k: v for k, v in self.services_status.items() if v.get("active", True)}
    
    def get_all_services(self) -> Dict[str, Dict]:
        """الحصول على جميع الخدمات"""
        return self.services_status.copy()
    
    def get_price(self, service: str) -> int:
        """الحصول على سعر خدمة"""
        return self.admin_settings.get("prices", {}).get(service, 1000)
    
    def update_price(self, service: str, price: int):
        """تحديث سعر خدمة"""
        if price < 0:
            raise ValidationError("السعر لا يمكن أن يكون سالباً")
        
        if "prices" not in self.admin_settings:
            self.admin_settings["prices"] = {}
        
        self.admin_settings["prices"][service] = price
        self.save_admin_settings()
    
    def get_welcome_bonus(self) -> int:
        """الحصول على الهدية الترحيبية"""
        return self.admin_settings.get("welcome_bonus", WELCOME_BONUS)
    
    def update_welcome_bonus(self, amount: int):
        """تحديث الهدية الترحيبية"""
        if amount < 0:
            raise ValidationError("مبلغ الهدية لا يمكن أن يكون سالباً")
        
        self.admin_settings["welcome_bonus"] = amount
        self.save_admin_settings()
    
    def get_referral_bonus(self) -> int:
        """الحصول على مكافأة الإحالة"""
        return self.admin_settings.get("referral_bonus", REFERRAL_BONUS)
    
    def update_referral_bonus(self, amount: int):
        """تحديث مكافأة الإحالة"""
        if amount < 0:
            raise ValidationError("مبلغ المكافأة لا يمكن أن يكون سالباً")
        
        self.admin_settings["referral_bonus"] = amount
        self.save_admin_settings()
    
    def get_answer_reward(self) -> int:
        """الحصول على مكافأة الإجابة"""
        return self.admin_settings.get("answer_reward", ANSWER_REWARD)
    
    def update_answer_reward(self, amount: int):
        """تحديث مكافأة الإجابة"""
        if amount < 0:
            raise ValidationError("مبلغ المكافأة لا يمكن أن يكون سالباً")
        
        self.admin_settings["answer_reward"] = amount
        self.save_admin_settings()
    
    def is_maintenance_mode(self) -> bool:
        """التحقق من وضع الصيانة"""
        return self.admin_settings.get("maintenance", False)
    
    def set_maintenance_mode(self, enabled: bool, message: str = ""):
        """تعيين وضع الصيانة"""
        self.admin_settings["maintenance"] = enabled
        if message:
            self.admin_settings["maintenance_message"] = message
        self.save_admin_settings()
    
    def save_channel_info(self):
        """حفظ معلومات القناة"""
        EnhancedDataManager.save_data(CHANNEL_FILE, self.channel_info)
    
    def save_services_status(self):
        """حفظ حالة الخدمات"""
        EnhancedDataManager.save_data(SERVICES_FILE, self.services_status)
    
    def save_admin_settings(self):
        """حفظ الإعدادات الإدارية"""
        EnhancedDataManager.save_data(ADMIN_FILE, self.admin_settings)

# ============= الفئة الرئيسية للبوت المحسن =============
class EnhancedYallaNataalamBot:
    """البوت التعليمي المحسن"""
    
    def __init__(self):
        # تهيئة المدراء
        self.user_manager = EnhancedUserManager()
        self.materials_manager = EnhancedMaterialsManager()
        self.questions_manager = EnhancedQuestionsManager()
        self.settings_manager = EnhancedSettingsManager()
        self.vip_manager = EnhancedVIPManager()
        
        # تهيئة الخدمات
        self.ai_service = EnhancedAIService(GEMINI_API_KEY)
        self.referral_system = ReferralSystem(EnhancedDataManager, self.user_manager)
        self.notification_system = NotificationSystem(EnhancedDataManager, self.user_manager)
        
        # ربط المدراء
        self.user_manager.settings_manager = self.settings_manager
        self.settings_manager.vip_manager = self.vip_manager
        
        # متغيرات الحالة
        self.is_running = False
        self.backup_task = None
        
        logger.info("=" * 60)
        logger.info("🤖 بوت 'يلا نتعلم' التعليمي - الإصدار المحسن 3.0")
        logger.info("=" * 60)
        logger.info(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        logger.info(f"💎 الهدية: {self.settings_manager.get_welcome_bonus():,} دينار")
        logger.info(f"👑 VIP الاشتراك: {self.vip_manager.get_subscription_price():,} دينار شهرياً")
        logger.info(f"🤖 الذكاء الاصطناعي: {'✅' if self.ai_service.is_initialized else '❌'}")
        logger.info("=" * 60)
    
    async def send_notification(self, user_id: int, message: str, context: ContextTypes.DEFAULT_TYPE):
        """إرسال إشعار"""
        return await self.notification_system.send_notification(user_id, message, context)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء المحادثة"""
        user = update.effective_user
        
        # التحقق من وضع الصيانة
        if self.settings_manager.is_maintenance_mode():
            maintenance_message = self.settings_manager.admin_settings.get("maintenance_message", 
                                                                         "البوت قيد الصيانة حالياً. الرجاء المحاولة لاحقاً.")
            await update.message.reply_text(maintenance_message, parse_mode=ParseMode.HTML)
            return
        
        # تحديث معلومات المستخدم
        self.user_manager.update_user_info(user.id, user.first_name, user.username)
        user_data = self.user_manager.get_user(user.id)
        
        # التحقق من الإحالة
        if context.args and len(context.args) > 0:
            ref_arg = context.args[0]
            if ref_arg.startswith("ref"):
                try:
                    referrer_id = int(ref_arg[3:])
                    if referrer_id != user.id:
                        success, message = self.referral_system.register_referral(referrer_id, user.id)
                        if success:
                            await self.send_notification(
                                referrer_id,
                                f"🎉 <b>تمت إحالة جديدة!</b>\n\n👤 <b>المستخدم الجديد:</b> {user.first_name}\n💰 <b>المكافأة:</b> {self.settings_manager.get_referral_bonus():,} دينار",
                                context
                            )
                except:
                    pass
        
        welcome_message = f"""
🎓 <b>مرحباً {user.first_name}!</b>

أهلاً بك في بوت "يلا نتعلم" التعليمي 📚

🆔 <b>رقم حسابك:</b> <code>{user.id}</code>
💰 <b>رصيدك الحالي:</b> {user_data['balance']:,} دينار

🎁 <b>هدية ترحيبية:</b> {self.settings_manager.get_welcome_bonus():,} دينار

📝 <b>لشحن الرصيد:</b>
1. انسخ رقم حسابك أعلاه 👆
2. راسل الدعم الفني: @{SUPPORT_USERNAME}
3. أرسل رقم حسابك والمبلغ المطلوب

اختر الخدمة التي تريدها:
"""
        
        keyboard = []
        active_services = self.settings_manager.get_active_services()
        
        # إضافة الخدمات النشطة
        row = []
        for service_key, service_data in active_services.items():
            if service_key in ["exemption", "summarize", "qa", "materials", "help_student"]:
                price = self.settings_manager.get_price(service_key)
                button_text = f"{service_data['name']} ({price:,} د)"
                callback_data = f"service_{service_key}"
                
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        if row:
            keyboard.append(row)
        
        # إضافة خدمات VIP
        if self.settings_manager.is_service_active("vip_lectures"):
            keyboard.append([InlineKeyboardButton("👑 محاضرات VIP", callback_data="vip_lectures_store")])
        
        # إضافة الأزرار الأساسية
        keyboard.append([
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
            InlineKeyboardButton("❓ أسئلة الطلاب", callback_data="student_questions")
        ])
        
        keyboard.append([
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite_friends"),
            InlineKeyboardButton("📢 قناة البوت", url=self.settings_manager.get_channel_link())
        ])
        
        keyboard.append([
            InlineKeyboardButton("👑 اشتراك VIP", callback_data="vip_subscription_info"),
            InlineKeyboardButton("🆘 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}")
        ])
        
        # زر لوحة التحكم للمدير
        if user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    # ============= قسم تلخيص الملازم =============
    async def handle_service_summarize(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالجة خدمة تلخيص الملازم"""
        user_id = query.from_user.id
        
        if not self.settings_manager.is_service_active("summarize"):
            await query.edit_message_text(
                "⏸️ <b>هذه الخدمة غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                f"📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("summarize")
        
        if user_data['balance'] < price:
            await query.edit_message_text(
                f"❌ <b>رصيدك غير كافي!</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                f"🆔 <b>رقم حسابك للشحن:</b> <code>{user_id}</code>\n\n"
                f"📞 تواصل مع الدعم الفني: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        self.user_manager.set_pending_purchase(user_id, "summarize", price)
        
        await query.edit_message_text(
            "📤 <b>أرسل ملف PDF المراد تلخيصه</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "⏳ قد تستغرق العملية بضع دقائق\n"
            "⚠️ <b>سيتم خصم المبلغ بعد إتمام الخدمة</b>",
            parse_mode=ParseMode.HTML
        )
        
        return SUMMARIZE_PDF
    
    async def handle_summarize_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ملف PDF للتلخيص"""
        user_id = update.effective_user.id
        
        if not update.message.document:
            await update.message.reply_text("❌ <b>يرجى إرسال ملف PDF فقط</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return SUMMARIZE_PDF
        
        document = update.message.document
        
        if not document.mime_type == 'application/pdf':
            await update.message.reply_text("❌ <b>يرجى إرسال ملف PDF فقط</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return SUMMARIZE_PDF
        
        processing_msg = await update.message.reply_text("⏳ <b>جاري معالجة الملف...</b>", parse_mode=ParseMode.HTML)
        
        try:
            # تحميل الملف
            file = await document.get_file()
            pdf_path = TEMP_DIR / f"temp_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # استخدم aiofiles إذا كان متاحاً
            if HAS_AIOFILES:
                async with aiofiles.open(pdf_path, 'wb') as f:
                    content = await file.download_as_bytearray()
                    await f.write(content)
            else:
                await file.download_to_drive(pdf_path)
            
            await processing_msg.edit_text("📖 <b>جاري قراءة الملف...</b>", parse_mode=ParseMode.HTML)
            
            # قراءة وتلخيص الملف
            summary = await self.ai_service.summarize_pdf(pdf_path)
            
            if summary.startswith("❌"):
                await processing_msg.edit_text(f"{summary}\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                os.remove(pdf_path)
                self.user_manager.cancel_purchase(user_id)
                return ConversationHandler.END
            
            await processing_msg.edit_text("📄 <b>جاري إنشاء ملف PDF جديد...</b>", parse_mode=ParseMode.HTML)
            
            # إنشاء ملف PDF للتلخيص
            output_path = TEMP_DIR / f"summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            success = self.ai_service.create_summary_pdf("ملف PDF", summary, output_path)
            
            if success and output_path.exists():
                if self.user_manager.complete_purchase(user_id):
                    price = self.settings_manager.get_price("summarize")
                    new_balance = self.user_manager.update_balance(user_id, -price, f"تلخيص ملف PDF")
                    
                    # إرسال الملف
                    await update.message.reply_document(
                        document=open(output_path, 'rb'),
                        filename=f"تلخيص_{document.file_name or 'ملف.pdf'}",
                        caption=f"✅ <b>تم تلخيص الملزمة بنجاح</b>\n\n"
                               f"📊 <b>ملخص التلخيص:</b>\n{summary[:300]}...\n\n"
                               f"💰 تم خصم: {price:,} دينار\n"
                               f"💳 رصيدك المتبقي: {new_balance:,} دينار",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # تنظيف الملفات المؤقتة
                    try:
                        os.remove(pdf_path)
                        os.remove(output_path)
                    except:
                        pass
                    
                    keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("🔙", reply_markup=reply_markup)
                else:
                    await processing_msg.edit_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
                    try:
                        os.remove(pdf_path)
                        if output_path.exists():
                            os.remove(output_path)
                    except:
                        pass
            else:
                await processing_msg.edit_text("❌ <b>فشل في إنشاء ملف PDF</b>\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                try:
                    os.remove(pdf_path)
                except:
                    pass
                self.user_manager.cancel_purchase(user_id)
        
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة PDF: {e}")
            await processing_msg.edit_text("❌ <b>حدث خطأ في معالجة الملف</b>\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        
        return ConversationHandler.END
    
    # ============= قسم سؤال وجواب بالذكاء =============
    async def handle_service_qa(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالجة خدمة سؤال وجواب"""
        user_id = query.from_user.id
        
        if not self.settings_manager.is_service_active("qa"):
            await query.edit_message_text(
                "⏸️ <b>هذه الخدمة غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                f"📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("qa")
        
        if user_data['balance'] < price:
            await query.edit_message_text(
                f"❌ <b>رصيدك غير كافي!</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                f"🆔 <b>رقم حسابك للشحن:</b> <code>{user_id}</code>\n\n"
                f"📞 تواصل مع الدعم الفني: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        self.user_manager.set_pending_purchase(user_id, "qa", price)
        
        await query.edit_message_text(
            "❓ <b>أرسل سؤالك الآن</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "⏳ جاهز للإجابة على أسئلتك\n"
            "⚠️ <b>سيتم خصم المبلغ بعد إتمام الخدمة</b>",
            parse_mode=ParseMode.HTML
        )
        
        return QA_QUESTION
    
    async def handle_qa_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة السؤال"""
        user_id = update.effective_user.id
        
        question = update.message.text.strip()
        
        if len(question) < 5:
            await update.message.reply_text("❌ <b>السؤال قصير جداً</b>\n\nيرجى كتابة سؤال مفصل", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return QA_QUESTION
        
        processing_msg = await update.message.reply_text("🤖 <b>جاري البحث عن الإجابة...</b>", parse_mode=ParseMode.HTML)
        
        try:
            answer = await self.ai_service.answer_question(question)
            
            if answer.startswith("❌"):
                await processing_msg.edit_text(f"{answer}\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                self.user_manager.cancel_purchase(user_id)
                return ConversationHandler.END
            
            if self.user_manager.complete_purchase(user_id):
                price = self.settings_manager.get_price("qa")
                new_balance = self.user_manager.update_balance(user_id, -price, f"سؤال وجواب بالذكاء")
                
                await processing_msg.edit_text(
                    f"❓ <b>سؤالك:</b>\n{question}\n\n"
                    f"💡 <b>الإجابة:</b>\n{answer[:2000]}\n\n"
                    f"💰 تم خصم: {price:,} دينار\n"
                    f"💳 رصيدك المتبقي: {new_balance:,} دينار",
                    parse_mode=ParseMode.HTML
                )
                
                keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("🔙", reply_markup=reply_markup)
            else:
                await processing_msg.edit_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
                self.user_manager.cancel_purchase(user_id)
        
        except Exception as e:
            logger.error(f"❌ خطأ في الإجابة على السؤال: {e}")
            await processing_msg.edit_text("❌ <b>حدث خطأ في الإجابة</b>\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        
        return ConversationHandler.END
    
    # ============= قسم ساعدوني طلاب =============
    async def handle_service_help_student(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالجة خدمة ساعدوني طلاب"""
        user_id = query.from_user.id
        
        if not self.settings_manager.is_service_active("help_student"):
            await query.edit_message_text(
                "⏸️ <b>هذه الخدمة غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                f"📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        can_ask, message = self.user_manager.can_ask_question(user_id)
        if not can_ask:
            await query.edit_message_text(
                f"⏳ <b>لا يمكنك طرح سؤال جديد الآن</b>\n\n{message}\n\n"
                f"💡 يمكنك الإجابة على أسئلة الآخرين وكسب {self.settings_manager.get_answer_reward():,} نقطة",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("help_student")
        
        if user_data['balance'] < price:
            await query.edit_message_text(
                f"❌ <b>رصيدك غير كافي!</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                f"🆔 <b>رقم حسابك للشحن:</b> <code>{user_id}</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        self.user_manager.set_pending_purchase(user_id, "help_student", price)
        
        await query.edit_message_text(
            "🤝 <b>ساعدوني طلاب</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "📝 <b>أرسل سؤالك الآن:</b>\n"
            "• يمكنك إرسال نص فقط\n"
            "• السؤال يجب أن يكون متعلقاً بالدراسة\n"
            "• سوف يتم خصم المبلغ بعد إرسال السؤال\n\n"
            "⚠️ <b>ملاحظة:</b> يمكنك طرح سؤال واحد كل 24 ساعة\n"
            f"🎯 <b>المكافأة للمجيب:</b> {self.settings_manager.get_answer_reward():,} نقطة",
            parse_mode=ParseMode.HTML
        )
        
        return HELP_STUDENT_QUESTION
    
    async def handle_help_student_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة سؤال ساعدوني طلاب"""
        user_id = update.effective_user.id
        
        question_text = update.message.text.strip()
        
        if len(question_text) < 10:
            await update.message.reply_text("❌ <b>السؤال قصير جداً</b>\n\nيرجى كتابة سؤال مفصل", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return HELP_STUDENT_QUESTION
        
        if self.user_manager.complete_purchase(user_id):
            price = self.settings_manager.get_price("help_student")
            new_balance = self.user_manager.update_balance(user_id, -price, f"طرح سؤال في ساعدوني طلاب")
            
            self.user_manager.update_question_time(user_id)
            
            question_id = self.questions_manager.add_question(user_id, question_text)
            
            await update.message.reply_text(
                f"✅ <b>تم إضافة سؤالك بنجاح!</b>\n\n"
                f"🆔 <b>رقم السؤال:</b> {question_id}\n"
                f"💰 <b>تم خصم:</b> {price:,} دينار\n"
                f"💳 <b>رصيدك المتبقي:</b> {new_balance:,} دينار\n\n"
                f"⏳ <b>الحالة:</b> في انتظار الإجابة\n"
                f"🎯 <b>المكافأة للمجيب:</b> {self.settings_manager.get_answer_reward():,} نقطة\n\n"
                f"💡 سوف تتلقى إشعاراً عندما يتم الرد على سؤالك",
                parse_mode=ParseMode.HTML
            )
            
            await self.show_student_questions_internal(update, context, user_id)
        else:
            await update.message.reply_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        
        return ConversationHandler.END
    
    async def show_student_questions_internal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, exclude_user_id: int = None):
        """عرض أسئلة الطلاب"""
        try:
            active_questions = self.questions_manager.get_active_questions(exclude_user_id)
            
            if not active_questions:
                keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                
                if isinstance(update, Update):
                    await update.message.reply_text(
                        "📭 <b>لا توجد أسئلة متاحة للإجابة حالياً</b>\n\n"
                        "يمكنك العودة لاحقاً للبحث عن أسئلة للإجابة عليها",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.edit_message_text(
                        "📭 <b>لا توجد أسئلة متاحة للإجابة حالياً</b>\n\n"
                        "يمكنك العودة لاحقاً للبحث عن أسئلة للإجابة عليها",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                return
            
            message = f"🤝 <b>الأسئلة المتاحة للإجابة:</b>\n\n"
            message += f"🎯 <b>مكافأة الإجابة:</b> {self.settings_manager.get_answer_reward():,} دينار\n\n"
            
            keyboard = []
            for question in active_questions[:15]:  # عرض أول 15 سؤال
                question_text = question['question'][:50] + "..." if len(question['question']) > 50 else question['question']
                views = question.get('views', 0)
                question_id = question.get('id', '')
                
                btn_text = f"❓ {question_text} ({views} 👁️)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_question_{question_id}")])
            
            keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="student_questions")])
            keyboard.append([InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if isinstance(update, Update):
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"❌ خطأ في عرض أسئلة الطلاب: {e}")
            if isinstance(update, Update):
                await update.message.reply_text("❌ <b>حدث خطأ في تحميل الأسئلة</b>", parse_mode=ParseMode.HTML)
            else:
                await update.answer("❌ حدث خطأ في تحميل الأسئلة", show_alert=True)
    
    async def handle_view_question(self, query, context: ContextTypes.DEFAULT_TYPE, question_id: str):
        """عرض تفاصيل سؤال"""
        question = self.questions_manager.get_question_by_id(question_id)
        
        if not question:
            await query.answer("❌ السؤال غير موجود", show_alert=True)
            return
        
        question_owner = self.user_manager.get_user(question['user_id'])
        question_owner_name = question_owner.get('first_name', 'مجهول')
        
        message = f"""
❓ <b>تفاصيل السؤال</b>

👤 <b>صاحب السؤال:</b> {question_owner_name}
📅 <b>التاريخ:</b> {question.get('date', 'غير معروف')}
👁️ <b>المشاهدات:</b> {question.get('views', 0)}
💎 <b>مكافأة الإجابة:</b> {self.settings_manager.get_answer_reward():,} دينار

📝 <b>السؤال:</b>
{question['question']}

"""
        
        keyboard = []
        
        if not question.get('answered', False):
            # إذا لم يتم الإجابة عليه
            message += "⏳ <b>الحالة:</b> في انتظار الإجابة\n\n"
            keyboard.append([InlineKeyboardButton("💡 الإجابة على السؤال", callback_data=f"answer_question_{question_id}")])
        else:
            # إذا تمت الإجابة عليه
            answers = question.get('answers', [])
            message += f"✅ <b>الحالة:</b> تمت الإجابة ({len(answers)} إجابة)\n\n"
            
            for i, answer in enumerate(answers[:3]):  # عرض أول 3 إجابات
                answerer = self.user_manager.get_user(answer['answerer_id'])
                answerer_name = answerer.get('first_name', 'مجهول')
                
                message += f"👤 <b>الإجابة من {answerer_name}:</b>\n"
                message += f"{answer['answer'][:200]}...\n\n"
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع للأسئلة", callback_data="student_questions")])
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_answer_question(self, query, context: ContextTypes.DEFAULT_TYPE, question_id: str):
        """الإجابة على سؤال"""
        await query.edit_message_text(
            f"💡 <b>الإجابة على السؤال #{question_id}</b>\n\n"
            f"🎯 <b>المكافأة:</b> {self.settings_manager.get_answer_reward():,} دينار\n\n"
            "📝 <b>اكتب إجابتك الآن:</b>\n"
            "• يمكنك كتابة نص طويل\n"
            "• كن دقيقاً وواضحاً\n"
            "• استخدم أمثلة إذا لزم الأمر\n\n"
            "❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['answering_question'] = question_id
        return QUESTION_ANSWER
    
    async def handle_question_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إجابة السؤال"""
        user_id = update.effective_user.id
        answer_text = update.message.text.strip()
        question_id = context.user_data.get('answering_question')
        
        if not question_id:
            await update.message.reply_text("❌ <b>حدث خطأ في تحديد السؤال</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        
        if len(answer_text) < 10:
            await update.message.reply_text("❌ <b>الإجابة قصيرة جداً</b>\n\nيرجى كتابة إجابة مفصلة", parse_mode=ParseMode.HTML)
            return QUESTION_ANSWER
        
        # إضافة الإجابة
        success, question_owner_id = self.questions_manager.add_answer(question_id, user_id, answer_text)
        
        if success:
            # منح مكافأة الإجابة
            reward = self.settings_manager.get_answer_reward()
            new_balance, should_notify = self.user_manager.update_balance(
                user_id, 
                reward, 
                f"مكافأة الإجابة على سؤال #{question_id}"
            )
            
            # تحديث إحصائيات المستخدم
            user_data = self.user_manager.get_user(user_id)
            user_data["questions_answered"] = user_data.get("questions_answered", 0) + 1
            
            # إشعار صاحب السؤال
            if question_owner_id:
                question_owner_message = f"""
💡 <b>تمت الإجابة على سؤالك!</b>

🆔 <b>رقم السؤال:</b> {question_id}
👤 <b>المجيب:</b> {user_data.get('first_name', 'مجهول')}
📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

📝 <b>يمكنك رؤية الإجابة من خلال قسم الأسئلة</b>
"""
                await self.send_notification(question_owner_id, question_owner_message, context)
            
            await update.message.reply_text(
                f"✅ <b>تمت الإجابة بنجاح!</b>\n\n"
                f"🎯 <b>المكافأة:</b> {reward:,} دينار\n"
                f"💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار\n\n"
                f"📝 <b>شكراً لمساعدتك للطلاب الآخرين!</b>",
                parse_mode=ParseMode.HTML
            )
            
            if 'answering_question' in context.user_data:
                del context.user_data['answering_question']
            
            keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🔙", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ <b>فشل في إضافة الإجابة</b>\n\nقد يكون السؤال قد تمت الإجابة عليه مسبقاً", parse_mode=ParseMode.HTML)
        
        return ConversationHandler.END
    
    # ============= قسم ملازمي ومرشحاتي =============
    async def handle_service_materials(self, query):
        """معالجة خدمة المواد التعليمية"""
        user_id = query.from_user.id
        
        if not self.settings_manager.is_service_active("materials"):
            await query.edit_message_text(
                "⏸️ <b>خدمة المواد غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                f"📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("materials")
        
        if user_data['balance'] < price:
            await query.edit_message_text(
                f"❌ <b>رصيدك غير كافي!</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                f"🆔 <b>رقم حسابك للشحن:</b> <code>{user_id}</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        stages = self.materials_manager.get_all_stages()
        
        if not stages:
            keyboard = [[InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="back_home")]]
            await query.edit_message_text(
                "📭 <b>لا توجد مواد متاحة حالياً</b>\n\n"
                "📞 تواصل مع الدعم الفني لإضافة مواد جديدة",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        self.user_manager.set_pending_purchase(user_id, "materials", price)
        
        keyboard = []
        for stage in stages:
            materials_count = len(self.materials_manager.get_materials_by_stage(stage))
            btn_text = f"📘 {stage} ({materials_count})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"materials_stage_{stage}")])
        
        keyboard.append([InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📖 <b>اختر المرحلة الدراسية:</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "⚠️ <b>سيتم خصم المبلغ عند اختيار المرحلة</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_materials_stage_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, stage: str):
        """معالجة اختيار مرحلة المواد"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if self.user_manager.complete_purchase(user_id):
            price = self.settings_manager.get_price("materials")
            new_balance = self.user_manager.update_balance(user_id, -price, f"الوصول لمواد مرحلة {stage}")
            
            materials = self.materials_manager.get_materials_by_stage(stage)
            
            if not materials:
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="service_materials")]]
                await query.edit_message_text(
                    f"📭 <b>لا توجد مواد لمرحلة {stage}</b>\n\n"
                    f"💰 تم خصم: {price:,} دينار\n"
                    f"💳 رصيدك المتبقي: {new_balance:,} دينار",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
                return
            
            message = f"<b>📚 مواد مرحلة {stage}:</b>\n\n"
            message += f"💰 تم خصم: {price:,} دينار\n"
            message += f"💳 رصيدك المتبقي: {new_balance:,} دينار\n\n"
            
            keyboard = []
            for material in materials:
                btn_text = f"📄 {material.get('name', 'بدون اسم')[:30]}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"download_material_{material['id']}")])
                
                message += f"<b>📖 {material.get('name', 'بدون اسم')}</b>\n"
                description = material.get('description', '')
                if len(description) > 60:
                    description = description[:60] + "..."
                message += f"📝 {description}\n"
                message += f"⬇️ {material.get('downloads', 0)} تحميل | 👁️ {material.get('views', 0)} مشاهدة\n\n"
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="service_materials")])
            keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
    
    async def handle_download_material(self, query, context: ContextTypes.DEFAULT_TYPE, material_id: int):
        """تحميل مادة"""
        material = self.materials_manager.get_material(material_id)
        
        if not material:
            await query.answer("❌ المادة غير موجودة", show_alert=True)
            return
        
        try:
            # تحديث عدد التحميلات
            self.materials_manager.increment_downloads(material_id)
            
            # إرسال الملف
            file_id = material.get('file_id')
            file_name = material.get('file_name', f"مادة_{material_id}.pdf")
            
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=file_id,
                filename=file_name,
                caption=f"📄 <b>{material.get('name', 'بدون اسم')}</b>\n\n"
                       f"📝 {material.get('description', '')[:200]}\n"
                       f"🎓 المرحلة: {material.get('stage', 'غير محدد')}\n"
                       f"📅 تاريخ الإضافة: {material.get('added_date', 'غير معروف')}",
                parse_mode=ParseMode.HTML
            )
            
            await query.answer("✅ تم إرسال المادة بنجاح", show_alert=True)
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال المادة: {e}")
            await query.answer("❌ فشل في إرسال المادة", show_alert=True)
    
    # ============= نظام VIP الكامل =============
    async def show_vip_lectures_store(self, query):
        """عرض متجر محاضرات VIP"""
        approved_lectures = self.vip_manager.get_approved_lectures()
        
        if not approved_lectures:
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="vip_lectures_store")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
            ]
            
            if self.user_manager.is_vip(query.from_user.id) or query.from_user.id == ADMIN_ID:
                keyboard.insert(0, [InlineKeyboardButton("📤 رفع محاضرة", callback_data="vip_add_lecture")])
            
            await query.edit_message_text(
                "📭 <b>لا توجد محاضرات VIP متاحة حالياً</b>\n\n"
                "يمكنك العودة لاحقاً للتحقق من المحاضرات الجديدة",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = f"👑 <b>متجر محاضرات VIP ({len(approved_lectures)})</b>\n\n"
        message += "📚 <b>اختر محاضرة للشراء:</b>\n\n"
        
        keyboard = []
        for lecture in approved_lectures[:15]:
            title = lecture.get('title', 'بدون عنوان')[:40]
            price = lecture.get('price', 0)
            teacher_id = lecture.get('teacher_id')
            teacher_data = self.user_manager.get_user(teacher_id)
            teacher_name = teacher_data.get('first_name', 'مجهول')[:15]
            
            btn_text = f"🎓 {title}"
            if price > 0:
                btn_text += f" - {price:,} د"
            else:
                btn_text += " - مجاني"
            
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"vip_view_lecture_{lecture['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔄 تحديث", callback_data="vip_lectures_store")])
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        if self.user_manager.is_vip(query.from_user.id) or query.from_user.id == ADMIN_ID:
            keyboard.insert(0, [InlineKeyboardButton("📤 رفع محاضرة", callback_data="vip_add_lecture")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_view_lecture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """عرض تفاصيل محاضرة"""
        query = update.callback_query
        await query.answer()
        
        lecture = self.vip_manager.get_lecture_by_id(lecture_id)
        if not lecture or lecture["status"] != "approved":
            await query.edit_message_text("❌ <b>المحاضرة غير موجودة أو غير معتمدة</b>", parse_mode=ParseMode.HTML)
            return
        
        teacher_id = lecture["teacher_id"]
        teacher_data = self.user_manager.get_user(teacher_id)
        teacher_name = teacher_data.get('first_name', 'مجهول')
        
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        
        # التحقق إذا كان المستخدم اشترى المحاضرة مسبقاً
        student_purchases = self.vip_manager.get_student_purchases(user_id)
        already_purchased = any(purchase["lecture_id"] == lecture_id for purchase in student_purchases)
        
        # التحقق إذا كان المستخدم هو المعلم نفسه
        is_teacher = teacher_id == user_id
        
        message = f"""
👑 <b>تفاصيل المحاضرة</b>

📝 <b>العنوان:</b> {lecture.get('title', 'بدون عنوان')}
👤 <b>المعلم:</b> {teacher_name}
💰 <b>السعر:</b> {lecture.get('price', 0):,} دينار
📅 <b>تاريخ النشر:</b> {lecture.get('approved_date', 'غير معروف')}
👁️ <b>المشاهدات:</b> {lecture.get('views', 0)}
🛒 <b>المبيعات:</b> {lecture.get('sales', 0)}
💎 <b>الأرباح:</b> {lecture.get('earnings', 0):,} دينار

📄 <b>الوصف:</b>
{lecture.get('description', 'بدون وصف')}

💳 <b>رصيدك:</b> {user_data['balance']:,} دينار
"""
        
        keyboard = []
        
        if already_purchased or is_teacher:
            message += "\n✅ <b>لديك صلاحية التحميل</b>"
            keyboard.append([InlineKeyboardButton("📥 تحميل المحاضرة", callback_data=f"vip_download_{lecture_id}")])
            
            if is_teacher:
                keyboard.append([InlineKeyboardButton("🗑️ حذف المحاضرة", callback_data=f"vip_delete_lecture_{lecture_id}")])
        else:
            if lecture.get('price', 0) == 0:
                keyboard.append([InlineKeyboardButton("🎁 تحميل مجاني", callback_data=f"vip_buy_{lecture_id}")])
            else:
                if user_data['balance'] >= lecture.get('price', 0):
                    keyboard.append([InlineKeyboardButton(f"🛒 شراء المحاضرة ({lecture.get('price', 0):,} د)", callback_data=f"vip_buy_{lecture_id}")])
                else:
                    message += f"\n❌ <b>رصيدك غير كافي للشراء</b>\n💵 تحتاج: {lecture.get('price', 0):,} دينار"
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع للمتجر", callback_data="vip_lectures_store")])
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_buy_lecture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """شراء محاضرة VIP"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lecture = self.vip_manager.get_lecture_by_id(lecture_id)
        
        if not lecture or lecture["status"] != "approved":
            await query.answer("❌ المحاضرة غير موجودة", show_alert=True)
            return
        
        price = lecture.get('price', 0)
        
        # التحقق إذا كان المحاضرة مجانية
        if price == 0:
            await self.handle_vip_download_lecture(query, context, lecture_id)
            return
        
        user_data = self.user_manager.get_user(user_id)
        
        if user_data['balance'] < price:
            await query.answer(f"❌ رصيدك غير كافي! تحتاج {price:,} دينار", show_alert=True)
            return
        
        # التحقق إذا كان المستخدم اشترى المحاضرة مسبقاً
        student_purchases = self.vip_manager.get_student_purchases(user_id)
        if any(purchase["lecture_id"] == lecture_id for purchase in student_purchases):
            await query.answer("✅ لقد اشتريت هذه المحاضرة مسبقاً", show_alert=True)
            await self.handle_vip_download_lecture(query, context, lecture_id)
            return
        
        # خصم المبلغ من الطالب
        new_balance, _ = self.user_manager.update_balance(user_id, -price, f"شراء محاضرة VIP: {lecture.get('title', '')}")
        
        # تسجيل عملية الشراء
        success, teacher_id = self.vip_manager.purchase_lecture(user_id, lecture_id, price)
        
        if success:
            # إعطاء حصة للمعلم
            teacher_share = self.vip_manager.vip_data["settings"]["teacher_share_percentage"]
            teacher_amount = int(price * (teacher_share / 100))
            
            teacher_new_balance, _ = self.user_manager.update_balance(
                teacher_id, 
                teacher_amount, 
                f"ربح من بيع محاضرة: {lecture.get('title', '')}"
            )
            
            # تحديث إحصائيات المعلم
            teacher_data = self.user_manager.get_user(teacher_id)
            teacher_data["vip_earnings"] = teacher_data.get("vip_earnings", 0) + teacher_amount
            teacher_data["vip_sales"] = teacher_data.get("vip_sales", 0) + 1
            self.user_manager.save_users()
            
            # إشعار للمعلم
            teacher_message = f"""
💰 <b>تم بيع محاضرة لك!</b>

📝 <b>المحاضرة:</b> {lecture.get('title', 'بدون عنوان')}
👤 <b>الطالب:</b> {user_data.get('first_name', 'مجهول')}
💵 <b>السعر:</b> {price:,} دينار
🎁 <b>حصتك:</b> {teacher_amount:,} دينار ({teacher_share}%)
💳 <b>رصيدك الجديد:</b> {teacher_new_balance:,} دينار

🎉 <b>مبروك على البيع!</b>
"""
            await self.send_notification(teacher_id, teacher_message, context)
            
            # إشعار للطالب
            await query.edit_message_text(
                f"✅ <b>تم شراء المحاضرة بنجاح!</b>\n\n"
                f"📝 <b>المحاضرة:</b> {lecture.get('title', 'بدون عنوان')}\n"
                f"👤 <b>المعلم:</b> {self.user_manager.get_user(teacher_id).get('first_name', 'مجهول')}\n"
                f"💵 <b>المبلغ:</b> {price:,} دينار\n"
                f"💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار\n\n"
                f"📥 <b>يمكنك الآن تحميل المحاضرة</b>",
                parse_mode=ParseMode.HTML
            )
            
            # إضافة زر التحميل
            keyboard = [
                [InlineKeyboardButton("📥 تحميل المحاضرة", callback_data=f"vip_download_{lecture_id}")],
                [InlineKeyboardButton("🔙 رجوع للمتجر", callback_data="vip_lectures_store")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📥", reply_markup=reply_markup)
        else:
            # استرجاع المبلغ في حالة الفشل
            self.user_manager.update_balance(user_id, price, f"استرجاع رصيد لشراء محاضرة فاشل")
            await query.answer("❌ فشل في عملية الشراء", show_alert=True)
    
    async def handle_vip_download_lecture(self, query, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """تحميل محاضرة VIP"""
        user_id = query.from_user.id
        lecture = self.vip_manager.get_lecture_by_id(lecture_id)
        
        if not lecture:
            await query.answer("❌ المحاضرة غير موجودة", show_alert=True)
            return
        
        # التحقق من صلاحية التحميل
        if lecture.get('price', 0) > 0:
            # إذا كانت مدفوعة
            student_purchases = self.vip_manager.get_student_purchases(user_id)
            has_purchased = any(purchase["lecture_id"] == lecture_id for purchase in student_purchases)
            
            # التحقق إذا كان المستخدم هو المعلم نفسه
            is_teacher = lecture['teacher_id'] == user_id
            
            if not has_purchased and not is_teacher:
                await query.answer("❌ يجب شراء المحاضرة أولاً", show_alert=True)
                return
        
        file_info = lecture.get('file_info', {})
        file_id = file_info.get('file_id')
        file_type = file_info.get('file_type', 'document')
        
        if not file_id:
            await query.answer("❌ لا يوجد ملف لهذه المحاضرة", show_alert=True)
            return
        
        try:
            # زيادة عدد التحميلات
            lecture["downloads"] = lecture.get("downloads", 0) + 1
            self.vip_manager.save_all_data()
            
            # إرسال الملف
            if file_type == 'video':
                await context.bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=f"📹 <b>{lecture.get('title', 'بدون عنوان')}</b>\n\n"
                           f"👤 <b>المعلم:</b> {self.user_manager.get_user(lecture['teacher_id']).get('first_name', 'مجهول')}\n"
                           f"📝 {lecture.get('description', '')[:200]}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption=f"📄 <b>{lecture.get('title', 'بدون عنوان')}</b>\n\n"
                           f"👤 <b>المعلم:</b> {self.user_manager.get_user(lecture['teacher_id']).get('first_name', 'مجهول')}\n"
                           f"📝 {lecture.get('description', '')[:200]}",
                    parse_mode=ParseMode.HTML
                )
            
            await query.answer("✅ تم إرسال المحاضرة", show_alert=True)
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الملف: {e}")
            await query.answer("❌ فشل في إرسال الملف", show_alert=True)
    
    async def handle_vip_delete_lecture(self, query, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """حذف محاضرة VIP"""
        user_id = query.from_user.id
        is_admin = user_id == ADMIN_ID
        
        # طلب تأكيد
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، احذف", callback_data=f"vip_confirm_delete_{lecture_id}_{int(is_admin)}"),
                InlineKeyboardButton("❌ إلغاء", callback_data=f"vip_view_lecture_{lecture_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ <b>تأكيد الحذف</b>\n\n"
            "هل أنت متأكد من حذف هذه المحاضرة؟\n"
            "❌ <b>هذا الإجراء لا يمكن التراجع عنه</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_confirm_delete(self, query, context: ContextTypes.DEFAULT_TYPE, lecture_id: str, is_admin_str: str):
        """تأكيد حذف محاضرة"""
        is_admin = is_admin_str == "1"
        user_id = query.from_user.id
        
        success = self.vip_manager.delete_lecture(lecture_id, user_id, is_admin)
        
        if success:
            await query.answer("✅ تم حذف المحاضرة بنجاح", show_alert=True)
            await self.show_vip_lectures_store(query)
        else:
            await query.answer("❌ فشل في حذف المحاضرة", show_alert=True)
    
    # ============= نظام الإحالة الكامل =============
    async def handle_invite_friends(self, query):
        """عرض نظام الإحالة"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        
        stats = self.referral_system.get_referral_stats(user_id)
        
        message = f"""
👥 <b>نظام دعوة الأصدقاء</b>

🎯 <b>كيف تعمل:</b>
1. أرسل رابط الدعوة لأصدقائك
2. عندما ينضم صديقك ويستخدم البوت
3. تحصل على مكافأة {self.settings_manager.get_referral_bonus():,} دينار لكل صديق

📊 <b>إحصائياتك:</b>
• 👥 عدد المحالين: {stats['total_invited']:,}
• 💰 إجمالي الأرباح: {stats['total_earned']:,} دينار
• 📅 آخر إحالة: {stats['last_referral'] or 'لا توجد'}

🔗 <b>رابط الدعوة الخاص بك:</b>
<code>{stats['referral_link']}</code>

🎁 <b>مكافأة إضافية:</b>
عندما يجلب المحالون أصدقاء، تحصل على نسبة من أرباحهم!
"""
        
        keyboard = [
            [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={stats['referral_link']}&text=انضم%20للبوت%20التعليمي%20الرائع!")],
            [InlineKeyboardButton("📋 قائمة المحالين", callback_data="referral_list")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_referral_list(self, query):
        """عرض قائمة المحالين"""
        user_id = query.from_user.id
        stats = self.referral_system.get_referral_stats(user_id)
        
        if not stats['recent_referrals']:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="invite_friends")]]
            await query.edit_message_text(
                "📭 <b>لا توجد إحالات حتى الآن</b>\n\n"
                "شارك رابطك مع أصدقائك لتبدأ في كسب المكافآت!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = "📋 <b>آخر المحالين:</b>\n\n"
        
        for i, referral in enumerate(stats['recent_referrals'], 1):
            message += f"{i}. 👤 {referral['name']}\n"
            message += f"   🆔 ID: {referral['user_id']}\n"
            message += f"   📅 {referral['join_date']}\n"
            message += "   ─" * 10 + "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="referral_list")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="invite_friends")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # ============= نظام الإعفاء المحسن =============
    async def handle_service_exemption(self, query):
        """معالجة خدمة حساب درجة الإعفاء"""
        user_id = query.from_user.id
        
        if not self.settings_manager.is_service_active("exemption"):
            await query.edit_message_text(
                "⏸️ <b>هذه الخدمة غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                f"📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("exemption")
        
        if user_data['balance'] < price:
            await query.edit_message_text(
                f"❌ <b>رصيدك غير كافي!</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                f"🆔 <b>رقم حسابك للشحن:</b> <code>{user_id}</code>\n\n"
                f"📞 تواصل مع الدعم الفني: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        self.user_manager.set_pending_purchase(user_id, "exemption", price)
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="back_home")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧮 <b>حاسبة درجة الإعفاء</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "📝 <b>الخطوة 1 من 3:</b>\n"
            "أدخل درجة الكورس الأول (0-100):\n\n"
            "🎯 <b>المعدل المطلوب للإعفاء:</b> 90 فما فوق\n"
            "⚠️ <b>سيتم خصم المبلغ بعد الحساب</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        return EXEMPTION_COURSE1
    
    async def handle_exemption_course1(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة درجة الكورس الأول"""
        try:
            score = float(update.message.text.strip())
            
            if score < 0 or score > 100:
                await update.message.reply_text("❌ <b>الدرجة يجب أن تكون بين 0 و 100</b>\n\nأعد إدخال درجة الكورس الأول:", parse_mode=ParseMode.HTML)
                return EXEMPTION_COURSE1
            
            context.user_data['exemption_scores'] = [score]
            
            await update.message.reply_text(
                "✅ <b>تم حفظ درجة الكورس الأول</b>\n\n"
                "📝 <b>الخطوة 2 من 3:</b>\n"
                "أدخل درجة الكورس الثاني (نصف السنة):",
                parse_mode=ParseMode.HTML
            )
            
            return EXEMPTION_COURSE2
            
        except ValueError:
            await update.message.reply_text("❌ <b>أدخل رقماً صحيحاً فقط</b>\n\nأعد إدخال درجة الكورس الأول:", parse_mode=ParseMode.HTML)
            return EXEMPTION_COURSE1
    
    async def handle_exemption_course2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة درجة الكورس الثاني"""
        try:
            score = float(update.message.text.strip())
            
            if score < 0 or score > 100:
                await update.message.reply_text("❌ <b>الدرجة يجب أن تكون بين 0 و 100</b>\n\nأعد إدخال درجة الكورس الثاني:", parse_mode=ParseMode.HTML)
                return EXEMPTION_COURSE2
            
            context.user_data['exemption_scores'].append(score)
            
            await update.message.reply_text(
                "✅ <b>تم حفظ درجة الكورس الثاني</b>\n\n"
                "📝 <b>الخطوة 3 من 3:</b>\n"
                "أدخل درجة الكورس الثالث:",
                parse_mode=ParseMode.HTML
            )
            
            return EXEMPTION_COURSE3
            
        except ValueError:
            await update.message.reply_text("❌ <b>أدخل رقماً صحيحاً فقط</b>\n\nأعد إدخال درجة الكورس الثاني:", parse_mode=ParseMode.HTML)
            return EXEMPTION_COURSE2
    
    async def handle_exemption_course3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة درجة الكورس الثالث"""
        user_id = update.effective_user.id
        
        try:
            score = float(update.message.text.strip())
            
            if score < 0 or score > 100:
                await update.message.reply_text("❌ <b>الدرجة يجب أن تكون بين 0 و 100</b>\n\nأعد إدخال درجة الكورس الثالث:", parse_mode=ParseMode.HTML)
                return EXEMPTION_COURSE3
            
            scores = context.user_data['exemption_scores'] + [score]
            
            # حساب المعدل
            average = sum(scores) / 3
            
            if average >= 90:
                message = f"""
🎉 <b>تهانينا! تم إعفاؤك من المادة</b> 🎉

📊 <b>درجاتك:</b>
الكورس الأول: {scores[0]}
الكورس الثاني: {scores[1]}  
الكورس الثالث: {scores[2]}

🧮 <b>المعدل:</b> {average:.2f}

✅ <b>أنت معفي من المادة</b>
"""
            else:
                message = f"""
📊 <b>درجاتك:</b>
الكورس الأول: {scores[0]}
الكورس الثاني: {scores[1]}
الكورس الثالث: {scores[2]}

🧮 <b>المعدل:</b> {average:.2f}

⚠️ <b>المعدل أقل من 90</b>
❌ <b>لم تحصل على الإعفاء</b>
"""
            
            if self.user_manager.complete_purchase(user_id):
                price = self.settings_manager.get_price("exemption")
                new_balance, _ = self.user_manager.update_balance(user_id, -price, f"حساب درجة الإعفاء")
                
                message += f"\n💰 تم خصم: {price:,} دينار"
                message += f"\n💳 رصيدك المتبقي: {new_balance:,} دينار"
                
                user_data = self.user_manager.get_user(user_id)
                user_data.setdefault("exemption_scores", []).append({
                    "scores": scores,
                    "average": average,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "exempted": average >= 90
                })
                self.user_manager.save_users()
                
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)
                
                if 'exemption_scores' in context.user_data:
                    del context.user_data['exemption_scores']
                
                keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("🔙", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
                self.user_manager.cancel_purchase(user_id)
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ <b>أدخل رقماً صحيحاً فقط</b>\n\nأعد إدخال درجة الكورس الثالث:", parse_mode=ParseMode.HTML)
            return EXEMPTION_COURSE3
    
    # ============= لوحة التحكم الكاملة =============
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لوحة التحكم الإدارية"""
        if isinstance(update, Update) and update.message:
            user = update.effective_user
            message = update.message
        else:
            query = update.callback_query
            await query.answer()
            user = query.from_user
            message = query
        
        if user.id != ADMIN_ID:
            if hasattr(message, 'edit_message_text'):
                await message.edit_message_text("⛔ <b>غير مسموح لك بالدخول!</b>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("⛔ <b>غير مسموح لك بالدخول!</b>", parse_mode=ParseMode.HTML)
            return
        
        total_users = len(self.user_manager.users)
        total_balance = sum(user.get("balance", 0) for user in self.user_manager.users.values())
        
        vip_users = sum(1 for user_id_str, user_data in self.user_manager.users.items() 
                       if self.user_manager.is_vip(int(user_id_str)))
        
        active_questions = len(self.questions_manager.get_active_questions())
        
        panel_text = f"""
👑 <b>لوحة التحكم الإدارية</b>

📊 <b>إحصائيات البوت:</b>
• 👥 عدد المستخدمين: {total_users:,}
• 💰 إجمالي الرصيد: {total_balance:,} دينار
• 👑 مشتركين VIP: {vip_users}
• 📢 رابط القناة: {self.settings_manager.get_channel_link()}
• ❓ الأسئلة النشطة: {active_questions}
• 📚 عدد المواد: {len(self.materials_manager.materials)}
• 📤 محاضرات VIP: {len(self.vip_manager.get_approved_lectures())}
• ⏳ محاضرات قيد المراجعة: {len(self.vip_manager.get_pending_lectures())}

⚙️ <b>اختر الإجراء:</b>
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("💰 شحن/خصم الرصيد", callback_data="admin_charge")],
            [InlineKeyboardButton("⚙️ إدارة الخدمات", callback_data="admin_services")],
            [InlineKeyboardButton("💰 تغيير الأسعار", callback_data="admin_change_prices")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("📚 إدارة المواد", callback_data="admin_materials")],
            [InlineKeyboardButton("❓ إدارة الأسئلة", callback_data="admin_questions")],
            [InlineKeyboardButton("👑 إدارة VIP", callback_data="admin_vip_management")],
            [InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 رجوع للبوت", callback_data="back_home")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(message, 'edit_message_text'):
            await message.edit_message_text(panel_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(panel_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def handle_admin_change_prices(self, query):
        """تغيير أسعار الخدمات"""
        services = self.settings_manager.get_all_services()
        
        message = "💰 <b>تغيير أسعار الخدمات</b>\n\n"
        message += "📊 <b>الأسعار الحالية:</b>\n\n"
        
        keyboard = []
        for service_key, service_data in services.items():
            if service_key in ["vip_lectures"]:
                continue  # تخطي خدمات VIP
            
            current_price = self.settings_manager.get_price(service_key)
            service_name = service_data.get('name', service_key)
            message += f"{service_name}: {current_price:,} دينار\n"
            keyboard.append([InlineKeyboardButton(f"تغيير {service_name.split()[-1]}", callback_data=f"change_price_{service_key}")])
        
        # إضافة سعر اشتراك VIP
        vip_price = self.vip_manager.get_subscription_price()
        message += f"\n👑 اشتراك VIP شهري: {vip_price:,} دينار"
        keyboard.append([InlineKeyboardButton("تغيير سعر VIP", callback_data="change_price_vip_subscription")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_change_price_service(self, query, context: ContextTypes.DEFAULT_TYPE, service: str):
        """تغيير سعر خدمة محددة"""
        service_names = {
            "exemption": "حساب درجة الإعفاء",
            "summarize": "تلخيص الملازم",
            "qa": "سؤال وجواب بالذكاء",
            "materials": "ملازمي ومرشحاتي",
            "help_student": "ساعدوني طلاب",
            "vip_subscription": "اشتراك VIP شهري"
        }
        
        if service == "vip_subscription":
            current_price = self.vip_manager.get_subscription_price()
        else:
            current_price = self.settings_manager.get_price(service)
        
        service_name = service_names.get(service, service)
        
        await query.edit_message_text(
            f"💰 <b>تغيير سعر الخدمة</b>\n\n"
            f"📝 <b>الخدمة:</b> {service_name}\n"
            f"💵 <b>السعر الحالي:</b> {current_price:,} دينار\n\n"
            f"🔢 <b>أدخل السعر الجديد:</b>\n"
            f"<code>1000</code>\n\n"
            f"❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['changing_price_service'] = service
        return CHANGE_PRICE_SERVICE
    
    async def handle_change_price_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تغيير السعر"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        text = update.message.text.strip()
        
        if not text.isdigit():
            await update.message.reply_text(
                "❌ <b>مبلغ غير صحيح!</b>\n\n"
                "يجب أن يكون المبلغ رقماً فقط\n"
                "أعد إدخال السعر:",
                parse_mode=ParseMode.HTML
            )
            return CHANGE_PRICE_SERVICE
        
        new_price = int(text)
        service = context.user_data.get('changing_price_service')
        
        if new_price <= 0:
            await update.message.reply_text(
                "❌ <b>السعر يجب أن يكون أكبر من صفر</b>\n\n"
                "أعد إدخال السعر:",
                parse_mode=ParseMode.HTML
            )
            return CHANGE_PRICE_SERVICE
        
        if service == "vip_subscription":
            self.vip_manager.update_subscription_price(new_price)
        else:
            self.settings_manager.update_price(service, new_price)
        
        service_names = {
            "exemption": "حساب درجة الإعفاء",
            "summarize": "تلخيص الملازم",
            "qa": "سؤال وجواب بالذكاء",
            "materials": "ملازمي ومرشحاتي",
            "help_student": "ساعدوني طلاب",
            "vip_subscription": "اشتراك VIP شهري"
        }
        
        service_name = service_names.get(service, service)
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير السعر بنجاح!</b>\n\n"
            f"📝 <b>الخدمة:</b> {service_name}\n"
            f"💰 <b>السعر الجديد:</b> {new_price:,} دينار",
            parse_mode=ParseMode.HTML
        )
        
        if 'changing_price_service' in context.user_data:
            del context.user_data['changing_price_service']
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    async def handle_admin_services(self, query):
        """إدارة الخدمات"""
        all_services = self.settings_manager.get_all_services()
        
        message = "⚙️ <b>إدارة الخدمات</b>\n\n"
        message += "🔧 <b>حالة الخدمات:</b>\n\n"
        
        keyboard = []
        for service_key, service_data in all_services.items():
            active = service_data.get("active", True)
            status = "🟢 مفعل" if active else "🔴 معطل"
            price = self.settings_manager.get_price(service_key) if service_key in self.settings_manager.admin_settings.get("prices", {}) else 0
            service_name = service_data.get("name", service_key)
            
            message += f"{service_name}: {status} ({price:,} د)\n"
            
            btn_text = f"{'❌ تعطيل' if active else '✅ تفعيل'} {service_name.split()[-1]}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_service_{service_key}")])
        
        keyboard.append([InlineKeyboardButton("➕ إضافة خدمة", callback_data="admin_add_service")])
        keyboard.append([InlineKeyboardButton("➖ إزالة خدمة", callback_data="admin_remove_service")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_toggle_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE, service: str):
        """تبديل حالة الخدمة"""
        query = update.callback_query
        await query.answer()
        
        new_status = self.settings_manager.toggle_service(service)
        status_text = "تم تفعيل" if new_status else "تم تعطيل"
        
        service_data = self.settings_manager.services_status.get(service, {})
        service_name = service_data.get("name", service)
        
        await query.answer(f"✅ {status_text} {service_name}")
        await self.handle_admin_services(query)
    
    async def handle_admin_vip_management(self, query):
        """إدارة نظام VIP"""
        pending_lectures = len(self.vip_manager.get_pending_lectures())
        approved_lectures = len(self.vip_manager.get_approved_lectures())
        subscription_price = self.vip_manager.get_subscription_price()
        
        vip_users = 0
        for user_id_str, user_data in self.user_manager.users.items():
            if self.user_manager.is_vip(int(user_id_str)):
                vip_users += 1
        
        message = f"""
👑 <b>إدارة نظام VIP</b>

📊 <b>الإحصائيات:</b>
• 👥 مشتركين VIP: {vip_users}
• 📤 محاضرات قيد المراجعة: {pending_lectures}
• ✅ محاضرات معتمدة: {approved_lectures}
• 💰 سعر الاشتراك: {subscription_price:,} دينار

⚙️ <b>اختر الإجراء:</b>
"""
        
        keyboard = [
            [InlineKeyboardButton("📝 مراجعة المحاضرات", callback_data="vip_review_lectures")],
            [InlineKeyboardButton("👥 إدارة المعلمين", callback_data="vip_manage_teachers")],
            [InlineKeyboardButton("💰 تغيير سعر الاشتراك", callback_data="vip_change_subscription_price")],
            [InlineKeyboardButton("📊 إحصائيات VIP", callback_data="vip_statistics")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_review_lectures(self, query):
        """مراجعة المحاضرات"""
        pending_lectures = self.vip_manager.get_pending_lectures()
        
        if not pending_lectures:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_vip_management")]]
            await query.edit_message_text(
                "📭 <b>لا توجد محاضرات قيد المراجعة</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = f"📝 <b>المحاضرات قيد المراجعة ({len(pending_lectures)})</b>\n\n"
        
        keyboard = []
        for lecture in pending_lectures[:10]:
            teacher_id = lecture["teacher_id"]
            teacher_data = self.user_manager.get_user(teacher_id)
            teacher_name = teacher_data.get("first_name", "مجهول")
            
            title = lecture.get("title", "بدون عنوان")[:30]
            date = lecture.get("added_date", "").split()[0]
            price = lecture.get("price", 0)
            
            btn_text = f"📤 {title} - {teacher_name}"
            if price > 0:
                btn_text += f" ({price:,} د)"
            
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"vip_review_detail_{lecture['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_vip_management")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_review_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """تفاصيل مراجعة المحاضرة"""
        query = update.callback_query
        await query.answer()
        
        lecture = None
        for l in self.vip_manager.get_pending_lectures():
            if l["id"] == lecture_id:
                lecture = l
                break
        
        if not lecture:
            await query.edit_message_text("❌ <b>المحاضرة غير موجودة</b>", parse_mode=ParseMode.HTML)
            return
        
        teacher_id = lecture["teacher_id"]
        teacher_data = self.user_manager.get_user(teacher_id)
        
        message = f"""
📤 <b>مراجعة المحاضرة #{lecture_id}</b>

👤 <b>المعلم:</b>
• 🆔 ID: {teacher_id}
• 📛 الاسم: {teacher_data.get('first_name', 'مجهول')}
• 📅 اشتراك حتى: {teacher_data.get('vip_expiry', 'غير مشترك')}

📝 <b>تفاصيل المحاضرة:</b>
• 📌 العنوان: {lecture.get('title', 'بدون عنوان')}
• 📄 الوصف: {lecture.get('description', 'بدون وصف')}
• 💰 السعر: {lecture.get('price', 0):,} دينار
• 📅 تاريخ الإضافة: {lecture.get('added_date', 'غير معروف')}
• 📊 نوع الملف: {lecture.get('file_info', {}).get('file_type', 'غير معروف')}

⚡ <b>اختر الإجراء:</b>
"""
        
        keyboard = [
            [InlineKeyboardButton("👁️ معاينة المحاضرة", callback_data=f"vip_preview_lecture_{lecture_id}")],
            [InlineKeyboardButton("✅ الموافقة على المحاضرة", callback_data=f"vip_approve_lecture_{lecture_id}")],
            [InlineKeyboardButton("❌ رفض المحاضرة", callback_data=f"vip_reject_lecture_{lecture_id}")],
            [InlineKeyboardButton("👤 حظر المعلم", callback_data=f"vip_ban_teacher_{teacher_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="vip_review_lectures")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_preview_lecture(self, query, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """معاينة المحاضرة"""
        lecture = self.vip_manager.get_lecture_by_id(lecture_id)
        
        if not lecture:
            await query.answer("❌ المحاضرة غير موجودة", show_alert=True)
            return
        
        file_info = lecture.get('file_info', {})
        file_type = file_info.get('file_type', 'document')
        
        message = f"""
👁️ <b>معاينة المحاضرة</b>

📝 <b>العنوان:</b> {lecture.get('title', 'بدون عنوان')}
📄 <b>الوصف:</b> {lecture.get('description', 'بدون وصف')}
💰 <b>السعر:</b> {lecture.get('price', 0):,} دينار
📊 <b>نوع الملف:</b> {file_type}
📏 <b>حجم الملف:</b> {file_info.get('file_size', 0) / 1024 / 1024:.2f} ميجابايت

⚡ <b>اختر الإجراء:</b>
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ الموافقة", callback_data=f"vip_approve_lecture_{lecture_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"vip_reject_lecture_{lecture_id}")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"vip_review_detail_{lecture_id}")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_approve_lecture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """الموافقة على محاضرة"""
        query = update.callback_query
        await query.answer()
        
        if self.vip_manager.approve_lecture(lecture_id, "تمت الموافقة من الإدارة"):
            lecture = self.vip_manager.get_lecture_by_id(lecture_id)
            
            if lecture:
                teacher_id = lecture["teacher_id"]
                notify_message = f"""
✅ <b>تمت الموافقة على محاضراتك!</b>

🆔 <b>رقم المحاضرة:</b> {lecture_id}
📝 <b>العنوان:</b> {lecture.get('title', 'بدون عنوان')}
📅 <b>تاريخ الموافقة:</b> {lecture.get('approved_date', 'غير معروف')}

🎉 <b>مبروك! المحاضرة متاحة الآن للطلاب.</b>
"""
                await self.send_notification(teacher_id, notify_message, context)
            
            await query.answer("✅ تمت الموافقة على المحاضرة", show_alert=True)
            await self.handle_vip_review_lectures(query)
        else:
            await query.answer("❌ فشل في الموافقة على المحاضرة", show_alert=True)
    
    async def handle_vip_reject_lecture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """طلب سبب رفض المحاضرة"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "❌ <b>رفض المحاضرة</b>\n\n"
            "📝 <b>اكتب سبب الرفض:</b>\n"
            "• كن واضحاً ودقيقاً\n"
            "• اذكر الأسباب بالتسلسل\n"
            "• سوف يتم إرسال السبب للمعلم\n\n"
            "❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['rejecting_lecture'] = lecture_id
        return VIP_REJECT_REASON
    
    async def handle_vip_reject_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة سبب الرفض"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        rejection_reason = update.message.text.strip()
        lecture_id = context.user_data.get('rejecting_lecture')
        
        if not lecture_id:
            await update.message.reply_text("❌ <b>حدث خطأ في تحديد المحاضرة</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        
        if len(rejection_reason) < 5:
            await update.message.reply_text("❌ <b>السبب قصير جداً</b>\n\nاكتب سبباً مفصلاً للرفض:", parse_mode=ParseMode.HTML)
            return VIP_REJECT_REASON
        
        if self.vip_manager.reject_lecture(lecture_id, rejection_reason):
            lecture = self.vip_manager.get_lecture_by_id(lecture_id)
            
            if lecture:
                teacher_id = lecture["teacher_id"]
                notify_message = f"""
❌ <b>تم رفض محاضراتك</b>

🆔 <b>رقم المحاضرة:</b> {lecture_id}
📝 <b>العنوان:</b> {lecture.get('title', 'بدون عنوان')}
📅 <b>تاريخ الرفض:</b> {lecture.get('rejected_date', 'غير معروف')}

📝 <b>سبب الرفض:</b>
{rejection_reason}

📞 <b>للاستفسار:</b> @{SUPPORT_USERNAME}
"""
                await self.send_notification(teacher_id, notify_message, context)
            
            await update.message.reply_text(
                f"✅ <b>تم رفض المحاضرة بنجاح!</b>\n\n"
                f"📝 <b>تم إرسال سبب الرفض للمعلم.</b>",
                parse_mode=ParseMode.HTML
            )
            
            if 'rejecting_lecture' in context.user_data:
                del context.user_data['rejecting_lecture']
            
            await self.admin_panel(update, context)
        else:
            await update.message.reply_text("❌ <b>فشل في رفض المحاضرة</b>", parse_mode=ParseMode.HTML)
        
        return ConversationHandler.END
    
    # ============= معالجة الردود الرئيسية =============
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع Callback Queries"""
        query = update.callback_query
        
        try:
            await query.answer()
            
            # ============= الخدمات الرئيسية =============
            if query.data == "service_summarize":
                await self.handle_service_summarize(query, context)
                return SUMMARIZE_PDF
            
            elif query.data == "service_qa":
                await self.handle_service_qa(query, context)
                return QA_QUESTION
            
            elif query.data == "service_help_student":
                await self.handle_service_help_student(query, context)
                return HELP_STUDENT_QUESTION
            
            elif query.data == "service_materials":
                await self.handle_service_materials(query)
            
            elif query.data == "service_exemption":
                await self.handle_service_exemption(query)
                return EXEMPTION_COURSE1
            
            elif query.data.startswith("materials_stage_"):
                stage = query.data.replace("materials_stage_", "")
                await self.handle_materials_stage_selection(update, context, stage)
            
            elif query.data.startswith("download_material_"):
                material_id = int(query.data.replace("download_material_", ""))
                await self.handle_download_material(query, context, material_id)
            
            # ============= نظام VIP =============
            elif query.data == "vip_lectures_store":
                await self.show_vip_lectures_store(query)
            
            elif query.data.startswith("vip_view_lecture_"):
                lecture_id = query.data.replace("vip_view_lecture_", "")
                await self.handle_vip_view_lecture(update, context, lecture_id)
            
            elif query.data.startswith("vip_buy_"):
                lecture_id = query.data.replace("vip_buy_", "")
                await self.handle_vip_buy_lecture(update, context, lecture_id)
            
            elif query.data.startswith("vip_download_"):
                lecture_id = query.data.replace("vip_download_", "")
                await self.handle_vip_download_lecture(query, context, lecture_id)
            
            elif query.data.startswith("vip_delete_lecture_"):
                lecture_id = query.data.replace("vip_delete_lecture_", "")
                await self.handle_vip_delete_lecture(query, context, lecture_id)
            
            elif query.data.startswith("vip_confirm_delete_"):
                parts = query.data.replace("vip_confirm_delete_", "").split("_")
                lecture_id = parts[0]
                is_admin = parts[1]
                await self.handle_vip_confirm_delete(query, context, lecture_id, is_admin)
            
            elif query.data == "vip_subscription_info":
                await self.show_vip_subscription_info(query)
            
            elif query.data == "vip_subscribe":
                await self.handle_vip_subscribe(query, context)
            
            elif query.data == "vip_add_lecture":
                await self.handle_vip_add_lecture(query, context)
                return VIP_LECTURE_TITLE
            
            # ============= نظام الإحالة =============
            elif query.data == "invite_friends":
                await self.handle_invite_friends(query)
            
            elif query.data == "referral_list":
                await self.handle_referral_list(query)
            
            # ============= أسئلة الطلاب =============
            elif query.data == "student_questions":
                await self.show_student_questions_internal(update, context, query.from_user.id)
            
            elif query.data.startswith("view_question_"):
                question_id = query.data.replace("view_question_", "")
                await self.handle_view_question(query, context, question_id)
            
            elif query.data.startswith("answer_question_"):
                question_id = query.data.replace("answer_question_", "")
                return await self.handle_answer_question(query, context, question_id)
            
            # ============= لوحة التحكم =============
            elif query.data == "admin_panel":
                await self.admin_panel(update, context)
            
            elif query.data == "admin_change_prices":
                await self.handle_admin_change_prices(query)
            
            elif query.data.startswith("change_price_"):
                service = query.data.replace("change_price_", "")
                await self.handle_change_price_service(query, context, service)
                return CHANGE_PRICE_SERVICE
            
            elif query.data == "admin_vip_management":
                await self.handle_admin_vip_management(query)
            
            elif query.data == "vip_review_lectures":
                await self.handle_vip_review_lectures(query)
            
            elif query.data.startswith("vip_review_detail_"):
                lecture_id = query.data.replace("vip_review_detail_", "")
                await self.handle_vip_review_detail(update, context, lecture_id)
            
            elif query.data.startswith("vip_preview_lecture_"):
                lecture_id = query.data.replace("vip_preview_lecture_", "")
                await self.handle_vip_preview_lecture(query, context, lecture_id)
            
            elif query.data.startswith("vip_approve_lecture_"):
                lecture_id = query.data.replace("vip_approve_lecture_", "")
                await self.handle_vip_approve_lecture(update, context, lecture_id)
            
            elif query.data.startswith("vip_reject_lecture_"):
                lecture_id = query.data.replace("vip_reject_lecture_", "")
                await self.handle_vip_reject_lecture(update, context, lecture_id)
            
            elif query.data.startswith("vip_ban_teacher_"):
                teacher_id = int(query.data.replace("vip_ban_teacher_", ""))
                await self.handle_vip_ban_teacher(update, context, teacher_id)
            
            elif query.data == "vip_change_subscription_price":
                await self.handle_vip_change_subscription_price(query, context)
                return VIP_CHANGE_SUBSCRIPTION_PRICE
            
            # ============= باقي الأوامر =============
            elif query.data == "balance":
                await self.handle_balance_check(update, context)
            
            elif query.data == "back_home":
                await self.handle_back_home(update, context)
            
            elif query.data == "admin_services":
                await self.handle_admin_services(query)
            
            elif query.data.startswith("toggle_service_"):
                service = query.data.replace("toggle_service_", "")
                await self.handle_toggle_service(update, context, service)
            
            else:
                await query.answer("⏳ جاري التحميل...")
        
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرد: {e}")
            await query.answer("❌ حدث خطأ. حاول مرة أخرى")
    
    # ============= دوال مساعدة إضافية =============
    async def handle_balance_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض رصيد المستخدم"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        
        balance_text = f"""
💰 <b>رصيدك الحالي:</b> {user_data['balance']:,} دينار

🆔 <b>رقم حسابك:</b> <code>{user_id}</code>

📊 <b>آخر المعاملات:</b>
"""
        
        transactions = user_data.get('transactions', [])[-5:]
        if transactions:
            for trans in transactions:
                sign = "+" if trans['amount'] > 0 else ""
                date = trans['date'].split()[0]
                description = trans['description'][:30]
                balance_text += f"\n📅 {date}: {sign}{trans['amount']:,} - {description}"
        else:
            balance_text += "\n📭 لا توجد معاملات سابقة"
        
        balance_text += f"\n\n💵 <b>إجمالي الإنفاق:</b> {user_data.get('total_spent', 0):,} دينار"
        balance_text += f"\n💎 <b>إجمالي الأرباح:</b> {user_data.get('total_earned', 0):,} دينار"
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")],
            [InlineKeyboardButton("📥 شحن الرصيد", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ]
        
        await query.edit_message_text(
            balance_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_back_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """العودة للصفحة الرئيسية"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        # إعادة توجيه لاستدعاء الأمر start
        await self.start(Update(
            update_id=update.update_id,
            message=query.message,
            callback_query=query
        ), context)
    
    async def handle_vip_add_lecture(self, query, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إضافة محاضرة VIP"""
        user_id = query.from_user.id
        
        if not self.user_manager.is_vip(user_id):
            await query.answer("❌ يجب الاشتراك في VIP أولاً", show_alert=True)
            return
        
        await query.edit_message_text(
            "📤 <b>إضافة محاضرة VIP جديدة</b>\n\n"
            "📝 <b>الخطوة 1 من 4:</b>\n"
            "أدخل عنوان المحاضرة:\n\n"
            "💡 مثال: 'شرح الدرس الأول في الرياضيات'",
            parse_mode=ParseMode.HTML
        )
        
        return VIP_LECTURE_TITLE
    
    async def handle_vip_lecture_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة عنوان المحاضرة"""
        title = update.message.text.strip()
        
        if len(title) < 5:
            await update.message.reply_text("❌ <b>العنوان قصير جداً</b>\n\nأدخل عنواناً واضحاً (5 أحرف على الأقل):", parse_mode=ParseMode.HTML)
            return VIP_LECTURE_TITLE
        
        context.user_data['vip_lecture_title'] = title
        
        await update.message.reply_text(
            "✅ <b>تم حفظ العنوان</b>\n\n"
            "📝 <b>الخطوة 2 من 4:</b>\n"
            "أدخل وصف المحاضرة:\n\n"
            "💡 مثال: 'شرح مفصل للدرس الأول مع أمثلة تطبيقية'",
            parse_mode=ParseMode.HTML
        )
        
        return VIP_LECTURE_DESC
    
    async def handle_vip_lecture_desc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة وصف المحاضرة"""
        description = update.message.text.strip()
        
        if len(description) < 10:
            await update.message.reply_text("❌ <b>الوصف قصير جداً</b>\n\nأدخل وصفاً مفصلاً (10 أحرف على الأقل):", parse_mode=ParseMode.HTML)
            return VIP_LECTURE_DESC
        
        context.user_data['vip_lecture_desc'] = description
        
        await update.message.reply_text(
            "✅ <b>تم حفظ الوصف</b>\n\n"
            "📝 <b>الخطوة 3 من 4:</b>\n"
            "حدد سعر المحاضرة (اختياري):\n\n"
            "💡 أدخل 0 إذا كانت مجانية\n"
            "💸 أو أدخل السعر المطلوب",
            parse_mode=ParseMode.HTML
        )
        
        return VIP_LECTURE_PRICE
    
    async def handle_vip_lecture_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة سعر المحاضرة"""
        try:
            price = int(update.message.text.strip())
            
            if price < 0:
                await update.message.reply_text("❌ <b>السعر لا يمكن أن يكون سالباً</b>\n\nأدخل سعراً صحيحاً:", parse_mode=ParseMode.HTML)
                return VIP_LECTURE_PRICE
            
            context.user_data['vip_lecture_price'] = price
            
            await update.message.reply_text(
                "✅ <b>تم حفظ السعر</b>\n\n"
                "📝 <b>الخطوة 4 من 4:</b>\n"
                "أرسل ملف المحاضرة (فيديو):\n\n"
                "📹 يمكنك إرسال ملف فيديو\n"
                "📎 أو ملف PDF\n"
                "⚠️ الحد الأقصى: 50 ميجابايت",
                parse_mode=ParseMode.HTML
            )
            
            return VIP_LECTURE_FILE
            
        except ValueError:
            await update.message.reply_text("❌ <b>أدخل رقماً صحيحاً فقط</b>\n\nأدخل سعر المحاضرة:", parse_mode=ParseMode.HTML)
            return VIP_LECTURE_PRICE
    
    async def handle_vip_lecture_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ملف المحاضرة"""
        user_id = update.effective_user.id
        
        if not update.message.document and not update.message.video:
            await update.message.reply_text("❌ <b>لم ترسل ملفاً!</b>\n\nأرسل ملف المحاضرة (فيديو أو PDF):", parse_mode=ParseMode.HTML)
            return VIP_LECTURE_FILE
        
        file_info = {}
        
        if update.message.document:
            document = update.message.document
            file_info = {
                "file_id": document.file_id,
                "file_name": document.file_name or f"lecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "file_type": "document",
                "mime_type": document.mime_type,
                "file_size": document.file_size
            }
        elif update.message.video:
            video = update.message.video
            file_info = {
                "file_id": video.file_id,
                "file_name": f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                "file_type": "video",
                "mime_type": "video/mp4",
                "file_size": video.file_size,
                "duration": video.duration,
                "width": video.width,
                "height": video.height
            }
        
        # إضافة المحاضرة
        lecture_id = self.vip_manager.add_lecture(
            user_id,
            context.user_data['vip_lecture_title'],
            context.user_data['vip_lecture_desc'],
            file_info,
            context.user_data['vip_lecture_price']
        )
        
        # تنظيف بيانات السياق
        for key in ['vip_lecture_title', 'vip_lecture_desc', 'vip_lecture_price']:
            if key in context.user_data:
                del context.user_data[key]
        
        if lecture_id:
            # إشعار المدير
            admin_message = f"""
📤 <b>محاضرة VIP جديدة تنتظر الموافقة</b>

👤 <b>المعلم:</b> {user_id}
📛 <b>الاسم:</b> {self.user_manager.get_user(user_id)['first_name']}
📝 <b>العنوان:</b> {context.user_data.get('vip_lecture_title', 'بدون عنوان')}
💰 <b>السعر:</b> {context.user_data.get('vip_lecture_price', 0):,} دينار
🆔 <b>رقم المحاضرة:</b> {lecture_id}

⚡ <b>استخدم لوحة التحكم للموافقة أو الرفض</b>
"""
            await self.send_notification(ADMIN_ID, admin_message, context)
            
            await update.message.reply_text(
                f"✅ <b>تم إرسال المحاضرة للمراجعة!</b>\n\n"
                f"🆔 <b>رقم المحاضرة:</b> {lecture_id}\n"
                f"⏳ <b>الحالة:</b> في انتظار الموافقة\n\n"
                f"📞 <b>سيتم إعلامك عند الموافقة عليها.</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ <b>فشل في إضافة المحاضرة</b>", parse_mode=ParseMode.HTML)
        
        keyboard = [[InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔙", reply_markup=reply_markup)
        
        return ConversationHandler.END
    
    async def handle_vip_change_subscription_price(self, query, context: ContextTypes.DEFAULT_TYPE):
        """تغيير سعر اشتراك VIP"""
        current_price = self.vip_manager.get_subscription_price()
        
        await query.edit_message_text(
            f"💰 <b>تغيير سعر اشتراك VIP</b>\n\n"
            f"💵 <b>السعر الحالي:</b> {current_price:,} دينار شهرياً\n\n"
            f"🔢 <b>أدخل السعر الجديد:</b>\n"
            f"<code>5000</code>\n\n"
            f"❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        
        return VIP_CHANGE_SUBSCRIPTION_PRICE
    
    async def handle_vip_subscription_price_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تغيير سعر اشتراك VIP"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        text = update.message.text.strip()
        
        if not text.isdigit():
            await update.message.reply_text(
                "❌ <b>مبلغ غير صحيح!</b>\n\n"
                "يجب أن يكون المبلغ رقماً فقط\n"
                "أعد إدخال السعر:",
                parse_mode=ParseMode.HTML
            )
            return VIP_CHANGE_SUBSCRIPTION_PRICE
        
        new_price = int(text)
        
        if new_price <= 0:
            await update.message.reply_text(
                "❌ <b>السعر يجب أن يكون أكبر من صفر</b>\n\n"
                "أعد إدخال السعر:",
                parse_mode=ParseMode.HTML
            )
            return VIP_CHANGE_SUBSCRIPTION_PRICE
        
        self.vip_manager.update_subscription_price(new_price)
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير سعر الاشتراك بنجاح!</b>\n\n"
            f"💰 <b>السعر الجديد:</b> {new_price:,} دينار شهرياً",
            parse_mode=ParseMode.HTML
        )
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    async def handle_vip_ban_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int):
        """حظر معلم"""
        query = update.callback_query
        await query.answer()
        
        if self.vip_manager.ban_teacher(teacher_id):
            self.user_manager.remove_vip_subscription(teacher_id)
            
            notify_message = f"""
🚫 <b>تم حظر حسابك من نظام VIP!</b>

❌ <b>تم إلغاء اشتراكك وحظر حسابك</b>

📞 <b>للاستفسار:</b> @{SUPPORT_USERNAME}
"""
            await self.send_notification(teacher_id, notify_message, context)
            
            await query.answer("✅ تم حظر المعلم وإلغاء اشتراكه", show_alert=True)
        else:
            await query.answer("❌ فشل في حظر المعلم", show_alert=True)
        
        await self.handle_vip_review_lectures(query)
    
    async def show_vip_subscription_info(self, query):
        """عرض معلومات اشتراك VIP"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        
        vip_price = self.vip_manager.get_subscription_price()
        is_vip = self.user_manager.is_vip(user_id)
        
        if is_vip:
            expiry_date = user_data.get("vip_expiry")
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                days_left = (expiry - datetime.now()).days
                vip_status = f"✅ <b>مشترك VIP حتى:</b> {expiry_date}\n⏳ <b>متبقي:</b> {days_left} يوم"
            except:
                vip_status = "✅ <b>مشترك VIP</b>"
        else:
            vip_status = "❌ <b>غير مشترك</b>"
        
        message = f"""
👑 <b>نظام المحاضرات VIP</b>

📊 <b>حالتك:</b> {vip_status}

💰 <b>سعر الاشتراك الشهري:</b> {vip_price:,} دينار

🎯 <b>مزايا الاشتراك:</b>
• ✅ رفع محاضرات فيديو
• ✅ قسم خاص لمحاضراتك
• ✅ دخل إضافي من بيع المحاضرات
• ✅ لوحة تحكم خاصة
• ✅ دعم فني مميز

📝 <b>شروط الاشتراك:</b>
1. أن تكون معلماً أو محاضراً
2. دفع الاشتراك الشهري
3. الموافقة على المحاضرات من الإدارة
4. الالتزام بمعايير الجودة

💳 <b>رصيدك الحالي:</b> {user_data['balance']:,} دينار
"""
        
        keyboard = []
        
        if is_vip:
            keyboard.append([InlineKeyboardButton("📤 رفع محاضرة جديدة", callback_data="vip_add_lecture")])
            keyboard.append([InlineKeyboardButton("📚 محاضراتي", callback_data="vip_my_lectures")])
            keyboard.append([InlineKeyboardButton("📊 إحصائياتي", callback_data="vip_my_stats")])
        else:
            if user_data['balance'] >= vip_price:
                keyboard.append([InlineKeyboardButton("💳 اشتراك الآن", callback_data="vip_subscribe")])
            else:
                keyboard.append([InlineKeyboardButton("💰 شحن الرصيد", url=f"https://t.me/{SUPPORT_USERNAME}")])
        
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 إدارة VIP", callback_data="admin_vip_management")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_subscribe(self, query, context: ContextTypes.DEFAULT_TYPE):
        """الاشتراك في VIP"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        vip_price = self.vip_manager.get_subscription_price()
        
        if user_data['balance'] < vip_price:
            await query.answer(f"❌ رصيدك غير كافي! تحتاج {vip_price:,} دينار", show_alert=True)
            return
        
        new_balance, should_notify = self.user_manager.update_balance(user_id, -vip_price, "اشتراك VIP شهري")
        
        self.user_manager.add_vip_subscription(user_id, 1)
        
        notify_message = f"""
✅ <b>تم تفعيل اشتراك VIP بنجاح!</b>

💰 <b>المبلغ:</b> {vip_price:,} دينار
💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار
📅 <b>تاريخ الانتهاء:</b> {self.user_manager.get_user(user_id)['vip_expiry']}

🎉 <b>مبروك! يمكنك الآن رفع محاضراتك.</b>
"""
        await self.send_notification(user_id, notify_message, context)
        
        admin_message = f"""
👑 <b>اشتراك VIP جديد</b>

👤 <b>المستخدم:</b> {user_id}
📛 <b>الاسم:</b> {user_data['first_name']}
📅 <b>تاريخ الانتهاء:</b> {self.user_manager.get_user(user_id)['vip_expiry']}
"""
        await self.send_notification(ADMIN_ID, admin_message, context)
        
        await query.answer("✅ تم تفعيل اشتراك VIP بنجاح!", show_alert=True)
        await self.show_vip_subscription_info(query)
    
    async def show_vip_my_lectures(self, query):
        """عرض محاضرات المعلم"""
        user_id = query.from_user.id
        lectures = self.vip_manager.get_teacher_lectures(user_id)
        
        if not lectures:
            keyboard = [
                [InlineKeyboardButton("📤 إضافة محاضرة", callback_data="vip_add_lecture")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
            ]
            await query.edit_message_text(
                "📭 <b>لا توجد محاضرات لعرضها</b>\n\n"
                "يمكنك إضافة محاضرة جديدة من الزر أدناه",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = f"📚 <b>محاضراتي ({len(lectures)})</b>\n\n"
        
        keyboard = []
        for lecture in lectures[:10]:
            status_emoji = "✅" if lecture.get("status") == "approved" else "⏳"
            title = lecture.get("title", "بدون عنوان")[:30]
            price = lecture.get("price", 0)
            views = lecture.get("views", 0)
            
            btn_text = f"{status_emoji} {title}"
            if price > 0:
                btn_text += f" ({price:,} د)"
            
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_vip_lecture_{lecture['id']}")])
        
        keyboard.append([InlineKeyboardButton("📤 إضافة محاضرة", callback_data="vip_add_lecture")])
        keyboard.append([InlineKeyboardButton("📊 الإحصائيات", callback_data="vip_my_stats")])
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        user = update.effective_user
        
        # تحديث معلومات المستخدم
        self.user_manager.update_user_info(user.id, user.first_name, user.username)
        
        # التحقق من وضع الصيانة
        if self.settings_manager.is_maintenance_mode():
            maintenance_message = self.settings_manager.admin_settings.get("maintenance_message", 
                                                                         "البوت قيد الصيانة حالياً. الرجاء المحاولة لاحقاً.")
            await update.message.reply_text(maintenance_message, parse_mode=ParseMode.HTML)
            return
        
        # معالجة الملفات إذا كان المستخدم في حالة تلخيص
        if update.message.document and context.user_data.get('awaiting_pdf'):
            await self.handle_summarize_pdf(update, context)
        
        elif update.message.text:
            text = update.message.text
            
            if text.startswith('/'):
                await update.message.reply_text(
                    "🤖 <b>استخدم الأزرار للتفاعل مع البوت</b>\n\n"
                    "📝 اكتب /start لعرض القائمة الرئيسية",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "📝 <b>استخدم القائمة الرئيسية للوصول للخدمات</b>\n\n"
                    "💡 اكتب /start لفتح القائمة",
                    parse_mode=ParseMode.HTML
                )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأخطاء العام"""
        logger.error(f"❌ تحديث {update} تسبب في خطأ {context.error}")
        
        try:
            # إرسال رسالة خطأ للمستخدم
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ <b>حدث خطأ غير متوقع</b>\n\n"
                    f"🆘 تواصل مع الدعم الفني: @{SUPPORT_USERNAME}",
                    parse_mode=ParseMode.HTML
                )
        except:
            pass
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء المحادثة"""
        user_id = update.effective_user.id
        
        # تنظيف بيانات السياق
        for key in list(context.user_data.keys()):
            del context.user_data[key]
        
        await update.message.reply_text(
            "❌ <b>تم إلغاء العملية</b>\n\n"
            "🏠 العودة للقائمة الرئيسية",
            parse_mode=ParseMode.HTML
        )
        
        # العودة للصفحة الرئيسية
        await self.start(update, context)
        return ConversationHandler.END
    
    async def backup_scheduler(self):
        """جدولة النسخ الاحتياطي"""
        while self.is_running:
            try:
                # الانتظار 24 ساعة
                await asyncio.sleep(24 * 60 * 60)
                
                # إنشاء نسخة احتياطية
                backup_folder = EnhancedDataManager.create_backup()
                if backup_folder:
                    logger.info(f"📦 تم إنشاء نسخة احتياطية تلقائية في: {backup_folder}")
                    
                    # إشعار المدير
                    admin_message = f"""
📦 <b>نسخة احتياطية تلقائية</b>

✅ تم إنشاء نسخة احتياطية للبيانات
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
📁 الموقع: {backup_folder}

🔒 <b>البيانات في أمان</b>
"""
                    # يمكن إرسال الإشعار للمدير هنا
                    
            except Exception as e:
                logger.error(f"❌ خطأ في النسخ الاحتياطي التلقائي: {e}")
    
    def run(self):
        """تشغيل البوت"""
        print("=" * 60)
        print("🤖 بوت 'يلا نتعلم' التعليمي - الإصدار المحسن 3.0")
        print("=" * 60)
        print(f"👑 المدير: {ADMIN_ID}")
        print(f"🆘 الدعم: @{SUPPORT_USERNAME}")
        print(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        print(f"💎 الهدية الترحيبية: {self.settings_manager.get_welcome_bonus():,} دينار")
        print(f"👑 سعر VIP: {self.vip_manager.get_subscription_price():,} دينار شهرياً")
        print(f"🤖 الذكاء الاصطناعي: {'✅' if self.ai_service.is_initialized else '❌'}")
        print("=" * 60)
        print("✅ البوت يعمل الآن...")
        
        # إنشاء تطبيق البوت
        persistence = PicklePersistence(filepath=DATA_DIR / 'bot_persistence.pickle')
        app = Application.builder().token(TOKEN).persistence(persistence).build()
        
        # إعداد معالج المحادثة
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                CommandHandler("admin", self.admin_panel),
                CallbackQueryHandler(self.handle_callback)
            ],
            states={
                # نظام الإعفاء
                EXEMPTION_COURSE1: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_exemption_course1),
                    CallbackQueryHandler(self.handle_callback)
                ],
                EXEMPTION_COURSE2: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_exemption_course2),
                    CallbackQueryHandler(self.handle_callback)
                ],
                EXEMPTION_COURSE3: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_exemption_course3),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # تلخيص الملازم
                SUMMARIZE_PDF: [
                    MessageHandler(filters.Document.PDF | filters.TEXT & ~filters.COMMAND, self.handle_summarize_pdf),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # سؤال وجواب بالذكاء
                QA_QUESTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_qa_question),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # ساعدوني طلاب
                HELP_STUDENT_QUESTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_help_student_question),
                    CallbackQueryHandler(self.handle_callback)
                ],
                QUESTION_ANSWER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_question_answer),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # لوحة التحكم
                CHANGE_PRICE_SERVICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_change_price_amount),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHANGE_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_change_channel),
                    CallbackQueryHandler(self.handle_callback)
                ],
                VIP_CHANGE_SUBSCRIPTION_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_subscription_price_change),
                    CallbackQueryHandler(self.handle_callback)
                ],
                VIP_REJECT_REASON: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_reject_reason),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # نظام VIP
                VIP_LECTURE_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_lecture_title),
                    CallbackQueryHandler(self.handle_callback)
                ],
                VIP_LECTURE_DESC: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_lecture_desc),
                    CallbackQueryHandler(self.handle_callback)
                ],
                VIP_LECTURE_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_lecture_price),
                    CallbackQueryHandler(self.handle_callback)
                ],
                VIP_LECTURE_FILE: [
                    MessageHandler(filters.Document.ALL | filters.VIDEO | filters.TEXT & ~filters.COMMAND, self.handle_vip_lecture_file),
                    CallbackQueryHandler(self.handle_callback)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("start", self.start),
                CallbackQueryHandler(self.handle_callback, pattern="^back_home$|^admin_panel$")
            ]
        )
        
        # إضافة المعالجات
        app.add_handler(conv_handler)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.Document.PDF, self.handle_summarize_pdf))
        app.add_error_handler(self.error_handler)
        
        # تشغيل البوت
        self.is_running = True
        
        # بدء جدولة النسخ الاحتياطي
        self.backup_task = asyncio.create_task(self.backup_scheduler())
        
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

# ============= تشغيل البوت =============
if __name__ == "__main__":
    bot = EnhancedYallaNataalamBot()
    bot.run()
