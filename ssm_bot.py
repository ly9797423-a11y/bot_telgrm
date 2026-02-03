# ssm_bot.py - النسخة الكاملة المصححة
import os
import sys
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify
import requests
import random
import string

# ==================== المكتبات الأساسية ====================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        filters,
        ContextTypes,
        ConversationHandler
    )
    from telegram.constants import ParseMode, ChatAction
    print("✅ مكتبة Telegram مثبتة")
except ImportError as e:
    print(f"❌ خطأ في مكتبة Telegram: {e}")
    print("✅ قم بتشغيل: pip install python-telegram-bot")
    sys.exit(1)

try:
    import google.genai as genai  # المكتبة الجديدة
    print("✅ مكتبة Google GenAI مثبتة")
except ImportError:
    print("⚠️ مكتبة Google GenAI غير مثبتة، سيتم تعطيل خدمات الذكاء الاصطناعي")
    genai = None

try:
    from PIL import Image
    import io
    import aiohttp
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    print("✅ مكتبات الملفات والصور مثبتة")
except ImportError as e:
    print(f"⚠️ مكتبات الملفات غير مثبتة: {e}")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    print("✅ مكتبات العربية مثبتة")
except ImportError:
    print("⚠️ مكتبات العربية غير مثبتة")
    arabic_reshaper = None

# ==================== التكوين ====================
TOKEN = os.environ.get("BOT_TOKEN", "8481569753:AAH3alhJ0hcHldht-PxV7j8TzBlRsMqAqGI")
GEMINI_API_KEY = os.environ.get("GEMINI_KEY", "AIzaSyAqlug21bw_eI60ocUtc1Z76NhEUc-zuzY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6130994941"))
SUPPORT_USERNAME = os.environ.get("SUPPORT_USER", "Allawi04@")
BOT_USERNAME = "FC4Xbot"
DATABASE_NAME = "ssm_bot.db"

# أسعار الخدمات (قابلة للتغيير من لوحة التحكم)
SERVICE_PRICES = {
    "exemption": 1000,
    "summarize": 1000,
    "qna": 1000,
    "materials": 1000
}

