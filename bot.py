import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# إعداد المتغيرات البيئية
TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
GROUP_ID = os.getenv('GROUP_ID') # رقم المجموعة من Railway Variables

# الاتصال بقاعدة البيانات
client = MongoClient(MONGO_URI)
db = client['tgbot'] # تأكد أن هذا هو اسم القاعدة في MongoDB Atlas

# --- دالة الإرسال اليومي (تلقائية) ---
async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    try:
        state = db.settings.find_one({"id": "global_state"})
        if not state: return
        
        m_idx = state['madhar_index']
        day = state['day_in_cycle']
        
        madhar = db.madahir.find_one({"index": m_idx})
        if not madhar: return

        text = ""
        reply_markup = None

        if day == 1:
            text = f"🔹 <b>اليوم 1: {madhar['name']}</b>\n\n{madhar['description']}\n\n⚠️ <b>المخاطر:</b>\n"
            for m in madhar.get('makhatir', []):
                text += f"• {m['text']}\n{m['dalil']}\n"
        
        elif day == 2:
            text = f"⚖️ <b>اليوم 2: الموقف السوي (المظهر {m_idx})</b>\n\n"
            for r in madhar.get('right_person', []):
                text += f"✅ {r['text']}\n{r['dalil']}\n"
            text += "\n❓ <b>أسئلة للمحاسبة:</b>\n"
            for q in madhar.get('questions', []):
                text += f"- {q}\n"
                
        elif day == 3:
            text = f"🎯 <b>اليوم 3: التحدي العملي (المظهر {m_idx})</b>\n\n"
            for c in madhar.get('challenges', []):
                text += f"⚡️ {c}\n"
            keyboard = [[InlineKeyboardButton("✅ أتممت التكليفات", callback_data=f"done_{m_idx}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

        # الإرسال للمجموعة
        await context.bot.send_message(chat_id=GROUP_ID, text=text, reply_markup=reply_markup, parse_mode='HTML')

        # تحديث العداد لليوم التالي (Recovery)
        next_day = day + 1 if day < 3 else 1
        next_idx = m_idx if day < 3 else (m_idx + 1 if m_idx < 18 else 1)
        db.settings.update_one({"id": "global_state"}, {"$set": {"madhar_index": next_idx, "day_in_cycle": next_day}})
        
    except Exception as e:
        print(f"Error in daily broadcast: {e}")

# --- معالجة الضغط على زر الإنجاز ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    m_idx = query.data.split("_")[1]
    
    # تسجيل الإنجاز في جدول users
    db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"completed_madahir": int(m_idx)}, "$set": {"name": query.from_user.full_name}},
        upsert=True
    )
    await query.answer("بارك الله فيك، تم تسجيل إنجازك!")

# --- أمر الاختبار الشامل ---
async def test_all_structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        state = db.settings.find_one({"id": "global_state"})
        m_idx = state.get('madhar_index', 1) if state else 1
        madhar = db.madahir.find_one({"index": m_idx})
        
        if not madhar:
            await update.message.reply_text("❌ لم يتم العثور على البيانات!")
            return

        # إرسال عينة من الأيام الثلاثة دفعة واحدة لرؤية التنسيق
        await update.message.reply_text(f"🧪 <b>فحص هيكل المظهر رقم {m_idx}</b>", parse_mode='HTML')
        
        # اليوم 1
        t1 = f"<b>[هيكل اليوم 1]</b>\n🌟 {madhar['name']}\n{madhar['description']}"
        await context.bot.send_message(chat_id, t1, parse_mode='HTML')
        
        # اليوم 3 (مع الزر للتجربة)
        t3 = f"<b>[هيكل اليوم 3]</b>\n🎯 التحدي: {madhar['challenges'][0]}"
        keyboard = [[InlineKeyboardButton("✅ تجربة الزر", callback_data=f"done_{m_idx}")]]
        await context.bot.send_message(chat_id, t3, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

if __name__ == '__main__':
    # بناء التطبيق
    application = ApplicationBuilder().token(TOKEN).build()
    
    # تشغيل الجدولة التلقائية
    if application.job_queue:
        application.job_queue.run_repeating(daily_broadcast, interval=86400, first=10)
    
    # تعريف الأوامر
    application.add_handler(CommandHandler('test_group', test_all_structure))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("البوت يعمل بنجاح...")
    application.run_polling()
    