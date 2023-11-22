import asyncio

from loguru import logger

from monitor import fetch_user_directories, setup_and_monitor

# 定义全局变量来控制监控循环
is_running = True


async def start_monitoring():
    """
    Start the monitoring process for multiple users.
    """
    global is_running
    logger.info("Starting VintageVigil ......")

    user_directories = fetch_user_directories("user")

    monitor_tasks = [
        asyncio.create_task(setup_and_monitor(user_dir, is_running))
        for user_dir in user_directories
    ]
    await asyncio.gather(*monitor_tasks, return_exceptions=True)

    logger.info("VintageVigil stopped.")


# 主程序入口
if __name__ == "__main__":
    try:
        asyncio.run(start_monitoring())
    except KeyboardInterrupt:
        logger.info("Detected program interruption. Shutting down...")
        is_running = False  # 通知监控任务停止

        # Wait for a while to let all tasks notice the change
        asyncio.run(asyncio.sleep(3))
        logger.info(
            "All tasks have been notified to stop. The program is shutting down."
        )
