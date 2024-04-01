from loguru import logger
import asyncio
from telebot.async_telebot import AsyncTeleBot

class TelegramClient:

    def __init__(
        self, bot: AsyncTeleBot, chat_ids: dict, http_client, send_type="news"
    ):
        """
        初始化Telegram客户端。

        :param bot: Telegram 机器人实例。
        :param chat_id: 要发送消息的聊天 ID。
        :param send_type: 消息发送类型（text, photo, news）。
        :raises ValueError: 如果send_type不是有效的类型或chat_ids为空。
        """
        valid_send_types = ["text", "photo", "news"]
        if send_type not in valid_send_types:
            raise ValueError(
                f"send_type {send_type} is invalid. Valid options are {valid_send_types}"
            )
        if not chat_ids:
            raise ValueError("chat_ids cannot be empty")

        self.bot = bot
        self.chat_ids = chat_ids
        self.send_type = send_type
        self.http_client = http_client

        self.client_type = "telegram"

        self.message_queue = asyncio.Queue()
        self.running_tasks = []

    async def initialize(self) -> None:
        """
        初始化Telegram客户端，并发送一条初始化成功的消息。
        """
        for index, _ in enumerate(self.chat_ids):
            chat_id = self.chat_ids[index]

            await self.send_message(
                photo_url="https://raw.githubusercontent.com/Samiya321/VintageVigil/main/favicon.ico",
                message="TelegramClient initialized successfully.",
                chat_id= chat_id
            )

    async def send_text(self, message: str, chat_id: int) -> None:
        """
        向Telegram发送文本消息。

        :param message: 要发送的消息文本。
        :param chat_id: 目标聊天的ID。
        """
        try:
            await self.bot.send_message(chat_id, message)
        except Exception as e:
            logger.error(f"Unexpected error during sending text: {e}")

    async def send_photo(self, photo_url: str, chat_id: int) -> None:
        """
        向Telegram发送图片消息。

        :param photo_url: 要发送的图片URL。
        :param chat_id: 目标聊天的ID。
        """
        try:
            await self.try_send_photo_with_retries(
                photo_url,
                lambda url: self.bot.send_photo(chat_id, photo=url),
            )
        except Exception as e:
            logger.error(
                f"Error during sending photo to {chat_id}: {e}, photo_url: {photo_url}"
            )

    async def send_news(self, message: str, photo_url: str, chat_id: int) -> None:
        """
        向Telegram发送图文消息。

        :param message: 要发送的消息文本。
        :param photo_url: 要发送的图片URL。
        :param chat_id: 目标聊天的ID。
        """
        try:
            await self.try_send_photo_with_retries(
                photo_url,
                lambda url: self.bot.send_photo(chat_id, photo=url, caption=message),
            )
        except Exception as e:
            logger.error(
                f"Error during sending news to {chat_id}: {e}, photo_url: {photo_url}"
            )

    async def try_send_photo_with_retries(self, photo_url, send_func):
        """
        尝试发送图片，如果失败则重试。

        :param photo_url: 要发送的图片 URL。
        :param send_func: 发送图片的函数。
        """
        try:
            response = await self.http_client.get(photo_url)
            response.raise_for_status()
            image_data = await response.content()
            await response.close()
            await send_func(image_data)
        except Exception as e:
            logger.error(
                f"Error during sending original photo: {e}, photo_url: {photo_url}"
            )

    async def send_message(
        self, message: str, photo_url: str = "", chat_id: int = 0
    ) -> None:
        """
        根据设定的发送类型发送消息。

        :param message: 要发送的消息文本。
        :param photo_url: 可选，要发送的图片URL。
        :param chat_ids_index: 聊天ID列表中的索引。
        """
        try:
            if self.send_type == "text":
                await self.send_text(message, chat_id)
            elif self.send_type == "photo":
                await self.send_text(message, chat_id)
                await self.send_photo(photo_url, chat_id)
            elif self.send_type == "news":
                await self.send_news(message, photo_url, chat_id)
        except Exception as e:
            logger.error(f"Telegram API error for chat ID {chat_id}: {e}")

    async def enqueue_message(
        self, message: str, photo_url: str = "", chat_id_index: int = 0
    ):
        """
        将消息添加到队列中，并立即开始处理。
        """
        chat_id = self.chat_ids[chat_id_index]
        # 直接启动任务处理消息，而不是等待
        task = asyncio.create_task(self.send_message(message, photo_url, chat_id))
        self.running_tasks.append(task)
        # Optionally, you can add a callback to remove the task from the list upon completion
        task.add_done_callback(self.running_tasks.remove)

    async def shutdown(self):
        # 取消所有运行中的任务
        for task in self.running_tasks:
            task.cancel()
        # 等待所有任务完成或被取消
        await asyncio.gather(*self.running_tasks, return_exceptions=True)
