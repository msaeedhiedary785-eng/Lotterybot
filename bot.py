import json
import os
import random
import requests
import telebot
from flask import Flask
from threading import Thread
import time

TOKEN = '8734549948:AAG1q3YsKwHdafTA-QQRdt6cZ82yGIVExps'
bot = telebot.TeleBot(TOKEN)

app = Flask('')


@app.route('/')
def home():
  return 'Bot is active and running!'


def run_web():
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


def self_ping():
  time.sleep(10)
  app_url = os.environ.get('RENDER_EXTERNAL_URL')
  if app_url:
    while True:
      try:
        requests.get(app_url)
      except:
        pass
      time.sleep(300)


# آیدی عددی شما:
MAIN_OWNER_ID = 7351850953

ADMINS_FILE = 'admins.json'


def load_admins():
  if os.path.exists(ADMINS_FILE):
    try:
      with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
        return set(json.load(f))
    except:
      return {MAIN_OWNER_ID}
  return {MAIN_OWNER_ID}


def save_admins(admins_set):
  with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
    json.dump(list(admins_set), f)


admins_list = load_admins()
admins_list.add(MAIN_OWNER_ID)
save_admins(admins_list)


def is_admin(user_id):
  return user_id in admins_list or user_id == MAIN_OWNER_ID


# --- دستورات مدیریت ادمین‌ها (فقط توسط مالک اصلی) ---


@bot.message_handler(commands=['addadmin'])
def add_admin(message):
  if message.from_user.id != MAIN_OWNER_ID:
    bot.reply_to(message, '⛔️ این دستور فقط مخصوص مالک اصلی ربات است!')
    return

  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit():
    bot.reply_to(
        message,
        '⚠️ لطفاً آیدی عددی شخص را وارد کنید.\nمثال:\n`/addadmin 987654321`',
        parse_mode='Markdown',
    )
    return

  new_admin_id = int(args[1])
  admins_list.add(new_admin_id)
  save_admins(admins_list)
  bot.reply_to(
      message,
      f'✅ کاربر با آیدی `{new_admin_id}` به لیست ادمین‌ها اضافه شد!',
      parse_mode='Markdown',
  )


@bot.message_handler(commands=['deladmin'])
def delete_admin(message):
  if message.from_user.id != MAIN_OWNER_ID:
    bot.reply_to(message, '⛔️ این دستور فقط مخصوص مالک اصلی ربات است!')
    return

  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit():
    bot.reply_to(
        message,
        '⚠️ لطفاً آیدی عددی شخص را وارد کنید.\nمثال:\n`/deladmin 987654321`',
        parse_mode='Markdown',
    )
    return

  target_id = int(args[1])
  if target_id == MAIN_OWNER_ID:
    bot.reply_to(message, '⛔️ نمی‌توانید مالک اصلی را حذف کنید!')
    return

  if target_id in admins_list:
    admins_list.remove(target_id)
    save_admins(admins_list)
    bot.reply_to(
        message,
        f'🗑 کاربر با آیدی `{target_id}` از لیست ادمین‌ها حذف شد.',
        parse_mode='Markdown',
    )
  else:
    bot.reply_to(message, 'ℹ️ این کاربر جزو ادمین‌ها نبود.')


@bot.message_handler(commands=['admins'])
def list_admins(message):
  if not is_admin(message.from_user.id):
    return
  text = '📋 **لیست ادمین‌های ربات:**\n' + '\n'.join([
      f'- `{uid}`' + (' (مالک)' if uid == MAIN_OWNER_ID else '')
      for uid in admins_list
  ])
  bot.reply_to(message, text, parse_mode='Markdown')


# --- بخش قرعه‌کشی ---

lottery_pools = {}


@bot.message_handler(commands=['setup', 'شروع'])
def setup_lottery(message):
  if not is_admin(message.from_user.id):
    bot.reply_to(message, '⛔️ شما اجازه استفاده از این دستور را ندارید!')
    return

  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit():
    bot.reply_to(
        message,
        (
            '⚠️ لطفاً عدد آخر را بعد از دستور وارد کنید.\nمثال:\n`/setup 25`'
            ' (یعنی از ۱ تا ۲۵)'
        ),
        parse_mode='Markdown',
    )
    return

  count = int(args[1])
  chat_id = message.chat.id
  lottery_pools[chat_id] = list(range(1, count + 1))

  bot.reply_to(
      message,
      (
          f'✅ لیست قرعه‌کشی از **۱ تا {count}** آماده شد!\nحالا با دستور'
          ' `/draw` یا `/قرعه` شماره بکشید.'
      ),
      parse_mode='Markdown',
  )


@bot.message_handler(commands=['draw', 'قرعه'])
def draw_number(message):
  if not is_admin(message.from_user.id):
    bot.reply_to(message, '⛔️ شما اجازه استفاده از این دستور را ندارید!')
    return

  chat_id = message.chat.id

  if chat_id not in lottery_pools or not lottery_pools[chat_id]:
    bot.reply_to(
        message,
        '⚠️ اول باید لیست رو مقداردهی کنی!\nمثال:\n`/setup 25`',
        parse_mode='Markdown',
    )
    return

  pool = lottery_pools[chat_id]
  chosen = random.choice(pool)
  pool.remove(chosen)

  bot.reply_to(
      message,
      (
          f'🎉 عدد برنده: **{chosen}**\n\nتعداد اعداد باقی‌مانده:'
          f' {len(pool)}'
      ),
      parse_mode='Markdown',
  )


if __name__ == '__main__':
  keep_alive()
  t_ping = Thread(target=self_ping)
  t_ping.start()

  bot.infinity_polling()
