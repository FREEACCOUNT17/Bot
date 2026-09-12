import os
import threading
import time
import random
import requests
from flask import Flask
import telebot
from telebot import types

# 1. FLASK WEB SERWERI
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

# Wagtlaýyn maglumat bazalary
user_captchas = {}
user_warns = {}
user_languages = {}

# Diller boýunça tekstler
TEXTS = {
    'tk': {
        'welcome': "Salam! Men toparyňyzy gözegçilikde saklaýan we kripto kurslaryny görkezýän bot.\n\n"
                   "Dil üýtgetmek üçin: /lang\n"
                   "Komandalar sanawyny görmek üçin / basyň.",
        'add_to_group': "➕ Topara goşmak",
        'select_lang': "Lütfen dil saýlaň / Dili tanlang:",
        'lang_set': "Dil Türkmen diline üýtgedildi! 🇹🇲",
        'crypto_title': "🤝 **P2P Real El Bahalary (USDT / Crypto):**\n\n",
        'crypto_err': "⚠️ Kurslary alyp bolmady, bir azdan gaýtadan synanyşyň.",
        'reply_req': "Bu komandany ulanmak üçin ulanyjynyň habaryna reply (jogap) ediň.",
        'warn_msg': "⚠️ {name} duýduryş aldy! ({warns}/3)",
        'warn_ban': "🚫 {name} 3 gezek duýduryş alandygy üçin topardan çykaryldy!",
        'mute_msg': "🔇 {name} 1 sagat möhlet bilen dymdyryldy.",
        'unmute_btn': "🔊 Mute-dan çykarmak",
        'unmute_msg': "🔊 {name} dymdyrmadan çykaryldy!",
        'ban_msg': "🚫 {name} topardan çykaryldy.",
        'link_warn': "⚠️ {name}, toparda ssylka paýlaşmak gadagan!",
        'captcha_text': "Hoş geldiňiz [{name}](tg://user?id={id})!\nRobot däldigiňizi tassyklaň: **{n1} + {n2} = ?**",
        'captcha_ok': "Dogry! Indi habar ýazyp bilersiňiz.",
        'captcha_err': "Ýalňyş jogap! Gaýtadan synanyşyň."
    },
    'uz': {
        'welcome': "Salom! Men guruhingizni nazorat qiluvchi va kripto kurslarini ko'rsatuvchi botman.\n\n"
                   "Tilni o'zgartirish uchun: /lang\n"
                   "Buyruqlar ro'yxatini ko'rish uchun / bosing.",
        'add_to_group': "➕ Guruhga qo'shish",
        'select_lang': "Lütfen dil saýlaň / Dili tanlang:",
        'lang_set': "Til O'zbek tiliga o'zgartirildi! 🇺🇿",
        'crypto_title': "🤝 **P2P Real Bozor Narxlari (USDT / Crypto):**\n\n",
        'crypto_err': "⚠️ Kurslarni olib bo'lmadi, birozdan so'ng qayta urinib ko'ring.",
        'reply_req': "Bu buyruqni ishlatish uchun foydalanuvchi xabariga reply (javob) bering.",
        'warn_msg': "⚠️ {name} ogohlantirish oldi! ({warns}/3)",
        'warn_ban': "🚫 {name} 3 marta ogohlantirish olgani uchun guruhdan chiqarildi!",
        'mute_msg': "🔇 {name} 1 soatga ovozsiz rejimga o'tkazildi.",
        'unmute_btn': "🔊 Ovozni yoqish (Unmute)",
        'unmute_msg': "🔊 {name} ovozsiz rejimdan chiqarildi!",
        'ban_msg': "🚫 {name} guruhdan chiqarildi.",
        'link_warn': "⚠️ {name}, guruhda havola (link) ulashish taqiqlangan!",
        'captcha_text': "Xush kelibsiz [{name}](tg://user?id={id})!\nRobot emasligingizni tasdiqlang: **{n1} + {n2} = ?**",
        'captcha_ok': "To'g'ri! Endi xabar yozishingiz mumkin.",
        'captcha_err': "Noto'g'ri javob! Qayta urinib ko'ring."
    }
}

