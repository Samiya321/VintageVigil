import asyncio
import os
import httpx

from loguru import logger

from common import Config, ProductDatabase, TelegramClient, setup_logger, WecomClient
from .monitoring import monitor_site


async def setup_notification_clients(notification_config, httpx_client, telegram_bots):
    """
    Set up notification clients based on the configuration.
    """
    notification_clients = {}
    try:
        # Setup Telegram Clients
        if notification_config.get("telegram_chat_id"):
            for index, bot in telegram_bots.items():
                if bot:
                    client_key = f"telegram_{index + 1}"
                    notification_clients[client_key] = TelegramClient(
                        bot,
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
                        httpx_client,
                        notification_config.get("we_send_type"),
                    )
                    await notification_clients[client_key].initialize()

        return notification_clients
    except Exception as e:
        logger.error(f"Error setting up notification clients: {e}")
        raise


async def setup_monitoring(user_dir, httpx_client, telegram_bots):
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
        notification_clients = await setup_notification_clients(
            config.notify_config, httpx_client, telegram_bots
        )

        return config, database, notification_clients

    except Exception as e:
        logger.error(f"Error during setup for {user_dir}: {e}")
        raise


def fetch_user_directories(base_path):
    """
    Retrieve directories for user monitoring.
    """
    return [dir_entry.path for dir_entry in os.scandir(base_path) if dir_entry.is_dir()]


async def setup_and_monitor(user_dir, is_running, httpx_client, telegram_bots):
    """
    Setup and start monitoring for a specific user.
    """
    database = None
    notification_clients = None
    try:
        if os.path.exists(f"{user_dir}/config.toml"):
            (
                config,
                database,
                notification_clients,
            ) = await setup_monitoring(user_dir, httpx_client, telegram_bots)
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
        # 清理操作：关闭数据库
        if database:
            database.close()
        logger.info(f"Monitoring stopped for user: {user_dir}")
