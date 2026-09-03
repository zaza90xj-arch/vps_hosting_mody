import requests
import json
import os
import random
import string
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================
# الإعدادات الأساسية
# ============================================

API_BASE_URL = "https://avi-vps-hosting.onrender.com"
BOT_TOKEN = "8739282232:AAE65zI-xVwmWYbij-ADEylj2DgA90k4a84"
ADMIN_IDS = [8707728504, 8707728504]
DB_FILE = "bot_database.json"
BOT_USERNAME = "𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1"

# تم إزالة FORCE_CHANNELS بالكامل

USERS_PER_PAGE = 10

# ============================================
# دالة مساعدة لتأمين النصوص في HTML
# ============================================

def h(text):
    """تأمين النص من أكواد HTML ضارة"""
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ============================================
# قاعدة البيانات (ملف JSON)
# ============================================

def load_db():
    if not os.path.exists(DB_FILE):
        default = {
            "users": {},
            "redeem_codes": {},
            "total_panels": 0,
            "banned_users": [],
            "maintenance": False
            # تم حذف force_channels
        }
        save_db(default)
        return default
    with open(DB_FILE, 'r') as f:
        db = json.load(f)

    # تحديث تلقائي للإصدارات القديمة (إزالة أي أثر للقنوات)
    changed = False
    if 'banned_users' not in db:
        db['banned_users'] = []
        changed = True
    if 'maintenance' not in db:
        db['maintenance'] = False
        changed = True
    if 'force_channels' in db:
        del db['force_channels']
        changed = True
    if changed:
        save_db(db)

    return db

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user(user_id, first_name=None):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db['users']:
        db['users'][user_id] = {
            'first_name': first_name,
            'username_tg': None,
            'referral_code': generate_referral_code(),
            'referral_count': 0,
            'total_referrals': 0,
            'panels': [],
            'redeem_used': False,
            'referred_by': None,
            'created_at': str(datetime.now())
        }
        save_db(db)
    elif first_name:
        db['users'][user_id]['first_name'] = first_name
        save_db(db)
    return db['users'][user_id]

def update_user(user_id, data):
    db = load_db()
    db['users'][str(user_id)] = data
    save_db(db)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_redeem_code():
    chars = string.ascii_uppercase + string.digits
    return f"AVI_CODEX_{''.join(random.choices(chars, k=2))}-{''.join(random.choices(chars, k=2))}-{''.join(random.choices(chars, k=2))}"

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_banned(user_id):
    db = load_db()
    return str(user_id) in db.get('banned_users', [])

def is_maintenance_on():
    db = load_db()
    return db.get('maintenance', False)

# ============================================
# تم حذف دوال الاشتراك الإجباري
# ============================================

# ============================================
# الاتصال بـ API الخارجي
# ============================================

def create_panel_api(username=None):
    try:
        params = {}
        if username:
            params['username'] = username
        resp = requests.get(f"{API_BASE_URL}/api/create", params=params, timeout=20)
        return resp.json()
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# ============================================
# لوحات المفاتيح (القوائم)
# ============================================

