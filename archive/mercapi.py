from mercapi import Mercapi

from .base.search_result_item import SearchResultItem


class MercariMercapi:
    def __init__(self, client):
        self._mercapi = Mercapi()
        self.client = client

    async def search(self, kw):
        results = await self._mercapi.search(query=kw)
        page_count = 0  # 初始化页面计数器

        while page_count < 20:  # 限制为前20页
            for item in results.items:
                yield SearchResultItem(
                    id=item.id_,
                    name=item.name,
                    price=item.price,
                    image_url=item.thumbnails[0] if item.thumbnails else "",
                    product_url=f"https://jp.mercari.com/item/{item.id_}",
                    site = "mercapi",
                    status = self.get_item_status(item)
                )

            if results.meta.next_page_token:
                results = await results.next_page()
                page_count += 1  # 增加页面计数
            else:
                break  # 如果没有下一页，则中断循环

    def get_item_status(self, item):
        if item.status == "ITEM_STATUS_ON_SALE":
            status = 1
        else:
            status = 0
        return status
