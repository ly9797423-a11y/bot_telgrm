#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - البوت التعليمي للطلاب العراقيين
الإصدار المحدث مع نظام VIP
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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto
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
GEMINI_API_KEY = "AIzaSyARsl_YMXA74bPQpJduu0jJVuaku7MaHuY"

# ============= حالات المحادثة =============
(
    ADMIN_MENU, CHARGE_USER, CHARGE_AMOUNT, PRICE_CHANGE, CHANGE_PRICE_SERVICE,
    MATERIAL_FILE, MATERIAL_DESC, MATERIAL_STAGE, QUESTION_DETAILS, 
    QUESTION_ANSWER, BAN_USER, CHANGE_CHANNEL, DELETE_MATERIAL, 
    ADD_MATERIAL, VIEW_USER, TOGGLE_SERVICE, EXEMPTION_COURSE1,
    EXEMPTION_COURSE2, EXEMPTION_COURSE3, VIP_MANAGEMENT,
    VIP_ADD_LECTURE, VIP_LECTURE_TITLE, VIP_LECTURE_DESC,
    VIP_LECTURE_FILE, VIP_LECTURE_PRICE, VIP_SUBSCRIPTION_MANAGE,
    VIP_CHANGE_SUBSCRIPTION_PRICE, VIP_APPROVE_LECTURE, 
    VIP_BAN_TEACHER, VIP_VIEW_LECTURES
) = range(29)

# ============= إعداد التسعير =============
SERVICE_PRICES = {
    "exemption": 1000,
    "summarize": 1000,
    "qa": 1000,
    "materials": 1000,
    "help_student": 250,
    "vip_subscription": 5000  # سعر الاشتراك الشهري VIP
}

# ============= إعداد الخدمات النشطة =============
ACTIVE_SERVICES = {
    "exemption": True,
    "summarize": True,
    "qa": True,
    "materials": True,
    "help_student": True,
    "vip_lectures": True
}

WELCOME_BONUS = 1000
REFERRAL_BONUS = 500
ANSWER_REWARD = 100

# ============= إعداد الملفات =============
DATA_FILE = "users_data.json"
MATERIALS_FILE = "materials_data.json"
ADMIN_FILE = "admin_settings.json"
QUESTIONS_FILE = "questions_data.json"
BANNED_FILE = "banned_users.json"
CHANNEL_FILE = "channel_info.json"
SERVICES_FILE = "services_status.json"
VIP_FILE = "vip_data.json"  # ملف جديد لنظام VIP
VIP_LECTURES_FILE = "vip_lectures.json"

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
                "total_spent": 0,
                "vip_subscription": None,
                "vip_expiry": None,
                "is_teacher": False,
                "vip_lectures": [],
                "teacher_status": "pending"  # pending, approved, banned
            }
            self.save_users()
            logger.info(f"New user created: {user_id}")
        return self.users[user_id_str]
    
    def is_vip(self, user_id: int) -> bool:
        """التحقق إذا كان المستخدم مشترك في VIP"""
        user = self.get_user(user_id)
        if not user.get("vip_expiry"):
            return False
        
        try:
            expiry_date = datetime.strptime(user["vip_expiry"], "%Y-%m-%d %H:%M:%S")
            return datetime.now() < expiry_date
        except:
            return False
    
    def add_vip_subscription(self, user_id: int, months: int = 1):
        """إضافة اشتراك VIP للمستخدم"""
        user = self.get_user(user_id)
        
        now = datetime.now()
        if user.get("vip_expiry"):
            try:
                current_expiry = datetime.strptime(user["vip_expiry"], "%Y-%m-%d %H:%M:%S")
                if current_expiry > now:
                    new_expiry = current_expiry + timedelta(days=30 * months)
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
        
        # تسجيل المعاملة
        transaction = {
            "date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "vip_subscription",
            "months": months,
            "expiry_date": user["vip_expiry"]
        }
        user.setdefault("vip_transactions", []).append(transaction)
        
        self.save_users()
        logger.info(f"VIP subscription added for user {user_id} until {user['vip_expiry']}")
        return True
    
    def remove_vip_subscription(self, user_id: int):
        """إزالة اشتراك VIP من المستخدم"""
        user = self.get_user(user_id)
        user["vip_subscription"] = False
        user["vip_expiry"] = None
        user["teacher_status"] = "pending"
        self.save_users()
        logger.info(f"VIP subscription removed for user {user_id}")
        return True
    
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
            
            if time_diff.total_seconds() < 86400:
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
    
    def update_balance(self, user_id: int, amount: int, description: str = "") -> Tuple[int, bool]:
        """تحديد رصيد المستخدم مع إرسال إشعار"""
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
        
        if amount > 0:
            user["total_earned"] = user.get("total_earned", 0) + amount
        else:
            user["total_spent"] = user.get("total_spent", 0) + abs(amount)
        
        self.save_users()
        logger.info(f"Updated balance for user {user_id}: {old_balance} -> {user['balance']} ({amount})")
        
        # إرسال إشعار للمستخدم
        notify_user = amount > 0  # إرسال إشعار فقط للشحنات الإيجابية
        return user["balance"], notify_user
    
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
        
        for question in active_questions[:10]:
            question["views"] = question.get("views", 0) + 1
        
        return active_questions[:10]
    
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

