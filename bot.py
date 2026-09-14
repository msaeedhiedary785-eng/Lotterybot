import json
import os
import random
import requests
import telebot
from telebot import types
from flask import Flask
from threading import Thread
import time

TOKEN = '8734549948:AAG8XuP5fWTa1oGHt4QYrP49i_VYx9iXYSk'
bot = telebot.TeleBot(TOKEN)

# آیدی عددی صاحب اصلی ربات خودتان را اینجا بگذارید (اگر 7351850953 آیدی خودتان نیست، با آیدی عددی واقعی خودتان عوض کنید):
MAIN_OWNER_ID = 7351850953

# مجموعه‌ای برای ذخیره یوزرنیم‌های ادمین (با حروف کوچک و بدون @)
admins_usernames = set()

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


# ذخیره وضعیت مکالمه‌ی هر کاربر
user_state = {}


def is_authorized(user_id, username):
  if user_id == MAIN_OWNER_ID:
    return True
  if username and username.lower() in admins_usernames:
    return True
  return False


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
  chat_id = message.chat.id
  # پاک کردن وضعیت قبلی کاربر هنگام زدن استارت مجدد
  user_state.pop(chat_id, None)

  markup = types.InlineKeyboardMarkup()
  btn = types.InlineKeyboardButton(
      '🎲 قرعه کشی', callback_data='start_lottery'
  )
  markup.add(btn)

  # نمایش دکمه‌های افزودن و حذف ادمین فقط برای صاحب اصلی ربات
  if message.from_user.id == MAIN_OWNER_ID:
    btn_add_admin = types.InlineKeyboardButton(
        '➕ افزودن ادمین', callback_data='add_admin'
    )
    btn_del_admin = types.InlineKeyboardButton(
        '➖ حذف ادمین', callback_data='del_admin'
    )
    markup.add(btn_add_admin, btn_del_admin)

  bot.send_message(
      chat_id,
      '✨ خوش اومدی به ربات قرعه کشی مشهد استار\nلطفاً یکی از گزینه‌های زیر را انتخاب کن:',
      reply_markup=markup,
  )


@bot.callback_query_handler(func=lambda call: call.data == 'add_admin')
def add_admin_callback(call):
  if call.from_user.id != MAIN_OWNER_ID:
    bot.answer_callback_query(call.id, '⛔️ این گزینه فقط برای صاحب ربات است!')
    return

  chat_id = call.message.chat.id
  user_state[chat_id] = {'step': 'waiting_new_admin_username'}
  bot.send_message(
      chat_id,
      '✍️ لطفاً آیدی ادمین جدید را با علامت @ بفرست (مثلاً: `@username`):',
  )


@bot.callback_query_handler(func=lambda call: call.data == 'del_admin')
def del_admin_callback(call):
  if call.from_user.id != MAIN_OWNER_ID:
    bot.answer_callback_query(call.id, '⛔️ این گزینه فقط برای صاحب ربات است!')
    return

  if not admins_usernames:
    bot.answer_callback_query(
        call.id, 'هیچ ادمینی تا حالا ثبت نشده است!', show_alert=True
    )
    return

  markup = types.InlineKeyboardMarkup(row_width=1)
  for uname in admins_usernames:
    btn = types.InlineKeyboardButton(
        f'❌ حذف @{uname}', callback_data=f'remove_admin_{uname}'
    )
    markup.add(btn)

  bot.send_message(
      call.message.chat.id,
      '📋 لیست مدیران فعلی:\nروی یوزرنیم مورد نظر برای حذف کلیک کن:',
      reply_markup=markup,
  )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('remove_admin_')
)
def remove_admin_handler(call):
  if call.from_user.id != MAIN_OWNER_ID:
    bot.answer_callback_query(call.id, '⛔️ این گزینه فقط برای صاحب ربات است!')
    return

  uname = call.data.replace('remove_admin_', '')
  if uname in admins_usernames:
    admins_usernames.remove(uname)
    bot.answer_callback_query(
        call.id, f'@{uname} از لیست ادمین‌ها حذف شد.', show_alert=True
    )
    bot.edit_message_text(
        f'✅ ادمین `@{uname}` با موفقیت از لیست حذف شد.',
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='Markdown',
    )
  else:
    bot.answer_callback_query(call.id, 'این یوزرنیم در لیست یافت نشد.', show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == 'start_lottery')
