from abc import ABC, abstractmethod
from math import ceil
from urllib import parse
from .common_imports import *


class BaseScrapy(ABC):
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 初始重试延迟（秒）

    def __init__(self, base_url, page_size, http_client, method, headers=None):
        self.base_url = base_url
        self.page_size = page_size
        self.headers = headers if headers else {}
        self.http_client = http_client
        self.method = method

    async def async_init(self):
        pass

    async def search(
        self, search_term, iteration_count, user_max_pages
    ) -> AsyncGenerator[SearchResultItem, None]:
        # 获取最大页数
        max_pages = await self.get_max_pages(search_term)

        # 限制最大页数
        if iteration_count != 0:
            max_pages = min(max_pages, user_max_pages)

        if max_pages == 0:
            return  # 直接返回，不执行任何任务

        # 确保并发数不超过 MAX_CONCURRENT_PAGES 或 max_pages
        concurrent_pages = min(search_term["max_concurrency"], max_pages)

        # 使用 semaphore 来限制并发数
        semaphore = asyncio.Semaphore(concurrent_pages)

        async def fetch_with_semaphore(page):
            async with semaphore:
                return await self.fetch_products(search_term, page)

        tasks = [fetch_with_semaphore(page) for page in range(1, max_pages + 1)]
        pages_content = await asyncio.gather(*tasks, return_exceptions=True)

        # 遍历每一页的结果
        for page_products in pages_content:
            # 处理或记录异常 跳过空列表
            if (
                isinstance(page_products, (Exception, BaseException))
                or not page_products
            ):
                # 处理异常或空结果
                continue
            # 迭代返回该页的商品信息
            for product in page_products:
                yield product

    # 搜索具体页数里的内容
    async def fetch_products(self, search_term, page: int) -> List[SearchResultItem]:
        # 获取响应体的text
        response_text = await self.get_response(search_term, page)
        if response_text is None:
            logger.error(f"Failed to get response for page {page}'")
            return []

        # 获取商品信息，json格式或者Selecter
        items = await self.get_response_items(response_text)
        # logger.info(f"Got {len(items)} items on page {page}")

        # 如果商品列表为空，则直接返回
        if not items:
            return []  # 如果没有项目，直接退出函数

        tasks = [self.create_product_from_card(item) for item in items]  # type: ignore
        products = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            product for product in products if isinstance(product, SearchResultItem)
        ]

    # 请求链接和参数，可在子类中重写
    async def create_request_url(self, params):
        return self.base_url, params

    async def get_response(self, search_term, page: int) -> Optional[str]:
        try:
            if self.method.upper() == "GET":
                params = await self.create_search_params(search_term, page)
                url, params = await self.create_request_url(params)
                response = await self.http_client.get(
                    url, params=params, headers=self.headers
                )
            elif self.method.upper() == "POST":
                data = self.create_data(search_term, page)
                response = await self.http_client.post(
                    self.base_url, data=data, headers=self.headers
                )
            else:
                raise ValueError("Unsupported HTTP method")
            response.raise_for_status()
            response_text = await response.text()
            await response.close()
            return response_text
        except Exception as e:
            logger.error(f"发生未预期的异常：{e}")

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

        site = await self.get_item_site(item=item)

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
            match = re.search(r"\d+", hit_number.replace(",", ""))
            number = int(match.group()) if match else 0
            return ceil(number / page_size)
        except AttributeError:
            logger.error("No number found")
            return 0

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
    async def get_item_site(self, item) -> str:
        pass

    @abstractmethod
    async def get_item_id(self, item) -> str:
        pass

    @abstractmethod
    async def get_item_name(self, item) -> str:
        pass

    @abstractmethod
    async def get_item_price(self, item) -> float:
        pass

    @abstractmethod
    async def get_item_product_url(self, item, id) -> str:
        pass

    @abstractmethod
    async def get_item_image_url(self, item, id) -> str:
        pass

    @abstractmethod
    async def get_item_status(self, item) -> int:
        pass

    def create_data(self, search, page):
        pass
