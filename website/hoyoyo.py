from .base.common_imports import *
from .base.scraper import BaseScrapy


class HoYoYo(BaseScrapy):
    def __init__(self, http_client):
        headers = {
            "x-requested-with": "XMLHttpRequest",
            "Host": "cn.hoyoyo.com",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
        }
        super().__init__(
            base_url="http://cn.hoyoyo.com/suruga~search.html",
            page_size=24,
            http_client=http_client,
            method="GET",
            headers=headers,
        )

    async def create_request_url(self, params):
        return params,None

    async def create_search_params(self, search, page: int) -> dict:
        search_url = search["keyword"]
        return f"{search_url}&page={page}"

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
