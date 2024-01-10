from loguru import logger
import asyncio

from common.utils import extract_keyword_from_url, get_price_status_string


async def process_item(
    item,
    search_query,
    message_template,
    notification_clients,
    telegram_tasks,
):
    message = _create_notification_message(item, message_template, search_query)
    try:
        logger.info(
            f"{search_query['website_name']}: {extract_keyword_from_url(search_query['keyword'])} {item.product_url} {get_price_status_string(item.price_change)}"
        )
        notify_client = notification_clients[search_query["notify"][0]]
        if notify_client.client_type == "telegram":
            task = _send_notification(
                notify_client, message, item, search_query["notify"][1] -1 
            )
            telegram_tasks.append(task)
            if len(telegram_tasks) >= 10:
                await asyncio.gather(*telegram_tasks, return_exceptions=True)
                telegram_tasks.clear()
        elif notify_client.client_type == "wecom":
            await _send_notification(
                notify_client, message, item, search_query["notify"][1] - 1
            )
    except Exception as e:
        logger.error(f"Error preparing notification: {e}")


def _create_notification_message(item, message_template, search_query):
    price_currency = item.price * search_query["exchange_rate"]
    price = f"{item.pre_price} 円 ==> {item.price}" if item.pre_price else item.price
    return message_template.safe_substitute(
        id=item.id,
        imageURL=item.image_url,
        productName=item.name,
        price=price,
        priceStatus=get_price_status_string(item.price_change),
        priceCurrency=f"{price_currency:.2f}",
        productURL=item.product_url,
        site=item.site,
        keyword=extract_keyword_from_url(search_query["keyword"]),
    )


async def _send_notification(client, message, item, chat_id_index):
    """
    Send notifications using the specified client with the given message and item details.
    """
    try:
        if client.client_type == "telegram":
            await client.send_message(message, item.image_url, chat_id_index)
        elif client.client_type == "wecom":
            await client.send_message(
                message, item.image_url, item.product_url, item.name, chat_id_index
            )
            await asyncio.sleep(0.01)  # 添加小延迟
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        await asyncio.sleep(0.01)  # 即使出错也添加延迟
