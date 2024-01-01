from .base.scraper_mercari import BaseSearch
from .base.search_result_item import SearchResultItem
from typing import AsyncGenerator


class MercariItems(BaseSearch):
    def __init__(self, client):
        super().__init__("https://api.mercari.jp/items/get_items", client)
        self.has_next = True
        self.pager_id = ""

    async def search(
        self, search, iteration_count, user_max_pages
    ) -> AsyncGenerator[SearchResultItem, None]:
        self.has_next = True
        self.pager_id = ""
        while self.has_next:
            async for item in self.fetch_products(search):
                yield item

    async def fetch_products(self, search) -> AsyncGenerator[SearchResultItem, None]:
        params = self.create_params(search)
        response = await self.get_response("GET", params=params)

        if not response:
            self.has_next = False  # 将 has_next 设置为 False 以停止进一步的迭代
            return  # 当没有下一页时直接返回，以结束函数执行

        for item in response.get("data", []):
            searched_item = await self.create_product_from_card(item)
            yield searched_item

        self.has_next = response.get("meta", {}).get("has_next", False)
        if self.has_next:
            self.pager_id = response["data"][-1].get("pager_id", "")

    def create_params(self, search):
        params = {
            "seller_id": search["keyword"],
            "limit": 150,
            # "status": "on_sale,trading,sold_out",
            "status": getattr(search["filter"], "status", "on_sale, trading"),
        }
        # 仅当 self.pager_id 非空时才添加 max_pager_id 参数
        if self.pager_id:
            params["max_pager_id"] = self.pager_id

        return params

    async def get_item_site(self, item):
        return "mercari_user"

    async def get_item_status(self, item):
        if item.get("status") == "on_sale":
            status = 1
        else:
            status = 0
        return status