# ==================== تطبيق Flask ====================
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>بوت يلا نتعلم - للطلاب العراقيين</title>
        <style>
            body { font-family: 'Arial', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: 50px auto; background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            h1 { text-align: center; font-size: 2.5em; margin-bottom: 30px; color: #fff; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .status-card { background: rgba(255,255,255,0.2); border-radius: 15px; padding: 20px; margin: 20px 0; border-left: 5px solid #4CAF50; }
            .btn { display: inline-block; padding: 12px 30px; margin: 10px; background: linear-gradient(45deg, #FF416C, #FF4B2B); color: white; text-decoration: none; border-radius: 50px; font-weight: bold; transition: transform 0.3s; }
            .btn:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(255,75,43,0.4); }
            .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
            .info-box { background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; text-align: center; }
            .footer { text-align: center; margin-top: 40px; font-size: 0.9em; opacity: 0.8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت "يلا نتعلم" للطلاب العراقيين</h1>
            
            <div class="status-card">
                <h2>✅ حالة البوت: <span style="color: #4CAF50;">شغال وعامل</span></h2>
                <p>تم تشغيل البوت بنجاح على منصة Render</p>
                <p>🕒 وقت التشغيل: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
            
            <div class="info-grid">
                <div class="info-box">
                    <h3>👑 المدير</h3>
                    <p>""" + str(ADMIN_ID) + """</p>
                </div>
                <div class="info-box">
                    <h3>💬 الدعم</h3>
                    <p>""" + SUPPORT_USERNAME + """</p>
                </div>
                <div class="info-box">
                    <h3>🤖 يوزر البوت</h3>
                    <p>@""" + BOT_USERNAME + """</p>
                </div>
                <div class="info-box">
                    <h3>🚀 المنصة</h3>
                    <p>Render.com</p>
                </div>
            </div>
            
            <div style="text-align: center;">
                <a href="https://t.me/""" + BOT_USERNAME + """" class="btn" target="_blank">🚀 استخدام البوت في تلجرام</a>
                <a href="https://t.me/""" + SUPPORT_USERNAME.replace("@", "") + """" class="btn" target="_blank">👨‍💻 الدعم الفني</a>
            </div>
            
            <div class="footer">
                <p>© 2024 بوت يلا نتعلم - جميع الحقوق محفوظة</p>
                <p>تم التطوير خصيصاً للطلاب العراقيين</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "yalanatelim-bot",
        "version": "2.0.0"
    }), 200

@app.route('/admin/<secret>')
def admin_dashboard(secret):
    if secret != hashlib.md5(str(ADMIN_ID).encode()).hexdigest()[:10]:
        return "غير مصرح", 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    stats['total_balance'] = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
    stats['today_users'] = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify(stats)

# ==================== قاعدة البيانات ====================
def init_db():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            invited_by INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    ''')
    
    # جدول المعاملات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول الدعوات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER,
            invited_id INTEGER UNIQUE,
            reward_claimed INTEGER DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invited_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول الملازم
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            file_id TEXT,
            file_type TEXT DEFAULT 'document',
            grade TEXT,
            downloads INTEGER DEFAULT 0,
            added_by INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # جدول استخدام الخدمات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_type TEXT,
            cost INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # جدول الإعدادات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # الإعدادات الافتراضية
    default_settings = [
        ("welcome_bonus", "1000", "مكافأة ترحيب للمستخدمين الجدد"),
        ("referral_bonus", "500", "مكافأة دعوة الأصدقاء"),
        ("maintenance_mode", "0", "وضع الصيانة (1 = نشط, 0 = غير نشط)"),
        ("support_username", SUPPORT_USERNAME, "يوزر الدعم الفني"),
        ("admin_id", str(ADMIN_ID), "أيدي المدير"),
        ("exemption_price", "1000", "سعر خدمة حساب الإعفاء"),
        ("summarize_price", "1000", "سعر خدمة تلخيص PDF"),
        ("qna_price", "1000", "سعر خدمة الأسئلة والأجوبة"),
        ("materials_price", "1000", "سعر خدمة الملازم"),
        ("bot_username", BOT_USERNAME, "يوزر البوت"),
        ("min_charge", "1000", "أقل مبلغ للشحن"),
        ("max_charge", "100000", "أعلى مبلغ للشحن")
    ]
    
    for key, value, desc in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value, description) 
            VALUES (?, ?, ?)
        ''', (key, value, desc))
    
    # إضافة مواد افتراضية إذا لم تكن موجودة
    cursor.execute("SELECT COUNT(*) FROM materials")
    if cursor.fetchone()[0] == 0:
        default_materials = [
            ("رياضيات السادس العلمي", "ملزمة شاملة لرياضيات السادس العلمي مع حلول", "", "السادس العلمي"),
            ("الفيزياء السادس الأدبي", "ملخص فيزياء شامل للسادس الأدبي", "", "السادس الأدبي"),
            ("الكيمياء السادس العلمي", "ملزمة كيمياء مع تجارب عملية", "", "السادس العلمي"),
            ("الأحياء السادس العلمي", "ملخص أحياء مع رسوم توضيحية", "", "السادس العلمي"),
            ("اللغة العربية", "قواعد اللغة العربية للسادس", "", "السادس")
        ]
        cursor.executemany(
            "INSERT INTO materials (name, description, file_id, grade) VALUES (?, ?, ?, ?)",
            default_materials
        )
    
    # إنشاء فهارس لتحسين الأداء
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_join ON users(join_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_grade ON materials(grade)")
    
    conn.commit()
    conn.close()
    print("✅ تم تهيئة قاعدة البيانات بنجاح")

def get_db_connection():
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False, timeout=10)

def get_user(user_id: int):
    """الحصول على بيانات المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id: int, username: str, first_name: str, last_name: str = "", invited_by: int = 0):
    """إنشاء مستخدم جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # الحصول على مكافأة الترحيب
        cursor.execute("SELECT value FROM settings WHERE key = 'welcome_bonus'")
        welcome_bonus = int(cursor.fetchone()[0])
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, balance, invited_by) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, welcome_bonus, invited_by))
        
        # تسجيل المعاملة
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, welcome_bonus, "welcome_bonus", "مكافأة ترحيب"))
        
        # إذا كان هناك مدعو، منح مكافأة الدعوة
        if invited_by > 0:
            cursor.execute("SELECT value FROM settings WHERE key = 'referral_bonus'")
            referral_bonus = int(cursor.fetchone()[0])
            
            # تسجيل الدعوة
            cursor.execute('''
                INSERT OR IGNORE INTO referrals (inviter_id, invited_id)
                VALUES (?, ?)
            ''', (invited_by, user_id))
            
            # منح المكافأة للمدعو
            cursor.execute('''
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            ''', (referral_bonus, invited_by))
            
            # تسجيل المعاملة للمدعو
            cursor.execute('''
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (?, ?, ?, ?)
            ''', (invited_by, referral_bonus, "referral_bonus", f"مكافأة دعوة للمستخدم {user_id}"))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في إنشاء المستخدم: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_balance(user_id: int, amount: int, trans_type: str, description: str = ""):
    """تحديث رصيد المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # تحديث الرصيد
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, last_active = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (amount, user_id))
        
        if cursor.rowcount == 0:
            return False
        
        # تسجيل المعاملة
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, trans_type, description))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث الرصيد: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_balance(user_id: int):
    """الحصول على رصيد المستخدم"""
    user = get_user(user_id)
    return user[4] if user else 0  # العمود 4 هو balance

def get_setting(key: str, default: str = ""):
    """الحصول على إعداد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def update_setting(key: str, value: str):
    """تحديث إعداد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings 
        SET value = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE key = ?
    ''', (value, key))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def log_service_usage(user_id: int, service_type: str, cost: int, details: str = ""):
    """تسجيل استخدام الخدمة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO service_logs (user_id, service_type, cost, details)
        VALUES (?, ?, ?, ?)
    ''', (user_id, service_type, cost, details))
    conn.commit()
    conn.close()

# ==================== دوال المساعدة ====================
def format_arabic(text: str) -> str:
    """تنسيق النص العربي"""
    if arabic_reshaper:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except:
            return text
    return text

def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}"

def create_referral_link(user_id: int) -> str:
    """إنشاء رابط دعوة"""
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

def validate_grades(grades_str: str):
    """التحقق من صحة الدرجات"""
    try:
        grades = [float(g.strip()) for g in grades_str.split()]
        if len(grades) != 3:
            return None, "يجب إدخال 3 درجات فقط"
        
        for grade in grades:
            if grade < 0 or grade > 100:
                return None, "الدرجات يجب أن تكون بين 0 و 100"
        
        average = sum(grades) / 3
        return grades, average, None
    except ValueError:
        return None, None, "يجب إدخال أرقام صحيحة"

# ==================== خدمات الذكاء الاصطناعي ====================
def setup_ai():
    """تهيئة الذكاء الاصطناعي"""
    if not genai or not GEMINI_API_KEY:
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        print(f"❌ خطأ في تهيئة الذكاء الاصطناعي: {e}")
        return None

async def ask_ai(question: str) -> str:
    """سؤال الذكاء الاصطناعي"""
    model = setup_ai()
    if not model:
        return "عذراً، خدمة الذكاء الاصطناعي غير متوفرة حالياً."
    
    try:
        prompt = f"""
        أنت مساعد تعليمي للطلاب العراقيين.
        أجب عن السؤال التالي بناءً على المنهج العراقي وبطريقة واضحة ومنظمة:
        
        السؤال: {question}
        
        متطلبات الإجابة:
        1. استخدم اللغة العربية الفصحى
        2. كن دقيقاً وواضحاً
        3. إذا كان السؤال رياضياً، اذكر الخطوات
        4. راعي مستوى الطالب
        5. لا تخرج عن نطاق السؤال
        """
        
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as e:
        print(f"❌ خطأ في الذكاء الاصطناعي: {e}")
        return "عذراً، حدث خطأ في معالجة سؤالك. يرجى المحاولة لاحقاً."

async def summarize_text(text: str) -> str:
    """تلخيص النص"""
    model = setup_ai()
    if not model:
        return "عذراً، خدمة التلخيص غير متوفرة."
    
    try:
        prompt = f"""
        قم بتلخيص النص التالي بطريقة علمية ومنظمة:
        
        {text[:3000]}
        
        متطلبات الملخص:
        1. كن مختصراً ومركزاً على النقاط الرئيسية
        2. استخدم اللغة العربية الفصحى
        3. نظم المعلومات في نقاط
        4. احذف المعلومات غير المهمة
        5. لا تتعدى 500 كلمة
        """
        
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as e:
        print(f"❌ خطأ في التلخيص: {e}")
        return "عذراً، حدث خطأ في تلخيص النص."

# ==================== معالجات البوت ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من وضع الصيانة
    if get_setting("maintenance_mode") == "1":
        await update.message.reply_text(
            "⛔ البوت تحت الصيانة حالياً.\n"
            "الرجاء المحاولة لاحقاً.\n\n"
            f"للتواصل: {SUPPORT_USERNAME}"
        )
        return
    
    # التحقق من رابط الدعوة
    invited_by = 0
    if context.args:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                invited_by = int(arg.split('_')[1])
            except:
                pass
    
    # التحقق إذا كان المستخدم جديداً
    existing_user = get_user(user_id)
    
    if not existing_user:
        # إنشاء مستخدم جديد
        if create_user(user_id, user.username, user.first_name, user.last_name, invited_by):
            welcome_bonus = int(get_setting("welcome_bonus", "1000"))
            
            welcome_msg = f"""
            🎉 أهلاً وسهلاً {user.first_name}!
            
            ✅ تم إضافتك بنجاح إلى بوت "يلا نتعلم"
            
            🎁 مكافأة الترحيب: {format_number(welcome_bonus)} دينار
            💰 رصيدك الحالي: {format_number(welcome_bonus)} دينار
            
            📚 خدمات البوت المتاحة:
            • 🧮 حساب درجة الإعفاء الفردي
            • 📄 تلخيص الملازم بالذكاء الاصطناعي
            • ❓ أسئلة وأجوبة أي مادة
            • 📚 ملازمي ومرشحاتي
            
            💸 جميع الخدمات مدفوعة (1000 دينار للخدمة)
            
            🔗 لدعوة الأصدقاء: /invite
            👑 للشحن والتواصل: {SUPPORT_USERNAME}
            """
        else:
            welcome_msg = "❌ حدث خطأ في إنشاء حسابك. يرجى المحاولة مرة أخرى."
    else:
        balance = existing_user[4]
        welcome_msg = f"""
        👋 أهلاً بعودتك {user.first_name}!
        
        💰 رصيدك الحالي: {format_number(balance)} دينار
        
        📚 اختر الخدمة التي تحتاجها:
        """
    
    await update.message.reply_text(
        format_arabic(welcome_msg),
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )

