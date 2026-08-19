import asyncio
import logging
import os
from threading import Thread

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from flask import Flask
import psycopg2

# ————————————————————————————————————————————————————————————————
# RENDER UCHUN WEB-SERVER (KEEP ALIVE)
# ————————————————————————————————————————————————————————————————
app = Flask('')


@app.route('/')
def home():
  return "Bot 24/7 rejimida muvaffaqiyatli ishlayapti!"


def run():
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.start()


DATABASE_URL = os.getenv('DATABASE_URL')

# ————————————————————————————————————————————————————————————————
# BOSHLANG'ICH SOZLAMALAR
# ————————————————————————————————————————————————————————————————
API_TOKEN = '8923311651:AAGELYry39UjMM49s_B1x6cIGNVqcldc7ks'
ADMIN_ID = 8084947526  # Telegram ID
KANAL_ID = '@manoli_kinolar2026'  # Majburiy obuna kanali username
KANAL_LINK = 'https://t.me/Manoli_kinolar2026'  # Kanal havolasi

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ————————————————————————————————————————————————————————————————
# DATA BAZA (PostgreSQL / Supabase)
# ————————————————————————————————————————————————————————————————
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute(
    '''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)'''
)
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS kinolar (kod TEXT PRIMARY KEY, nomi TEXT, file_id TEXT)'''
)
conn.commit()


# ————————————————————————————————————————————————————————————————
# FSM HOLATLARI
# ————————————————————————————————————————————————————————————————
class AdminXolatlari(StatesGroup):
  kino_qoshish = State()
  kino_ochirish = State()
  reklama = State()


# ————————————————————————————————————————————————————————————————
# TUGMALAR (KEYBOARDS)
# ————————————————————————————————————————————————————————————————
menu_buttons = ReplyKeyboardMarkup(resize_keyboard=True)
menu_buttons.add('🔍 Kino izlash', '👨‍💻 Admin bilan aloqa')

admin_buttons = ReplyKeyboardMarkup(resize_keyboard=True)
admin_buttons.add('🔍 Kino izlash', '👨‍💻 Admin bilan aloqa')
admin_buttons.add("➕ Kino qo'shish", "🗑 Kino o'chirish")
admin_buttons.add('📊 Statistika', '📢 Xabar tarqatish')

cancel_button = ReplyKeyboardMarkup(resize_keyboard=True).add('❌ Bekor qilish')


# ————————————————————————————————————————————————————————————————
# MAJBURIY OBUNANI TEKSHIRISH
# ————————————————————————————————————————————————————————————————
async def check_sub(user_id: int) -> bool:
  try:
    member = await bot.get_chat_member(chat_id=KANAL_ID, user_id=user_id)
    return member.status in ['creator', 'administrator', 'member']
  except Exception:
    return False


# ————————————————————————————————————————————————————————————————
# BOT BUYRUQLARI VA ASOSIY LOGIKA
# ————————————————————————————————————————————————————————————————


@dp.message_handler(text='❌ Bekor qilish', state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
  await state.finish()
  reply_m = admin_buttons if message.from_user.id == ADMIN_ID else menu_buttons
  await message.reply('🔄 Amaliyot bekor qilindi.', reply_markup=reply_m)


@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
  await state.finish()
  user_id = message.from_user.id

  try:
    cursor.execute(
        'INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING',
        (user_id,),
    )
    conn.commit()
  except Exception:
    conn.rollback()

  if user_id != ADMIN_ID and not await check_sub(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            text="📢 Kanalga obuna bo'lish", url=KANAL_LINK
        )
    )
    markup.add(
        InlineKeyboardButton(
            text='✅ Tekshirish', callback_data='check_subscription'
        )
    )
    await message.reply(
        '👋 Assalomu alaykum!\nBotdan foydalanish uchun quyidagi kanalimizga'
        ' obuna bo'ling:',
        reply_markup=markup,
    )
    return

  if user_id == ADMIN_ID:
    await message.reply('⚙️ Admin panel faol!', reply_markup=admin_buttons)
  else:
    await message.reply(
        '👋 Xush kelibsiz! Quyidagi tugmalardan foydalaning:',
        reply_markup=menu_buttons,
    )


@dp.callback_query_handler(text='check_subscription', state='*')
async def check_callback(call: types.CallbackQuery):
  user_id = call.from_user.id
  if await check_sub(user_id):
    await call.answer('🚀 Obuna tasdiqlandi!', show_alert=True)
    await call.message.delete()
    reply_m = admin_buttons if user_id == ADMIN_ID else menu_buttons
    await bot.send_message(
        user_id, 'Botdan foydalanishingiz mumkin:', reply_markup=reply_m
    )
  else:
    await call.answer(
        '❌ Siz hali kanalga obuna bo'lmagansiz!', show_alert=True
    )


@dp.message_handler(text='👨‍💻 Admin bilan aloqa', state='*')
async def admin_contact(message: types.Message):
  text = (
      '👨‍💻 <b>Savol va takliflar bo'yicha adminga murojaat qiling:</b>\n\n'
      f"👉 <a href='tg://user?id={ADMIN_ID}'>Adminga yozish uchun bosing</a>"
  )
  await message.reply(text, parse_mode='HTML')


@dp.message_handler(text='🔍 Kino izlash', state='*')
async def search_info(message: types.Message):
  if message.from_user.id != ADMIN_ID and not await check_sub(
      message.from_user.id
  ):
    await send_welcome(message, None)
    return
  await message.reply('🍿 Kino kodini yuboring. Masalan: 101')


@dp.message_handler(text='📊 Statistika', state='*')
async def show_stats(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  cursor.execute('SELECT COUNT(*) FROM users')
  u_count = cursor.fetchone()[0]
  cursor.execute('SELECT COUNT(*) FROM kinolar')
  k_count = cursor.fetchone()[0]
  await message.reply(
      f'📊 <b>Bot statistikasi:</b>\n\n👥 Foydalanuvchilar: {u_count} ta\n🎬'
      f' Kinolar: {k_count} ta',
      parse_mode='HTML',
  )


# ————————————————————————————————————————————————————————————————
# ADMIN FUNKSIYALARI
# ————————————————————————————————————————————————————————————————


# 1. Kino qo'shish
@dp.message_handler(text="➕ Kino qo'shish", state='*')
async def add_kino_start(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  await AdminXolatlari.kino_qoshish.set()
  await message.reply(
      "Kino qo'shish uchun ma'lumotlarni quyidagi formatda yuboring:\n\n"
      '<code>kod*nomi*file_id</code>\n\n'
      'Masalan: <code>101*Forsaj 10*BAACAgIAAx...</code>',
      reply_markup=cancel_button,
      parse_mode='HTML',
  )


@dp.message_handler(state=AdminXolatlari.kino_qoshish)
async def add_kino_save(message: types.Message, state: FSMContext):
  matn = message.text.strip()
  parts = matn.split('*')
  if len(parts) == 3:
    kod, nomi, file_id = (
        parts[0].strip(),
        parts[1].strip(),
        parts[2].strip(),
    )
    cursor.execute(
        'INSERT INTO kinolar (kod, nomi, file_id) VALUES (%s, %s, %s) ON'
        ' CONFLICT (kod) DO UPDATE SET nomi = EXCLUDED.nomi, file_id ='
        ' EXCLUDED.file_id',
        (kod, nomi, file_id),
    )
    conn.commit()
    await state.finish()
    await message.reply(
        f'✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kodi: {kod}\n🎬 Nomi: {nomi}',
        reply_markup=admin_buttons,
    )
  else:
    await message.reply(
        '❌ Format xato! Iltimos <code>kod*nomi*file_id</code> ko'rinishida'
        ' yuboring.',
        parse_mode='HTML',
    )


# 2. Kino o'chirish
@dp.message_handler(text="🗑 Kino o'chirish", state='*')
async def delete_kino_start(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  await AdminXolatlari.kino_ochirish.set()
  await message.reply(
      "🗑 O'chirmoqchi bo'lgan kinongizning <b>kodini (raqamini)</b> yuboring:",
      reply_markup=cancel_button,
      parse_mode='HTML',
  )


@dp.message_handler(state=AdminXolatlari.kino_ochirish)
async def delete_kino_save(message: types.Message, state: FSMContext):
  kod = message.text.strip()
  cursor.execute('SELECT nomi FROM kinolar WHERE kod = %s', (kod,))
  kino = cursor.fetchone()
  if kino:
    cursor.execute('DELETE FROM kinolar WHERE kod = %s', (kod,))
    conn.commit()
    await state.finish()
    await message.reply(
        f'🗑 <b>{kino[0]}</b> (Kod: {kod}) bazadan muvaffaqiyatli o'chirildi!',
        reply_markup=admin_buttons,
        parse_mode='HTML',
    )
  else:
    await message.reply(
        "❌ Bu kod bilan kino topilmadi. Qayta urinib ko'ring:"
    )


# 3. Reklama tarqatish
@dp.message_handler(text='📢 Xabar tarqatish', state='*')
async def start_reklama(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  await AdminXolatlari.reklama.set()
  await message.reply(
      '📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (matn, rasm'
      ' yoki video):',
      reply_markup=cancel_button,
  )


@dp.message_handler(
    state=AdminXolatlari.reklama, content_types=types.ContentType.ANY
)
async def send_reklama(message: types.Message, state: FSMContext):
  await state.finish()

  cursor.execute('SELECT user_id FROM users')
  barcha_foydalanuvchilar = cursor.fetchall()

  yuborildi = 0
  xato = 0

  kutish_xabari = await message.reply(
      '⏳ Xabar tarqatilmoqda, iltimos kuting...'
  )

  for user in barcha_foydalanuvchilar:
    try:
      await message.copy_to(chat_id=user[0])
      yuborildi += 1
      await asyncio.sleep(0.05)
    except Exception:
      xato += 1

  await kutish_xabari.delete()
  await message.reply(
      '📢 <b>Xabar tarqatish yakunlandi!</b>\n\n'
      f'✅ Muvaffaqiyatli: {yuborildi} ta\n'
      f'❌ Yetkazilmadi: {xato} ta',
      reply_markup=admin_buttons,
      parse_mode='HTML',
  )


# Admin video yuborganda file_id berish
@dp.message_handler(content_types=['video'], state='*')
async def get_video_id(message: types.Message):
  if message.from_user.id == ADMIN_ID:
    await message.reply(
        '🎬 Videongizning <code>file_id</code> kodi:\n\n'
        f'<code>{message.video.file_id}</code>',
        parse_mode='HTML',
    )


# Matnli xabarlarni qabul qilish (Kino qidiruv)
@dp.message_handler(state='*')
async def handle_messages(message: types.Message):
  user_id = message.from_user.id
  matn = message.text.strip()

  boshqa_tugmalar = [
      '🔍 Kino izlash',
      '👨‍💻 Admin bilan aloqa',
      "➕ Kino qo'shish",
      "🗑 Kino o'chirish",
      '📊 Statistika',
      '📢 Xabar tarqatish',
      '❌ Bekor qilish',
  ]
  if matn in boshqa_tugmalar:
    return

  if user_id != ADMIN_ID and not await check_sub(user_id):
    await send_welcome(message, None)
    return

  cursor.execute('SELECT nomi, file_id FROM kinolar WHERE kod = %s', (matn,))
  kino = cursor.fetchone()

  if kino:
    nomi, file_id = kino
    await message.reply(
        f'🎬 <b>Kino nomi:</b> {nomi}\n\n🍿 Yoqimli tomosha!', parse_mode='HTML'
    )
    try:
      await bot.send_video(chat_id=message.chat.id, video=file_id)
    except Exception:
      await message.reply('❌ Videoni yuborishda xatolik yuz berdi!')
  else:
    await message.reply(
        '❌ <b>Bunday kodli kino topilmadi!</b>\n\nIltimos, kodni tekshirib'
        ' qaytadan yuboring.',
        parse_mode='HTML',
    )


if __name__ == '__main__':
  keep_alive()  # Render uchun veb-serverni fonda yoqish
  executor.start_polling(dp, skip_updates=True)
