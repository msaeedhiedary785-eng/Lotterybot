import json
import os
import random
import requests
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import time

TOKEN = '8734549948:AAG1q3YsKwHdafTA-QQRdt6cZ82yGIVExps'
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

def self_ping():
    time.sleep(10)
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if app_url:
        while True:
            try:
                requests.get(app_url)
            except:
                pass
            time.sleep(300)

MAIN_OWNER_ID = 7351850953

# دیکشنری برای ذخیره وضعیت قرعه‌کشی هر کاربر
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🎲 قرعه کشی", callback_data="start_lottery")
    markup.add(btn)
    bot.send_message(
        message.chat.id,
        "✨ خوش اومدی به ربات قرعه کشی مشهد استار",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "start_lottery")
def ask_max_number(call):
    markup = types.InlineKeyboardMarkup(row_width=3)
    # گزینه‌های سقف قرعه‌کشی (مثلا ۲۵، ۵۰، ۱۰۰)
    buttons = [
        types.InlineKeyboardButton("۲۵ تایی (۱ تا ۲۵)", callback_data="max_25"),
        types.InlineKeyboardButton("۵۰ تایی (۱ تا ۵۰)", callback_data="max_50"),
        types.InlineKeyboardButton("۱۰۰ تایی (۱ تا ۱۰۰)", callback_data="max_100")
    ]
    markup.add(*buttons)
    bot.edit_message_text(
        "عدد سقف قرعه‌کشی را انتخاب کن (مثلاً از ۱ تا چند):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("max_"))
def ask_draw_count(call):
    max_num = int(call.data.split("_")[1])
    user_data[call.message.chat.id] = {"max_num": max_num}

    markup = types.InlineKeyboardMarkup(row_width=5)
    # تعداد دفعات قرعه‌کشی (مثلا ۱ تا ۱۰ یا بیشتر)
    count_buttons = [
        types.InlineKeyboardButton(str(i), callback_data=f"count_{i}")
        for i in range(1, 11)
    ]
    markup.add(*count_buttons)
    
    # دکمه‌های بیشتر برای تعداد دفعات (مثلا ۱۵، ۲۰، ۲۵، ۳۰)
    extra_counts = [12, 15, 20, 25, 30]
    extra_buttons = [
        types.InlineKeyboardButton(f"{c} بار", callback_data=f"count_{c}")
        for c in extra_counts
    ]
    markup.add(*extra_buttons)

    bot.edit_message_text(
        f"سقف قرعه‌کشی: ۱ تا {max_num}\nحالا تعداد دفعات قرعه‌کشی را انتخاب کن:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("count_"))
def start_draw_process(call):
    count = int(call.data.split("_")[1])
    chat_id = call.message.chat.id
    
    if chat_id not in user_data:
        user_data[chat_id] = {"max_num": 25}
    
    max_num = user_data[chat_id].get("max_num", 25)
    pool = list(range(1, max_num + 1))
    random.shuffle(pool)

    drawn = pool.pop(0)
    user_data[chat_id] = {
        "max_num": max_num,
        "total_count": count,
        "remaining_count": count - 1,
        "pool": pool,
        "drawn_list": [drawn]
    }

    markup = types.InlineKeyboardMarkup()
    if count - 1 > 0:
        btn = types.InlineKeyboardButton("🔄 قرعه بعدی", callback_data="next_draw")
        markup.add(btn)
    else:
        # اگر فقط ۱ بار بود
        markup = get_finished_markup()

    text = (
        f"🎉 **قرعه شماره ۱:**\n\n"
        f"عدد برنده: **{drawn}**\n\n"
        f"باقیمانده قرعه‌ها: {count - 1}"
    )

    bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "next_draw")
def next_draw_callback(call):
    chat_id = call.message.chat.id
    data = user_data.get(chat_id)

    if not data or not data.get("pool") or data.get("remaining_count", 0) <= 0:
        bot.answer_callback_query(call.id, "قرعه‌کشی به پایان رسیده است!")
        return

    pool = data["pool"]
    drawn = pool.pop(0)
    data["remaining_count"] -= 1
    data["drawn_list"].append(drawn)

    current_step = data["total_count"] - data["remaining_count"]

    if data["remaining_count"] > 0:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("🔄 قرعه بعدی", callback_data="next_draw")
        markup.add(btn)
        
        all_drawn_str = ", ".join(map(str, data["drawn_list"]))
        text = (
            f"🎉 **قرعه شماره {current_step}:**\n\n"
            f"عدد برنده جدید: **{drawn}**\n\n"
            f"📋 لیست برنده‌ها تا اینجا: {all_drawn_str}\n"
            f"⏳ دفعات باقی‌مانده: {data['remaining_count']}"
        )
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        # تمام شد
        markup = get_finished_markup()
        all_drawn_str = ", ".join(map(str, data["drawn_list"]))
        text = (
            f"🏁 **پایان قرعه کشی!**\n\n"
            f"تمام {data['total_count']} عدد انجام شد.\n"
            f"🏆 **اعداد برنده نهایی:** {all_drawn_str}"
        )
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

def get_finished_markup():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🎲 قرعه کشی مجدد", callback_data="start_lottery")
    markup.add(btn)
    return markup

if __name__ == '__main__':
    keep_alive()
    t_ping = Thread(target=self_ping)
    t_ping.start()

    bot.infinity_polling()
