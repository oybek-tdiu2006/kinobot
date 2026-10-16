@dp.message_handler(state=AdminXolatlari.kino_ochirish)
async def delete_kino_save(message: types.Message, state: FSMContext):
    kod = message.text.strip()
    cursor.execute("SELECT nomi FROM kinolar WHERE kod = ?", (kod,))
    kino = cursor.fetchone()
    if kino:
        cursor.execute("DELETE FROM kinolar WHERE kod = ?", (kod,))
        conn.commit()
        await state.finish()
        await message.reply(f"🗑 <b>{kino[0]}</b> (Kod: {kod}) bazadan muvaffaqiyatli o'chirildi!", reply_markup=admin_buttons, parse_mode="HTML")
    else:
        await message.reply("❌ Bu kod bilan kino topilmadi. Qayta urinib ko'ring:")

@dp.message_handler(text="📢 Xabar tarqatish", state="*")
async def start_reklama(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await AdminXolatlari.reklama.set()
    await message.reply("📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (matn, rasm yoki video):", reply_markup=cancel_button)

@dp.message_handler(state=AdminXolatlari.reklama, content_types=types.ContentType.ANY)
async def send_reklama(message: types.Message, state: FSMContext):
    await state.finish()
    
    cursor.execute("SELECT user_id FROM users")
    barcha_foydalanuvchilar = cursor.fetchall()
    
    yuborildi = 0
    xato = 0
    
    kutish_xabari = await message.reply("⏳ Xabar tarqatilmoqda, iltimos kuting...")
    
    for user in barcha_foydalanuvchilar:
        try:
            await message.copy_to(chat_id=user[0])
            yuborildi += 1
            await asyncio.sleep(0.05)
        except Exception:
            xato += 1
            
    await kutish_xabari.delete()
    await message.reply(
        f"📢 <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"✅ Muvaffaqiyatli: {yuborildi} ta\n"
        f"❌ Yetkazilmadi: {xato} ta",
        reply_markup=admin_buttons,
        parse_mode="HTML"
    )

@dp.message_handler(content_types=['video'], state="*")
async def get_video_id(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply(f"🎬 Videongizning <code>file_id</code> kodi:\n\n<code>{message.video.file_id}</code>", parse_mode="HTML")

@dp.message_handler(state="*")
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    matn = message.text.strip()

    boshqa_tugmalar = [
        "🔍 Kino izlash", "👨‍💻 Admin bilan aloqa", "➕ Kino qo'shish", 
        "🗑 Kino o'chirish", "📊 Statistika", "📢 Xabar tarqatish", 
        "❌ Bekor qilish", "💾 Baza zaxirasi"
    ]
    if matn in boshqa_tugmalar:
        return

    if user_id != ADMIN_ID and not await check_sub(user_id):
        await send_welcome(message, None)
        return

    # Har safar alohida cursor ochib qidirish (keshda qolib ketishini oldini oladi)
    local_cursor = conn.cursor()
    local_cursor.execute("SELECT nomi, file_id FROM kinolar WHERE kod = ?", (matn,))
    kino = local_cursor.fetchone()

    if kino:
        nomi, file_id = kino
        await message.reply(f"🎬 <b>Kino nomi:</b> {nomi}\n\n🍿 Yoqimli tomosha!", parse_mode="HTML")
        try: 
            await bot.send_video(chat_id=message.chat.id, video=file_id)
        except Exception: 
            await message.reply("❌ Videoni yuborishda xatolik yuz berdi!")
    else:
        await message.reply("❌ <b>Bunday kodli kino topilmadi!</b>\n\nIltimos, kodni tekshirib qaytadan yuboring.", parse_mode="HTML")

if name == 'main':
    executor.start_polling(dp, skip_updates=True)