def get_main_keyboard():
    """لوحة المفاتيح الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("🧮 حساب الإعفاء", callback_data='service_exemption'),
            InlineKeyboardButton("📄 تلخيص PDF", callback_data='service_summarize')
        ],
        [
            InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data='service_qna'),
            InlineKeyboardButton("📚 الملازم", callback_data='service_materials')
        ],
        [
            InlineKeyboardButton("💰 رصيدي", callback_data='balance'),
            InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')
        ],
        [
            InlineKeyboardButton("👑 لوحة التحكم", callback_data='admin_panel')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار Inline Keyboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'balance':
        await show_balance(query, context)
    elif data == 'invite':
        await show_invite(query, context)
    elif data == 'admin_panel':
        await admin_panel(query, context)
    elif data.startswith('service_'):
        await handle_service(query, context, data.replace('service_', ''))
    elif data.startswith('mat_'):
        await send_material(query, context, data.replace('mat_', ''))
    elif data == 'main_menu':
        await query.edit_message_text(
            "🏠 القائمة الرئيسية",
            reply_markup=get_main_keyboard()
        )

async def handle_service(query, context, service_type: str):
    """معالجة اختيار خدمة"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ لم يتم العثور على حسابك")
        return
    
    # الحصول على سعر الخدمة
    price_key = f"{service_type}_price"
    price = int(get_setting(price_key, "1000"))
    
    # التحقق من الرصيد
    balance = user[4]
    
    if balance < price:
        await query.edit_message_text(
            format_arabic(f"""
            ⚠️ رصيدك غير كافي
            
            💰 سعر الخدمة: {format_number(price)} دينار
            💵 رصيدك الحالي: {format_number(balance)} دينار
            📉 الناقص: {format_number(price - balance)} دينار
            
            📞 لشحن الرصيد تواصل مع:
            {SUPPORT_USERNAME}
            
            أو ادعو أصدقاء للحصول على مكافآت
            """),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        return
    
    # خصم المبلغ
    service_names = {
        'exemption': 'حساب درجة الإعفاء',
        'summarize': 'تلخيص PDF',
        'qna': 'أسئلة وأجوبة',
        'materials': 'تحميل الملازم'
    }
    
    service_name = service_names.get(service_type, service_type)
    
    if update_balance(user_id, -price, "service_payment", f"دفع خدمة {service_name}"):
        log_service_usage(user_id, service_type, price, service_name)
        
        if service_type == 'exemption':
            await query.edit_message_text(
                format_arabic(f"""
                🧮 خدمة حساب درجة الإعفاء
                
                ✅ تم خصم {format_number(price)} دينار من رصيدك
                💰 رصيدك المتبقي: {format_number(balance - price)} دينار
                
                📝 أرسل درجات الكورسات الثلاثة (مثال: 85 90 95)
                سيتم حساب المعدل وتحديد إذا كنت معفياً
                """),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
                ])
            )
            context.user_data['awaiting_grades'] = True
            
        elif service_type == 'summarize':
            await query.edit_message_text(
                format_arabic(f"""
                📄 خدمة تلخيص PDF
                
                ✅ تم خصم {format_number(price)} دينار من رصيدك
                💰 رصيدك المتبقي: {format_number(balance - price)} دينار
                
                📤 أرسل ملف PDF الآن
                سيتم تلخيصه لك باستخدام الذكاء الاصطناعي
                """),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
                ])
            )
            context.user_data['awaiting_pdf'] = True
            
        elif service_type == 'qna':
            await query.edit_message_text(
                format_arabic(f"""
                ❓ خدمة الأسئلة والأجوبة
                
                ✅ تم خصم {format_number(price)} دينار من رصيدك
                💰 رصيدك المتبقي: {format_number(balance - price)} دينار
                
                💬 أرسل سؤالك الآن (نص أو صورة)
                سيتم الرد عليك باستخدام الذكاء الاصطناعي
                """),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
                ])
            )
            context.user_data['awaiting_question'] = True
            
        elif service_type == 'materials':
            await show_materials_list(query)
    else:
        await query.edit_message_text("❌ حدث خطأ في المعاملة")

