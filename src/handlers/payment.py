from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    LabeledPrice,
    PreCheckoutQuery,
    Message,
    FSInputFile
)
from aiogram.enums import ParseMode
import yookassa
from utils.utils import SERVERS
from utils.menus import payment_methods
from utils.qr_generator import create_qr_with_logo
from payment.cryptomus import create_cryptomus_invoice, check_cryptomus_invoice
from db.db_operations import add_subscription_to_profile, confirm_referral, get_client_from_db
from db.models import Subscription
from api_manager.vpn_panel import VPNPanelAPI
import json
import uuid
import math
import logging
from os import getenv

logger = logging.getLogger(__name__)

payment_router = Router()

@payment_router.callback_query(F.data.startswith("tariff_"))
async def handle_tariff_selection(call: CallbackQuery):
    _, months, location = call.data.split("_")
    months = int(months)
    client = await get_client_from_db(telegram_id=call.from_user.id)
    discount = client.discount if client else 0
    server = SERVERS.get(location)
    tariff = server.tariffs[months]
    discounted_price = tariff.amount * (1 - discount / 100)
    
    logger.info(f"User {call.from_user.id} selected tariff: {months} months at location {location}.")
    await call.message.edit_text(
        text=f"Выбранный тариф:\n\n"
            f"{server.description}"
            f"{tariff.label}\n"
            f"Сумма к оплате: {discounted_price:.2f} рублей\n\n"
            f"Выберите способ оплаты:",
        reply_markup=payment_methods(location=location, months=months)
    )

@payment_router.callback_query(F.data.startswith("payment_"))
async def handle_payment_method(call: CallbackQuery, bot: Bot):
    method = call.data.split("_")[1]
    location = call.data.split("_")[2]
    months = int(call.data.split("_")[3])
    server = SERVERS.get(location)
    tariff = server.tariffs[months]
    
    logger.info(f"User {call.from_user.id} selected payment method: {method}.")
    
    if method == "stars":
        await bot.send_invoice(
            call.message.chat.id,
            title="Оплата подписки",
            description=f"Выбранный тариф:\n\n{server.description}\n{tariff.label}",
            payload=json.dumps({
                "method": "stars",
                "telegram_id": call.message.chat.id,
                "username": call.from_user.username,
                "location": location,
                "months": months,
            }),
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=tariff.label, amount=tariff.amount_stars)],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Оплатить ⭐️ {tariff.amount_stars}", pay=True)],
                [InlineKeyboardButton(text="🚫 Отменить оплату", callback_data=f"cancel_payment_{method}")]
            ])
        )
    
    elif method == "card":
        await bot.send_invoice(
            call.message.chat.id,
            title="Оплата подписки",
            description=f"Выбранный тариф:\n\n{server.description}\n{tariff.label}",
            payload=json.dumps({
                "method": "card",
                "telegram_id": call.message.chat.id,
                "username": call.from_user.username,
                "location": location,
                "months": months,
            }),
            provider_token=getenv("YOOKASSA_PAYMENT_PROVIDER_TOKEN"),
            currency="RUB",
            prices=[LabeledPrice(label=tariff.label, amount=tariff.amount * 100)],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Оплатить {tariff.amount} рублей", pay=True)],
                [InlineKeyboardButton(text="🚫 Отменить оплату", callback_data=f"cancel_payment_{method}")]
            ])
        )
    
    elif method == "yookassa":
        invoice_id = str(uuid.uuid4())
        payment = yookassa.Payment.create({
            "amount": {
                'value': tariff.amount,
                'currency': "RUB"
            },
            "receipt": {
                "customer": {
                    "email": "abv7777@bk.ru"
                },
                "items": [{
                    "description": f"Выбранный тариф:\n\n{server.description}\n{tariff.label}",
                    "quantity": 1.000,
                    "amount": {
                        "value": tariff.amount,
                        "currency": "RUB"
                    },
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "commodity"
                }]
            },
            'confirmation': {
                'type': 'redirect',
                'return_url': 'https://t.me/ShadowGate_bot'
            },
            'capture': True,
            'metadata': {
                'method': method,
                'telegram_id': str(call.from_user.id),
                'username': call.from_user.username,
                'location': location,
                'months': months
            },
            'description': f"Выбранный тариф:\n\n{server.description}\n{tariff.label}"
        }, invoice_id)
        
        payment_url = payment.confirmation.confirmation_url
        payment_id = payment.id
        
        await bot.send_message(
            call.message.chat.id,
            text=f"Выбранный тариф:\n\n{server.description}\n{tariff.label}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Оплатить {tariff.amount} рублей", url=payment_url)],
                [InlineKeyboardButton(text="Проверить оплату", callback_data=f"check_yookassa_payment_{payment_id}")],
                [InlineKeyboardButton(text="🚫 Отменить оплату", callback_data=f"cancel_payment_{method}")]
            ])
        )
    
    elif method == "cryptomus":
        payment_id = str(uuid.uuid4())
        invoice = await create_cryptomus_invoice(
            amount=str(tariff.amount),
            payment_id=payment_id,
            telegram_id=call.message.chat.id,
            username=call.from_user.username,
            location=location,
            months=months
        )
        
        await bot.send_message(
            chat_id=call.from_user.id,
            text=f"Выбранный тариф:\n\n{server.description}\n{tariff.label}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Оплатить ${math.ceil(float(invoice['result']['payer_amount']))}",
                    url=invoice["result"]["url"]
                )],
                [InlineKeyboardButton(
                    text="Проверить оплату",
                    callback_data=f"check_cryptomus_payment_{payment_id}"
                )],
                [InlineKeyboardButton(
                    text="🚫 Отменить оплату",
                    callback_data=f"cancel_payment_{method}"
                )]
            ])
        )

