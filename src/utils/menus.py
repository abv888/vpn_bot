from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db.db_operations import get_client_from_db
from utils.utils import SERVERS

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подключить VPN",
                    callback_data="connect_vpn"
                ),
                InlineKeyboardButton(
                    text="Помощь",
                    callback_data="help"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Мои подписки",
                    callback_data="my_subscriptions"
                ),
                InlineKeyboardButton(
                    text="Мои рефералы",
                    callback_data="my_referrals"
                )
            ],
            [
                InlineKeyboardButton(
                    text="VPN — бесплатно (7 дней)",
                    callback_data="free_vpn"
                )
            ]
        ]
    )

def location_menu():
    buttons = [
        [InlineKeyboardButton(text=server.description, callback_data=f"location_{code}")]
        for code, server in SERVERS.items()
    ]
    buttons.append(
        [InlineKeyboardButton(
                    text="Главная страница",
                    callback_data="menu"
                )]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tariff_menu(
        selected_location, discount
):
    server = SERVERS.get(selected_location)
        
    buttons = [
        [InlineKeyboardButton(
            text=f"{months} {tariff.string} — {tariff.amount - (tariff.amount * discount)} руб.",
            callback_data=f"tariff_{months}_{selected_location}"
        )]
        for months, tariff in server.tariffs.items()
    ]
    buttons.append(
        [InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data="connect_vpn"
                )]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=
           buttons
        
    )

def help_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Чат с поддержкой",
                    url="https://t.me/shadowgate_support"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Как подключить свое устройство?",
                    callback_data="help_device"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Как оплатить VPN-подписку?",
                    callback_data="help_payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Лимит расхода трафика",
                    callback_data="traffic_limit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Главная страница",
                    callback_data="menu"
                )
            ]
        ]
    )

def help_device():
    return InlineKeyboardMarkup(
        inline_keyboard= [
            [
                InlineKeyboardButton(
                    text="iPhone",
                    url="https://teletype.in/@rmot/9Da58YDAqje"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Android",
                    url="https://teletype.in/@rmot/Iuw3-iJU0NV"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Mac",
                    url="https://teletype.in/@rmot/9Da58YDAqje"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Windows",
                    url="https://wiki.aeza.net/nekoray-universal-client"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Чат с поддержкой",
                    url="https://t.me/shadowgate_support"
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data="help"
                )
            ]
        ]
    )

def payment_methods(location, months):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Банковская карта",
                    callback_data=f"payment_card_{location}_{months}"
                ),
                InlineKeyboardButton(
                    text="💳 ЮMoney",
                    callback_data=f"payment_yookassa_{location}_{months}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐️ Звёзды",
                    callback_data=f"payment_stars_{location}_{months}"
                ),
                InlineKeyboardButton(
                    text="🪙 Криптовалюта",
                    callback_data=f"payment_cryptomus_{location}_{months}"
                )
                
            ],
            [   InlineKeyboardButton(
                    text="↩️ Назад",
                    callback_data=f"location_{location}"
                )
            ]
        ]
    )
