# import asyncio
# import json
# import logging
# import math
# import uuid
# from os import getenv

# import yookassa
# from aiogram import Bot, Dispatcher, F, types
# from aiogram.enums import ParseMode
# from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, PreCheckoutQuery
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.dispatcher.middlewares.base import BaseMiddleware

# from src.db.models import Subscription, init_db
# from src.api_manager.vpn_panel import VPNPanelAPI
# from src.utils.menus import main_menu, tariff_menu, help_menu, payment_methods, location_menu, help_device
# from src.utils.qr_generator import create_qr_with_logo
# from src.utils.utils import UserData, SERVERS, SubscriptionNavigation, calculate_discount, show_subscription
# from src.payment.cryptomus import create_cryptomus_invoice, check_cryptomus_invoice
# from src.db.db_operations import add_client_to_db, add_subscription_to_profile, confirm_referral, get_client_from_db

# from dotenv import load_dotenv, find_dotenv

# load_dotenv(find_dotenv())

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# bot = Bot(token=getenv("BOT_TOKEN"))
# dp = Dispatcher()
# vpn = json.loads(getenv("VPN"))
# print(vpn)

# yookassa.Configuration.account_id = getenv("YOOKASSA_SHOP_ID")
# yookassa.Configuration.secret_key = getenv("YOOKASSA_API_TOKEN")

# class VPNMiddleware(BaseMiddleware):
#     def __init__(self):
#         super().__init__()
#         self.connections = {}
        
#     async def __call__(self, handler, event, data):
#         # VPN API нужен только для определенных операций
#         needs_vpn = False
#         location = None

#         # Проверяем, нужен ли VPN для текущей операции
#         if hasattr(event, 'data') and event.data:
#             if "check_" in event.data:  # Проверка платежа
#                 needs_vpn = True
#                 if "_payment_" in event.data:
#                     location = event.data.split("_")[2]
#             elif "payment_" in event.data:  # Обработка платежа
#                 needs_vpn = True
#                 location = event.data.split("_")[2]

#         # Если это успешный платеж
#         if hasattr(event, 'successful_payment') and event.successful_payment is not None:
#             needs_vpn = True
#             try:
#                 payment_data = json.loads(event.successful_payment.invoice_payload)
#                 location = payment_data.get('location', 'NL')
#             except Exception as e:
#                 logger.error(f"Error parsing payment data: {e}")
#                 location = "NL"

#         if needs_vpn:
#             location = location or "NL"
#             if location not in self.connections:
#                 try:
#                     vpn_api = VPNPanelAPI(location=location)
#                     await vpn_api.authenticate()
#                     self.connections[location] = vpn_api
#                     logger.info(f"Created new VPN connection for location: {location}")
#                 except Exception as e:
#                     logger.error(f"Failed to create VPN connection for {location}: {e}")
#                     raise

#             data["vpn_api"] = self.connections[location]
#             data["selected_location"] = location

#         try:
#             return await handler(event, data)
#         except Exception as e:
#             if needs_vpn:
#                 logger.error(f"Error in handler for location {location}: {e}")
#             raise

#     async def close_all(self):
#         """Закрыть все соединения"""
#         for location, connection in self.connections.items():
#             try:
#                 await connection.close()
#                 logger.info(f"Closed VPN connection for location: {location}")
#             except Exception as e:
#                 logger.error(f"Error closing VPN connection for {location}: {e}")

# @dp.message(F.text == "/start")
# async def send_welcome(message: Message):
#     logger.info(f"User {message.from_user.id} started the bot.")
#     await message.answer("ShadowGate — Ваш лучший VPN сервис!", reply_markup=main_menu())

# @dp.message(F.text == "/menu")
# async def menu(message: Message):
#     logger.info(f"User {message.from_user.id} accessed the menu.")
#     await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
#     await bot.send_message(
#         chat_id=message.from_user.id,
#         text="ShadowGate — Ваш лучший VPN сервис!",
#         reply_markup=main_menu()
#     )

