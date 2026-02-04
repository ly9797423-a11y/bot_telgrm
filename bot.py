#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - البوت التعليمي للطلاب العراقيين
المطور: Allawi04@
"""

import logging
import json
import os
import re
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import PyPDF2
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from telegram.constants import ParseMode
import google.generativeai as genai
import requests

# ============= إعدادات البوت =============
TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
BOT_USERNAME = "@FC4Xbot"
ADMIN_ID = 6130994941
SUPPORT_USERNAME = "Allawi04"
GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"

# ============= حالات المحادثة =============
(
    ADMIN_MENU, CHARGE_USER, CHARGE_AMOUNT, PRICE_CHANGE, 
    MATERIAL_FILE, MATERIAL_DESC, MATERIAL_STAGE, 
    QUESTION_DETAILS, QUESTION_ANSWER, BAN_USER,
    CHANGE_CHANNEL, DELETE_MATERIAL, ADD_MATERIAL,
    VIEW_USER, TOGGLE_SERVICE
) = range(15)

# ============= إعداد التسعير =============
SERVICE_PRICES = {
    "exemption": 1000,      # حساب درجة الإعفاء
    "summarize": 1000,      # تلخيص الملازم
    "qa": 1000,             # سؤال وجواب
    "materials": 1000,      # ملازمي ومرشحاتي
    "help_student": 250     # ساعدوني طلاب (جديد)
}

# ============= إعداد الخدمات النشطة =============
ACTIVE_SERVICES = {
    "exemption": True,
    "summarize": True,
    "qa": True,
    "materials": True,
    "help_student": True
}

WELCOME_BONUS = 1000        # هدية الترحيب
REFERRAL_BONUS = 500        # مكافأة الدعوة
ANSWER_REWARD = 100         # مكافأة الإجابة على سؤال طالب

# ============= إعداد الملفات =============
DATA_FILE = "users_data.json"
MATERIALS_FILE = "materials_data.json"
ADMIN_FILE = "admin_settings.json"
QUESTIONS_FILE = "questions_data.json"
BANNED_FILE = "banned_users.json"
CHANNEL_FILE = "channel_info.json"
SERVICES_FILE = "services_status.json"

# ============= إعداد التسجيل =============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= إدارة البيانات =============
class DataManager:
    @staticmethod
    def load_data(filename: str, default=None):
        """تحميل البيانات من ملف JSON"""
        if default is None:
            default = {}
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return default
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return default

    @staticmethod
    def save_data(filename: str, data):
        """حفظ البيانات إلى ملف JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")

