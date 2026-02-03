#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت "يلا نتعلم" - بوت تعليمي للطلاب العراقيين
مطور بواسطة: Allawi04@
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import re
import io
import hashlib
from pathlib import Path

# المكتبات الأساسية
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.types import InputFile, InputMediaDocument
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import BotBlocked, ChatNotFound

# مكتبات PDF والمعالجة
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import PyPDF2
from PIL import Image

# مكتبة الذكاء الاصطناعي Gemini
import google.generativeai as genai

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# بيانات الإعداد
BOT_TOKEN = "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI"
GEMINI_API_KEY = "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY"
ADMIN_ID = 6130994941  # ايدي المدير
BOT_USERNAME = "@FC4Xbot"  # يوزر البوت
SUPPORT_USERNAME = "Allawi04@"  # يوزر الدعم

# تهيئة الذكاء الاصطناعي Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    gemini_vision_model = genai.GenerativeModel('gemini-pro-vision')
except Exception as e:
    logger.error(f"فشل تهيئة Gemini API: {e}")
    gemini_model = None
    gemini_vision_model = None

# تهيئة البوت
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# تسجيل الخطوط العربية
try:
    pdfmetrics.registerFont(TTFont('Arabic', 'fonts/NotoSansArabic-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('English', 'fonts/DejaVuSans.ttf'))
except:
    # استخدام خطوط افتراضية إذا لم تكن موجودة
    pass

# حالات FSM
class UserStates(StatesGroup):
    waiting_for_course1 = State()
    waiting_for_course2 = State()
    waiting_for_course3 = State()
    waiting_for_pdf = State()
    waiting_for_question = State()
    waiting_for_image = State()
    admin_waiting_user_id = State()
    admin_waiting_amount = State()
    admin_waiting_price = State()
    admin_waiting_price_service = State()
    admin_waiting_material_name = State()
    admin_waiting_material_desc = State()
    admin_waiting_material_stage = State()
    admin_waiting_material_file = State()
    admin_waiting_invite_reward = State()

# فئات البيانات
class User:
    def __init__(self, user_id: int, username: str = "", first_name: str = ""):
        self.user_id = user_id
        self.username = username or f"user_{user_id}"
        self.first_name = first_name or "مستخدم"
        self.balance = 1000  # هدية ترحيبية 1000 دينار
        self.is_admin = False
        self.is_blocked = False
        self.join_date = datetime.now()
        self.last_active = datetime.now()
        self.invite_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
        self.invited_by = None
        self.invited_count = 0
        self.total_spent = 0
        
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'balance': self.balance,
            'is_admin': self.is_admin,
            'is_blocked': self.is_blocked,
            'join_date': self.join_date.isoformat(),
            'last_active': self.last_active.isoformat(),
            'invite_code': self.invite_code,
            'invited_by': self.invited_by,
            'invited_count': self.invited_count,
            'total_spent': self.total_spent
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        user = cls(data['user_id'], data['username'], data['first_name'])
        user.balance = data['balance']
        user.is_admin = data.get('is_admin', False)
        user.is_blocked = data.get('is_blocked', False)
        user.join_date = datetime.fromisoformat(data['join_date'])
        user.last_active = datetime.fromisoformat(data['last_active'])
        user.invite_code = data.get('invite_code', '')
        user.invited_by = data.get('invited_by')
        user.invited_count = data.get('invited_count', 0)
        user.total_spent = data.get('total_spent', 0)
        return user

class Material:
    def __init__(self, material_id: int, name: str, description: str, stage: str, file_id: str):
        self.material_id = material_id
        self.name = name
        self.description = description
        self.stage = stage
        self.file_id = file_id
        self.add_date = datetime.now()
        
    def to_dict(self):
        return {
            'material_id': self.material_id,
            'name': self.name,
            'description': self.description,
            'stage': self.stage,
            'file_id': self.file_id,
            'add_date': self.add_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        material = cls(
            data['material_id'],
            data['name'],
            data['description'],
            data['stage'],
            data['file_id']
        )
        material.add_date = datetime.fromisoformat(data['add_date'])
        return material

class BotDatabase:
    def __init__(self):
        self.users_file = "data/users.json"
        self.materials_file = "data/materials.json"
        self.settings_file = "data/settings.json"
        self.stats_file = "data/stats.json"
        
        # إنشاء المجلدات إذا لم تكن موجودة
        os.makedirs("data", exist_ok=True)
        
        # تحميل البيانات
        self.users = self._load_users()
        self.materials = self._load_materials()
        self.settings = self._load_settings()
        self.stats = self._load_stats()
        
        # إعدادات افتراضية
        if 'service_prices' not in self.settings:
            self.settings['service_prices'] = {
                'exemption': 1000,
                'summarize': 1000,
                'qa': 1000,
                'materials': 1000
            }
        
        if 'invite_reward' not in self.settings:
            self.settings['invite_reward'] = 500
        
        if 'maintenance' not in self.settings:
            self.settings['maintenance'] = False
        
        if 'channel_link' not in self.settings:
            self.settings['channel_link'] = "https://t.me/+"
        
        self.save_settings()
        
    def _load_users(self) -> Dict[int, User]:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {int(k): User.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"خطأ في تحميل المستخدمين: {e}")
        return {}
    
    def _load_materials(self):
        try:
            if os.path.exists(self.materials_file):
                with open(self.materials_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {int(k): Material.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"خطأ في تحميل المواد: {e}")
        return {}
    
    def _load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل الإعدادات: {e}")
        return {}
    
    def _load_stats(self):
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل الإحصائيات: {e}")
        return {
            'total_users': 0,
            'active_today': 0,
            'total_services': 0,
            'total_revenue': 0,
            'today_date': datetime.now().date().isoformat()
        }
    
    def save_users(self):
        try:
            data = {str(k): v.to_dict() for k, v in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ المستخدمين: {e}")
    
    def save_materials(self):
        try:
            data = {str(k): v.to_dict() for k, v in self.materials.items()}
            with open(self.materials_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ المواد: {e}")
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")
    
    def save_stats(self):
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الإحصائيات: {e}")
    
    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)
    
    def add_user(self, user: User):
        self.users[user.user_id] = user
        self.save_users()
        
        # تحديث الإحصائيات
        today = datetime.now().date().isoformat()
        if self.stats['today_date'] != today:
            self.stats['today_date'] = today
            self.stats['active_today'] = 0
        
        self.stats['total_users'] = len(self.users)
        self.stats['active_today'] += 1
        self.save_stats()
    
    def update_user(self, user: User):
        self.users[user.user_id] = user
        self.save_users()
    
    def get_material(self, material_id: int) -> Optional[Material]:
        return self.materials.get(material_id)
    
    def add_material(self, material: Material):
        self.materials[material.material_id] = material
        self.save_materials()
    
    def delete_material(self, material_id: int):
        if material_id in self.materials:
            del self.materials[material_id]
            self.save_materials()
            return True
        return False
    
    def get_all_materials(self) -> List[Material]:
        return list(self.materials.values())
    
    def get_materials_by_stage(self, stage: str) -> List[Material]:
        return [m for m in self.materials.values() if m.stage == stage]

# إنشاء قاعدة البيانات
db = BotDatabase()

# إعداد المدير الأساسي
if ADMIN_ID not in db.users:
    admin_user = User(ADMIN_ID, "Allawi04", "مدير النظام")
    admin_user.is_admin = True
    admin_user.balance = 1000000  # رصيد كبير للمدير
    db.add_user(admin_user)

# ========== دوال مساعدة ==========

def format_arabic(text: str) -> str:
    """تنسيق النص العربي للعرض الصحيح"""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except:
        return text

def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}".replace(",", "،")

def create_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """إنشاء قائمة رئيسية مع InlineKeyboardButtons"""
    user = db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # الأزرار الرئيسية
    buttons = [
        InlineKeyboardButton("📊 حساب درجة الإعفاء الفردي", callback_data="service_exemption"),
        InlineKeyboardButton("📄 تلخيص الملازم", callback_data="service_summarize"),
        InlineKeyboardButton("❓ سؤال وجواب", callback_data="service_qa"),
        InlineKeyboardButton("📚 ملازمي ومرشحاتي", callback_data="service_materials"),
        InlineKeyboardButton("💰 رصيدي: " + format_number(user.balance) + " دينار", callback_data="show_balance"),
        InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="invite_friends"),
        InlineKeyboardButton("📞 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}"),
        InlineKeyboardButton("📢 قناة البوت", url=db.settings['channel_link'])
    ]
    
    # إضافة زر لوحة التحكم للمديرين فقط
    if user and user.is_admin:
        buttons.append(InlineKeyboardButton("👑 لوحة التحكم", callback_data="admin_panel"))
    
    # إضافة الأزرار إلى الكيبورد
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.row(buttons[i], buttons[i + 1])
        else:
            keyboard.add(buttons[i])
    
    return keyboard

def create_admin_panel() -> InlineKeyboardMarkup:
    """لوحة تحكم المدير"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
        InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
        InlineKeyboardButton("💰 نظام الشحن", callback_data="admin_charge"),
        InlineKeyboardButton("💵 تعديل الأسعار", callback_data="admin_prices"),
        InlineKeyboardButton("🔧 وضع الصيانة", callback_data="admin_maintenance"),
        InlineKeyboardButton("📚 إدارة الملازم", callback_data="admin_materials"),
        InlineKeyboardButton("🎁 تعديل مكافأة الدعوة", callback_data="admin_invite_reward"),
        InlineKeyboardButton("🔗 تحديث رابط القناة", callback_data="admin_update_channel"),
        InlineKeyboardButton("↩️ العودة للقائمة", callback_data="back_to_menu")
    ]
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.row(buttons[i], buttons[i + 1])
        else:
            keyboard.add(buttons[i])
    
    return keyboard

def check_maintenance(user_id: int) -> bool:
    """التحقق من وضع الصيانة"""
    if db.settings.get('maintenance', False):
        if not (db.users.get(user_id) and db.users[user_id].is_admin):
            return True
    return False

async def send_notification(user_id: int, message: str):
    """إرسال إشعار للمستخدم"""
    try:
        await bot.send_message(user_id, message)
        return True
    except (BotBlocked, ChatNotFound):
        return False
    except Exception as e:
        logger.error(f"خطأ في إرسال الإشعار: {e}")
        return False

async def process_pdf_summary(pdf_file) -> Optional[bytes]:
    """معالجة وتلخيص ملف PDF باستخدام الذكاء الاصطناعي"""
    try:
        # استخراج النص من PDF
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page_num in range(min(len(pdf_reader.pages), 20)):  # الحد الأقصى 20 صفحة
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        if not text.strip():
            return None
        
        # استخدام Gemini AI للتلخيص
        if gemini_model:
            prompt = f"""
            قم بتلخيص هذا النص التعليمي بطريقة منظمة وعلمية مع الحفاظ على الأفكار الرئيسية.
            أعد التنظيم بحذف المعلومات غير المهمة والتركيز على النقاط الأساسية.
            استخدم عناوين واضحة ونقاط محددة.
            النص:
            {text[:3000]}  # الحد الأقصى 3000 حرف
            """
            
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                prompt
            )
            
            summary = response.text
            
            # إنشاء PDF جديد مع الخطوط العربية
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            
            # إعداد الصفحة
            width, height = letter
            y_position = height - 50
            
            # عنوان الملف
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y_position, "ملخص المادة التعليمية")
            y_position -= 30
            
            # تاريخ التلخيص
            c.setFont("Helvetica", 10)
            c.drawString(50, y_position, f"تاريخ التلخيص: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            y_position -= 30
            
            # النص الملخص
            c.setFont("Helvetica", 12)
            lines = summary.split('\n')
            
            for line in lines:
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                    c.setFont("Helvetica", 12)
                
                # معالجة النص العربي
                if any('\u0600' <= char <= '\u06FF' for char in line):
                    try:
                        reshaped = arabic_reshaper.reshape(line)
                        display_text = get_display(reshaped)
                        c.drawString(50, y_position, display_text)
                    except:
                        c.drawString(50, y_position, line)
                else:
                    c.drawString(50, y_position, line)
                
                y_position -= 20
            
            c.save()
            buffer.seek(0)
            return buffer.getvalue()
        
        return None
        
    except Exception as e:
        logger.error(f"خطأ في معالجة PDF: {e}")
        return None

async def process_image_question(image_file) -> Optional[str]:
    """معالجة الصور للإجابة على الأسئلة باستخدام الذكاء الاصطناعي"""
    try:
        if gemini_vision_model:
            # قراءة الصورة
            image = Image.open(image_file)
            
            # استخدام Gemini Vision
            prompt = """
            هذه صورة تحتوي على سؤال أو تمرين تعليمي عراقي.
            يرجى تقديم إجابة علمية مفصلة ومنهجية حسب المنهج العراقي.
            ركز على الخطوات الحلولية والتفسيرات العلمية.
            """
            
            response = await asyncio.to_thread(
                gemini_vision_model.generate_content,
                [prompt, image]
            )
            
            return response.text
        
        return None
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {e}")
        return None

# ========== معالجات الرسائل ==========

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """معالج أمر /start"""
    user_id = message.from_user.id
    
    # التحقق من الصيانة
    if check_maintenance(user_id):
        await message.answer("⚙️ البوت قيد الصيانة حالياً. نعتذر للإزعاج وسنعود قريباً.")
        return
    
    # تسجيل المستخدم الجديد
    if user_id not in db.users:
        user = User(
            user_id,
            message.from_user.username or "",
            message.from_user.first_name or ""
        )
        db.add_user(user)
        
        # إرسال رسالة ترحيب مع الهدية
        welcome_msg = format_arabic(f"""
        🎉 أهلاً وسهلاً بك {user.first_name} في بوت "يلا نتعلم"!
        
        🎁 لقد حصلت على هدية ترحيبية: 1,000 دينار عراقي
        
        💰 رصيدك الحالي: {format_number(user.balance)} دينار
        
        📚 يمكنك استخدام الخدمات التعليمية المتاحة:
        
        1. حساب درجة الإعفاء الفردي
        2. تلخيص الملازم بالذكاء الاصطناعي
        3. أسئلة وأجوبة بالذكاء الاصطناعي
        4. قسم الملازم والمرشحات
        
        كل خدمة بسعر {format_number(db.settings['service_prices']['exemption'])} دينار
        """)
        
        await message.answer(welcome_msg, reply_markup=create_main_menu(user_id))
        
        # إرسال إشعار للمدير
        if ADMIN_ID:
            admin_msg = format_arabic(f"""
            📊 مستخدم جديد انضم للبوت:
            
            👤 الاسم: {user.first_name}
            🆔 الايدي: {user_id}
            📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            👥 إجمالي المستخدمين: {db.stats['total_users']}
            """)
            await send_notification(ADMIN_ID, admin_msg)
    else:
        user = db.users[user_id]
        user.last_active = datetime.now()
        db.update_user(user)
        
        welcome_back = format_arabic(f"""
        أهلاً بعودتك {user.first_name}! 👋
        
        💰 رصيدك الحالي: {format_number(user.balance)} دينار
        
        اختر الخدمة التي تريدها من القائمة:
        """)
        
        await message.answer(welcome_back, reply_markup=create_main_menu(user_id))

@dp.message_handler(commands=['panel'], user_id=ADMIN_ID)
async def cmd_panel(message: types.Message):
    """لوحة تحكم المدير"""
    await message.answer("👑 لوحة تحكم المدير", reply_markup=create_admin_panel())

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message, state: FSMContext):
    """معالجة الرسائل النصية"""
    user_id = message.from_user.id
    
    if check_maintenance(user_id):
        await message.answer("⚙️ البوت قيد الصيانة حالياً.")
        return
    
    user = db.get_user(user_id)
    if not user:
        await cmd_start(message)
        return
    
    current_state = await state.get_state()
    
    # معالجة حالات الإعفاء الفردي
    if current_state == UserStates.waiting_for_course1.state:
        try:
            grade = float(message.text)
            if 0 <= grade <= 100:
                await state.update_data(course1=grade)
                await UserStates.waiting_for_course2.set()
                await message.answer("📝 أدخل درجة الكورس الثاني (0-100):")
            else:
                await message.answer("⚠️ الرجاء إدخال درجة بين 0 و 100:")
        except:
            await message.answer("⚠️ الرجاء إدخال رقم صحيح:")
    
    elif current_state == UserStates.waiting_for_course2.state:
        try:
            grade = float(message.text)
            if 0 <= grade <= 100:
                await state.update_data(course2=grade)
                await UserStates.waiting_for_course3.set()
                await message.answer("📝 أدخل درجة الكورس الثالث (0-100):")
            else:
                await message.answer("⚠️ الرجاء إدخال درجة بين 0 و 100:")
        except:
            await message.answer("⚠️ الرجاء إدخال رقم صحيح:")
    
    elif current_state == UserStates.waiting_for_course3.state:
        try:
            grade = float(message.text)
            if 0 <= grade <= 100:
                await state.update_data(course3=grade)
                
                # حساب المعدل
                data = await state.get_data()
                avg = (data['course1'] + data['course2'] + data['course3']) / 3
                
                # خصم السعر
                price = db.settings['service_prices']['exemption']
                if user.balance >= price:
                    user.balance -= price
                    user.total_spent += price
                    db.update_user(user)
                    
                    # تحديث الإحصائيات
                    db.stats['total_services'] += 1
                    db.stats['total_revenue'] += price
                    db.save_stats()
                    
                    if avg >= 90:
                        result_msg = format_arabic(f"""
                        🎉 مبروك! تم حساب معدلك بنجاح:
                        
                        📊 الدرجات المدخلة:
                        الكورس الأول: {data['course1']}
                        الكورس الثاني: {data['course2']}
                        الكورس الثالث: {data['course3']}
                        
                        ⚖️ المعدل النهائي: {avg:.2f}
                        
                        🏆 أنت معفي من المادة! 
                        تهانينا على هذا الإنجاز!
                        
                        💰 تم خصم: {format_number(price)} دينار
                        💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                        """)
                    else:
                        result_msg = format_arabic(f"""
                        📊 تم حساب معدلك بنجاح:
                        
                        الدرجات المدخلة:
                        الكورس الأول: {data['course1']}
                        الكورس الثاني: {data['course2']}
                        الكورس الثالث: {data['course3']}
                        
                        ⚖️ المعدل النهائي: {avg:.2f}
                        
                        ⚠️ للأسف، أنت لست معفياً من المادة.
                        المعدل المطلوب للإعفاء: 90
                        
                        💰 تم خصم: {format_number(price)} دينار
                        💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                        """)
                    
                    await message.answer(result_msg, reply_markup=create_main_menu(user_id))
                    await state.finish()
                else:
                    await message.answer(f"💰 رصيدك غير كافي. تحتاج {format_number(price)} دينار")
                    await state.finish()
            else:
                await message.answer("⚠️ الرجاء إدخال درجة بين 0 و 100:")
        except:
            await message.answer("⚠️ الرجاء إدخال رقم صحيح:")
    
    # معالجة الأسئلة النصية
    elif current_state == UserStates.waiting_for_question.state:
        if gemini_model:
            price = db.settings['service_prices']['qa']
            if user.balance >= price:
                user.balance -= price
                user.total_spent += price
                db.update_user(user)
                
                db.stats['total_services'] += 1
                db.stats['total_revenue'] += price
                db.save_stats()
                
                await message.answer("🤔 جارٍ تحليل سؤالك والبحث عن الإجابة المناسبة...")
                
                try:
                    prompt = f"""
                    هذا سؤال طالب عراقي يرجى الإجابة عليه بطريقة علمية مفصلة ومنهجية حسب المنهج العراقي:
                    
                    {message.text}
                    
                    قدم الإجابة بخطوات واضحة وتفسيرات علمية مع أمثلة إذا لزم الأمر.
                    """
                    
                    response = await asyncio.to_thread(
                        gemini_model.generate_content,
                        prompt
                    )
                    
                    answer = response.text
                    
                    response_msg = format_arabic(f"""
                    📝 إجابة سؤالك:
                    
                    {answer}
                    
                    💰 تم خصم: {format_number(price)} دينار
                    💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                    """)
                    
                    await message.answer(response_msg, reply_markup=create_main_menu(user_id))
                except Exception as e:
                    logger.error(f"خطأ في معالجة السؤال: {e}")
                    await message.answer("⚠️ حدث خطأ في معالجة سؤالك. يرجى المحاولة مرة أخرى.")
                
                await state.finish()
            else:
                await message.answer(f"💰 رصيدك غير كافي. تحتاج {format_number(price)} دينار")
                await state.finish()
    
    # معالجة أوامر المدير
    elif user.is_admin:
        if current_state == UserStates.admin_waiting_user_id.state:
            try:
                target_id = int(message.text)
                await state.update_data(target_user_id=target_id)
                await UserStates.admin_waiting_amount.set()
                await message.answer("💵 أدخل المبلغ المطلوب شحنه:")
            except:
                await message.answer("⚠️ الرجاء إدخال ايدي مستخدم صحيح:")
        
        elif current_state == UserStates.admin_waiting_amount.state:
            try:
                amount = int(message.text)
                data = await state.get_data()
                target_id = data['target_user_id']
                
                target_user = db.get_user(target_id)
                if target_user:
                    target_user.balance += amount
                    db.update_user(target_user)
                    
                    await message.answer(f"✅ تم شحن {format_number(amount)} دينار للمستخدم {target_id}")
                    
                    # إرسال إشعار للمستخدم
                    notification = format_arabic(f"""
                    💰 إشعار إيداع:
                    
                    تم إضافة مبلغ: {format_number(amount)} دينار
                    رصيدك الجديد: {format_number(target_user.balance)} دينار
                    
                    بواسطة: إدارة البوت
                    """)
                    await send_notification(target_id, notification)
                else:
                    await message.answer("⚠️ المستخدم غير موجود")
                
                await state.finish()
            except:
                await message.answer("⚠️ الرجاء إدخال مبلغ صحيح:")
        
        elif current_state == UserStates.admin_waiting_price_service.state:
            try:
                price = int(message.text)
                data = await state.get_data()
                service = data['service_to_update']
                
                db.settings['service_prices'][service] = price
                db.save_settings()
                
                service_names = {
                    'exemption': 'حساب درجة الإعفاء الفردي',
                    'summarize': 'تلخيص الملازم',
                    'qa': 'سؤال وجواب',
                    'materials': 'قسم الملازم'
                }
                
                await message.answer(
                    f"✅ تم تحديث سعر خدمة '{service_names.get(service, service)}' إلى {format_number(price)} دينار",
                    reply_markup=create_admin_panel()
                )
                await state.finish()
            except:
                await message.answer("⚠️ الرجاء إدخال سعر صحيح:")

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message, state: FSMContext):
    """معالجة ملفات PDF"""
    user_id = message.from_user.id
    
    if check_maintenance(user_id):
        await message.answer("⚙️ البوت قيد الصيانة حالياً.")
        return
    
    user = db.get_user(user_id)
    if not user:
        return
    
    current_state = await state.get_state()
    
    if current_state == UserStates.waiting_for_pdf.state:
        if message.document.mime_type == 'application/pdf':
            price = db.settings['service_prices']['summarize']
            
            if user.balance >= price:
                user.balance -= price
                user.total_spent += price
                db.update_user(user)
                
                db.stats['total_services'] += 1
                db.stats['total_revenue'] += price
                db.save_stats()
                
                await message.answer("📄 جارٍ معالجة ملف PDF وتلخيصه...")
                
                try:
                    # تحميل الملف
                    file_info = await bot.get_file(message.document.file_id)
                    downloaded_file = await bot.download_file(file_info.file_path)
                    
                    # معالجة وتلخيص PDF
                    pdf_bytes = await process_pdf_summary(downloaded_file)
                    
                    if pdf_bytes:
                        # إرسال الملف الملخص
                        summary_file = io.BytesIO(pdf_bytes)
                        summary_file.name = f"ملخص_{message.document.file_name}"
                        
                        await message.answer_document(
                            InputFile(summary_file, filename=summary_file.name),
                            caption=format_arabic(f"""
                            ✅ تم تلخيص ملف PDF بنجاح!
                            
                            💰 تم خصم: {format_number(price)} دينار
                            💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                            
                            📝 تم تنظيم النص وحذف المعلومات غير المهمة.
                            """)
                        )
                    else:
                        await message.answer("⚠️ تعذر استخراج النص من ملف PDF. تأكد من أن الملف يحتوي على نص قابل للقراءة.")
                        # إعادة المبلغ
                        user.balance += price
                        db.update_user(user)
                
                except Exception as e:
                    logger.error(f"خطأ في معالجة PDF: {e}")
                    await message.answer("⚠️ حدث خطأ في معالجة الملف. يرجى المحاولة مرة أخرى.")
                    # إعادة المبلغ
                    user.balance += price
                    db.update_user(user)
                
                await state.finish()
            else:
                await message.answer(f"💰 رصيدك غير كافي. تحتاج {format_number(price)} دينار")
                await state.finish()
        else:
            await message.answer("⚠️ يرجى إرسال ملف PDF فقط")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message, state: FSMContext):
    """معالجة الصور للأسئلة"""
    user_id = message.from_user.id
    
    if check_maintenance(user_id):
        await message.answer("⚙️ البوت قيد الصيانة حالياً.")
        return
    
    user = db.get_user(user_id)
    if not user:
        return
    
    current_state = await state.get_state()
    
    if current_state == UserStates.waiting_for_image.state:
        price = db.settings['service_prices']['qa']
        
        if user.balance >= price:
            user.balance -= price
            user.total_spent += price
            db.update_user(user)
            
            db.stats['total_services'] += 1
            db.stats['total_revenue'] += price
            db.save_stats()
            
            await message.answer("🖼️ جارٍ تحليل الصورة والإجابة على السؤال...")
            
            try:
                # تحميل الصورة
                file_info = await bot.get_file(message.photo[-1].file_id)
                downloaded_file = await bot.download_file(file_info.file_path)
                
                # معالجة الصورة
                answer = await process_image_question(downloaded_file)
                
                if answer:
                    response_msg = format_arabic(f"""
                    📝 إجابة سؤالك من الصورة:
                    
                    {answer}
                    
                    💰 تم خصم: {format_number(price)} دينار
                    💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                    """)
                    
                    await message.answer(response_msg, reply_markup=create_main_menu(user_id))
                else:
                    await message.answer("⚠️ تعذر تحليل الصورة. يرجى المحاولة بصورة أوضح.")
                    # إعادة المبلغ
                    user.balance += price
                    db.update_user(user)
            
            except Exception as e:
                logger.error(f"خطأ في معالجة الصورة: {e}")
                await message.answer("⚠️ حدث خطأ في معالجة الصورة. يرجى المحاولة مرة أخرى.")
                # إعادة المبلغ
                user.balance += price
                db.update_user(user)
            
            await state.finish()
        else:
            await message.answer(f"💰 رصيدك غير كافي. تحتاج {format_number(price)} دينار")
            await state.finish()

# ========== معالجات CallbackQuery ==========

@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def back_to_menu(callback_query: types.CallbackQuery):
    """العودة للقائمة الرئيسية"""
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=format_arabic("🏠 القائمة الرئيسية"),
        reply_markup=create_main_menu(callback_query.from_user.id)
    )

@dp.callback_query_handler(lambda c: c.data == 'show_balance')
async def show_balance(callback_query: types.CallbackQuery):
    """عرض الرصيد"""
    await bot.answer_callback_query(callback_query.id)
    
    user = db.get_user(callback_query.from_user.id)
    if user:
        balance_msg = format_arabic(f"""
        💰 معلومات رصيدك:
        
        الرصيد الحالي: {format_number(user.balance)} دينار
        إجمالي المشتريات: {format_number(user.total_spent)} دينار
        
        📅 تاريخ الانضمام: {user.join_date.strftime('%Y-%m-%d')}
        
        لشحن الرصيد، تواصل مع الدعم الفني:
        @{SUPPORT_USERNAME.replace('@', '')}
        """)
        
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=balance_msg,
            reply_markup=create_main_menu(callback_query.from_user.id)
        )

@dp.callback_query_handler(lambda c: c.data == 'invite_friends')
async def invite_friends(callback_query: types.CallbackQuery):
    """نظام الدعوة"""
    await bot.answer_callback_query(callback_query.id)
    
    user = db.get_user(callback_query.from_user.id)
    if user:
        invite_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user.invite_code}"
        reward = db.settings['invite_reward']
        
        invite_msg = format_arabic(f"""
        👥 نظام دعوة الأصدقاء
        
        🔗 رابط دعوتك الخاص:
        {invite_link}
        
        🎁 مكافأة الدعوة:
        لكل صديق يدخل عبر رابطك: {format_number(reward)} دينار
        
        📊 عدد المدعوين: {user.invited_count}
        
        📝 كيفية العمل:
        1. أرسل الرابط لصديقك
        2. صديقك يضغط على الرابط
        3. يبدأ باستخدام البوت
        4. تحصل على {format_number(reward)} دينار تلقائياً
        """)
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="back_to_menu"))
        
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=invite_msg,
            reply_markup=keyboard
        )

@dp.callback_query_handler(lambda c: c.data.startswith('service_'))
async def handle_service(callback_query: types.CallbackQuery, state: FSMContext):
    """معالجة طلبات الخدمات"""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    service_type = callback_query.data.replace('service_', '')
    
    if check_maintenance(user_id):
        await bot.send_message(user_id, "⚙️ البوت قيد الصيانة حالياً.")
        return
    
    user = db.get_user(user_id)
    if not user:
        return
    
    price = db.settings['service_prices'].get(service_type, 1000)
    
    if user.balance < price:
        await bot.send_message(
            user_id,
            f"💰 رصيدك غير كافي لهذه الخدمة.\nالسعر: {format_number(price)} دينار\nرصيدك: {format_number(user.balance)} دينار\n\nلشحن الرصيد تواصل مع الدعم: @{SUPPORT_USERNAME.replace('@', '')}",
            reply_markup=create_main_menu(user_id)
        )
        return
    
    if service_type == 'exemption':
        await UserStates.waiting_for_course1.set()
        await bot.send_message(
            user_id,
            "📝 أدخل درجة الكورس الأول (0-100):",
            reply_markup=ReplyKeyboardRemove()
        )
    
    elif service_type == 'summarize':
        await UserStates.waiting_for_pdf.set()
        await bot.send_message(
            user_id,
            f"📄 أرسل ملف PDF لتلخيصه (السعر: {format_number(price)} دينار)",
            reply_markup=ReplyKeyboardRemove()
        )
    
    elif service_type == 'qa':
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📝 نص", callback_data="qa_text"),
            InlineKeyboardButton("🖼️ صورة", callback_data="qa_image")
        )
        keyboard.add(InlineKeyboardButton("↩️ إلغاء", callback_data="back_to_menu"))
        
        await bot.send_message(
            user_id,
            f"❓ اختر طريقة إرسال السؤال (السعر: {format_number(price)} دينار):",
            reply_markup=keyboard
        )
    
    elif service_type == 'materials':
        materials = db.get_all_materials()
        if materials:
            keyboard = InlineKeyboardMarkup(row_width=1)
            
            # تصنيف حسب المرحلة
            stages = set(m.stage for m in materials)
            for stage in stages:
                stage_materials = [m for m in materials if m.stage == stage]
                keyboard.add(InlineKeyboardButton(
                    f"📚 {stage} ({len(stage_materials)})",
                    callback_data=f"materials_stage_{stage}"
                ))
            
            keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="back_to_menu"))
            
            await bot.send_message(
                user_id,
                f"📚 اختر المرحلة الدراسية لعرض الملازم (السعر: {format_number(price)} دينار):",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "⚠️ لا توجد ملازم متاحة حالياً.",
                reply_markup=create_main_menu(user_id)
            )

@dp.callback_query_handler(lambda c: c.data in ['qa_text', 'qa_image'])
async def handle_qa_method(callback_query: types.CallbackQuery, state: FSMContext):
    """اختيار طريقة السؤال"""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'qa_text':
        await UserStates.waiting_for_question.set()
        await bot.send_message(
            user_id,
            "📝 اكتب سؤالك الآن:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await UserStates.waiting_for_image.set()
        await bot.send_message(
            user_id,
            "🖼️ أرسل صورة السؤال الآن:",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.callback_query_handler(lambda c: c.data.startswith('materials_stage_'))
async def show_materials_stage(callback_query: types.CallbackQuery):
    """عرض ملازم مرحلة محددة"""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    stage = callback_query.data.replace('materials_stage_', '')
    
    user = db.get_user(user_id)
    if not user:
        return
    
    price = db.settings['service_prices']['materials']
    
    if user.balance < price:
        await bot.send_message(
            user_id,
            f"💰 رصيدك غير كافي. تحتاج {format_number(price)} دينار"
        )
        return
    
    materials = db.get_materials_by_stage(stage)
    
    if materials:
        # خصم السعر
        user.balance -= price
        user.total_spent += price
        db.update_user(user)
        
        db.stats['total_services'] += 1
        db.stats['total_revenue'] += price
        db.save_stats()
        
        for material in materials[:5]:  # إرسال أول 5 ملازم فقط
            try:
                await bot.send_document(
                    user_id,
                    material.file_id,
                    caption=format_arabic(f"""
                    📚 {material.name}
                    
                    📝 {material.description}
                    
                    🎓 المرحلة: {material.stage}
                    
                    💰 تم خصم: {format_number(price)} دينار
                    💳 رصيدك المتبقي: {format_number(user.balance)} دينار
                    """)
                )
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"خطأ في إرسال الملف: {e}")
        
        await bot.send_message(
            user_id,
            f"✅ تم إرسال {len(materials)} ملف لمرحلة {stage}",
            reply_markup=create_main_menu(user_id)
        )
    else:
        await bot.send_message(
            user_id,
            f"⚠️ لا توجد ملازم لمرحلة {stage}",
            reply_markup=create_main_menu(user_id)
        )

# ========== لوحة التحكم ==========

@dp.callback_query_handler(lambda c: c.data == 'admin_panel')
async def admin_panel(callback_query: types.CallbackQuery):
    """فتح لوحة التحكم"""
    await bot.answer_callback_query(callback_query.id)
    
    user = db.get_user(callback_query.from_user.id)
    if user and user.is_admin:
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="👑 لوحة تحكم المدير",
            reply_markup=create_admin_panel()
        )
    else:
        await bot.answer_callback_query(callback_query.id, "⚠️ ليس لديك صلاحية الوصول", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'admin_stats')
async def admin_stats(callback_query: types.CallbackQuery):
    """عرض إحصائيات البوت"""
    await bot.answer_callback_query(callback_query.id)
    
    stats = db.stats
    total_balance = sum(u.balance for u in db.users.values())
    total_revenue = stats.get('total_revenue', 0)
    
    stats_msg = format_arabic(f"""
    📊 إحصائيات البوت:
    
    👥 إجمالي المستخدمين: {format_number(stats.get('total_users', 0))}
    📅 المستخدمين النشطين اليوم: {format_number(stats.get('active_today', 0))}
    
    💰 إجمالي الأرصدة: {format_number(total_balance)} دينار
    💵 إجمالي الإيرادات: {format_number(total_revenue)} دينار
    
    🛒 إجمالي الخدمات المباعة: {format_number(stats.get('total_services', 0))}
    
    📈 أسعار الخدمات:
    • حساب الإعفاء: {format_number(db.settings['service_prices']['exemption'])} دينار
    • تلخيص PDF: {format_number(db.settings['service_prices']['summarize'])} دينار
    • سؤال وجواب: {format_number(db.settings['service_prices']['qa'])} دينار
    • قسم الملازم: {format_number(db.settings['service_prices']['materials'])} دينار
    
    🎁 مكافأة الدعوة: {format_number(db.settings['invite_reward'])} دينار
    ⚙️ وضع الصيانة: {'مفعل' if db.settings.get('maintenance') else 'معطل'}
    """)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="admin_panel"))
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=stats_msg,
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_users')
async def admin_users(callback_query: types.CallbackQuery):
    """إدارة المستخدمين"""
    await bot.answer_callback_query(callback_query.id)
    
    users = list(db.users.values())
    users.sort(key=lambda x: x.join_date, reverse=True)
    
    users_list = ""
    for i, user in enumerate(users[:10], 1):  # عرض أول 10 مستخدمين فقط
        role = "👑" if user.is_admin else "👤"
        status = "❌" if user.is_blocked else "✅"
        users_list += f"{i}. {role} {user.first_name} - {status} - {format_number(user.balance)} دينار\n"
    
    users_msg = format_arabic(f"""
    👥 إدارة المستخدمين (أحدث 10):
    
    {users_list}
    
    إجمالي المستخدمين: {len(users)}
    """)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user"),
        InlineKeyboardButton("👑 رفع مشرف", callback_data="admin_promote_user")
    )
    keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="admin_panel"))
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=users_msg,
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_charge')
async def admin_charge(callback_query: types.CallbackQuery, state: FSMContext):
    """نظام شحن الرصيد"""
    await bot.answer_callback_query(callback_query.id)
    
    await UserStates.admin_waiting_user_id.set()
    await bot.send_message(
        callback_query.from_user.id,
        "🆔 أرسل ايدي المستخدم للشحن:"
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_prices')
async def admin_prices(callback_query: types.CallbackQuery):
    """تعديل أسعار الخدمات"""
    await bot.answer_callback_query(callback_query.id)
    
    prices = db.settings['service_prices']
    
    prices_msg = format_arabic(f"""
    💵 أسعار الخدمات الحالية:
    
    1. حساب درجة الإعفاء الفردي: {format_number(prices['exemption'])} دينار
    2. تلخيص الملازم: {format_number(prices['summarize'])} دينار
    3. سؤال وجواب: {format_number(prices['qa'])} دينار
    4. قسم الملازم: {format_number(prices['materials'])} دينار
    
    اختر الخدمة لتعديل سعرها:
    """)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("1. حساب الإعفاء", callback_data="admin_price_exemption"),
        InlineKeyboardButton("2. تلخيص PDF", callback_data="admin_price_summarize")
    )
    keyboard.add(
        InlineKeyboardButton("3. سؤال وجواب", callback_data="admin_price_qa"),
        InlineKeyboardButton("4. قسم الملازم", callback_data="admin_price_materials")
    )
    keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="admin_panel"))
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=prices_msg,
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith('admin_price_'))
async def admin_update_price(callback_query: types.CallbackQuery, state: FSMContext):
    """تحديث سعر خدمة محددة"""
    await bot.answer_callback_query(callback_query.id)
    
    service = callback_query.data.replace('admin_price_', '')
    service_names = {
        'exemption': 'حساب درجة الإعفاء الفردي',
        'summarize': 'تلخيص الملازم',
        'qa': 'سؤال وجواب',
        'materials': 'قسم الملازم'
    }
    
    current_price = db.settings['service_prices'][service]
    
    await state.update_data(service_to_update=service)
    await UserStates.admin_waiting_price_service.set()
    
    await bot.send_message(
        callback_query.from_user.id,
        format_arabic(f"""
        💵 تحديث سعر خدمة '{service_names.get(service, service)}'
        
        السعر الحالي: {format_number(current_price)} دينار
        
        أدخل السعر الجديد (بالدينار العراقي):
        """)
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_maintenance')
async def admin_maintenance(callback_query: types.CallbackQuery):
    """تفعيل/تعطيل وضع الصيانة"""
    await bot.answer_callback_query(callback_query.id)
    
    current_status = db.settings.get('maintenance', False)
    new_status = not current_status
    
    db.settings['maintenance'] = new_status
    db.save_settings()
    
    status_text = "مفعل" if new_status else "معطل"
    
    await bot.send_message(
        callback_query.from_user.id,
        f"⚙️ تم {'تفعيل' if new_status else 'تعطيل'} وضع الصيانة"
    )
    
    # إرسال إشعار لجميع المستخدمين إذا تم تفعيل الصيانة
    if new_status:
        for user_id in db.users:
            if user_id != ADMIN_ID:
                try:
                    await send_notification(user_id, "⚠️ البوت قيد الصيانة حالياً. نعتذر للإزعاج وسنعود قريباً.")
                except:
                    pass

@dp.callback_query_handler(lambda c: c.data == 'admin_materials')
async def admin_materials(callback_query: types.CallbackQuery):
    """إدارة الملازم"""
    await bot.answer_callback_query(callback_query.id)
    
    materials = db.get_all_materials()
    
    materials_msg = format_arabic(f"""
    📚 إدارة الملازم والمرشحات
    
    إجمالي الملازم: {len(materials)}
    
    اختر الإجراء المطلوب:
    """)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("➕ إضافة ملزمة جديدة", callback_data="admin_add_material"),
        InlineKeyboardButton("🗑️ حذف ملزمة", callback_data="admin_delete_material"),
        InlineKeyboardButton("📋 عرض جميع الملازم", callback_data="admin_view_materials")
    )
    keyboard.add(InlineKeyboardButton("↩️ العودة", callback_data="admin_panel"))
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=materials_msg,
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_invite_reward')
async def admin_invite_reward(callback_query: types.CallbackQuery, state: FSMContext):
    """تعديل مكافأة الدعوة"""
    await bot.answer_callback_query(callback_query.id)
    
    current_reward = db.settings['invite_reward']
    
    await UserStates.admin_waiting_invite_reward.set()
    
    await bot.send_message(
        callback_query.from_user.id,
        format_arabic(f"""
        🎁 تعديل مكافأة الدعوة
        
        المكافأة الحالية: {format_number(current_reward)} دينار
        
        أدخل المكافأة الجديدة (بالدينار العراقي):
        """)
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_update_channel')
async def admin_update_channel(callback_query: types.CallbackQuery):
    """تحديث رابط القناة"""
    await bot.answer_callback_query(callback_query.id)
    
    await bot.send_message(
        callback_query.from_user.id,
        format_arabic(f"""
        🔗 تحديث رابط قناة البوت
        
        الرابط الحالي: {db.settings.get('channel_link', 'غير محدد')}
        
        أرسل الرابط الجديد:
        """)
    )

# ========== معالجة تحديث رابط القناة ==========

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text.startswith('http'))
async def update_channel_link(message: types.Message):
    """تحديث رابط القناة"""
    if message.text.startswith('http'):
        db.settings['channel_link'] = message.text
        db.save_settings()
        
        await message.answer(f"✅ تم تحديث رابط القناة إلى:\n{message.text}")
    else:
        await message.answer("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http أو https")

# ========== معالجة مكافأة الدعوة ==========

@dp.message_handler(state=UserStates.admin_waiting_invite_reward)
async def handle_invite_reward_update(message: types.Message, state: FSMContext):
    """تحديث مكافأة الدعوة"""
    try:
        reward = int(message.text)
        if reward >= 0:
            db.settings['invite_reward'] = reward
            db.save_settings()
            
            await message.answer(f"✅ تم تحديث مكافأة الدعوة إلى {format_number(reward)} دينار")
        else:
            await message.answer("⚠️ يرجى إدخال قيمة موجبة أو صفر")
    except:
        await message.answer("⚠️ يرجى إدخال رقم صحيح")
    
    await state.finish()

# ========== تشغيل البوت ==========

async def on_startup(dp):
    """دالة التشغيل"""
    logger.info("✅ بدأ تشغيل البوت...")
    
    # إرسال إشعار للمدير
    try:
        await bot.send_message(
            ADMIN_ID,
            "🤖 بوت 'يلا نتعلم' يعمل الآن!\n\n"
            f"👥 المستخدمين: {db.stats['total_users']}\n"
            f"💰 إجمالي الإيرادات: {format_number(db.stats.get('total_revenue', 0))} دينار"
        )
    except:
        pass

async def on_shutdown(dp):
    """دالة الإيقاف"""
    logger.info("⏹️ إيقاف البوت...")
    await bot.close()

if __name__ == '__main__':
    # تشغيل البوت
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