def ask_total_persons(call):
  user_id = call.from_user.id
  username = call.from_user.username

  if not is_authorized(user_id, username):
    bot.answer_callback_query(
        call.id,
        '⛔️ شما اجازه استفاده از این ربات را ندارید!',
        show_alert=True,
    )
    return

  chat_id = call.message.chat.id
  user_state[chat_id] = {'step': 'waiting_max_num'}
  bot.send_message(
      chat_id,
      '✍️ لطفاً تعداد کل افراد قرعه‌کشی را وارد کن (مثلاً ۲۵ تا خودش بفهمد از ۱ تا ۲۵ است):',
  )


@bot.message_handler(func=lambda message: True)
def handle_text_input(message):
  chat_id = message.chat.id
  text = message.text.strip()
  user_id = message.from_user.id
  username = message.from_user.username

  if chat_id not in user_state:
    bot.send_message(
        chat_id, '⚠️ لطفاً ابتدا دستور /start را بزنید و از منو استفاده کنید.'
    )
    return

  state = user_state[chat_id]
  current_step = state.get('step')

  # دریافت یوزرنیم ادمین جدید
  if current_step == 'waiting_new_admin_username':
    if user_id != MAIN_OWNER_ID:
      return

    clean_username = text.lstrip('@').lower()
    if clean_username:
      admins_usernames.add(clean_username)
      user_state.pop(chat_id, None)
      bot.send_message(
          chat_id,
          f'✅ ادمین جدید با یوزرنیم `@{clean_username}` با موفقیت اضافه شد و حالا می‌تواند از ربات استفاده کند.',
          parse_mode='Markdown',
      )
    else:
      bot.send_message(
          chat_id,
          '⚠️ لطفاً یک یوزرنیم معتبر همراه با @ وارد کن (مثلا @my_admin):',
      )
    return

  # بررسی اینکه کاربر مجوز استفاده دارد یا خیر
  if not is_authorized(user_id, username):
    return

  # مرحله ۱: دریافت تعداد کل افراد (مثلا ۲۵ -> یعنی ۱ تا ۲۵)
  if current_step == 'waiting_max_num':
    if text.isdigit() and int(text) > 0:
      max_num = int(text)
      user_state[chat_id] = {'step': 'waiting_draw_count', 'max_num': max_num}
      bot.send_message(
          chat_id,
          f'✅ بازه قرعه‌کشی از ۱ تا {max_num} ثبت شد (بدون اعداد تکراری).\n\n✍️ حالا تعداد دفعات قرعه‌کشی را بنویس (مثلاً ۵ بار یا ۷ بار):',
      )
    else:
      bot.send_message(
          chat_id, '⚠️ لطفاً فقط یک عدد صحیح و بزرگ‌تر از صفر وارد کن:'
      )

  # مرحله ۲: دریافت تعداد دفعات قرعه‌کشی (مثلا ۵ بار)
  elif current_step == 'waiting_draw_count':
    if text.isdigit() and int(text) > 0:
      count = int(text)
      max_num = state['max_num']

      if count > max_num:
        bot.send_message(
            chat_id,
            f'⚠️ تعداد دفعات قرعه‌کشی ({count}) نمی‌تواند بیشتر از تعداد کل افراد ({max_num}) باشد. لطفاً عدد کوچک‌تر یا مساوی وارد کن:',
        )
        return

      # ساخت لیست اعداد از ۱ تا max_num و بر زدن تصادفی بدون تکرار
      pool = list(range(1, max_num + 1))
      random.shuffle(pool)

      user_state[chat_id] = {
          'step': 'ready_to_start_draw',
          'max_num': max_num,
          'total_count': count,
          'pool': pool,
          'drawn_list': [],
      }

      markup = types.InlineKeyboardMarkup()
      btn = types.InlineKeyboardButton(
          '🎲 شروع قرعه کشی', callback_data='start_actual_draw'
      )
      markup.add(btn)

      bot.send_message(
          chat_id,
          f'✅ تنظیمات ثبت شد:\n• بازه: ۱ تا {max_num}\n• تعداد دفعات قرعه‌کشی: {count} بار\n\nحالا روی دکمه زیر کلیک کن:',
          reply_markup=markup,
      )
    else:
      bot.send_message(
          chat_id, '⚠️ لطفاً تعداد دفعات قرعه‌کشی را به صورت عدد وارد کن:'
      )


