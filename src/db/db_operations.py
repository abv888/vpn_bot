from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from utils.utils import calculate_discount, generate_referral_code
from .models import AsyncSession, DBClient, Subscription, async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)

async def add_client_to_db(telegram_id: int):
    try:
        async with async_session() as session:
            logger.info(f"Checking if user {telegram_id} already exists in the database.")
            
            # Проверяем, существует ли пользователь
            existing_client_query = await session.execute(
                select(DBClient).where(DBClient.telegram_id == int(telegram_id))
            )
            existing_client = existing_client_query.scalar_one_or_none()

            if existing_client:
                logger.warning(f"User {telegram_id} already exists in the database.")
                return False

            logger.info(f"Adding new user {telegram_id} to the database.")
            new_client = DBClient(
                telegram_id=telegram_id,
                referral_code=str(uuid.uuid4().hex),
                email=None,
                name=None,
                referred_users=[],
                referred_by=None,
                discount=0.0
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
                select(DBClient).where(DBClient.telegram_id == int(telegram_id))
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
    

async def update_client_in_db(telegram_id: int, email: str = None, name: str = None, referred_by: str = None):
    try:
        async with async_session() as session:
            logger.info(f"Updating user {telegram_id} in the database.")
            
            update_data = {}
            if email is not None:
                update_data['email'] = email
            if name is not None:
                update_data['name'] = name
            if referred_by is not None:
                update_data['referred_by'] = referred_by

            if not update_data:
                logger.warning("No data provided for update")
                return False

            result = await session.execute(
                update(DBClient)
                .where(DBClient.telegram_id == int(telegram_id))
                .values(**update_data)
            )
            await session.commit()

            if result.rowcount > 0:
                logger.info(f"User {telegram_id} updated successfully.")
                return True
            else:
                logger.warning(f"User {telegram_id} not found for update.")
                return False

    except SQLAlchemyError as e:
        logger.error(f"Database error while updating user {telegram_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while updating user {telegram_id}: {e}")
        return False

    
async def add_subscription_to_profile(telegram_id: int, subscription: Subscription):
    async with async_session() as session:
        result = await session.execute(
            select(DBClient).where(DBClient.telegram_id == int(telegram_id))
        )
        client = result.scalar_one_or_none()
        if client:
            updated_subscriptions: List[dict] = client.subscriptions or []
            expiry_date = datetime.now() + timedelta(days=int(subscription.expiry_time))
            subscription.expiry_time = expiry_date.strftime("%d.%m.%Y %H:%M:%S")
            updated_subscriptions.append(subscription.to_dict())
            await session.execute(
                update(DBClient)
                .where(DBClient.telegram_id == int(telegram_id))
                .values(subscriptions=updated_subscriptions)
            )
            await session.commit()
        else:
            raise ValueError(f"Клиент с telegram_id {telegram_id} не найден.")
        
async def add_referral_to_referrer(referrer_telegram_id: int, referral_telegram_id: int):
    try:
        async with async_session() as session:
            logger.info(f"Adding referral {referral_telegram_id} to referrer {referrer_telegram_id}")
            
            # Изменяем способ получения результата запроса
            query = select(DBClient).where(DBClient.telegram_id == int(referrer_telegram_id))
            result = await session.execute(query)
            referrer = result.scalar()  # Используем scalar() вместо scalar_one_or_none()
            
            if referrer:
                logger.info(f"Found referrer, current referred_users: {referrer.referred_users}")
                
                # Проверяем, существует ли уже такой реферал
                if not referrer.referred_users:
                    referrer.referred_users = []
                
                if not any(r.get("telegram_id") == int(referral_telegram_id) for r in referrer.referred_users):
                    new_referred_users = referrer.referred_users.copy()
                    new_referred_users.append({
                        "telegram_id": int(referral_telegram_id),
                        "status": "registered"
                    })
                    
                    # Явно обновляем в базе именно referred_users
                    stmt = (
                        update(DBClient)
                        .where(DBClient.telegram_id == int(referrer_telegram_id))
                        .values({"referred_users": new_referred_users})
                    )
                    await session.execute(stmt)
                    await session.commit()
                else:
                    logger.info(f"Referral {referral_telegram_id} already exists in list")
            else:
                logger.error(f"Referrer with telegram_id {referrer_telegram_id} not found")
                
    except Exception as e:
        logger.error(f"Error in add_referral_to_referrer: {str(e)}")
        # Перевыбрасываем исключение, чтобы обработать его на уровне выше
        raise

async def confirm_referral(referral_telegram_id: int):
    try:
        async with async_session() as session:
            logger.info(f"Starting confirm_referral for user ID {referral_telegram_id}")
            
            result = await session.execute(
                select(DBClient).where(DBClient.telegram_id == int(referral_telegram_id))
            )
            referral = result.scalar()

            if referral and referral.referred_by:
                referrer_result = await session.execute(
                    select(DBClient).where(DBClient.referral_code == str(referral.referred_by))
                )
                referrer = referrer_result.scalar()

                if referrer:
                    if not referrer.referred_users:
                        referrer.referred_users = []

                    for r in referrer.referred_users:
                        if str(r.get("telegram_id")) == str(referral_telegram_id):
                            if r["status"] == "confirmed":
                                logger.info(f"Referral {referral_telegram_id} already confirmed")
                                return  
                            elif r["status"] == "registered":
                                r["status"] = "confirmed"
                                if not hasattr(referrer, 'discount'):
                                    referrer.discount = 0
                                new_discount = await calculate_discount(referrer)
                                referrer.discount = new_discount
                                await session.commit()
                                logger.info(f"Confirmed referral {referral_telegram_id} and updated discount to {referrer.discount}")
                                return
                    
                    logger.warning(f"Referral {referral_telegram_id} not found in referred_users list")
                else:
                    logger.error(f"Referrer not found for referral code {referral.referred_by}")
    except Exception as e:
        logger.error(f"Error in confirm_referral: {str(e)}")
        