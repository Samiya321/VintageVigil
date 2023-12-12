import asyncio
import httpx
import os
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_helper

from loguru import logger

from monitor import fetch_user_directories, setup_and_monitor

# 定义全局变量来控制监控循环
is_running = True


async def initialize_resources(parse_mode=None):
    load_dotenv()
    proxy = os.getenv("HTTP_PROXY")

    # Initialize httpx AsyncClient clinet
    httpx_client = httpx.AsyncClient(
        proxies=proxy, verify=False, http2=False, timeout=10, follow_redirects=True
    )

    # Initialize telegram bot
    asyncio_helper.CONNECT_TIMEOUT = 10
    asyncio_helper.REQUEST_TIMEOUT = 10
    asyncio_helper.proxy = proxy or None

    telegram_bot_tokens = [
        os.getenv("TELEGRAM_BOT_TOKEN_1"),
        os.getenv("TELEGRAM_BOT_TOKEN_2"),
    ]
    telegram_bots = {}

    for index, token in enumerate(telegram_bot_tokens):
        telegram_bots[index] = AsyncTeleBot(token, parse_mode=parse_mode)

    return httpx_client, telegram_bots


async def close_resources(httpx_client, telegram_bots):
    logger.info("Closing httpx client and telegram bot resources")
    await httpx_client.aclose()
    logger.info("httpx client has closed")

    for index, bot in telegram_bots.items():
        await bot.close_session()
        logger.info("telegram bot: {} has closed".format(index))


async def start_monitoring():
    """
    Start the monitoring process for multiple users.
    """
    global is_running
    try:
        logger.info("Starting VintageVigil ......")

        httpx_client, telegram_bots = await initialize_resources()
        user_directories = fetch_user_directories("user")

        monitor_tasks = [
            asyncio.create_task(
                setup_and_monitor(user_dir, is_running, httpx_client, telegram_bots)
            )
            for user_dir in user_directories
        ]
        await asyncio.gather(*monitor_tasks, return_exceptions=True)
    finally:
        if httpx_client or telegram_bots:
            logger.info("Closing all resources...")
            await close_resources(httpx_client, telegram_bots)


# 主程序入口
if __name__ == "__main__":
    try:
        asyncio.run(start_monitoring())
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        logger.info("Detected program interruption. Shutting down...")
        is_running = False  # 通知监控任务停止
        # Wait for a while to let all tasks notice the change
        asyncio.run(asyncio.sleep(2))
    finally:
        logger.info("VintageVigil stopped.")
