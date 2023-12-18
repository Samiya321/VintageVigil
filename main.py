import asyncio
import httpx
import os
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_helper

from loguru import logger

from monitor import setup_and_monitor


class MonitoringController:
    def __init__(self):
        """
        Initializes the MonitoringController class.

        The MonitoringController class is responsible for controlling the monitoring loop,
        managing resources such as the httpx client and telegram bots, and starting the monitoring process.
        """
        self.is_running = True  # 用于通知监控任务停止
        self.httpx_client = None
        self.telegram_bots = {}

    async def initialize_resources(self, parse_mode=None):
        """
        Initializes the necessary resources for monitoring.

        This method loads the environment variables, initializes the httpx AsyncClient,
        and initializes the telegram bots.

        Args:
            parse_mode (str, optional): The parse mode for telegram messages. Defaults to None.
        """
        load_dotenv()
        proxy = os.getenv("HTTP_PROXY")

        # Initialize httpx AsyncClient
        self.httpx_client = httpx.AsyncClient(
            proxies=proxy, verify=False, http2=False, timeout=10, follow_redirects=True
        )

        # Initialize telegram bots
        asyncio_helper.REQUEST_TIMEOUT = 10
        asyncio_helper.proxy = proxy or None

        telegram_bot_tokens = [
            os.getenv("TELEGRAM_BOT_TOKEN_1"),
            os.getenv("TELEGRAM_BOT_TOKEN_2"),
        ]

        for index, token in enumerate(telegram_bot_tokens):
            if token:
                self.telegram_bots[index] = AsyncTeleBot(token, parse_mode=parse_mode)

    async def close_resources(self):
        """
        Closes the allocated resources.

        This method closes the httpx client and telegram bot resources.
        """
        logger.info("Closing httpx client and telegram bot resources")
        if self.httpx_client:
            await self.httpx_client.aclose()
            logger.info("httpx client has closed")

        for index, bot in self.telegram_bots.items():
            await bot.close_session()
            logger.info(f"telegram bot: {index} has closed")

    def fetch_user_directories(self, base_path):
        """
        Retrieve directories for user monitoring.
        """
        return [
            dir_entry.path for dir_entry in os.scandir(base_path) if dir_entry.is_dir()
        ]

    async def start_monitoring(self):
        """
        Starts the monitoring process.

        This method starts the VintageVigil monitoring process by initializing the necessary resources
        and setting up and monitoring user directories asynchronously.
        """
        logger.info("Starting VintageVigil...")
        await self.initialize_resources()
        user_directories = self.fetch_user_directories("user")

        monitor_tasks = [
            asyncio.create_task(
                setup_and_monitor(
                    user_dir, self.is_running, self.httpx_client, self.telegram_bots
                )
            )
            for user_dir in user_directories
        ]
        await asyncio.gather(*monitor_tasks, return_exceptions=True)

    async def run(self):
        """
        The main entry point for the monitoring controller.
        This method starts the monitoring and handles shutting down gracefully.
        """
        try:
            await self.start_monitoring()
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            logger.info("Detected program interruption. Shutting down...")
            self.is_running = False
        finally:
            logger.info("Closing resources...")
            await self.close_resources()
            await asyncio.sleep(1)


if __name__ == "__main__":
    controller = MonitoringController()
    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("VintageVigil stopped.")
