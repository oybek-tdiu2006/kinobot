import asyncio
import logging
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from flask import Flask
from threading import Thread

# ————————————————————————————————————————————————————————————————
# BOSHLANG'ICH SOZLAMALAR
# ————————————————————————————————————————————————————————————————
API_TOKEN = '8923311651:AAGELYry39UjMM49s_B1x6cIGNVqcldc7ks'  # Bot tokeni
ADMIN_ID = 8084947526  # Telegram Admin ID
KANAL_ID = '@manoli_kinolar2026'  # Majburiy obuna kanali username
KANAL_LINK = 'https://t.me/Manoli_kinolar2026'  # Kanal havolasi

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ————————————————————————————————————————————————————————————————
# SUPABASE (POSTGRESQL) DATA BAZA
# ————————————————————————————————————————————————————————————————
DATABASE_URL = "postgresql://postgres:oybekhan200@db.bdwpqxhxcdalvrprjixg.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Jadvalarni avtomatik yaratish
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS kinolar (kod TEXT PRIMARY KEY, nomi TEXT, file_id TEXT)''')
    conn.commit()
    cursor.close()
    conn.close()
except Exception as e:
    logging.error(f"Baza yaratishda xatolik: {e}")

# ————————————————————————————————————————————————————————————————
# RENDER UCHUN KEEP-ALIVE SERVER (Uxlashini oldini oladi)
# ————————————————————————————————————————————————————————————————
app = Flask('')

@app.route('/')
def home():
    return "Bot ishlayapti va faol!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

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
menu_buttons.add("🔍 Kino izlash", "👨‍💻 Admin bilan aloqa")

admin_buttons = ReplyKeyboardMarkup(resize_keyboard=True)
admin_buttons.add("🔍 Kino izlash", "👨‍💻 Admin bilan aloqa")
admin_buttons.add("➕ Kino qo'shish", "🗑 Kino o'chirish")
admin_buttons.add("📊 Statistika", "📢 Xabar tarqatish")

cancel_button = ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Bekor qilish")

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

@dp.message_handler(text="❌ Bekor qilish", state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    reply_m = admin_buttons if message.from_user.id == ADMIN_ID else menu_buttons
    await message.reply("🔄 Amaliyot bekor qilindi.", reply_markup=reply_m)

@dp.message_handler(commands=['start'], state="*")
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    
    try:
        db_conn = get_db_connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
        db_conn.commit()
        db_cursor.close()
        db_conn.close()
    except Exception as e:
        logging.error(f"User save error: {e}")

    if user_id != ADMIN_ID and not await check_sub(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=KANAL_LINK))
        markup.add(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
        await message.reply("👋 Assalomu alaykum!\nBotdan foydalanish uchun quyidagi kanalimizga obuna bo'ling:", reply_markup=markup)
        return

    if user_id == ADMIN_ID:
        await message.reply("⚙️ Admin panel faol!", reply_markup=admin_buttons)
    else:
        await message.reply("👋 Xush kelibsiz! Quyidagi tugmalardan foydalaning:", reply_markup=menu_buttons)

@dp.callback_query_handler(text="check_subscription", state="*")
async def check_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_sub(user_id):
        await call.answer("🚀 Obuna tasdiqlandi!", show_alert=True)
        await call.message.delete()
        reply_m = admin_buttons if user_id == ADMIN_ID else menu_buttons
        await bot.send_message(user_id, "Botdan foydalanishingiz mumkin:", reply_markup=reply_m)
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmagansiz!", show_alert=True)

@dp.message_handler(text="👨‍💻 Admin bilan aloqa", state="*")
async def admin_contact(message: types.Message):
    text = (
        "👨‍💻 <b>Savol va takliflar bo'yicha adminga murojaat qiling:</b>\n\n"
        f"👉 <a href='tg://user?id={ADMIN_ID}'>Adminga yozish uchun bosing</a>"
    )
    await message.reply(text, parse_mode="HTML")

@dp.message_handler(text="🔍 Kino izlash", state="*")
async def search_info(message: types.Message):
    if message.from_user.id != ADMIN_ID and not await check_sub(message.from_user.id):
        await send_welcome(message, None)
        return
    await message.reply("🍿 Kino kodini yuboring. Masalan: 101")

@dp.message_handler(text="📊 Statistika", state="*")
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        db_conn = get_db_connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT COUNT(*) FROM users")
        u_count = db_cursor.fetchone()[0]
        db_cursor.execute("SELECT COUNT(*) FROM kinolar")
        k_count = db_cursor.fetchone()[0]
        db_cursor.close()
        db_conn.close()
        await message.reply(f"📊 <b>Bot statistikasi:</b>\n\n👥 Foydalanuvchilar: {u_count} ta\n🎬 Kinolar: {k_count} ta", parse_mode="HTML")
    except Exception as e:
