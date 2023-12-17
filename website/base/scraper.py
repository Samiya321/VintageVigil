from abc import ABC, abstractmethod
from math import ceil
from urllib import parse
from .common_imports import *


class BaseScrapy(ABC):
    MAX_CONCURRENT_PAGES = 10  # Moved to a class-level constant
    MAX_RETRIES = 3  # 定义最大重试次数
    RETRY_DELAY = 1  # 定义初始重试延迟（秒）

    def __init__(self, base_url, page_size, client, headers=None):
        self.base_url = base_url
        self.page_size = page_size
        self.headers = headers if headers else {}
        self.client = client

    async def search(
        self, search_term, iteration_count
    ) -> AsyncGenerator[SearchResultItem, None]:
        # 获取最大页数
        max_pages = await self.get_max_pages(search_term)

        # 只处理前20页的内容
        # if iteration_count != 0 and max_pages > 30:
        #     max_pages = 30

        if max_pages == 0:
            return  # 直接返回，不执行任何任务

        # 限制最大页数
        # 确保并发数不超过 MAX_CONCURRENT_PAGES 或 max_pages
        concurrent_pages = min(self.MAX_CONCURRENT_PAGES, max_pages)

        # 使用 semaphore 来限制并发数
        semaphore = asyncio.Semaphore(concurrent_pages)

        async def fetch_with_semaphore(page):
            async with semaphore:
                return await self.fetch_products(search_term, page)

        tasks = [fetch_with_semaphore(page) for page in range(1, max_pages + 1)]
        pages_content = await asyncio.gather(*tasks, return_exceptions=True)

        # 全并发处理每一页
        # tasks = [
        #     self.fetch_products(search_term, page) for page in range(1, max_pages + 1)
        # ]
        # pages_content = await asyncio.gather(*tasks, return_exceptions=True)

        # 遍历每一页的结果
        for page_products in pages_content:
            # 处理或记录异常 跳过空列表
            if isinstance(page_products, Exception) or not page_products:
                # 处理异常或空结果
                continue
            # 迭代返回该页的商品信息
            for product in page_products:
                yield product

    # 搜索具体页数里的内容
    async def fetch_products(
        self, search_term, page: int
    ) -> AsyncGenerator[SearchResultItem, None]:
        # 获取响应体的text
        response_text = await self.get_response(search_term, page)
        if response_text is None:
            logger.error(f"Failed to get response for page {page}'")
            return []

        # 获取商品信息，json格式或者Selecter
        items = await self.get_response_items(response_text)
        # logger.info(f"Got {len(items)} items on page {page}")
        # 如果商品列表为空，则直接返回[]
        if not items:
            return []

        tasks = [self.create_product_from_card(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # 请求链接和参数，可在子类中重写
    async def create_request_url(self, params):
        return self.base_url, params

    async def get_response(self, search_term, page: int):
        params = await self.create_search_params(search_term, page)
        url, params = await self.create_request_url(params)

        for attempt in range(BaseScrapy.MAX_RETRIES):
            try:
                response = await self.client.get(
                    url, params=params, headers=self.headers, follow_redirects=True
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.error(f"请求的URL {e.response.url} 返回了404状态码，停止重试。")
                    return None
                logger.warning(
                    f"由于状态码 {e.response.status_code}，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)
            except httpx.TimeoutException:
                logger.warning(
                    f"请求超时，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)
            except httpx.RequestError as e:
                logger.warning(
                    f"网络错误：{e}，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)

            except Exception as e:
                logger.error(f"发生未预期的异常：{e}")
                break  # 发生未知异常时终止循环
        else:
            logger.error(f"在尝试了 {BaseScrapy.MAX_RETRIES} 次后，仍未能成功获取响应。")

        return None

    async def create_product_from_card(self, item) -> SearchResultItem:
        """
        Create a product object from an item card.

        Args:
            item: The item card to process.

        Returns:
            SearchResultItem: The processed product.
        """
        name = await self.get_item_name(item=item)

        product_id = await self.get_item_id(item=item)

        product_url = await self.get_item_product_url(item=item, id=product_id)

        image_url = await self.get_item_image_url(item=item, id=product_id)

        price = await self.get_item_price(item=item)

        site = await self.get_item_site()

        status = await self.get_item_status(item=item)

        return SearchResultItem(
            name=name,
            price=price,
            image_url=image_url,
            product_url=product_url,
            id=product_id,
            site=site,
            status=status,
        )

    async def extract_number_from_content(
        self, hit_number: str, page_size: int
    ) -> Optional[int]:
        """
        Extracts a number from a string and calculates the number of pages based on the page size.

        Args:
            hit_number (str): The string containing the number.
            page_size (int): The size of each page.

        Returns:
            Optional[int]: The total number of pages or None if no number is found.
        """
        try:
            number = int(re.search(r"\d+", hit_number.replace(",", "")).group())
            return ceil(number / page_size)
        except AttributeError:
            logger.error("No number found")
            return None

    def get_param_value(self, url: str, param_name: str) -> Optional[str]:
        """
        Extracts the value of a specified parameter from a URL.

        Args:
            url (str): The URL to parse.
            param_name (str): The name of the parameter to extract.

        Returns:
            Optional[str]: The value of the parameter or None if not found.
        """
        parsed_url = parse.urlparse(url)
        query_params = parse.parse_qs(parsed_url.query)
        return query_params.get(param_name, [None])[0]

    def encode_params(self, params: dict) -> str:
        """
        Encodes URL parameters, excluding the 'page' parameter when its value is 1.

        Args:
            params (dict): The parameters to encode.

        Returns:
            str: The encoded URL parameters.
        """
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
    async def get_item_site(self):
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
    async def get_item_product_url(self, item, id):
        pass

    @abstractmethod
    async def get_item_image_url(self, item, id):
        pass

    @abstractmethod
    async def get_item_status(self, item):
        pass
