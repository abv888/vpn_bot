# # database.py

# import asyncpg
# import uuid
# from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST
# from datetime import datetime, timedelta

# class Database:
#     def __init__(self):
#         self.pool = None

#     async def connect(self):
#         self.pool = await asyncpg.create_pool(
#             database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
#         )
#         await self.create_tables()

#     async def create_tables(self):
#         async with self.pool.acquire() as conn:
#             await conn.execute("""
#                 CREATE TABLE IF NOT EXISTS users (
#                     telegram_id BIGINT PRIMARY KEY,
#                     telegram_username VARCHAR(50),
#                     name VARCHAR(100),
#                     email VARCHAR(100),
#                     subscriptions JSONB DEFAULT '[]'::jsonb
#                 );
#             """)

#     async def add_user(self, telegram_id, telegram_username):
#         async with self.pool.acquire() as conn:
#             await conn.execute(
#                 "INSERT INTO users (telegram_id, telegram_username) VALUES ($1, $2) ON CONFLICT (telegram_id) DO NOTHING",
#                 telegram_id, telegram_username
#             )

#     async def update_user_info(self, telegram_id, name, email):
#         async with self.pool.acquire() as conn:
#             await conn.execute(
#                 "UPDATE users SET name = $1, email = $2 WHERE telegram_id = $3",
#                 name, email, telegram_id
#             )

#     async def add_subscription(self, telegram_id, geolocation, duration_days):
#         async with self.pool.acquire() as conn:
#             subscription_id = str(uuid.uuid4())
#             start_date = datetime.now()
#             end_date = start_date + timedelta(days=duration_days)

#             new_subscription = {
#                 "subscription_id": subscription_id,
#                 "geolocation": geolocation,
#                 "start_date": start_date.isoformat(),
#                 "end_date": end_date.isoformat(),
#                 "status": "active"
#             }

#             await conn.execute("""
#                 UPDATE users
#                 SET subscriptions = subscriptions || $1::jsonb
#                 WHERE telegram_id = $2
#             """, new_subscription, telegram_id)

#     async def update_subscription_location(self, telegram_id, geolocation):
#         async with self.pool.acquire() as conn:
#             await conn.execute("""
#                 UPDATE users
#                 SET subscriptions = jsonb_set(
#                     subscriptions,
#                     '{0, geolocation}',
#                     $1::text,
#                     false
#                 )
#                 WHERE telegram_id = $2
#             """, geolocation, telegram_id)

#     async def get_active_subscriptions(self, telegram_id):
#         async with self.pool.acquire() as conn:
#             row = await conn.fetchrow(
#                 "SELECT subscriptions FROM users WHERE telegram_id = $1", telegram_id
#             )
#             if row and row["subscriptions"]:
#                 # Фильтруем активные подписки
#                 active_subscriptions = [
#                     sub for sub in row["subscriptions"] if sub["status"] == "active"
#                 ]
#                 return active_subscriptions
#             return []

#     async def update_subscription_status(self):
#         async with self.pool.acquire() as conn:
#             await conn.execute("""
#                 UPDATE users
#                 SET subscriptions = jsonb_set(
#                     subscriptions,
#                     '{status}',
#                     '"expired"',
#                     false
#                 )
#                 WHERE EXISTS (
#                     SELECT * FROM jsonb_array_elements(subscriptions) AS sub
#                     WHERE sub->>'end_date' < $1
#                 )
#             """, datetime.now().isoformat())

#     async def close(self):
#         await self.pool.close()
