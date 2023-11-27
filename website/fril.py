from parsel import Selector

from .base.scraper import BaseScrapy
import re


class Fril(BaseScrapy):
    def __init__(self):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
        }
        super().__init__(base_url="https://fril.jp/s", page_size=36, headers=headers)

    async def create_search_params(self, search, page: int) -> dict:
        if "https" in search.keyword:
            # 从 URL 解析参数
            get_param = (
                lambda param, default="": self.get_param_value(search.keyword, param)
                or default
            )
            return {
                "query": get_param("query"),
                "transaction": get_param("transaction", "selling"),
                "sort": get_param("sort", "created_at"),
                "page": page,
                "order": get_param("order", "desc"),
            }
        else:
            return {
                "query": search.keyword,
                "transaction": "selling",
                "sort": "created_at",
                "page": page,
                "order": "desc",
            }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        hit_text = selector.css(
            "div.col-sm-12.col-xs-3.page-count.text-right::text"
        ).get()
        hit_number = re.search(r"約(.+)件中", hit_text).group(1)
        hit_number = hit_number.replace(",", "")
        return await self.extract_number_from_content(hit_number, self.pageSize)

    async def get_response_items(self, response):
        selector = Selector(response)
        if selector is None:
            return []
        items = selector.css(".item-box")
        return items

    async def get_item_id(self, item: Selector):
        product_url = self.get_item_product_url(item, None)
        return re.search("fril.jp/([0-9a-z]+)", product_url).group(1)

    async def get_item_name(self, item: Selector):
        return item.css(".item-box__item-name span::text").get()

    async def get_item_price(self, item: Selector):
        price_text = (
            item.css(".item-box__item-price").xpath("./span[last()]/text()").get()
        )
        price = float(re.sub(r"[^\d]", "", price_text))
        return price

    async def get_item_image_url(self, item: Selector, id: str):
        image_url_with_query = item.css(
            ".item-box__image-wrapper a img::attr(data-original)"
        ).get()
        image_url = re.sub(r"\?.*$", "", image_url_with_query)
        # 加上random=64，避免tg服务器无法解析链接
        # image_url = image_url + "?random=64"
        return image_url

    async def get_item_product_url(self, item: Selector, id: str):
        return item.css(".item-box__image-wrapper a::attr(href)").get()

    async def get_item_site(self):
        return "fril"
