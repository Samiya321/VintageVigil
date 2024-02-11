from loguru import logger
import asyncio
from string import Template

from .send_notification import process_item
from common.utils import extract_keyword_from_url


async def process_search_keyword(
    scraper,
    search_query,
    database,
    notification_clients,
    user_dir,
    is_running,
):
    """
    Process a given search keyword for a website and execute necessary operations.
    """
    with logger.contextualize(
        website_name=search_query["website_name"],
        keyword=search_query["keyword"],
        user_path=user_dir,
    ):
        iteration_count = 0
        message_template = Template(search_query["msg_tpl"])
        while is_running:
            try:
                logger.info(f"--------- Start of iteration {iteration_count} ---------")
                logger.info(
                    f"{search_query['website_name']} : {extract_keyword_from_url(search_query['keyword'])} 开始监控"
                )
                products_to_process = await _collect_products(
                    scraper,
                    search_query,
                    iteration_count,
                    is_running,
                    search_query["user_max_pages"],
                )

                for item in database.upsert_products(
                    products_to_process,
                    search_query["keyword"],
                    search_query["website_name"],
                    search_query["push_price_changes"],
                ):
                    if iteration_count > 0:
                        await process_item(
                            item,
                            search_query,
                            message_template,
                            notification_clients,
                        )

                logger.info(f"--------- End of iteration {iteration_count} ---------\n")
                iteration_count += 1
                await asyncio.sleep(search_query["delay"])
            except Exception as e:
                logger.error(f"Error processing search keyword: {e}")


async def _collect_products(
    scraper, search_query, iteration_count, is_running, user_max_pages
):
    products = set()
    async for product in scraper.search(search_query, iteration_count, user_max_pages):
        if not is_running:
            break
        products.add(product)
    return products
