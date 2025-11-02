import os, re, requests, telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
BOT_TOKEN  = os.getenv("BOT_TOKEN")
MONGO_URI  = os.getenv("MONGO_URI")
PROV_TOKEN = os.getenv("PROVIDER_TOKEN") or ""

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
db  = MongoClient(MONGO_URI).get_database("tiktokbot")
users = db.users

def get_clean_video(url: str) -> bytes:
    api = "https://ssstik.io/abc"          # demo endpoint
    # The code below uses a direct post request which might be easily blocked. 
    # For better stability, use a reliable API later.
    r = requests.post(api, data={"id": url, "locale": "en"}, timeout=30)
    r.raise_for_status()
    return r.content

def ads_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Ads Channel", url="t.me/youradschannel"))
    kb.add(InlineKeyboardButton("⭐ Remove limits – 2$", callback_data="pay"))
    return kb

@bot.message_handler(commands=["start"])
def welcome(msg):
    uid = msg.from_user.id
    users.update_one({"_id": uid}, {"$setOnInsert": {"count": 0, "paid": False}}, upsert=True)
    bot.reply_to(msg, "Send TikTok / Instagram / YouTube / Pinterest link and I’ll return the video without watermark.")

@bot.message_handler(regexp=r"https?://(?:www\.)?(tiktok|instagram|youtube|youtu\.be|pin)\.com/\S+")
def handle_link(msg):
    uid = msg.from_user.id
    u   = users.find_one({"_id": uid})
    if u["count"] >= 3 and not u.get("paid"):
        # Note: This checks for "paid" field existence AND if it's False
        return bot.send_message(uid, "⛔ Daily limit reached.", reply_markup=ads_kb())

    bot.send_chat_action(uid, "upload_video")
    try:
        mp4 = get_clean_video(msg.text)
        bot.send_video(uid, mp4, caption="✅ Done!")
        users.update_one({"_id": uid}, {"$inc": {"count": 1}})
    except Exception as e:
        bot.reply_to(msg, "❌ Failed, check the link.")

@bot.callback_query_handler(func=lambda c: c.data == "pay")
def invoice(c):
    prices = [telebot.types.LabeledPrice("Lifetime VIP", 200)]   # 200 Stars (Telegram Stars)
    bot.send_invoice(c.from_user.id, title="VIP", description="Unlimited downloads, no ads",
                     invoice_payload="vip", provider_token=PROV_TOKEN, currency="XTR",
                     prices=prices, start_parameter="pay")

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q): bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def got_pay(msg):
    users.update_one({"_id": msg.from_user.id}, {"$set": {"paid": True}})
    bot.send_message(msg.from_user.id, "✅ VIP activated!")

if __name__ == "main":
    print("Bot running...")
    bot.infinity_polling(skip_pending=True)