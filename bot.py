import os
import logging
import datetime
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# إعداد الربط عبر المتغيرات البيئية (للسلامة في Railway)
TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client['almaniea_db'] # تأكد من اسم قاعدة البيانات هنا

# --- دالة إرسال المظهر حسب اليوم (المنطق الرئيسي) ---
async def send_daily_content(context: ContextTypes.DEFAULT_TYPE, target_chat_id: int):
    # جلب الحالة الحالية
    state = db.settings.find_one({"id": "global_state"})
    m_idx = state['madhar_index']
    day = state['day_in_cycle']
    
    madhar = db.madahir.find_one({"index": m_idx})
    if not madhar: return

    if day == 1:
        # اليوم 1: المظهر + الوصف + المخاطر
        msg = f"🌟 <b>المظهر {m_idx}: {madhar['name']}</b>\n\n"
        msg += f"📝 {madhar['description']}\n\n"
        msg += "⚠️ <b>المخاطر والعواقب:</b>\n"
        for item in madhar['makhatir']:
            msg += f"• {item['text']}\n{item['dalil']}\n"
        await context.bot.send_message(target_chat_id, msg, parse_mode='HTML')

    elif day == 2:
        # اليوم 2: الشخص السوي + الأسئلة الكاشفة
        msg = f"⚖️ <b>تابع المظهر {m_idx}: الموقف الصحيح</b>\n\n"
        for item in madhar['right_person']:
            msg += f"✅ {item['text']}\n{item['dalil']}\n"
        
        msg += "\n❓ <b>أسئلة للمحاسبة:</b>\n"
        for q in madhar['questions']:
            msg += f"- {q}\n"
        await context.bot.send_message(target_chat_id, msg, parse_mode='HTML')

    elif day == 3:
        # اليوم 3: التحدي + استبيان الإحصاء
        msg = f"🎯 <b>اليوم الثالث: التحديات العملية (المظهر {m_idx})</b>\n\n"
        for ch in madhar['challenges']:
            msg += f"⚡️ {ch}\n"
        
        keyboard = [[InlineKeyboardButton("✅ أتممت التكليفات", callback_data=f"done_{m_idx}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg += "\n📌 <b>إحصاء الإنجاز:</b> هل قمت بالمهام؟"
        await context.bot.send_message(target_chat_id, msg, reply_markup=reply_markup, parse_mode='HTML')

# --- أمر الاختبار الفوري (Test) ---
async def test_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يرسل محتوى الأيام الثلاثة دفعة واحدة للتجربة فقط"""
    chat_id = update.effective_chat.id
    state = db.settings.find_one({"id": "global_state"})
    m_idx = state['madhar_index']
    
    await update.message.reply_text(f"🧪 <b>بدء اختبار المظهر {m_idx} فوراً...</b>", parse_mode='HTML')
    
    # محاكاة لليوم الأول
    db.settings.update_one({"id": "global_state"}, {"$set": {"day_in_cycle": 1}})
    await send_daily_content(context, chat_id)
    
    # محاكاة لليوم الثاني
    db.settings.update_one({"id": "global_state"}, {"$set": {"day_in_cycle": 2}})
    await send_daily_content(context, chat_id)
    
    # محاكاة لليوم الثالث
    db.settings.update_one({"id": "global_state"}, {"$set": {"day_in_cycle": 3}})
    await send_daily_content(context, chat_id)

# --- معالجة الضغط على الزر (الإحصاء) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    m_idx = query.data.split("_")[1]
    
    db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"completed_madahir": int(m_idx)}, "$set": {"name": query.from_user.full_name}},
        upsert=True
    )
    await query.answer("بارك الله فيك، تم تسجيل إنجازك!")

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('test', test_now))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("البوت يعمل... أرسل /test للتجربة")
    application.run_polling()