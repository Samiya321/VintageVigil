from uuid import uuid4

import ecdsa
from mercapi.util.jwt import generate_dpop

from .common_imports import *


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
    def __init__(self, root_url, client, page_size=120):
        self.page_size = page_size
        self.root_url = root_url
        self.client = client

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
                # image_url = "https://static.mercdn.net/item/detail/orig/photos/{}_1.jpg".format(id)
                image_url = "https://static.mercdn.net/c!/w=360,f=webp/item/detail/orig/photos/{}_1.jpg".format(
                    id
                )
            else:
                # image_url = "https://static.mercdn.net/thumb/photos/{}_1.jpg".format(id)

                image_url = item["thumbnails"][0]

        else:
            image_url = item["thumbnails"][0]

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
    