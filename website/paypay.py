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
        # 使用字典推导式和getattr简化参数的创建
        params = {
            "query": search.keyword,
            "results": self.page_size,
            "offset": (page - 1) * self.page_size,
        }
        for param in ["imageShape", "sort", "order", "webp", "module", "itemStatus"]:
            params[param] = getattr(search, param, params.get(param, "default_value"))

        return params

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        data = json.loads(re.search(r"{.*}", res.text, re.DOTALL).group())
        return ceil(data.get("totalResultsAvailable", 0) / self.page_size)

    async def get_response_items(self, response):
        data = json.loads(re.search(r"{.*}", response, re.DOTALL).group())
        return data.get("items", [])

    async def get_item_id(self, item):
        return item.get("itemid")

    async def get_item_name(self, item):
        return item.get("title")

    async def get_item_price(self, item):
        return item.get("price")

    async def get_item_image_url(self, item, id):
        return item.get("thumbnailImageUrl")

    async def get_item_product_url(self, item, id):
        return f"https://paypayfleamarket.yahoo.co.jp/item/{id}"

    async def get_item_site(self):
        return "paypay"
