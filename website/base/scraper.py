from abc import ABC, abstractmethod
from math import ceil
from urllib import parse
from .common_imports import *


class BaseScrapy(ABC):
    def __init__(
        self,
        base_url,
        page_size,
        client,
        headers=None,
    ):
        self.base_url = base_url
        self.pageSize = page_size
        self.headers = headers if headers else {}
        self.client = client

    async def search(
        self, search, iteration_count
    ) -> AsyncGenerator[SearchResultItem, None]:
        # 获取最大页数
        max_pages = await self.get_max_pages(search)
        if max_pages == 0:
            return  # 直接返回，不执行任何任务

        # 根据最大页数，把每一页生成一个任务
        tasks = (self.fetch_products(search, page) for page in range(1, max_pages + 1))
        # 运行任务
        pages_content = await asyncio.gather(*tasks, return_exceptions=True)

        # 遍历每一页的结果
        for index, page_products in enumerate(pages_content):
            # 处理或记录异常
            if isinstance(page_products, Exception):
                logger.error(f"Error fetching page {index + 1}: {page_products}")
                continue
            # 跳过空列表
            if not page_products:
                continue
            # 迭代返回该页的商品信息
            for product in page_products:
                yield product

    # 搜索具体页数里的内容
    async def fetch_products(
        self, search, page: int
    ) -> AsyncGenerator[SearchResultItem, None]:
        # 获取响应体的text
        res = await self.get_response(search, page)
        if res is None:
            logger.error(f"Failed to get response for page {page} in search '{search}'")
            return []

        # 获取商品信息，json格式或者Selecter
        items = await self.get_response_items(res)

        # 如果商品列表为空，则直接返回[]
        if not items:
            return []

        # 将商品列表中的商品封装为自己的格式
        tasks = (self.create_product_from_card(item) for item in items)
        return await asyncio.gather(*tasks)

    # 请求链接和参数，可在子类中重写
    async def create_request_url(self, params):
        return self.base_url, params

    async def get_response(self, search, page: int):
        params = await self.create_search_params(search, page)
        
        url, params = await self.create_request_url(params)

        max_retries = 5  # 定义最大重试次数
        retry_delay = 1  # 定义初始重试延迟（秒）

        for attempt in range(max_retries):
            try:
                response = await self.client.get(
                    url, params=params, headers=self.headers, timeout=20
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {e.response.url} after status code {e.response.status_code}"
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries}  due to network error: {e}"
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
        else:
            logger.error(f"Failed to get response after {max_retries} attempts")

        return None  # 如果重试失败，返回 None

    async def create_product_from_card(self, item) -> SearchResultItem:
        name = await self.get_item_name(item)

        product_url = await self.get_item_product_url(item)

        id = await self.get_item_id(product_url)

        image_url = await self.get_item_image_url(item)

        price = await self.get_item_price(item)

        site = await self.get_item_site()

        search_result_item = SearchResultItem(
            name=name,
            price=price,
            image_url=image_url,
            product_url=product_url,
            id=id,
            site=site,
        )
        return search_result_item

    async def extract_number_from_content(self, hit_number: str, page_size: int) -> int:
        result = hit_number.replace(",", "")
        result = re.search(r"\d+", result)
        if result:
            number = int(result.group())
        else:
            logger.error("No number found")
            return 0
        return ceil(number / page_size)

    def get_param_value(self, url, param_name):
        parsed_url = parse.urlparse(url)
        query_params = parse.parse_qs(parsed_url.query)
        return query_params.get(param_name, [None])[0]

    def encode_params(self, params):
        # 自定义URL参数编码，排除页码为1的情况
        return "&".join(
            f"{key}={value}"
            for key, value in params.items()
            if not (key == "page" and value == 1)
        )

    @abstractmethod
    async def create_search_params(self, search, page: int) -> dict:
        pass

    @abstractmethod
    async def get_max_pages(self, search) -> int:
        pass

    @abstractmethod
    async def get_response_items(self, response):
        pass

    @abstractmethod
    async def get_item_id(self, item):
        pass

    @abstractmethod
    async def get_item_name(self, item):
        pass

    @abstractmethod
    async def get_item_price(self, item):
        pass

    @abstractmethod
    async def get_item_image_url(self, item):
        pass

    @abstractmethod
    async def get_item_product_url(self, item):
        pass

    @abstractmethod
    async def get_item_site(self):
        pass