# @dp.callback_query(F.data == "menu")
# async def main_menu_callback(call: CallbackQuery):
#     logger.info(f"User {call.from_user.id} returned to main menu.")
#     await call.message.edit_text("ShadowGate — Ваш лучший VPN сервис!", reply_markup=main_menu())

# @dp.callback_query(F.data == "connect_vpn")
# async def ask_for_email(call: CallbackQuery, state: FSMContext):
#     logger.info(f"User {call.from_user.id} selected 'Connect VPN'.")
#     client = await get_client_from_db(telegram_id=call.from_user.id)
#     if client:
#         await call.message.edit_text("Выберите локацию:", reply_markup=location_menu())
#     else:
#         await call.message.edit_text("Пожалуйста, введите вашу электронную почту:")
#         await state.set_state(UserData.waiting_for_email)

# @dp.message(UserData.waiting_for_email)
# async def ask_for_name(message: Message, state: FSMContext):
#     email = message.text.strip()
#     if "@" not in email or "." not in email:
#         await message.answer("Пожалуйста, введите корректный адрес электронной почты.")
#         return
#     await state.update_data(email=email)
#     await message.answer("Введите ваше имя:")
#     await state.set_state(UserData.waiting_for_name)

# @dp.message(UserData.waiting_for_name)
# async def save_user_data(message: Message, state: FSMContext):
#     name = message.text.strip()
#     await state.update_data(name=name)
#     await message.answer(
#         "Если у вас есть реферальный код, введите его сейчас. Если нет, нажмите кнопку 'Пропустить'.",
#         reply_markup=InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="Пропустить", callback_data="skip_referral")]
#             ]
#         )
#     )
#     await state.set_state(UserData.waiting_for_referral)

# @dp.message(UserData.waiting_for_referral)
# async def handle_referral_code(message: Message, state: FSMContext):
#     referral_code = message.text.strip()
#     logger.info(f"User {message.from_user.id} entered referral code: {referral_code}")
#     referrer = await get_client_from_db(referral_code=referral_code)
#     if referrer:
#         user_data = await state.get_data()
#         name = user_data.get("name")
#         email = user_data.get("email")
#         logger.info(f"Referral code {referral_code} is valid. Referrer: {referrer.telegram_id}")
#         await add_client_to_db(
#             email=email,
#             telegram_id=message.from_user.id,
#             name=name,
#             referred_by=referral_code,
#             referral_code=uuid.uuid4().hex
#         )

#         await state.clear()
#         await message.answer("Ваши данные успешно сохранены. Выберите локацию:", reply_markup=location_menu())
#     else:
#         logger.warning(f"Invalid referral code entered by user {message.from_user.id}: {referral_code}")
#         await message.answer("Неверный реферальный код. Попробуйте ещё раз или нажмите 'Пропустить'.",
#                              reply_markup=InlineKeyboardMarkup(
#                                  inline_keyboard=[
#                                      [InlineKeyboardButton(text="Пропустить", callback_data="skip_referral")]
#                                  ]
#                              ))

# @dp.callback_query(F.data == "skip_referral")
# async def skip_referral_code(call: CallbackQuery, state: FSMContext):
#     user_data = await state.get_data()
#     name = user_data.get("name")
#     email = user_data.get("email")
#     referred_by = None 
#     logger.info(f"User {call.from_user.id} skipped referral code. Name: {name}, Email: {email}")
#     client_added  = await add_client_to_db(
#         email=email,
#         telegram_id=call.from_user.id,
#         name=name,
#         referred_by=referred_by,
#         referral_code=uuid.uuid4().hex
#     )
#     if not client_added:
#         logger.info(f"User {call.from_user.id} already exists in the database.")
#     else:
#         logger.info(f"User {call.from_user.id} successfully added to the database.")
#     await state.clear()
#     await call.message.edit_text("Ваши данные успешно сохранены. Выберите локацию:", reply_markup=location_menu())

