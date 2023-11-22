import sqlite3
from typing import Tuple

from loguru import logger


class ProductDatabase:
    # 将 SQL 查询语句作为类属性
    SQL_CREATE_WEBSITE_KEYWORDS_TABLE = """
        CREATE TABLE IF NOT EXISTS website_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            keyword TEXT NOT NULL,
            product_count INTEGER DEFAULT 0,
            UNIQUE(website, keyword)
        );
    """
    SQL_CREATE_PRODUCTS_TABLE = """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT NOT NULL,
            keyword_id INTEGER NOT NULL,
            name TEXT,
            price REAL NOT NULL,
            image_url TEXT,
            product_url TEXT,
            PRIMARY KEY (id, keyword_id),
            FOREIGN KEY (keyword_id) REFERENCES website_keywords (id)
        );
    """
    SQL_UPSERT_QUERY = """
    INSERT INTO products (id, keyword_id, price, name, image_url, product_url) 
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(id, keyword_id) DO UPDATE SET
    price = excluded.price,
    name = excluded.name,
    image_url = excluded.image_url,
    product_url = excluded.product_url;
    """

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.setup_database()

    def upsert_products(self, items, keyword, website):
        logger.info(
            f"Number of items entered into the database for processing: {len(items)}"
        )

        self.insert_or_ignore_keyword(website, keyword)
        keyword_id = self.get_keyword_id(website, keyword)

        to_insert_or_update = []

        updated_num = 0
        new_num = 0

        for item in items:
            item_key = (item["id"], keyword_id)
            current_price = item["price"]

            # 仅当需要时查询现有价格
            existing_price = self._execute_query(
                "SELECT price FROM products WHERE id = ? AND keyword_id = ?;", item_key
            ).fetchone()

            # 判断是否需要插入或更新
            if existing_price is not None:
                if current_price != existing_price[0]:
                    # 价格有变动，准备更新数据
                    item["price_change"] = 2 if current_price > existing_price[0] else 3
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
                    item["pre_price"] = existing_price[0]
                    updated_num += 1
                    yield item
            else:
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
                item["price_change"] = 1
                new_num += 1
                yield item

        if to_insert_or_update:
            with self.conn:  # 使用事务处理
                self.conn.executemany(self.SQL_UPSERT_QUERY, to_insert_or_update)

        self.update_product_count(keyword_id)
        if updated_num > 0 or new_num > 0:
            logger.info(
                f"Number of updated items updated in the database, Updated: {updated_num}/New: {new_num}"
            )

    def _execute_query(self, query: str, params: Tuple = ()):
        """执行 SQL 查询"""
        try:
            cursor = self.conn.execute(query, params)
            return cursor
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error: {e}")
            # 根据需要添加更多的错误处理逻辑
            return None

    def setup_database(self):
        with self.conn:
            self._execute_query(self.SQL_CREATE_WEBSITE_KEYWORDS_TABLE)
        with self.conn:
            self._execute_query(self.SQL_CREATE_PRODUCTS_TABLE)

    def insert_or_ignore_keyword(self, website: str, keyword: str):
        with self.conn:  # 这将自动处理事务
            self._execute_query(
                "INSERT OR IGNORE INTO website_keywords (website, keyword) VALUES (?, ?);",
                (website, keyword),
            )

    def get_keyword_id(self, website: str, keyword: str) -> int:
        cursor = self._execute_query(
            "SELECT id FROM website_keywords WHERE website = ? AND keyword = ?;",
            (website, keyword),
        )
        return cursor.fetchone()[0]

    def update_product_count(self, keyword_id):
        with self.conn:
            count = self._execute_query(
                "SELECT COUNT(*) FROM products WHERE keyword_id = ?;", (keyword_id,)
            ).fetchone()[0]
            self._execute_query(
                "UPDATE website_keywords SET product_count = ? WHERE id = ?;",
                (count, keyword_id),
            )

    def close(self):
        """显式关闭数据库连接"""
        self.conn.close()
        logger.info(f"Database connection closed: {self.db_name}")
