from .scraper_manager import fetch_scraper
from string import Template
from loguru import logger
import asyncio

from .monitor_keyword import process_search_keyword


async def monitor_site(
    site_config, database, notification_clients, user_dir, is_running, httpx_client
):
    """
    Monitor a specific website for changes in product information.
    """
    logger.info(f"Starting monitoring for site: {site_config[0]}")

    scraper = fetch_scraper(site_config[1]['website_name'], httpx_client)

    if scraper and site_config[1:]:
        search_tasks = [
            process_search_keyword(
                scraper,
                search_query,
                database,
                notification_clients,
                user_dir,
                is_running,
            )
            for search_query in site_config[1:]
        ]
        await asyncio.gather(*search_tasks, return_exceptions=True)

    logger.info(f"Monitoring ended for site: {site_config[0]}")