async def process_grades_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة درجات الإعفاء"""
    if not context.user_data.get('awaiting_grades'):
        return
    
    grades_str = update.message.text
    grades, average, error = validate_grades(grades_str)
    
    if error:
        await update.message.reply_text(f"⚠️ {error}")
        return
    
    # حساب النتيجة
    if average >= 90:
        result = f"""
        🎉 مبروك! أنت معفي من المادة
        
        📊 الدرجات المدخلة:
        • الكورس الأول: {grades[0]}
        • الكورس الثاني: {grades[1]}
        • الكورس الثالث: {grades[2]}
        
        🧮 المعدل: {average:.2f}
        
        ✅ معدلك 90 أو أعلى، أنت معفي بنجاح!
        
        🎊 تهانينا على هذا الإنجاز!
        """
    else:
        result = f"""
        ⚠️ للأسف لست معفياً
        
        📊 الدرجات المدخلة:
        • الكورس الأول: {grades[0]}
        • الكورس الثاني: {grades[1]}
        • الكورس الثالث: {grades[2]}
        
        🧮 المعدل: {average:.2f}
        
        ❌ معدلك أقل من 90، تحتاج إلى تحسين.
        
        💡 نصيحة: ركز على المواد التي تحتاج تحسين
        """
    
    await update.message.reply_text(format_arabic(result))
    context.user_data.pop('awaiting_grades', None)

async def process_pdf_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملف PDF"""
    if not context.user_data.get('awaiting_pdf'):
        return
    
    if not update.message.document:
        await update.message.reply_text("⚠️ يرجى إرسال ملف PDF")
        return
    
    document = update.message.document
    
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("⚠️ الملف يجب أن يكون بصيغة PDF")
        return
    
    # إعلام المستخدم بالمعالجة
    processing_msg = await update.message.reply_text("🔄 جاري معالجة الملف وتلخيصه...")
    
    try:
        # هنا يمكن إضافة كود حقيقي لمعالجة PDF
        # للتبسيط، سنستخدم نموذجاً
        sample_summary = """
        📄 ملخص الملف
        
        هذا نموذج لملخص الملف. في النسخة الكاملة:
        1. سيتم استخراج النص من PDF
        2. استخدام الذكاء الاصطناعي للتلخيص
        3. إرسال الملخص المنظم
        
        ✅ تمت المعالجة بنجاح
        """
        
        await update.message.reply_text(format_arabic(sample_summary))
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في معالجة الملف")
    finally:
        await processing_msg.delete()
        context.user_data.pop('awaiting_pdf', None)

async def process_question_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأسئلة"""
    if not context.user_data.get('awaiting_question'):
        return
    
    question_text = ""
    
    if update.message.photo:
        # معالجة الصورة
        question_text = update.message.caption or "ما الموجود في هذه الصورة؟"
    elif update.message.text:
        question_text = update.message.text
    
    if not question_text:
        await update.message.reply_text("⚠️ يرجى إرسال سؤال")
        return
    
    processing_msg = await update.message.reply_text("🤔 جاري البحث عن الإجابة...")
    
    try:
        answer = await ask_ai(question_text)
        
        response = f"""
        🧠 الإجابة:
        
        {answer}
        
        📚 تمت الإجابة بناءً على المنهج العراقي
        """
        
        await update.message.reply_text(format_arabic(response))
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في معالجة سؤالك")
    finally:
        await processing_msg.delete()
        context.user_data.pop('awaiting_question', None)

async def show_balance(query, context):
    """عرض رصيد المستخدم"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ لم يتم العثور على حسابك")
        return
    
    balance = user[4]
    join_date = user[6]
    
    # الحصول على عدد المعاملات
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
    transactions_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND amount > 0", (user_id,))
    total_earned = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND amount < 0", (user_id,))
    total_spent = cursor.fetchone()[0] or 0
    conn.close()
    
    balance_msg = f"""
    💰 معلومات رصيدك
    
    👤 الاسم: {user[2] or 'غير معروف'}
    🆔 الأيدي: {user_id}
    📅 تاريخ الانضمام: {join_date[:10] if join_date else 'غير معروف'}
    
    ⚖️ الرصيد الحالي: {format_number(balance)} دينار
    📊 إجمالي الإيرادات: {format_number(total_earned)} دينار
    💸 إجمالي المصروفات: {format_number(abs(total_spent))} دينار
    📈 عدد المعاملات: {transactions_count}
    
    💸 أسعار الخدمات:
    • حساب الإعفاء: {format_number(int(get_setting('exemption_price', '1000')))} دينار
    • تلخيص PDF: {format_number(int(get_setting('summarize_price', '1000')))} دينار
    • أسئلة وأجوبة: {format_number(int(get_setting('qna_price', '1000')))} دينار
    • الملازم: {format_number(int(get_setting('materials_price', '1000')))} دينار
    
    📞 للشحن: {SUPPORT_USERNAME}
    """
    
    await query.edit_message_text(
        format_arabic(balance_msg),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 دعوة أصدقاء", callback_data='invite')],
            [InlineKeyboardButton("📊 سجل المعاملات", callback_data='transactions_log')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ])
    )

