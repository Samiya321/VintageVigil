from loguru import logger
import asyncio

from .send_notification import process_item
from common.utils import extract_keyword_from_url

async def process_search_keyword(
    scraper,
    search_query,
    website_config,
    database,
    notification_clients,
    message_template,
    user_dir,
    is_running,
):
    """
    Process a given search keyword for a website and execute necessary operations.
    """
    with logger.contextualize(
        website_name=website_config.website_name,
        keyword=search_query.keyword,
        user_path=user_dir,
    ):
        iteration_count = 0
        while is_running:
            try:
                logger.info(f"--------- Start of iteration {iteration_count} ---------")
                logger.info(
                    f"{website_config.website_name} : {extract_keyword_from_url(search_query.keyword)} 开始监控"
                )
                products_to_process = await _collect_products(
                    scraper, search_query, iteration_count, is_running
                )

                telegram_tasks = []
                for item in database.upsert_products(
                    products_to_process,
                    search_query.keyword,
                    website_config.website_name,
                    website_config.push_price_changes,
                ):
                    if iteration_count > 0:
                        await process_item(
                            item,
                            message_template,
                            website_config,
                            search_query,
                            notification_clients,
                            telegram_tasks,
                        )

                await _execute_telegram_tasks(telegram_tasks)

                logger.info(f"--------- End of iteration {iteration_count} ---------\n")
                iteration_count += 1
                await asyncio.sleep(website_config.delay)
            except Exception as e:
                logger.error(f"Error processing search keyword: {e}")


async def _collect_products(scraper, search_query, iteration_count, is_running):
    products = set()
    async for product in scraper.search(search_query, iteration_count):
        if not is_running:
            break
        products.add(product)
    return products


async def _execute_telegram_tasks(telegram_tasks):
    if telegram_tasks:
        await asyncio.gather(*telegram_tasks, return_exceptions=True)
