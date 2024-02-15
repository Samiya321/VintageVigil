from parsel import Selector

from .base.common_imports import *
from .base.scraper import BaseScrapy


class Suruga(BaseScrapy):

    def __init__(self, http_client):
        headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        }
        super().__init__(
            base_url="http://www.suruga-ya.jp/search",
            page_size=24,
            headers= headers,
            http_client=http_client,
            method="GET",
        )

    async def create_request_url(self, params):
        final_url = f"{self.base_url}?{self.encode_params(params)}"
        return final_url, None

    async def create_search_params(self, search, page: int) -> dict:
        # 判断搜索关键字是否为URL
        is_url = "https" in search["keyword"]
        get_param = (
            (
                lambda param, default="": self.get_param_value(search["keyword"], param)
                or default
            )
            if is_url
            else lambda param, default="": default
        )

        return {
            "category": get_param("category") if is_url else "",  # カテゴリー
            "search_word": get_param("search_word") if is_url else search["keyword"],
            "rankBy": get_param("rankBy", "modificationTime:descending")
            if is_url
            else "modificationTime:descending",  # 並べ替え
            "hendou": get_param("hendou") if is_url else "",  # 変動
            "page": page,
            "adult_s": get_param("adult_s", 1) if is_url else 1,  # セーフサーチ
            "inStock": get_param("inStock", "Off") if is_url else "Off",  # 品切れ
        }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        hit_text = selector.css("div.hit").get()

        # 使用正则表达式直接从 hit_text 中提取数字
        match = re.search(r"該当件数:(.+)件中", hit_text) if hit_text else None
        hit_number = match.group(1) if match else "0"

        # 将字符串转换为数字，计算最大页数
        max_pages = await self.extract_number_from_content(hit_number, self.page_size)
        return max_pages or 0

    async def get_response_items(self, response):
        selector = Selector(response)
        return selector.css("div.item:has(div.item_detail)") if selector else []

    async def get_item_name(self, item):
        return item.css("p.title a::text").get()

    async def get_item_id(self, item):
        product_link = item.css("p.title a::attr(href)").get()
        match = re.search(r"product/(detail|other)/(\w+)", product_link)
        return match.group(2) if match else None

    async def get_item_image_url(self, item, id):
        return f"https://www.suruga-ya.jp/database/photo.php?shinaban={id}&size=m"
        # return item.css(".photo_box a img::attr(src)").get()
        # return f"https://www.suruga-ya.jp/database/pics_light/game/{id}.jpg"

    async def get_item_product_url(self, item, id):
        return f"https://www.suruga-ya.jp/product/other/{id}"

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

        prices = [
            extract_price(text)
            for text in [
                item.css(
                    "div.item_price div p.mgnB5.mgnT5 span.text-red.fontS15 strong::text"
                ).get(),  # 分店价格
                item.css("p.price_teika strong::text").get(),  # 本店价格
            ]
            if text
        ]

        return min(prices, default=0) if prices else 0

    async def get_item_site(self, item):
        return "suruga"

    async def get_item_status(self, item):
        """
        根据商品的可用性和定价信息确定商品状态。

        返回值：
            0: 本店及第三方店铺均售空
            1: 本店及第三方店铺均在售
            2: 本店在售 第三方店铺售空
            3: 本店售空 第三方店铺在售
            None: 在所有其他情况下。
        """

        official_status = item.css("p.price::text").get()  # 本店是否品切

        other_status = item.css(
            "div.mgnT10.highlight-box strong::text"
        ).get()  # 第三方店铺是否有货

        # 判断商品状态
        if official_status and not other_status:
            return 0  # 本店及第三方店铺均售空
        elif not official_status and other_status:
            return 1  # 本店及第三方店铺均在售
        elif not official_status and not other_status:
            return 2  # 本店在售 第三方店铺售空
        elif official_status and other_status:
            return 3  # 本店售空 第三方店铺在售
        else:
            return None  # 其他情况