# ============= إدارة نظام VIP =============
class VIPManager:
    def __init__(self):
        self.vip_data = DataManager.load_data(VIP_FILE, {
            "subscription_price": 5000,
            "teachers": [],
            "pending_lectures": [],
            "approved_lectures": [],
            "banned_teachers": []
        })
        
        self.lectures = DataManager.load_data(VIP_LECTURES_FILE, [])
    
    def add_lecture(self, teacher_id: int, title: str, description: str, file_info: Dict, price: int = 0) -> str:
        """إضافة محاضرة جديدة (في انتظار الموافقة)"""
        lecture_id = str(uuid.uuid4())[:8].upper()
        lecture_data = {
            "id": lecture_id,
            "teacher_id": teacher_id,
            "title": title,
            "description": description,
            "file_info": file_info,
            "price": price,
            "status": "pending",  # pending, approved, rejected
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "approved_date": None,
            "views": 0,
            "downloads": 0
        }
        
        self.lectures.append(lecture_data)
        self.vip_data["pending_lectures"].append(lecture_id)
        self.save_all_data()
        
        logger.info(f"Added lecture {lecture_id} by teacher {teacher_id}")
        return lecture_id
    
    def approve_lecture(self, lecture_id: str) -> bool:
        """الموافقة على محاضرة"""
        for lecture in self.lectures:
            if lecture["id"] == lecture_id and lecture["status"] == "pending":
                lecture["status"] = "approved"
                lecture["approved_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # نقل من قائمة الانتظار إلى القائمة المعتمدة
                if lecture_id in self.vip_data["pending_lectures"]:
                    self.vip_data["pending_lectures"].remove(lecture_id)
                self.vip_data["approved_lectures"].append(lecture_id)
                
                self.save_all_data()
                logger.info(f"Approved lecture {lecture_id}")
                return True
        return False
    
    def reject_lecture(self, lecture_id: str) -> bool:
        """رفض محاضرة"""
        for lecture in self.lectures:
            if lecture["id"] == lecture_id and lecture["status"] == "pending":
                lecture["status"] = "rejected"
                
                if lecture_id in self.vip_data["pending_lectures"]:
                    self.vip_data["pending_lectures"].remove(lecture_id)
                
                self.save_all_data()
                logger.info(f"Rejected lecture {lecture_id}")
                return True
        return False
    
    def get_pending_lectures(self) -> List[Dict]:
        """الحصول على المحاضرات في انتظار الموافقة"""
        return [lecture for lecture in self.lectures if lecture["status"] == "pending"]
    
    def get_approved_lectures(self) -> List[Dict]:
        """الحصول على المحاضرات المعتمدة"""
        return [lecture for lecture in self.lectures if lecture["status"] == "approved"]
    
    def get_teacher_lectures(self, teacher_id: int) -> List[Dict]:
        """الحصول على محاضرات معلم معين"""
        return [lecture for lecture in self.lectures 
                if lecture["teacher_id"] == teacher_id and lecture["status"] == "approved"]
    
    def delete_lecture(self, lecture_id: str) -> bool:
        """حذف محاضرة"""
        original_count = len(self.lectures)
        self.lectures = [lecture for lecture in self.lectures if lecture["id"] != lecture_id]
        
        # إزالة من القوائم الأخرى
        for key in ["pending_lectures", "approved_lectures"]:
            if lecture_id in self.vip_data[key]:
                self.vip_data[key].remove(lecture_id)
        
        if len(self.lectures) < original_count:
            self.save_all_data()
            logger.info(f"Deleted lecture {lecture_id}")
            return True
        return False
    
    def ban_teacher(self, teacher_id: int) -> bool:
        """حظر معلم"""
        if teacher_id not in self.vip_data["banned_teachers"]:
            self.vip_data["banned_teachers"].append(teacher_id)
            self.save_all_data()
            logger.info(f"Banned teacher {teacher_id}")
            return True
        return False
    
    def unban_teacher(self, teacher_id: int) -> bool:
        """إلغاء حظر معلم"""
        if teacher_id in self.vip_data["banned_teachers"]:
            self.vip_data["banned_teachers"].remove(teacher_id)
            self.save_all_data()
            logger.info(f"Unbanned teacher {teacher_id}")
            return True
        return False
    
    def update_subscription_price(self, price: int):
        """تحديث سعر الاشتراك الشهري"""
        self.vip_data["subscription_price"] = price
        self.save_all_data()
    
    def get_subscription_price(self) -> int:
        """الحصول على سعر الاشتراك"""
        return self.vip_data.get("subscription_price", 5000)
    
    def save_all_data(self):
        """حفظ جميع بيانات VIP"""
        DataManager.save_data(VIP_FILE, self.vip_data)
        DataManager.save_data(VIP_LECTURES_FILE, self.lectures)

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
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': api_key
        }
        
    def call_gemini_api(self, prompt: str) -> str:
        """استدعاء API Gemini 2.0 Flash"""
        try:
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '❌ لم أتمكن من إجابة على سؤالك')
            else:
                logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
                return f"❌ خطأ في خدمة الذكاء الاصطناعي (رمز الخطأ: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return "❌ تجاوز المهلة، يرجى المحاولة مرة أخرى"
        except Exception as e:
            logger.error(f"Gemini API Exception: {e}")
            return f"❌ حدث خطأ في الخدمة: {str(e)[:100]}"
    
    def summarize_pdf(self, pdf_path: str) -> str:
        """تلخيص ملف PDF"""
        try:
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
            
            return self.call_gemini_api(prompt)
            
        except Exception as e:
            logger.error(f"❌ خطأ في تلخيص PDF: {e}")
            return f"❌ حدث خطأ في التلخيص: {str(e)[:100]}"
    
    def answer_question(self, question: str) -> str:
        """الإجابة على الأسئلة التعليمية"""
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
            
            return self.call_gemini_api(prompt)
            
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
        self.vip_manager = VIPManager()
        self.ai_service = AIService(GEMINI_API_KEY)
        
        logger.info("✅ تم تهيئة البوت بنجاح")
        logger.info(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        logger.info(f"💎 الهدية: {self.settings_manager.get_welcome_bonus()} دينار")
        logger.info(f"👑 VIP الاشتراك: {self.vip_manager.get_subscription_price()} دينار شهرياً")
    
    async def send_notification(self, user_id: int, message: str, context: ContextTypes.DEFAULT_TYPE):
        """إرسال إشعار للمستخدم"""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الإشعار لـ {user_id}: {e}")
            return False
    
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
        
        # زر VIP إذا كان المستخدم معلم
        if self.user_manager.is_vip(user.id):
            keyboard.append([InlineKeyboardButton("👑 محاضراتي VIP", callback_data="vip_my_lectures")])
        
        # إضافة الأزرار الأخرى
        keyboard.append([
            InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
            InlineKeyboardButton("❓ أسئلة الطلاب", callback_data="student_questions")
        ])
        
        keyboard.append([
            InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite"),
            InlineKeyboardButton("📢 قناة البوت", url=self.settings_manager.get_channel_link())
        ])
        
        keyboard.append([
            InlineKeyboardButton("👑 اشتراك VIP", callback_data="vip_subscription_info"),
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
    
    # ============= نظام الإعفاء المعدل =============
    async def show_exemption_calculator(self, query):
        """عرض آلة حساب الإعفاء"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        price = self.settings_manager.get_price("exemption")
        
        context = query.data.split('_') if '_' in query.data else []
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرجوع للرئيسية", callback_data="back_home")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧮 <b>حاسبة درجة الإعفاء</b>\n\n"
            f"💰 سعر الخدمة: {price:,} دينار\n"
            f"💳 رصيدك الحالي: {user_data['balance']:,} دينار\n\n"
            "📝 <b>الخطوة 1 من 3:</b>\n"
            "أدخل درجة الكورس الأول:\n\n"
            "🎯 <b>المعدل المطلوب للإعفاء:</b> 90 فما فوق\n"
            "⚠️ <b>سيتم خصم المبلغ بعد الحساب</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        return EXEMPTION_COURSE1
    
    async def handle_exemption_course1(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال درجة الكورس الأول"""
        user_id = update.effective_user.id
        
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
        """استقبال درجة الكورس الثاني"""
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
        """استقبال درجة الكورس الثالث وحساب المعدل"""
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
            
            # إكمال عملية الشراء
            if self.user_manager.complete_purchase(user_id):
                price = self.settings_manager.get_price("exemption")
                new_balance, should_notify = self.user_manager.update_balance(user_id, -price, f"حساب درجة الإعفاء")
                
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
                
                # تنظيف البيانات المؤقتة
                if 'exemption_scores' in context.user_data:
                    del context.user_data['exemption_scores']
                
                # زر العودة
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
    
    # ============= نظام VIP =============
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
        
        if query.from_user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 إدارة VIP", callback_data="admin_vip_management")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def handle_vip_subscribe(self, query, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اشتراك VIP"""
        user_id = query.from_user.id
        user_data = self.user_manager.get_user(user_id)
        vip_price = self.vip_manager.get_subscription_price()
        
        if user_data['balance'] < vip_price:
            await query.answer(f"❌ رصيدك غير كافي! تحتاج {vip_price:,} دينار", show_alert=True)
            return
        
        # خصم المبلغ
        new_balance, should_notify = self.user_manager.update_balance(user_id, -vip_price, "اشتراك VIP شهري")
        
        # تفعيل الاشتراك
        self.user_manager.add_vip_subscription(user_id, 1)
        
        # إرسال إشعار
        notify_message = f"""
✅ <b>تم تفعيل اشتراك VIP بنجاح!</b>

💰 <b>المبلغ:</b> {vip_price:,} دينار
💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار
📅 <b>تاريخ الانتهاء:</b> {self.user_manager.get_user(user_id)['vip_expiry']}

🎉 <b>مبروك! يمكنك الآن رفع محاضراتك.</b>
"""
        await self.send_notification(user_id, notify_message, context)
        
        # إشعار للمدير
        admin_message = f"""
👑 <b>اشتراك VIP جديد</b>

👤 <b>المستخدم:</b> {user_id}
📛 <b>الاسم:</b> {user_data['first_name']}
📅 <b>تاريخ الانتهاء:</b> {self.user_manager.get_user(user_id)['vip_expiry']}
"""
        await self.send_notification(ADMIN_ID, admin_message, context)
        
        await query.answer("✅ تم تفعيل اشتراك VIP بنجاح!", show_alert=True)
        await self.show_vip_subscription_info(query)
    
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
        """استقبال عنوان المحاضرة"""
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
        """استقبال وصف المحاضرة"""
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
        """استقبال سعر المحاضرة"""
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
        """استقبال ملف المحاضرة"""
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
        
        # تنظيف البيانات المؤقتة
        for key in ['vip_lecture_title', 'vip_lecture_desc', 'vip_lecture_price']:
            if key in context.user_data:
                del context.user_data[key]
        
        # إشعار للمدير
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
        
        # زر العودة
        keyboard = [[InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔙", reply_markup=reply_markup)
        
        return ConversationHandler.END
    
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
        for lecture in lectures[:10]:  # عرض أول 10 محاضرات
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
    
    # ============= لوحة التحكم المعدلة =============
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
        
        # إحصائيات VIP
        vip_users = sum(1 for user in self.user_manager.users.values() 
                       if user.get("vip_subscription") and self.user_manager.is_vip(int(list(self.user_manager.users.keys())[0])))
        
        panel_text = f"""
👑 <b>لوحة التحكم الإدارية</b>

📊 <b>إحصائيات البوت:</b>
• 👥 عدد المستخدمين: {total_users:,}
• 💰 إجمالي الرصيد: {total_balance:,} دينار
• 👑 مشتركين VIP: {vip_users}
• 📢 رابط القناة: {self.settings_manager.get_channel_link()}
• ❓ الأسئلة النشطة: {len(self.questions_manager.get_active_questions())}
• 📚 عدد المواد: {len(self.materials_manager.materials)}
• 📤 محاضرات VIP: {len(self.vip_manager.get_approved_lectures())}

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
        """عرض قائمة تغيير الأسعار"""
        services = {
            "exemption": "🧮 حساب درجة الإعفاء",
            "summarize": "📚 تلخيص الملازم", 
            "qa": "❓ سؤال وجواب بالذكاء",
            "materials": "📖 ملازمي ومرشحاتي",
            "help_student": "🤝 ساعدوني طلاب",
            "vip_subscription": "👑 اشتراك VIP شهري"
        }
        
        message = "💰 <b>تغيير أسعار الخدمات</b>\n\n"
        message += "📊 <b>الأسعار الحالية:</b>\n\n"
        
        keyboard = []
        for service_key, service_name in services.items():
            current_price = self.settings_manager.get_price(service_key)
            message += f"{service_name}: {current_price:,} دينار\n"
            keyboard.append([InlineKeyboardButton(f"تغيير {service_name}", callback_data=f"change_price_{service_key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_change_price_service(self, query, context: ContextTypes.DEFAULT_TYPE, service: str):
        """بدء تغيير سعر خدمة"""
        service_names = {
            "exemption": "حساب درجة الإعفاء",
            "summarize": "تلخيص الملازم",
            "qa": "سؤال وجواب بالذكاء",
            "materials": "ملازمي ومرشحاتي",
            "help_student": "ساعدوني طلاب",
            "vip_subscription": "اشتراك VIP شهري"
        }
        
        current_price = self.settings_manager.get_price(service)
        
        await query.edit_message_text(
            f"💰 <b>تغيير سعر الخدمة</b>\n\n"
            f"📝 <b>الخدمة:</b> {service_names.get(service, service)}\n"
            f"💵 <b>السعر الحالي:</b> {current_price:,} دينار\n\n"
            f"🔢 <b>أدخل السعر الجديد:</b>\n"
            f"<code>1000</code>\n\n"
            f"❌ للإلغاء: /cancel",
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['changing_price_service'] = service
        return CHANGE_PRICE_SERVICE
    
    async def handle_change_price_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال السعر الجديد"""
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
        
        # تحديث السعر
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
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير السعر بنجاح!</b>\n\n"
            f"📝 <b>الخدمة:</b> {service_names.get(service, service)}\n"
            f"💰 <b>السعر الجديد:</b> {new_price:,} دينار",
            parse_mode=ParseMode.HTML
        )
        
        # تنظيف البيانات المؤقتة
        if 'changing_price_service' in context.user_data:
            del context.user_data['changing_price_service']
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    async def handle_admin_vip_management(self, query):
        """عرض إدارة VIP"""
        pending_lectures = len(self.vip_manager.get_pending_lectures())
        approved_lectures = len(self.vip_manager.get_approved_lectures())
        subscription_price = self.vip_manager.get_subscription_price()
        
        vip_users = 0
        for user_id_str, user_data in self.user_manager.users.items():
            if user_data.get("vip_subscription") and self.user_manager.is_vip(int(user_id_str)):
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
        """عرض المحاضرات قيد المراجعة"""
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
        for lecture in pending_lectures[:10]:  # عرض أول 10 محاضرات
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
        """عرض تفاصيل محاضرة للمراجعة"""
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
    
    async def handle_vip_approve_lecture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, lecture_id: str):
        """الموافقة على محاضرة"""
        query = update.callback_query
        await query.answer()
        
        if self.vip_manager.approve_lecture(lecture_id):
            # إشعار للمعلم
            lecture = None
            for l in self.vip_manager.lectures:
                if l["id"] == lecture_id:
                    lecture = l
                    break
            
            if lecture:
                teacher_id = lecture["teacher_id"]
                notify_message = f"""
✅ <b>تمت الموافقة على محاضراتك!</b>

🆔 <b>رقم المحاضرة:</b> {lecture_id}
📝 <b>العنوان:</b> {lecture.get('title', 'بدون عنوان')}

🎉 <b>مبروك! المحاضرة متاحة الآن للطلاب.</b>
"""
                await self.send_notification(teacher_id, notify_message, context)
            
            await query.answer("✅ تمت الموافقة على المحاضرة", show_alert=True)
            await self.handle_vip_review_lectures(query)
        else:
            await query.answer("❌ فشل في الموافقة على المحاضرة", show_alert=True)
    
    async def handle_vip_ban_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: int):
        """حظر معلم"""
        query = update.callback_query
        await query.answer()
        
        if self.vip_manager.ban_teacher(teacher_id):
            # إزالة الاشتراك VIP
            self.user_manager.remove_vip_subscription(teacher_id)
            
            # إشعار للمعلم
            notify_message = """
🚫 <b>تم حظر حسابك من نظام VIP!</b>

❌ <b>تم إلغاء اشتراكك وحظر حسابك للأسباب التالية:</b>
1. مخالفة شروط استخدام النظام
2. محتوى غير مناسب
3. شكاوى متكررة

📞 <b>للاستفسار:</b> @{SUPPORT_USERNAME}
"""
            await self.send_notification(teacher_id, notify_message, context)
            
            await query.answer("✅ تم حظر المعلم وإلغاء اشتراكه", show_alert=True)
        else:
            await query.answer("❌ فشل في حظر المعلم", show_alert=True)
        
        await self.handle_vip_review_lectures(query)
    
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
        """استقبال سعر اشتراك VIP الجديد"""
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
        
        # تحديث السعر
        self.vip_manager.update_subscription_price(new_price)
        
        await update.message.reply_text(
            f"✅ <b>تم تغيير سعر الاشتراك بنجاح!</b>\n\n"
            f"💰 <b>السعر الجديد:</b> {new_price:,} دينار شهرياً",
            parse_mode=ParseMode.HTML
        )
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    # ============= إدارة الشحن مع الإشعارات =============
    async def handle_charge_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال المبلغ للشحن/الخصم مع إرسال إشعار"""
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
            
            # شحن المستخدم
            new_balance, should_notify = self.user_manager.update_balance(target_id, amount, "شحن من المدير")
            user_data = self.user_manager.get_user(target_id)
            
            # إرسال إشعار للمستخدم
            if should_notify:
                notify_message = f"""
💰 <b>تم شحن رصيدك!</b>

💵 <b>المبلغ:</b> {amount:,} دينار
💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار
📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}

🎉 <b>تمت العملية بنجاح!</b>
"""
                await self.send_notification(target_id, notify_message, context)
            
            await update.message.reply_text(
                f"✅ <b>تم الشحن بنجاح!</b>\n\n"
                f"👤 <b>المستخدم:</b> {target_id}\n"
                f"💰 <b>المبلغ:</b> {amount:,} دينار\n"
                f"💳 <b>الرصيد الجديد:</b> {user_data.get('balance', 0):,} دينار",
                parse_mode=ParseMode.HTML
            )
        
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
            
            # خصم من المستخدم
            new_balance, should_notify = self.user_manager.update_balance(target_id, -amount, "خصم من المدير")
            user_data = self.user_manager.get_user(target_id)
            
            # إرسال إشعار للمستخدم
            if should_notify:
                notify_message = f"""
💸 <b>تم خصم من رصيدك!</b>

💵 <b>المبلغ:</b> {amount:,} دينار
💳 <b>رصيدك الجديد:</b> {new_balance:,} دينار
📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}
📝 <b>السبب:</b> خصم من المدير

