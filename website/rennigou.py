import time
import jwt
import os
from .base.common_imports import *
from .base.scraper import BaseScrapy


class Rennigou(BaseScrapy):
    def __init__(self, client):
        super().__init__(
            base_url="https://rl.rennigou.jp/supplier/search/index",
            page_size=12,
            client=client,
        )
        self.has_next = True
        self.issuer = "FQwcwtrHtmdxQ0aCKlQoxNMy9glEr4Zd"
        self.key = "OYZJEYvhNbwYG3WOecDzw8Mq8SixjD23"

    async def get_response(self, search_term, page: int) -> Optional[str]:
        for attempt in range(BaseScrapy.MAX_RETRIES):
            try:
                response = await self.client.post(
                    self.base_url,
                    data=self.create_data(search_term, page),
                    headers=self.create_headers(),
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.error(f"请求的URL {e.response.url} 返回了404状态码，停止重试。")
                    return None
                logger.warning(
                    f"由于状态码 {e.response.status_code}，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)
            except httpx.TimeoutException:
                logger.warning(
                    f"请求超时，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)
            except httpx.RequestError as e:
                logger.warning(
                    f"网络错误：{e}，正在进行第 {attempt + 1}/{BaseScrapy.MAX_RETRIES} 次重试..."
                )
                await asyncio.sleep(BaseScrapy.RETRY_DELAY)

            except Exception as e:
                logger.error(f"发生未预期的异常：{e}")
                break  # 发生未知异常时终止循环
        else:
            logger.error(f"在尝试了 {BaseScrapy.MAX_RETRIES} 次后，仍未能成功获取响应。")

        return None

    async def search(
        self, search_term, iteration_count, user_max_pages
    ) -> AsyncGenerator[SearchResultItem, None]:
        current_page = 1

        # 限制并发页数
        concurrent_pages = search_term['max_concurrency']

        while True:
            tasks = []
            for _ in range(concurrent_pages):
                # 根据iteration_count和user_max_pages决定是否继续添加任务
                if (
                    iteration_count != 0 and current_page > user_max_pages
                ) or not self.has_next:
                    break
                tasks.append(self.fetch_products(search_term, current_page))
                current_page += 1

            if not tasks:  # 如果没有任务需要执行，则退出循环
                break

            current_page_contents = await asyncio.gather(*tasks, return_exceptions=True)

            for page_content in current_page_contents:
                if isinstance(page_content, (Exception, BaseException)):
                    continue  # 处理或记录异常

                if page_content is None or not self.has_next:
                    self.has_next = False
                    break  # 如果没有下一页，则停止抓取

                for product in page_content:
                    yield product

            if not self.has_next:
                break

        self.has_next = True  # 重置 has_next 以供下次搜索使用

    async def get_max_pages(self, search) -> int:
        return 0

    def create_jwt_token(self):
        current_time = time.time()
        if (
            not hasattr(self, "_jwt_token_expiry")
            or current_time >= self._jwt_token_expiry
        ):
            self._jwt_token_expiry = current_time + (30 * 24 * 60 * 60)  # 30天后过期
            payload = {
                "iss": self.issuer,
                "iat": current_time,
                "exp": self._jwt_token_expiry,
            }
            self._jwt_token = jwt.encode(payload, self.key, algorithm="HS256")
        return self._jwt_token

    def create_headers(self):
        headers = {
            "Authorization": f"Bearer {self.create_jwt_token()}",
            "uid": os.getenv("RENNIGOU_UID"),
            "token": os.getenv("RENNIGOU_TOKEN"),
        }

        return headers

    def to_json_exclude_specific_keys(self, search, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = []

        filtered_dict = {
            key: value
            for key, value in search["filter"].items()
            if key not in exclude_keys
        }

        filtered_dict["keyword"] = search["keyword"]
        return json.dumps(filtered_dict)

    def create_data(self, search, page):
        data = {
            "websiteType": search["websiteType"],
            "limit": 12,
            "page": page,
            "searchCriteria": self.to_json_exclude_specific_keys(search),
        }
        return data

    async def get_response_items(self, response):
        try:
            res = json.loads(response) if response else {}
        except json.JSONDecodeError:
            return []
        data = res.get("data", {})
        items_list = data.get("list", [])
        self.has_next = data.get("hasNext", False)  # 直接解析
        return items_list

    async def get_item_id(self, item):
        return item.get("Id")

    async def get_item_name(self, item):
        return item.get("Name")

    async def get_item_price(self, item):
        def parse_price(price_str):
            try:
                return int(price_str) if price_str else 0
            except ValueError:
                return 0

        if item.get("Source") == "surugaya":
            prices = item.get("CustomizeSiteOtherInfo")
            if prices:
                used_price = parse_price(prices.get("usedPriceYen", "0"))
                new_price = parse_price(prices.get("newPriceYen", "0"))
                price = min(used_price, new_price)
            else:
                price = 0
        else:
            price = item.get("Price", 0)

        return price

    async def get_item_image_url(self, item, id):
        return item.get("Thumbnail")

    async def get_item_product_url(self, item, id):
        return item.get("link")

    async def get_item_site(self, item):
        website = item.get("Source")
        return f"rennigou_{website}"

    async def get_item_status(self, item):
        if item.get("Source") == "surugaya":
            left_tags = item.get("LeftTags")
            if left_tags and len(left_tags) > 0 and left_tags[0].get("name") == "缺货":
                return 0
        return 1 if item.get("Status") == "on_sale" else 0

    async def create_search_params(self, search, page: int):
        pass
