MESSAGE_TEMPLATE = """
【$priceStatus】$productName
【链接】$productURL
【价格】$price 円 == $priceCurrency 元
"""

NOTIFY_MAPPING = {1: "telegram_1", 2: "telegram_2", 3: "wecom_1"}

SEND_TYPE_MAPPING = {1: "text", 2: "photo", 3: "news"}

DEFAULT_DELAY = 60

DEFAULT_USER = "Default User"

DEFAULT_SEND_TYPE = "news"

EXCHANGE_RATE = 0.049
