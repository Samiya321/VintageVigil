from parsel import Selector

from .base.scraper import BaseScrapy


class JumpShop(BaseScrapy):
    def __init__(self, client):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76",
        }
        super().__init__(
            base_url="https://jumpshop-online.com/search",
            page_size=20,
            headers=headers,
            client=client,
            method="GET",
        )

    async def create_search_params(self, search, page: int) -> dict:
        is_url_search = "https" in search["keyword"]
        get_param = (
            (
                lambda param, default="": self.get_param_value(search["keyword"], param)
                or default
            )
            if is_url_search
            else lambda param, default="": default
        )

        return {
            "q": get_param("q") if is_url_search else search["keyword"],
            "page": page,
            "options[prefix]": "last",
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        content = selector.css('meta[property="og:title"]').attrib.get("content", "")

        max_pages = await self.extract_number_from_content(content, self.page_size)
        return max_pages or 0

    async def get_response_items(self, response):
        selector = Selector(response)
        return selector.css("div.card-wrapper") if selector else []

    async def get_item_id(self, item):
        product_url = item.css("a.full-unstyled-link::attr(href)").get()
        return product_url.split("/products/")[1].split("?")[0] if product_url else None

    async def get_item_name(self, item):
        return item.css("span.card-information__text::text").get().strip()

    async def get_item_price(self, item):
        price_text = item.css("span.price-item--sale::text").get().strip()
        return float(price_text[1:].replace(",", "")) if price_text else 0

    async def get_item_image_url(self, item, id):
        image_url = item.css("img::attr(src)").get()
        return f"https:{image_url}" if image_url else None

    async def get_item_product_url(self, item, id):
        product_link = item.css("a.full-unstyled-link::attr(href)").get()
        return f"https://jumpshop-online.com{product_link}" if product_link else None

    async def get_item_site(self, item):
        return "jumpshop"

    async def get_item_status(self, item):
        sold_out = item.css("div.price.price--sold-out")
        return 0 if sold_out else 1
