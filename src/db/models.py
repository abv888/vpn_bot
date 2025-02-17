import enum
from os import getenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Float, Integer, String, Text, JSON

Base = declarative_base()

class Subscription:
    def __init__(self, subscription_id, location, expiry_time, qr, link):
        self.subscription_id = subscription_id
        self.location = location
        self.expiry_time = expiry_time
        self.qr = qr
        self.link = link
    
    def to_dict(self):
        return {
            "subscription_id": self.subscription_id,
            "location": self.location,
            "expiry_time": self.expiry_time,
            "qr": self.qr,
            "link": self.link,
        }
class ReferralStatus(str, enum.Enum):
    REGISTERED = "registered"
    CONFIRMED = "confirmed"

class DBClient(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    subscriptions = Column(JSON, default=[])
    referral_code = Column(String, unique=True, nullable=True)
    referred_by = Column(String, nullable=True)
    referred_users =  Column(JSON, default=list)
    discount = Column(Float, default=0.0)

async_engine = create_async_engine(
    f"postgresql+asyncpg://{getenv("DB_USER")}:{getenv("DB_PASSWORD")}@{getenv("DB_HOST")}:5432/{getenv("DB_NAME")}",
    echo=True,
    pool_pre_ping=True,
    pool_recycle=1800
)

AsyncSession = async_sessionmaker(
    async_engine, expire_on_commit=False
)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)