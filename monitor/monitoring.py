# monitoring.py
import asyncio
from string import Template

from loguru import logger

from .manager import fetch_scraper


def get_price_status_string(price_change):
    """
    Return a string representation of the price status.
    """
    return {1: "上新", 2: "涨价", 3: "降价"}.get(price_change, "")


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
    # 使用 logger.contextualize 方法添加上下文信息
    with logger.contextualize(
        website_name=website_config.website_name,
        keyword=search_query.keyword,
        user_path=user_dir,
    ):
        iteration_count = 0
        while is_running:
            try:
                logger.info(
                    f"Processing keyword: {search_query.keyword} for website: {website_config.website_name}"
                )
                unique_products = set()
                products_to_process = []
                async for product in scraper.search(search_query, iteration_count):
                    if not is_running:  # 检查 is_running 状态
                        break  # 如果 is_running 为 False，则中断循环
                    product_info = product.to_dict()
                    product_key = frozenset(product_info.items())
                    if product_key not in unique_products:
                        unique_products.add(product_key)
                        products_to_process.append(product_info)

                pass
                for item in database.upsert_products(
                    products_to_process,
                    search_query.keyword,
                    website_config.website_name,
                ):
                    if iteration_count > 0:
                        price_currency = item["price"] * website_config.exchange_rate
                        if item.get("pre_price") is not None:
                            item["price"] = f"{item['pre_price']} 円 ==> {item['price']}"
                        message = message_template.substitute(
                            priceStatus=get_price_status_string(item["price_change"]),
                            productName=item["name"],
                            productURL=item["product_url"],
                            price=item["price"],
                            priceCurrency=f"{price_currency:.2f}",
                        )
                        try:
                            notify_client = notification_clients[search_query.notify]
                            await send_notification(notify_client, message, item)
                            item_id = item["id"]
                            logger.info(f"Notification for item sent: {item_id}")
                        except Exception as e:
                            logger.error(f"Error sending notification: {e}")

                iteration_count += 1
                await asyncio.sleep(website_config.delay)
            except Exception as e:
                logger.error(f"Error processing search keyword: {e}")


async def send_notification(client, message, item):
    """
    Send notifications using the specified client with the given message and item details.
    """
    try:
        if client.client_type == "telegram":
            await client.send_message(message, item["image_url"])
        elif client.client_type == "wecom":
            await client.send_message(
                message, item["image_url"], item["product_url"], item["name"]
            )
            await asyncio.sleep(0.01)  # 添加小延迟
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        await asyncio.sleep(0.01)  # 即使出错也添加延迟


async def monitor_site(
    site_config, database, notification_clients, user_dir, is_running, httpx_client
):
    """
    Monitor a specific website for changes in product information.
    """
    logger.info(f"Starting monitoring for site: {site_config.common.website_name}")

    scraper = fetch_scraper(site_config.common.website_name, httpx_client)
    message_template = Template(site_config.common.msg_tpl)

    if scraper and site_config.searches:
        search_tasks = [
            asyncio.create_task(
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
            )
            for search_query in site_config.searches
        ]
        await asyncio.gather(*search_tasks, return_exceptions=True)

    logger.info(f"Monitoring ended for site: {site_config.common.website_name}")
