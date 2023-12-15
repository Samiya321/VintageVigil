from loguru import logger
import asyncio

from common.utils import extract_keyword_from_url, get_price_status_string


async def process_item(
    item,
    message_template,
    website_config,
    search_query,
    notification_clients,
    telegram_tasks,
):
    message = _create_notification_message(item, message_template, website_config)
    try:
        logger.info(
            f"{website_config.website_name}: {extract_keyword_from_url(search_query.keyword)} {item.product_url} {get_price_status_string(item.price_change)}"
        )
        notify_client = notification_clients[search_query.notify]
        if notify_client.client_type == "telegram":
            task = _send_notification(notify_client, message, item)
            telegram_tasks.append(task)
            if len(telegram_tasks) >= 10:
                await asyncio.gather(*telegram_tasks, return_exceptions=True)
                telegram_tasks.clear()
        elif notify_client.client_type == "wecom":
            await _send_notification(notify_client, message, item)
    except Exception as e:
        logger.error(f"Error preparing notification: {e}")


def _create_notification_message(item, message_template, website_config):
    price_currency = item.price * website_config.exchange_rate
    price = (
        f"{item.pre_price} 円 ==> {item.price}"
        if item.pre_price is not None
        else item.price
    )
    return message_template.substitute(
        priceStatus=get_price_status_string(item.price_change),
        productName=item.name,
        productURL=item.product_url,
        price=price,
        priceCurrency=f"{price_currency:.2f}",
    )


async def _send_notification(client, message, item):
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
