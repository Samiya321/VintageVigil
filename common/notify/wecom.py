from datetime import datetime, timedelta
from loguru import logger
import asyncio

class WecomClient:
    def __init__(
        self, corp_id, corp_secret, agent_id, user_ids, http_client, send_type="news"
    ):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.user_ids = user_ids
        self.http_client = http_client
        self.send_type = send_type
        self.client_type = "wecom"
        self.access_token = None
        self.token_expires_at = None
        self.message_queue = asyncio.Queue()
        self.worker_task = asyncio.create_task(self.process_message_queue())

    async def _make_request(self, url, method="get", **kwargs):
        """统一处理网络请求"""
        try:
            if method == "get":
                response = await self.http_client.get(url, **kwargs)
            else:
                response = await self.http_client.post(url, **kwargs)
            data = await response.json()
            if data.get("errcode") != 0:
                logger.error(f"Error from WeCom API: {data.get('errmsg')}")
                return None
            return data
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    async def initialize(self):
        for index, chat_id in enumerate(self.user_ids):
            await self.send_message(
                title="WeCom 实例化成功",
                photo_url="https://raw.githubusercontent.com/Samiya321/VintageVigil/main/favicon.ico",
                message="WeCom 实例化成功。",
                chat_ids_index=index,
            )

    async def get_access_token(self, force_refresh=False):
        """获取或刷新访问令牌"""
        if (
            self.access_token
            and self.token_expires_at > datetime.now()
            and not force_refresh
        ):
            return self.access_token
        return await self._fetch_access_token()

    async def _fetch_access_token(self):
        """从WeCom API获取新的访问令牌"""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        data = await self._make_request(url)
        if data:
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        return self.access_token

    async def upload_image_get_media_id(self, image_url):
        access_token = await self.get_access_token()
        if not access_token:
            return None

        return await self._upload_image(image_url, access_token)

    async def _upload_image(self, image_url, access_token):
        upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=file"
        try:
            image_response = await self.http_client.get(image_url)
            image_response.raise_for_status()

            files = {"file": await image_response.content()}
            response = await self.http_client.post(upload_url, files=files)
            response_json = await response.json()
            return response_json.get("media_id")
        except Exception as e:
            logger.error(f"上传图片失败: {e}")
            return None

    async def send_text(self, message: str, chat_id):
        """向企业微信用户发送文本消息"""
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
        return await self._make_request(url, method="post", json=payload)

    async def send_photo(self, photo_url: str, chat_id):
        """上传图片到企业微信服务器并向用户发送图片消息"""
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
        return await self._make_request(url, method="post", json=payload)

    async def send_news(
        self, message: str, photo_url: str, message_url: str, title: str, chat_id
    ):
        """向企业微信用户发送图文消息"""
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
                        "url": message_url,
                        "picurl": photo_url,
                    }
                ]
            },
        }
        return await self._make_request(url, method="post", json=payload)

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

    async def process_message_queue(self):
        """
        持续处理消息队列中的消息。
        """
        while True:
            message_info = await self.message_queue.get()

            # 提取所有需要的信息
            message = message_info["message"]
            photo_url = message_info.get("photo_url", "")
            message_url = message_info.get("message_url", "")
            title = message_info.get("title", "")
            chat_ids_index = message_info["chat_ids_index"]  # 直接使用索引

            try:
                # 直接调用send_message方法发送消息
                await self.send_message(
                    message=message,
                    photo_url=photo_url,
                    message_url=message_url,
                    title=title,
                    chat_ids_index=chat_ids_index,
                )
            except Exception as e:
                logger.error(f"Error sending WeCom message: {e}")
            finally:
                self.message_queue.task_done()

    async def enqueue_message(
        self, message, photo_url="", message_url="", title="", chat_ids_index=0
    ):
        """
        将消息根据类型加入到队列中。
        """
        # 直接使用send_type从self获取，不需要作为参数传递
        await self.message_queue.put(
            {
                "message": message,
                "photo_url": photo_url,
                "message_url": message_url,
                "title": title,
                "chat_ids_index": chat_ids_index,  # 使用索引而非直接传chat_id
            }
        )

    async def shutdown(self):
        """优雅地关闭消息队列和后台任务"""
        await self.message_queue.join()
        self.worker_task.cancel()
        try:
            await self.worker_task
        except asyncio.CancelledError:
            pass
