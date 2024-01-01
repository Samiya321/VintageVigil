# 默认用户名
DEFAULT_USER = "Default User"

# 消息发送类型
SEND_TYPE_MAPPING = {1: "text", 2: "photo", 3: "news"}
# 默认消息发送类型
DEFAULT_SEND_TYPE = "news"


# 通知方式
NOTIFY_MAPPING = {1: "telegram_1", 2: "telegram_2", 3: "wecom_1"}

# 默认延迟
DEFAULT_DELAY = 1200

# 默认日汇
EXCHANGE_RATE = 0.050

# 默认是否开启价格变动推送
PUSH_PRICE_CHANGES = True

# 默认检索最大页数
USER_DEFAULT_MAX_PAGES = 20

# 默认最大并发数
MAX_CONCURRENCY = 10

# 默认消息发送模板
MESSAGE_TEMPLATE = """
【$priceStatus】$productName
【链接】$productURL
【价格】$price 円 == $priceCurrency 元
"""
