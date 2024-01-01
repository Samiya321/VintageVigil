import os
from loguru import logger

from common import Config, ProductDatabase, TelegramClient, setup_logger, WecomClient


class InitializationManager:
    def __init__(self, httpx_client, telegram_bots):
        self.httpx_client = httpx_client
        self.telegram_bots = telegram_bots

    async def setup_notification_clients(self, notification_config):
        notification_clients = {}
        try:
            await self._setup_telegram_clients(
                notification_config, notification_clients
            )
            await self._setup_wecom_clients(notification_config, notification_clients)
            return notification_clients
        except Exception as e:
            logger.error(f"Failed to setup notification clients: {e}")
            raise e

    async def _setup_telegram_clients(self, notification_config, notification_clients):
        if "telegram_chat_id" in notification_config:
            for index, bot in enumerate(self.telegram_bots.values()):
                client_key = f"telegram_{index + 1}"
                notification_clients[client_key] = TelegramClient(
                    bot,
                    notification_config["telegram_chat_id"],
                    self.httpx_client,
                    notification_config["tg_send_type"],
                )
                await notification_clients[client_key].initialize()

    async def _setup_wecom_clients(self, notification_config, notification_clients):
        if "wecom_user_id" in notification_config:
            wecom_agent_ids = [os.getenv("WECOM_AGENT_ID_1")]
            corp_id = os.getenv("WECOM_CORP_ID")
            corp_secret = os.getenv("WECOM_CORP_SECRET")
            for index, agent_id in enumerate(wecom_agent_ids):
                client_key = f"wecom_{index + 1}"
                notification_clients[client_key] = WecomClient(
                    corp_id,
                    corp_secret,
                    agent_id,
                    notification_config["wecom_user_id"],
                    self.httpx_client,
                    notification_config["we_send_type"],
                )
                await notification_clients[client_key].initialize()

    async def setup_monitoring_for_user(self, user_dir):
        try:
            # Load configuration
            config = Config.from_toml(user_dir)

            # Setup logger
            setup_logger(config.websites, user_dir)

            # Setup database
            database_path = f"{user_dir}/data/database.db"
            database = ProductDatabase(database_path)

            # Initialize notification clients
            notification_clients = await self.setup_notification_clients(
                config.notify_config
            )
            return config, database, notification_clients
        except Exception as e:
            logger.error(f"Error during setup for {user_dir}: {e}")
            raise e
