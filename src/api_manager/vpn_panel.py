import json
import aiohttp
import uuid
import datetime
import logging
from os import getenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VPNConfig:
    def __init__(self):
        try:
            self.vpn_configs = json.loads(getenv("VPN"))
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга VPN конфигурации: {e}")
            raise
        except TypeError as e:
            logger.error(f"VPN конфигурация не найдена в переменных окружения: {e}")
            raise

    def get_config(self, location: str) -> dict:
        config = self.vpn_configs.get(location)
        if not config:
            raise ValueError(f"Конфигурация для локации {location} не найдена")
        return config


class Client:
    def __init__(
            self, 
            inbound_id, 
            client_id, 
            email, 
            port, 
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
    def __init__(self, location: str):
        self.vpn_config = VPNConfig()
        self.location = location
        self.config = self.vpn_config.get_config(location)
        self.session = aiohttp.ClientSession()
        self.host = f"https://{self.config['domen']}:{self.config['port']}/{self.config['path']}"
        self.username = self.config['username']
        self.password = self.config['password']
        self.inbound_id = self.config['inbound']
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
        try:
            async with self.session.post(f"{self.host}/login", headers=headers, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Authentication failed with status {response.status}")
                self.authenticated = True
        except Exception as e:
            logger.error(f"Ошибка аутентификации для локации {self.location}: {e}")
            raise

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
                "id": self.inbound_id,
                "settings": "{\"clients\": [{\"id\": \""+f"{id}"+"\",\"email\": \""+f"{id}-{email}"+"\",\"flow\":\"xtls-rprx-vision\",\"limitIp\": 0,\"totalGB\": 0,\"expiryTime\": "+f"{expiry_time}"+",\"enable\": true,\"tgId\": \"\",\"subId\": \""+f"{id}-{email}"+"\",\"reset\": 0}]}"
            }
            logger.info(f"Добавление клиента для локации {self.location}: {payload}")
            
            async with self.session.post(
                f"{self.host}/panel/api/inbounds/addClient", 
                json=payload, 
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка добавления клиента: {response.status}")

                response_data = await response.json()
                logger.info(f"Ответ от addClient для локации {self.location}: {response_data}")

                if not response_data.get("success", False):
                    raise Exception(f"Не удалось добавить клиента: {response_data.get('msg', 'Нет сообщения')}")
                return response_data
        except Exception as e:
            logger.error(f"Ошибка в add_client для локации {self.location}: {e}")
            raise

    async def get_client(self, client_email):
        try:
            await self.ensure_authenticated()
            async with self.session.get(f"{self.host}/panel/api/inbounds/get/{self.inbound_id}") as response:
                if response.status != 200:
                    logger.error(f"Ошибка получения данных для локации {self.location}: {response.status}")
                    return None
                
                response_data = await response.json()
                logger.info(f"Ответ от API для локации {self.location}: {response_data}")
                
                if not response_data.get("success", False):
                    raise Exception(f"Запрос завершился неудачно: {response_data.get('msg', 'Нет сообщения')}")
                
                inbound = response_data.get("obj")
                if not inbound:
                    logger.error(f"Ответ не содержит 'obj' для локации {self.location}")
                    return None
                
                settings = json.loads(inbound["settings"])
                stream_settings = json.loads(inbound["streamSettings"])
                
                for client_settings in settings["clients"]:
                    if client_settings["email"] == client_email:
                        return Client(
                            inbound_id=self.inbound_id,
                            client_id=client_settings["id"],
                            email=client_settings["email"],
                            port=inbound["port"],
                            protocol=inbound["protocol"],
                            network=stream_settings["network"],
                            security=stream_settings["security"],
                            flow=client_settings["flow"]
                        )
            
                raise Exception(f"Клиент с email {client_email} не найден в локации {self.location}.")
        except Exception as e:
            logger.error(f"Ошибка в get_client для локации {self.location}: {e}")
            return None

    async def configure_link(self, client: Client):
        vpn_connection_string = (
            f"{client.protocol}://{client.client_id}@{self.config['domen']}:{client.port}"
            f"?type={client.network}&security={client.security}&pbk={self.config['pbk']}&fp=chrome&sni=google.com&sid={self.config['sid']}&spx=%2F"
            f"&flow={client.flow}#{client.email}"
        )
        return vpn_connection_string

    async def close(self):
        await self.session.close()