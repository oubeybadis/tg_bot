import os
import sys
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# --- 1. إعدادات البيئة (Local vs Host) ---
# يحاول البوت جلب التوكن من النظام (Railway)، إذا لم يجده يستخدم التوكن الذي تضعه أنت يدوياً
TOKEN = os.getenv('TELEGRAM_TOKEN', '8299199892:AAFL-hUeOcKYYvoHV8-MYeIAfAnIhZ8wzi0')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://oubeybadis009_db_user:5d5K9tAot0HFEFZh@cluster0.jz2pymp.mongodb.net/?appName=Cluster0') # أو رابط الأطلس المباشر
GROUP_ID = os.getenv('GROUP_ID', '-5141081043')

# --- 2. الاتصال بقاعدة البيانات ---
try:
    client = MongoClient(MONGO_URI)
    # نتحقق من الاتصال
    client.admin.command('ping')
    db = client['tgbot']
    print("✅ تم الاتصال بقاعدة البيانات بنجاح")
except Exception as e:
    print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    sys.exit(1)

# --- 3. الدوال الأساسية (Daily & Callback) ---

async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """الدالة التي تعمل تلقائياً كل 24 ساعة"""
    state = db.settings.find_one({"id": "global_state"})
    if not state: return
    
    m_idx, day = state['madhar_index'], state['day_in_cycle']
    madhar = db.madahir.find_one({"index": m_idx})
    if not madhar: return

    # بناء الرسالة بناءً على اليوم
    text = f"🌟 <b>المظهر {m_idx}: {madhar['name']}</b>\n"
    reply_markup = None

    if day == 1:
        text += f"\n📝 {madhar['description']}\n\n⚠️ <b>المخاطر:</b>\n"
        for m in madhar.get('makhatir', []):
            text += f"• {m['text']}\n{m['dalil']}\n"
    elif day == 2:
        text += f"\n✅ <b>الموقف السوي:</b>\n"
        for r in madhar.get('right_person', []):
            text += f"• {r['text']}\n{r['dalil']}\n"
        text += "\n❓ <b>أسئلة للمحاسبة:</b>\n" + "\n".join([f"- {q}" for q in madhar.get('questions', [])])
    elif day == 3:
        text += f"\n🎯 <b>التحديات العملية:</b>\n" + "\n".join([f"⚡️ {c}" for c in madhar.get('challenges', [])])
        keyboard = [[InlineKeyboardButton("✅ أتممت التكليفات", callback_data=f"done_{m_idx}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=GROUP_ID, text=text, reply_markup=reply_markup, parse_mode='HTML')

    # تحديث الحالة لليوم التالي
    new_day = day + 1 if day < 3 else 1
    new_idx = m_idx if day < 3 else (m_idx + 1 if m_idx < 18 else 1)
    db.settings.update_one({"id": "global_state"}, {"$set": {"madhar_index": new_idx, "day_in_cycle": new_day}})

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار الإنجاز"""
    query = update.callback_query
    m_idx = query.data.split("_")[1]
    db.users.update_one(
        {"user_id": query.from_user.id},
        {"$addToSet": {"completed": int(m_idx)}, "$set": {"name": query.from_user.full_name}},
        upsert=True
    )
    await query.answer("بارك الله فيك، تم تسجيل إنجازك!")

# --- 4. دالة الاختبار الشامل (Test All) ---

async def test_all_structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال هيكل الأيام الثلاثة دفعة واحدة لرؤية التنسيق"""
    chat_id = update.effective_chat.id
    madhar = db.madahir.find_one({"index": 1}) # نختبر بالمظهر الأول
    
    if not madhar:
        await update.message.reply_text("❌ لم أجد بيانات في مجموعة madahir")
        return

    await update.message.reply_text("🧪 <b>بدء اختبار الهيكل الكامل...</b>", parse_mode='HTML')
    
    # محاكاة اليوم 1 و 2 و 3
    for d in range(1, 4):
        # هنا استدعينا منطق الرسالة بشكل يدوي للاختبار
        msg = f"📌 <b>معاينة رسالة اليوم {d}:</b>\n"
        # (بقية كود التنسيق مشابه للـ daily_broadcast أعلاه)
        await context.bot.send_message(chat_id, msg + " سيظهر هنا محتوى المظهر المنسق...", parse_mode='HTML')

# --- 5. التشغيل الرئيسي ---

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # الجدولة (تعمل في الخلفية)
    if application.job_queue:
        # ترسل للمجموعة كل 24 ساعة، وتبدأ أول مرة بعد 5 ثوانٍ من تشغيل البوت
        application.job_queue.run_repeating(daily_broadcast, interval=86400, first=5)

    # الأوامر
    application.add_handler(CommandHandler('test_all', test_all_structure))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print(f"🚀 البوت يعمل الآن في وضع: {'Host' if os.getenv('TELEGRAM_TOKEN') else 'Local'}")
    application.run_polling()