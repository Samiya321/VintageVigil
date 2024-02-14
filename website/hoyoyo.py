from .base.common_imports import *
from .base.scraper import BaseScrapy


class HoYoYo(BaseScrapy):
    def __init__(self, http_client):
        headers = {
            "x-requested-with": "XMLHttpRequest",
            "Host": "cn.hoyoyo.com",
        }
        super().__init__(
            base_url="https://cn.hoyoyo.com/suruga~search.html",
            page_size=24,
            http_client=http_client,
            method="GET",
            headers=headers,
        )

    async def create_search_params(self, search, page: int) -> dict:
        return {
            "keyword": search["keyword"],
            "page": page,
        }

    async def get_max_pages(self, search) -> int:
        response = await self.get_response(search, 1)
        data = json.loads(response) if response else {}
        return data.get("meta", {}).get("pager", {}).get("total_page", 0)

    async def get_response_items(self, response):
        data = json.loads(response) if response else {}
        return data.get("goods", [])

    async def get_item_id(self, item):
        return item.get("id")

    async def get_item_name(self, item):
        return item.get("name")

    async def get_item_price(self, item):
        return item.get("price")

    async def get_item_image_url(self, item, id):
        return item.get("image")

    async def get_item_product_url(self, item, id):
        return item.get("origin_url")

    async def get_item_site(self, item):
        return "hoyoyo"

    async def get_item_status(self, item):
        return 1 if item.get("sale_out") == "0" else 0
