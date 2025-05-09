import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from rapidfuzz import process, fuzz

# تحميل البيانات
with open("FAC.json", encoding="utf-8") as f:
    universities = json.load(f)

with open("diplo.json", encoding="utf-8") as f:
    diplomas = json.load(f)

# قاموس اختصارات خاصة
alias_map = {
    "جامعة المنار": "Université de Tunis El Manar",
    "جامعة تونس المنار": "Université de Tunis El Manar",
    "المنار": "Université de Tunis El Manar",
    "جامعة تونس": "Université de Tunis",
    "جامعة منوبة": "Université de la Manouba",
    "جامعة قرطاج": "Université de Carthage",
    "جامعة الزيتونة": "Université Zitouna",
    "جامعة سوسة": "Université de Sousse",
    "جامعة المنستير": "Université de Monastir",
    "جامعة المهدية": "Université de Monastir",
    "جامعة القيروان": "Université de Kairouan",
    "ايزيك القيروان": "Institut Supérieur d’Informatique et de Gestion de Kairouan",
    "ايزيك قيروان": "Institut Supérieur d’Informatique et de Gestion de Kairouan",
    "isigk": "Institut Supérieur d’Informatique et de Gestion de Kairouan",
    "جامعة صفاقس": "Université de Sfax",
    "جامعة قابس": "Université de Gabès",
    "جامعة قفصة": "Université de Gafsa",
    "جامعة مدنين": "Université de Gabès",
    "جامعة جندوبة": "Université de Jendouba",
    "جامعة الكاف": "Université de Jendouba",
    "جامعة باجة": "Université de Jendouba",
    "msb": "The Mediterranean School of Business",
    "جامعة smu": "The Mediterranean School of Business",
    "جامعة msb": "The Mediterranean School of Business",
    "المدرسة المتوسطية العليا للأعمال": "The Mediterranean School of Business",
    "manouba university": "Université de la Manouba",
    "university of sousse": "Université de Sousse",
    "university of sfax": "Université de Sfax",
    "utm": "Université de Tunis El Manar",
    "uma": "Université de la Manouba",
}

# إعداد الأسماء للبحث
university_names = []
uni_name_map = {}

for uni in universities:
    name = uni["nameShort"]
    university_names.append(name)
    uni_name_map[name] = uni

    for alt in uni.get("alternativeNames", []):
        alt_name = alt["nameShort"]
        university_names.append(alt_name)
        uni_name_map[alt_name] = uni

# التحقق إذا السؤال عن شهادة
def is_degree_question(text):
    keywords = ["licence", "maîtrise", "doctorat", "إجازة", "شهادة", "master", "mastère"]
    return any(k.lower() in text.lower() for k in keywords)

# البحث الذكي عن جامعة
def search_university_fuzzy(query):
    query = alias_map.get(query.lower(), query)
    result = process.extractOne(query, university_names, scorer=fuzz.token_sort_ratio, score_cutoff=60)
    if result:
        name, score, _ = result
        uni = uni_name_map[name]
        status = uni["institutionType"]["status"]["nameShort"]
        city = uni.get("location", {}).get("originName", "غير معروف")
        site = uni.get("homepage", "لا يوجد")

        status_text = {
            "H+": "✅ معترف بها (H+)",
            "H +/-": "⚠️ معترف بها بشروط (H+/-)\n💡 يتطلب شهادة معادلة (Certificat d'Équivalence).",
            "H-": "❌ غير معترف بها (H-)"
        }.get(status, "❓ التصنيف غير معروف")

        response = f"""🏛️ الجامعة: {uni['nameShort']}
📍 المدينة: {city}
🧾 الحالة: {status_text}
🌐 الموقع: {site if site else 'لا يوجد'}"""

        return response, site if site else None
    return None, None

# البحث عن شهادة
def search_degree(query):
    for deg in diplomas:
        if query.lower() in deg["nameShort"].lower():
            name = deg['nameShort']
            type_ = deg["degreeType"]["nameShort"]
            eq = deg["equivalences"][0]["equivalenceClass"] if deg.get("equivalences") else "❓ غير محددة"
            return f"""🎓 الشهادة: {name}
📘 النوع: {type_}
⚖️ المعادلة: {eq}"""
    return None

# اقتراح أسماء قريبة
def suggest_similar_names(query):
    matches = process.extract(query, university_names, scorer=fuzz.token_sort_ratio, limit=3)
    return "\n".join([f"🔸 {m[0]}" for m in matches if m[1] >= 50])

# البحث حسب المدينة
def search_by_city(city_name):
    results = [
        uni for uni in universities
        if uni.get("location", {}).get("originName", "").lower() == city_name.lower()
    ]
    if not results:
        return "🔍 لم أجد جامعات في هذه المدينة."
    
    return "\n\n".join([
        f"🏛️ {uni['nameShort']} — {uni['institutionType']['status']['nameShort']}" for uni in results
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً بك في بوت Anabin للتعرف على الجامعات والشهادات.\n"
        "أرسل اسم الجامعة أو الشهادة وسأعطيك حالة الاعتراف.\n"
        "مثال: جامعة صفاقس، Licence en Informatique\n"
        "يمكنك أيضاً أن تسأل: جامعات في سوسة"
    )

# المعالجة الرئيسية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = update.message.from_user.username or "مجهول"

    # سجل الاستعلام
    with open("queries.log", "a", encoding="utf-8") as log:
        log.write(f"{username}: {text}\n")

    # البحث حسب المدينة
    if text.lower().startswith("جامعات في "):
        city = text[10:].strip()
        result = search_by_city(city)
        await update.message.reply_text(result)
        return

    # تحقق من نوع الاستعلام
    if is_degree_question(text):
        result = search_degree(text)
        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("❗ لم أجد شهادة بهذا الاسم.")
        return

    # البحث عن الجامعة
    response, site = search_university_fuzzy(text)
    if response:
        buttons = []
        if site:
            buttons = [[InlineKeyboardButton("🌐 زيارة الموقع", url=site)]]
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        suggestions = suggest_similar_names(text)
        await update.message.reply_text(
            f"❗ لم أجد نتيجة لهذا الاسم.\nربما تقصد:\n{suggestions or 'لا اقتراحات متاحة'}"
        )

# تشغيل البوت
def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN") or "PUT-YOUR-TOKEN-HERE"
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
