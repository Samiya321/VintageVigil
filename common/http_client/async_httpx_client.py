import httpx
from loguru import logger
from tenacity import (
    retry,
    wait_fixed,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
)


# 自定义重试前的回调函数
def custom_before_sleep_log(retry_state):
    exception = retry_state.outcome.exception()
    if exception:
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            logger.error(f"HTTP 错误 {status_code}: {exception.response.text}")
            if status_code == 503:
                logger.warning("服务器暂不可用 (503)，将在延迟后重试。")
            elif status_code == 404:
                logger.error("请求的URL返回了404状态码，停止重试。")
        elif isinstance(exception, httpx.TimeoutException):
            logger.error("请求超时。")
        elif isinstance(exception, httpx.RequestError):
            logger.error(f"网络请求错误：{exception}")
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
    "retry": retry_if_exception_type(httpx.HTTPError),
    "before_sleep": custom_before_sleep_log,
}
class AsyncHTTPResponse:
    def __init__(self, response: httpx.Response):
        self._response = response

    async def json(self):
        return self._response.json()

    async def text(self):
        return self._response.text

    async def content(self):
        return self._response.content

    @property
    def status_code(self):
        return self._response.status_code

    def raise_for_status(self):
        self._response.raise_for_status()

    async def close(self):
        pass

class AsyncHTTPXClient:
    def __init__(
        self,
        http2=False,
        timeout=10.0,
        proxy=None,
        redirects=True,
        ssl_verify=False,
    ):        
        self._client_kwargs = {
            "http2": http2,
            "timeout": timeout,
            "proxies": proxy,
            "follow_redirects": redirects,
            "verify": ssl_verify,
        }
        self._client = None

    async def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(**self._client_kwargs)
        return self._client

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(self, method, url, **kwargs) -> AsyncHTTPResponse:
        client = await self._get_client()
        response = await client.request(method, url, **kwargs)
        return AsyncHTTPResponse(response)

    @retry(**RETRY_ARGUMENTS)
    async def get(self, url, *, params=None, headers=None) -> AsyncHTTPResponse:
        return await self._request("GET", url, params=params, headers=headers)

    @retry(**RETRY_ARGUMENTS)
    async def post(
        self, url, *, data=None, json=None, headers=None, files=None
    ) -> AsyncHTTPResponse:
        return await self._request(
            "POST", url, data=data, json=json, headers=headers, files=files
        )
