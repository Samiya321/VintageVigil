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

    for website in websites:
        for index, search in enumerate(website.searches):
            keyword = search.keyword
            index = int(index) + 1
            logger.add(
                f"{log_path}/{website.common.website_name}-{index}.log",
                filter=get_website_keyword_filter(
                    website.common.website_name, keyword, user_path
                ),
                rotation="10 MB",  # 每个日志文件最大10MB
                retention="24 hours",  # 保留24小时内的日志
                enqueue=True,  # 异步写入日志
            )
