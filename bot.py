import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from database import Database

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

db = Database()

# حالات المحادثة
(REGISTER_NAME, REGISTER_USERNAME, POST_CONTENT, COMMENT_WRITE,
 VERIFICATION_REASON, SEARCH_USER) = range(6)

# ============ الأزرار ============

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 نشر منشور", callback_data="new_post"),
         InlineKeyboardButton("🏠 الرئيسية", callback_data="timeline")],
        [InlineKeyboardButton("👤 حسابي", callback_data="my_profile"),
         InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
        [InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications"),
         InlineKeyboardButton("✅ طلب توثيق", callback_data="request_verify")],
    ]
    return InlineKeyboardMarkup(keyboard)

def post_keyboard(post_id, user_id):
    like_text = "❤️" if db.has_liked(user_id, post_id) else "🤍"
    keyboard = [
        [
            InlineKeyboardButton(f"{like_text} إعجاب", callback_data=f"like_{post_id}"),
            InlineKeyboardButton("💬 تعليق", callback_data=f"comment_{post_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("✅ طلبات التوثيق", callback_data="admin_verify")],
        [InlineKeyboardButton("📢 إشعار جماعي", callback_data="admin_broadcast")],
    ]
    return InlineKeyboardMarkup(keyboard)

def profile_keyboard(user_id, profile_user_id):
    if user_id == profile_user_id:
        keyboard = [
            [InlineKeyboardButton("📝 منشوراتي", callback_data=f"myposts_{profile_user_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="timeline")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("👥 متابعة", callback_data=f"follow_{profile_user_id}")],
            [InlineKeyboardButton("📝 منشوراته", callback_data=f"myposts_{profile_user_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="timeline")],
        ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="timeline")]]
    return InlineKeyboardMarkup(keyboard)

# ============ تنسيق ============

def format_post(post, user_id):
    post_id, post_user_id, content, created_at, likes, comments, _, full_name, username, is_verified = post
    verified_badge = " ✅" if is_verified else ""
    text = f"""
╭━━━━━━━━━━━━━━━━╮
┃   🏛️ منصة بغداد   ┃
╰━━━━━━━━━━━━━━━━╯

👤 {full_name}{verified_badge}
🆔 @{username}
🕐 {created_at}

━━━━━━━━━━━━━━━━━
📝 {content}
━━━━━━━━━━━━━━━━━

❤️ {likes} إعجاب    💬 {comments} تعليق
"""
    return text

def format_profile(user, user_id):
    user_id_db, full_name, username, is_verified, is_banned, bio, join_date = user
    followers = db.get_followers_count(user_id_db)
    following = db.get_following_count(user_id_db)
    verified_badge = " ✅" if is_verified else ""
    
    text = f"""
╭━━━━━━━━━━━━━━━━╮
┃   🏛️ منصة بغداد   ┃
╰━━━━━━━━━━━━━━━━╯

👤 {full_name}{verified_badge}
🆔 @{username}
📝 {bio if bio else 'لا يوجد نبذة'}
📅 انضم: {join_date}

━━━━━━━━━━━━━━━━━
👥 المتابِعون: {followers}  |  المتابَعون: {following}
━━━━━━━━━━━━━━━━━
"""
    return text

# ============ البداية ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if db.user_exists(user_id):
        user = db.get_user(user_id)
        if user[4] == 1:
            await update.message.reply_text("⚠️ عذراً، حسابك محظور من المنصة.")
            return ConversationHandler.END
        await update.message.reply_text(
            f"👋 أهلاً بعودتك {user[1]}!\n\nاستخدم الأزرار أدناه:",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🏛️ *أهلاً بك في منصة بغداد!*\n\n"
        "📝 منصة تدوين مصغرة للكلمة الحرة\n"
        "لنبدأ بتسجيل حسابك...\n\n"
        "✍️ *أدخل اسمك الكامل:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['full_name'] = update.message.text.strip()
    await update.message.reply_text(
        "✅ جميل!\n\n"
        "🆔 الآن اختر *معرف المستخدم (username)* الخاص بك:\n"
        "• باللغة الإنجليزية فقط\n"
        "• بدون مسافات\n"
        "• مثال: ahmed_baghdadi",
        parse_mode=ParseMode.MARKDOWN
    )
    return REGISTER_USERNAME

async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    
    if not username.replace('_', '').replace('.', '').isalnum():
        await update.message.reply_text("❌ معرف غير صالح. استخدم حروف إنجليزية وأرقام و _ و . فقط.\nحاول مجدداً:")
        return REGISTER_USERNAME
    
    if len(username) < 3 or len(username) > 30:
        await update.message.reply_text("❌ المعرف يجب أن يكون بين 3 و 30 حرف.\nحاول مجدداً:")
        return REGISTER_USERNAME
    
    if db.username_taken(username):
        await update.message.reply_text("❌ هذا المعرف مستخدم بالفعل. اختر معرفاً آخر:")
        return REGISTER_USERNAME
    
    user_id = update.effective_user.id
    full_name = context.user_data['full_name']
    
    db.register_user(user_id, full_name, username)
    
    await update.message.reply_text(
        f"🎉 *مبروك! تم تسجيلك بنجاح في منصة بغداد!*\n\n"
        f"👤 الاسم: {full_name}\n"
        f"🆔 المعرف: @{username}\n\n"
        f"ابدأ بنشر أول تغريدة لك 📝",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# ============ النشر ============

async def new_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not db.user_exists(user_id):
        await query.edit_message_text("❌ تحتاج لتسجيل الدخول أولاً. أرسل /start")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📝 *أرسل منشورك الآن:*\n"
        "• نص فقط (بدون صور أو فيديوهات)\n"
        "• الحد الأقصى 500 حرف",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )
    return POST_CONTENT

async def post_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    content = update.message.text.strip()
    
    if len(content) > 500:
        await update.message.reply_text("❌ المنشور طويل جداً. الحد الأقصى 500 حرف.\nحاول مجدداً:")
        return POST_CONTENT
    
    post_id = db.create_post(user_id, content)
    post = db.get_post(post_id)
    
    await update.message.reply_text(
        format_post(post, user_id),
        reply_markup=post_keyboard(post_id, user_id)
    )
    await update.message.reply_text(
        "✅ تم نشر تغريدتك!",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# ============ الرئيسية ============

async def show_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not db.user_exists(user_id):
        await query.edit_message_text("❌ تحتاج لتسجيل الدخول أولاً. أرسل /start")
        return
    
    posts = db.get_timeline(user_id, limit=10)
    
    if not posts:
        await query.edit_message_text(
            "📭 لا توجد منشورات حالياً.\nتابع مستخدمين آخرين لرؤية منشوراتهم!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    for i, post in enumerate(posts):
        text = format_post(post, user_id)
        keyboard = post_keyboard(post[0], user_id)
        
        if i == 0:
            await query.edit_message_text(text, reply_markup=keyboard)
        else:
            await query.message.reply_text(text, reply_markup=keyboard)
    
    await query.message.reply_text("📍 هذه هي أحدث المنشورات", reply_markup=main_menu_keyboard())

# ============ الملف الشخصي ============

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not db.user_exists(user_id):
        await query.edit_message_text("❌ تحتاج لتسجيل الدخول أولاً. أرسل /start")
        return
    
    user = db.get_user(user_id)
    text = format_profile(user, user_id)
    
    await query.edit_message_text(
        text,
        reply_markup=profile_keyboard(user_id, user_id)
    )

# ============ اللايكات والتعليقات ============

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    post_id = int(query.data.split('_')[1])
    
    if not db.user_exists(user_id):
        await query.answer("سجل دخولك أولاً", show_alert=True)
        return
    
    liked = db.toggle_like(user_id, post_id)
    
    post = db.get_post(post_id)
    if post:
        await query.edit_message_text(
            format_post(post, user_id),
            reply_markup=post_keyboard(post_id, user_id)
        )
    
    await query.answer("❤️ تم الإعجاب" if liked else "💔 تم إلغاء الإعجاب")

async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    post_id = int(query.data.split('_')[1])
    
    if not db.user_exists(user_id):
        await query.answer("سجل دخولك أولاً", show_alert=True)
        return
    
    context.user_data['comment_post_id'] = post_id
    
    await query.edit_message_text(
        "💬 *أرسل تعليقك:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )
    return COMMENT_WRITE

async def comment_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    content = update.message.text.strip()
    post_id = context.user_data.get('comment_post_id')
    
    if not post_id:
        await update.message.reply_text("❌ حدث خطأ. حاول مجدداً.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    db.add_comment(user_id, post_id, content)
    
    post = db.get_post(post_id)
    if post and post[1] != user_id:
        commenter = db.get_user(user_id)
        db.add_notification(post[1], f"💬 {commenter[1]} علّق على منشورك: {content[:50]}...")
    
    await update.message.reply_text("✅ تم إضافة تعليقك!", reply_markup=main_menu_keyboard())
    
    post = db.get_post(post_id)
    if post:
        await update.message.reply_text(
            format_post(post, user_id),
            reply_markup=post_keyboard(post_id, user_id)
        )
    
    return ConversationHandler.END

# ============ البحث والمتابعة ============

async def show_user_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    profile_id = int(query.data.split('_')[1])
    
    user = db.get_user(profile_id)
    posts = db.get_user_posts(profile_id, limit=10)
    
    if not posts:
        await query.edit_message_text(
            f"📭 @{user[2]} لم ينشر أي شيء بعد.",
            reply_markup=profile_keyboard(user_id, profile_id)
        )
        return
    
    for i, post in enumerate(posts):
        text = format_post(post, user_id)
        keyboard = post_keyboard(post[0], user_id)
        
        if i == 0:
            await query.edit_message_text(text, reply_markup=keyboard)
        else:
            await query.message.reply_text(text, reply_markup=keyboard)

async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *أرسل معرف المستخدم (username) للبحث عنه:*\n"
        "مثال: @ahmed_baghdadi",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )
    return SEARCH_USER

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().replace('@', '').lower()
    user = db.get_user_by_username(username)
    
    if not user:
        await update.message.reply_text("❌ لم يتم العثور على هذا المستخدم.\nحاول مجدداً أو ارجع للقائمة:", reply_markup=back_keyboard())
        return SEARCH_USER
    
    user_id = update.effective_user.id
    text = format_profile(user, user_id)
    
    await update.message.reply_text(text, reply_markup=profile_keyboard(user_id, user[0]))
    return ConversationHandler.END

async def handle_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    following_id = int(query.data.split('_')[1])
    
    result = db.toggle_follow(user_id, following_id)
    
    following_user = db.get_user(following_id)
    
    if result is None:
        await query.answer("لا يمكنك متابعة نفسك", show_alert=True)
    elif result:
        db.add_notification(following_id, f"👥 مستخدم جديد يتابعك!")
        await query.answer(f"✅ أنت الآن تتابع @{following_user[2]}")
    else:
        await query.answer(f"❌ ألغيت متابعة @{following_user[2]}")
    
    text = format_profile(following_user, user_id)
    keyboard = profile_keyboard(user_id, following_id)
    await query.edit_message_text(text, reply_markup=keyboard)

# ============ التوثيق ============

async def request_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user = db.get_user(user_id)
    if user[3] == 1:
        await query.edit_message_text("✅ حسابك موثق بالفعل!", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    if db.has_pending_verification(user_id):
        await query.edit_message_text("⏳ لديك طلب توثيق قيد المراجعة.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END
    
    await query.edit_message_text(
        "✅ *طلب توثيق الحساب*\n\n"
        "📝 اكتب سبب طلب التوثيق:\n"
        "• من أنت؟\n"
        "• لماذا تستحق التوثيق؟",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )
    return VERIFICATION_REASON

async def verification_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reason = update.message.text.strip()
    
    db.request_verification(user_id, reason)
    
    await update.message.reply_text(
        "✅ تم إرسال طلب التوثيق!\n"
        "سيتم مراجعته من قبل الإدارة قريباً.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# ============ الإشعارات ============

async def show_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    notifications = db.get_unread_notifications(user_id)
    
    if not notifications:
        await query.edit_message_text("🔔 لا توجد إشعارات جديدة.", reply_markup=main_menu_keyboard())
        return
    
    text = "🔔 *الإشعارات:*\n\n"
    for notif in notifications[:10]:
        text += f"• {notif[2]}\n  _{notif[4]}_\n\n"
    
    db.mark_notifications_read(user_id)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )

# ============ الأدمن ============

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح لك.", reply_markup=main_menu_keyboard())
        return
    
    await update.message.reply_text(
        "🛡️ *لوحة تحكم الأدمن - منصة بغداد*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_keyboard()
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    users_count = db.get_users_count()
    posts_count = db.get_posts_count()
    
    text = f"""
📊 *إحصائيات منصة بغداد*

👥 المستخدمين: {users_count}
📝 المنشورات: {posts_count}
"""
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_keyboard())

async def admin_verify_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    requests = db.get_pending_verifications()
    
    if not requests:
        await query.edit_message_text("✅ لا توجد طلبات توثيق معلقة.", reply_markup=admin_keyboard())
        return
    
    for req in requests:
        req_id, user_id, reason, status, created_at, full_name, username = req
        text = f"📋 طلب توثيق #{req_id}\n👤 {full_name} (@{username})\n📝 {reason}\n🕐 {created_at}"
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول", callback_data=f"approve_{req_id}_{user_id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{req_id}"),
            ]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    await query.edit_message_text("📋 طلبات التوثيق أعلاه:", reply_markup=admin_keyboard())

async def admin_approve_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    _, req_id, user_id = query.data.split('_')
    db.approve_verification(int(req_id), int(user_id))
    db.add_notification(int(user_id), "✅ تم توثيق حسابك في منصة بغداد!")
    
    await query.edit_message_text(f"✅ تمت الموافقة على الطلب #{req_id}")

async def admin_reject_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    req_id = int(query.data.split('_')[1])
    db.reject_verification(req_id)
    
    await query.edit_message_text(f"❌ تم رفض الطلب #{req_id}")

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    await query.edit_message_text(
        "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:",
        reply_markup=back_keyboard()
    )
    return "BROADCAST_MSG"

async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        return ConversationHandler.END
    
    message = update.message.text
    users = db.get_all_users()
    count = 0
    
    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 *إشعار من الإدارة:*\n\n{message}", parse_mode=ParseMode.MARKDOWN)
            count += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ تم الإرسال إلى {count} مستخدم.", reply_markup=admin_keyboard())
    return ConversationHandler.END

# ============ الرجوع ============

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏛️ *منصة بغداد - القائمة الرئيسية*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

# ============ الرسائل العشوائية ============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db.user_exists(user_id):
        await update.message.reply_text(
            "👋 استخدم الأزرار أدناه للتنقل:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text("🏛️ أهلاً بك! أرسل /start للتسجيل في منصة بغداد.")

# ============ التشغيل ============

def main():
    app = Application.builder().token(TOKEN).build()
    
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    post_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_post_start, pattern='^new_post$')],
        states={
            POST_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_content),
                CallbackQueryHandler(go_back, pattern='^timeline$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    comment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_comment, pattern='^comment_')],
        states={
            COMMENT_WRITE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, comment_write),
                CallbackQueryHandler(go_back, pattern='^timeline$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_user_start, pattern='^search_user$')],
        states={
            SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_user),
                CallbackQueryHandler(go_back, pattern='^timeline$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    verify_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(request_verify, pattern='^request_verify$')],
        states={
            VERIFICATION_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, verification_reason),
                CallbackQueryHandler(go_back, pattern='^timeline$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern='^admin_broadcast$')],
        states={
            "BROADCAST_MSG": [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(reg_conv)
    app.add_handler(post_conv)
    app.add_handler(comment_conv)
    app.add_handler(search_conv)
    app.add_handler(verify_conv)
    app.add_handler(broadcast_conv)
    
    app.add_handler(CallbackQueryHandler(show_timeline, pattern='^timeline$'))
    app.add_handler(CallbackQueryHandler(my_profile, pattern='^my_profile$'))
    app.add_handler(CallbackQueryHandler(show_notifications, pattern='^notifications$'))
    app.add_handler(CallbackQueryHandler(show_user_posts, pattern='^myposts_'))
    app.add_handler(CallbackQueryHandler(handle_like, pattern='^like_'))
    app.add_handler(CallbackQueryHandler(handle_follow, pattern='^follow_'))
    app.add_handler(CallbackQueryHandler(go_back, pattern='^back$'))
    
    app.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    app.add_handler(CallbackQueryHandler(admin_verify_list, pattern='^admin_verify$'))
    app.add_handler(CallbackQueryHandler(admin_approve_verify, pattern='^approve_'))
    app.add_handler(CallbackQueryHandler(admin_reject_verify, pattern='^reject_'))
    
    app.add_handler(CommandHandler('admin', admin_panel))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🏛️ منصة بغداد تعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    import sys
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