# ============= إدارة المستخدمين =============
class UserManager:
    def __init__(self):
        self.users = DataManager.load_data(DATA_FILE, {})
        self.banned_users = DataManager.load_data(BANNED_FILE, {})
        
    def get_user(self, user_id: int) -> Dict:
        """الحصول على بيانات المستخدم أو إنشاء مستخدم جديد"""
        user_id_str = str(user_id)
        
        # التحقق من الحظر
        if user_id_str in self.banned_users:
            return self.banned_users[user_id_str]
        
        if user_id_str not in self.users:
            self.users[user_id_str] = {
                "balance": WELCOME_BONUS,
                "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "first_name": "",
                "username": "",
                "referral_code": str(user_id),
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
                "total_spent": 0
            }
            self.save_users()
            logger.info(f"New user created: {user_id}")
        return self.users[user_id_str]
    
    def update_user_info(self, user_id: int, first_name: str, username: str = ""):
        """تحديث معلومات المستخدم"""
        user = self.get_user(user_id)
        user["first_name"] = first_name
        if username:
            user["username"] = username
        self.save_users()
    
    def can_ask_question(self, user_id: int) -> Tuple[bool, str]:
        """التحقق إذا كان يمكن للمستخدم طرح سؤال"""
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
                return False, f"⏳ يمكنك طرح سؤال جديد بعد {hours} ساعة و{minutes} دقيقة"
            return True, ""
        except:
            return True, ""
    
    def update_question_time(self, user_id: int):
        """تحديث وقت آخر سؤال"""
        user = self.get_user(user_id)
        user["last_question_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user["questions_asked"] = user.get("questions_asked", 0) + 1
        self.save_users()
    
    def update_balance(self, user_id: int, amount: int, description: str = "") -> int:
        """تحديد رصيد المستخدم"""
        user = self.get_user(user_id)
        old_balance = user.get("balance", 0)
        user["balance"] = old_balance + amount
        
        transaction = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "description": description,
            "balance_before": old_balance,
            "balance_after": user["balance"]
        }
        user.setdefault("transactions", []).append(transaction)
        
        # تحديث الإحصائيات
        if amount > 0:
            user["total_earned"] = user.get("total_earned", 0) + amount
        else:
            user["total_spent"] = user.get("total_spent", 0) + abs(amount)
        
        self.save_users()
        logger.info(f"Updated balance for user {user_id}: {old_balance} -> {user['balance']} ({amount})")
        return user["balance"]
    
    def set_pending_purchase(self, user_id: int, service: str, price: int):
        """تعيين عملية شراء معلقة"""
        user = self.get_user(user_id)
        user["pending_purchase"] = {
            "service": service,
            "price": price,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_users()
    
    def complete_purchase(self, user_id: int) -> bool:
        """إكمال عملية الشراء"""
        user = self.get_user(user_id)
        if user.get("pending_purchase"):
            purchase = user["pending_purchase"]
            # تسجيل الخدمة المستخدمة
            user.setdefault("used_services", []).append({
                "service": purchase["service"],
                "date": purchase["timestamp"],
                "cost": purchase["price"]
            })
            user["pending_purchase"] = None
            self.save_users()
            return True
        return False
    
    def cancel_purchase(self, user_id: int):
        """إلغاء عملية الشراء"""
        user = self.get_user(user_id)
        if user.get("pending_purchase"):
            purchase = user["pending_purchase"]
            # استرجاع المبلغ
            self.update_balance(user_id, purchase["price"], f"استرجاع رصيد لخدمة: {purchase['service']}")
            user["pending_purchase"] = None
            self.save_users()
            return True
        return False
    
    def get_all_users(self) -> List[Tuple[str, Dict]]:
        """الحصول على جميع المستخدمين"""
        return list(self.users.items())
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بواسطة ID"""
        return self.users.get(str(user_id))
    
    def get_top_users(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """الحصول على أفضل المستخدمين حسب الرصيد"""
        users_list = list(self.users.items())
        users_list.sort(key=lambda x: x[1].get("balance", 0), reverse=True)
        return users_list[:limit]
    
    def save_users(self):
        """حفظ بيانات المستخدمين"""
        DataManager.save_data(DATA_FILE, self.users)
    
    def save_banned(self):
        """حفظ المستخدمين المحظورين"""
        DataManager.save_data(BANNED_FILE, self.banned_users)

# ============= إدارة المواد التعليمية =============
class MaterialsManager:
    def __init__(self):
        self.materials = DataManager.load_data(MATERIALS_FILE, [])
    
    def get_materials_by_stage(self, stage: str) -> List[Dict]:
        """الحصول على المواد حسب المرحلة"""
        return [m for m in self.materials if m.get("stage") == stage]
    
    def get_all_stages(self) -> List[str]:
        """الحصول على جميع المراحل المتاحة"""
        stages = set(m.get("stage", "") for m in self.materials)
        return [s for s in stages if s]
    
    def add_material(self, material_data: Dict):
        """إضافة مادة جديدة"""
        material_data["id"] = len(self.materials) + 1
        material_data["added_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.materials.append(material_data)
        self.save_materials()
        logger.info(f"Added material: {material_data.get('name', 'Unknown')}")
    
    def delete_material(self, material_id: int) -> bool:
        """حذف مادة"""
        original_count = len(self.materials)
        self.materials = [m for m in self.materials if m.get("id") != material_id]
        
        if len(self.materials) < original_count:
            self.save_materials()
            logger.info(f"Deleted material ID: {material_id}")
            return True
        return False
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """الحصول على مادة بواسطة ID"""
        for material in self.materials:
            if material.get("id") == material_id:
                return material
        return None
    
    def save_materials(self):
        """حفظ المواد"""
        DataManager.save_data(MATERIALS_FILE, self.materials)

# ============= إدارة الأسئلة =============
class QuestionsManager:
    def __init__(self):
        self.questions = DataManager.load_data(QUESTIONS_FILE, [])
    
    def add_question(self, user_id: int, question_text: str) -> str:
        """إضافة سؤال جديد"""
        question_id = str(uuid.uuid4())[:8].upper()
        question_data = {
            "id": question_id,
            "user_id": user_id,
            "question": question_text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "answers": [],
            "answered": False,
            "views": 0
        }
        self.questions.append(question_data)
        self.save_questions()
        logger.info(f"Added question {question_id} by user {user_id}")
        return question_id
    
    def add_answer(self, question_id: str, answerer_id: int, answer_text: str) -> Tuple[bool, Optional[int]]:
        """إضافة إجابة على سؤال"""
        for question in self.questions:
            if question["id"] == question_id and not question["answered"]:
                answer_data = {
                    "answerer_id": answerer_id,
                    "answer": answer_text,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                question["answers"].append(answer_data)
                question["answered"] = True
                self.save_questions()
                logger.info(f"Added answer to question {question_id} by user {answerer_id}")
                return True, question["user_id"]
        return False, None
    
    def get_active_questions(self, exclude_user_id: int = None) -> List[Dict]:
        """الحصول على الأسئلة النشطة"""
        active_questions = [q for q in self.questions if not q["answered"]]
        
        if exclude_user_id:
            active_questions = [q for q in active_questions if q["user_id"] != exclude_user_id]
        
        # زيادة عدد المشاهدات
        for question in active_questions[:10]:
            question["views"] = question.get("views", 0) + 1
        
        return active_questions[:10]  # عرض أول 10 أسئلة فقط
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """الحصول على سؤال بواسطة ID"""
        for question in self.questions:
            if question["id"] == question_id:
                return question
        return None
    
    def remove_old_questions(self, days: int = 7):
        """إزالة الأسئلة القديمة"""
        cutoff_date = datetime.now() - timedelta(days=days)
        original_count = len(self.questions)
        
        self.questions = [
            q for q in self.questions 
            if datetime.strptime(q["date"], "%Y-%m-%d %H:%M:%S") > cutoff_date
        ]
        
        if len(self.questions) < original_count:
            self.save_questions()
            logger.info(f"Removed {original_count - len(self.questions)} old questions")
    
    def save_questions(self):
        """حفظ الأسئلة"""
        DataManager.save_data(QUESTIONS_FILE, self.questions)

# ============= إدارة القناة والخدمات =============
class SettingsManager:
    def __init__(self):
        self.channel_info = DataManager.load_data(CHANNEL_FILE, {
            "channel_link": "https://t.me/FCJCV",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self.services_status = DataManager.load_data(SERVICES_FILE, ACTIVE_SERVICES.copy())
        
        self.admin_settings = DataManager.load_data(ADMIN_FILE, {
            "maintenance": False,
            "prices": SERVICE_PRICES.copy(),
            "welcome_bonus": WELCOME_BONUS,
            "referral_bonus": REFERRAL_BONUS,
            "answer_reward": ANSWER_REWARD,
            "notify_new_users": True,
            "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    def get_channel_link(self) -> str:
        """الحصول على رابط القناة"""
        return self.channel_info.get("channel_link", "https://t.me/FCJCV")
    
    def update_channel_link(self, new_link: str):
        """تحديث رابط القناة"""
        self.channel_info["channel_link"] = new_link
        self.channel_info["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_channel_info()
    
    def is_service_active(self, service: str) -> bool:
        """التحقق إذا كانت الخدمة نشطة"""
        return self.services_status.get(service, True)
    
    def toggle_service(self, service: str) -> bool:
        """تفعيل/تعطيل خدمة"""
        if service in self.services_status:
            self.services_status[service] = not self.services_status[service]
            self.save_services_status()
            return self.services_status[service]
        return False
    
    def get_active_services(self) -> List[str]:
        """الحصول على الخدمات النشطة"""
        return [service for service, active in self.services_status.items() if active]
    
    def get_all_services(self) -> Dict[str, bool]:
        """الحصول على جميع الخدمات وحالتها"""
        return self.services_status.copy()
    
    def get_price(self, service: str) -> int:
        """الحصول على سعر الخدمة"""
        return self.admin_settings.get("prices", {}).get(service, 1000)
    
    def update_price(self, service: str, price: int):
        """تحديث سعر الخدمة"""
        if "prices" not in self.admin_settings:
            self.admin_settings["prices"] = {}
        self.admin_settings["prices"][service] = price
        self.save_admin_settings()
    
    def get_welcome_bonus(self) -> int:
        """الحصول على قيمة الهدية الترحيبية"""
        return self.admin_settings.get("welcome_bonus", WELCOME_BONUS)
    
    def update_welcome_bonus(self, amount: int):
        """تحديث قيمة الهدية الترحيبية"""
        self.admin_settings["welcome_bonus"] = amount
        self.save_admin_settings()
    
    def save_channel_info(self):
        """حفظ معلومات القناة"""
        DataManager.save_data(CHANNEL_FILE, self.channel_info)
    
    def save_services_status(self):
        """حفظ حالة الخدمات"""
        DataManager.save_data(SERVICES_FILE, self.services_status)
    
    def save_admin_settings(self):
        """حفظ إعدادات المدير"""
        DataManager.save_data(ADMIN_FILE, self.admin_settings)

# ============= الذكاء الاصطناعي =============
class AIService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.setup_ai()
    
    def setup_ai(self):
        """إعداد الذكاء الاصطناعي"""
        try:
            genai.configure(api_key=self.api_key)
            
            # قائمة النماذج المتاحة
            models_to_try = [
                'gemini-1.5-pro-latest',
                'gemini-1.0-pro-latest',
                'gemini-pro',
                'models/gemini-pro'
            ]
            
            for model_name in models_to_try:
                try:
                    logger.info(f"جرب نموذج: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    # اختبار النموذج
                    test_response = self.model.generate_content("مرحباً")
                    if test_response.text:
                        logger.info(f"✅ تم تهيئة النموذج بنجاح: {model_name}")
                        break
                except Exception as e:
                    logger.warning(f"❌ فشل مع النموذج {model_name}: {e}")
                    continue
            
            if not self.model:
                logger.error("❌ جميع نماذج الذكاء الاصطناعي فشلت")
                
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة الذكاء الاصطناعي: {e}")
    
    def summarize_pdf(self, pdf_path: str) -> str:
        """تلخيص ملف PDF"""
        try:
            if not self.model:
                return "❌ خدمة الذكاء الاصطناعي غير متاحة حالياً"
            
            # استخراج النص من PDF
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if len(text) < 100:
                return "❌ النص قصير جداً للتلخيص"
            
            # طلب التلخيص
            prompt = f"""
            أنت مساعد تعليمي للطلاب العراقيين. قم بتلخيص النص التعليمي التالي:
            
            {text[:3000]}
            
            المتطلبات:
            1. استخدم اللغة العربية الفصحى
            2. ركز على النقاط الرئيسية
            3. حذف المعلومات غير الأساسية
            4. نظم النقاط بشكل منطقي
            5. اجعل التلخيص مفيداً للدراسة
            
            قدم التلخيص في فقرات واضحة.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"❌ خطأ في تلخيص PDF: {e}")
            return f"❌ حدث خطأ في التلخيص: {str(e)[:100]}"
    
    def answer_question(self, question: str) -> str:
        """الإجابة على الأسئلة التعليمية"""
        try:
            if not self.model:
                return "❌ خدمة الذكاء الاصطناعي غير متاحة حالياً"
            
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
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإجابة على السؤال: {e}")
            return f"❌ حدث خطأ في الإجابة: {str(e)[:100]}"
    
    def create_summary_pdf(self, original_text: str, summary: str, output_path: str) -> bool:
        """إنشاء ملف PDF للتلخيص"""
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            # العنوان
            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, height - 50, "تلخيص الملزمة التعليمية")
            c.line(50, height - 65, width - 50, height - 65)
            
            # تاريخ التلخيص
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 90, f"تاريخ التلخيص: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
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
                try:
                    reshaped_text = arabic_reshaper.reshape(line)
                    bidi_text = get_display(reshaped_text)
                    display_text = bidi_text[:80]
                except:
                    display_text = line[:80]
                
                c.drawString(50, y_position, display_text)
                y_position -= 20
            
            c.save()
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء PDF: {e}")
            return False

