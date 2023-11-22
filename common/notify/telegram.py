import os
import time

from loguru import logger
from telebot import asyncio_helper
from telebot.async_telebot import AsyncTeleBot


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, send_type="news", parse_mode=None):
        if not bot_token or not chat_id:
            raise ValueError("bot_token 和 chat_id 不能为空")

        asyncio_helper.CONNECT_TIMEOUT = 20
        asyncio_helper.REQUEST_TIMEOUT = 20
        asyncio_helper.proxy = os.getenv("HTTP_PROXY") or None
        self.bot = AsyncTeleBot(bot_token, parse_mode=parse_mode)
        self.chat_id = chat_id
        self.send_type = send_type
        self.client_type = "telegram"

    async def initialize(self):
        await self.send_message(
            photo_url="https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/m79600701178_1.jpg",
            message="TelegramClient 实例化成功。",
        )

    async def close(self):
        await self.bot.close_session()
        logger.info("TelegramClient 关闭成功。")

    async def send_text(self, message: str):
        max_retries = 3
        # retry_delay = 1  # 1 second

        for attempt in range(max_retries):
            try:
                await self.bot.send_message(self.chat_id, message)
                return  # 成功发送，直接返回
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Unexpected error during sending text: {e}"
                )
                # if attempt < max_retries - 1:
                #     await asyncio.sleep(retry_delay)
                #     retry_delay *= 2  # 指数退避

    async def send_photo(self, photo_url: str):
        max_retries = 3
        # retry_delay = 1

        for attempt in range(max_retries):
            try:
                await self.bot.send_photo(self.chat_id, photo=photo_url)
                return
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Unexpected error during sending photo: {e}"
                )
                # if attempt < max_retries - 1:
                #     await asyncio.sleep(retry_delay)
                #     retry_delay *= 2

    async def send_news(self, message: str, photo_url: str):
        max_retries = 3
        # retry_delay = 1

        start_time = time.time()
        for attempt in range(max_retries):
            try:
                await self.bot.send_photo(
                    self.chat_id, photo=photo_url, caption=message
                )
                end_time = time.time()
                notification_time = end_time - start_time
                logger.info(f"Notification for item sent in {notification_time:.2f} seconds")
                return
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Unexpected error during sending news: {e}, photo_url: {photo_url}"
                )
                # if attempt < max_retries - 1:
                #     await asyncio.sleep(retry_delay)
                #     retry_delay *= 2

    async def send_message(self, message: str, photo_url=""):

        try:
            if self.send_type == "text":
                await self.send_text(message)
            elif self.send_type == "photo":
                if photo_url:
                    # 先发送文本，然后发送图片
                    await self.send_text(message)
                    await self.send_photo(photo_url)
                else:
                    # 如果没有图片URL，只发送文本
                    await self.send_text(message)
            elif self.send_type == "news" and photo_url:
                await self.send_news(message, photo_url)
            else:
                logger.warning(f"未知的发送类型: {self.send_type}")
        except asyncio_helper.RequestTimeout:
            logger.error("Telegram request timed out.")