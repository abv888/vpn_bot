import json
from os import getenv
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any
import uuid
from db.models import DBClient, Subscription

class Tariff:
    def __init__(self, amount: int, string: str, amount_stars: int, label: str):
        self.amount = amount
        self.string = string
        self.amount_stars = amount_stars
        self.label = label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "string": self.string,
            "amount_stars": self.amount_stars,
            "label": self.label
        }

class Server:
    def __init__(self, location: str, description: str, tariffs: Dict[int, Tariff]):
        self.location = location
        self.description = description
        self.tariffs = tariffs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "description": self.description,
            "tariffs": {months: tariff.to_dict() for months, tariff in self.tariffs.items()}
        }

class UserData(StatesGroup):
    waiting_for_email = State()
    waiting_for_name = State()
    waiting_for_referral = State()

class SubscriptionNavigation(StatesGroup):
    viewing = State()

def get_servers_from_config():
    vpn_configs = json.loads(getenv("VPN"))
    servers = {}
    
    for location, config in vpn_configs.items():
        servers[location] = Server(
            location=location,
            description=get_location_description(location),  # Добавим эту функцию
            tariffs=TARIFFS_DATA
        )
    return servers

def get_location_description(location: str) -> str:
    """Получает описание локации с флагом"""
    location_descriptions = {
        "NL": "🇳🇱 Нидерланды",
        "DE": "🇩🇪 Германия",
        "US": "🇺🇸 США",
        "FR": "🇫🇷 Франция",
        "GB": "🇬🇧 Великобритания",
        # Добавьте другие страны по необходимости
    }
    # Если локация неизвестна, возвращаем просто код страны
    return location_descriptions.get(location, f"🌍 {location}")

async def show_subscription(message, state: FSMContext, client):
    data = await state.get_data()
    subscriptions = data.get("subscriptions")
    current_index = data.get("current_index", 0)

    subscription = Subscription(**subscriptions[current_index])
    server = SERVERS.get(subscription.location)
    message_text = (
        f"<b>Ваше имя: </b>{client.name}\n"
        f"<b>E-mail:</b> {client.email}\n\n"
        f"<b>Подписка:</b>\n"
        f"{server.description}\n"
        f"<b>Дата окончания: </b>{subscription.expiry_time}"
    )
    navigation_buttons = []
    if current_index > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_subscription"))
    if current_index < len(subscriptions) - 1:
        navigation_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data="next_subscription"))
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Получить QR-код", callback_data="get_qr_code")],
            navigation_buttons,
            [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
        ]
    )
    await message.edit_text(message_text, parse_mode="HTML", reply_markup=markup)

async def calculate_discount(client: DBClient) -> float:
    referral_count = len(client.referred_users)
    if referral_count >= 50:
        return 50.0
    elif referral_count >= 40:
        return 40.0
    elif referral_count >= 30:
        return 30.0
    elif referral_count >= 20:
        return 20.0
    elif referral_count >= 10:
        return 10.0
    elif referral_count >= 5:
        return 5.0
    elif referral_count > 0:
        return 2.5
    return 0.0

async def generate_referral_code():
    return str(uuid.uuid4())

TARIFFS_DATA = {
    1: Tariff(amount=300, string="месяц", amount_stars=120, label="Подписка на 1 месяц"),
    3: Tariff(amount=810, string="месяца", amount_stars=300, label="Подписка на 3 месяца"),
    6: Tariff(amount=1260, string="месяцев", amount_stars=500, label="Подписка на 6 месяцев"),
    12: Tariff(amount=1800, string="месяцев", amount_stars=700, label="Подписка на 12 месяцев"),
}

# TARIFFS_DATA = {
#     1: Tariff(amount=300, string="месяц", amount_stars=1, label="Подписка на 1 месяц"),
#     3: Tariff(amount=810, string="месяца", amount_stars=1, label="Подписка на 3 месяца"),
#     6: Tariff(amount=1260, string="месяцев", amount_stars=1, label="Подписка на 6 месяцев"),
#     12: Tariff(amount=1800, string="месяцев", amount_stars=1, label="Подписка на 12 месяцев"),
# }

SERVERS = get_servers_from_config()