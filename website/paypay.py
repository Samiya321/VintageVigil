from math import ceil

from .base.common_imports import *
from .base.scraper import BaseScrapy


class Paypay(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="https://paypayfleamarket.yahoo.co.jp/api/v1/search",
            page_size=100,
            client=client,
        )

    async def create_search_params(self, search, page: int) -> dict:
        return {
            "query": search.keyword,
            "results": self.pageSize,
            "imageShape": getattr(search, "imageShape", "square"),
            "sort": getattr(search, "sort", "ranking"),
            "order": getattr(search, "order", "ASC"),
            "webp": getattr(search, "webp", "false"),
            "module": getattr(search, "module", "catalog:hit:21"),
            "itemStatus": getattr(search, "itemStatus", "open"),
            "offset": (page - 1) * self.pageSize,
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        data = json.loads(re.search(r"{.*}", res.text, re.DOTALL).group())
        max_pages = ceil(data["totalResultsAvailable"] / self.pageSize)
        return max_pages

    async def get_response_items(self, response):
        data = json.loads(re.search(r"{.*}", response, re.DOTALL).group())
        if not data or "items" not in data:
            return []  # 当get_response返回None或无有效数据时，返回空列表

        items = data["items"]
        return items


    async def get_item_id(self, item):
        return item["itemid"]

    async def get_item_name(self, item):
        return item["title"]

    async def get_item_price(self, item):
        return item["price"]

    async def get_item_image_url(self, item, id):
        image_url = item["thumbnailImageUrl"]
        return image_url

    async def get_item_product_url(self, item, id):
        product_url = "https://paypayfleamarket.yahoo.co.jp/item/{}".format(id)
        return product_url

    async def get_item_site(self):
        return "paypay"
