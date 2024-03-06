from urllib.parse import urlparse, parse_qs

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
        for key in ["q", "search_word", "query", "keyword"]:
            if key in query_params:
                # 通常参数是一个列表，返回第一个值
                return query_params[key][0]

    # 如果不是http开头的URL或者没有找到对应的关键字，则返回原始URL或None
    return keyword
