import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8789813084:AAG4atjox9G_53u9M5PT3C812ilksz4PZBY"
ADMIN_ID = 7570922005 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class TradeStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_skin_photo = State()

# Функция для пинга раз в 13 минут
async def keep_alive():
    while True:
        await asyncio.sleep(780)
        try:
            await bot.send_message(ADMIN_ID, "Пинг для поддержания активности на Render.")
        except Exception as e:
            print(f"Ошибка отправки пинга: {e}")

# Простой веб-сервер для Render, чтобы сервис не уходил в спячку
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await message.answer("Привет! На какую сумму голды ты хочешь пополнить баланс?")
    await state.set_state(TradeStates.waiting_for_amount)

@dp.message(TradeStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи только число.")
        return

    amount_net = int(message.text)
    amount_gross = int(amount_net / 0.7)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Принять", callback_data=f"admin_approve_{message.from_user.id}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"admin_reject_{message.from_user.id}")]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"Новая заявка от @{message.from_user.username} (ID: {message.from_user.id})\n"
        f"Хочет получить: {amount_net} G\n"
        f"С учетом комиссии (30%) нужно выставить за: {amount_gross} G",
        reply_markup=keyboard
    )
    
    await message.answer("Заявка отправлена администратору. Ожидай подтверждения...")
    await state.clear()

@dp.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_request(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    await state.set_state(TradeStates.waiting_for_skin_photo)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer("Отправь фото скина, который нужно купить пользователю.")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_request(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    await bot.send_message(user_id, "Твоя заявка была отклонена.")
    await callback.message.edit_text("Заявка отклонена.")
    await callback.answer()

@dp.message(TradeStates.waiting_for_skin_photo, F.photo)
async def admin_sends_skin(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я купил", callback_data="user_paid")]
    ])
    
    await bot.send_photo(
        user_id,
        photo=message.photo[-1].file_id,
        caption="Пожалуйста, купи этот скин на рынке.\nПосле покупки нажми кнопку ниже.",
        reply_markup=keyboard
    )
    
    await message.answer("Фото отправлено покупателю. Ожидаем оплату.")
    await state.clear()

@dp.callback_query(F.data == "user_paid")
async def user_confirms_payment(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить зачисление на сайт", callback_data=f"admin_confirm_{user_id}")],
        [InlineKeyboardButton(text="Оплата не найдена", callback_data=f"admin_fail_{user_id}")]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"Пользователь @{callback.from_user.username} подтвердил покупку скина.\nПроверь рынок и зачисли баланс.",
        reply_markup=keyboard
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Ожидаем проверки администратором и зачисления баланса на сайте...")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirms_topup(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    stars_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="review_1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="review_2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="review_3")
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="review_4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="review_5")
        ]
    ])
    
    await bot.send_message(
        user_id,
        "Твой баланс успешно пополнен! Оцени, пожалуйста, работу сервиса:",
        reply_markup=stars_keyboard
    )
    
    await callback.message.edit_text("Пополнение подтверждено. Запрос на отзыв отправлен.")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_fail_"))
async def admin_fails_topup(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    await bot.send_message(user_id, "Оплата не найдена. Баланс не зачислен.")
    await callback.message.edit_text("Зачисление отменено.")
    await callback.answer()

@dp.callback_query(F.data.startswith("review_"))
async def process_review(callback: CallbackQuery):
    rating = callback.data.split("_")[1]
    
    await callback.message.edit_text(f"Спасибо за твой отзыв: {rating} звезд!")
    
    await bot.send_message(
        ADMIN_ID,
        f"Новый отзыв от @{callback.from_user.username}: {rating} звезд."
    )
    await callback.answer()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем веб-сервер и фоновый пинг
    asyncio.create_task(start_web_server())
    asyncio.create_task(keep_alive())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())