def get_txt(chat_id, key):
    lang = user_languages.get(chat_id, 'tk')
    return TEXTS[lang].get(key, TEXTS['tk'][key])

def is_admin(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['administrator', 'creator']
    except Exception:
        return False

def setup_bot_commands():
    commands = [
        telebot.types.BotCommand("start", "Boty işe düşürmek"),
        telebot.types.BotCommand("lang", "Dil saýlamak / Tilni tanlash"),
        telebot.types.BotCommand("crypto", "P2P El bahalary / Bozor narxlari"),
        telebot.types.BotCommand("warn", "Duýduryş bermek (Admin)"),
        telebot.types.BotCommand("mute", "Dymdyrmak (Admin)"),
        telebot.types.BotCommand("unmute", "Dymdyrmadan çykarmak (Admin)"),
        telebot.types.BotCommand("ban", "Topardan çykarmak (Admin)")
    ]
    bot.set_my_commands(commands)

# --- HANDLERLER ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot_username = bot.get_me().username
    markup = types.InlineKeyboardMarkup()
    add_btn = types.InlineKeyboardButton(
        text=get_txt(message.chat.id, 'add_to_group'), 
        url=f"https://t.me/{bot_username}?startgroup=true"
    )
    markup.add(add_btn)
    bot.reply_to(message, get_txt(message.chat.id, 'welcome'), reply_markup=markup)

@bot.message_handler(commands=['lang'])
def select_language(message):
    markup = types.InlineKeyboardMarkup()
    btn_tk = types.InlineKeyboardButton("🇹🇲 Türkmençe", callback_data="setlang_tk")
    btn_uz = types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz")
    markup.add(btn_tk, btn_uz)
    bot.send_message(message.chat.id, get_txt(message.chat.id, 'select_lang'), reply_markup=markup)

@bot.message_handler(commands=['crypto'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['kurs', 'crypto'])
def get_crypto_prices(message):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,toncoin,tether&vs_currencies=usd"
        res = requests.get(url, timeout=10).json()
        
        btc = res.get('bitcoin', {}).get('usd', 'N/A')
        eth = res.get('ethereum', {}).get('usd', 'N/A')
        bnb = res.get('binancecoin', {}).get('usd', 'N/A')
        ton = res.get('toncoin', {}).get('usd', 'N/A')
        usdt = res.get('tether', {}).get('usd', '1.00')

        text = (
            get_txt(message.chat.id, 'crypto_title') +
            f"💵 **USDT (P2P El Baha):** ${usdt}\n"
            f"🪙 **Bitcoin (BTC):** ${btc}\n"
            f"💎 **Ethereum (ETH):** ${eth}\n"
            f"🟡 **Binance Coin (BNB):** ${bnb}\n"
            f"💎 **TON Coin (TON):** ${ton}\n\n"
            f"💡 *Bahalar P2P (elme-el/bazar) söwdasy boýunça düzülen.*"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, get_txt(message.chat.id, 'crypto_err'))

# --- ADMIN MODERASIÝA KOMANDALARY ---

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, get_txt(message.chat.id, 'reply_req'))
        return

    target_user = message.reply_to_message.from_user
    user_warns[target_user.id] = user_warns.get(target_user.id, 0) + 1

    if user_warns[target_user.id] >= 3:
        bot.ban_chat_member(message.chat.id, target_user.id)
        msg = get_txt(message.chat.id, 'warn_ban').format(name=target_user.first_name)
        bot.reply_to(message, msg)
        user_warns[target_user.id] = 0
    else:
        msg = get_txt(message.chat.id, 'warn_msg').format(name=target_user.first_name, warns=user_warns[target_user.id])
        bot.reply_to(message, msg)

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, get_txt(message.chat.id, 'reply_req'))
        return

    target_user = message.reply_to_message.from_user
    bot.restrict_chat_member(message.chat.id, target_user.id, until_date=time.time() + 3600, can_send_messages=False)
    
    markup = types.InlineKeyboardMarkup()
    unmute_btn = types.InlineKeyboardButton(
        text=get_txt(message.chat.id, 'unmute_btn'), 
        callback_data=f"unmute_{target_user.id}"
    )
    markup.add(unmute_btn)

    msg = get_txt(message.chat.id, 'mute_msg').format(name=target_user.first_name)
    bot.reply_to(message, msg, reply_markup=markup)

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, get_txt(message.chat.id, 'reply_req'))
        return

    target_user = message.reply_to_message.from_user
    bot.restrict_chat_member(
        message.chat.id, target_user.id,
        can_send_messages=True, can_send_media_messages=True,
        can_send_other_messages=True, can_add_web_page_previews=True
    )
    msg = get_txt(message.chat.id, 'unmute_msg').format(name=target_user.first_name)
    bot.reply_to(message, msg)

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, get_txt(message.chat.id, 'reply_req'))
        return

    target_user = message.reply_to_message.from_user
    bot.ban_chat_member(message.chat.id, target_user.id)
    msg = get_txt(message.chat.id, 'ban_msg').format(name=target_user.first_name)
    bot.reply_to(message, msg)

