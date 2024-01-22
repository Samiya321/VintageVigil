from .base.common_imports import *
from .base.scraper import BaseScrapy


class Lashinbang(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="http://lashinbang-f-s.snva.jp",
            page_size=100,
            client=client,
            method="GET",
        )

    async def create_search_params(self, search, page: int) -> dict:
        return {
            "q": search["keyword"],
            "s6o": 1,
            "pl": 1,
            "sort": getattr(search["filter"], "sort", "Number18%2CScore"),
            "limit": self.page_size,
            "o": (page - 1) * self.page_size,  # Offset calculation for pagination
            "n6l": 1,
            "callback": "callback",
            "controller": "lashinbang_front",
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        match = re.search(r"{.*}", res, re.DOTALL) if res else None
        json_data = match.group() if match else "{}"
        data = json.loads(json_data)
        return (
            data.get("kotohaco", {})
            .get("result", {})
            .get("info", {})
            .get("last_page", 0)
        )

    async def get_response_items(self, response):
        match = re.search(r"{.*}", response, re.DOTALL)
        json_data = match.group() if match else "{}"
        data = json.loads(json_data)
        return data.get("kotohaco", {}).get("result", {}).get("items", [])

    async def get_item_id(self, item):
        return item.get("itemid")

    async def get_item_name(self, item):
        return item.get("title")

    async def get_item_price(self, item):
        return item.get("price")

    async def get_item_image_url(self, item, id):
        image = item.get("image")
        if image == "https://img.lashinbang.com/":
            image = image + item.get("narrow14")
        return image

    async def get_item_product_url(self, item, id):
        return item.get("url")

    async def get_item_site(self, item):
        return "lashinbang"

    async def get_item_status(self, item):
        return item.get("number6")