async def show_invite(query, context):
    """عرض معلومات الدعوة"""
    user_id = query.from_user.id
    
    # الحصول على إحصائيات الدعوة
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (user_id,))
    referrals_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'referral_bonus'", (user_id,))
    referrals_earned = cursor.fetchone()[0] or 0
    conn.close()
    
    referral_bonus = int(get_setting("referral_bonus", "500"))
    referral_link = create_referral_link(user_id)
    
    invite_msg = f"""
    🔗 نظام الدعوة والمكافآت
    
    📊 إحصائيات دعوتك:
    • عدد مدعويك: {referrals_count} شخص
    • مكافأة لكل دعوة: {format_number(referral_bonus)} دينار
    • إجمالي أرباحك: {format_number(referrals_earned)} دينار
    
    💰 كيف تعمل الدعوة:
    1. شارك رابط الدعوة مع أصدقائك
    2. عند انضمامهم للبوت عبر الرابط
    3. تحصل على {format_number(referral_bonus)} دينار تلقائياً
    4. يمكنهم بدورهم دعوة آخرين
    
    📎 رابط دعوتك الخاص:
    {referral_link}
    """
    
    await query.edit_message_text(
        format_arabic(invite_msg),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 مشاركة الرابط", 
             url=f"https://t.me/share/url?url={referral_link}&text=انضم%20للبوت%20التعليمي%20يلا%20نتعلم")],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
        ]),
        disable_web_page_preview=True
    )

