from loguru import logger
import os
import asyncio

from .monitor_website import monitor_site
from .initialization import InitializationManager


async def _load_user_configuration(user_dir, httpx_client, telegram_bots):
    """
    Load the configuration for a user and initialize required components.
    """
    try:
        if os.path.exists(f"{user_dir}/config.toml"):
            initialize = InitializationManager(httpx_client, telegram_bots)
            return await initialize.setup_monitoring_for_user(user_dir)
        else:
            return None, None, None
    except Exception as e:
        logger.error(f"Error loading configuration for {user_dir}: {e}")
        return None, None, None


async def setup_and_monitor(user_dir, is_running, httpx_client, telegram_bots):
    """
    Setup and start monitoring for a specific user.
    """
    logger.info(f"Setting up monitoring for user: {user_dir}")
    config, database, notification_clients = await _load_user_configuration(
        user_dir, httpx_client, telegram_bots
    )

    if config and database and notification_clients:
        try:
            website_tasks = [
                monitor_site(
                    site,
                    database,
                    notification_clients,
                    user_dir,
                    is_running,
                    httpx_client,
                )
                for site in config.websites
            ]
            await asyncio.gather(*website_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in monitoring process for {user_dir}: {e}")
        finally:
            if database:
                database.close()
                logger.info(f"Closed database for user: {user_dir}")

    logger.info(f"Monitoring stopped for user: {user_dir}")