import aiohttp
import asyncio
from aiohttp import ClientTimeout, FormData
from typing import Optional, Dict, Any, Union
from tenacity import (
    retry,
    wait_fixed,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
)
from loguru import logger


# 通用响应类，用于封装 aiohttp 和 httpx 的响应对象
class AsyncResponse:
    def __init__(self, response: aiohttp.ClientResponse):
        self._response = response

    async def json(self):
        # 确保异步读取 JSON 数据
        return await self._response.json()

    async def text(self):
        # 确保异步读取文本数据
        return await self._response.text()

    async def content(self):
        # 确保异步读取二进制数据
        return await self._response.read()

    @property
    def status_code(self):
        return self._response.status

    def raise_for_status(self):
        self._response.raise_for_status()

    async def close(self):
        # if self._response is not None:
        #     await self._response.close()
        pass


def custom_before_sleep_log(retry_state):
    exception = retry_state.outcome.exception()
    if exception:
        if hasattr(exception, "status"):
            status_code = exception.status
            logger.error(f"HTTP 错误 {status_code}: {exception.message}")
            if status_code in (503, 404):
                logger.warning(f"服务器返回状态码 {status_code}，将在延迟后重试。")
        elif isinstance(exception, aiohttp.ServerDisconnectedError):
            logger.error("服务器断开连接。")
        elif isinstance(exception, aiohttp.ClientConnectorError):
            logger.error(f"连接失败: {exception}")
        elif isinstance(exception, asyncio.TimeoutError):
            logger.error("请求超时。")
        else:
            logger.error(f"遇到意外错误：{exception}")

        # 如果可能，打印出更多关于请求的信息
        if hasattr(exception, "request"):
            request = exception.request
            logger.error(f"请求详情 - URL: {request.url}, 方法: {request.method}")
    else:
        logger.info("正在重试...")


# 使用Tenacity库进行重试的通用配置
RETRY_ARGUMENTS = {
    "wait": wait_fixed(1),
    "stop": stop_after_attempt(3),
    "retry": retry_if_exception_type(aiohttp.ClientError),
    "before_sleep": custom_before_sleep_log,
}


class AsyncAIOHTTPClient:

    def __init__(
        self,
        http2=False,
        timeout: Optional[float] = 10.0,
        proxy: Optional[str] = None,
        redirects=True,
        ssl_verify: bool = False,
    ):
        self._timeout = ClientTimeout(total=timeout)
        self._ssl_verify = ssl_verify
        self._proxy = proxy
        self._client: Optional[aiohttp.ClientSession] = None

    async def _get_client(self) -> aiohttp.ClientSession:
        if self._client is None or self._client.closed:
            self._client = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=aiohttp.TCPConnector(ssl=self._ssl_verify),
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def _request(self, method: str, url: str, **kwargs) -> AsyncResponse:
        client = await self._get_client()
        if self._proxy:
            kwargs["proxy"] = self._proxy
        response = await client.request(method, url, ssl = False, **kwargs)
        return AsyncResponse(response)

    @retry(**RETRY_ARGUMENTS)
    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> AsyncResponse:
        return await self._request("GET", url, params=params, headers=headers)


    @retry(**RETRY_ARGUMENTS)
    async def post(
        self,
        url: str,
        *,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> AsyncResponse:
        if files:
            data = FormData()
            for key, value in files.items():
                # 判断value是否为一个包含_file对象的元组
                if isinstance(value, tuple):
                    filename, file_content, *rest = value
                    content_type = rest[0] if rest else "application/octet-stream"
                    # 检查 file_content 是否为 _io.BytesIO 实例
                    if hasattr(file_content, "getvalue"):
                        file_content = file_content.getvalue()
                    data.add_field(
                        key, file_content, filename=filename, content_type=content_type
                    )
                else:
                    # 处理非元组形式的文件内容（直接为文件内容）
                    data.add_field(key, value)
            kwargs = {"data": data}
        else:
            kwargs = {"data": data, "json": json}

        return await self._request("POST", url, headers=headers, **kwargs)