# @dp.callback_query(F.data == "my_referrals")
# async def show_referrals(call: CallbackQuery):
#     logger.info(f"User {call.from_user.id} clicked on 'My Referrals'.")
#     client = await get_client_from_db(telegram_id=call.from_user.id)
#     if not client:
#         logger.warning(f"User {call.from_user.id} not found in the database.")
#         await call.message.edit_text(
#             "Вы не зарегистрированы в системе. Пожалуйста, начните процесс подключения VPN.",
#             parse_mode="HTML",
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [InlineKeyboardButton(text="Подключить VPN", callback_data="connect_vpn")],
#                     [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
#                 ]
#             )
#         )
#         return

#     referred_users = client.referred_users or []
#     referral_code = client.referral_code
#     discount = client.discount or 0
#     logger.info(f"User {call.from_user.id} has {len(referred_users)} referred users and a discount of {discount}%.")
#     if not referred_users:
#         referral_text = (
#             f"Ваш реферальный код: <code>{referral_code}</code>\n"
#             f"Ваша скидка: {discount}%\n\n"
#             "У вас пока нет приглашенных пользователей.\n"
#             "Приглашайте друзей и получайте скидки на подписки!"
#         )
#         logger.info(f"User {call.from_user.id} has no referred users.")
#     else:
#         referral_text = (
#         f"<b>Мои рефералы:</b>\n"
#         f"Ваш реферальный код: <code>{client.referral_code}</code>\n"
#         f"Ваша скидка: {client.discount}%\n\n"
#         f"<b>Приглашенные пользователи:</b> {len(referred_users)}\n\n"
#         )
#         referral_details = []      
#         for index, referral in enumerate(referred_users, start=1):
#             status = "Подтвержден" if referral.get("confirmed") else "Зарегистрирован"
#             referral_details.append(
#                 f"{index}. {referral.get('name', 'Имя не указано')} "
#                 f"({referral.get('email', 'Email не указан')}) — <b>{status}</b>"
#             )
#         referral_text += "\n".join(referral_details)

#     await call.message.edit_text(
#         referral_text,
#         parse_mode="HTML",
#         reply_markup=InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
#             ]
#         )
#     )

# @dp.callback_query(F.data == "help")
# async def help_menu_callback(call: CallbackQuery):
#     logger.info(f"User {call.from_user.id} accessed help menu.")
#     await call.message.edit_text(
#         "Ниже представлены ответы на самые часто задаваемые вопросы.", reply_markup=help_menu()
#     )

# @dp.callback_query(F.data == "help_device")
# async def device_help_callback(call: CallbackQuery):
#     await call.message.edit_text(
#         "Для подключения устройства к VPN, выберите ваш тип устройства и следуйте инструкции:\n\n"
#         "Если вам нужна помощь, свяжитесь с нашей поддержкой.",
#         reply_markup=help_device()
#     )

# @dp.callback_query(F.data == "help_payment")
# async def payment_help_callback(call: CallbackQuery):
#     await call.message.edit_text(
#         "Чтобы оплатить подписку, нажмите «Подключить VPN», выберите нужную локацию и тарифный план, "
#         "выберите способ платежа и проведите оплату.\n\n"
#         "После этого система перенаправит вас на Telegram-бота ShadowGate и ваша подписка станет активна.",
#         reply_markup=InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="Подключить VPN", callback_data="connect_vpn")],
#                 [InlineKeyboardButton(text="Назад", callback_data="help")]
#             ]
#         )
#     )

# @dp.callback_query(F.data == "traffic_limit")
# async def traffic_limit_callback(call: CallbackQuery):
#     await call.message.edit_text(
#         "У ShadowGate есть ограничение на количество устройств, на которые вы можете установить ваш ключ.\n"
#         "Одна подписка - одно устройство!\n"
#         "Зато нет ограничений на скорость соединения, она всегда максимальная!\n\n"
#         "И даже нет ограничения на объем трафика, который можно выкачать за 1 месяц!\n"
#         "Вы и Ваши близкие можете пользоваться нашим сервисом без ограничений.",
#         reply_markup=InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="Назад", callback_data="help")]
#             ]
#         )
#     )

