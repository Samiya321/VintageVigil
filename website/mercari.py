from uuid import uuid4

import ecdsa
from mercapi.util.jwt import generate_dpop

from .base.common_imports import *


class MercariSearchStatus:
    TRADING = "STATUS_SOLD_OUT"
    ON_SALE = "STATUS_TRADING"
    SOLD_OUT = "STATUS_ON_SALE"


class MercariSort:
    SORT_DEFAULT = "SORT_DEFAULT"
    SORT_CREATED_TIME = "SORT_CREATED_TIME"
    SORT_NUM_LIKES = "SORT_NUM_LIKES"
    SORT_SCORE = "SORT_SCORE"
    SORT_PRICE = "SORT_PRICE"


class MercariOrder:
    ORDER_DESC = "ORDER_DESC"
    ORDER_ASC = "ORDER_ASC"


class MercariItemStatus:
    ITEM_STATUS_UNSPECIFIED = "ITEM_STATUS_UNSPECIFIED"
    ITEM_STATUS_ON_SALE = "ITEM_STATUS_ON_SALE"
    ITEM_STATUS_TRADING = "ITEM_STATUS_TRADING"
    ITEM_STATUS_SOLD_OUT = "ITEM_STATUS_SOLD_OUT"
    ITEM_STATUS_STOP = "ITEM_STATUS_STOP"
    ITEM_STATUS_CANCEL = "ITEM_STATUS_CANCEL"
    ITEM_STATUS_ADMIN_CANCEL = "ITEM_STATUS_ADMIN_CANCEL"


class BaseSearch:
    def __init__(self, root_url, page_size=120):
        self.page_size = page_size
        self.root_url = root_url
        self.client = httpx.AsyncClient(
            proxies=os.getenv("HTTP_PROXY"),
            verify=False,
            http2=True,
            timeout=httpx.Timeout(10.0),  # 设置统一的超时时间
        )

    async def close(self):
        await self.client.aclose()

    async def search(self, **kwargs) -> AsyncGenerator[SearchResultItem, None]:
        pass  # 由子类实现

    async def fetch_products(self, **kwargs) -> AsyncGenerator[SearchResultItem, None]:
        pass  # 由子类实现

    async def get_response(self, method, data=None, params=None):
        max_retries = 5  # Maximum number of retries
        retry_delay = 1  # Initial delay between retries, in seconds

        for attempt in range(max_retries):
            try:
                headers = self.create_headers(method.upper())

                if method.lower() == "post":
                    response = await self.client.post(
                        url=self.root_url,
                        headers=headers,
                        data=data,
                    )
                else:  # Assume GET if not POST
                    response = await self.client.get(
                        url=self.root_url,
                        headers=headers,
                        params=params,
                    )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                error_message = (
                    f"HTTP error {e.response.status_code} on attempt {attempt + 1}"
                )
            except (httpx.RequestError, httpx.TimeoutException) as e:
                error_message = f"Network error on attempt {attempt + 1}: {e}"
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break  # Breaking on unexpected errors

            # Log the error message and handle retry logic
            logger.error(error_message)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed after {max_retries} attempts.")
                break

        return None

    def create_headers(self, method):
        # ... 实现创建请求头的逻辑
        headers = {
            "DPoP": self.create_headers_dpop(method),
            "X-Platform": "web",  # mercari requires this header
            "Accept": "*/*",
            "Accept-Encoding": "deflate, gzip",
            "Content-Type": "application/json; charset=utf-8",
            # courtesy header since they're blocking python-requests (returns 0 results)
            "User-Agent": "python-mercari",
        }
        return headers

    def create_headers_dpop(self, method):
        dpop = generate_dpop(
            url=self.root_url,
            method=method,
            key=ecdsa.SigningKey.generate(ecdsa.NIST256p),
            extra_payload={"uuid": str(uuid4())},
        )
        return dpop

    async def create_product_from_card(self, item) -> SearchResultItem:
        # 商品名称
        name = item["name"]
        # 商品ID
        id = item["id"]
        # 商品价格
        price = item["price"]

        # 商品链接
        if id[0] == "m" and id[1:].isdigit():
            product_url = "https://jp.mercari.com/item/{}".format(id)
        else:
            product_url = "https://jp.mercari.com/shops/product/{}".format(id)

        # 商品图片链接
        image_type = "image"
        if id[0] == "m" and id[1:].isdigit():
            if image_type == "image":
                # image_url = "https://static.mercdn.net/item/detail/orig/photos/{}_1.jpg?random=64".format(id)
                image_url = "https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/{}_1.jpg?random=64".format(
                    id
                )
            else:
                # image_url = "https://static.mercdn.net/thumb/photos/{}_1.jpg?random=64".format(id)

                image_url = item["thumbnails"][0] + "?random=64"

        else:
            image_url = item["thumbnails"][0] + "?random=64"

        # 组合商品信息
        item = SearchResultItem(
            name=name,
            price=price,
            image_url=image_url,
            product_url=product_url,
            id=id,
            site="mercari",
        )

        return item