@payment_router.callback_query(F.data.startswith("cancel_payment_"))
async def cancel_payment(call: CallbackQuery, bot: Bot):
    await bot.delete_message(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id
    )

@payment_router.callback_query(F.data.startswith("check_"))
async def check_payment(call: CallbackQuery, bot: Bot, vpn_api: VPNPanelAPI):
    method = call.data.split("_")[1]
    payment_id = call.data.split("_")[-1]
    user_id_str = str(call.from_user.id)
    logger.info(f"Checking payment status for user {call.from_user.id} via {method}.")
    
    if method == "cryptomus":
        try:
            invoice = await check_cryptomus_invoice(payment_id=payment_id)
            status = invoice["result"]["status"]
            logger.info(f"Payment status for {call.from_user.id}: {status}.")
            
            if status in ["check", "paid", "paid_over"]:
                payload = json.loads(invoice["result"]["additional_data"])
                client_id = str(uuid.uuid4())
                
                await vpn_api.add_client(
                    day=int(payload.get("months")) * 30,
                    email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}",
                    id=client_id
                )
                
                client = await vpn_api.get_client(
                    client_email=f"{client_id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
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
                    chat_id=int(payload.get("telegram_id")),
                    photo=FSInputFile(f"users/qr/{client.client_id}.png"),
                    caption=f"<code>{link}</code>",
                    parse_mode=ParseMode.HTML
                )
                
                await add_subscription_to_profile(
                    telegram_id=int(user_id_str), 
                    subscription=Subscription(
                        subscription_id=client.client_id,
                        location=payload.get('location'),
                        expiry_time=30 * payload.get('months'),
                        qr=f"users/qr/{client.client_id}.png",
                        link=link
                    ))
                
                await confirm_referral(referral_telegram_id=int(user_id_str))
            
            elif status == "check":
                if call.message.text != "Ожидание появления платежа в блокчейне...":
                    await call.message.edit_text(
                        text="Ожидание появления платежа в блокчейне...",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="Проверить оплату",
                                callback_data=f"check_{method}_payment_{payment_id}"
                            )]
                        ])
                    )
                else:
                    await call.answer(
                        text="Статус не изменился.", 
                        show_alert=True
                    )
            
            elif status == "process" or status == "confirm_check":
                if call.message.text != "Платеж находится в обработке...":
                    await call.message.edit_text(
                        text="Платеж находится в обработке...",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="Проверить оплату",
                                callback_data=f"check_{method}_payment_{payment_id}"
                            )]
                        ])
                    )
                else:
                    await call.answer(
                        text="Статус не изменился.", 
                        show_alert=True
                    )
        except Exception as e:
            logger.error(f"Error checking payment status for user {call.from_user.id}: {e}")
    
    elif method == "yookassa":
        try:
            user_id_str = str(call.from_user.id)
            payment = yookassa.Payment.find_one(payment_id=payment_id)
            if payment.status == "succeeded":
                payload = payment.metadata
                client_id = str(uuid.uuid4())

                
                await vpn_api.add_client(
                    day=int(payload.get("months")) * 30,
                    email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}",
                    id=client_id
                )
                
                client = await vpn_api.get_client(
                    client_email=f"{client_id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
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
                    chat_id=payload.get("telegram_id"),
                    photo=FSInputFile(f"users/qr/{client.client_id}.png"),
                    caption=f"<code>{link}</code>",
                    parse_mode=ParseMode.HTML
                )
                
                await add_subscription_to_profile(
                    telegram_id=call.from_user.id, 
                    subscription=Subscription(
                        subscription_id=client.client_id,
                        location=payload.get('location'),
                        expiry_time=30 * payload.get('months'),
                        qr=f"users/qr/{client.client_id}.png",
                        link=link
                    ))
                
                await confirm_referral(referral_telegram_id=call.from_user.id)
            
            elif payment.status == "pending":
                if call.message.text != "Платеж находится в обработке...":
                    await call.message.edit_text(
                        text="Платеж находится в обработке...",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="Проверить оплату",
                                callback_data=f"check_{method}_payment_{payment_id}"
                            )]
                        ])
                    )
                else:
                    await call.answer(
                        text="Статус не изменился.", 
                        show_alert=True
                    )
        except Exception as e:
            logger.error(f"Error checking payment status for user {call.from_user.id}: {e}")

@payment_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@payment_router.message(F.successful_payment)
async def success_payment_handler(message: Message, bot: Bot, vpn_api: VPNPanelAPI):
    payload = json.loads(message.successful_payment.invoice_payload)
    client_id = str(uuid.uuid4())
    
    await vpn_api.add_client(
        day=int(payload.get("months")) * 30,
        email=f"{payload.get('username')}-{payload.get('location')}-{payload.get('months')}",
        id=client_id
    )
    
    client = await vpn_api.get_client(
        client_email=f"{client_id}-{payload.get('username')}-{payload.get('location')}-{payload.get('months')}"
    )
    
    link = await vpn_api.configure_link(client=client)
    create_qr_with_logo(
        data=link,
        file_path=f"users/qr/{client.client_id}.png"
    )
    
    await bot.send_photo(
        chat_id=payload.get("telegram_id"),
        photo=FSInputFile(f"users/qr/{client.client_id}.png"),
        caption=f"<code>{link}</code>",
        parse_mode=ParseMode.HTML
    )
    
    await add_subscription_to_profile(
        telegram_id=payload.get("telegram_id"),
        subscription=Subscription(
            subscription_id=client.client_id,
            location=payload.get('location'),
            expiry_time=30 * payload.get('months'),
            qr=f"users/qr/{client.client_id}.png",
            link=link
        ))
    
    await confirm_referral(referral_telegram_id=payload.get("telegram_id"))