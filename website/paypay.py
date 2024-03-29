from math import ceil

from .base.common_imports import *
from .base.scraper import BaseScrapy


class Paypay(BaseScrapy):

    def __init__(self, http_client):
        super().__init__(
            base_url="http://paypayfleamarket.yahoo.co.jp/api/v1/search",
            page_size=100,
            http_client=http_client,
            method="GET",
        )

    async def create_search_params(self, search, page: int) -> dict:
        return {
            "query": search["keyword"],
            "results": self.page_size,
            "offset": (page - 1) * self.page_size,
            "imageShape": getattr(search["filter"], "imageShape", "square"),
            "sort": getattr(search["filter"], "sort", "ranking"),
            "order": getattr(search["filter"], "order", "DESC"),
            "webp": getattr(search["filter"], "webp", "false"),
            "module": getattr(search["filter"], "module", "catalog:hit:21"),
            "itemStatus": getattr(search["filter"], "itemStatus", "open"),
        }

    async def get_max_pages(self, search) -> int:
        response = await self.get_response(search, 1)
        data = json.loads(response) if response else {}
        return ceil(data.get("totalResultsAvailable", 0) / self.page_size)

    async def get_response_items(self, response):
        data = json.loads(response) if response else {}
        return data.get("items", [])

    async def get_item_id(self, item):
        return item.get("id")

    async def get_item_name(self, item):
        return item.get("title")

    async def get_item_price(self, item):
        return item.get("price")

    async def get_item_image_url(self, item, id):
        return item.get("thumbnailImageUrl")

    async def get_item_product_url(self, item, id):
        return f"https://paypayfleamarket.yahoo.co.jp/item/{id}"

    async def get_item_site(self, item):
        return "paypay"

    async def get_item_status(self, item):
        return 1 if item.get("itemStatus") == "OPEN" else 0