# ==================== لوحة التحكم ====================
async def admin_panel(query, context):
    """لوحة تحكم المدير"""
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية الوصول")
        return
    
    # إحصائيات سريعة
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
    today_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM service_logs WHERE DATE(timestamp) = DATE('now')")
    today_services = cursor.fetchone()[0]
    
    conn.close()
    
    maintenance = get_setting("maintenance_mode", "0")
    
    admin_msg = f"""
    👑 لوحة تحكم المدير
    
    📊 الإحصائيات العامة:
    • إجمالي المستخدمين: {format_number(total_users)}
    • المستخدمين الجدد اليوم: {format_number(today_users)}
    • إجمالي الأرصدة: {format_number(total_balance)} دينار
    • الخدمات المستخدمة اليوم: {format_number(today_services)}
    • وضع الصيانة: {'✅ مفعل' if maintenance == '1' else '❌ غير مفعل'}
    
    ⚙️ اختر الإجراء:
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("💰 شحن رصيد", callback_data='admin_charge')],
        [InlineKeyboardButton("⚙️ تغيير الأسعار", callback_data='admin_prices')],
        [InlineKeyboardButton("📊 إحصائيات كاملة", callback_data='admin_stats')],
        [InlineKeyboardButton("📚 إدارة الملازم", callback_data='admin_materials')],
        [InlineKeyboardButton("🛠️ وضع الصيانة", callback_data='admin_maintenance')],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        format_arabic(admin_msg),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users_list(query, context):
    """قائمة المستخدمين للمدير"""
    if query.from_user.id != ADMIN_ID:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, balance, join_date 
        FROM users 
        ORDER BY join_date DESC 
        LIMIT 50
    ''')
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("📭 لا يوجد مستخدمين")
        return
    
    users_text = "👥 آخر 50 مستخدم:\n\n"
    for user in users:
        user_id, username, first_name, balance, join_date = user
        users_text += f"🆔 {user_id} | 👤 {first_name or 'N/A'} | 💰 {format_number(balance)} | 📅 {join_date[:10]}\n"
    
    # إرسال في رسالة منفصلة
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=users_text[:4000]
    )
    
    await query.edit_message_text(
        "✅ تم إرسال قائمة المستخدمين إليك في الخاص",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
        ])
    )

async def admin_charge_start(query, context):
    """بدء عملية شحن رصيد"""
    if query.from_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        "💰 شحن رصيد مستخدم\n\n"
        "أرسل أيدي المستخدم والمبلغ بهذا الشكل:\n"
        "<code>أيدي_المستخدم المبلغ</code>\n\n"
        "مثال: <code>123456789 5000</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]
        ])
    )
    
    return 'ADMIN_AWAITING_CHARGE'

async def admin_charge_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة شحن الرصيد"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ صيغة غير صحيحة. استخدم: أيدي المبلغ")
            return 'ADMIN_AWAITING_CHARGE'
        
        user_id = int(parts[0])
        amount = int(parts[1])
        
        user = get_user(user_id)
        if not user:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return 'ADMIN_AWAITING_CHARGE'
        
        if update_balance(user_id, amount, "admin_charge", f"شحن من المدير {ADMIN_ID}"):
            new_balance = user[4] + amount
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=format_arabic(f"""
                    💰 إشعار شحن رصيد
                    
                    ✅ تم شحن رصيدك بمبلغ: {format_number(amount)} دينار
                    
                    ⚖️ رصيدك السابق: {format_number(user[4])} دينار
                    ⚖️ رصيدك الجديد: {format_number(new_balance)} دينار
                    
                    📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    
                    📞 للاستفسار: {SUPPORT_USERNAME}
                    """)
                )
            except:
                pass
            
            await update.message.reply_text(
                f"✅ تم شحن {format_number(amount)} دينار للمستخدم {user_id}\n"
                f"💰 رصيده الجديد: {format_number(new_balance)} دينار"
            )
        else:
            await update.message.reply_text("❌ فشلت عملية الشحن")
        
        # العودة للوحة التحكم
        await admin_panel_simple(update, context)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إرسال أرقام صحيحة")
        return 'ADMIN_AWAITING_CHARGE'

async def admin_panel_simple(update, context):
    """لوحة تحكم مبسطة"""
    if update.callback_query:
        query = update.callback_query
        await admin_panel(query, context)
    else:
        # إرسال لوحة تحكم جديدة
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 لوحة التحكم", callback_data='admin_panel')]
        ])
        await update.message.reply_text("الرجاء استخدام الأزرار أدناه:", reply_markup=keyboard)

async def admin_change_prices(query, context):
    """تغيير أسعار الخدمات"""
    if query.from_user.id != ADMIN_ID:
        return
    
    prices_text = "💰 أسعار الخدمات الحالية:\n\n"
    
    services = [
        ('exemption_price', 'حساب الإعفاء'),
        ('summarize_price', 'تلخيص PDF'),
        ('qna_price', 'أسئلة وأجوبة'),
        ('materials_price', 'الملازم')
    ]
    
    for key, name in services:
        price = get_setting(key, "1000")
        prices_text += f"• {name}: {format_number(int(price))} دينار\n"
    
    keyboard = []
    for key, name in services:
        keyboard.append([InlineKeyboardButton(f"تغيير سعر {name}", callback_data=f'change_{key}')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])
    
    await query.edit_message_text(
        prices_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_change_price_start(query, context):
    """بدء تغيير سعر خدمة"""
    if query.from_user.id != ADMIN_ID:
        return
    
    price_key = query.data.replace('change_', '')
    
    service_names = {
        'exemption_price': 'حساب الإعفاء',
        'summarize_price': 'تلخيص PDF',
        'qna_price': 'أسئلة والأجوبة',
        'materials_price': 'الملازم'
    }
    
    service_name = service_names.get(price_key, price_key)
    current_price = get_setting(price_key, "1000")
    
    context.user_data['changing_price_key'] = price_key
    
    await query.edit_message_text(
        f"✏️ تغيير سعر {service_name}\n\n"
        f"السعر الحالي: {format_number(int(current_price))} دينار\n\n"
        f"أرسل السعر الجديد بالدينار:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_prices')]
        ])
    )
    
    return 'ADMIN_AWAITING_PRICE'

async def admin_save_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ السعر الجديد"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        new_price = int(update.message.text)
        
        if new_price < 100:
            await update.message.reply_text("⚠️ السعر يجب أن يكون 100 دينار على الأقل")
            return 'ADMIN_AWAITING_PRICE'
        
        price_key = context.user_data.get('changing_price_key')
        if not price_key:
            await update.message.reply_text("⚠️ لم يتم تحديد السعر المراد تغييره")
            return
        
        service_names = {
            'exemption_price': 'حساب الإعفاء',
            'summarize_price': 'تلخيص PDF',
            'qna_price': 'أسئلة والأجوبة',
            'materials_price': 'الملازم'
        }
        
        service_name = service_names.get(price_key, price_key)
        
        if update_setting(price_key, str(new_price)):
            # تحديث السعر في الذاكرة
            if price_key == 'exemption_price':
                SERVICE_PRICES['exemption'] = new_price
            elif price_key == 'summarize_price':
                SERVICE_PRICES['summarize'] = new_price
            elif price_key == 'qna_price':
                SERVICE_PRICES['qna'] = new_price
            elif price_key == 'materials_price':
                SERVICE_PRICES['materials'] = new_price
            
            await update.message.reply_text(
                f"✅ تم تغيير سعر {service_name} إلى {format_number(new_price)} دينار"
            )
        else:
            await update.message.reply_text("❌ فشل تغيير السعر")
        
        context.user_data.pop('changing_price_key', None)
        await admin_panel_simple(update, context)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح")
        return 'ADMIN_AWAITING_PRICE'

async def admin_toggle_maintenance(query, context):
    """تبديل وضع الصيانة"""
    if query.from_user.id != ADMIN_ID:
        return
    
    current = get_setting("maintenance_mode", "0")
    new_value = "0" if current == "1" else "1"
    
    if update_setting("maintenance_mode", new_value):
        status = "✅ تم تفعيل وضع الصيانة" if new_value == "1" else "❌ تم إلغاء وضع الصيانة"
        await query.edit_message_text(
            status,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع للوحة", callback_data='admin_panel')]
            ])
        )
    else:
        await query.edit_message_text("❌ فشل تغيير وضع الصيانة")

async def show_materials_list(query):
    """عرض قائمة الملازم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, description, grade, downloads 
        FROM materials 
        WHERE is_active = 1 
        ORDER BY downloads DESC, name ASC
        LIMIT 20
    ''')
    materials = cursor.fetchall()
    conn.close()
    
    if not materials:
        await query.edit_message_text(
            "📭 لا توجد ملازم متاحة حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]
            ])
        )
        return
    
    keyboard = []
    for mat_id, name, desc, grade, downloads in materials:
        button_text = f"{name[:20]}... ({grade}) 📥{downloads}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'mat_{mat_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')])
    
    await query.edit_message_text(
        "📚 الملازم والمرشحات المتاحة:\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_material(query, context, material_id: str):
    """إرسال ملزمة"""
    try:
        mat_id = int(material_id)
    except ValueError:
        await query.edit_message_text("❌ معرف الملزمة غير صحيح")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, description, file_id, file_type 
        FROM materials 
        WHERE id = ? AND is_active = 1
    ''', (mat_id,))
    material = cursor.fetchone()
    
    if material:
        name, description, file_id, file_type = material
        
        # زيادة عداد التنزيلات
        cursor.execute('''
            UPDATE materials 
            SET downloads = downloads + 1 
            WHERE id = ?
        ''', (mat_id,))
        conn.commit()
        
        if file_id:
            # إرسال الملف
            if file_type == 'photo':
                await query.message.reply_photo(
                    photo=file_id,
                    caption=f"📚 {name}\n\n{description or ''}\n✅ تم التحميل بنجاح"
                )
            else:
                await query.message.reply_document(
                    document=file_id,
                    caption=f"📚 {name}\n\n{description or ''}\n✅ تم التحميل بنجاح"
                )
        else:
            await query.message.reply_text(
                f"📚 {name}\n\n{description or ''}\n\n❌ الملف غير متوفر للتحميل حالياً"
            )
    else:
        await query.message.reply_text("❌ الملزمة غير متوفرة")
    
    conn.close()