# ============= الفئة الرئيسية للبوت =============
class YallaNataalamBot:
    def __init__(self):
        self.user_manager = UserManager()
        self.materials_manager = MaterialsManager()
        self.questions_manager = QuestionsManager()
        self.settings_manager = SettingsManager()
        self.ai_service = AIService(GEMINI_API_KEY)
        
        logger.info("✅ تم تهيئة البوت بنجاح")
        logger.info(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        logger.info(f"💎 الهدية: {self.settings_manager.get_welcome_bonus()} دينار")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء البوت"""
        user = update.effective_user
        
        # تحديث معلومات المستخدم
        self.user_manager.update_user_info(user.id, user.first_name, user.username)
        
        # الحصول على بيانات المستخدم
        user_data = self.user_manager.get_user(user.id)
        
        # عرض ID المستخدم
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
        
        # إنشاء الأزرار بناءً على الخدمات النشطة
        keyboard = []
        active_services = self.settings_manager.get_active_services()
        
        service_buttons = {
            "exemption": ("🧮 حساب درجة الإعفاء", "service_exemption"),
            "summarize": ("📚 تلخيص الملازم", "service_summarize"),
            "qa": ("❓ سؤال وجواب بالذكاء", "service_qa"),
            "materials": ("📖 ملازمي ومرشحاتي", "service_materials"),
            "help_student": ("🤝 ساعدوني طلاب", "service_help_student")
        }
        
        # إضافة الخدمات النشطة
        row = []
        for service, (text, callback) in service_buttons.items():
            if service in active_services:
                price = self.settings_manager.get_price(service)
                button_text = f"{text} ({price:,} د)"
                row.append(InlineKeyboardButton(button_text, callback_data=callback))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        if row:
            keyboard.append(row)
        
        # إضافة الأزرار الأخرى
        keyboard.append([
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")
        ])
        
        keyboard.append([
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite"),
            InlineKeyboardButton("📢 قناة البوت", url=self.settings_manager.get_channel_link())
        ])
        
        keyboard.append([
            InlineKeyboardButton("🆘 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}")
        ])
        
        if user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_service_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اختيار الخدمة"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        service = query.data.replace("service_", "")
        
        # التحقق من نشاط الخدمة
        if not self.settings_manager.is_service_active(service):
            await query.edit_message_text(
                "⏸️ <b>هذه الخدمة غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                "📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # الحصول على بيانات المستخدم
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price(service)
        
        # التحقق من الرصيد
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
        
        # تعيين عملية شراء معلقة
        self.user_manager.set_pending_purchase(user_id, service, price)
        
        if service == "exemption":
            await self.show_exemption_calculator(query)
        
        elif service == "summarize":
            await query.edit_message_text(
                "📤 <b>أرسل ملف PDF المراد تلخيصه</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                "⏳ قد تستغرق العملية بضع دقائق\n"
                "⚠️ <b>سيتم خصم المبلغ بعد إتمام الخدمة</b>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['awaiting_pdf'] = True
        
        elif service == "qa":
            await query.edit_message_text(
                "❓ <b>أرسل سؤالك الآن</b>\n\n"
                f"💰 سعر الخدمة: {price:,} دينار\n"
                f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
                "⏳ جاهز للإجابة على أسئلتك\n"
                "⚠️ <b>سيتم خصم المبلغ بعد إتمام الخدمة</b>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['awaiting_question'] = True
        
        elif service == "materials":
            await self.show_materials_menu(query)
        
        elif service == "help_student":
            await self.handle_help_student(query, context)
    
    async def show_exemption_calculator(self, query):
        """عرض آلة حساب الإعفاء"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("exemption")
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="back_home")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧮 <b>حاسبة درجة الإعفاء</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "أدخل درجاتك لثلاثة كورسات:\n"
            "1. درجة الكورس الأول\n"
            "2. درجة الكورس الثاني\n"
            "3. درجة الكورس الثالث\n\n"
            "📝 <b>أرسل الدرجات بهذا الشكل:</b>\n"
            "<code>90 85 95</code>\n\n"
            "🎯 <b>المعدل المطلوب للإعفاء:</b> 90 فما فوق\n"
            "⚠️ <b>سيتم خصم المبلغ بعد الحساب</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_exemption_calculation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة حساب درجة الإعفاء"""
        user_id = update.effective_user.id
        
        try:
            text = update.message.text.strip()
            
            if len(text.split()) >= 3:
                scores = list(map(float, text.split()[:3]))
                
                # التحقق من الدرجات
                for score in scores:
                    if score < 0 or score > 100:
                        await update.message.reply_text("❌ <b>الدرجات يجب أن تكون بين 0 و 100</b>", parse_mode=ParseMode.HTML)
                        self.user_manager.cancel_purchase(user_id)
                        return
                
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
                
                # إكمال عملية الشراء
                if self.user_manager.complete_purchase(user_id):
                    # خصم المبلغ
                    price = self.settings_manager.get_price("exemption")
                    new_balance = self.user_manager.update_balance(user_id, -price, f"حساب درجة الإعفاء")
                    
                    message += f"\n💰 تم خصم: {price:,} دينار"
                    message += f"\n💳 رصيدك المتبقي: {new_balance:,} دينار"
                    
                    # حفظ الدرجات
                    user_data = self.user_manager.get_user(user_id)
                    user_data.setdefault("exemption_scores", []).append({
                        "scores": scores,
                        "average": average,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "exempted": average >= 90
                    })
                    self.user_manager.save_users()
                    
                    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
                    
                    # زر العودة
                    keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("🔙", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
                    self.user_manager.cancel_purchase(user_id)
                
            else:
                await update.message.reply_text("❌ <b>يجب إدخال 3 درجات</b>\n\nأعد إدخال الدرجات:", parse_mode=ParseMode.HTML)
                
        except ValueError:
            await update.message.reply_text("❌ <b>أدخل أرقاماً صحيحة فقط</b>\n\nأعد إدخال الدرجات:", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        except Exception as e:
            logger.error(f"❌ خطأ في حساب الإعفاء: {e}")
            await update.message.reply_text("❌ <b>حدث خطأ في الحساب</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
    
    async def handle_pdf_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ملف PDF للتلخيص"""
        user_id = update.effective_user.id
        
        if not context.user_data.get('awaiting_pdf'):
            return
        
        document = update.message.document
        
        # التحقق من نوع الملف
        if not document.mime_type == 'application/pdf':
            await update.message.reply_text("❌ <b>يرجى إرسال ملف PDF فقط</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return
        
        # إرسال رسالة الانتظار
        processing_msg = await update.message.reply_text("⏳ <b>جاري معالجة الملف...</b>", parse_mode=ParseMode.HTML)
        
        try:
            # تحميل الملف
            file = await document.get_file()
            pdf_path = f"temp_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            await file.download_to_drive(pdf_path)
            
            await processing_msg.edit_text("📖 <b>جاري قراءة الملف...</b>", parse_mode=ParseMode.HTML)
            
            # استخراج النص من PDF
            text = ""
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                await processing_msg.edit_text(f"❌ <b>خطأ في قراءة الملف:</b> {str(e)[:100]}", parse_mode=ParseMode.HTML)
                os.remove(pdf_path)
                self.user_manager.cancel_purchase(user_id)
                return
            
            if len(text) < 100:
                await processing_msg.edit_text("❌ <b>الملف فارغ أو لا يحتوي على نص كافٍ</b>", parse_mode=ParseMode.HTML)
                os.remove(pdf_path)
                self.user_manager.cancel_purchase(user_id)
                return
            
            await processing_msg.edit_text("🤖 <b>جاري التلخيص بالذكاء الاصطناعي...</b>", parse_mode=ParseMode.HTML)
            
            # استخدام الذكاء الاصطناعي للتلخيص
            summary = self.ai_service.summarize_pdf(pdf_path)
            
            if summary.startswith("❌"):
                await processing_msg.edit_text(f"{summary}\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                os.remove(pdf_path)
                self.user_manager.cancel_purchase(user_id)
                return
            
            await processing_msg.edit_text("📄 <b>جاري إنشاء ملف PDF جديد...</b>", parse_mode=ParseMode.HTML)
            
            # إنشاء ملف PDF جديد
            output_path = f"summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            success = self.ai_service.create_summary_pdf(text[:1000], summary, output_path)
            
            if success:
                # إكمال عملية الشراء وخصم المبلغ
                if self.user_manager.complete_purchase(user_id):
                    price = self.settings_manager.get_price("summarize")
                    new_balance = self.user_manager.update_balance(user_id, -price, f"تلخيص ملف PDF")
                    
                    # إرسال الملف للمستخدم
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
                    os.remove(pdf_path)
                    os.remove(output_path)
                    
                    # زر العودة
                    keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text("🔙", reply_markup=reply_markup)
                else:
                    await processing_msg.edit_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
                    os.remove(pdf_path)
                    if os.path.exists(output_path):
                        os.remove(output_path)
            else:
                await processing_msg.edit_text("❌ <b>فشل في إنشاء ملف PDF</b>\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                os.remove(pdf_path)
                self.user_manager.cancel_purchase(user_id)
        
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة PDF: {e}")
            await processing_msg.edit_text("❌ <b>حدث خطأ في معالجة الملف</b>\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        
        context.user_data['awaiting_pdf'] = False
    
    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأسئلة بالذكاء الاصطناعي"""
        user_id = update.effective_user.id
        
        if not context.user_data.get('awaiting_question'):
            return
        
        question = update.message.text.strip()
        
        if len(question) < 5:
            await update.message.reply_text("❌ <b>السؤال قصير جداً</b>\n\nيرجى كتابة سؤال مفصل", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return
        
        # إرسال رسالة الانتظار
        processing_msg = await update.message.reply_text("🤖 <b>جاري البحث عن الإجابة...</b>", parse_mode=ParseMode.HTML)
        
        try:
            # استخدام الذكاء الاصطناعي للإجابة
            answer = self.ai_service.answer_question(question)
            
            if answer.startswith("❌"):
                await processing_msg.edit_text(f"{answer}\n\n⚠️ <b>تم استرجاع المبلغ</b>", parse_mode=ParseMode.HTML)
                self.user_manager.cancel_purchase(user_id)
                return
            
            # إكمال عملية الشراء وخصم المبلغ
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
                
                # زر العودة
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
        
        context.user_data['awaiting_question'] = False
    
    async def handle_help_student(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالجة خدمة ساعدوني طلاب"""
        user_id = query.from_user.id
        
        # التحقق من إمكانية طرح سؤال
        can_ask, message = self.user_manager.can_ask_question(user_id)
        if not can_ask:
            await query.edit_message_text(
                f"⏳ <b>لا يمكنك طرح سؤال جديد الآن</b>\n\n{message}\n\n"
                f"💡 يمكنك الإجابة على أسئلة الآخرين وكسب {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة",
                parse_mode=ParseMode.HTML
            )
            return
        
        # التحقق من الرصيد
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
        
        # تعيين عملية شراء معلقة
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
            f"🎯 <b>المكافأة للمجيب:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['awaiting_help_question'] = True
    
    async def handle_help_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة سؤال خدمة ساعدوني طلاب"""
        user_id = update.effective_user.id
        
        if not context.user_data.get('awaiting_help_question'):
            return
        
        question_text = update.message.text.strip()
        
        if len(question_text) < 10:
            await update.message.reply_text("❌ <b>السؤال قصير جداً</b>\n\nيرجى كتابة سؤال مفصل", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
            return
        
        # إكمال عملية الشراء وخصم المبلغ
        if self.user_manager.complete_purchase(user_id):
            price = self.settings_manager.get_price("help_student")
            new_balance = self.user_manager.update_balance(user_id, -price, f"طرح سؤال في ساعدوني طلاب")
            
            # تحديث وقت آخر سؤال
            self.user_manager.update_question_time(user_id)
            
            # إضافة السؤال إلى قاعدة البيانات
            question_id = self.questions_manager.add_question(user_id, question_text)
            
            await update.message.reply_text(
                f"✅ <b>تم إضافة سؤالك بنجاح!</b>\n\n"
                f"🆔 <b>رقم السؤال:</b> {question_id}\n"
                f"💰 <b>تم خصم:</b> {price:,} دينار\n"
                f"💳 <b>رصيدك المتبقي:</b> {new_balance:,} دينار\n\n"
                f"⏳ <b>الحالة:</b> في انتظار الإجابة\n"
                f"🎯 <b>المكافأة للمجيب:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة\n\n"
                f"💡 سوف تتلقى إشعاراً عندما يتم الرد على سؤالك",
                parse_mode=ParseMode.HTML
            )
            
            # عرض الأسئلة المتاحة للإجابة
            await self.show_available_questions(update, context, user_id)
        else:
            await update.message.reply_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
        
        context.user_data['awaiting_help_question'] = False
    
    async def show_available_questions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, exclude_user_id: int = None):
        """عرض الأسئلة المتاحة للإجابة"""
        active_questions = self.questions_manager.get_active_questions(exclude_user_id)
        
        if not active_questions:
            keyboard = [[InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📭 <b>لا توجد أسئلة متاحة للإجابة حالياً</b>\n\n"
                "يمكنك العودة لاحقاً للبحث عن أسئلة للإجابة عليها",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        
        message = f"🤝 <b>الأسئلة المتاحة للإجابة:</b>\n\n"
        message += f"🎯 <b>مكافأة الإجابة:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة\n\n"
        
        keyboard = []
        for question in active_questions:
            question_text = question['question'][:50] + "..." if len(question['question']) > 50 else question['question']
            date = question['date'].split()[0]
            views = question.get('views', 0)
            
            btn_text = f"❓ {question_text} ({views} 👁️)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_question_{question['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_questions")])
        keyboard.append([InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_view_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: str):
        """عرض سؤال للإجابة"""
        query = update.callback_query
        await query.answer()
        
        question = self.questions_manager.get_question_by_id(question_id)
        
        if not question:
            await query.edit_message_text("❌ <b>هذا السؤال لم يعد موجوداً</b>", parse_mode=ParseMode.HTML)
            return
        
        message = f"❓ <b>السؤال #{question_id}</b>\n\n"
        message += f"📅 <b>التاريخ:</b> {question['date']}\n"
        message += f"👁️ <b>المشاهدات:</b> {question.get('views', 0)}\n\n"
        message += f"📝 <b>نص السؤال:</b>\n{question['question']}\n\n"
        message += f"🎯 <b>المكافأة:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة"
        
        keyboard = [
            [InlineKeyboardButton("💬 جاوب على السؤال", callback_data=f"answer_question_{question_id}")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="refresh_questions")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_answer_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: str):
        """بدء الإجابة على سؤال"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # التحقق إذا كان السؤال لا يزال نشطاً
        question = self.questions_manager.get_question_by_id(question_id)
        if not question or question["answered"]:
            await query.edit_message_text("❌ <b>هذا السؤال تمت الإجابة عليه مسبقاً</b>", parse_mode=ParseMode.HTML)
            return
        
        # التحقق إذا كان المستخدم يحاول الإجابة على سؤاله
        if question["user_id"] == user_id:
            await query.edit_message_text("❌ <b>لا يمكنك الإجابة على سؤالك الخاص</b>", parse_mode=ParseMode.HTML)
            return
        
        context.user_data['answering_question_id'] = question_id
        context.user_data['answering_question_text'] = question['question']
        
        await query.edit_message_text(
            f"💬 <b>الإجابة على السؤال #{question_id}</b>\n\n"
            f"📝 <b>السؤال:</b>\n{question['question']}\n\n"
            f"✏️ <b>أرسل إجابتك الآن:</b>\n"
            f"• كن دقيقاً وواضحاً\n"
            f"• استخدم اللغة العربية\n"
            f"• قدم معلومات مفيدة\n\n"
            f"🎯 <b>المكافأة:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة",
            parse_mode=ParseMode.HTML
        )
        
        return QUESTION_ANSWER
    
    async def handle_question_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إجابة السؤال"""
        user_id = update.effective_user.id
        question_id = context.user_data.get('answering_question_id')
        
        if not question_id:
            return ConversationHandler.END
        
        answer_text = update.message.text.strip()
        
        if len(answer_text) < 10:
            await update.message.reply_text("❌ <b>الإجابة قصيرة جداً</b>\n\nيرجى كتابة إجابة مفصلة", parse_mode=ParseMode.HTML)
            return QUESTION_ANSWER
        
        # إضافة الإجابة إلى قاعدة البيانات
        success, question_owner_id = self.questions_manager.add_answer(question_id, user_id, answer_text)
        
        if success:
            # منح مكافأة للمجيب
            reward = self.settings_manager.admin_settings.get('answer_reward', 100)
            self.user_manager.update_balance(user_id, reward, f"مكافأة إجابة على سؤال #{question_id}")
            
            # تحديث إحصائيات المستخدم
            user_data = self.user_manager.get_user(user_id)
            user_data["questions_answered"] = user_data.get("questions_answered", 0) + 1
            self.user_manager.save_users()
            
            await update.message.reply_text(
                f"✅ <b>تم إرسال إجابتك بنجاح!</b>\n\n"
                f"💰 <b>المكافأة:</b> +{reward} نقطة\n"
                f"💳 <b>رصيدك الحالي:</b> {user_data['balance']:,} دينار",
                parse_mode=ParseMode.HTML
            )
            
            # إرسال الإجابة لصاحب السؤال
            try:
                question_owner_data = self.user_manager.get_user(question_owner_id)
                if question_owner_data:
                    await context.bot.send_message(
                        chat_id=question_owner_id,
                        text=f"💬 <b>تمت الإجابة على سؤالك #{question_id}</b>\n\n"
                             f"📝 <b>سؤالك:</b>\n{context.user_data.get('answering_question_text', '')}\n\n"
                             f"💡 <b>الإجابة:</b>\n{answer_text}\n\n"
                             f"👍 شكراً للمجيب على مساعدتك!",
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الإجابة لصاحب السؤال: {e}")
        else:
            await update.message.reply_text("❌ <b>فشل في إرسال الإجابة</b>\n\nقد يكون السؤال قد تمت الإجابة عليه مسبقاً", parse_mode=ParseMode.HTML)
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('answering_question_id', None)
        context.user_data.pop('answering_question_text', None)
        
        # عرض الأسئلة المتاحة للإجابة
        await self.show_available_questions(update, context, user_id)
        return ConversationHandler.END
    
    async def show_materials_menu(self, query):
        """عرض قائمة المواد"""
        user_id = query.from_user.id
        
        # التحقق من نشاط الخدمة
        if not self.settings_manager.is_service_active("materials"):
            await query.edit_message_text(
                "⏸️ <b>خدمة المواد غير متاحة حالياً</b>\n\n"
                "تم تعطيل هذه الخدمة مؤقتاً.\n"
                "📞 للاستفسار: @{SUPPORT_USERNAME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # التحقق من الرصيد
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
        
        # تعيين عملية شراء معلقة
        self.user_manager.set_pending_purchase(user_id, "materials", price)
        
        keyboard = []
        for stage in stages:
            # حساب عدد المواد في هذه المرحلة
            materials_count = len(self.materials_manager.get_materials_by_stage(stage))
            btn_text = f"📘 {stage} ({materials_count})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"stage_{stage}")])
        
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
    
    async def show_stage_materials(self, query, stage: str):
        """عرض مواد مرحلة محددة"""
        user_id = query.from_user.id
        
        # إكمال عملية الشراء وخصم المبلغ
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
                btn_text = f"📄 {material.get('name', 'بدون اسم')}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"download_material_{material['id']}")])
                
                message += f"<b>📖 {material.get('name', 'بدون اسم')}</b>\n"
                description = material.get('description', '')
                if len(description) > 60:
                    description = description[:60] + "..."
                message += f"📝 {description}\n\n"
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="service_materials")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text("❌ <b>حدث خطأ في المعاملة</b>", parse_mode=ParseMode.HTML)
            self.user_manager.cancel_purchase(user_id)
    
    async def handle_download_material(self, update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
        """تحميل مادة"""
        query = update.callback_query
        await query.answer()
        
        material = self.materials_manager.get_material(material_id)
        
        if not material:
            await query.edit_message_text("❌ <b>المادة غير موجودة</b>", parse_mode=ParseMode.HTML)
            return
        
        # التحقق إذا كان هناك ملف
        file_path = material.get('file_path')
        file_id = material.get('file_id')
        
        if file_path and os.path.exists(file_path):
            try:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=open(file_path, 'rb'),
                    filename=f"{material.get('name', 'مادة')}.pdf",
                    caption=f"📚 <b>{material.get('name', 'بدون اسم')}</b>\n\n"
                           f"📝 {material.get('description', '')}\n"
                           f"🎓 {material.get('stage', 'غير محدد')}\n"
                           f"📅 {material.get('added_date', 'غير معروف')}",
                    parse_mode=ParseMode.HTML
                )
                await query.answer("✅ تم إرسال الملف")
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الملف: {e}")
                await query.answer("❌ فشل في إرسال الملف")
        elif file_id:
            try:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=file_id,
                    caption=f"📚 <b>{material.get('name', 'بدون اسم')}</b>\n\n"
                           f"📝 {material.get('description', '')}\n"
                           f"🎓 {material.get('stage', 'غير محدد')}\n"
                           f"📅 {material.get('added_date', 'غير معروف')}",
                    parse_mode=ParseMode.HTML
                )
                await query.answer("✅ تم إرسال الملف")
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الملف: {e}")
                await query.answer("❌ فشل في إرسال الملف")
        else:
            await query.answer("❌ لا يوجد ملف لهذه المادة")
    
    # ============= لوحة التحكم =============
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فتح لوحة التحكم"""
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
        
        panel_text = f"""
👑 <b>لوحة التحكم الإدارية</b>

📊 <b>إحصائيات البوت:</b>
• 👥 عدد المستخدمين: {total_users:,}
• 💰 إجمالي الرصيد: {total_balance:,} دينار
• 📢 رابط القناة: {self.settings_manager.get_channel_link()}
• ❓ الأسئلة النشطة: {len(self.questions_manager.get_active_questions())}
• 📚 عدد المواد: {len(self.materials_manager.materials)}

⚙️ <b>اختر الإجراء:</b>
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("💰 شحن/خصم الرصيد", callback_data="admin_charge")],
            [InlineKeyboardButton("⚙️ إدارة الخدمات", callback_data="admin_services")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("📚 إدارة المواد", callback_data="admin_materials")],
            [InlineKeyboardButton("❓ إدارة الأسئلة", callback_data="admin_questions")],
            [InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 رجوع للبوت", callback_data="back_home")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(message, 'edit_message_text'):
            await message.edit_message_text(panel_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(panel_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    async def handle_admin_users(self, query):
        """عرض إدارة المستخدمين"""
        users_count = len(self.user_manager.users)
        
        keyboard = [
            [InlineKeyboardButton("🔍 عرض مستخدم", callback_data="admin_user_view")],
            [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="admin_user_list_1")],
            [InlineKeyboardButton("🏆 أفضل 10 مستخدمين", callback_data="admin_top_users")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            f"👥 <b>إدارة المستخدمين</b>\n\n"
            f"📊 عدد المستخدمين: {users_count:,}\n\n"
            f"اختر الإجراء:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def show_users_list(self, query, page: int = 1):
        """عرض قائمة المستخدمين"""
        users = self.user_manager.get_all_users()
        users_per_page = 10
        total_pages = max(1, (len(users) + users_per_page - 1) // users_per_page)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * users_per_page
        end_idx = min(start_idx + users_per_page, len(users))
        
        message = f"📋 <b>قائمة المستخدمين</b>\n\n"
        message += f"📄 الصفحة {page}/{total_pages}\n"
        message += f"👥 إجمالي المستخدمين: {len(users):,}\n\n"
        
        for idx, (user_id_str, user_data) in enumerate(users[start_idx:end_idx], start_idx + 1):
            user_id = int(user_id_str)
            balance = user_data.get("balance", 0)
            join_date = user_data.get("joined_date", "غير معروف").split()[0]
            first_name = user_data.get("first_name", "بدون اسم")[:15]
            
            message += f"{idx}. <code>{user_id}</code> - {first_name}\n"
            message += f"   💰 {balance:,} دينار | 📅 {join_date}\n"
            message += "   ─" * 15 + "\n"
        
        keyboard = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"admin_user_list_{page-1}"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"admin_user_list_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_users")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_charge(self, query):
        """عرض قائمة الشحن"""
        keyboard = [
            [InlineKeyboardButton("💰 شحن مستخدم", callback_data="admin_charge_user")],
            [InlineKeyboardButton("💸 خصم من مستخدم", callback_data="admin_deduct_user")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            "💰 <b>إدارة الشحن والرصيد</b>\n\n"
            "اختر نوع المعاملة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_charge_user(self, query, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية شحن مستخدم"""
        await query.edit_message_text(
            "💰 <b>شحن مستخدم</b>\n\n"
            "🔢 <b>أرسل ID المستخدم:</b>\n"
            "<code>123456789</code>\n\n"
            "💡 يمكنك الحصول على ID من قائمة المستخدمين",
            parse_mode=ParseMode.HTML
        )
        context.user_data['admin_action'] = 'charge_user'
        return CHARGE_USER
    
    async def handle_admin_deduct_user(self, query, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية خصم من مستخدم"""
        await query.edit_message_text(
            "💸 <b>خصم من مستخدم</b>\n\n"
            "🔢 <b>أرسل ID المستخدم:</b>\n"
            "<code>123456789</code>\n\n"
            "⚠️ تأكد من وجود رصيد كافي لدى المستخدم",
            parse_mode=ParseMode.HTML
        )
        context.user_data['admin_action'] = 'deduct_user'
        return CHARGE_USER
    
    async def handle_charge_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال ID المستخدم للشحن/الخصم"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        text = update.message.text.strip()
        
        if not text.isdigit():
            await update.message.reply_text(
                "❌ <b>ID غير صحيح!</b>\n\n"
                "يجب أن يكون ID مكون من أرقام فقط\n"
                "أعد إدخال ID المستخدم:",
                parse_mode=ParseMode.HTML
            )
            return CHARGE_USER
        
        target_id = int(text)
        
        # التحقق من وجود المستخدم
        target_user = self.user_manager.get_user_by_id(target_id)
        if not target_user:
            await update.message.reply_text(
                f"❌ <b>المستخدم غير موجود!</b>\n\n"
                f"ID: {target_id}\n\n"
                "تأكد من:\n"
                "• أن المستخدم استخدم البوت\n"
                "• صحة ID المستخدم\n"
                "• يمكنك التحقق من قائمة المستخدمين\n\n"
                "أعد إدخال ID المستخدم:",
                parse_mode=ParseMode.HTML
            )
            return CHARGE_USER
        
        context.user_data['charge_target'] = target_id
        context.user_data['charge_target_name'] = target_user.get('first_name', 'مستخدم')
        context.user_data['charge_target_balance'] = target_user.get('balance', 0)
        
        action = context.user_data.get('admin_action', '')
        
        if action == 'charge_user':
            await update.message.reply_text(
                f"✅ <b>تم تحديد المستخدم</b>\n\n"
                f"👤 <b>المستخدم:</b> {target_id}\n"
                f"📛 <b>الاسم:</b> {context.user_data['charge_target_name']}\n"
                f"💰 <b>الرصيد الحالي:</b> {context.user_data['charge_target_balance']:,} دينار\n\n"
                f"💵 <b>أرسل المبلغ للشحن:</b>\n"
                f"<code>5000</code>",
                parse_mode=ParseMode.HTML
            )
        elif action == 'deduct_user':
            await update.message.reply_text(
                f"✅ <b>تم تحديد المستخدم</b>\n\n"
                f"👤 <b>المستخدم:</b> {target_id}\n"
                f"📛 <b>الاسم:</b> {context.user_data['charge_target_name']}\n"
                f"💰 <b>الرصيد الحالي:</b> {context.user_data['charge_target_balance']:,} دينار\n\n"
                f"💸 <b>أرسل المبلغ للخصم:</b>\n"
                f"<code>1000</code>",
                parse_mode=ParseMode.HTML
            )
        
        return CHARGE_AMOUNT
    
    async def handle_charge_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال المبلغ للشحن/الخصم"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        text = update.message.text.strip()
        
        if not text.isdigit():
            await update.message.reply_text(
                "❌ <b>مبلغ غير صحيح!</b>\n\n"
                "يجب أن يكون المبلغ رقماً فقط\n"
                "أعد إدخال المبلغ:",
                parse_mode=ParseMode.HTML
            )
            return CHARGE_AMOUNT
        
        amount = int(text)
        target_id = context.user_data.get('charge_target')
        action = context.user_data.get('admin_action', '')
        
        if action == 'charge_user':
            if amount <= 0:
                await update.message.reply_text(
                    "❌ <b>المبلغ يجب أن يكون أكبر من صفر</b>\n\n"
                    "أعد إدخال المبلغ:",
                    parse_mode=ParseMode.HTML
                )
                return CHARGE_AMOUNT
            
            if self.user_manager.update_balance(target_id, amount, "شحن من المدير"):
                user_data = self.user_manager.get_user(target_id)
                
                await update.message.reply_text(
                    f"✅ <b>تم الشحن بنجاح!</b>\n\n"
                    f"👤 <b>المستخدم:</b> {target_id}\n"
                    f"💰 <b>المبلغ:</b> {amount:,} دينار\n"
                    f"💳 <b>الرصيد الجديد:</b> {user_data.get('balance', 0):,} دينار",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text("❌ <b>فشل في الشحن</b>", parse_mode=ParseMode.HTML)
        
        elif action == 'deduct_user':
            if amount <= 0:
                await update.message.reply_text(
                    "❌ <b>المبلغ يجب أن يكون أكبر من صفر</b>\n\n"
                    "أعد إدخال المبلغ:",
                    parse_mode=ParseMode.HTML
                )
                return CHARGE_AMOUNT
            
            current_balance = context.user_data.get('charge_target_balance', 0)
            
            if current_balance < amount:
                await update.message.reply_text(
                    f"❌ <b>رصيد المستخدم غير كافي!</b>\n\n"
                    f"💰 رصيد المستخدم: {current_balance:,} دينار\n"
                    f"💸 المبلغ المطلوب: {amount:,} دينار\n\n"
                    f"أعد إدخال مبلغ أقل:",
                    parse_mode=ParseMode.HTML
                )
                return CHARGE_AMOUNT
            
            if self.user_manager.update_balance(target_id, -amount, "خصم من المدير"):
                user_data = self.user_manager.get_user(target_id)
                
                await update.message.reply_text(
                    f"✅ <b>تم الخصم بنجاح!</b>\n\n"
                    f"👤 <b>المستخدم:</b> {target_id}\n"
                    f"💸 <b>المبلغ:</b> {amount:,} دينار\n"
                    f"💳 <b>الرصيد الجديد:</b> {user_data.get('balance', 0):,} دينار",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text("❌ <b>فشل في الخصم</b>", parse_mode=ParseMode.HTML)
        
        # تنظيف البيانات المؤقتة
        for key in ['admin_action', 'charge_target', 'charge_target_name', 'charge_target_balance']:
            if key in context.user_data:
                del context.user_data[key]
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    async def handle_admin_services(self, query):
        """عرض إدارة الخدمات"""
        all_services = self.settings_manager.get_all_services()
        
        message = "⚙️ <b>إدارة الخدمات</b>\n\n"
        message += "🔧 <b>حالة الخدمات:</b>\n\n"
        
        service_names = {
            "exemption": "🧮 حساب درجة الإعفاء",
            "summarize": "📚 تلخيص الملازم",
            "qa": "❓ سؤال وجواب بالذكاء",
            "materials": "📖 ملازمي ومرشحاتي",
            "help_student": "🤝 ساعدوني طلاب"
        }
        
        keyboard = []
        for service, active in all_services.items():
            status = "🟢 مفعل" if active else "🔴 معطل"
            price = self.settings_manager.get_price(service)
            service_name = service_names.get(service, service)
            
            message += f"{service_name}: {status} ({price:,} د)\n"
            
            btn_text = f"{'❌ تعطيل' if active else '✅ تفعيل'} {service_name.split()[-1]}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_service_{service}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_toggle_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE, service: str):
        """تفعيل/تعطيل خدمة"""
        query = update.callback_query
        await query.answer()
        
        new_status = self.settings_manager.toggle_service(service)
        status_text = "تم تفعيل" if new_status else "تم تعطيل"
        
        service_names = {
            "exemption": "حساب درجة الإعفاء",
            "summarize": "تلخيص الملازم",
            "qa": "سؤال وجواب بالذكاء",
            "materials": "ملازمي ومرشحاتي",
            "help_student": "ساعدوني طلاب"
        }
        
        service_name = service_names.get(service, service)
        
        await query.answer(f"✅ {status_text} {service_name}")
        await self.handle_admin_services(query)
    
    async def handle_admin_materials(self, query):
        """عرض إدارة المواد"""
        materials_count = len(self.materials_manager.materials)
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة مادة جديدة", callback_data="admin_material_add")],
            [InlineKeyboardButton("📋 عرض جميع المواد", callback_data="admin_material_list")],
            [InlineKeyboardButton("🗑️ حذف مادة", callback_data="admin_material_delete_menu")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            f"📚 <b>إدارة المواد التعليمية</b>\n\n"
            f"📊 عدد المواد: {materials_count}\n\n"
            f"اختر الإجراء:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_material_add(self, query, context: ContextTypes.DEFAULT_TYPE):
        """بدء إضافة مادة"""
        await query.edit_message_text(
            "➕ <b>إضافة مادة جديدة</b>\n\n"
            "📤 <b>الخطوة 1 من 3:</b> أرسل ملف PDF للمادة\n\n"
            "⚠️ يجب أن يكون الملف بصيغة PDF فقط",
            parse_mode=ParseMode.HTML
        )
        return MATERIAL_FILE
    
    async def handle_material_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال ملف المادة"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        if not update.message.document:
            await update.message.reply_text(
                "❌ <b>لم ترسل ملفاً!</b>\n\n"
                "يرجى إرسال ملف PDF للمادة:",
                parse_mode=ParseMode.HTML
            )
            return MATERIAL_FILE
        
        document = update.message.document
        
        if not document.mime_type == 'application/pdf':
            await update.message.reply_text(
                "❌ <b>الملف ليس بصيغة PDF!</b>\n\n"
                "يرجى إرسال ملف PDF فقط:",
                parse_mode=ParseMode.HTML
            )
            return MATERIAL_FILE
        
        # حفظ معلومات الملف
        file_id = document.file_id
        file_name = document.file_name or f"material_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # تحميل الملف مؤقتاً
        try:
            file = await document.get_file()
            temp_path = f"temp_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            await file.download_to_drive(temp_path)
            
            context.user_data['material_file'] = {
                'file_id': file_id,
                'file_name': file_name,
                'temp_path': temp_path
            }
            
            await update.message.reply_text(
                "✅ <b>تم حفظ الملف بنجاح</b>\n\n"
                "📝 <b>الخطوة 2 من 3:</b> أرسل وصف المادة\n\n"
                "💡 مثال: 'ملزمة رياضيات للصف السادس تحتوي على جميع الدروس والتمارين'",
                parse_mode=ParseMode.HTML
            )
            
            return MATERIAL_DESC
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل الملف: {e}")
            await update.message.reply_text(
                "❌ <b>حدث خطأ في تحميل الملف</b>\n\n"
                "أعد إرسال الملف:",
                parse_mode=ParseMode.HTML
            )
            return MATERIAL_FILE
    
    async def handle_material_desc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال وصف المادة"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        description = update.message.text.strip()
        
        if len(description) < 10:
            await update.message.reply_text(
                "❌ <b>الوصف قصير جداً!</b>\n\n"
                "يرجى كتابة وصف مفصل (10 أحرف على الأقل):",
                parse_mode=ParseMode.HTML
            )
            return MATERIAL_DESC
        
        context.user_data['material_desc'] = description
        
        await update.message.reply_text(
            "✅ <b>تم حفظ الوصف بنجاح</b>\n\n"
            "🎓 <b>الخطوة 3 من 3:</b> أرسل المرحلة الدراسية\n\n"
            "💡 مثال: 'السادس الاعدادي' أو 'الثالث متوسط'",
            parse_mode=ParseMode.HTML
        )
        
        return MATERIAL_STAGE
    
    async def handle_material_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال مرحلة المادة"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        stage = update.message.text.strip()
        
        if len(stage) < 2:
            await update.message.reply_text(
                "❌ <b>المرحلة قصيرة جداً!</b>\n\n"
                "يرجى إدخال اسم المرحلة بشكل صحيح:",
                parse_mode=ParseMode.HTML
            )
            return MATERIAL_STAGE
        
        try:
            # جمع بيانات المادة
            file_info = context.user_data.get('material_file', {})
            description = context.user_data.get('material_desc', '')
            
            if not file_info or not description:
                await update.message.reply_text(
                    "❌ <b>بيانات غير مكتملة!</b>\n\n"
                    "يرجى إعادة العملية من البداية",
                    parse_mode=ParseMode.HTML
                )
                return ConversationHandler.END
            
            # إنشاء اسم للمادة
            material_name = f"ملزمة {stage} - {datetime.now().strftime('%Y/%m/%d')}"
            
            # حفظ المادة
            material_data = {
                "name": material_name,
                "description": description,
                "stage": stage,
                "file_id": file_info.get('file_id'),
                "file_name": file_info.get('file_name'),
                "file_path": file_info.get('temp_path'),
                "added_by": user_id
            }
            
            self.materials_manager.add_material(material_data)
            
            # تنظيف الملف المؤقت
            temp_path = file_info.get('temp_path')
            if temp_path and os.path.exists(temp_path):
                # يمكنك هنا نقل الملف إلى موقع دائم إذا أردت
                pass
            
            # تنظيف بيانات السياق
            for key in ['material_file', 'material_desc']:
                if key in context.user_data:
                    del context.user_data[key]
            
            await update.message.reply_text(
                f"✅ <b>تم إضافة المادة بنجاح!</b>\n\n"
                f"📚 <b>الاسم:</b> {material_name}\n"
                f"📝 <b>الوصف:</b> {description[:100]}...\n"
                f"🎓 <b>المرحلة:</b> {stage}\n"
                f"📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode=ParseMode.HTML
            )
            
            await self.admin_panel(update, context)
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة المادة: {e}")
            await update.message.reply_text(
                f"❌ <b>حدث خطأ في إضافة المادة:</b>\n{str(e)[:100]}",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
    
    async def handle_admin_material_delete_menu(self, query):
        """عرض قائمة حذف المواد"""
        materials = self.materials_manager.materials
        
        if not materials:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_materials")]]
            await query.edit_message_text(
                "📭 <b>لا توجد مواد للحذف</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = "🗑️ <b>اختر المادة للحذف:</b>\n\n"
        
        keyboard = []
        for material in materials[:10]:  # عرض أول 10 مواد فقط
            btn_text = f"❌ {material.get('name', 'بدون اسم')} - {material.get('stage', 'غير محدد')}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"delete_material_{material['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_materials")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_delete_material(self, update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
        """حذف مادة"""
        query = update.callback_query
        await query.answer()
        
        material = self.materials_manager.get_material(material_id)
        
        if not material:
            await query.edit_message_text("❌ <b>المادة غير موجودة</b>", parse_mode=ParseMode.HTML)
            return
        
        # حذف المادة
        if self.materials_manager.delete_material(material_id):
            # حذف الملف إذا كان موجوداً
            file_path = material.get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            
            await query.edit_message_text(
                f"✅ <b>تم حذف المادة بنجاح!</b>\n\n"
                f"📚 <b>اسم المادة:</b> {material.get('name', 'بدون اسم')}\n"
                f"🎓 <b>المرحلة:</b> {material.get('stage', 'غير محدد')}",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text("❌ <b>فشل في حذف المادة</b>", parse_mode=ParseMode.HTML)
        
        # العودة لقائمة المواد
        await self.handle_admin_materials(query)
    
    async def handle_admin_questions(self, query):
        """عرض إدارة الأسئلة"""
        active_questions = self.questions_manager.get_active_questions()
        total_questions = len(self.questions_manager.questions)
        
        keyboard = [
            [InlineKeyboardButton("❓ عرض الأسئلة النشطة", callback_data="admin_active_questions")],
            [InlineKeyboardButton("🗑️ إزالة الأسئلة القديمة", callback_data="admin_remove_old_questions")],
            [InlineKeyboardButton("📊 إحصائيات الأسئلة", callback_data="admin_questions_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            f"❓ <b>إدارة الأسئلة</b>\n\n"
            f"📊 <b>الإحصائيات:</b>\n"
            f"• ❓ الأسئلة النشطة: {len(active_questions)}\n"
            f"• 📂 إجمالي الأسئلة: {total_questions}\n"
            f"• 🎯 مكافأة الإجابة: {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة\n\n"
            f"اختر الإجراء:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_settings(self, query):
        """عرض إعدادات البوت"""
        keyboard = [
            [InlineKeyboardButton("📢 تغيير رابط القناة", callback_data="admin_change_channel")],
            [InlineKeyboardButton("💰 تغيير أسعار الخدمات", callback_data="admin_change_prices")],
            [InlineKeyboardButton("🎁 تغيير الهدية الترحيبية", callback_data="admin_change_welcome_bonus")],
            [InlineKeyboardButton("👥 تغيير مكافأة الدعوة", callback_data="admin_change_referral_bonus")],
            [InlineKeyboardButton("💬 تغيير مكافأة الإجابة", callback_data="admin_change_answer_reward")],
            [InlineKeyboardButton("💾 إنشاء نسخة احتياطية", callback_data="admin_backup_data")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>إعدادات البوت</b>\n\n"
            "اختر الإجراء المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_admin_change_channel(self, query, context: ContextTypes.DEFAULT_TYPE):
        """بدء تغيير رابط القناة"""
        current_link = self.settings_manager.get_channel_link()
        
        await query.edit_message_text(
            "📢 <b>تغيير رابط قناة البوت</b>\n\n"
            f"🔗 <b>الرابط الحالي:</b> {current_link}\n\n"
            "🔗 <b>أرسل الرابط الجديد:</b>\n"
            "• يجب أن يبدأ بـ https://t.me/\n"
            "• مثال: https://t.me/FCJCV\n\n"
            "❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        return CHANGE_CHANNEL
    
    async def handle_change_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال رابط القناة الجديد"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        new_link = update.message.text.strip()
        
        # التحقق من صحة الرابط
        if not new_link.startswith("https://t.me/"):
            await update.message.reply_text(
                "❌ <b>رابط غير صحيح!</b>\n\n"
                "يجب أن يبدأ الرابط بـ: https://t.me/\n"
                "أعد إرسال الرابط الصحيح:",
                parse_mode=ParseMode.HTML
            )
            return CHANGE_CHANNEL
        
        # تحديث رابط القناة
        self.settings_manager.update_channel_link(new_link)
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير رابط القناة بنجاح!</b>\n\n"
            f"📢 <b>الرابط الجديد:</b> {new_link}\n\n"
            f"سيظهر الرابط الجديد في واجهة المستخدم مباشرة.",
            parse_mode=ParseMode.HTML
        )
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
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
        user_data = self.user_manager.get_user(user.id)
        
        welcome_message = f"""
🎓 <b>مرحباً بعودتك {user.first_name}!</b>

🆔 <b>رقم حسابك:</b> <code>{user.id}</code>
💰 <b>رصيدك الحالي:</b> {user_data['balance']:,} دينار

اختر الخدمة:
"""
        
        # إنشاء الأزرار بناءً على الخدمات النشطة
        keyboard = []
        active_services = self.settings_manager.get_active_services()
        
        service_buttons = {
            "exemption": ("🧮 حساب درجة الإعفاء", "service_exemption"),
            "summarize": ("📚 تلخيص الملازم", "service_summarize"),
            "qa": ("❓ سؤال وجواب بالذكاء", "service_qa"),
            "materials": ("📖 ملازمي ومرشحاتي", "service_materials"),
            "help_student": ("🤝 ساعدوني طلاب", "service_help_student")
        }
        
        # إضافة الخدمات النشطة
        row = []
        for service, (text, callback) in service_buttons.items():
            if service in active_services:
                price = self.settings_manager.get_price(service)
                button_text = f"{text} ({price:,} د)"
                row.append(InlineKeyboardButton(button_text, callback_data=callback))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        if row:
            keyboard.append(row)
        
        # إضافة الأزرار الأخرى
        keyboard.append([
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")
        ])
        
        keyboard.append([
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite"),
            InlineKeyboardButton("📢 قناة البوت", url=self.settings_manager.get_channel_link())
        ])
        
        keyboard.append([
            InlineKeyboardButton("🆘 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}")
        ])
        
        if user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع عمليات الرد"""
        query = update.callback_query
        
        try:
            await query.answer()
            
            # لوحة التحكم
            if query.data == "admin_panel":
                await self.admin_panel(update, context)
            
            elif query.data == "admin_users":
                await self.handle_admin_users(query)
            
            elif query.data.startswith("admin_user_list_"):
                page = int(query.data.replace("admin_user_list_", ""))
                await self.show_users_list(query, page)
            
            elif query.data == "admin_charge":
                await self.handle_admin_charge(query)
            
            elif query.data == "admin_charge_user":
                await self.handle_admin_charge_user(query, context)
                return CHARGE_USER
            
            elif query.data == "admin_deduct_user":
                await self.handle_admin_deduct_user(query, context)
                return CHARGE_USER
            
            elif query.data == "admin_services":
                await self.handle_admin_services(query)
            
            elif query.data.startswith("toggle_service_"):
                service = query.data.replace("toggle_service_", "")
                await self.handle_toggle_service(update, context, service)
            
            elif query.data == "admin_materials":
                await self.handle_admin_materials(query)
            
            elif query.data == "admin_material_add":
                await self.handle_admin_material_add(query, context)
                return MATERIAL_FILE
            
            elif query.data == "admin_material_delete_menu":
                await self.handle_admin_material_delete_menu(query)
            
            elif query.data.startswith("delete_material_"):
                material_id = int(query.data.replace("delete_material_", ""))
                await self.handle_delete_material(update, context, material_id)
            
            elif query.data == "admin_questions":
                await self.handle_admin_questions(query)
            
            elif query.data == "admin_settings":
                await self.handle_admin_settings(query)
            
            elif query.data == "admin_change_channel":
                await self.handle_admin_change_channel(query, context)
                return CHANGE_CHANNEL
            
            # الخدمات الرئيسية
            elif query.data.startswith("service_"):
                await self.handle_service_selection(update, context)
            
            elif query.data.startswith("stage_"):
                stage = query.data.replace("stage_", "")
                await self.show_stage_materials(query, stage)
            
            elif query.data.startswith("download_material_"):
                material_id = int(query.data.replace("download_material_", ""))
                await self.handle_download_material(update, context, material_id)
            
            elif query.data.startswith("view_question_"):
                question_id = query.data.replace("view_question_", "")
                await self.handle_view_question(update, context, question_id)
            
            elif query.data.startswith("answer_question_"):
                question_id = query.data.replace("answer_question_", "")
                return await self.handle_answer_question(update, context, question_id)
            
            elif query.data == "refresh_questions":
                await self.show_available_questions(update, context, query.from_user.id)
            
            elif query.data == "balance":
                await self.handle_balance_check(update, context)
            
            elif query.data == "back_home":
                await self.handle_back_home(update, context)
            
            else:
                await query.answer("⏳ جاري التحميل...")
        
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرد: {e}")
            await query.answer("❌ حدث خطأ. حاول مرة أخرى")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        user = update.effective_user
        
        # تحديث معلومات المستخدم
        self.user_manager.update_user_info(user.id, user.first_name, user.username)
        
        # معالجة الملفات
        if update.message.document and context.user_data.get('awaiting_pdf'):
            await self.handle_pdf_file(update, context)
        
        # معالجة النصوص
        elif update.message.text:
            text = update.message.text
            
            # الأسئلة بالذكاء الاصطناعي
            if context.user_data.get('awaiting_question'):
                await self.handle_question(update, context)
            
            # أسئلة ساعدوني طلاب
            elif context.user_data.get('awaiting_help_question'):
                await self.handle_help_question(update, context)
            
            # حساب الإعفاء
            elif text.replace('.', '', 1).isdigit() or (text.count(' ') >= 2 and all(part.replace('.', '', 1).isdigit() for part in text.split()[:3])):
                await self.handle_exemption_calculation(update, context)
            
            # رسائل المدير
            elif context.user_data.get('admin_action'):
                action = context.user_data.get('admin_action')
                
                if action in ['charge_user', 'deduct_user']:
                    await self.handle_charge_user_id(update, context)
                
                elif action == 'change_channel':
                    await self.handle_change_channel(update, context)
            
            # رسالة عادية
            else:
                await update.message.reply_text(
                    "🤖 <b>استخدم الأزرار للتفاعل مع البوت</b>\n\n"
                    "📝 اكتب /start لعرض القائمة الرئيسية",
                    parse_mode=ParseMode.HTML
                )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأخطاء"""
        logger.error(f"❌ تحديث {update} تسبب في خطأ {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ <b>حدث خطأ غير متوقع</b>\n\n"
                    f"🆘 تواصل مع الدعم الفني: @{SUPPORT_USERNAME}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء العملية"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return ConversationHandler.END
        
        await update.message.reply_text("❌ <b>تم إلغاء العملية</b>", parse_mode=ParseMode.HTML)
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    def run(self):
        """تشغيل البوت"""
        print("=" * 50)
        print("🤖 بوت 'يلا نتعلم' التعليمي")
        print("=" * 50)
        print(f"👑 المدير: {ADMIN_ID}")
        print(f"🆘 الدعم: @{SUPPORT_USERNAME}")
        print(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        print(f"💎 الهدية الترحيبية: {self.settings_manager.get_welcome_bonus():,} دينار")
        print(f"👥 مكافأة الدعوة: {self.settings_manager.admin_settings.get('referral_bonus', 500):,} دينار")
        print(f"🎯 مكافأة الإجابة: {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة")
        print("=" * 50)
        print("✅ البوت يعمل الآن...")
        
        app = Application.builder().token(TOKEN).build()
        
        # إنشاء ConversationHandler للوحة التحكم
        admin_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.handle_callback)],
            states={
                CHARGE_USER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_charge_user_id),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHARGE_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_charge_amount),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHANGE_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_change_channel),
                    CallbackQueryHandler(self.handle_callback)
                ],
                MATERIAL_FILE: [
                    MessageHandler(filters.Document.PDF | filters.TEXT & ~filters.COMMAND, self.handle_material_file),
                    CallbackQueryHandler(self.handle_callback)
                ],
                MATERIAL_DESC: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_material_desc),
                    CallbackQueryHandler(self.handle_callback)
                ],
                MATERIAL_STAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_material_stage),
                    CallbackQueryHandler(self.handle_callback)
                ],
                QUESTION_ANSWER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_question_answer),
                    CallbackQueryHandler(self.handle_callback)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.handle_callback, pattern="^back_home$|^admin_panel$")
            ]
        )
        
        # إضافة handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("admin", self.admin_panel))
        app.add_handler(admin_conv_handler)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.Document.PDF, self.handle_pdf_file))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        app.add_error_handler(self.error_handler)
        
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

# ============= تشغيل البوت =============
if __name__ == "__main__":
    bot = YallaNataalamBot()
    bot.run()
