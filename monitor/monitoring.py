import asyncio
from string import Template
from urllib.parse import urlparse, parse_qs

from loguru import logger

from .manager import fetch_scraper


def get_price_status_string(price_change):
    """
    Return a string representation of the price status.
    """
    return {0: "不变", 1: "上新", 2: "补货", 3: "涨价", 4: "降价"}.get(price_change, "")


def extract_keyword_from_url(keyword):
    # 检查URL是否以http开头
    if keyword.startswith("http"):
        parsed_url = urlparse(keyword)
        query_params = parse_qs(parsed_url.query)

        # 检查关键参数并返回相应的值
        for key in ["q", "search_word", "query"]:
            if key in query_params:
                # 通常参数是一个列表，返回第一个值
                return query_params[key][0]

    # 如果不是http开头的URL或者没有找到对应的关键字，则返回原始URL或None
    return keyword


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
                    f"--------- Start of iteration {iteration_count} ---------"
                )  # 循环开始时的日志
                logger.info(
                    f"{website_config.website_name} : {extract_keyword_from_url(search_query.keyword)} 开始监控"
                )
                products_to_process = set()
                async for product in scraper.search(search_query, iteration_count):
                    if not is_running:  # 检查 is_running 状态
                        break  # 如果 is_running 为 False，则中断循环
                    products_to_process.add(product)

                # 用于收集 Telegram 客户端的异步任务
                telegram_tasks = []
                for item in database.upsert_products(
                    products_to_process,
                    search_query.keyword,
                    website_config.website_name,
                    website_config.push_price_changes,
                ):
                    if iteration_count > 0:
                        price_currency = item.price * website_config.exchange_rate
                        if item.pre_price is not None:
                            price = f"{item.pre_price} 円 ==> {item.price}"
                        else:
                            price = item.price
                        message = message_template.substitute(
                            priceStatus=get_price_status_string(item.price_change),
                            productName=item.name,
                            productURL=item.product_url,
                            price=price,
                            priceCurrency=f"{price_currency:.2f}",
                        )
                        # 创建并添加异步任务到列表
                        try:
                            logger.info(
                                f"{website_config.website_name}: {extract_keyword_from_url(search_query.keyword)} {item.product_url} {get_price_status_string(item.price_change)}"
                            )
                            notify_client = notification_clients[search_query.notify]
                            if notify_client.client_type == "telegram":
                                task = send_notification(notify_client, message, item)
                                telegram_tasks.append(task)
                                if len(telegram_tasks) >= 10:  # 如果达到10个任务
                                    await asyncio.gather(
                                        *telegram_tasks, return_exceptions=True
                                    )  # 执行这些任务
                                    telegram_tasks = []  # 清空列表以便收集新的任务
                            elif notify_client.client_type == "wecom":
                                # 对于 WeCom 客户端，同步执行发送消息
                                await send_notification(notify_client, message, item)

                        except Exception as e:
                            logger.error(f"Error preparing notification: {e}")

                # 循环结束后，使用 asyncio.gather 并发执行所有收集到的异步任务
                if telegram_tasks:
                    await asyncio.gather(*telegram_tasks, return_exceptions=True)

                logger.info(
                    f"--------- End of iteration {iteration_count} ---------\n"
                )  # 循环结束时的日志
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
            await client.send_message(message, item.image_url)
        elif client.client_type == "wecom":
            await client.send_message(
                message, item.image_url, item.product_url, item.name
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
