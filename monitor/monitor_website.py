from .scraper_manager import fetch_scraper
from string import Template
from loguru import logger
import asyncio

from .monitor_keyword import process_search_keyword


async def _initialize_site_monitoring(site_config, httpx_client):
    """
    Initialize the scraper and message template for a website.
    """
    try:
        scraper = fetch_scraper(site_config.common.website_name, httpx_client)
        message_template = Template(site_config.common.msg_tpl)
        return scraper, message_template
    except Exception as e:
        logger.error(
            f"Error initializing monitoring for {site_config.common.website_name}: {e}"
        )
        return None, None


async def monitor_site(
    site_config, database, notification_clients, user_dir, is_running, httpx_client
):
    """
    Monitor a specific website for changes in product information.
    """
    logger.info(f"Starting monitoring for site: {site_config.common.website_name}")

    scraper, message_template = await _initialize_site_monitoring(
        site_config, httpx_client
    )

    if scraper and site_config.searches:
        search_tasks = [
            process_search_keyword(
                scraper,
                search_query,
                site_config.common,
                database,
                notification_clients,
                message_template,
                user_dir,
                is_running,
            )
            for search_query in site_config.searches
        ]
        await asyncio.gather(*search_tasks, return_exceptions=True)

    logger.info(f"Monitoring ended for site: {site_config.common.website_name}")
