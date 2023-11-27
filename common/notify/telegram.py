import os
import time

from loguru import logger
from telebot import asyncio_helper
from httpx import AsyncClient


class TelegramClient:
    def __init__(self, bot, chat_id: str, send_type="news"):
        if not chat_id:
            raise ValueError("chat_id 不能为空")
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
        """
        从 URL 下载图片并上传到 Imgur，返回新的直链。

        :param image_url: 图片的原始 URL。
        :param client_id: Imgur 的客户端 ID。
        :return: Imgur 上图片的直链，上传失败返回 None。
        """
        headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        with AsyncClient(proxies=os.getenv("HTTP_PROXY")) as client:
            # 从 URL 下载图片
            response = await client.get(image_url)
            if response.status_code != 200:
                print("Error downloading image")
                return None

            image_data = response.content

            # 上传图片到 Imgur
            response = await client.post(
                "https://api.imgur.com/3/image",
                headers=headers,
                files={"image": image_data},
            )

            if response.status_code == 200:
                return response.json()["data"]["link"]
            else:
                print("Error uploading image:", response.json())
                return None

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
        for retry in ["random=64", "random=54", "original"]:
            modified_photo_url = photo_url
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
                    f"Retry: {retry}: Unexpected error during sending photo: {e}, photo_url: {modified_photo_url}"
                )
                if retry == "original":  # 如果已经是最后一次重试
                    break  # 退出内部循环，尝试下一次外部重试

        # All retries failed, try uploading to Imgur and sending again
        new_photo_url = await self.upload_to_imgur(photo_url)
        if new_photo_url:
            try:
                await self.bot.send_photo(self.chat_id, photo=new_photo_url)
                logger.info("Notification sent with Imgur URL")
            except Exception as e:
                logger.error(
                    f"Error during sending news with Imgur URL: {e}, photo_url: {new_photo_url}"
                )

    async def send_news(self, message: str, photo_url: str):
        for retry in ["random=64", "random=54", "original"]:
            modified_photo_url = photo_url
            if retry != "original":
                if "?" in modified_photo_url:
                    modified_photo_url += "&" + retry
                else:
                    modified_photo_url += "?" + retry

            try:
                start_time = time.time()
                await self.bot.send_photo(
                    self.chat_id, photo=modified_photo_url, caption=message
                )
                end_time = time.time()
                notification_time = end_time - start_time
                logger.info(f"Notification sent in {notification_time:.2f} seconds")
                return
            except Exception as e:
                logger.error(
                    f"Retry: {retry}: Error during sending news: {e}, photo_url: {modified_photo_url}"
                )
                if retry == "original":
                    break

        # All retries failed, try uploading to Imgur and sending again
        new_photo_url = await self.upload_to_imgur(photo_url)
        if new_photo_url:
            try:
                await self.bot.send_photo(
                    self.chat_id, photo=new_photo_url, caption=message
                )
                logger.info("Notification sent with Imgur URL")
            except Exception as e:
                logger.error(
                    f"Error during sending news with Imgur URL: {e}, photo_url: {new_photo_url}"
                )

    async def send_message(self, message: str, photo_url=""):
        # paypay的图片补丁
        if "images.auctions.yahoo.co.jp" in photo_url:
            photo_url = await self.upload_to_imgur(photo_url)
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
