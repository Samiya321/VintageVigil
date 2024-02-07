from datetime import datetime, timedelta
from io import BytesIO

from loguru import logger


class WecomClient:
    def __init__(
        self, corp_id, corp_secret, agent_id, user_ids, http_client, send_type="news"
    ):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.user_ids = user_ids
        self.access_token = None
        self.token_expires_at = None
        self.send_type = send_type
        self.http_client = http_client
        self.client_type = "wecom"

    async def initialize(self):
        for index, chat_id in enumerate(self.user_ids):
            await self.send_message(
                title="WeCom 实例化成功",
                photo_url="https://raw.githubusercontent.com/Samiya321/VintageVigil/main/favicon.ico",
                message="WeCom 实例化成功。",
                chat_ids_index=index,
            )

    async def get_access_token(self, force_refresh=False):
        current_time = datetime.now()
        if (
            self.access_token
            and self.token_expires_at
            and self.token_expires_at > current_time
            and not force_refresh
        ):
            return self.access_token

        return await self._fetch_access_token()

    async def _fetch_access_token(self):
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            response = await self.http_client.get(url)
            data = await response.json()
            await response.close()
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)  # 默认有效期7200秒
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            return self.access_token
        except Exception as e:
            logger.error(f"获取访问令牌失败: {e}")
            return None

    async def upload_image_get_media_id(self, image_url):
        access_token = await self.get_access_token()
        if not access_token:
            return None

        return await self._upload_image(image_url, access_token)

    async def _upload_image(self, image_url, access_token):
        upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image"
        try:
            image_response = await self.http_client.get(image_url)
            image_response.raise_for_status()

            files = {"media": BytesIO(await image_response.content())}
            response = await self.http_client.post(upload_url, files=files)
            response_json = await response.json()
            await response.close()
            await image_response.close()
            return response_json.get("media_id")
        except Exception as e:
            logger.error(f"上传图片失败: {e}")
            return None

    async def _send_wechat_message(self, url, message_payload):
        try:
            response = await self.http_client.post(url, json=message_payload)
            response_json = await response.json()
            await response.close()
            return response_json
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            return {"error": "Failed to send message"}

    async def send_text(self, message: str, chat_id):
        access_token = await self.get_access_token()
        if not access_token:
            return {"error": "Failed to get access token"}

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        payload = {
            "touser": chat_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": message},
        }
        return await self._send_wechat_message(url, payload)

    async def send_photo(self, photo_url: str, chat_id):
        media_id = await self.upload_image_get_media_id(photo_url)
        if not media_id:
            return {"error": "Failed to upload image"}

        access_token = await self.get_access_token()
        if not access_token:
            return {"error": "Failed to get access token"}

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        payload = {
            "touser": chat_id,
            "msgtype": "image",
            "agentid": self.agent_id,
            "image": {"media_id": media_id},
        }
        return await self._send_wechat_message(url, payload)

    async def send_news(
        self, message: str, photo_url: str, message_url: str, title: str, chat_id
    ):
        access_token = await self.get_access_token()
        if not access_token:
            return {"error": "Failed to get access token"}

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        payload = {
            "touser": chat_id,
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
        return await self._send_wechat_message(url, payload)

    async def send_message(
        self,
        message: str,
        photo_url: str = "",
        message_url="",
        title="",
        chat_ids_index=0,
    ):
        chat_id = self.user_ids[chat_ids_index]
        if self.send_type == "text":
            return await self.send_text(message, chat_id)
        elif self.send_type == "photo" and photo_url:
            await self.send_photo(photo_url, chat_id)
            await self.send_text(message, chat_id)
            return
        elif self.send_type == "news":
            return await self.send_news(message, photo_url, message_url, title, chat_id)
        else:
            logger.warning(f"未知的发送类型: {self.send_type}")
            return {"error": "Unknown send type"}
