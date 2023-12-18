import sqlite3
from typing import Tuple, Optional

from loguru import logger

from ..utils import extract_keyword_from_url

class ProductDatabase:
    # SQL 语句集中管理
    SQL_STATEMENTS = {
        "create_website_keywords_table": """
            -- 创建一个用于存储网站关键词的表
            -- 如果表已存在，则此操作不会有任何效果
            CREATE TABLE IF NOT EXISTS website_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 主键，自动递增
                website TEXT NOT NULL,                 -- 网站名
                keyword TEXT NOT NULL,                 -- 关键词
                product_count_1 INTEGER DEFAULT 0,     -- 统计 status 为 1, 2, 3 的商品数量
                product_count_2 INTEGER DEFAULT 0,     -- 统计 status 为 0 的商品数量
                UNIQUE(website, keyword)               -- 确保每个网站和关键词的组合是唯一的
            );
        """,
        "create_products_table": """
            -- 创建一个用于存储产品信息的表
            -- 如果表已存在，则此操作不会有任何效果
            CREATE TABLE IF NOT EXISTS products (
                id TEXT NOT NULL,                      -- 产品 ID
                keyword_id INTEGER NOT NULL,           -- 关联的关键词 ID
                name TEXT,                             -- 产品名
                price REAL NOT NULL,                   -- 价格
                image_url TEXT,                        -- 图片 URL
                product_url TEXT,                      -- 产品 URL
                status INTEGER,                        -- 产品状态
                PRIMARY KEY (id, keyword_id),          -- 将产品 ID 和关键词 ID 一起作为主键
                FOREIGN KEY (keyword_id) REFERENCES website_keywords (id) -- 外键关联到 website_keywords 表
            );
        """,
        "upsert_product": """
            -- 插入或更新产品信息
            -- 如果具有相同的产品 ID 和关键词 ID 的记录已存在，则更新该记录
            INSERT INTO products (id, keyword_id, price, name, image_url, product_url, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, keyword_id) DO UPDATE SET
            price = excluded.price,
            name = excluded.name,
            image_url = excluded.image_url,
            product_url = excluded.product_url,
            status = excluded.status;
        """,
        "insert_or_ignore_keyword": """
            -- 插入新的网站和关键词对
            -- 如果相同的网站和关键词对已存在，则忽略此插入
            INSERT OR IGNORE INTO website_keywords (website, keyword) VALUES (?, ?);
        """,
        "select_keyword_id": """
            -- 根据网站名和关键词选择关键词 ID
            SELECT id FROM website_keywords WHERE website = ? AND keyword = ?;
        """,
        "update_product_count": """
            -- 更新特定关键词 ID 的产品计数
            UPDATE website_keywords 
            SET product_count_1 = (SELECT COUNT(*) FROM products WHERE keyword_id = ? AND status IN (1, 2, 3)),
                product_count_2 = (SELECT COUNT(*) FROM products WHERE keyword_id = ? AND status = 0)
            WHERE id = ?;
        """,
        "count_products_by_keyword": """
            -- 计算特定关键词的产品总数
            SELECT COUNT(*) FROM products WHERE keyword_id = ?;
        """,
        "bulk_fetch_prices": """
            -- 批量获取一系列产品的价格
            -- 使用参数替换来构建查询的 IN 子句
            SELECT id, price FROM products WHERE (id, keyword_id) IN ({});
        """,
    }

    def __init__(self, db_name: str):
        """
        初始化 ProductDatabase 实例。

        :param db_name: 数据库的文件名。
        """
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.setup_database()

    def setup_database(self):
        """创建数据库表格，如果它们不存在的话。"""
        self._safe_execute("create_website_keywords_table")
        self._safe_execute("create_products_table")

    def _safe_execute(
        self, query_key: str, params: Tuple = (), fetch_one=False, fetch_all=False
    ):
        """
        安全地执行数据库查询，并处理任何数据库异常。

        :param query_key: SQL_STATEMENTS 字典中的键，用于指定要执行的 SQL 语句。
        :param params: 传递给 SQL 语句的参数。
        :param fetch_one: 如果为 True，则只返回查询的第一行。
        :param fetch_all: 如果为 True，则返回查询的所有行。
        :return: 根据 fetch_one 和 fetch_all 返回相应的查询结果，如果出现异常，则返回 None。
        """
        query = self.SQL_STATEMENTS[query_key]
        try:
            cursor = self.conn.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error: {e}")
            return None

    def insert_or_ignore_keyword(self, website: str, keyword: str):
        """
        插入一个新的 website 和 keyword 对，如果它们已存在，则忽略此操作。

        :param website: 网站名。
        :param keyword: 关键词。
        """
        self._safe_execute("insert_or_ignore_keyword", (website, keyword))

    def get_keyword_id(self, website: str, keyword: str) -> Optional[int]:
        """
        根据给定的网站名和关键词获取关键词 ID。

        :param website: 网站名。
        :param keyword: 关键词。
        :return: 对应的关键词 ID，如果未找到则返回 None。
        """
        result = self._safe_execute(
            "select_keyword_id", (website, keyword), fetch_one=True
        )
        return result[0] if isinstance(result, tuple) and result else 0

    def update_product_count(self, keyword_id):
        """
        更新特定关键词 ID 的产品数量。

        :param keyword_id: 关键词 ID。
        """
        self._safe_execute("update_product_count", (keyword_id, keyword_id, keyword_id))


    def upsert_products(
        self, items, keyword: str, website: str, push_price_changes: bool
    ):
        """
        插入或更新产品信息。

        :param items: 包含产品信息的列表。
        :param keyword: 关联的关键词。
        :param website: 关联的网站。
        :param push_price_changes: 是否推送价格变化的商品。
        :yield: 处理后的每个产品信息。
        """
        keyword = extract_keyword_from_url(keyword)
        logger.info(f"{website}: {keyword}   搜索商品数量: {len(items)}")

        self.insert_or_ignore_keyword(website, keyword)
        keyword_id = self.get_keyword_id(website, keyword)

        existing_prices_statuses = self._bulk_fetch_prices_statuses(items, keyword_id)
        to_insert_or_update = []

        new_num = 0
        price_changed_num = 0
        restocked_num = 0

        for item in items:
            price_change = self.process_item(item, existing_prices_statuses)
            new_num, price_changed_num, restocked_num = self.update_counts(
                price_change,
                new_num,
                price_changed_num,
                restocked_num,
            )
            item.price_change = price_change

            valid_price_changes = {3, 4}
            pre_price = existing_prices_statuses.get(item.id, {}).get("price")
            if price_change in valid_price_changes:
                item.pre_price = pre_price

            if self.should_yield_item(price_change, push_price_changes):
                yield item

            to_insert_or_update.append(self.prepare_data_for_insert(item, keyword_id))

        self.execute_bulk_upsert(to_insert_or_update)
        self.update_product_count(keyword_id)
        if (new_num + price_changed_num + restocked_num) != 0:
            logger.info(
                f"Database Updated 价格变动:{price_changed_num} 新品：{new_num} 补货：{restocked_num}"
            )

    def process_item(self, item, existing_prices_statuses):
        """
        处理单个商品。

        :param item: 商品信息。
        :param existing_prices_statuses: 现有的价格和状态信息。
        :return: 价格变动类型。
        """
        existing = existing_prices_statuses.get(item.id, {})
        existing_price = existing.get("price")
        existing_status = existing.get("status")

        if existing_price is None or existing_status is None:  # 新品
            return 1
        if item.status == 0:  # 已售罄
            return 0
        if item.status == existing_status or existing_status == 1:
            if item.price > existing_price:  # 价格上涨
                return 3
            elif item.price < existing_price:  # 价格下跌
                return 4
            return 0  # 价格不变
        return 2  # 补货

    def update_counts(
        self,
        price_change,
        new_num,
        price_changed_num,
        restocked_num,
    ):
        """
        更新和记录商品计数。

        :param price_change: 价格变动类型。
        :param new_num: 新品计数。
        :param price_changed_num: 价格变动计数。
        :param restocked_num: 补货计数。
        :param item: 商品信息。
        :param website: 关联网站。
        :param keyword: 关联关键词。
        :return: 更新后的计数。
        """
        if price_change == 1:  # 新品
            new_num += 1
        elif price_change in [3, 4]:  # 价格变动
            price_changed_num += 1
        elif price_change == 2:  # 补货
            restocked_num += 1

        return new_num, price_changed_num, restocked_num

    def should_yield_item(self, price_change, push_price_changes):
        """
        决定是否yield商品。

        :param price_change: 价格变动类型。
        :param push_price_changes: 是否推送价格变化的商品。
        :return: 是否yield商品。
        """
        return (push_price_changes and price_change != 0) or (0 < price_change < 3)

    def prepare_data_for_insert(self, item, keyword_id):
        """
        准备用于插入的数据。

        :param item: 商品信息。
        :param keyword_id: 关键词ID。
        :return: 准备插入的数据。
        """
        return (
            item.id,
            keyword_id,
            item.price,
            item.name,
            item.image_url,
            item.product_url,
            item.status,
        )

    def execute_bulk_upsert(self, to_insert_or_update):
        """
        执行批量插入或更新。

        :param to_insert_or_update: 待插入或更新的数据列表。
        """
        if to_insert_or_update:
            with self.conn:
                self.conn.executemany(
                    self.SQL_STATEMENTS["upsert_product"], to_insert_or_update
                )

    def _bulk_fetch_prices_statuses(self, items, keyword_id) -> dict:
        """
        批量获取产品的当前价格和状态。

        :param items: 包含产品信息的字典列表。
        :param keyword_id: 关联的关键词 ID。
        :return: 一个字典，包含产品 ID 和对应的价格及状态。
        """

        prices_statuses = {}

        # 创建临时表
        self.conn.execute(
            "CREATE TEMPORARY TABLE temp_ids (id TEXT, keyword_id INTEGER)"
        )

        # 插入数据到临时表
        self.conn.executemany(
            "INSERT INTO temp_ids (id, keyword_id) VALUES (?, ?)",
            [(item.id, keyword_id) for item in items],
        )

        # 执行查询
        query = """
        SELECT p.id, p.price, p.status FROM products p
        INNER JOIN temp_ids t ON p.id = t.id AND p.keyword_id = t.keyword_id
        """
        cursor = self.conn.execute(query)
        for id, price, status in cursor.fetchall():
            prices_statuses[id] = {"price": price, "status": status}

        # 删除临时表
        self.conn.execute("DROP TABLE temp_ids")

        return prices_statuses

    def close(self):
        """
        显式关闭数据库连接。
        """
        self.conn.close()
        logger.info(f"Database connection closed: {self.db_name}")
