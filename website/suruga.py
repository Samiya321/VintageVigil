from parsel import Selector

from .base.common_imports import *
from .base.scraper import BaseScrapy


class Suruga(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="https://www.suruga-ya.jp/search", page_size=24, client=client
        )

    async def create_request_url(self, params):
        final_url = f"{self.base_url}?{self.encode_params(params)}"
        return final_url, None

    async def create_search_params(self, search, page: int) -> dict:
        # 判断搜索关键字是否为URL
        is_url = "https" in search.keyword
        get_param = (
            (
                lambda param, default="": self.get_param_value(search.keyword, param)
                or default
            )
            if is_url
            else lambda param, default="": default
        )

        return {
            "category": get_param("category") if is_url else "",
            "search_word": get_param("search_word") if is_url else search.keyword,
            "rankBy": get_param("rankBy", "modificationTime:descending"),
            "hendou": get_param("hendou"),
            "page": page,
            "adult_s": get_param("adult_s", 1),
            "inStock": get_param("inStock", "Off"),
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        hit_element = selector.css("div.hit").get()
        hit_number = re.search(r"該当件数:(.+)件中", hit_element).group(1)
        return await self.extract_number_from_content(hit_number, self.page_size)

    async def get_response_items(self, response):
        selector = Selector(response)
        return selector.css("div.item:has(div.item_detail)") if selector else []

    async def get_item_name(self, item):
        return item.css("p.title a::text").get()

    async def get_item_id(self, item):
        url = item.css("p.title a::attr(href)").get()
        return re.search(r"(\d+)", url).group(1) if url else None

    async def get_item_image_url(self, item, id):
        return f"https://www.suruga-ya.jp/database/photo.php?shinaban={id}&size=m"
        # return "https://www.suruga-ya.jp/database/pics_light/game/{}.jpg".format(id)

    async def get_item_product_url(self, item, id):
        return f"https://www.suruga-ya.jp/product/detail/{id}"

    async def get_item_price(self, item):
        """
        Extracts and returns the minimum available price from a given item element.
        Handles different scenarios like regular price, out-of-stock, and price_teika.

        Args:
        item (Selector): The selector object for the item from which the price is to be extracted.

        Returns:
        float: The lowest extracted price as a float, or 0 if no valid price is found.
        """

        def extract_price(text):
            """
            Helper function to extract and convert price text to float.

            Args:
            text (str): The price text to be converted.

            Returns:
            float: The converted price or 0 if conversion fails.
            """
            replace_chars = str.maketrans("", "", "中古：税込定価：新品：￥,")
            try:
                return float(text.translate(replace_chars).strip())
            except ValueError:
                return 0

        prices = []

        # Extract official store price, if available
        official_price = item.css("p.price::text").get()
        if official_price and official_price.strip() != "品切れ":
            prices.append(extract_price(official_price))

        # Extract third-party store price, if available
        third_party_price_text = item.css(
            "div.item_price div p.mgnB5.mgnT5 span.text-red.fontS15 strong::text"
        ).get()
        if third_party_price_text:
            prices.append(extract_price(third_party_price_text))

        # Extract highlighted price_teika, if available
        highlighted_price_text = item.css("p.price_teika strong::text").get()
        if highlighted_price_text:
            prices.append(extract_price(highlighted_price_text))

        # Return the minimum valid price found, or 0 if none
        return min(prices, default=0)

    async def get_item_site(self):
        return "suruga"
