import os
import json
import datetime
import pytz
import asyncio
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest

# --- 1. إعدادات البيئة ---
IS_HOSTED = os.getenv('TELEGRAM_TOKEN') is not None
TOKEN = os.getenv('TELEGRAM_TOKEN', '8299199892:AAFL-hUeOcKYYvoHV8-MYeIAfAnIhZ8wzi0')
GROUP_ID = os.getenv('GROUP_ID', '-5141081043')
TIMEZONE = pytz.timezone("Africa/Algiers")

if IS_HOSTED:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['tgbot']
else:
    print("💻 وضع التطوير المحلي: البيانات من data.json")

# --- 2. دالة جلب البيانات ---
def fetch_data(collection, query=None):
    if IS_HOSTED:
        return db[collection].find_one(query) if query else db[collection].find_one()
    else:
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                if collection == "settings": return data.get("settings")
                if collection == "madahir":
                    return next((m for m in data.get("madahir", []) if m['index'] == query.get('index')), None)
        except: return None

# --- 3. محرك صياغة الرسائل المحدث ---
def build_message(madhar, day, part):
    m_idx = madhar['index']
    m_name = madhar['name']
    text = ""
    reply_markup = None

    if day == 1:
        if part == 'morning':
            text = (f"☀️ <b>صباح الوعي والتزكية..</b>\n"
                    f"المظهر {m_idx}: {m_name}\n\n"
                    f"نبدأ اليوم رحلتنا مع مظهر قلبي دقيق:\n"
                    f"📝 <b>التعريف:</b> {madhar['description']}\n\n"
                    f"سنلتقي مساءً للتعمق أكثر! 🌱")
        else:
            text = (f"🌙 <b>وقفة مع النفس..</b>\n\n"
                    f"بعد يوم من المراقبة، اسأل نفسك بصدق وهدوء:\n"
                    f"❓ <b>الأسئلة الكاشفة:</b>\n\n" + 
                    "\n\n".join([f"{q}؟" for q in madhar.get('questions', [])]) +
                    f"\n\nتذكر: الصدق مع النفس هو أول خطوات العلاج.. 💡")
    elif day == 2:
        if part == 'morning':
            text = f"🚫 <b>المخاطر:</b>\n"
            for m in madhar.get('makhatir', []):
                text += f"• {m['text']}\n<blockquote>{m['dalil']}</blockquote>\n"
            text += f"\nاجعل هذا التحذير نصب عينيك اليوم. 🛡"
        else:
            text = f"<b>هكذا يكون المؤمن..</b>\n\n" \
                   f"بعد أن عرفنا المخاطر، إليك كيف يتصرف المؤمن الصحيح:\n" \
                   f"✅ <b>الموقف الصحيح:</b>\n"
            for r in madhar.get('right_person', []):
                text += f"• {r['text']}\n<blockquote>{r['dalil']}</blockquote>\n"
            text += f"\nحاول أن تمارس هذا الخلق في تعاملاتك الآن. ✨"
    elif day == 3:
        if part == 'morning':
            text = (f"🎯 <b>وقت العمل والتحدي!</b>\n\n"
                    f"صباح الهمة! اليوم هو يوم التطبيق الفعلي، لنكسر صنم {m_name} بداخلنا:\n"
                    f"⚡️ <b>الأفعال المضادة:</b>\n\n" + "\n\n".join([f"- {c}" for c in madhar.get('challenges', [])]) +
                    f"\n\nالمؤمن لا يكتفي بالعلم، بل يعمل! انطلق 🚀")
        else:
            # تم حذف منطق الزر هنا بناءً على طلبك
            text = (f"⌛️ <b>اقتربنا من النهاية..</b>\n\n"
                    f"مضت 3 أيام من مجاهدة مظهر ({m_name}).\n"
                    f"📢 <b>تذكير:</b> إذا لم تكمل تكليفاتك فسارع الآن، لا تؤجل طهارة قلبك! 🏃‍♂️💨")
            reply_markup = None 

    return text, reply_markup

# --- 4. معالجة الضغط على الزر (للمظاهر السابقة إن وجدت) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    m_idx = query.data.split("_")[1]
    
    if IS_HOSTED:
        db.users.update_one(
            {"user_id": query.from_user.id},
            {"$addToSet": {"completed": int(m_idx)}, "$set": {"name": query.from_user.full_name}},
            upsert=True
        )
    
    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=query.from_user.id, text="بارك الله فيك، تم تسجيل إنجازك! ✨")

# --- 5. الدوال المجدولة والاختبار ---
async def scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    state = fetch_data("settings")
    madhar = fetch_data("madahir", {"index": state['madhar_index']})
    if not madhar: return

    text, markup = build_message(madhar, state['day_in_cycle'], state['day_part'])
    await context.bot.send_message(chat_id=GROUP_ID, text=text, reply_markup=markup, parse_mode='HTML')

    if IS_HOSTED:
        part, day, m_idx = state['day_part'], state['day_in_cycle'], state['madhar_index']
        new_part = 'evening' if part == 'morning' else 'morning'
        new_day = day + 1 if (part == 'evening' and day < 3) else (1 if part == 'evening' else day)
        new_idx = m_idx + 1 if (part == 'evening' and day == 3) else m_idx
        db.settings.update_one({"id": "global_state"}, {"$set": {"madhar_index": new_idx, "day_in_cycle": new_day, "day_part": new_part}})

async def test_full_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = fetch_data("settings")
    madhar = fetch_data("madahir", {"index": state['madhar_index']})
    cycle = [(1, 'morning'), (1, 'evening'), (2, 'morning'), (2, 'evening'), (3, 'morning'), (3, 'evening')]
    for d, p in cycle:
        text, markup = build_message(madhar, d, p)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=markup, parse_mode='HTML')
        await asyncio.sleep(1)
async def test_group_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks if the bot can send a message to the defined GROUP_ID."""
    try:
        test_msg = await context.bot.send_message(
            chat_id=GROUP_ID, 
            text="✅ **فحص الاتصال:** البوت يعمل بنجاح في هذه المجموعة ومستعد لجدول الغد!",
            parse_mode='HTML'
        )
        await update.message.reply_text(f"✅ تم إرسال رسالة التجربة بنجاح إلى المجموعة (ID: {GROUP_ID})")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل الإرسال للمجموعة. تأكد من:\n1. البوت مضاف للمجموعة.\n2. البوت لديه صلاحية إرسال الرسائل.\n\nالخطأ: {str(e)}")
# --- 6. التشغيل الأساسي (Main) ---
async def main():
    request_config = HTTPXRequest(connect_timeout=60, read_timeout=60)
    # ملاحظة: يفضل تغيير التوكن للامان
    application = ApplicationBuilder().token(TOKEN).request(request_config).build()
    application.add_handler(CommandHandler('test_all', test_full_cycle))
    application.add_handler(CommandHandler('test_group', test_group_connection))
    application.add_handler(CallbackQueryHandler(handle_callback))

    if application.job_queue:
        application.job_queue.run_daily(scheduled_broadcast, time=datetime.time(hour=7, minute=0, tzinfo=TIMEZONE))
        application.job_queue.run_daily(scheduled_broadcast, time=datetime.time(hour=17, minute=0, tzinfo=TIMEZONE))

    async with application:
        await application.initialize()
        await application.start()
        print(f"🚀 البوت يعمل الآن.. النصوص محدثة.")
        await application.updater.start_polling()
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): print("👋 تم إيقاف البوت.")