class MercariSearch(BaseSearch):
    def __init__(self):
        super().__init__("https://api.mercari.jp/v2/entities:search")

    async def search(
            self, search, iteration_count
    ) -> AsyncGenerator[SearchResultItem, None]:
        # iteration_count = 2
        if iteration_count == 0:
            score_page = 100
            created_time_page = 100
        else:
            score_page = 3
            created_time_page = 3
        tasks = [
            self.search_with_sort(search, "SORT_SCORE", score_page),
            self.search_with_sort(search, "SORT_CREATED_TIME", created_time_page),
        ]
        all_products = await asyncio.gather(*tasks, return_exceptions=True)

        for products in all_products:
            if isinstance(products, Exception):
                # 这里可以记录异常或执行其他异常处理逻辑
                continue

            for product in products:
                yield product

    async def search_with_sort(
            self, search, sort_type, max_pages
    ) -> List[SearchResultItem]:
        tasks = (
            self.fetch_products(search, page, sort_type) for page in range(0, max_pages)
        )
        pages_content = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            product
            for page_products in pages_content
            if not isinstance(page_products, Exception)
            for product in page_products
        ]

    async def fetch_products(
            self, search, page: int, sort_type
    ) -> AsyncGenerator[SearchResultItem, None]:
        try:
            data = self.create_data(search, page, sort_type)
            serialized_data = json.dumps(data, ensure_ascii=False).encode("utf-8")

            response = await self.get_response("POST", data=serialized_data)

            if not response or "items" not in response:
                return []  # 处理空响应或缺少项的情况

            tasks = (self.create_product_from_card(item) for item in response["items"])
            return await asyncio.gather(*tasks)
        except Exception as e:
            # 处理可能的异常情况，例如网络错误或解析失败
            return []  # 或者根据需要进行其他合适的错误处理

    def create_data(self, search, page, sort_type):
        data = {
            # this seems to be random, but we'll add a prefix for mercari to track if they wanted to
            "userId": "MERCARI_BOT_{}".format(uuid4()),
            "pageSize": self.page_size,
            "pageToken": "v1:{}".format(page),
            # same thing as userId, courtesy of a prefix for mercari
            "searchSessionId": "MERCARI_BOT_{}".format(uuid4()),
            # this is hardcoded in their frontend currently, so leaving it
            "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
            "searchCondition": {
                "keyword": search.keyword,
                "excludeKeyword": getattr(search, "exclude_keyword", ""),
                "sort": sort_type,
                "order": "ORDER_DESC",
                "status": getattr(
                    search, "status", ["STATUS_ON_SALE", "STATUS_TRADING"]
                ),
                "categoryId": getattr(search, "category", []),
                "brandId": getattr(search, "brandId", []),
                "priceMin": getattr(search, "price_min", 0),
                "priceMax": getattr(search, "price_max", 0),
            },
            # I'm not certain what these are, but I believe it's what mercari queries against
            # this is the default in their site, so leaving it as these 2
            "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        }
        return data


class MercariItems(BaseSearch):
    def __init__(self):
        super().__init__("https://api.mercari.jp/items/get_items")
        self.has_next = True
        self.pager_id = ""

    async def search(
            self, search, iteration_count
    ) -> AsyncGenerator[SearchResultItem, None]:
        while self.has_next:
            async for item in self.fetch_products(search):
                yield item

    async def fetch_products(self, search) -> AsyncGenerator[SearchResultItem, None]:
        params = self.create_params(search)

        response = await self.get_response("GET", params=params)
        if not response:
            self.has_next = False  # 将 has_next 设置为 False 以停止进一步的迭代
            return  # 直接返回以结束函数执行

        items = response["data"]
        for item in items:
            searched_item = await self.create_product_from_card(item)
            yield searched_item

        self.has_next = response["meta"]["has_next"]
        if items:
            self.pager_id = items[-1]["pager_id"]

    def create_params(self, search):
        params = {
            "seller_id": search.keyword,
            "limit": 150,
            # "status": "on_sale,trading,sold_out",
            "status": getattr(search, "status", "on_sale"),
            "max_pager_id": self.pager_id,
        }
        return params
