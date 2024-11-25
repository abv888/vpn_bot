# vpn_panel.py

import json
import aiohttp
import uuid
import datetime
import logging
from os import getenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Client:
    def __init__(
            self, 
            inbound_id, 
            client_id, 
            email, port, 
            protocol, 
            network, 
            security, 
            flow
        ):
        self.inbound_id = inbound_id
        self.client_id = client_id
        self.email = email
        self.port = port
        self.protocol = protocol
        self.network = network
        self.security = security
        self.flow = flow


class VPNPanelAPI:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.host = f"https://{getenv("VPN_DOMEN")}/{getenv("WEBBASEPATH")}"
        self.username = getenv("VPN_PANEL_USERNAME")
        self.password = getenv("VPN_PANEL_PASSWORD")
        self.authenticated = False

    async def authenticate(self):
        data = {
            "username": self.username,
            "password": self.password
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        async with self.session.post(f"{self.host}/login", headers=headers, json=data) as response:
            if response.status != 200:
                raise Exception(f"Authentication failed with status {response.status}")
            self.authenticated = True

    async def ensure_authenticated(self):
        if not self.authenticated:
            await self.authenticate()

    async def add_client(self, day, email, id):
        try:
            await self.ensure_authenticated()
            epoch = datetime.datetime.utcfromtimestamp(0)
            current_time = datetime.datetime.utcnow()
            x_time = int((current_time - epoch).total_seconds() * 1000.0)
            expiry_time = x_time + (86400000 * day)
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {
                "id": 6,
                "settings": "{\"clients\": [{\"id\": \""+f"{id}"+"\",\"flow\": \"\",\"email\": \""+f"{id}-{email}"+"\",\"flow\":\"xtls-rprx-vision\",\"limitIp\": 0,\"totalGB\": 0,\"expiryTime\": "+f"{expiry_time}"+",\"enable\": true,\"tgId\": \"\",\"subId\": \""+f"{id}-{email}"+"\",\"reset\": 0}]}"
            }
            async with self.session.post(
            f"{self.host}/panel/api/inbounds/addClient", 
            json=payload, 
            headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка добавления клиента: {response.status}")

                response_data = await response.json()
                logger.info(f"Ответ от addClient: {response_data}")

                if not response_data.get("success", False):
                    raise Exception(f"Не удалось добавить клиента: {response_data.get('msg', 'Нет сообщения')}")
                return response_data
        except Exception as e:
            logger.error(f"Ошибка в add_client: {e}")
            raise


    async def get_client(self, inbound_id, client_email):
        try:
            async with self.session.get(f"{self.host}/panel/api/inbounds/get/{inbound_id}") as response:
                if response.status != 200:
                    logger.error(f"Ошибка получения данных: {response.status}")
                    return None
                
                response_data = await response.json()
                logger.info(f"Ответ от API: {response_data}")
                
                # Проверяем, содержит ли ответ ключ 'obj'
                if not response_data.get("success", False):
                    raise Exception(f"Запрос завершился неудачно: {response_data.get('msg', 'Нет сообщения')}")
                
                inbound = response_data.get("obj")
                if not inbound:
                    logger.error("Ответ не содержит 'obj'")
                    return None
                
                settings = json.loads(inbound["settings"])
                stream_settings = json.loads(inbound["streamSettings"])
                
                for client_settings in settings["clients"]:
                    if client_settings["email"] == client_email:
                        return Client(
                            inbound_id=inbound_id,
                            client_id=client_settings["id"],
                            email=client_settings["email"],
                            port=inbound["port"],
                            protocol=inbound["protocol"],
                            network=stream_settings["network"],
                            security=stream_settings["security"],
                            flow=client_settings["flow"]
                        )
            
                # Если клиент с указанным email не найден
                raise Exception(f"Клиент с email {client_email} не найден.")
        except Exception as e:
            logger.error(f"Ошибка в get_client: {e}")
            return None


    async def configure_link(self, client: Client):
        """Generate a connection link for a client."""
        vpn_connection_string = (
            f"{client.protocol}://{client.client_id}@{getenv("VPN_DOMEN")}:{client.port}"
            f"?type={client.network}&security={client.security}&fp=&alpn=h3,h2,http/1.1"
            f"&flow={client.flow}#{client.email}"
        )
        return vpn_connection_string

    async def close(self):
        """Close the session to avoid resource leaks."""
        await self.session.close()
