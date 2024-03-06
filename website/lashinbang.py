from .base.common_imports import *
from .base.scraper import BaseScrapy


class Lashinbang(BaseScrapy):
    def __init__(self, http_client):
        headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
        }
        super().__init__(
            base_url="http://lashinbang-f-s.snva.jp",
            page_size=100,
            http_client=http_client,
            method="GET",
        )

    async def create_search_params(self, search, page: int) -> dict:
        return {
            "q": search["keyword"], # 搜索关键词
            "sort": getattr(search["filter"], "sort", "Number18%2CScore"), # 商品排序方式
            "limit": self.page_size, # 每页返回的商品数量
            "o": (page - 1) * self.page_size,  # 偏移值，用于翻页
            "s6o": 1, # TODO
            "pl": 1, # TODO
            "n6l": 1, # 只看在库有货的商品，如果为0则显示所有商品（包括品切的）
            "s1": 2, # 打开全年龄限制
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
