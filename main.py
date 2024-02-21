import asyncio
import os
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_helper
import argparse
from loguru import logger

from monitor import setup_and_monitor
from common import AsyncHTTPXClient, AsyncAIOHTTPClient

class MonitoringController:
    def __init__(self, base_path="user", direct_user_path=None):
        """
        Initializes the MonitoringController class with the ability to accept a custom directory path.

        Args:
            base_path (str, optional): Base directory path to look for user directories. Defaults to "user".
            direct_user_path (str, optional): Direct path to a user directory. If provided, only this directory will be monitored.
        """
        self.is_running = True  # 用于通知监控任务停止
        self.base_path = base_path
        self.direct_user_path = direct_user_path
        self.http_client = None
        self.telegram_bots = {}

    async def initialize_resources(self, parse_mode=None):
        """
        Initializes the necessary resources for monitoring.

        This method loads the environment variables, initializes the http_client,
        and initializes the telegram bots.

        Args:
            parse_mode (str, optional): The parse mode for telegram messages. Defaults to None.
        """

        load_dotenv()

        proxy = os.getenv('HTTP_PROXY')

        timeout = 10.0

        # Initialize http client

        http_client_type = os.getenv('HTTP_CLIENT')

        if http_client_type == "httpx":
            # 使用 AsyncHTTPXClient
            self.http_client = AsyncHTTPXClient(
                http2=False,
                timeout=timeout,
                proxy=proxy,
                redirects=True,
                ssl_verify=False,
            )
        else:
            # 默认使用 AsyncAIOHTTPClient
            self.http_client = AsyncAIOHTTPClient(
                http2=False,
                timeout=timeout,
                proxy=proxy,
                redirects=True,
                ssl_verify=False,
            )

        # Initialize telegram bots
        asyncio_helper.REQUEST_TIMEOUT = timeout
        asyncio_helper.proxy = proxy or None

        # 尝试从环境变量获取API URL，如果未设置，则使用默认值
        API_URL = os.getenv('TELEGRAM_API_URL', 'https://api.telegram.org/bot{0}/{1}')
        # 将API_URL设置到asyncio_helper的属性中
        asyncio_helper.API_URL = API_URL

        # 动态获取所有的TELEGRAM_BOT_TOKEN环境变量
        telegram_bot_tokens = {
            key: value
            for key, value in os.environ.items()
            if key.startswith("TELEGRAM_BOT_TOKEN")
        }

        self.telegram_bots = {}  # 确保这个字典已经被初始化

        for index, token in telegram_bot_tokens.items():
            if token:
                self.telegram_bots[index] = AsyncTeleBot(
                    token,
                    parse_mode=parse_mode,
                )

    async def close_resources(self):
        """
        Closes the allocated resources.

        This method closes the http_client and telegram bot resources.
        """
        logger.info("Closing http_client and telegram bot resources")
        if self.http_client:
            await self.http_client.close()
            logger.info("http_client has closed")

        for index, bot in self.telegram_bots.items():
            await bot.close_session()
            logger.info(f"telegram bot: {index} has closed")

    def fetch_user_directories(self):
        """
        Retrieve directories for user monitoring based on the provided path.
        """
        # 如果提供了直接的用户路径，则仅返回该路径
        if self.direct_user_path:
            return (
                [self.direct_user_path] if os.path.exists(self.direct_user_path) else []
            )
        # 否则，返回基路径下的所有用户目录
        return [
            dir_entry.path
            for dir_entry in os.scandir(self.base_path)
            if dir_entry.is_dir()
        ]

    async def start_monitoring(self):
        """
        Starts the monitoring process, with modifications to accept custom directory paths.
        """
        logger.info("Starting VintageVigil...")
        await self.initialize_resources(parse_mode="Markdown")
        user_directories = self.fetch_user_directories()

        monitor_tasks = [
            asyncio.create_task(
                setup_and_monitor(
                    user_dir, self.is_running, self.http_client, self.telegram_bots
                )
            )
            for user_dir in user_directories
            if os.path.exists(f"{user_dir}/notify.toml")
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
    parser = argparse.ArgumentParser(
        description="Monitor user directories for notifications."
    )
    parser.add_argument(
        "-r",
        "--base-path",
        help="Base directory path to look for user directories.",
        default="user",
    )
    parser.add_argument(
        "-u", "--user-path", help="Direct path to a specific user directory to monitor."
    )

    args = parser.parse_args()

    controller = MonitoringController(
        base_path=args.base_path, direct_user_path=args.user_path
    )
    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        logger.info("VintageVigil stopped.")
