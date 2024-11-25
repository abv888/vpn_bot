# # payment.py
# import requests
# from config import YOOKASSA_API_KEY, CRYPTO_API_URL
# from src.db.database import Database
#
# db = Database()
#
# async def create_yookassa_payment(user_id, subscription_type, amount):
#     url = "https://api.yookassa.ru/v3/payments"
#     headers = {
#         "Authorization": f"Bearer {YOOKASSA_API_KEY}"
#     }
#     data = {
#         "amount": {"value": str(amount), "currency": "RUB"},
#         "capture": True,
#         "confirmation": {"type": "redirect", "return_url": "https://your_redirect_url"},
#         "description": f"Оплата подписки: {subscription_type}",
#         "metadata": {"user_id": user_id, "subscription_type": subscription_type}
#     }
#     response = requests.post(url, json=data, headers=headers)
#     if response.status_code == 200:
#         await db.add_payment(user_id, subscription_type, amount, "yookassa")
#         return response.json()["confirmation"]["confirmation_url"]
#     return None
#
# async def create_crypto_payment(user_id, subscription_type, amount):
#     url = f"{CRYPTO_API_URL}/create_payment"
#     headers = {"Authorization": f"Bearer {YOOKASSA_API_KEY}"}
#     data = {
#         "amount": amount,
#         "currency": "BTC",
#         "description": f"Оплата подписки: {subscription_type}",
#         "callback_url": PAYMENT_WEBHOOK_URL,
#         "metadata": {"user_id": user_id, "subscription_type": subscription_type}
#     }
#     response = requests.post(url, json=data, headers=headers)
#     if response.status_code == 200:
#         await db.add_payment(user_id, subscription_type, amount, "crypto")
#         return response.json()["payment_url"]
#     return None
#
# async def handle_payment_webhook(data):
#     payment_id = data.get("payment_id")
#     status = data.get("status")
#     if status == "succeeded":
#         payment = await db.get_payment_by_id(payment_id)
#         if payment:
#             user_id = payment["user_id"]
#             subscription_type = payment["subscription_type"]
#             days = {"1_month": 30, "6_months": 180, "12_months": 365}.get(subscription_type, 0)
#             await db.update_payment_status(payment_id, "completed")
#             await add_paid_subscription(user_id, subscription_type, days)
#     else:
#         await db.update_payment_status(payment_id, "failed")
