import httpx
import json


class WeChatClient:
    def __init__(self, httpx_client, send_type="text"):
        self.client = httpx_client
        self.api_url = "http://localhost:3001/webhook/msg/v2"
        self.send_type = send_type

    async def initialize(self):
        await self.send_message("Initialization message", "WeChatClient 初始化成功")

    async def send_message(self, message, photo_url="", message_url="", title=""):
        if self.send_type == "text":
            return await self.send_text(message)
        elif self.send_type == "photo" and photo_url:
            return await self.send_photo(photo_url)
        elif self.send_type == "news":
            await self.send_photo(photo_url)
            await self.send_text(message)
        else:
            raise ValueError(f"Unknown send type: {self.send_type}")

    async def send_text(self, message):
        data = {"content": message}
        return await self._post_request(data)

    async def send_photo(self, photo_url):
        data = {"type": "fileUrl", "content": photo_url}
        return await self._post_request(data)

    async def _post_request(self, data, is_room=False):
        payload = {"to": to, "isRoom": is_room, "data": data}
        try:
            response = await self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


# Example Usage
# async with httpx.AsyncClient() as client:
#     wechat_client = WeChatClient(client)
#     await wechat_client.initialize()
#     await wechat_client.send_text("testUser", "Hello WeChat!")
