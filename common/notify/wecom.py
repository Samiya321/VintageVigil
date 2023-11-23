from datetime import datetime, timedelta
from io import BytesIO

from loguru import logger


class WecomClient:
    def __init__(
        self,
        corp_id,
        corp_secret,
        agent_id,
        user_id,
        httpx_client, 
        send_type="news",
    ):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.user_id = user_id
        self.access_token = None
        self.token_expires_at = None
        self.send_type = send_type
        self.client = httpx_client
        self.client_type = "wecom"

    async def initialize(self):
        await self.send_message(
            title="WeCom 实例化成功",
            photo_url="https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/m79600701178_1.jpg",
            message="WeCom 实例化成功。",
        )

    async def get_access_token(self, force_refresh=False):
        if (
            self.access_token
            and self.token_expires_at > datetime.now()
            and not force_refresh
        ):
            return self.access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            response = await self.client.get(url)
            data = response.json()
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)  # 默认有效期7200秒
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            return self.access_token
        except Exception as e:
            logger.error(f"获取访问令牌失败: {e}")
            return None

    async def upload_image_get_media_id(self, image_url):
        access_token = await self.get_access_token()
        if access_token:
            upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image"
            try:
                # 下载图片
                image_response = await self.client.get(image_url)
                image_response.raise_for_status()

                # 上传图片
                files = {"media": BytesIO(image_response.content)}
                response = await self.client.post(upload_url, files=files)
                result = response.json()
                return result.get("media_id")
            except Exception as e:
                logger.error(f"上传图片失败: {e}")
                return None
        else:
            return None

    async def send_text(self, message: str):
        access_token = await self.get_access_token()
        if access_token:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            message = {
                "touser": self.user_id,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": message},
            }
            try:
                response = await self.client.post(url, json=message)
                return response.json()
            except Exception as e:
                logger.error(f"发送文本消息失败: {e}")
                return {"error": "Failed to send text message"}
        else:
            return {"error": "Failed to get access token"}

    async def send_photo(self, photo_url: str):
        media_id = await self.upload_image_get_media_id(photo_url)
        if media_id:
            access_token = await self.get_access_token()
            if access_token:
                url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                message = {
                    "touser": self.user_id,
                    "msgtype": "image",
                    "agentid": self.agent_id,
                    "image": {"media_id": media_id},
                }
                try:
                    response = await self.client.post(url, json=message)
                    return response.json()
                except Exception as e:
                    logger.error(f"发送图片消息失败: {e}")
                    return {"error": "Failed to send image message"}
            else:
                return {"error": "Failed to get access token"}
        else:
            return {"error": "Failed to upload image"}

    async def send_news(
        self, message: str, photo_url: str, message_url: str, title: str
    ):
        access_token = await self.get_access_token()
        if access_token:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            message = {
                "touser": self.user_id,
                "msgtype": "news",
                "agentid": self.agent_id,
                "news": {
                    "articles": [
                        {
                            "title": title,
                            "description": message,
                            "picurl": photo_url,
                            "url": message_url,
                        }
                    ]
                },
            }
            try:
                response = await self.client.post(url, json=message)
                return response.json()
            except Exception as e:
                logger.error(f"发送图文消息失败: {e}")
                return {"error": "Failed to send news message"}
        else:
            return {"error": "Failed to get access token"}

    async def send_message(
        self, message: str, photo_url: str = "", message_url="", title=""
    ):
        if self.send_type == "text":
            await self.send_text(message)
        elif self.send_type == "photo":
            if photo_url:
                # 先发送图片，然后发送文本
                await self.send_photo(photo_url)
                await self.send_text(message)
            else:
                # 如果没有图片URL，只发送文本
                await self.send_text(message)
        elif self.send_type == "news":
            await self.send_news(message, photo_url, message_url, title)
