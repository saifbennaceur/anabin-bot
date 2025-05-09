from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from rapidfuzz import process
import json

# --- تحميل البيانات ---
with open("FAC.json", encoding="utf-8") as f:
    universities = json.load(f)

with open("diplo.json", encoding="utf-8") as f:
    diplomas = json.load(f)

# --- تجهيز أسماء الجامعات فقط لأجل البحث السريع ---
university_names = [uni["nameShort"] for uni in universities]

# --- البحث الذكي عن جامعة ---
def search_university_fuzzy(query):
    result = process.extractOne(query, university_names, score_cutoff=60)
    if result:
        name, score, index = result
        uni = universities[index]
        status = uni["institutionType"]["status"]["nameShort"]
        if status == "H+":
            return f"✅ الجامعة \"{uni['nameShort']}\" معترف بها (H+)."
        elif status == "H +/-":
            return f"⚠️ الجامعة \"{uni['nameShort']}\" معترف بها بشروط (H+/-).\n💡 يجب توفر شهادة معادلة (Certificat d'Équivalence)."
        else:
            return f"❌ الجامعة \"{uni['nameShort']}\" غير معترف بها."
    return None

# --- البحث عن شهادة ---
def search_degree(query):
    for deg in diplomas:
        if query.lower() in deg["nameShort"].lower():
            name = deg['nameShort']
            type_ = deg["degreeType"]["nameShort"]
            eq = deg["equivalences"][0]["equivalenceClass"] if deg.get("equivalences") else "❓ غير محدد"
            return f"🎓 الشهادة: {name}\n📘 النوع: {type_}\n⚖️ المعادلة: {eq}"
    return None

# --- المعالجة الرئيسية للرسائل ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    response = search_university_fuzzy(text) or search_degree(text)
    if not response:
        response = "❗ لم أجد نتيجة لهذا الاسم. حاول كتابة اسم الجامعة أو الشهادة بدقة أكبر."
    await update.message.reply_text(response)

# --- تشغيل البوت ---
def main():
    BOT_TOKEN ="8072475015:AAGP4Ow0AeYJ4YUuE4a6utPlcINS9Wy5scY"
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 البوت شغّال الآن... اضغط Ctrl+C لإيقافه.")
    app.run_polling()

if __name__ == "__main__":
    main()
