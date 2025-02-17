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

bot = Bot(token=getenv("BOT_TOKEN"))
dp = Dispatcher()

yookassa.Configuration.account_id = getenv("YOOKASSA_SHOP_ID")
yookassa.Configuration.secret_key = getenv("YOOKASSA_API_TOKEN")

dp.include_router(router)

async def main():
    vpn_middleware = VPNMiddleware()
    
    try:
        dp.message.middleware.register(vpn_middleware)
        dp.callback_query.middleware.register(vpn_middleware)
        
        await init_db()
        print("DB initialized successfully.")
        
        await dp.start_polling(bot)
    finally:
        await vpn_middleware.close_all()

if __name__ == '__main__':
    asyncio.run(main())