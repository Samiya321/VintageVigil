import asyncio
import os
import httpx

from loguru import logger

from common import Config, ProductDatabase, TelegramClient, setup_logger, WecomClient
from .monitoring import monitor_site


async def setup_notification_clients(notification_config):
    """
    Set up notification clients based on the configuration.
    """
    notification_clients = {}
    try:
        # Setup Telegram Clients
        if notification_config.get("telegram_chat_id"):
            telegram_bot_tokens = [
                os.getenv("TELEGRAM_BOT_TOKEN_1"),
                os.getenv("TELEGRAM_BOT_TOKEN_2"),
            ]
            for index, token in enumerate(telegram_bot_tokens):
                if token:
                    client_key = f"telegram_{index + 1}"
                    notification_clients[client_key] = TelegramClient(
                        token,
                        notification_config.get("telegram_chat_id"),
                        notification_config.get("tg_send_type"),
                    )
                    # Initialize client
                    await notification_clients[client_key].initialize()

        # Setup WeCom Clients
        if notification_config.get("wecom_user_id"):
            wecom_agent_ids = [os.getenv("WECOM_AGENT_ID_1")]
            corp_id = os.getenv("WECOM_CORP_ID")
            corp_secret = os.getenv("WECOM_CORP_SECRET")
            for index, agent_id in enumerate(wecom_agent_ids):
                if agent_id:
                    client_key = f"wecom_{index + 1}"
                    notification_clients[client_key] = WecomClient(
                        corp_id,
                        corp_secret,
                        agent_id,
                        notification_config.get("wecom_user_id"),
                        notification_config.get("we_send_type"),
                    )
                    await notification_clients[client_key].initialize()

        return notification_clients
    except Exception as e:
        logger.error(f"Error setting up notification clients: {e}")
        raise


async def setup_monitoring(user_dir):
    """
    Setup monitoring system for a given user.
    """
    try:
        config_path = f"{user_dir}/config.toml"
        database_path = f"{user_dir}/database.db"

        # Load configuration
        config = Config.from_toml(config_path)

        # Setup logger
        setup_logger(config.websites, user_dir)

        # Setup database
        database = ProductDatabase(database_path)

        # Initialize notification clients
        notification_clients = await setup_notification_clients(config.notify_config)

        # Initialize httpx AsyncClient clinet
        httpx_client = httpx.AsyncClient(
            proxies=os.getenv("HTTP_PROXY"), verify=False, http2=False, timeout= 20
        )
        return config, database, notification_clients, httpx_client

    except Exception as e:
        logger.error(f"Error during setup for {user_dir}: {e}")
        raise


def fetch_user_directories(base_path):
    """
    Retrieve directories for user monitoring.
    """
    return [dir_entry.path for dir_entry in os.scandir(base_path) if dir_entry.is_dir()]


async def setup_and_monitor(user_dir, is_running):
    """
    Setup and start monitoring for a specific user.
    """
    database = None
    notification_clients = None
    httpx_client = None
    try:
        if os.path.exists(f"{user_dir}/config.toml"):
            (
                config,
                database,
                notification_clients,
                httpx_client,
            ) = await setup_monitoring(user_dir)
            website_tasks = [
                asyncio.create_task(
                    monitor_site(
                        site,
                        database,
                        notification_clients,
                        user_dir,
                        is_running,
                        httpx_client,
                    )
                )
                for site in config.websites
            ]
            await asyncio.gather(*website_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error in monitoring process for {user_dir}: {e}")

    finally:
        # 清理操作：关闭数据库和客户端和http连接
        if database:
            database.close()
        if httpx_client:
            await httpx_client.aclose()
        if notification_clients:
            for notification_client in notification_clients.values():
                await notification_client.close()
        logger.info(f"Monitoring stopped for user: {user_dir}")
