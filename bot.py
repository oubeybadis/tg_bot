import os
import asyncio
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# إعدادات الاتصال (يفضل وضعها في Variables في Railway)
MONGO_URI = "رابط_مونغو_الخاص_بك"
TOKEN = "توكن_البوت_الخاص_بك"

client = MongoClient(MONGO_URI)
db = client['AlmanieaDB']

async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر لإرسال المظهر الحالي فوراً للتأكد من التنسيق والربط"""
    # 1. جلب الحالة الحالية
    state = db.settings.find_one({"id": "global_state"})
    m_idx = state['madhar_index']
    
    # 2. جلب بيانات المظهر من مجموعة madahir
    madhar = db.madahir.find_one({"index": m_idx})
    
    if not madhar:
        await update.message.reply_text("❌ لم يتم العثور على المظهر في القاعدة!")
        return

    # 3. صياغة الرسالة (تجربة إرسال كل شيء معاً للتأكد من التنسيق)
    msg = f"🧪 <b>تجربة المظهر رقم {m_idx}:</b>\n\n"
    msg += f"<b>{madhar['name']}</b>\n{madhar['description']}\n\n"
    
    # تجربة عرض المخاطر (Array)
    msg += "⚠️ <b>المخاطر:</b>\n"
    for m in madhar['makhatir']:
        msg += f"- {m['text']}\n{m['dalil']}\n"
        
    await update.message.reply_text(msg, parse_mode='HTML')

async def reset_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة العداد للمظهر رقم 1 للتجربة من جديد"""
    db.settings.update_one({"id": "global_state"}, {"$set": {"madhar_index": 1, "day_in_cycle": 1}})
    await update.message.reply_text("✅ تم إعادة العداد للمظهر رقم 1.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # أوامر الاختبار
    application.add_handler(CommandHandler('test', test_send))
    application.add_handler(CommandHandler('reset', reset_test))
    
    print("البوت يعمل... أرسل /test في التليجرام لتجربة الربط.")
    application.run_polling()