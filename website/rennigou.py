import time
from jose import jwt
import os
from datetime import datetime, timedelta
from .base.common_imports import *
from .base.scraper import BaseScrapy


class Rennigou(BaseScrapy):
    def __init__(self, http_client):
        super().__init__(
            base_url="https://rl.rennigou.jp/supplier/search/index",
            page_size=12,
            http_client=http_client,
            method="POST",
        )
        self.has_next = True
        self.issuer = "FQwcwtrHtmdxQ0aCKlQoxNMy9glEr4Zd"
        self.key = "OYZJEYvhNbwYG3WOecDzw8Mq8SixjD23"
        self.uid, self.token = "", ""

    async def async_init(self):
        self.uid, self.token = await self.login()
        self.create_headers()

    async def search(
        self, search_term, iteration_count, user_max_pages
    ) -> AsyncGenerator[SearchResultItem, None]:
        max_concurrency = search_term.get(
            "max_concurrency", 20
        )  # 从search_term获取最大并发数，默认为10
        semaphore = asyncio.Semaphore(max_concurrency)  # 使用信号量来限制并发数量

        async def fetch_page(page_number):
            async with semaphore:
                return await self.fetch_products(search_term, page_number)

        current_page = 1
        tasks = []

        # 当has_next为真且未达到iteration_count指定的页数限制时，继续创建任务
        while self.has_next and (
            iteration_count == 0 or current_page <= user_max_pages
        ):
            if iteration_count != 0 and current_page > user_max_pages:
                break  # 达到user_max_pages限制时停止创建新任务

            # 创建任务，直到达到并发限制或没有更多页面需要请求
            while (
                len(tasks) < max_concurrency
                and (iteration_count == 0 or current_page <= user_max_pages)
                and self.has_next
            ):
                tasks.append(fetch_page(current_page))
                current_page += 1

            # 使用asyncio.gather等待所有当前任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            tasks = []  # 重置任务列表以便下一批任务的创建

            # 处理结果
            for page_content in results:
                if page_content is None:
                    self.has_next = False
                    break
                for product in page_content:
                    yield product

            # 检查是否继续创建新任务
            if not self.has_next or (
                iteration_count != 0 and current_page > user_max_pages
            ):
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
        self.check_token_expiry()
        self.headers = {
            "Authorization": f"Bearer {self.create_jwt_token()}",
            "uid": self.uid,
            "token": self.token,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/json, text/plain, */*",
        }
        return True

    async def login(self):
        login_url = "https://rl.rennigou.jp/user/index/login"
        payload = {
            "type": 3,
            "mail": os.getenv("RENNIGOU_MAIL"),
            "pass": os.getenv("RENNIGOU_PASS"),
        }
        response = await self.http_client.post(login_url, data=payload)
        response_json = await response.json()
        await response.close()

        # 检查返回的代码是否成功
        if response_json.get("code") == 0:
            user_info = response_json.get("data", {}).get("userInfo", {})
            uid = str(user_info.get("user_id"))
            token = response_json.get("data", {}).get("token")

            # 设置token的有效期为3天
            self.token_expiry = datetime.now() + timedelta(days=3)

            return uid, token
        else:
            raise Exception("登录失败: " + response_json.get("msg", "未知错误"))

    # 在调用接口前检查token是否过期，如果过期则重新登录
    def check_token_expiry(self):
        if datetime.now() >= self.token_expiry:
            self.uid, self.token = self.login()

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