# @dp.callback_query(F.data == "my_subscriptions")
# async def show_subscriptions(call: CallbackQuery, state: FSMContext):
#     client = await get_client_from_db(telegram_id=call.from_user.id)
#     if not client:
#         await call.message.edit_text(
#             "У вас пока нет сохраненных подписок. Вы можете оформить подписку, выбрав локацию.",
#             parse_mode="HTML",
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [InlineKeyboardButton(text="Выбрать локацию", callback_data="connect_vpn")],
#                     [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
#                 ]
#             )
#         )
#         return
#     subscriptions = client.subscriptions or []
#     if not subscriptions:
#         logger.info(f"User {call.from_user.id} has no subscriptions.")
#         await call.message.edit_text(
#             "У вас пока нет подписок. Вы можете оформить подписку, выбрав локацию.",
#             parse_mode="HTML",
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [InlineKeyboardButton(text="Выбрать локацию", callback_data="connect_vpn")],
#                     [InlineKeyboardButton(text="Главная страница", callback_data="menu")],
#                 ]
#             )
#         )
#         return
#     await state.update_data(subscriptions=subscriptions, current_index=0)
#     await show_subscription(call.message, state, client)

# @dp.callback_query(F.data == "next_subscription")
# async def next_subscription(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     current_index = data.get("current_index", 0)
#     subscriptions = data.get("subscriptions")
#     if current_index < len(subscriptions) - 1:
#         await state.update_data(current_index=current_index + 1)
#         client = await get_client_from_db(telegram_id=call.from_user.id)
#         await show_subscription(call.message, state, client)

# @dp.callback_query(F.data == "prev_subscription")
# async def prev_subscription(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     current_index = data.get("current_index", 0)
#     if current_index > 0:
#         await state.update_data(current_index=current_index - 1)
#         client = await get_client_from_db(telegram_id=call.from_user.id)
#         await show_subscription(call.message, state, client)

# @dp.callback_query(F.data == "get_qr_code")
# async def get_qr_code(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     current_index = data.get("current_index", 0)
#     subscriptions = data.get("subscriptions")
#     subscription = Subscription(**subscriptions[current_index])
#     server = SERVERS.get(subscription.location)
#     qr_message = await bot.send_photo(
#         chat_id=call.message.chat.id,
#         photo=FSInputFile(subscription.qr),
#         caption=(
#             f"<b>QR-код для подписки:</b>\n"
#             f"{server.description}\n"
#             f"<b>Дата окончания:</b> {subscription.expiry_time}\n"
#             "<b>Ссылка на конфигурацию:</b>\n"
#             f"<code>{subscription.link}</code>"
#         ),
#         parse_mode="HTML",
#         reply_markup=InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="🔙 Вернуться назад", callback_data="delete_qr_code")],
#             ]
#         ),
#     )
#     await state.update_data(qr_message_id=qr_message.message_id)

# @dp.callback_query(F.data == "delete_qr_code")
# async def delete_qr_code(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     qr_message_id = data.get("qr_message_id")
#     if qr_message_id:
#         try:
#             await bot.delete_message(chat_id=call.message.chat.id, message_id=qr_message_id)
#             await state.update_data(qr_message_id=None)
#         except Exception as e:
#             logger.error(f"Ошибка при удалении сообщения: {e}")
#             await call.answer("Не удалось удалить сообщение. Возможно, оно уже удалено.", show_alert=True)
#     else:
#         await call.answer("Сообщение с QR-кодом не найдено.", show_alert=True)

# @dp.callback_query(F.data.startswith("location_"))
# async def tariff_menu_callback(call: CallbackQuery):
#     location = call.data.split("_")[1]
#     logger.info(f"User {call.from_user.id} selected location: {location}.")
#     await call.message.edit_text("Выберите тариф:", reply_markup=tariff_menu(location))