def get_user_menu():
    keyboard = [
        [KeyboardButton("🆕 إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺")],
        [KeyboardButton("📊 لوحاتي"), KeyboardButton("🔗 الإحالات")],
        [KeyboardButton("🎁 كود استرداد"), KeyboardButton("💳 شراء لوحة")],
        [KeyboardButton("📞 الدعم"), KeyboardButton("👤 ملفي")],
        [KeyboardButton("𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1")]   # زر المطور (غير قابل للضغط، يمكن تحويله لنص)
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_main_menu():
    """قائمة المستخدم العادي مع إضافة زر مدير إضافي للمشرفين."""
    keyboard = [
        [KeyboardButton("🆕 إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺")],
        [KeyboardButton("📊 لوحاتي"), KeyboardButton("🔗 الإحالات")],
        [KeyboardButton("🎁 كود استرداد"), KeyboardButton("💳 شراء لوحة")],
        [KeyboardButton("📞 الدعم"), KeyboardButton("👤 ملفي")],
        [KeyboardButton("👑 لوحة المدير")],
        [KeyboardButton("𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_panel_menu():
    """قائمة المدير المنفصلة (تم إزالة خيارات القنوات)."""
    keyboard = [
        [KeyboardButton("📢 بث رسالة")],
        [KeyboardButton("🛠️ تشغيل/إيقاف الصيانة")],
        [KeyboardButton("🚫 حظر / إلغاء حظر مستخدم")],
        [KeyboardButton("👥 كل المستخدمين")],
        [KeyboardButton("🎫 توليد أكواد"), KeyboardButton("📋 كل اللوحات")],
        [KeyboardButton("🔗 إضافة إحالة يدوياً"), KeyboardButton("📊 الإحصائيات")],
        [KeyboardButton("⬅️ رجوع للقائمة الرئيسية")],
        [KeyboardButton("𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================
# تنسيق عرض اللوحة (مع اسم 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺)
# ============================================

def format_panel(data):
    return (
        "<b>╔══════════════════════╗\n  ✅ تم إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 بنجاح!\n╚══════════════════════╝</b>\n\n"
        f"🌐 <b>الرابط:</b> {h(data['full_url'])}\n"
        f"👤 <b>اسم المستخدم:</b> <code>{h(data['username'])}</code>\n"
        f"🔑 <b>كلمة المرور:</b> <code>{h(data['password'])}</code>\n"
        f"🆔 <b>معرف السيرفر:</b> <code>{h(data['server_id'].upper())}</code>\n"
        f"🖥️ <b>النوع:</b> Python\n"
        f"💾 <b>الذاكرة:</b> {h(data['ram'])} | 💿 <b>المساحة:</b> {h(data['disk'])}\n"
        f"⏰ <b>مدة الصلاحية:</b> {h(data['validity'])}\n"
        f"📅 <b>تاريخ الانتهاء:</b> {h(data['expiry_date'])}\n\n"
        "🔐 قم بتسجيل الدخول باستخدام البيانات أعلاه!"
    )

def build_all_users_page(db, page=0, per_page=USERS_PER_PAGE):
    """عرض جميع المستخدمين مع ترقيم الصفحات لدعم أكثر من 1000 مستخدم."""
    users_list = list(db['users'].items())
    total = len(users_list)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * per_page
    end_idx = start_idx + per_page
    chunk = users_list[start_idx:end_idx]

    msg = f"👥 <b>جميع المستخدمين</b> (إجمالي {total})\n📄 الصفحة {page + 1}/{total_pages}\n\n"
    if not chunk:
        msg += "لا يوجد مستخدمون بعد."
    for i, (uid, u_data) in enumerate(chunk, start_idx + 1):
        name = h(u_data.get('first_name') or 'غير معروف')
        username_tg = u_data.get('username_tg')
        username_str = f"@{h(username_tg)}" if username_tg else "غير موجود"
        msg += (
            f"<b>{i}.</b> {name}\n"
            f"   👤 المعرف: {username_str}\n"
            f"   🆔 الرقم التعريفي: <code>{uid}</code>\n\n"
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"users_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ التالي", callback_data=f"users_page_{page + 1}"))
    markup = InlineKeyboardMarkup([nav_buttons]) if nav_buttons else None
    return msg, markup

async def do_broadcast(context: ContextTypes.DEFAULT_TYPE, from_chat_id, message_id):
    """بث رسالة (نص / صورة / فيديو / مستند) لجميع المستخدمين المسجلين."""
    db = load_db()
    user_ids = list(db['users'].keys())
    total = len(user_ids)
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=int(uid), from_chat_id=from_chat_id, message_id=message_id)
            sent += 1
        except Exception:
            failed += 1
    return sent, failed, total

# ============================================
# معالجات الأوامر والرسائل
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    admin = is_admin(user_id)

    if not admin and is_banned(user_id):
        await update.message.reply_text("🚫 <b>لقد تم حظرك من استخدام هذا البوت.</b>", parse_mode=ParseMode.HTML)
        return

    if not admin and is_maintenance_on():
        await update.message.reply_text("🛠️ <b>البوت في وضع الصيانة. يرجى المحاولة لاحقاً.</b>", parse_mode=ParseMode.HTML)
        return
    
    first_name = user.first_name or "مستخدم"
    username_tg = user.username
    
    args = context.args
    referred_by = None
    
    if args:
        referral_code = args[0]
        db = load_db()
        
        existing_user = db['users'].get(str(user_id), {})
        already_referred = existing_user.get('referred_by') is not None
        
        if not already_referred:
            for uid, u_data in db['users'].items():
                if u_data.get('referral_code') == referral_code:
                    if str(user_id) != uid:
                        referred_by = uid
                        u_data['referral_count'] = u_data.get('referral_count', 0) + 1
                        u_data['total_referrals'] = u_data.get('total_referrals', 0) + 1
                        save_db(db)
                        
                        try:
                            can_claim = "🎁 يمكنك الحصول على لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 مجانية!" if u_data['referral_count'] >= 4 else f"📌 تحتاج {4 - u_data['referral_count']} إحالة أخرى"
                            await context.bot.send_message(
                                chat_id=int(uid),
                                text=f"🔗 <b>إحالة جديدة!</b>\n👤 <b>المستخدم:</b> {h(first_name)}\n📊 <b>متاح لديك:</b> {u_data['referral_count']}/4\n\n{can_claim}",
                                parse_mode=ParseMode.HTML
                            )
                        except: pass
                    break
    
    db_user = get_user(user_id, first_name)
    db_user['username_tg'] = username_tg
    if referred_by and not db_user.get('referred_by'):
        db_user['referred_by'] = referred_by
    update_user(user_id, db_user)
    
    ref_code = db_user.get('referral_code', 'N/A')
    ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
    
    if admin:
        msg = f"👑 أهلاً بك أيها المدير {h(first_name)}!\n\n𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 - بوابتك للاستضافة السحابية\n𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1"
        menu = get_admin_main_menu()
    else:
        msg = f"🚀 <b>أهلاً بك {h(first_name)} في 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺!</b>\n\n🎁 4 إحالات = لوحة مجانية!\n🔗 رابط الإحالة الخاص بك: {ref_link}\n\n𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1"
        menu = get_user_menu()
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=menu)

# تم حذف check_sub_callback لأنه لم يعد مستخدماً

async def users_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return

    try:
        page = int(query.data.replace("users_page_", ""))
    except ValueError:
        page = 0

    db = load_db()
    msg, markup = build_all_users_page(db, page)
    try:
        await query.message.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=markup)
    except Exception:
        pass
    await query.answer()

async def maintenance_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return

    db = load_db()
    db['maintenance'] = query.data == "maint_on"
    save_db(db)
    status = "🔴 تشغيل" if db['maintenance'] else "🟢 إيقاف"
    await query.message.edit_text(f"🛠️ <b>حالة الصيانة الآن:</b> {status}", parse_mode=ParseMode.HTML)
    await query.answer("✅ تم التحديث!")

async def handle_broadcast_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال محتوى البث (صورة / فيديو / مستند) من المدير بعد الضغط على زر البث."""
    user = update.effective_user
    if not user or not is_admin(user.id) or not context.user_data.get('awaiting_broadcast'):
        return

    context.user_data['awaiting_broadcast'] = False
    status_msg = await update.message.reply_text("📢 جاري البث... يرجى الانتظار")
    sent, failed, total = await do_broadcast(context, update.effective_chat.id, update.message.message_id)
    await status_msg.edit_text(
        f"📢 <b>اكتمل البث!</b>\n\n✅ تم الإرسال: {sent}\n❌ فشل: {failed}\n👥 الإجمالي: {total}",
        parse_mode=ParseMode.HTML
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    
    admin = is_admin(user_id)

    if not admin and is_banned(user_id):
        await update.message.reply_text("🚫 <b>لقد تم حظرك من استخدام هذا البوت.</b>", parse_mode=ParseMode.HTML)
        return

    if not admin and is_maintenance_on():
        await update.message.reply_text("🛠️ <b>البوت في وضع الصيانة. يرجى المحاولة لاحقاً.</b>", parse_mode=ParseMode.HTML)
        return
    
    # تجاهل الضغط على زر المطور (مجرد نص)
    if text == "𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1":
        return

    if text == "👤 ملفي":
        db_user = get_user(user_id)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={db_user.get('referral_code', 'N/A')}"
        
        msg = (
            f"👤 <b>ملفك الشخصي</b>\n"
            f"├─ المعرف: <code>{user_id}</code>\n"
            f"├─ الاسم: {h(user.first_name or 'غير معروف')}\n"
            f"├─ الإحالات المتاحة: {db_user.get('referral_count', 0)}/4\n"
            f"├─ إجمالي الإحالات: {db_user.get('total_referrals', 0)}\n"
            f"├─ عدد اللوحات: {len(db_user.get('panels', []))}\n"
            f"└─ رابط الإحالة: {ref_link}\n\n𝑫𝒆𝒗: 𝑴𝑶𝑫𝒀𝑿𝑩𝑶𝑻1"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    elif text == "🆕 إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺":
        db_user = get_user(user_id)
        ref_count = db_user.get('referral_count', 0)
        
        if not admin and ref_count < 4 and not db_user.get('redeem_used', False):
            remaining = 4 - ref_count
            await update.message.reply_text(
                f"⚠️ <b>تحتاج 4 إحالات أو كود استرداد!</b>\n\n📊 المتاح: {ref_count}/4\n📌 المتبقي: {remaining}\n\n💡 شارك رابط الإحالة الخاص بك!\n🎁 أو استخدم كود الاسترداد",
                parse_mode=ParseMode.HTML
            )
            return
        
        msg = await update.message.reply_text("🔄 جاري إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺...")
        result = create_panel_api(username=None)
        
        if result.get('status') == 'success':
            panel_data = {
                'server_id': result['server_id'], 'full_url': result['full_url'],
                'username': result['username'], 'password': result['password'],
                'created_at': str(datetime.now()), 'expiry': result['expiry_date']
            }
            
            if 'panels' not in db_user: db_user['panels'] = []
            if not any(p.get('server_id') == panel_data['server_id'] for p in db_user['panels']):
                db_user['panels'].append(panel_data)
            
            if not admin:
                if ref_count >= 4: db_user['referral_count'] = ref_count - 4
                db_user['redeem_used'] = False
            
            update_user(user_id, db_user)
            db = load_db()
            db['total_panels'] = db.get('total_panels', 0) + 1
            save_db(db)
            
            await msg.edit_text(format_panel(result), parse_mode=ParseMode.HTML)
            
            for aid in ADMIN_IDS:
                try:
                    await context.bot.send_message(aid, f"🆕 <b>لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 جديدة!</b>\n👤 <code>{user_id}</code>\n🆔 <code>{h(result['server_id'])}</code>", parse_mode=ParseMode.HTML)
                except: pass
        else:
            await msg.edit_text(f"❌ {h(result.get('message', 'فشل الإنشاء!'))}", parse_mode=ParseMode.HTML)
    
    elif text == "📊 لوحاتي":
        db_user = get_user(user_id)
        panels = db_user.get('panels', [])
        if not panels:
            await update.message.reply_text("📊 لا توجد لوحات 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺!")
            return
        msg = "📊 <b>لوحات 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 الخاصة بك</b>\n\n"
        for i, p in enumerate(panels, 1):
            msg += f"<b>{i}.</b> 🆔 <code>{h(p['server_id'][:8].upper())}</code>\n   👤 <code>{h(p['username'])}</code> | 🔑 <code>{h(p['password'])}</code>\n   📅 {h(p.get('expiry', 'غير محدد'))}\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "🔗 الإحالات":
        db_user = get_user(user_id)
        ref_code = db_user.get('referral_code', 'N/A')
        ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
        msg = f"🔗 <b>الإحالات الخاصة بك</b>\n\n🎁 <b>4 إحالات = لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 مجانية</b>\n\n📊 المتاح: {db_user.get('referral_count', 0)}/4\n📈 الإجمالي: {db_user.get('total_referrals', 0)}\n\n🔗 <b>الرابط:</b> {ref_link}\n📋 <b>الكود:</b> <code>{ref_code}</code>\n\n⚠️ الإحالة الذاتية أو المكررة غير مسموح بها!"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "🎁 كود استرداد":
        await update.message.reply_text("🎁 أرسل كود الاسترداد:")
        context.user_data['awaiting_redeem'] = True
    
    elif text in ["💳 شراء لوحة", "📞 الدعم"]:
        keyboard = [[InlineKeyboardButton("💬 تواصل مع المدير", url="https://t.me/AVI_CODEX")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if text == "💳 شراء لوحة":
            msg = "💳 <b>شراء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺</b>\n\n├─ 3 أيام: 50 جنيه\n├─ 7 أيام: 100 جنيه\n└─ 30 يوماً: 300 جنيه\n\n📞 اضغط أدناه للتواصل:"
        else:
            msg = "📞 <b>الدعم</b>\n\nاضغط أدناه للتواصل مع المدير!"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    elif text == "🎫 توليد أكواد" and admin:
        codes, db = [], load_db()
        for _ in range(15):
            code = generate_redeem_code()
            db['redeem_codes'][code] = {'used': False, 'used_by': None, 'created_at': str(datetime.now())}
            codes.append(code)
        save_db(db)
        await update.message.reply_text("🎫 <b>15 كود!</b>\n\n" + '\n'.join(f"<code>{c}</code>" for c in codes), parse_mode=ParseMode.HTML)
    
    elif text == "📋 كل اللوحات" and admin:
        db = load_db()
        msg = f"📋 <b>جميع لوحات 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺</b>\n👥 المستخدمون: {len(db['users'])}\n🖥️ اللوحات: {db.get('total_panels', 0)}\n\n"
        for uid, u_data in list(db['users'].items())[:10]:
            panels = u_data.get('panels', [])
            if panels:
                name = h(u_data.get('first_name', uid))
                msg += f"👤 <b>{name}</b> ({len(panels)})\n"
                for p in panels[-1:]: msg += f"  🆔 <code>{h(p['server_id'][:8].upper())}</code> | {h(p.get('expiry', 'غير محدد')[:10])}\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "👥 كل المستخدمين" and admin:
        db = load_db()
        msg, markup = build_all_users_page(db, 0)
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=markup)

    elif text == "👑 لوحة المدير" and admin:
        db = load_db()
        total_users = len(db['users'])
        total_panels = db.get('total_panels', 0)
        maint_status = "🔴 تشغيل" if db.get('maintenance') else "🟢 إيقاف"
        msg = (
            "👑 <b>لوحة المدير</b>\n\n"
            f"👥 المستخدمون: {total_users}\n"
            f"🖥️ اللوحات: {total_panels}\n"
            f"🛠️ الصيانة: {maint_status}\n\n"
            "اختر أحد الخيارات أدناه:"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_admin_panel_menu())

    elif text == "⬅️ رجوع للقائمة الرئيسية" and admin:
        await update.message.reply_text("🔙 <b>العودة إلى القائمة الرئيسية</b>", parse_mode=ParseMode.HTML, reply_markup=get_admin_main_menu())

    elif text == "📢 بث رسالة" and admin:
        context.user_data['awaiting_broadcast'] = True
        await update.message.reply_text(
            "📢 <b>البث</b>\n\nأرسل الرسالة (نص / صورة / فيديو / مستند) التي تريد بثها لجميع المستخدمين.\n\nأرسل /cancel للإلغاء.",
            parse_mode=ParseMode.HTML
        )

    elif text == "🛠️ تشغيل/إيقاف الصيانة" and admin:
        db = load_db()
        current = db.get('maintenance', False)
        status_text = "🔴 تشغيل" if current else "🟢 إيقاف"
        keyboard = [[
            InlineKeyboardButton("🟢 إيقاف", callback_data="maint_off"),
            InlineKeyboardButton("🔴 تشغيل", callback_data="maint_on")
        ]]
        await update.message.reply_text(
            f"🛠️ <b>وضع الصيانة</b>\n\nالحالة الحالية: {status_text}\n\nاختر الإجراء:",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif text == "🚫 حظر / إلغاء حظر مستخدم" and admin:
        context.user_data['awaiting_ban_id'] = True
        await update.message.reply_text("🚫 <b>أرسل الرقم التعريفي للمستخدم لحظره أو إلغاء حظره (تبديل):</b>\n\nأرسل /cancel للإلغاء.", parse_mode=ParseMode.HTML)

    elif text == "🔗 إضافة إحالة يدوياً" and admin:
        context.user_data['awaiting_referral_add'] = True
        await update.message.reply_text("🔗 <b>أرسل الرقم التعريفي للمستخدم لإضافة إحالة واحدة له:</b>\n\nأرسل /cancel للإلغاء.", parse_mode=ParseMode.HTML)

    elif text == "📊 الإحصائيات" and admin:
        db = load_db()
        total_users = len(db['users'])
        total_panels = db.get('total_panels', 0)
        banned = len(db.get('banned_users', []))
        total_redeem = len(db.get('redeem_codes', {}))
        used_redeem = sum(1 for c in db.get('redeem_codes', {}).values() if c.get('used'))
        total_referrals_sum = sum(u.get('total_referrals', 0) for u in db['users'].values())
        msg = (
            "📊 <b>الإحصائيات</b>\n\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🖥️ إجمالي اللوحات: {total_panels}\n"
            f"🚫 المستخدمون المحظورون: {banned}\n"
            f"🎫 أكواد الاسترداد: {used_redeem}/{total_redeem} مستخدمة\n"
            f"🔗 إجمالي الإحالات الممنوحة: {total_referrals_sum}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    elif context.user_data.get('awaiting_broadcast') and admin:
        context.user_data['awaiting_broadcast'] = False
        if text and text.strip().lower() == '/cancel':
            await update.message.reply_text("❌ تم إلغاء البث.")
        else:
            status_msg = await update.message.reply_text("📢 جاري البث... يرجى الانتظار")
            sent, failed, total = await do_broadcast(context, update.effective_chat.id, update.message.message_id)
            await status_msg.edit_text(
                f"📢 <b>اكتمل البث!</b>\n\n✅ تم الإرسال: {sent}\n❌ فشل: {failed}\n👥 الإجمالي: {total}",
                parse_mode=ParseMode.HTML
            )

    elif context.user_data.get('awaiting_ban_id') and admin:
        context.user_data['awaiting_ban_id'] = False
        if text and text.strip().lower() == '/cancel':
            await update.message.reply_text("❌ تم الإلغاء.")
        else:
            target_id = text.strip()
            db = load_db()
            if 'banned_users' not in db: db['banned_users'] = []
            if target_id in db['banned_users']:
                db['banned_users'].remove(target_id)
                save_db(db)
                await update.message.reply_text(f"✅ <b>تم إلغاء حظر المستخدم</b> <code>{h(target_id)}</code>", parse_mode=ParseMode.HTML)
            else:
                db['banned_users'].append(target_id)
                save_db(db)
                await update.message.reply_text(f"🚫 <b>تم حظر المستخدم</b> <code>{h(target_id)}</code>", parse_mode=ParseMode.HTML)

    elif context.user_data.get('awaiting_referral_add') and admin:
        context.user_data['awaiting_referral_add'] = False
        if text and text.strip().lower() == '/cancel':
            await update.message.reply_text("❌ تم الإلغاء.")
        else:
            target_id = text.strip()
            db = load_db()
            if target_id not in db['users']:
                await update.message.reply_text("❌ المستخدم غير موجود في قاعدة البيانات!")
            else:
                db['users'][target_id]['referral_count'] = db['users'][target_id].get('referral_count', 0) + 1
                db['users'][target_id]['total_referrals'] = db['users'][target_id].get('total_referrals', 0) + 1
                save_db(db)
                await update.message.reply_text(f"✅ <b>تمت إضافة إحالة واحدة للمستخدم</b> <code>{h(target_id)}</code>", parse_mode=ParseMode.HTML)
                try:
                    await context.bot.send_message(int(target_id), "🎉 <b>لقد تلقيت إحالة إضافية من المدير!</b>", parse_mode=ParseMode.HTML)
                except: pass
    
    elif context.user_data.get('awaiting_redeem'):
        code = text.strip().upper()
        db = load_db()
        if code in db['redeem_codes']:
            if not db['redeem_codes'][code]['used']:
                db['redeem_codes'][code]['used'] = True
                db['redeem_codes'][code]['used_by'] = str(user_id)
                save_db(db)
                db_user = get_user(user_id)
                db_user['redeem_used'] = True
                update_user(user_id, db_user)
                await update.message.reply_text("✅ تم استرداد الكود بنجاح!\nيمكنك الآن استخدام 🆕 إنشاء لوحة 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("❌ هذا الكود مستخدم بالفعل!")
        else:
            await update.message.reply_text("❌ كود غير صحيح!")
        context.user_data['awaiting_redeem'] = False

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

# ============================================
# تشغيل البوت
# ============================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # تم حذف معالج check_sub
    app.add_handler(CallbackQueryHandler(users_page_callback, pattern="^users_page_"))
    app.add_handler(CallbackQueryHandler(maintenance_toggle_callback, pattern="^maint_"))
    app.add_handler(MessageHandler((filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND, handle_broadcast_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print(f"🤖 بوت 𝑴𝑶𝑫𝒀 𝑽𝑷𝑺 يعمل...\nAPI: {API_BASE_URL}\nالبوت: @{BOT_USERNAME}")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
