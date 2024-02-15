from loguru import logger
import asyncio

from .monitor_website import monitor_site
from .initialization import InitializationManager


async def _load_user_configuration(user_dir, http_client, telegram_bots):
    """
    Load the configuration for a user and initialize required components.
    """
    try:
        initialize = InitializationManager(http_client, telegram_bots)
        return await initialize.setup_monitoring_for_user(user_dir)
    except Exception as e:
        logger.error(f"Error loading configuration for {user_dir}: {e}")
        return None, None, None


async def setup_and_monitor(user_dir, is_running, http_client, telegram_bots):
    """
    Setup and start monitoring for a specific user.
    """
    logger.info(f"Setting up monitoring for user: {user_dir}")
    config, database, notification_clients = await _load_user_configuration(
        user_dir, http_client, telegram_bots
    )

    if config and database and notification_clients:
        try:
            website_tasks = [
                monitor_site(
                    website,
                    database,
                    notification_clients,
                    user_dir,
                    is_running,
                    http_client,
                )
                for website in config.websites
            ]
            await asyncio.gather(*website_tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt caught, shutting down...")
        except Exception as e:
            logger.error(f"Error in monitoring process for {user_dir}: {e}")
        finally:
            if database:
                database.close()
                logger.info(f"Closed database for user: {user_dir}")
            if notification_clients:
                for client_name, client in notification_clients.items():
                    try:
                        await client.shutdown()
                        logger.info(f"Shutdown {client_name} successfully.")
                    except Exception as e:
                        logger.info(f"Error shutting down {client_name}: {e}")

    logger.info(f"Monitoring stopped for user: {user_dir}")
