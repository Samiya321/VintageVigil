import time
import asyncio
from common import ProductDatabase
from website import Suruga, Paypay, JumpShop, Lashinbang, Fril


async def test_website(website, keywords):
    Website = website.capitalize()

    scrapy = globals()[Website]()
    database = "database.db"
    website = website
    keywords = keywords
    db = ProductDatabase(database)

    items_to_process = []
    async for product in scrapy.search(keywords):
        items_to_process.append(
            {
                "id": product.id,
                "price": product.price,
                "name": product.name,
                "image_url": product.image_url,
                "product_url": product.product_url,
            }
        )

    db.upsert_products(items_to_process, keywords, website)

    await scrapy.close()


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(test_website(website="surugaya", keywords="家庭教師ヒットマンREBORN"))
    cost_time = time.time() - start_time
    print(cost_time)
