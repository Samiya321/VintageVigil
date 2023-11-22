from website import MercariSearch, MercariItems, MercariMercapi
import asyncio
import time


async def test_mercari_search():
    mercari = MercariSearch()
    items = list()

    class Search:
        def __init__(self, keyword):
            self.keyword = keyword

    # 创建一个 Search 实例并给 keyword 赋值
    search = Search(keyword="家庭教師ヒットマンREBORN")

    iteration_count = 0
    async for item in mercari.search(search, iteration_count):
        items.append(item)
    await mercari.close()
    print(len(items))


async def test_mercari_items():
    mercari = MercariItems()
    items = list()
    async for item in mercari.search(204948396):
        items.append(item)
    await mercari.close()
    print(len(items))


async def test_mercapi_search():
    mercari = MercariMercapi()
    items = list()
    async for searched_item in mercari.search("家庭教師ヒットマンREBORN"):
        # print(searched_item.name, searched_item.price)
        # if searched_item.buyer_id == '261434822':
        items.append(searched_item)
    print(len(items))


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(test_mercari_search())
    cost_time = time.time() - start_time
    print(cost_time)