# ==================== إعداد البوت ====================
def setup_bot_application():
    """إعداد تطبيق البوت"""
    print("🚀 بدء إعداد تطبيق البوت...")
    
    try:
        # إنشاء التطبيق
        application = Application.builder().token(TOKEN).build()
        print("✅ تم إنشاء تطبيق البوت")
        
        # إضافة معالجات الأوامر
        application.add_handler(CommandHandler("start", start_command))
        
        # إضافة معالجات الأزرار
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # إضافة معالجات الرسائل
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            process_grades_message
        ))
        
        application.add_handler(MessageHandler(
            filters.Document.PDF,
            process_pdf_message
        ))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            process_question_message
        ))
        
        application.add_handler(MessageHandler(
            filters.PHOTO,
            process_question_message
        ))
        
        # إضافة معالجات المحادثة للمدير
        admin_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(admin_charge_start, pattern='^admin_charge$'),
                CallbackQueryHandler(admin_change_price_start, pattern='^change_.*')
            ],
            states={
                'ADMIN_AWAITING_CHARGE': [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, admin_charge_process)
                ],
                'ADMIN_AWAITING_PRICE': [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_price)
                ]
            },
            fallbacks=[]
        )
        application.add_handler(admin_conv_handler)
        
        # إضافة معالجات أخرى للمدير
        application.add_handler(CallbackQueryHandler(admin_users_list, pattern='^admin_users$'))
        application.add_handler(CallbackQueryHandler(admin_change_prices, pattern='^admin_prices$'))
        application.add_handler(CallbackQueryHandler(admin_toggle_maintenance, pattern='^admin_maintenance$'))
        
        return application
        
    except Exception as e:
        print(f"❌ خطأ في إعداد البوت: {e}")
        return None

def run_flask_server():
    """تشغيل خادم Flask"""
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 تشغيل خادم Flask على المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_bot():
    """تشغيل البوت"""
    application = setup_bot_application()
    if not application:
        print("❌ فشل إعداد البوت")
        return
    
    print("🤖 بدء تشغيل البوت...")
    application.run_polling()

# ==================== التشغيل الرئيسي ====================
def main():
    """الدالة الرئيسية"""
    print("=" * 50)
    print("🚀 بدء تشغيل بوت 'يلا نتعلم'")
    print("=" * 50)
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # تشغيل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    print("✅ تم تشغيل خادم Flask")
    
    # تشغيل البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ تم تشغيل البوت")
    
    print("=" * 50)
    print(f"👑 المدير: {ADMIN_ID}")
    print(f"💬 الدعم: {SUPPORT_USERNAME}")
    print(f"🤖 البوت: @{BOT_USERNAME}")
    print("=" * 50)
    
    # إبقاء البرنامج شغالاً
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ إيقاف البوت...")
        sys.exit(0)

if __name__ == '__main__':
    main()
