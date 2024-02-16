from abc import ABC, abstractmethod
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


class BaseSearch(ABC):

    def __init__(self, root_url, http_client, page_size=120):
        self.page_size = page_size
        self.root_url = root_url
        self.http_client = http_client

    async def async_init(self):
        pass

    async def search(self, **kwargs):
        pass  # 由子类实现

    async def fetch_products(self, **kwargs):
        pass  # 由子类实现

    async def get_response(self, method, data=None, params=None):
        headers = self.create_headers(method.upper())
        try:
            if method.lower() == "post":
                response = await self.http_client.post(
                    self.root_url, data=data, headers=headers
                )
            else:
                response = await self.http_client.get(
                    self.root_url, params=params, headers=headers
                )
            response.raise_for_status()
            # res_headers = response._response.headers.get("Cf-Cache-Status")
            # if res_headers != "DYNAMIC":
            #     pass
            await response.close()

            return await response.json()
        except Exception as e:
            logger.error(f"遇到错误：{e}")

    def create_headers(self, method):
        # ... 实现创建请求头的逻辑
        headers = {
            "DPoP": self.create_headers_dpop(method),
            "X-Platform": "web",  # mercari requires this header
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "deflate, gzip",
            "Content-Type": "application/json; charset=utf-8",
            # courtesy header since they're blocking python-requests (returns 0 results)
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
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

        site = await self.get_item_site(item = item)

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

    async def get_item_id(self, item):
        return item["id"]

    async def get_item_name(self, item):
        return item["name"]

    async def get_item_price(self, item):
        return item["price"]

    async def get_item_product_url(self, item, id):
        if id[0] == "m" and id[1:].isdigit():
            product_url = "https://jp.mercari.com/item/{}".format(id)
        else:
            product_url = "https://mercari-shops.com/products/{}".format(id)
        return product_url

    async def get_item_image_url(self, item, id):
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
        return image_url

    @abstractmethod
    async def get_item_site(self, item) -> str:
        pass

    @abstractmethod
    async def get_item_status(self, item) -> int:
        pass
