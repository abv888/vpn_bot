import json
from aiogram import BaseMiddleware
from api_manager.vpn_panel import VPNPanelAPI
import logging

logger = logging.getLogger(__name__)

class VPNMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.connections = {}
        
    async def __call__(self, handler, event, data):
        # VPN API нужен только для определенных операций
        needs_vpn = False
        location = None

        if hasattr(event, 'data') and event.data:
            # Проверяем, нужен ли VPN для текущей операции
            if event.data.startswith("payment_"):
                # Для payment_ не создаем соединение, только для check_payment
                needs_vpn = False
            elif event.data.startswith("check_"):
                needs_vpn = True
                # Для проверки платежа локация должна быть в метаданных платежа
                if "_payment_" in event.data:
                    # Локацию получим позже из данных платежа
                    pass
            elif event.data.startswith("location_"):
                location = event.data.split("_")[1]
                needs_vpn = True

        # Если это успешный платеж
        if hasattr(event, 'successful_payment') and event.successful_payment is not None:
            needs_vpn = True
            try:
                payment_data = json.loads(event.successful_payment.invoice_payload)
                location = payment_data.get('location', 'NL')
            except Exception as e:
                logger.error(f"Error parsing payment data: {e}")
                location = "NL"

        if needs_vpn and location:
            if location not in self.connections:
                try:
                    vpn_api = VPNPanelAPI(location=location)
                    await vpn_api.authenticate()
                    self.connections[location] = vpn_api
                    logger.info(f"Created new VPN connection for location: {location}")
                except Exception as e:
                    logger.error(f"Failed to create VPN connection for {location}: {e}")
                    raise

            data["vpn_api"] = self.connections[location]
            data["selected_location"] = location

        try:
            return await handler(event, data)
        finally:
            # Не закрываем соединения после каждого запроса,
            # они будут закрыты при завершении работы бота
            pass

    async def close_all(self):
        """Закрыть все соединения"""
        for location, connection in self.connections.items():
            try:
                await connection.close()
                logger.info(f"Closed VPN connection for location: {location}")
            except Exception as e:
                logger.error(f"Error closing VPN connection for {location}: {e}")