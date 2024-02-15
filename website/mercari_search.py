from .base.scraper_mercari import BaseSearch
from .base.common_imports import *

from uuid import uuid4


class MercariSearch(BaseSearch):

    def __init__(self, http_client):
        super().__init__("https://api.mercari.jp/v2/entities:search", http_client)

    async def search(
        self, search, iteration_count, user_max_pages
    ) -> AsyncGenerator[SearchResultItem, None]:
        score_page, created_time_page = (
            (100, 100) if iteration_count == 0 else (3, user_max_pages)
        )
        tasks = [
            self.search_with_sort(search, "SORT_SCORE", score_page),
            self.search_with_sort(search, "SORT_CREATED_TIME", created_time_page),
        ]
        all_products = await asyncio.gather(*tasks, return_exceptions=True)

        for products in all_products:
            if isinstance(products, (Exception, BaseException)):
                continue
            for product in products:
                yield product

    async def search_with_sort(
        self, search, sort_type, max_pages
    ) -> List[SearchResultItem]:
        async def fetch_with_semaphore(page):
            async with semaphore:
                return await self.fetch_products(search, page, sort_type)

        # 限制最大页数
        # 确保并发数不超过 MAX_CONCURRENT_PAGES 或 max_pages
        concurrent_pages = min(search["max_concurrency"], max_pages)
        # 使用 semaphore 来限制并发数
        semaphore = asyncio.Semaphore(concurrent_pages)
        tasks = [fetch_with_semaphore(page) for page in range(max_pages)]

        pages_content = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            product
            for page_products in pages_content
            if isinstance(page_products, list)
            for product in page_products
        ]

    async def fetch_products(
        self, search, page: int, sort_type
    ) -> List[SearchResultItem]:
        try:
            serialized_data = json.dumps(
                self.create_data(search, page, sort_type), ensure_ascii=False
            ).encode("utf-8")
            response = await self.get_response("POST", data=serialized_data)
            if (response is None) or ("items" not in response):
                return []  # 处理空响应或缺少项的情况

            tasks = [self.create_product_from_card(item) for item in response["items"]]
            products = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤掉异常对象
            return [
                product for product in products if isinstance(product, SearchResultItem)
            ]
        except Exception as e:
            # 处理可能的异常情况，例如网络错误或解析失败, 或者根据需要进行其他合适的错误处理
            logger.error(f"Error fetching products: {e}")
            return []

    def create_data(self, search, page, sort_type):
        return {
            # this seems to be random, but we'll add a prefix for mercari to track if they wanted to
            "userId": f"MERCARI_BOT_{uuid4()}",
            "pageSize": self.page_size,
            "pageToken": f"v1:{page}",
            # same thing as userId, courtesy of a prefix for mercari
            "searchSessionId": f"MERCARI_BOT_{uuid4()}",
            # this is hardcoded in their frontend currently, so leaving it
            "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
            "searchCondition": {
                "keyword": search["keyword"],
                "excludeKeyword": getattr(search["filter"], "exclude_keyword", ""),
                "sort": sort_type,
                "order": "ORDER_DESC",
                "status": getattr(
                    search["filter"], "status", ["STATUS_ON_SALE", "STATUS_TRADING"]
                ),
                "categoryId": getattr(search["filter"], "category", []),
                "brandId": getattr(search["filter"], "brandId", []),
                "priceMin": getattr(search["filter"], "price_min", 0),
                "priceMax": getattr(search["filter"], "price_max", 0),
            },
            # I'm not certain what these are, but I believe it's what mercari queries against
            # this is the default in their site, so leaving it as these 2
            "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        }

    async def get_item_site(self, item):
        return "mercari"

    async def get_item_status(self, item):
        if item.get("status") == "ITEM_STATUS_ON_SALE":
            status = 1
        else:
            status = 0
        return status