📞 <b>للاستفسار:</b> @{SUPPORT_USERNAME}
"""
                await self.send_notification(target_id, notify_message, context)
            
            await update.message.reply_text(
                f"✅ <b>تم الخصم بنجاح!</b>\n\n"
                f"👤 <b>المستخدم:</b> {target_id}\n"
                f"💸 <b>المبلغ:</b> {amount:,} دينار\n"
                f"💳 <b>الرصيد الجديد:</b> {user_data.get('balance', 0):,} دينار",
                parse_mode=ParseMode.HTML
            )
        
        # تنظيف البيانات المؤقتة
        for key in ['admin_action', 'charge_target', 'charge_target_name', 'charge_target_balance']:
            if key in context.user_data:
                del context.user_data[key]
        
        await self.admin_panel(update, context)
        return ConversationHandler.END
    
    # ============= زر أسئلة الطلاب =============
    async def show_student_questions(self, query):
        """عرض أسئلة الطلاب للإجابة"""
        user_id = query.from_user.id
        active_questions = self.questions_manager.get_active_questions(user_id)
        
        if not active_questions:
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="student_questions")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
            ]
            
            await query.edit_message_text(
                "📭 <b>لا توجد أسئلة متاحة للإجابة حالياً</b>\n\n"
                "يمكنك العودة لاحقاً للبحث عن أسئلة للإجابة عليها",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        message = f"🤝 <b>أسئلة الطلاب المتاحة للإجابة ({len(active_questions)})</b>\n\n"
        message += f"🎯 <b>مكافأة الإجابة:</b> {self.settings_manager.admin_settings.get('answer_reward', 100)} نقطة\n\n"
        
        keyboard = []
        for question in active_questions:
            question_text = question['question'][:50] + "..." if len(question['question']) > 50 else question['question']
            date = question['date'].split()[0]
            views = question.get('views', 0)
            
            btn_text = f"❓ {question_text[:30]} ({views} 👁️)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_question_{question['id']}")])
        
        keyboard.append([InlineKeyboardButton("🔄 تحديث القائمة", callback_data="student_questions")])
        keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    # ============= معالجة الردود =============
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع عمليات الرد"""
        query = update.callback_query
        
        try:
            await query.answer()
            
            # ============= لوحة التحكم =============
            if query.data == "admin_panel":
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
            
            elif query.data.startswith("vip_approve_lecture_"):
                lecture_id = query.data.replace("vip_approve_lecture_", "")
                await self.handle_vip_approve_lecture(update, context, lecture_id)
            
            elif query.data.startswith("vip_ban_teacher_"):
                teacher_id = int(query.data.replace("vip_ban_teacher_", ""))
                await self.handle_vip_ban_teacher(update, context, teacher_id)
            
            elif query.data == "vip_change_subscription_price":
                await self.handle_vip_change_subscription_price(query, context)
                return VIP_CHANGE_SUBSCRIPTION_PRICE
            
            # ============= نظام الإعفاء المعدل =============
            elif query.data == "service_exemption":
                await self.show_exemption_calculator(query)
                return EXEMPTION_COURSE1
            
            # ============= نظام VIP =============
            elif query.data == "vip_subscription_info":
                await self.show_vip_subscription_info(query)
            
            elif query.data == "vip_subscribe":
                await self.handle_vip_subscribe(query, context)
            
            elif query.data == "vip_add_lecture":
                await self.handle_vip_add_lecture(query, context)
                return VIP_LECTURE_TITLE
            
            elif query.data == "vip_my_lectures":
                await self.show_vip_my_lectures(query)
            
            # ============= أسئلة الطلاب =============
            elif query.data == "student_questions":
                await self.show_student_questions(query)
            
            # ============= باقي الأوامر (من الكود الأصلي) =============
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
    
    # ============= الدوال المساعدة من الكود الأصلي =============
    # (يجب نسخ باقي الدوال كما هي من الكود الأصلي مع تعديلات بسيطة)
    # بما في ذلك:
    # - handle_service_selection
    # - handle_pdf_file
    # - handle_question
    # - handle_help_student
    # - handle_help_question
    # - handle_view_question
    # - handle_answer_question
    # - handle_question_answer
    # - show_materials_menu
    # - show_stage_materials
    # - handle_download_material
    # - handle_admin_users
    # - show_users_list
    # - handle_admin_charge_user
    # - handle_admin_deduct_user
    # - handle_charge_user_id
    # - handle_admin_services
    # - handle_toggle_service
    # - handle_admin_materials
    # - handle_admin_material_add
    # - handle_material_file
    # - handle_material_desc
    # - handle_material_stage
    # - handle_admin_material_delete_menu
    # - handle_delete_material
    # - handle_admin_questions
    # - handle_admin_settings
    # - handle_admin_change_channel
    # - handle_change_channel
    # - handle_balance_check
    # - handle_back_home
    # - handle_message
    # - error_handler
    # - cancel
    # - run
    
    def run(self):
        """تشغيل البوت"""
        print("=" * 60)
        print("🤖 بوت 'يلا نتعلم' التعليمي - الإصدار المحدث")
        print("=" * 60)
        print(f"👑 المدير: {ADMIN_ID}")
        print(f"🆘 الدعم: @{SUPPORT_USERNAME}")
        print(f"📢 القناة: {self.settings_manager.get_channel_link()}")
        print(f"💎 الهدية الترحيبية: {self.settings_manager.get_welcome_bonus():,} دينار")
        print(f"👑 سعر VIP: {self.vip_manager.get_subscription_price():,} دينار شهرياً")
        print(f"🤖 الذكاء الاصطناعي: Gemini 2.0 Flash")
        print("=" * 60)
        print("✅ البوت يعمل الآن...")
        
        app = Application.builder().token(TOKEN).build()
        
        # إنشاء ConversationHandler متكامل
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
                
                # لوحة التحكم
                CHARGE_USER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_charge_user_id),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHARGE_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_charge_amount),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHANGE_PRICE_SERVICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_change_price_amount),
                    CallbackQueryHandler(self.handle_callback)
                ],
                CHANGE_CHANNEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_change_channel),
                    CallbackQueryHandler(self.handle_callback)
                ],
                
                # المواد التعليمية
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
                
                # الأسئلة والإجابات
                QUESTION_ANSWER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_question_answer),
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
                ],
                VIP_CHANGE_SUBSCRIPTION_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vip_subscription_price_change),
                    CallbackQueryHandler(self.handle_callback)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("start", self.start),
                CallbackQueryHandler(self.handle_callback, pattern="^back_home$|^admin_panel$")
            ]
        )
        
        # إضافة handlers
        app.add_handler(conv_handler)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.Document.PDF, self.handle_pdf_file))
        app.add_error_handler(self.error_handler)
        
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

# ============= تشغيل البوت =============
if __name__ == "__main__":
    bot = YallaNataalamBot()
    bot.run()
