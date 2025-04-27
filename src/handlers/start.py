from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from utils.menus import main_menu, location_menu
from db.db_operations import add_client_to_db, add_referral_to_referrer, get_client_from_db, update_client_in_db
from utils.utils import UserData
import uuid
import logging

logger = logging.getLogger(__name__)

start_router = Router()

@start_router.message(F.text == "/start")
async def send_welcome(message: Message):
    logger.info(f"User {message.from_user.id} started the bot.")
    await add_client_to_db(message.from_user.id)
    await message.answer("🥷🏽 <b>Baogrand VPN</b> - продвинутое решение для всех пользователей.\n\n" \
    "⚡️ Высокая скорость\n" \
    "🔓 Доступ к заблокированным сервисам\n" \
    "💰 Оплата картами РФ и криптовалютой", reply_markup=main_menu(), parse_mode=ParseMode.HTML)

@start_router.message(F.text == "/menu")
async def menu(message: Message):
    logger.info(f"User {message.from_user.id} accessed the menu.")
    await message.delete()
    await message.answer("🥷🏽 <b>Baogrand VPN</b> - продвинутое решение для всех пользователей.\n\n" \
    "⚡️ Высокая скорость\n" \
    "🔓 Доступ к заблокированным сервисам\n" \
    "💰 Оплата картами РФ и криптовалютой", reply_markup=main_menu(), parse_mode=ParseMode.HTML)

@start_router.callback_query(F.data == "menu")
async def main_menu_callback(call: CallbackQuery):
    logger.info(f"User {call.from_user.id} returned to main menu.")
    await call.message.edit_text("🥷🏽 <b>Baogrand VPN</b> - продвинутое решение для всех пользователей.\n\n" \
    "⚡️ Высокая скорость\n" \
    "🔓 Доступ к заблокированным сервисам\n" \
    "💰 Оплата картами РФ и криптовалютой", reply_markup=main_menu(), parse_mode=ParseMode.HTML)

@start_router.callback_query(F.data == "connect_vpn")
async def ask_for_email(call: CallbackQuery, state: FSMContext):
    logger.info(f"User {call.from_user.id} selected 'Connect VPN'.")
    client = await get_client_from_db(telegram_id=call.from_user.id)
    if client and client.email:
        await call.message.edit_text("Выберите локацию:", reply_markup=location_menu())
    else:
        await call.message.edit_text("Пожалуйста, введите вашу электронную почту:")
        await state.set_state(UserData.waiting_for_email)

@start_router.message(UserData.waiting_for_email)
async def ask_for_name(message: Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("Пожалуйста, введите корректный адрес электронной почты.")
        return
    await state.update_data(email=email)
    await message.answer("Введите ваше имя:")
    await state.set_state(UserData.waiting_for_name)

@start_router.message(UserData.waiting_for_name)
async def save_user_data(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(
        "Если у вас есть реферальный код, введите его сейчас. Если нет, нажмите кнопку 'Пропустить'.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Пропустить", callback_data="skip_referral")]
            ]
        )
    )
    await state.set_state(UserData.waiting_for_referral)

@start_router.message(UserData.waiting_for_referral)
async def handle_referral_code(message: Message, state: FSMContext):
    try:
        referral_code = message.text.strip()
        logger.info(f"User {message.from_user.id} entered referral code: {referral_code}")
        
        referrer = await get_client_from_db(referral_code=referral_code)
        if referrer:
            user_data = await state.get_data()
            name = user_data.get("name")
            email = user_data.get("email")
            logger.info(f"Referral code {referral_code} is valid. Referrer: {referrer.telegram_id}")
            
            # Обновляем данные клиента
            await update_client_in_db(
                telegram_id=message.from_user.id,
                email=email,
                name=name,
                referred_by=referral_code
            )
            
            try:
                # Добавляем реферала
                await add_referral_to_referrer(
                    referrer_telegram_id=referrer.telegram_id,
                    referral_telegram_id=message.from_user.id
                )
            except Exception as e:
                logger.error(f"Error adding referral: {str(e)}")
                # Даже если произошла ошибка с рефералом, позволяем пользователю продолжить
            
            await state.clear()
            await message.answer(
                "Ваши данные успешно сохранены. Выберите локацию:", 
                reply_markup=location_menu()
            )
        else:
            logger.warning(f"Invalid referral code entered by user {message.from_user.id}: {referral_code}")
            await message.answer(
                "Неверный реферальный код. Попробуйте ещё раз или нажмите 'Пропустить'.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Пропустить", callback_data="skip_referral")]
                    ]
                )
            )
    except Exception as e:
        logger.error(f"Error in handle_referral_code: {str(e)}")
        await message.answer(
            "Произошла ошибка при обработке реферального кода. Попробуйте заново или нажмите 'Пропустить'.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Пропустить", callback_data="skip_referral")]
                ]
            )
        )

@start_router.callback_query(F.data == "skip_referral")
async def skip_referral_code(call: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    name = user_data.get("name")
    email = user_data.get("email")
    referred_by = None 
    logger.info(f"User {call.from_user.id} skipped referral code. Name: {name}, Email: {email}")
    client_added = await update_client_in_db(
        telegram_id=call.from_user.id,
        email=email,
        referred_by=referred_by,
        name=name
        )
    if not client_added:
        logger.info(f"User {call.from_user.id} already exists in the database.")
    else:
        logger.info(f"User {call.from_user.id} successfully added to the database.")
    await state.clear()
    await call.message.edit_text("Ваши данные успешно сохранены. Выберите локацию:", reply_markup=location_menu())