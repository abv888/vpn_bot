# handlers/subscription.py

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from db.db_operations import get_client_from_db
from utils.utils import SERVERS, show_subscription
from utils.menus import tariff_menu
import logging

logger = logging.getLogger(__name__)

subscription_router = Router()

@subscription_router.callback_query(F.data == "my_subscriptions")
async def show_subscriptions(call: CallbackQuery, state: FSMContext):
    client = await get_client_from_db(telegram_id=call.from_user.id)
    if not client:
        await call.message.edit_text(
            "У вас пока нет сохраненных подписок. Вы можете оформить подписку, выбрав локацию.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Выбрать локацию", callback_data="connect_vpn")],
                    [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
                ]
            )
        )
        return
    subscriptions = client.subscriptions or []
    if not subscriptions:
        logger.info(f"User {call.from_user.id} has no subscriptions.")
        await call.message.edit_text(
            "У вас пока нет подписок. Вы можете оформить подписку, выбрав локацию.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Выбрать локацию", callback_data="connect_vpn")],
                    [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
                ]
            )
        )
        return
    await state.update_data(subscriptions=subscriptions, current_index=0)
    await show_subscription(call.message, state, client)

@subscription_router.callback_query(F.data == "next_subscription")
async def next_subscription(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = data.get("current_index", 0)
    subscriptions = data.get("subscriptions")
    if current_index < len(subscriptions) - 1:
        await state.update_data(current_index=current_index + 1)
        client = await get_client_from_db(telegram_id=call.from_user.id)
        await show_subscription(call.message, state, client)

@subscription_router.callback_query(F.data == "prev_subscription")
async def prev_subscription(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = data.get("current_index", 0)
    if current_index > 0:
        await state.update_data(current_index=current_index - 1)
        client = await get_client_from_db(telegram_id=call.from_user.id)
        await show_subscription(call.message, state, client)

@subscription_router.callback_query(F.data == "get_qr_code")
async def get_qr_code(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    current_index = data.get("current_index", 0)
    subscriptions = data.get("subscriptions")
    subscription = subscriptions[current_index]
    server = SERVERS.get(subscription["location"])
    qr_message = await bot.send_photo(
        chat_id=call.message.chat.id,
        photo=FSInputFile(subscription["qr"]),
        caption=(
            f"<b>QR-код для подписки:</b>\n"
            f"{server.description}\n"
            f"<b>Дата окончания:</b> {subscription['expiry_time']}\n"
            "<b>Ссылка на конфигурацию:</b>\n"
            f"<code>{subscription['link']}</code>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Вернуться назад", callback_data="delete_qr_code")],
            ]
        ),
    )
    await state.update_data(qr_message_id=qr_message.message_id)

@subscription_router.callback_query(F.data == "delete_qr_code")
async def delete_qr_code(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    qr_message_id = data.get("qr_message_id")
    if qr_message_id:
        try:
            await bot.delete_message(chat_id=call.message.chat.id, message_id=qr_message_id)
            await state.update_data(qr_message_id=None)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {e}")
            await call.answer("Не удалось удалить сообщение. Возможно, оно уже удалено.", show_alert=True)
    else:
        await call.answer("Сообщение с QR-кодом не найдено.", show_alert=True)

@subscription_router.callback_query(F.data.startswith("location_"))
async def location_selected(call: CallbackQuery):
    location = call.data.split("_")[1]
    logger.info(f"User {call.from_user.id} selected location: {location}.")
    await call.message.edit_text("Выберите тариф:", reply_markup=tariff_menu(location))