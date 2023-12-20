import os
from loguru import logger


def get_website_keyword_filter(website_name, keyword, user_path):
    def filter(record):
        return (
            record["extra"].get("website_name") == website_name
            and record["extra"].get("keyword") == keyword
            and record["extra"].get("user_path") == user_path
        )

    return filter


def setup_logger(websites, user_path):
    log_path = f"{user_path}/logs"

    # 检查环境变量DEBUG的值
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    # 根据DEBUG的值选择不同的日志格式
    if debug_mode:
        # 包含文件名和行号的详细日志格式
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss:SSS}</green> | <level>{level: <8}</level> | <cyan>{file}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
    else:
        # 不包含文件名和行号的简洁日志格式
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss:SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"

    for website in websites:
        for index, search in enumerate(website.searches):
            keyword = search.keyword
            index = int(index) + 1
            logger.add(
                f"{log_path}/{website.common.website_name}-{index}.log",
                filter=get_website_keyword_filter(
                    website.common.website_name, keyword, user_path
                ),
                format=log_format,  # 使用根据DEBUG值选择的日志格式
                rotation="10 MB",  # 每个日志文件最大10MB
                retention="24 hours",  # 保留24小时内的日志
                enqueue=True,  # 异步写入日志
            )
