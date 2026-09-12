import os
import threading
import time
import random
import requests
from flask import Flask
import telebot
from telebot import types

# 1. FLASK WEB SERWERI (Render-i oýa saklamak üçin)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 24/7 işläp dur!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. TELEGRAM BOT SAZLAMALARY
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable tapylmady!")

bot = telebot.TeleBot(TOKEN)

# Captcha üçin wagtlaýyn maglumatlar
user_captchas = {}
user_warns = {}

# --- BOT KOMANDALARY WE HANDLERLER ---

# /start komandasy
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Salam! Men toparyňyzy gözegçilikde saklaýan we "
        "kripto kurslaryny görkezýän bot.\n\n"
        "**Komandalar:**\n"
        "• `/crypto` ýa-da `kurs` - Kriptowalyuta kurslary\n"
        "• `/warn` - Agza duýduryş bermek (Admin)\n"
        "• `/mute` - Agzany dymdyrmak (Admin)\n"
        "• `/ban` - Agzany topardan çykarmak (Admin)"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# Kripto kurslaryny alyjy (CoinGecko API)
@bot.message_handler(commands=['crypto'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'kurs')
def get_crypto_prices(message):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,toncoin&vs_currencies=usd"
        res = requests.get(url, timeout=10).json()
        
        btc = res.get('bitcoin', {}).get('usd', 'N/A')
        eth = res.get('ethereum', {}).get('usd', 'N/A')
        bnb = res.get('binancecoin', {}).get('usd', 'N/A')
        ton = res.get('toncoin', {}).get('usd', 'N/A')

        text = (
            "📊 **Häzirki Kripto Kurslary:**\n\n"
            f"🪙 **Bitcoin (BTC):** ${btc}\n"
            f"💎 **Ethereum (ETH):** ${eth}\n"
            f"🟡 **Binance Coin (BNB):** ${bnb}\n"
            f"💎 **TON Coin (TON):** ${ton}"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Kurslary alyp bolmady, bir azdan gaýtadan synanyşyň.")

# --- CAPTCHA & TÄZE AGZALAR ---

@bot.message_handler(content_types=['new_chat_members'])
def welcome_and_captcha(message):
    for new_user in message.new_chat_members:
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        correct_answer = num1 + num2
        
        user_captchas[new_user.id] = correct_answer

        # Toparda ýazmak hukugyny wagtlaýyn çäklendirmek
        try:
            bot.restrict_chat_member(
                message.chat.id, 
                new_user.id, 
                until_date=time.time() + 300,
                can_send_messages=False
            )
        except Exception:
            pass

        markup = types.InlineKeyboardMarkup()
        # Ýalňyş we dogry jogap bar bolan düwmeler
        answers = [correct_answer, correct_answer + random.randint(1, 3), abs(correct_answer - random.randint(1, 2))]
        random.shuffle(answers)

        for ans in answers:
            markup.add(types.InlineKeyboardButton(text=str(ans), callback_data=f"captcha_{new_user.id}_{ans}"))

        bot.send_message(
            message.chat.id,
            f"Hoş geldiňiz [{new_user.first_name}](tg://user?id={new_user.id})!\n"
            f"Robot däldigiňizi tassyklaň: **{num1} + {num2} = ?**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("captcha_"))
def handle_captcha(call):
    _, user_id, user_answer = call.data.split("_")
    user_id = int(user_id)
    user_answer = int(user_answer)

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "Bu sorag size degişli däl!", show_alert=True)
        return

    if user_captchas.get(user_id) == user_answer:
        # Rugsat bermek
        bot.restrict_chat_member(
            call.message.chat.id, 
            user_id, 
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        bot.answer_callback_query(call.id, "Dogry! Indi habar ýazyp bilersiňiz.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        del user_captchas[user_id]
    else:
        bot.answer_callback_query(call.id, "Ýalňyş jogap! Gaýtadan synanyşyň.", show_alert=True)

# --- ADMIN KOMANDALARY (/warn, /mute, /ban) ---

def is_admin(chat_id, user_id):
    status = bot.get_chat_member(chat_id, user_id).status
    return status in ['administrator', 'creator']

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Duýduryş bermek üçin ulanyjynyň habaryna reply (jogap) ediň.")
        return

    target_user = message.reply_to_message.from_user
    user_warns[target_user.id] = user_warns.get(target_user.id, 0) + 1

    if user_warns[target_user.id] >= 3:
        bot.ban_chat_member(message.chat.id, target_user.id)
        bot.reply_to(message, f"🚫 {target_user.first_name} 3 gezek duýduryş alandygy üçin topardan çykaryldy!")
        user_warns[target_user.id] = 0
    else:
        bot.reply_to(message, f"⚠️ {target_user.first_name} duýduryş aldy! ({user_warns[target_user.id]}/3)")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Dymdyrmak üçin ulanyjynyň habaryna reply (jogap) ediň.")
        return

    target_user = message.reply_to_message.from_user
    bot.restrict_chat_member(message.chat.id, target_user.id, until_date=time.time() + 3600, can_send_messages=False)
    bot.reply_to(message, f"🔇 {target_user.first_name} 1 sagat möhlet bilen dymdyryldy.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, "Ban etmek üçin ulanyjynyň habaryna reply (jogap) ediň.")
        return

    target_user = message.reply_to_message.from_user
    bot.ban_chat_member(message.chat.id, target_user.id)
    bot.reply_to(message, f"🚫 {target_user.first_name} topardan çykaryldy.")

# --- MODERASIÝA (Link pozmak) ---

@bot.message_handler(func=lambda m: m.text and ("t.me/" in m.text or "http" in m.text or "https://" in m.text))
def delete_links(message):
    if not is_admin(message.chat.id, message.from_user.id):
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name}, toparda ssylka paýlaşmak gadagan!")
        except Exception:
            pass

# 3. ISHLETMEDIKI AKYM (Threading & Clean Polling)
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot.remove_webhook()
    time.sleep(1)

    print("Bot işläp başlady...")
    bot.infinity_polling(skip_pending_updates=True)
      
