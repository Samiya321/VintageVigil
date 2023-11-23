from parsel import Selector

from .base.common_imports import *
from .base.scraper import BaseScrapy


class Suruga(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="https://www.suruga-ya.jp/search", page_size=24, client=client
        )

    async def get_response(self, search, page: int):
        params = await self.create_search_params(search, page)

        final_url = f"{self.base_url}?{self.encode_params(params)}"

        max_retries = 5  # 定义最大重试次数
        retry_delay = 1  # 定义初始重试延迟（秒）

        for attempt in range(max_retries):
            try:
                response = await self.client.get(
                    final_url, headers=self.headers, timeout=20
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {e.response.url} after status code {e.response.status_code}"
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries}  due to network error: {e}"
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
        else:
            logger.error(f"Failed to get response after {max_retries} attempts")

        return None  # 如果重试失败，返回 None

    async def create_search_params(self, search, page: int) -> dict:
        if "https" in search.keyword:
            # 从 URL 解析参数
            get_param = (
                lambda param, default="": self.get_param_value(search.keyword, param)
                or default
            )
            return {
                "category": get_param("category"),
                "search_word": get_param("search_word"),
                "rankBy": get_param("rankBy", "modificationTime:descending"),
                "hendou": get_param("hendou"),
                "page": page,
                "adult_s": get_param("adult_s", 1),
                "inStock": get_param("inStock", "Off"),
            }
        else:
            # 使用默认值
            return {
                "category": "",
                "search_word": search.keyword,
                "rankBy": "modificationTime:descending",
                "page": page,
                "adult_s": 1,
                "inStock": "Off",
            }

    async def get_max_pages(self, search) -> int:
        res = await self.get_response(search, 1)
        selector = Selector(res)
        hit_element = selector.css("div.hit").get()
        hit_number = re.search(r"該当件数:(.+)件中", hit_element).group(1)
        return await self.extract_number_from_content(hit_number, self.pageSize)

    async def get_response_items(self, response):
        selector = Selector(response)
        if selector is None:
            return []
        items = selector.css("div.item:has(div.item_detail)")
        return items

    async def create_product_from_card(self, item) -> SearchResultItem:
        name = await self.get_item_name(item)

        id = await self.get_item_id(item)

        product_url = await self.get_item_product_url(id)

        image_url = await self.get_item_image_url(id)

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

    async def get_item_name(self, item):
        return item.css("p.title a::text").get()

    async def get_item_id(self, item):
        url = item.css("p.title a::attr(href)").get()
        item_id = re.search(r"(\d+)", url).group(1)
        return item_id

    async def get_item_image_url(self, item_id):
        # 加上random=64，避免tg服务器无法解析链接
        return "https://www.suruga-ya.jp/database/photo.php?shinaban={}&size=m&random=64".format(
            item_id
        )
        # return "https://www.suruga-ya.jp/database/pics_light/game/{}.jpg&random=64".format(id)

    async def get_item_product_url(self, item_id):
        return "https://www.suruga-ya.jp/product/detail/{}".format(item_id)

    async def get_item_price(self, item):
        """
        Extracts and returns the price from a given item element.
        Handles different scenarios like regular price, out-of-stock, and price_teika.

        Args:
        item (Selector): The selector object for the item from which the price is to be extracted.

        Returns:
        float: The extracted price as a float, or None if no price is found.
        """

        def extract_price(text):
            """
            Helper function to extract and convert price text to float.

            Args:
            text (str): The price text to be converted.

            Returns:
            float: The converted price.
            """
            replace_chars = str.maketrans("", "", "中古：税込定価：新品：￥,")
            try:
                price = float(text.translate(replace_chars).strip())
                return price
            except ValueError:
                return 0

        # Extract the main price or the out-of-stock price
        price = item.css("p.price::text").get()
        if price:
            price = price.strip()
            if price == "品切れ":
                price_elements = item.css(
                    "div.item_price div p.mgnB5.mgnT5 span.text-red.fontS15 strong::text"
                ).get()
                return extract_price(price_elements) if price_elements else 0
            else:
                return extract_price(price)

        # Extract the price_teika if main price is not available
        price_teika_elements = item.css("p.price_teika")
        if price_teika_elements:
            # 尝试从 <strong> 标签获取文本
            price_teika = price_teika_elements.css("strong::text").get()
            if price_teika is None:
                # 如果没有找到，回退到使用第一个元素的文本
                price_teika = price_teika_elements[0].css("::text").get()
                if price_teika is None:
                    price_teika = 0

            price_teika = extract_price(price_teika)

            return price_teika

        return 0

    async def get_item_site(self):
        return "suruga"
