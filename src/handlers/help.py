from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.menus import help_menu, help_device
import logging

logger = logging.getLogger(__name__)

help_router = Router()

@help_router.callback_query(F.data == "help")
async def help_menu_callback(call: CallbackQuery):
    logger.info(f"User {call.from_user.id} accessed help menu.")
    await call.message.edit_text(
        "Ниже представлены ответы на самые часто задаваемые вопросы.", 
        reply_markup=help_menu()
    )

@help_router.callback_query(F.data == "help_device")
async def device_help_callback(call: CallbackQuery):
    await call.message.edit_text(
        "Для подключения устройства к VPN, выберите ваш тип устройства и следуйте инструкции:\n\n"
        "Если вам нужна помощь, свяжитесь с нашей поддержкой.",
        reply_markup=help_device()
    )

@help_router.callback_query(F.data == "help_payment")
async def payment_help_callback(call: CallbackQuery):
    await call.message.edit_text(
        "Чтобы оплатить подписку, нажмите «Подключить VPN», выберите нужную локацию и тарифный план, "
        "выберите способ платежа и проведите оплату.\n\n"
        "После этого система перенаправит вас на Telegram-бота Baogrand VPN и ваша подписка станет активна.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подключить VPN", callback_data="connect_vpn")],
                [InlineKeyboardButton(text="Назад", callback_data="help")]
            ]
        )
    )

@help_router.callback_query(F.data == "traffic_limit")
async def traffic_limit_callback(call: CallbackQuery):
    await call.message.edit_text(
        "У Baogrand VPN есть ограничение на количество устройств, на которые вы можете установить ваш ключ.\n"
        "Одна подписка - одно устройство!\n"
        "Зато нет ограничений на скорость соединения, она всегда максимальная!\n\n"
        "И даже нет ограничения на объем трафика, который можно выкачать за 1 месяц!\n"
        "Вы и Ваши близкие можете пользоваться нашим сервисом без ограничений.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="help")]
            ]
        )
    )