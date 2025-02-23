import json
from aiogram import BaseMiddleware
import yookassa
from api_manager.vpn_panel import VPNPanelAPI
import logging

from payment.cryptomus import check_cryptomus_invoice

logger = logging.getLogger(__name__)

class VPNMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.connections = {}
        
    async def __call__(self, handler, event, data):
        needs_vpn = False
        location = None

        if hasattr(event, 'data') and event.data:
            if event.data.startswith("payment_"):
                needs_vpn = False
            elif event.data.startswith("check_"):
                needs_vpn = True
                # Получаем данные из callback_data
                method = event.data.split("_")[1]
                payment_id = event.data.split("_")[-1]
                
                try:
                    if method == "yookassa":
                        payment = yookassa.Payment.find_one(payment_id=payment_id)
                        location = payment.metadata.get('location')
                    elif method == "cryptomus":
                        invoice = await check_cryptomus_invoice(payment_id=payment_id)
                        payload = json.loads(invoice["result"]["additional_data"])
                        location = payload.get('location')
                except Exception as e:
                    logger.error(f"Error getting payment data: {e}")
                    location = "NL"  # Fallback локация
            elif event.data.startswith("location_"):
                location = event.data.split("_")[1]
                needs_vpn = True

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
            pass

    async def close_all(self):
        for location, connection in self.connections.items():
            try:
                await connection.close()
                logger.info(f"Closed VPN connection for location: {location}")
            except Exception as e:
                logger.error(f"Error closing VPN connection for {location}: {e}")