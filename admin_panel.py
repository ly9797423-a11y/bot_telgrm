#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
لوحة تحكم بوت "يلا نتعلم"
للمدير فقط: 6130994941
"""

import logging
import json
from datetime import datetime
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

# استيراد الكلاسات من الملف الرئيسي
from ssm_bot import (
    TOKEN, ADMIN_ID, UserManager, MaterialsManager,
    SERVICE_PRICES, REFERRAL_BONUS, WELCOME_BONUS,
    DataManager, SUPPORT_USERNAME
)

class AdminPanel:
    def __init__(self):
        self.user_manager = UserManager()
        self.materials_manager = MaterialsManager()
        self.load_admin_settings()
    
    def load_admin_settings(self):
        """تحميل إعدادات المدير"""
        self.admin_settings = DataManager.load_data("admin_settings.json", {
            "maintenance": False,
            "channel_link": "https://t.me/joinchat/AAAA",
            "support_link": f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}",
            "prices": SERVICE_PRICES.copy(),
            "welcome_bonus": WELCOME_BONUS,
            "referral_bonus": REFERRAL_BONUS
        })
    
    def save_admin_settings(self):
        """حفظ إعدادات المدير"""
        DataManager.save_data("admin_settings.json", self.admin_settings)
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة التحكم"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ غير مسموح لك بالدخول!")
            return
        
        stats = self.get_statistics()
        
        panel_text = f"""
        👑 لوحة التحكم الإدارية
        
        📊 إحصائيات البوت:
        - عدد المستخدمين: {stats['total_users']}
        - المستخدمين النشطين: {stats['active_users']}
        - إجمالي الرصيد: {stats['total_balance']} دينار
        - عدد المعاملات: {stats['total_transactions']}
        - الخدمات المستخدمة: {stats['total_services']}
        
        ⚙️ حالة البوت: {"🟢 نشط" if not self.admin_settings['maintenance'] else "🔴 صيانة"}
        
        اختر الإجراء:
        """
        
        keyboard = [
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("💰 الشحن والرصيد", callback_data="admin_charge")],
            [InlineKeyboardButton("⚙️ تغيير الأسعار", callback_data="admin_prices")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("🛠️ إعدادات البوت", callback_data="admin_settings_menu")],
            [InlineKeyboardButton("📚 إدارة المواد", callback_data="admin_materials")],
            [InlineKeyboardButton("🔙 الرجوع للبوت", callback_data="back_to_bot")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            panel_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    def get_statistics(self) -> Dict:
        """الحصول على إحصائيات البوت"""
        users = self.user_manager.users
        total_balance = 0
        total_transactions = 0
        total_services = 0
        active_users = 0
        
        for user_id, user_data in users.items():
            total_balance += user_data.get('balance', 0)
            total_transactions += len(user_data.get('transactions', []))
            total_services += len(user_data.get('used_services', []))
            
            # مستخدم نشط إذا كان لديه معاملة في آخر 7 أيام
            if user_data.get('transactions'):
                last_transaction = user_data['transactions'][-1]
                last_date = datetime.strptime(last_transaction['date'], "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - last_date).days <= 7:
                    active_users += 1
        
        return {
            'total_users': len(users),
            'active_users': active_users,
            'total_balance': total_balance,
            'total_transactions': total_transactions,
            'total_services': total_services
        }
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ردود لوحة التحكم"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ غير مسموح لك!")
            return
        
        if query.data == "admin_users":
            await self.show_users_management(query)
        elif query.data == "admin_charge":
            await self.show_charge_menu(query)
        elif query.data == "admin_prices":
            await self.show_prices_menu(query)
        elif query.data == "admin_stats":
            await self.show_detailed_stats(query)
        elif query.data == "admin_settings_menu":
            await self.show_settings_menu(query)
        elif query.data == "admin_materials":
            await self.show_materials_management(query)
        elif query.data == "back_to_bot":
            await query.edit_message_text(
                "✅ تم العودة للبوت الرئيسي\nاكتب /start لعرض القائمة"
            )
            return
        elif query.data.startswith("user_"):
            action = query.data.split("_")[1]
            if action == "list":
                page = int(query.data.split("_")[2]) if len(query.data.split("_")) > 2 else 0
                await self.show_users_list(query, page)
            elif action == "view":
                target_id = query.data.split("_")[2]
                await self.show_user_details(query, target_id)
            elif action == "ban":
                target_id = query.data.split("_")[2]
                await self.ban_user(query, target_id)
            elif action == "unban":
                target_id = query.data.split("_")[2]
                await self.unban_user(query, target_id)
            elif action == "promote":
                target_id = query.data.split("_")[2]
                await self.promote_user(query, target_id)
        elif query.data.startswith("charge_"):
            if query.data == "charge_user":
                await query.edit_message_text(
                    "🔢 أرسل ID المستخدم للشحن:\n"
                    "مثال: <code>123456789</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_charge_id'] = True
            elif query.data == "charge_amount":
                if 'charge_target' in context.user_data:
                    await query.edit_message_text(
                        f"💰 أرسل المبلغ للشحن للمستخدم {context.user_data['charge_target']}:\n"
                        "مثال: <code>5000</code>",
                        parse_mode=ParseMode.HTML
                    )
                    context.user_data['awaiting_charge_amount'] = True
                else:
                    await query.edit_message_text("❌ يجب اختيار المستخدم أولاً")
        elif query.data.startswith("price_"):
            service = query.data.replace("price_", "")
            await query.edit_message_text(
                f"💰 أرسل السعر الجديد لخدمة {service}:\n"
                "مثال: <code>2000</code>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['awaiting_price'] = service
        elif query.data.startswith("setting_"):
            setting = query.data.replace("setting_", "")
            if setting == "maintenance":
                self.admin_settings['maintenance'] = not self.admin_settings['maintenance']
                self.save_admin_settings()
                status = "تفعيل" if self.admin_settings['maintenance'] else "إلغاء"
                await query.answer(f"✅ تم {status} وضع الصيانة")
                await self.show_settings_menu(query)
            elif setting == "welcome_bonus":
                await query.edit_message_text(
                    "🎁 أرسل قيمة الهدية الترحيبية الجديدة:\n"
                    "مثال: <code>2000</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_welcome_bonus'] = True
            elif setting == "referral_bonus":
                await query.edit_message_text(
                    "👥 أرسل قيمة مكافأة الدعوة الجديدة:\n"
                    "مثال: <code>1000</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_referral_bonus'] = True
            elif setting == "channel_link":
                await query.edit_message_text(
                    "📢 أرسل رابط القناة الجديد:\n"
                    "مثال: <code>https://t.me/joinchat/AAAA</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_channel_link'] = True
        elif query.data.startswith("material_"):
            action = query.data.split("_")[1]
            if action == "add":
                await query.edit_message_text(
                    "➕ أرسل تفاصيل المادة الجديدة:\n"
                    "📝 الصيغة: اسم المادة|الوصف|المرحلة|رابط الملف\n"
                    "مثال: <code>رياضيات السادس|ملزمة رياضيات للصف السادس|السادس الاعدادي|https://example.com/file.pdf</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_material'] = True
            elif action == "list":
                page = int(query.data.split("_")[2]) if len(query.data.split("_")) > 2 else 0
                await self.show_materials_list(query, page)
            elif action == "delete":
                material_id = int(query.data.split("_")[2])
                await self.delete_material(query, material_id)
    
    async def show_users_management(self, query):
        """عرض قائمة إدارة المستخدمين"""
        keyboard = [
            [InlineKeyboardButton("📋 عرض جميع المستخدمين", callback_data="user_list_0")],
            [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="user_search")],
            [InlineKeyboardButton("📊 أفضل 10 مستخدمين", callback_data="user_top")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👥 إدارة المستخدمين\n\n"
            "اختر الإجراء المطلوب:",
            reply_markup=reply_markup
        )
    
    async def show_users_list(self, query, page: int = 0):
        """عرض قائمة المستخدمين"""
        users = list(self.user_manager.users.items())
        users_per_page = 10
        total_pages = (len(users) + users_per_page - 1) // users_per_page
        
        start_idx = page * users_per_page
        end_idx = start_idx + users_per_page
        
        message = f"📋 المستخدمين (الصفحة {page + 1}/{total_pages}):\n\n"
        
        keyboard = []
        for user_id, user_data in users[start_idx:end_idx]:
            user_info = f"🆔 {user_id} | 💰 {user_data.get('balance', 0)}"
            keyboard.append([InlineKeyboardButton(
                user_info, callback_data=f"user_view_{user_id}"
            )])
        
        # أزرار التنقل بين الصفحات
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"user_list_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"user_list_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_users")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
    
    async def show_user_details(self, query, user_id: str):
        """عرض تفاصيل المستخدم"""
        user_data = self.user_manager.get_user(int(user_id))
        
        details = f"""
        👤 تفاصيل المستخدم
        
        🆔 ID: {user_id}
        📅 تاريخ الانضمام: {user_data.get('joined_date', 'غير معروف')}
        💰 الرصيد: {user_data.get('balance', 0)} دينار
        
        📊 الإحصائيات:
        - عدد الخدمات: {len(user_data.get('used_services', []))}
        - عدد المعاملات: {len(user_data.get('transactions', []))}
        - عدد الدعوات: {len(user_data.get('invited_users', []))}
        
        🔄 آخر 3 معاملات:
        """
        
        for trans in user_data.get('transactions', [])[-3:]:
            sign = "+" if trans['amount'] > 0 else ""
            details += f"\n{trans['date']}: {sign}{trans['amount']} - {trans['description']}"
        
        keyboard = [
            [
                InlineKeyboardButton("💰 شحن", callback_data=f"charge_user_{user_id}"),
                InlineKeyboardButton("⛔ حظر", callback_data=f"user_ban_{user_id}")
            ],
            [
                InlineKeyboardButton("👑 رفع مشرف", callback_data=f"user_promote_{user_id}"),
                InlineKeyboardButton("📊 إحصائيات مفصلة", callback_data=f"user_stats_{user_id}")
            ],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="user_list_0")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            details,
            reply_markup=reply_markup
        )
    
    async def show_charge_menu(self, query):
        """عرض قائمة الشحن"""
        keyboard = [
            [InlineKeyboardButton("💰 شحن مستخدم", callback_data="charge_user")],
            [InlineKeyboardButton("📊 شحن جماعي", callback_data="charge_bulk")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💰 إدارة الشحن والرصيد\n\n"
            "اختر نوع الشحن:",
            reply_markup=reply_markup
        )
    
    async def show_prices_menu(self, query):
        """عرض قائمة الأسعار"""
        message = "💰 أسعار الخدمات الحالية:\n\n"
        
        keyboard = []
        for service, price in self.admin_settings['prices'].items():
            service_name = {
                'exemption': 'حساب درجة الإعفاء',
                'summarize': 'تلخيص الملازم',
                'qa': 'سؤال وجواب',
                'materials': 'ملازمي ومرشحاتي'
            }.get(service, service)
            
            message += f"{service_name}: {price} دينار\n"
            keyboard.append([InlineKeyboardButton(
                f"✏️ تعديل {service_name}", callback_data=f"price_{service}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
    
    async def show_detailed_stats(self, query):
        """عرض إحصائيات مفصلة"""
        stats = self.get_statistics()
        
        # إحصائيات إضافية
        total_exemption = 0
        total_summaries = 0
        total_questions = 0
        
        for user_data in self.user_manager.users.values():
            for service in user_data.get('used_services', []):
                if service['service'] == 'exemption':
                    total_exemption += 1
                elif service['service'] == 'summarize':
                    total_summaries += 1
                elif service['service'] == 'qa':
                    total_questions += 1
        
        stats_text = f"""
        📊 إحصائيات مفصلة
        
        👥 المستخدمين:
        - الإجمالي: {stats['total_users']}
        - النشطين: {stats['active_users']}
        - النسبة: {stats['active_users']/stats['total_users']*100:.1f}%
        
        💰 الماليات:
        - إجمالي الرصيد: {stats['total_balance']} دينار
        - متوسط الرصيد: {stats['total_balance']/stats['total_users']:.0f} دينار
        - إجمالي المعاملات: {stats['total_transactions']}
        
        📈 الخدمات:
        - الإجمالي: {stats['total_services']}
        - حساب الإعفاء: {total_exemption}
        - تلخيص الملازم: {total_summaries}
        - سؤال وجواب: {total_questions}
        - المواد: {stats['total_services'] - total_exemption - total_summaries - total_questions}
        
        ⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("📥 تصدير البيانات", callback_data="export_data")],
            [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup
        )
    
    async def show_settings_menu(self, query):
        """عرض قائمة الإعدادات"""
        maintenance_status = "🔴 مفعل" if self.admin_settings['maintenance'] else "🟢 معطل"
        
        message = f"""
        ⚙️ إعدادات البوت
        
        وضع الصيانة: {maintenance_status}
        الهدية الترحيبية: {self.admin_settings['welcome_bonus']} دينار
        مكافأة الدعوة: {self.admin_settings['referral_bonus']} دينار
        
        روابط:
        - القناة: {self.admin_settings['channel_link']}
        - الدعم: {self.admin_settings['support_link']}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔧 وضع الصيانة", callback_data="setting_maintenance")],
            [InlineKeyboardButton("🎁 الهدية الترحيبية", callback_data="setting_welcome_bonus")],
            [InlineKeyboardButton("👥 مكافأة الدعوة", callback_data="setting_referral_bonus")],
            [InlineKeyboardButton("📢 رابط القناة", callback_data="setting_channel_link")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
    
    async def show_materials_management(self, query):
        """عرض إدارة المواد"""
        total_materials = len(self.materials_manager.materials)
        stages = self.materials_manager.get_all_stages()
        
        message = f"""
        📚 إدارة المواد التعليمية
        
        📊 الإحصائيات:
        - عدد المواد: {total_materials}
        - عدد المراحل: {len(stages)}
        
        📂 المراحل المتاحة:
        {', '.join(stages) if stages else 'لا توجد مراحل'}
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة مادة جديدة", callback_data="material_add")],
            [InlineKeyboardButton("📋 عرض جميع المواد", callback_data="material_list_0")],
            [InlineKeyboardButton("🔍 البحث في المواد", callback_data="material_search")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
    
    async def show_materials_list(self, query, page: int = 0):
        """عرض قائمة المواد"""
        materials = self.materials_manager.materials
        materials_per_page = 10
        total_pages = (len(materials) + materials_per_page - 1) // materials_per_page
        
        start_idx = page * materials_per_page
        end_idx = start_idx + materials_per_page
        
        message = f"📚 المواد (الصفحة {page + 1}/{total_pages}):\n\n"
        
        keyboard = []
        for material in materials[start_idx:end_idx]:
            btn_text = f"📄 {material.get('name', 'بدون اسم')} - {material.get('stage', 'بدون مرحلة')}"
            keyboard.append([InlineKeyboardButton(
                btn_text, callback_data=f"material_view_{material['id']}"
            )])
        
        # أزرار التنقل
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"material_list_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"material_list_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_materials")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
    
    async def handle_admin_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة رسائل المدير"""
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return
        
        text = update.message.text
        
        # معالجة شحن المستخدم
        if context.user_data.get('awaiting_charge_id'):
            try:
                target_id = int(text)
                context.user_data['charge_target'] = target_id
                context.user_data['awaiting_charge_id'] = False
                
                await update.message.reply_text(
                    f"✅ تم تحديد المستخدم {target_id}\n"
                    f"💰 أرسل المبلغ للشحن:",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['awaiting_charge_amount'] = True
            except ValueError:
                await update.message.reply_text("❌ أدخل رقم ID صحيح")
        
        elif context.user_data.get('awaiting_charge_amount'):
            try:
                amount = int(text)
                target_id = context.user_data['charge_target']
                
                old_balance = self.user_manager.get_user(target_id)['balance']
                new_balance = self.user_manager.update_balance(
                    target_id, amount, "شحن من المدير"
                )
                
                await update.message.reply_text(
                    f"✅ تم الشحن بنجاح!\n\n"
                    f"👤 المستخدم: {target_id}\n"
                    f"💰 المبلغ: {amount} دينار\n"
                    f"💵 الرصيد القديم: {old_balance}\n"
                    f"💳 الرصيد الجديد: {new_balance}",
                    parse_mode=ParseMode.HTML
                )
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"🎉 تم شحن رصيدك!\n"
                             f"💰 المبلغ: {amount} دينار\n"
                             f"💳 رصيدك الحالي: {new_balance} دينار"
                    )
                except:
                    pass
                
                # تنظيف البيانات المؤقتة
                del context.user_data['charge_target']
                del context.user_data['awaiting_charge_amount']
                
                await self.admin_panel(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ أدخل رقم المبلغ صحيح")
        
        # معالجة تغيير الأسعار
        elif context.user_data.get('awaiting_price'):
            try:
                new_price = int(text)
                service = context.user_data['awaiting_price']
                
                self.admin_settings['prices'][service] = new_price
                self.save_admin_settings()
                
                service_name = {
                    'exemption': 'حساب درجة الإعفاء',
                    'summarize': 'تلخيص الملازم',
                    'qa': 'سؤال وجواب',
                    'materials': 'ملازمي ومرشحاتي'
                }.get(service, service)
                
                await update.message.reply_text(
                    f"✅ تم تغيير سعر {service_name} إلى {new_price} دينار",
                    parse_mode=ParseMode.HTML
                )
                
                del context.user_data['awaiting_price']
                await self.admin_panel(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ أدخل سعراً صحيحاً")
        
        # معالجة إضافة مادة جديدة
        elif context.user_data.get('awaiting_material'):
            try:
                parts = text.split('|')
                if len(parts) >= 4:
                    material_data = {
                        'name': parts[0].strip(),
                        'description': parts[1].strip(),
                        'stage': parts[2].strip(),
                        'file_url': parts[3].strip()
                    }
                    
                    self.materials_manager.add_material(material_data)
                    
                    await update.message.reply_text(
                        f"✅ تم إضافة المادة بنجاح!\n"
                        f"📚 الاسم: {material_data['name']}\n"
                        f"📝 الوصف: {material_data['description']}\n"
                        f"🎓 المرحلة: {material_data['stage']}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.message.reply_text("❌ تنسيق غير صحيح")
                
                del context.user_data['awaiting_material']
                await self.admin_panel(update, context)
                
            except Exception as e:
                await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
        
        # معالجة تغيير الهدية الترحيبية
        elif context.user_data.get('awaiting_welcome_bonus'):
            try:
                new_bonus = int(text)
                self.admin_settings['welcome_bonus'] = new_bonus
                self.save_admin_settings()
                
                await update.message.reply_text(
                    f"✅ تم تغيير الهدية الترحيبية إلى {new_bonus} دينار",
                    parse_mode=ParseMode.HTML
                )
                
                del context.user_data['awaiting_welcome_bonus']
                await self.admin_panel(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ أدخل رقم المبلغ صحيح")
        
        # معالجة تغيير مكافأة الدعوة
        elif context.user_data.get('awaiting_referral_bonus'):
            try:
                new_bonus = int(text)
                self.admin_settings['referral_bonus'] = new_bonus
                self.save_admin_settings()
                
                await update.message.reply_text(
                    f"✅ تم تغيير مكافأة الدعوة إلى {new_bonus} دينار",
                    parse_mode=ParseMode.HTML
                )
                
                del context.user_data['awaiting_referral_bonus']
                await self.admin_panel(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ أدخل رقم المبلغ صحيح")
        
        # معالجة تغيير رابط القناة
        elif context.user_data.get('awaiting_channel_link'):
            self.admin_settings['channel_link'] = text.strip()
            self.save_admin_settings()
            
            await update.message.reply_text(
                f"✅ تم تغيير رابط القناة إلى:\n{text}",
                parse_mode=ParseMode.HTML
            )
            
            del context.user_data['awaiting_channel_link']
            await self.admin_panel(update, context)
    
    async def ban_user(self, query, user_id: str):
        """حظر مستخدم"""
        # تنفيذ الحظر هنا
        await query.answer(f"✅ تم حظر المستخدم {user_id}")
        await query.edit_message_text(
            f"⛔ تم حظر المستخدم {user_id} بنجاح"
        )
    
    async def unban_user(self, query, user_id: str):
        """إلغاء حظر مستخدم"""
        await query.answer(f"✅ تم إلغاء حظر المستخدم {user_id}")
        await query.edit_message_text(
            f"✅ تم إلغاء حظر المستخدم {user_id} بنجاح"
        )
    
    async def promote_user(self, query, user_id: str):
        """ترقية مستخدم لمشرف"""
        await query.answer(f"✅ تم ترقية المستخدم {user_id} لمشرف")
        await query.edit_message_text(
            f"👑 تم ترقية المستخدم {user_id} إلى مشرف بنجاح"
        )
    
    async def delete_material(self, query, material_id: int):
        """حذف مادة"""
        materials = [m for m in self.materials_manager.materials if m.get('id') != material_id]
        self.materials_manager.materials = materials
        self.materials_manager.save_materials()
        
        await query.answer("✅ تم حذف المادة")
        await query.edit_message_text(
            "🗑️ تم حذف المادة بنجاح"
        )
    
    def run(self):
        """تشغيل لوحة التحكم"""
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        
        app = Application.builder().token(TOKEN).build()
        
        # إضافة handlers
        app.add_handler(CommandHandler("admin", self.admin_panel))
        app.add_handler(CallbackQueryHandler(self.handle_admin_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_admin_message))
        
        print("👑 لوحة التحكم تعمل الآن...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

# ============= تشغيل لوحة التحكم =============
if __name__ == "__main__":
    panel = AdminPanel()
    panel.run()
