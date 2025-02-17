from aiogram import Router
from .start import start_router
from .help import help_router
from .subscription import subscription_router
from .referral import referral_router
from .payment import payment_router

# Создаем общий роутер
router = Router()

# Включаем все роутеры
router.include_router(start_router)
router.include_router(help_router)
router.include_router(subscription_router)
router.include_router(referral_router)
router.include_router(payment_router)