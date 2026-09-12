import os
import random
import time
import requests
import telebot
from telebot.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = os.environ.get("BOT_TOKEN", "8877841915:AAG_oHSiHtTeQJNdLtnXLQ9SlgopZYXLYlA")

bot = telebot.TeleBot(TOKEN)

warns_db = {}     
captcha_db = {}   

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

@bot.message_handler(content_types=['new_chat_members'])
def on_new_members(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            bot.send_message(
                message.chat.id,
                "👋 **Salam herkese!**\n\n"
                "⚠️ Botyň doly işlemegi üçin **boty toparda ADMIN ediň**!\n"
                "💡 *Kurslary bilmek üçin `kurs` ýa-da `/crypto` ýazyň.*",
                parse_mode="Markdown"
            )
            continue

        if member.is_bot:
            continue

        try:
            bot.restrict_chat_member(
                message.chat.id,
                member.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception:
            pass

        num1, num2 = random.randint(1, 10), random.randint(1, 10)
        correct_answer = num1 + num2
        captcha_db[member.id] = {"answer": correct_answer, "chat_id": message.chat.id}

        options = [correct_answer, correct_answer + random.randint(1, 3), max(1, correct_answer - random.randint(1, 3))]
        random.shuffle(options)

        markup = InlineKeyboardMarkup()
        for opt in options:
            markup.add(InlineKeyboardButton(text=str(opt), callback_data=f"cap_{member.id}_{opt}"))

        bot.send_message(
            message.chat.id,
            f"👋 Salam [{member.first_name}](tg://user?id={member.id})!\n"
            f"Topara ýazmak üçin mysaly çözüň: **{num1} + {num2} = ?**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cap_"))
def handle_captcha(call):
    _, user_id_str, ans_str = call.data.split("_")
    user_id = int(user_id_str)
    ans = int(ans_str)

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Bu siz üçin däl!", show_alert=True)
        return

    data = captcha_db.get(user_id)
    if not data:
        bot.answer_callback_query(call.id, "❌ Möhlet ötdi.", show_alert=True)
        return

    if ans == data["answer"]:
        bot.restrict_chat_member(
            data["chat_id"],
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            )
        )
        bot.edit_message_text(f"✅ [{call.from_user.first_name}](tg://user?id={user_id}) Captcha geçdi!", data["chat_id"], call.message.message_id, parse_mode="Markdown")
        del captcha_db[user_id]
    else:
        bot.answer_callback_query(call.id, "❌ Nädogry!", show_alert=True)

@bot.message_handler(func=lambda m: m.text and ("kurs" in m.text.lower() or m.text.lower() in ["/crypto", "/kurs"]))
def send_crypto_rates(message):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,the-open-network,solana,binancecoin,tether&vs_currencies=usd"
        res = requests.get(url, timeout=5).json()

        btc = res.get('bitcoin', {}).get('usd', 0)
        eth = res.get('ethereum', {}).get('usd', 0)
        ton = res.get('the-open-network', {}).get('usd', 0)
        sol = res.get('solana', {}).get('usd', 0)
        bnb = res.get('binancecoin', {}).get('usd', 0)
        usdt = res.get('tether', {}).get('usd', 0)

        text = (
            "📊 **Hakyky Wagtda Kripto Kurslar:**\n\n"
            f"🪙 **Bitcoin (BTC):** ${btc:,.2f}\n"
            f"💎 **Ethereum (ETH):** ${eth:,.2f}\n"
            f"💎 **Toncoin (TON):** ${ton:,.2f}\n"
            f"⚡ **Solana (SOL):** ${sol:,.2f}\n"
            f"🟡 **BNB:** ${bnb:,.2f}\n"
            f"💵 **USD/USDT:** ${usdt:.2f}"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "❌ Kurslary alyp bolmady, täzeden synanyşyň.")

@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Ýazga Reply edip `/warn` ýazyň.")

    target = message.reply_to_message.from_user
    key = f"{message.chat.id}_{target.id}"
    warns_db[key] = warns_db.get(key, 0) + 1
    count = warns_db[key]

    if count >= 3:
        warns_db[key] = 0
        until = int(time.time()) + 86400  
        bot.restrict_chat_member(message.chat.id, target.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
        bot.send_message(message.chat.id, f"🚫 @{target.username or target.first_name} 3 warn aldy we **24 sagat Mute** edildi!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"⚠️ @{target.username or target.first_name} warn aldy! (**{count}/3**)", parse_mode="Markdown")

@bot.message_handler(commands=['unwarn'])
def unwarn_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply edip `/unwarn` ýazyň.")

    target = message.reply_to_message.from_user
    key = f"{message.chat.id}_{target.id}"
    if warns_db.get(key, 0) > 0:
        warns_db[key] -= 1
    bot.send_message(message.chat.id, f"✅ Warn aýryldy. Häzirki duýduryş: **{warns_db.get(key, 0)}/3**", parse_mode="Markdown")

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply edip `/mute` ýazyň.")

    target = message.reply_to_message.from_user
    until = int(time.time()) + 3600  
    bot.restrict_chat_member(message.chat.id, target.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
    bot.send_message(message.chat.id, f"🔇 @{target.username or target.first_name} 1 sagat Mute edildi.", parse_mode="Markdown")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply edip `/unmute` ýazyň.")

    target = message.reply_to_message.from_user
    bot.restrict_chat_member(message.chat.id, target.id, permissions=ChatPermissions(
        can_send_messages=True, can_send_media_messages=True,
        can_send_other_messages=True, can_add_web_page_previews=True
    ))
    bot.send_message(message.chat.id, f"🔊 @{target.username or target.first_name} Mute aýryldy.", parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply edip `/ban` ýazyň.")

    target = message.reply_to_message.from_user
    bot.ban_chat_member(message.chat.id, target.id)
    bot.send_message(message.chat.id, f"🚫 @{target.username or target.first_name} topardan banlandy!", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Diňe adminler üçin!")
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return bot.reply_to(message, "⚠️ `/unban USER_ID` diýip ID ýazyň.")

    user_id = int(args[1])
    bot.unban_chat_member(message.chat.id, user_id, only_if_banned=True)
    bot.reply_to(message, f"✅ ID `{user_id}` unban edildi.", parse_mode="Markdown")

print("Bot işläp başlady...")
bot.infinity_polling()
              