@bot.callback_query_handler(func=lambda call: call.data == 'start_actual_draw')
def start_actual_draw_callback(call):
  chat_id = call.message.chat.id
  data = user_state.get(chat_id)

  if not data or data.get('step') != 'ready_to_start_draw':
    bot.answer_callback_query(
        call.id, 'لطفاً مراحل را از ابتدا (دستور /start) طی کن.'
    )
    return

  pool = data['pool']
  count = data['total_count']

  drawn = pool.pop(0)
  drawn_list = [drawn]
  remaining_count = count - 1

  user_state[chat_id] = {
      'step': 'drawing',
      'max_num': data['max_num'],
      'total_count': count,
      'remaining_count': remaining_count,
      'pool': pool,
      'drawn_list': drawn_list,
  }

  markup = types.InlineKeyboardMarkup()
  if remaining_count > 0:
    btn = types.InlineKeyboardButton('🔄 قرعه بعدی', callback_data='next_draw')
    markup.add(btn)
  else:
    markup = get_finished_markup()

  text_msg = (
      f'🎉 **قرعه شماره ۱:**\n\n'
      f'عدد برنده: **{drawn}**\n\n'
      f'باقیمانده قرعه‌ها: {remaining_count}'
  )
  bot.edit_message_text(
      text_msg,
      chat_id=chat_id,
      message_id=call.message.message_id,
      reply_markup=markup,
      parse_mode='Markdown',
  )


@bot.callback_query_handler(func=lambda call: call.data == 'next_draw')
def next_draw_callback(call):
  user_id = call.from_user.id
  username = call.from_user.username
  if not is_authorized(user_id, username):
    bot.answer_callback_query(call.id, '⛔️ دسترسی نداری!')
    return

  chat_id = call.message.chat.id
  data = user_state.get(chat_id)

  if not data or data.get('step') != 'drawing':
    bot.answer_callback_query(call.id, 'لطفاً دوباره قرعه‌کشی را شروع کن.')
    return

  if data.get('remaining_count', 0) <= 0 or not data.get('pool'):
    bot.answer_callback_query(call.id, 'قرعه‌کشی به پایان رسیده است!')
    return

  pool = data['pool']
  drawn = pool.pop(0)
  data['remaining_count'] -= 1
  data['drawn_list'].append(drawn)

  current_step = data['total_count'] - data['remaining_count']

  if data['remaining_count'] > 0:
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton('🔄 قرعه بعدی', callback_data='next_draw')
    markup.add(btn)

    all_drawn_str = ', '.join(map(str, data['drawn_list']))
    text_msg = (
        f'🎉 **قرعه شماره {current_step}:**\n\n'
        f'عدد برنده جدید: **{drawn}**\n\n'
        f'📋 لیست برنده‌ها تا اینجا: {all_drawn_str}\n'
        f'⏳ دفعات باقی‌مانده: {data['remaining_count']}'
    )
    bot.edit_message_text(
        text_msg,
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown',
    )
  else:
    markup = get_finished_markup()
    all_drawn_str = ', '.join(map(str, data['drawn_list']))
    text_msg = (
        f'🏁 **پایان قرعه کشی!**\n\n'
        f'تمام {data['total_count']} قرعه انجام شد.\n'
        f'🏆 **اعداد برنده نهایی:** {all_drawn_str}'
    )
    bot.edit_message_text(
        text_msg,
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown',
    )


def get_finished_markup():
  markup = types.InlineKeyboardMarkup()
  btn = types.InlineKeyboardButton(
      '🎲 قرعه کشی مجدد', callback_data='start_lottery'
  )
  markup.add(btn)
  return markup


if __name__ == '__main__':
  keep_alive()
  t_ping = Thread(target=self_ping)
  t_ping.start()

  bot.infinity_polling()
