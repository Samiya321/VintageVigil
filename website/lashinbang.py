from .base.common_imports import *
from .base.scraper import BaseScrapy


class Lashinbang(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="https://lashinbang-f-s.snva.jp", page_size=24, client=client
        )

    async def create_search_params(self, search, page: int) -> dict:
        limit = 100
        return {
            "q": search.keyword,
            "s6o": 1,
            "pl": 1,
            "sort": getattr(search, "sort", "Number18%2CScore"),
            "limit": limit,
            "o": (page - 1) * limit,  # 等同于page
            "n6l": 1,
            "callback": "callback",
            "controller": "lashinbang_front",
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        data = json.loads(re.search(r"{.*}", res, re.DOTALL).group())
        max_pages = data["kotohaco"]["result"]["info"]["last_page"]
        return max_pages

    async def get_response_items(self, response):
        data = json.loads(re.search(r"{.*}", response, re.DOTALL).group())
        if (
            not data
            or "kotohaco" not in data
            or "result" not in data["kotohaco"]
            or "items" not in data["kotohaco"]["result"]
        ):
            return []  # 如果数据结构不完整或不存在，则返回空列表

        items = data["kotohaco"]["result"]["items"]
        return items

    async def create_product_from_card(self, item) -> SearchResultItem:
        name = await self.get_item_name(item)

        product_url = await self.get_item_product_url(item)

        id = await self.get_item_id(item)

        image_url = await self.get_item_image_url(item)

        price = await self.get_item_price(item)

        site = await self.get_item_site()

        search_result_item = SearchResultItem(
            name=name,
            price=price,
            image_url=image_url,
            product_url=product_url,
            id=id,
            site=site,
        )
        return search_result_item

    async def get_item_id(self, item):
        return item["itemid"]

    async def get_item_name(self, item):
        return item["title"]

    async def get_item_price(self, item):
        return item["price"]

    async def get_item_image_url(self, item):
        # 加上random=64，避免tg服务器无法解析链接
        image_url = item["image"] + "?random=64"
        return image_url

    async def get_item_product_url(self, item):
        return item["url"]

    async def get_item_site(self):
        return "lashinbang"
