from os import getenv
import json
import hashlib
import base64
import aiohttp

def generate_headers(data: str):
    api_key = getenv("CRYPTOMUS_API_KEY")
    merchant_id = getenv("CRYPTOMUS_MERCHANT_ID")
    
    if not api_key or not merchant_id:
        raise ValueError("API_KEY или MERCHANT_ID не установлены")

    sign = hashlib.md5(
        (base64.b64encode(data.encode("ascii")) + api_key.encode("ascii"))
    ).hexdigest()

    return {
        "merchant": merchant_id,
        "sign": sign,
        "Content-Type": "application/json",
    }

async def create_cryptomus_invoice(amount: int, payment_id: str, telegram_id: int, username: str, location: str, months: int):
    data = {
        "amount": str(amount),
        "order_id": payment_id,
        "currency": "RUB",
        "lifetime": 900,
        "to_currency": "USDT",
        "additional_data": json.dumps({
            "method": "cryptomus",
            "telegram_id": telegram_id,
            "username": username,
            "location": location,
            "months": months,
        })
    }
    url = getenv("CRYPTOMUS_PAYMENT_URL")
    if not url:
        raise ValueError("CRYPTOMUS_PAYMENT_URL не установлен")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=url,
            data=json.dumps(data),
            headers=generate_headers(json.dumps(data))
            ) as response:
            if response.status != 200:
                raise Exception("Не удалось создать инвойс Cryptomus")
            return await response.json()

async def check_cryptomus_invoice(payment_id: str):
    if not payment_id:
        raise ValueError("UUID не может быть пустым")

    data = {
        "order_id": payment_id
    }

    url = getenv("CRYPTOMUS_CHECK_URL")
    if not url:
        raise ValueError("CRYPTOMUS_CHECK_URL не установлен")
    

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=url,
            data=json.dumps(data),
            headers=generate_headers(json.dumps(data))
            ) as response:
            if response.status != 200:
                raise Exception("Не удалось проверить платеж Cryptomus")
            return await response.json()
