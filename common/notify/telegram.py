import os
import time

from loguru import logger
from telebot import asyncio_helper
import httpx


class TelegramClient:
    def __init__(self, bot, chat_id: str, send_type="news"):
        self.bot = bot
        self.chat_id = chat_id
        self.send_type = send_type
        self.client_type = "telegram"
        self.imgur_client_id = os.getenv("IMGUR_CLIENT_ID")

    async def initialize(self):
        await self.send_message(
            photo_url="https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/m79600701178_1.jpg",
            message="TelegramClient 实例化成功。",
        )

    async def upload_to_imgur(self, image_url):
        headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        async with httpx.AsyncClient(proxies=os.getenv("HTTP_PROXY")) as client:
            # 下载图片
            try:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            except httpx.HTTPError as e:
                logger.error(f"Error downloading image: {e}")
                return None

            # 上传图片到 Imgur
            try:
                response = await client.post(
                    "https://api.imgur.com/3/image",
                    headers=headers,
                    files={"image": image_data},
                )
                response.raise_for_status()
                return response.json()["data"]["link"]
            except httpx.HTTPError as e:
                logger.error(f"Error uploading image to Imgur: {e}")
                return None

    async def send_text(self, message: str):
        await self._retry_send(self.bot.send_message, message)

    async def send_photo(self, photo_url: str):
        modified_photo_urls = self._get_modified_photo_urls(photo_url)
        await self._retry_send(self.bot.send_photo, photo_url, modified_photo_urls)

    async def send_news(self, message: str, photo_url: str):
        modified_photo_urls = self._get_modified_photo_urls(photo_url)
        await self._retry_send(
            self.bot.send_photo, photo_url, modified_photo_urls, caption=message
        )

    async def _retry_send(self, send_func, original_data, modified_data=None, **kwargs):
        data_list = (
            [original_data] + modified_data if modified_data else [original_data]
        )

        for data in data_list:
            try:
                start_time = time.time()
                await send_func(self.chat_id, photo=data, **kwargs)
                end_time = time.time()
                logger.info(
                    f"Notification sent in {end_time - start_time:.2f} seconds"
                )
                return
            except Exception as e:
                logger.error(
                    f"Error during sending: {e}, data: {data}"
                )

        # 如果所有重试都失败，尝试上传到 Imgur 并再次发送
        new_data = await self.upload_to_imgur(original_data)
        if new_data:
            try:
                await send_func(self.chat_id, photo=new_data, **kwargs)
                logger.info("Notification sent with Imgur URL")
            except Exception as e:
                logger.error(
                    f"Error during sending with Imgur URL: {e}, data: {new_data}"
                )

    @staticmethod
    def _get_modified_photo_urls(photo_url):
        if "?" in photo_url:
            return [f"{photo_url}&random=64", f"{photo_url}&random=54"]
        else:
            return [f"{photo_url}?random=64", f"{photo_url}?random=54"]

    async def send_message(self, message: str, photo_url=""):
        # paypay的图片补丁
        if "images.auctions.yahoo.co.jp" in photo_url:
            photo_url = await self.upload_to_imgur(photo_url)
        try:
            if self.send_type == "text":
                await self.send_text(message)
            elif self.send_type == "photo":
                if photo_url:
                    await self.send_text(message)
                    await self.send_photo(photo_url)
                else:
                    await self.send_text(message)
            elif self.send_type == "news" and photo_url:
                await self.send_news(message, photo_url)
            else:
                logger.warning(f"未知的发送类型: {self.send_type}")
        except asyncio_helper.RequestTimeout:
            logger.error("Telegram request timed out.")
