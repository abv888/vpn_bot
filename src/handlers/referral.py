# handlers/referral.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db.db_operations import get_client_from_db
import logging

logger = logging.getLogger(__name__)

referral_router = Router()

@referral_router.callback_query(F.data == "my_referrals")
async def show_referrals(call: CallbackQuery):
    logger.info(f"User {call.from_user.id} clicked on 'My Referrals'.")
    client = await get_client_from_db(telegram_id=call.from_user.id)
    if not client:
        logger.warning(f"User {call.from_user.id} not found in the database.")
        await call.message.edit_text(
            "Вы не зарегистрированы в системе. Пожалуйста, начните процесс подключения VPN.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Подключить VPN", callback_data="connect_vpn")],
                    [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
                ]
            )
        )
        return

    referred_users = client.referred_users or []
    referral_code = client.referral_code
    discount = client.discount or 0
    logger.info(f"User {call.from_user.id} has {len(referred_users)} referred users and a discount of {discount}%.")
    
    if not referred_users:
        referral_text = (
            f"Ваш реферальный код: <code>{referral_code}</code>\n"
            f"Ваша скидка: {discount}%\n\n"
            "У вас пока нет приглашенных пользователей.\n"
            "Приглашайте друзей и получайте скидки на подписки!"
        )
        logger.info(f"User {call.from_user.id} has no referred users.")
    else:
        referral_text = (
            f"<b>Мои рефералы:</b>\n"
            f"Ваш реферальный код: <code>{client.referral_code}</code>\n"
            f"Ваша скидка: {client.discount}%\n\n"
            f"<b>Приглашенные пользователи:</b> {len(referred_users)}\n\n"
        )
        referral_details = []      
        for index, referral in enumerate(referred_users, start=1):
            status = "Подтвержден" if referral.get("confirmed") else "Зарегистрирован"
            referral_details.append(
                f"{index}. {referral.get('name', 'Имя не указано')} "
                f"({referral.get('email', 'Email не указан')}) — <b>{status}</b>"
            )
        referral_text += "\n".join(referral_details)

    await call.message.edit_text(
        referral_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
            ]
        )
    )