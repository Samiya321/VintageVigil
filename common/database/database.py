import sqlite3
from typing import Tuple, List, Optional

from loguru import logger


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
                product_count INTEGER DEFAULT 0,       -- 产品计数，默认为 0
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
                PRIMARY KEY (id, keyword_id),          -- 将产品 ID 和关键词 ID 一起作为主键
                FOREIGN KEY (keyword_id) REFERENCES website_keywords (id) -- 外键关联到 website_keywords 表
            );
        """,
        "upsert_product": """
            -- 插入或更新产品信息
            -- 如果具有相同的产品 ID 和关键词 ID 的记录已存在，则更新该记录
            INSERT INTO products (id, keyword_id, price, name, image_url, product_url) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, keyword_id) DO UPDATE SET
            price = excluded.price,
            name = excluded.name,
            image_url = excluded.image_url,
            product_url = excluded.product_url;
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
            UPDATE website_keywords SET product_count = ? WHERE id = ?;
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
        return result[0] if result else None

    def update_product_count(self, keyword_id: int):
        """
        更新特定关键词 ID 的产品数量。

        :param keyword_id: 关键词 ID。
        """

        count = self._safe_execute(
            "count_products_by_keyword", (keyword_id,), fetch_one=True
        )[0]
        self._safe_execute("update_product_count", (count, keyword_id))

    def upsert_products(self, items: List[dict], keyword: str, website: str):
        """
        插入或更新产品信息。

        :param items: 包含产品信息的字典列表。
        :param keyword: 关联的关键词。
        :param website: 关联的网站。
        :yield: 处理后的每个产品信息。
        """
        logger.info(
            f"Number of items entered into the database for processing: {len(items)}"
        )
        self.insert_or_ignore_keyword(website, keyword)
        keyword_id = self.get_keyword_id(website, keyword)
        existing_prices = self._bulk_fetch_prices(items, keyword_id)

        to_insert_or_update = []
        updated_num = 0
        new_num = 0

        for item in items:
            current_price = item["price"]
            existing_price = existing_prices.get(item["id"])

            if existing_price is None:
                # 商品在数据库中不存在，视为新商品
                item["price_change"] = 1
                new_num += 1
            elif current_price != existing_price:
                # 商品价格变化了，视为更新的商品
                item["price_change"] = 2 if current_price > existing_price else 3
                item["pre_price"] = existing_price
                updated_num += 1
            else:
                # 商品存在且价格未变，跳过处理
                continue

            to_insert_or_update.append(
                (
                    item["id"],
                    keyword_id,
                    item["price"],
                    item["name"],
                    item["image_url"],
                    item["product_url"],
                )
            )
            yield item

        if to_insert_or_update:
            with self.conn:  # 使用事务处理
                self.conn.executemany(
                    self.SQL_STATEMENTS["upsert_product"], to_insert_or_update
                )

        self.update_product_count(keyword_id)
        if updated_num > 0 or new_num > 0:
            logger.info(f"Database updated. New: {new_num}, Updated: {updated_num}")

    def _bulk_fetch_prices(self, items: List[dict], keyword_id: int) -> dict:
        """
        批量获取产品的当前价格。

        :param items: 包含产品信息的字典列表。
        :param keyword_id: 关联的关键词 ID。
        :return: 一个字典，包含产品 ID 和对应的价格。
        """

        # 构造一个包含所有项目 ID 和关键字 ID 的元组列表
        ids = [(item["id"], keyword_id) for item in items]

        # 为每个 (id, keyword_id) 对创建占位符 "?"
        placeholders = ",".join(["(?, ?)" for _ in ids])

        # 构造查询字符串
        query = "SELECT id, price FROM products WHERE (id, keyword_id) IN ({})".format(
            placeholders
        )
        # query = self.SQL_STATEMENTS["bulk_fetch_prices"].format(placeholders)
        # 将元组列表展开为参数列表
        params = [param for tup in ids for param in tup]

        # 执行查询
        cursor = self.conn.execute(query, params)
        result = cursor.fetchall()

        # 构造并返回包含查询结果的字典
        # 只包含数据库中实际存在的产品的价格
        prices = {id: price for id, price in result}
        return prices

    def close(self):
        """
        显式关闭数据库连接。
        """
        self.conn.close()
        logger.info(f"Database connection closed: {self.db_name}")
