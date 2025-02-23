import asyncio
import logging
from os import getenv
from pathlib import Path

import yookassa
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv, find_dotenv

from db.models import init_db
from handlers import router
from middleware.vpn import VPNMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

env_path =Path('.env')

logger.info(f"File exists: {env_path.exists()}")

load_dotenv(env_path)

logger.info("Checking environment variables:")
logger.info(f"DB_USER: {'Set' if getenv('DB_USER') else 'Not set'}")
logger.info(f"DB_PASSWORD: {'Set' if getenv('DB_PASSWORD') else 'Not set'}")
logger.info(f"VPN: {'Set' if getenv('VPN') else 'Not set'}")



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