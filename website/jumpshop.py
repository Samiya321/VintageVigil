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
        )

    async def create_search_params(self, search, page: int) -> dict:
        if "https" in search.keyword:
            # 从 URL 解析参数
            get_param = (
                lambda param, default="": self.get_param_value(search.keyword, param)
                or default
            )
            return {
                "q": get_param("q"),
                "page": page,
                "options[prefix]": get_param("options[prefix]", "last"),
            }
        else:
            # 使用默认值
            return {
                "page": page,
                "q": search.keyword,
                "options[prefix]": "last",
            }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        meta_element = selector.css('meta[property="og:title"]')
        content = meta_element.attrib["content"]
        return await self.extract_number_from_content(content, self.pageSize)

    async def get_response_items(self, response):
        selector = Selector(response)
        if selector is None:
            return []
        items = selector.css("div.card-wrapper")
        return items

    async def get_item_id(self, item):
        product_url = self.get_item_product_url(item, None)
        start_index = product_url.find("/products/") + len("/products/")
        end_index = product_url.find("?", start_index)
        return product_url[start_index:end_index]

    async def get_item_name(self, item):
        return item.css("span.card-information__text::text").get().strip()

    async def get_item_price(self, item):
        price_text = item.css("span.price-item--sale::text").get().strip()
        price = float(price_text[1:].replace(",", ""))
        return price

    async def get_item_image_url(self, item, id):
        image_url = item.css("img::attr(src)").get()
        image_url = "https:" + image_url
        # image_url = "https:" + image_url.split("?")[0]
        return image_url

    async def get_item_product_url(self, item, id):
        product_link = item.css("a.full-unstyled-link::attr(href)").get()
        return "https://jumpshop-online.com" + product_link

    async def get_item_site(self):
        return "jumpshop"
