from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.utils.utils import generate_referral_code
from .models import AsyncSession, DBClient, Subscription, async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)

async def add_client_to_db(email: str, telegram_id: int, name: str, referral_code: str, referred_by=None):
    try:
        async with async_session() as session:
            logger.info(f"Checking if user {telegram_id} already exists in the database.")
            
            # Проверяем, существует ли пользователь
            existing_client_query = await session.execute(
                select(DBClient).where(DBClient.telegram_id == telegram_id)
            )
            existing_client = existing_client_query.scalar_one_or_none()

            if existing_client:
                logger.warning(f"User {telegram_id} already exists in the database.")
                return False
            logger.info(
                f"Adding new user {telegram_id} to the database. "
                f"Name: {name}, Email: {email}, Referral Code: {referral_code}."
            )
            new_client = DBClient(
                email=email,
                telegram_id=telegram_id,
                name=name,
                referral_code=referral_code,
                referred_users=[],
                referred_by=referred_by
            )
            session.add(new_client)
            await session.commit()
            logger.info(f"User {telegram_id} added successfully.")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database error while adding user {telegram_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while adding user {telegram_id}: {e}")

async def get_client_from_db(telegram_id=None, referral_code=None) -> Optional[DBClient]:
    async with async_session() as session:
        if telegram_id:
            logger.info(f"Fetching client from database by Telegram ID: {telegram_id}")
            result = await session.execute(
                select(DBClient).where(DBClient.telegram_id == telegram_id)
            )
        elif referral_code:
            logger.info(f"Fetching client from database by Referral Code: {referral_code}")
            result = await session.execute(
                select(DBClient).where(DBClient.referral_code == referral_code)
            )
        else:
            logger.warning("Neither Telegram ID nor Referral Code provided to fetch client.")
            return None

        client = result.scalar_one_or_none()
        if client:
            logger.info(f"Client found: {client.telegram_id if telegram_id else client.referral_code}")
        else:
            logger.warning(f"Client not found in the database. Telegram ID: {telegram_id}, Referral Code: {referral_code}")
        return client

    
async def add_subscription_to_profile(telegram_id: int, subscription: Subscription):
    async with async_session() as session:
        result = await session.execute(
            select(DBClient).where(DBClient.telegram_id == telegram_id)
        )
        client = result.scalar_one_or_none()
        if client:
            updated_subscriptions: List[dict] = client.subscriptions or []
            expiry_date = datetime.now() + timedelta(days=30 * int(subscription.expiry_time))
            subscription.expiry_time = expiry_date.strftime("%d.%m.%Y %H:%M:%S")
            updated_subscriptions.append(subscription.to_dict())
            await session.execute(
                update(DBClient)
                .where(DBClient.telegram_id == telegram_id)
                .values(subscriptions=updated_subscriptions)
            )
            await session.commit()
        else:
            raise ValueError(f"Клиент с telegram_id {telegram_id} не найден.")
        
async def add_referral_to_referrer(referrer_telegram_id: int, referral_telegram_id: int):
    async with async_session() as session:
        referrer = await session.execute(
            select(DBClient).where(DBClient.telegram_id == referrer_telegram_id)
        ).scalar_one_or_none()
        if referrer:
            if not any(r["telegram_id"] == referral_telegram_id for r in referrer.referred_users):
                referrer.referred_users.append({"telegram_id": referral_telegram_id, "status": "registered"})
                await session.commit()
                logger.info(f"Added referral {referral_telegram_id} to referrer {referrer_telegram_id} with status 'registered'.")

async def confirm_referral(referral_telegram_id: int):
    async with async_session() as session:
        referral = await session.execute(
            select(DBClient).where(DBClient.telegram_id == referral_telegram_id)
        ).scalar_one_or_none()

        if referral and referral.referred_by:
            referrer = await session.execute(
                select(DBClient).where(DBClient.telegram_id == referral.referred_by)
            ).scalar_one_or_none()

            if referrer:
                for r in referrer.referred_users:
                    if r["telegram_id"] == referral_telegram_id and r["status"] == "registered":
                        r["status"] = "confirmed"
                        referrer.discount += 5
                        break
                await session.commit()
                logger.info(f"Referral {referral_telegram_id} confirmed for referrer {referrer.telegram_id}. Discount updated to {referrer.discount}.")
            else:
                return
        