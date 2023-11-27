import os
import time
from loguru import logger
from telebot import asyncio_helper
from httpx import AsyncClient


class TelegramClient:
    def __init__(self, bot, chat_id: str, send_type="news"):
        """
        初始化 Telegram 客户端。

        :param bot: Telegram 机器人实例。
        :param chat_id: 要发送消息的聊天 ID。
        :param send_type: 消息发送类型（text, photo, news）。
        """
        if not chat_id:
            raise ValueError("chat_id 不能为空")
        self.bot = bot
        self.chat_id = chat_id
        self.send_type = send_type
        self.client_type = "telegram"
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")

    async def initialize(self):
        """
        初始化 Telegram 客户端，并发送一条初始化成功的消息。
        """
        await self.send_message(
            photo_url="https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/m79600701178_1.jpg",
            message="TelegramClient 实例化成功。",
        )

    async def upload_to_imgur(self, image_url):
        """
        从 URL 下载图片并上传到 Imgur，返回新的直链。

        :param image_url: 图片的原始 URL。
        :return: Imgur 上图片的直链，上传失败返回 None。
        """
        headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        async with AsyncClient(proxies=os.getenv("HTTP_PROXY")) as client:
            # 下载图片
            response = await client.get(image_url)
            if response.status_code != 200:
                logger.error("Error downloading image")
                return None

            # 上传图片到 Imgur
            response = await client.post(
                "https://api.imgur.com/3/image",
                headers=headers,
                files={"image": response.content},
            )
            if response.status_code == 200:
                return response.json()["data"]["link"]
            else:
                logger.error(f"Error uploading image: {response.json()}")
                return None

    async def send_text(self, message: str):
        """
        向 Telegram 发送文本消息。

        :param message: 要发送的消息文本。
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.bot.send_message(self.chat_id, message)
                return  # 成功发送
            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Unexpected error during sending text: {e}"
                )

    async def send_photo(self, photo_url: str):
        """
        向 Telegram 发送图片消息。

        :param photo_url: 要发送的图片 URL。
        """
        await self.try_send_photo_with_retries(photo_url, self.bot.send_photo)

    async def send_news(self, message: str, photo_url: str):
        """
        向 Telegram 发送图文消息。

        :param message: 要发送的消息文本。
        :param photo_url: 要发送的图片 URL。
        """
        await self.try_send_photo_with_retries(
            photo_url,
            lambda url: self.bot.send_photo(self.chat_id, photo=url, caption=message),
        )

    async def try_send_photo_with_retries(self, photo_url, send_func):
        """
        尝试发送图片，如果失败则重试。

        :param photo_url: 要发送的图片 URL。
        :param send_func: 发送图片的函数。
        """
        for retry in ["random=64", "random=54", "original"]:
            if retry != "original":
                # 如果 URL 已有参数，使用 '&' 添加新参数；否则使用 '?'
                modified_photo_url = f"{photo_url}&{retry}" if "?" in photo_url else f"{photo_url}?{retry}"
            else:
                modified_photo_url = photo_url
                
            try:
                start_time = time.time()
                await send_func(modified_photo_url)
                logger.info(
                    f"Notification sent in {time.time() - start_time:.2f} seconds"
                )
                return
            except Exception as e:
                logger.error(
                    f"Retry: {retry}: Error during sending photo: {e}, photo_url: {modified_photo_url}"
                )

        # 如果重试失败，尝试上传到 Imgur 并再次发送
        new_photo_url = await self.upload_to_imgur(photo_url)
        if new_photo_url:
            try:
                await send_func(new_photo_url)
                logger.info("Notification sent with Imgur URL")
            except Exception as e:
                logger.error(
                    f"Error during sending with Imgur URL: {e}, photo_url: {new_photo_url}"
                )

    async def send_message(self, message: str, photo_url=""):
        """
        根据设定的发送类型发送消息。

        :param message: 要发送的消息文本。
        :param photo_url: 可选，要发送的图片 URL。
        """
        # 特殊处理paypay图片 URL
        if "images.auctions.yahoo.co.jp" in photo_url:
            photo_url = await self.upload_to_imgur(photo_url)
        try:
            if self.send_type == "text":
                await self.send_text(message)
            elif self.send_type == "photo":
                await self.send_text(message) if photo_url else await self.send_photo(
                    photo_url
                )
            elif self.send_type == "news":
                await self.send_news(message, photo_url)
            else:
                logger.warning(f"未知的发送类型: {self.send_type}")
        except asyncio_helper.RequestTimeout:
            logger.error("Telegram request timed out.")