# --- ALL CALLBACK QUERY HANDLER (Dil Saýlamak, Unmute, Captcha) ---

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    if call.data.startswith("setlang_"):
        lang_code = call.data.split("_")[1]
        user_languages[call.message.chat.id] = lang_code
        bot.answer_callback_query(call.id, "Üýtgedildi!")
        bot.edit_message_text(
            get_txt(call.message.chat.id, 'lang_set'),
            call.message.chat.id,
            call.message.message_id
        )

    elif call.data.startswith("unmute_"):
        if not is_admin(call.message.chat.id, call.from_user.id):
            bot.answer_callback_query(call.id, "Diňe adminler üçin!", show_alert=True)
            return

        target_user_id = int(call.data.split("_")[1])
        bot.restrict_chat_member(
            call.message.chat.id, target_user_id,
            can_send_messages=True, can_send_media_messages=True,
            can_send_other_messages=True, can_add_web_page_previews=True
        )
        bot.answer_callback_query(call.id, "Unmuted!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    elif call.data.startswith("captcha_"):
        _, user_id, user_answer = call.data.split("_")
        user_id = int(user_id)
        user_answer = int(user_answer)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "Bu sorag size degişli däl!", show_alert=True)
            return

        if user_captchas.get(user_id) == user_answer:
            bot.restrict_chat_member(
                call.message.chat.id, user_id,
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            )
            bot.answer_callback_query(call.id, get_txt(call.message.chat.id, 'captcha_ok'))
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            del user_captchas[user_id]
        else:
            bot.answer_callback_query(call.id, get_txt(call.message.chat.id, 'captcha_err'), show_alert=True)

# --- CAPTCHA & SSYLKA FINIKASY ---

@bot.message_handler(content_types=['new_chat_members'])
def welcome_and_captcha(message):
    for new_user in message.new_chat_members:
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        correct_answer = num1 + num2
        user_captchas[new_user.id] = correct_answer

        try:
            bot.restrict_chat_member(message.chat.id, new_user.id, until_date=time.time() + 300, can_send_messages=False)
        except Exception:
            pass

        markup = types.InlineKeyboardMarkup()
        answers = [correct_answer, correct_answer + random.randint(1, 3), abs(correct_answer - random.randint(1, 2))]
        random.shuffle(answers)

        for ans in answers:
            markup.add(types.InlineKeyboardButton(text=str(ans), callback_data=f"captcha_{new_user.id}_{ans}"))

        text = get_txt(message.chat.id, 'captcha_text').format(
            name=new_user.first_name, id=new_user.id, n1=num1, n2=num2
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and ("t.me/" in m.text or "http" in m.text or "https://" in m.text))
def delete_links(message):
    if not is_admin(message.chat.id, message.from_user.id):
        try:
            bot.delete_message(message.chat.id, message.message_id)
            msg = get_txt(message.chat.id, 'link_warn').format(name=message.from_user.first_name)
            bot.send_message(message.chat.id, msg)
        except Exception:
            pass

# 3. ISHLETMEDIKI AKYM
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(2)
        setup_bot_commands()
    except Exception as e:
        print(f"Sazlamalar ýerine ýetirilmedi: {e}")

    print("Bot işläp başlady...")
    bot.infinity_polling(timeout=20)
