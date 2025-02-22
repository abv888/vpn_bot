from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from api_manager.vpn_panel import VPNPanelAPI
from db.db_operations import add_subscription_to_profile, confirm_referral, get_client_from_db
from db.models import Subscription
from utils.qr_generator import create_qr_with_logo
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

@subscription_router.callback_query(F.data == "free_vpn")
async def free_vpn_sender(call :CallbackQuery, bot: Bot):
    vpn_api = VPNPanelAPI(location="NL")
    try:
        await vpn_api.add_client(
                        day=int(7),
                        email=f"{call.from_user.username}-NL-Test",
                        id=call.from_user.id
                    )           
        client = await vpn_api.get_client(
            client_email=f"{call.from_user.id}-{call.from_user.username}-NL-Test"
        )
        link = await vpn_api.configure_link(client=client)
        create_qr_with_logo(
            data=link,
            file_path=f"users/qr/{client.client_id}.png"
        )
        await bot.delete_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id
        )
        await bot.send_photo(
            chat_id=call.from_user.id,
            photo=FSInputFile(f"users/qr/{client.client_id}.png"),
            caption=f"<code>{link}</code>",
            parse_mode=ParseMode.HTML
        )
        await add_subscription_to_profile(
            telegram_id=call.from_user.id, 
            subscription=Subscription(
                subscription_id=client.client_id,
                location='NL',
                expiry_time=7,
                qr=f"users/qr/{client.client_id}.png",
                link=link
            ))
        await confirm_referral(referral_telegram_id=call.from_user.id)
    except Exception as e:
        await bot.send_message(
            chat_id=call.from_user.id,
            text="Вы уже использовали бесплатный период!"
        )