# @dp.callback_query(F.data.startswith("tariff_"))
# async def tariff_menu_callback(call: CallbackQuery, state: FSMContext):
#     user_data = await state.get_data()
#     referred_by = user_data.get("referred_by")
#     client = await get_client_from_db(telegram_id=call.from_user.id)
#     discount = await calculate_discount(client)
#     location = call.data.split("_")[-1]
#     months = int(call.data.split("_")[1])
#     server = SERVERS.get(location)
#     tariff = server.tariffs[months]
#     discounted_price = tariff.amount * (1 - discount / 100)
#     logger.info(f"User {call.from_user.id} selected tariff: {months} months at location {location}.")
#     await call.message.edit_text(
#         text=f"Выбранный тариф:\n\n"
#             f"{server.description}"
#             f"{tariff.label}\n"
#             f"Сумма к оплате: {discounted_price:.2f} рублей\n\n"
#             f"Выберите способ оплаты:",
#         reply_markup=payment_methods(location=location, months=months)
#     )

# @dp.callback_query(F.data.startswith("payment_"))
# async def payment_menu_callback(call: CallbackQuery):
#     method = call.data.split("_")[1]
#     location = call.data.split("_")[2]
#     months = int(call.data.split("_")[3])
#     server = SERVERS.get(location)
#     tariff = server.tariffs[months]
#     logger.info(f"User {call.from_user.id} selected payment method: {method}.")
#     if method == "stars":
#         await bot.send_invoice(
#             call.message.chat.id,
#             title="Оплата подписки",
#             description="Выбранный тариф:\n\n"
#                         f"{server.description}\n"
#                         f"{tariff.label}",
#             prices=[
#                 types.LabeledPrice(
#                     label=tariff.label,
#                     amount=tariff.amount_stars,
#                 )
#             ],
#             provider_token="",
#             currency="XTR",
#             payload=json.dumps(
#                 {
#                     "method": "stars",
#                     "telegram_id": call.message.chat.id,
#                     "username": call.from_user.username,
#                     "location": location,
#                     "months": months,
#                 }
#             ),
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [
#                         InlineKeyboardButton(
#                             text=f"Оплатить ⭐️ {tariff.amount_stars} ",
#                             pay=True
#                         )
#                     ],
#                     [
#                         InlineKeyboardButton(
#                             text=f"🚫 Отменить оплату",
#                             callback_data=f"cancel_payment_{method}"
#                         )
#                     ]
#                 ]
#             )
#         )
#     elif method == "card":
#         await bot.send_invoice(
#             call.message.chat.id,
#             title="Оплата подписки",
#             description="Выбранный тариф:\n\n"
#                         f"{server.description}\n"
#                         f"{tariff.label}",
#             prices=[
#                 types.LabeledPrice(
#                     label=tariff.label,
#                     amount=tariff.amount * 100,
#                 )
#             ],
#             provider_token=getenv("YOOKASSA_PAYMENT_PROVIDER_TOKEN"),
#             currency="RUB",
#             payload=json.dumps(
#                 {
#                     "method": "card",
#                     "telegram_id": call.message.chat.id,
#                     "username": call.from_user.username,
#                     "location": location,
#                     "months": months,
#                 }
#             ),
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [
#                         InlineKeyboardButton(
#                             text=f"Оплатить {tariff.amount} рублей",
#                             pay=True
#                         )
#                     ],
#                     [
#                         InlineKeyboardButton(
#                             text=f"🚫 Отменить оплату",
#                             callback_data=f"cancel_payment_{method}"
#                         )
#                     ]
#                 ]
#             )
#         )
#     elif method == "yookassa":
#         invoice_id = str(uuid.uuid4())
#         payment = yookassa.Payment.create(
#             {
#                 "amount": {
#                     'value': tariff.amount,
#                     'currency': "RUB"
#                 },
#                 "receipt": {
#                     "customer": {
#                         "email": "abv7777@bk.ru"
#                     },
#                     "items": [
#                         {
#                             "description": "Выбранный тариф:\n\n"
#                                             f"{server.description}\n"
#                                             f"{tariff.label}",
#                             "quantity": 1.000,
#                             "amount": {
#                                 "value": tariff.amount,
#                                 "currency": "RUB"
#                             },
#                             "vat_code": 1,
#                             "payment_mode": "full_prepayment",
#                             "payment_subject": "commodity"
#                         }
#                     ]
#                 },
#                 'confirmation': {
#                     'type': 'redirect',
#                     'return_url': 'https://t.me/ShadowGate_bot'
#                 },
#                 'capture': True,
#                 'metadata': {
#                     'method': method,
#                     'telegram_id': call.from_user.id,
#                     'username': call.from_user.username,
#                     'location': location,
#                     'months': months
#                 },
#                 'description': "Выбранный тариф:\n\n"
#                                 f"{server.description}\n"
#                                 f"{tariff.label}"
#             }, invoice_id
#         )
#         payment_url = payment.confirmation.confirmation_url
#         payment_id = payment.id
#         await bot.send_message(
#             call.message.chat.id,
#             text="Выбранный тариф:\n\n"
#                     f"{server.description}\n"
#                     f"{tariff.label}",
#             reply_markup=InlineKeyboardMarkup(
#                 inline_keyboard=[
#                     [
#                         InlineKeyboardButton(
#                             text=f"Оплатить {tariff.amount} рублей",
#                             url=payment_url
#                         )
#                     ],
#                     [
#                         InlineKeyboardButton(
#                             text="Проверить оплату",
#                             callback_data=f"check_yookassa_payment_{payment_id}"
#                         )
#                     ],
#                     [
#                         InlineKeyboardButton(
#                             text=f"🚫 Отменить оплату",
#                             callback_data=f"cancel_payment_{method}"
#                         )
#                     ]
#                 ]
#             )
#         )
#     elif method == "cryptomus":
#         payment_id = str(uuid.uuid4())
#         invoice = await create_cryptomus_invoice(
#             amount=str(tariff.amount),
#             payment_id=payment_id,
#             telegram_id=call.message.chat.id,
#             username=call.from_user.username,
#             location=location,
#             months=months
#         )
#         await bot.send_message(
#                 chat_id=call.from_user.id,
#                 text="Выбранный тариф:\n\n"
#                         f"{server.description}\n"
#                         f"{tariff.label}",
#                 reply_markup=InlineKeyboardMarkup(
#                     inline_keyboard=[
#                         [
#                             InlineKeyboardButton(
#                                 text=f"Оплатить ${math.ceil(float(invoice["result"]["payer_amount"]))}",
#                                 url=invoice["result"]["url"]
#                             )
#                         ],
#                         [
#                             InlineKeyboardButton(
#                                 text="Проверить оплату",
#                                 callback_data=f"check_cryptomus_payment_{payment_id}"
#                             )
#                         ],
#                         [
#                             InlineKeyboardButton(
#                                 text=f"🚫 Отменить оплату",
#                                 callback_data=f"cancel_payment_{method}"
#                             )
#                         ]
#                     ]
#                 )
#             )
        
# @dp.callback_query(F.data.startswith("cancel_payment_"))
# async def cancel_payment_callback(call: CallbackQuery):
#     await bot.delete_message(
#         chat_id=call.message.chat.id, 
#         message_id=call.message.message_id
#         )

# @dp.callback_query(F.data.startswith("check_"))
# async def check_payment_callback(call: CallbackQuery, vpn_api: VPNPanelAPI):
#     method = call.data.split("_")[1]
#     payment_id = call.data.split("_")[-1]
#     logger.info(f"Checking payment status for user {call.from_user.id} via {method}.")
#     if method == "cryptomus":
#         try:
#             invoice = await check_cryptomus_invoice(payment_id=payment_id)
#             status = invoice["result"]["status"]
#             logger.info(f"Payment status for {call.from_user.id}: {status}.")
#             if status in ["check","paid", "paid_over"]:
#                 payload = json.loads(invoice["result"]["additional_data"])
#                 id = uuid.uuid4()
#                 await vpn_api.add_client(
#                     day=int(payload.get("months")) * 30,
#                     email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}",
#                     id=id
#                 )
#                 client = await vpn_api.get_client(
#                     client_email=f"{id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
#                 )
#                 link = await vpn_api.configure_link(client=client)
#                 create_qr_with_logo(
#                     data=link,
#                     file_path=f"users/qr/{client.client_id}.png"
#                 )
#                 await bot.delete_message(
#                     chat_id=call.message.chat.id, 
#                     message_id=call.message.message_id
#                 )
#                 await bot.send_photo(
#                     chat_id=payload.get("telegram_id"),
#                     photo=FSInputFile(f"users/qr/{client.client_id}.png"),
#                     caption=f"<code>{link}</code>",
#                     parse_mode=ParseMode.HTML
#                 )
#                 await add_subscription_to_profile(
#                     telegram_id=call.from_user.id, 
#                     subscription=Subscription(
#                         subscription_id=client.client_id,
#                         location=payload.get('location'),
#                         expiry_time=payload.get('months'),
#                         qr=f"users/qr/{client.client_id}.png",
#                         link=link
#                     ))
#                 await confirm_referral(referral_telegram_id=call.from_user.id)
#             elif status == "check":
#                 if call.message.text != "Ожидание появления платежа в блокчейне...":
#                     await call.message.edit_text(
#                         text="Ожидание появления платежа в блокчейне...",
#                         reply_markup=InlineKeyboardMarkup(
#                             inline_keyboard=[
#                                 [
#                                     InlineKeyboardButton(
#                                         text="Проверить оплату",
#                                         callback_data=f"check_{method}_payment_{payment_id}"
#                                     )
#                                 ]
#                             ]
#                         )
#                     )
#                 else:
#                     await call.answer(
#                         text="Статус не изменился.", 
#                         show_alert=True
#                     )
#             elif status == "process" or status == "confirm_check":
#                 if call.message.text != "Платеж находится в обработке...":
#                     await call.message.edit_text(
#                         text="Платеж находится в обработке...",
#                         reply_markup=InlineKeyboardMarkup(
#                             inline_keyboard=[
#                                 [
#                                     InlineKeyboardButton(
#                                         text="Проверить оплату",
#                                         callback_data=f"check_{method}_payment_{payment_id}"
#                                     )
#                                 ]
#                             ]
#                         )
#                     )
#                 else:
#                     await call.answer(
#                         text="Статус не изменился.", 
#                         show_alert=True
#                     ) 
#         except Exception as e:
#             logger.error(f"Error checking payment status for user {call.from_user.id}: {e}")
#     if method == "yookassa":
#         try:
#             payment = yookassa.Payment.find_one(payment_id=payment_id)
#             if payment.status == "pending":
#                 payload = payment.metadata
#                 id = uuid.uuid4()
#                 await vpn_api.add_client(
#                         day=int(payload.get("months")) * 30,
#                         email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}",
#                         id=id
#                     )
#                 client = await vpn_api.get_client(
#                     client_email=f"{id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
#                 )
#                 link = await vpn_api.configure_link(client=client)
#                 create_qr_with_logo(
#                     data=link,
#                     file_path=f"users/qr/{client.client_id}.png"
#                 )
#                 await bot.delete_message(
#                     chat_id=call.message.chat.id, 
#                     message_id=call.message.message_id
#                 )
#                 await bot.send_photo(
#                     chat_id=payload.get("telegram_id"),
#                     photo=FSInputFile(f"users/qr/{client.client_id}.png"),
#                     caption=f"<code>{link}</code>",
#                     parse_mode=ParseMode.HTML
#                 )
#                 await add_subscription_to_profile(
#                     telegram_id=call.from_user.id, 
#                     subscription=Subscription(
#                         subscription_id=client.client_id,
#                         location=payload.get('location'),
#                         expiry_time=payload.get('months'),
#                         qr=f"users/qr/{client.client_id}.png",
#                         link=link
#                     ))
#                 await confirm_referral(referral_telegram_id=call.from_user.id)
#             elif payment.status == "pending":
#                 if call.message.text != "Платеж находится в обработке...":
#                     await call.message.edit_text(
#                             text="Платеж находится в обработке...",
#                             reply_markup=InlineKeyboardMarkup(
#                                 inline_keyboard=[
#                                     [
#                                         InlineKeyboardButton(
#                                             text="Проверить оплату",
#                                             callback_data=f"check_{method}_payment_{payment_id}"
#                                         )
#                                     ]
#                                 ]
#                             )
#                         )
#                 else:
#                     await call.answer(
#                         text="Статус не изменился.", 
#                         show_alert=True
#                     ) 
#         except Exception as e:
#             logger.error(f"Error checking payment status for user {call.from_user.id}: {e}")

# @dp.pre_checkout_query()
# async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
#     await pre_checkout_query.answer(ok=True)

# @dp.message(F.successful_payment)
# async def success_stars_payment_handler(message: Message, vpn_api: VPNPanelAPI):
#     payload = json.loads(message.successful_payment.invoice_payload)
#     id = uuid.uuid4()
#     await vpn_api.add_client(
#         day=int(payload.get("months")) * 30, 
#         email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}", 
#         id=id
#     )
#     client = await vpn_api.get_client(
#         client_email=f"{id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
#     )
#     link = await vpn_api.configure_link(client=client)
#     create_qr_with_logo(
#         data=link,
#         file_path=f"users/qr/{client.client_id}.png"
#     )
#     await bot.send_photo(
#         chat_id=payload.get("telegram_id"),
#         photo=FSInputFile(f"users/qr/{client.client_id}.png"),
#         caption=f"<code>{link}</code>",
#         parse_mode=ParseMode.HTML
#     )
#     await add_subscription_to_profile(
#         telegram_id=payload.get("telegram_id"), 
#         subscription=Subscription(
#             subscription_id=client.client_id,
#             location=payload.get('location'),
#             expiry_time=payload.get('months'),
#             qr=f"users/qr/{client.client_id}.png",
#             link=link
#         ))
#     await confirm_referral(referral_telegram_id=payload.get("telegram_id"))

# # Регистрация middleware
# dp.message.middleware.register(VPNMiddleware())
# dp.callback_query.middleware.register(VPNMiddleware())

# async def main():
#     # Создаем middleware
#     vpn_middleware = VPNMiddleware()
    
#     try:
#         # Регистрируем middleware
#         dp.message.middleware.register(vpn_middleware)
#         dp.callback_query.middleware.register(vpn_middleware)
        
#         # Инициализируем базу данных
#         await init_db()
#         print("DB initialized successfully.")
        
#         # Запускаем бота
#         await dp.start_polling(bot)
#     finally:
#         # Закрываем все VPN соединения при завершении
#         await vpn_middleware.close_all()

# if __name__ == '__main__':
#     asyncio.run(main())

# vpn_bot.py

import asyncio
import logging
from os import getenv

import yookassa
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv, find_dotenv

from db.models import init_db
from handlers import router
from middleware.vpn import VPNMiddleware

load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=getenv("BOT_TOKEN"))
dp = Dispatcher()

# Настройка YooKassa
yookassa.Configuration.account_id = getenv("YOOKASSA_SHOP_ID")
yookassa.Configuration.secret_key = getenv("YOOKASSA_API_TOKEN")

# Подключаем все роутеры
dp.include_router(router)

async def main():
    # Создаем middleware
    vpn_middleware = VPNMiddleware()
    
    try:
        # Регистрируем middleware
        dp.message.middleware.register(vpn_middleware)
        dp.callback_query.middleware.register(vpn_middleware)
        
        # Инициализируем базу данных
        await init_db()
        print("DB initialized successfully.")
        
        # Запускаем бота
        await dp.start_polling(bot)
    finally:
        # Закрываем все VPN соединения при завершении
        await vpn_middleware.close_all()

if __name__ == '__main__':
    asyncio.run(main())