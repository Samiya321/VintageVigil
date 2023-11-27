import os
import time

from loguru import logger
from telebot import asyncio_helper


class TelegramClient:
    def __init__(self, bot, chat_id: str, send_type="news"):
        if not chat_id:
            raise ValueError("chat_id 不能为空")
        self.bot = bot
        self.chat_id = chat_id
        self.send_type = send_type
        self.client_type = "telegram"

    async def initialize(self):
        await self.send_message(
            photo_url="https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/m79600701178_1.jpg",
            message="TelegramClient 实例化成功。",
        )

    async def send_text(self, message: str):
        max_retries = 3

        for attempt in range(max_retries):
            try:
                await self.bot.send_message(self.chat_id, message)
                return  # 成功发送，直接返回
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Unexpected error during sending text: {e}"
                )


    async def send_photo(self, photo_url: str):
        max_retries = 3

        for attempt in range(max_retries):
            modified_photo_url = photo_url
            for retry in ["original", "random=64", "random=54"]:
                if retry != "original":
                    if "?" in modified_photo_url:
                        modified_photo_url = modified_photo_url + "&" + retry
                    else:
                        modified_photo_url = modified_photo_url + "?" + retry

                try:
                    await self.bot.send_photo(self.chat_id, photo=modified_photo_url)
                    return  # 成功发送，退出函数
                except Exception as e:
                    logger.error(
                        f"Attempt {attempt + 1}, Retry: {retry}: Unexpected error during sending photo: {e}, photo_url: {modified_photo_url}"
                    )
                    if retry == "random=54":  # 如果已经是最后一次重试
                        break  # 退出内部循环，尝试下一次外部重试

            # 如果所有重试均失败，将执行下一个外部重试

    async def send_news(self, message: str, photo_url: str):
        max_retries = 3
        for attempt in range(max_retries):
            modified_photo_url = photo_url
            for retry in ["original", "random=64", "random=54"]:
                if retry != "original":
                    if "?" in modified_photo_url:
                        modified_photo_url = modified_photo_url + "&" + retry
                    else:
                        modified_photo_url = modified_photo_url + "?" + retry

                try:
                    start_time = time.time()
                    await self.bot.send_photo(
                        self.chat_id, photo=modified_photo_url, caption=message
                    )
                    end_time = time.time()
                    notification_time = end_time - start_time
                    logger.info(
                        f"Notification for item sent in {notification_time:.2f} seconds"
                    )
                    return  # 成功发送，退出函数
                except Exception as e:
                    logger.error(
                        f"Attempt {attempt + 1}, Retry: {retry}: Unexpected error during sending news: {e}, photo_url: {modified_photo_url}"
                    )
                    if retry == "random=54":  # 如果已经是最后一次重试
                        break  # 退出内部循环，尝试下一次外部重试

            # 如果所有重试均失败，将执行下一个外部重试

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
