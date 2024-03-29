from parsel import Selector

from .base.scraper import BaseScrapy
import re


class Fril(BaseScrapy):

    def __init__(self, http_client):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
        }
        super().__init__(
            base_url="http://fril.jp/s",
            page_size=36,
            headers=headers,
            http_client=http_client,
            method="GET",
        )

    async def create_search_params(self, search, page: int) -> dict:
        params = {
            "query": search["keyword"] if "https" not in search["keyword"] else "",
            "transaction": "selling",
            "sort": "created_at",
            "page": page,
            "order": "desc",
        }

        if "https" in search["keyword"]:
            for param in ["query", "transaction", "sort", "order"]:
                # 从 URL 提取参数值，如果未找到，则使用默认值
                param_value = self.get_param_value(search["keyword"], param)
                if param_value:
                    params[param] = param_value

        return params

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        hit_text = selector.css(
            "div.col-sm-12.col-xs-3.page-count.text-right::text"
        ).get()

        # 确保 hit_text 不是 None
        if hit_text:
            match = re.search(r"約(.+)件中", hit_text)
            if match:
                hit_number = match.group(1).replace(",", "")
                max_pages = await self.extract_number_from_content(
                    hit_number, self.page_size
                )
                return min(max_pages, 100) if max_pages else 100
        return 0

    async def get_response_items(self, response):
        selector = Selector(response)
        return selector.css(".item-box") if selector else []

    async def get_item_id(self, item: Selector):
        product_url = item.css(".item-box__image-wrapper a::attr(href)").get()
        if product_url:
            match = re.search("fril.jp/([0-9a-z]+)", product_url)
            if match:
                return match.group(1)
        return None

    async def get_item_name(self, item: Selector):
        return item.css(".item-box__item-name span::text").get()

    async def get_item_price(self, item: Selector):
        price_text = (
            item.css(".item-box__item-price").xpath("./span[last()]/text()").get()
        )
        return float(re.sub(r"[^\d]", "", price_text)) if price_text else 0

    async def get_item_image_url(self, item: Selector, id: str):
        # image_url = re.sub(r"\?.*$", "", image_url_with_query)
        return item.css(".item-box__image-wrapper a img::attr(data-original)").get()

    async def get_item_product_url(self, item: Selector, id: str):
        return item.css(".item-box__image-wrapper a::attr(href)").get()

    async def get_item_site(self, item):
        return "fril"

    async def get_item_status(self, item):
        return 0 if item.css(".item-box__soldout_ribbon") else 1
