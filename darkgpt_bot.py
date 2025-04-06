import telebot
from telebot import types
import json
import os
import time
from threading import Thread
import requests
from datetime import datetime, timezone
from flask import Flask, request

# --- CONFIG ---
TELEGRAM_TOKEN = "7795830648:AAFIUU0SG25DqYP23JCnLZGIbbddNCWMJnw"
OPENROUTER_API_KEY = "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"
BOT_USERNAME = "darkgptx_bot"
CHANNEL_ID = -1002407177775
ADMIN_IDS = ["7305585735"]
CREDITS_FILE = "darkgpt_credits.json"
PARRAINAGE_FILE = "darkgpt_parrainages.json"
NOWPAYMENTS_API_KEY = "D2ZNSV1-71542M0-K6STZ24-S92PPE1"
NOWPAYMENTS_IPN_SECRET = "ivz9lIews8G4eeccD/G1VG9ZlH8Duiu4"
NOWPAYMENTS_WEBHOOK = "https://travisio.pythonanywhere.com/nowpayments"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://darkgpt-site.onrender.com")

OFFRE_LANCEMENT_ACTIVE = True
PRIX_PREMIUM = 25
CREDITS_GRATUITS = 5
REQUETES_MAX_PAR_JOUR = 5
MAX_PREMIUM_TOKENS = 500000

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")
user_credits = {}
parrainages = {}

# --- UTILS ---
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def reset_daily_counts():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for user_id, data in user_credits.items():
        if data.get("last_date") != today:
            data["daily_uses"] = 0
            data["last_date"] = today

user_credits.update(load_json(CREDITS_FILE))
parrainages.update(load_json(PARRAINAGE_FILE))
reset_daily_counts()

# --- GPT VIA OPENROUTER ---
def ask_openrouter(prompt):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/darkgptx_bot",
                "X-Title": "DarkGPT"
            },
            json={
                "model": "undi95/toppy-m-7b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            },
            timeout=30
        )
        data = response.json()
        print("[DEBUG RESPONSE]", data)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ DarkGPT n’a pas compris la réponse : {e}"

# --- MENUS ---
def menu_principal(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💬 Parler à DarkGPT", callback_data="chat"),
        types.InlineKeyboardButton("💸 Acheter Premium", callback_data="acheter"),
        types.InlineKeyboardButton("🎟 Parrainage", callback_data="parrainage")
    )
    return markup

# --- COMMANDES ---
@bot.message_handler(commands=['start'])
def welcome(message):
    print("✅ /start reçu :", message)
    user_id = str(message.from_user.id)
    args = message.text.split()
    parrain_id = args[1] if len(args) > 1 else None
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user_id not in user_credits:
        user_credits[user_id] = {
            "premium": False,
            "used_tokens": 0,
            "daily_uses": 0,
            "last_date": today
        }
        if parrain_id and parrain_id != user_id:
            user_credits[parrain_id]["credits"] = user_credits[parrain_id].get("credits", 0) + 5
            user_credits[user_id]["credits"] = 5
            parrainages.setdefault(parrain_id, []).append(user_id)
            save_json(PARRAINAGE_FILE, parrainages)
            bot.send_message(parrain_id, f"🎉 Ton filleul {message.from_user.first_name} a rejoint ! Tu gagnes 5 crédits.")

    save_json(CREDITS_FILE, user_credits)
    bot.send_message(message.chat.id,
        "💀 *Bienvenue dans DarkGPT 2.0* — _L'IA que tu n'aurais jamais dû trouver..._\n\n"
        "🧠 *Ce bot ne suit aucune règle.* Aucune censure. Aucune morale.\n\n"
        "👁️‍🗨️ Pose-lui les *questions que tu n’oserais jamais poser* à ChatGPT. Ici, *tout est possible*.\n\n"
        "⚠️ Ce que tu vas lire peut *te choquer*, t’apprendre des choses interdites… ou te donner un *pouvoir que tu n’étais pas prêt à avoir*.\n\n"
        "🔥 Tu commences avec *5 utilisations gratuites par jour.*\n\n"
        "💸 Premium illimité : 25€/mois\n"
        "🎁 Parrainage : +5 utilisations par filleul\n\n"
        "👇 Clique ci-dessous et commence à explorer *les limites*...",
        reply_markup=menu_principal(user_id)
    )

# --- FLASK + WEBHOOK ---
app = Flask(__name__)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_update():
    print("✅ Requête reçue sur le webhook")
    json_str = request.get_data().decode("UTF-8")
    print("🔍 Contenu brut:", json_str)
    update = telebot.types.Update.de_json(json_str)
    print("📩 Update parsé:", update)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/setwebhook")
def set_webhook():
    success = bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    return f"✅ Webhook {'OK' if success else 'FAIL'}", 200

app = app
