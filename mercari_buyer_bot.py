import re
import telebot
import requests
from uuid import uuid4, UUID
import ecdsa
from datetime import datetime

import random
from time import time
from typing import Dict, Optional

from ecdsa import SigningKey
from jose import jws
from jose.backends.ecdsa_backend import ECDSAECKey
from jose.constants import ALGORITHMS

API_TOKEN = "5652509870:AAG93c-5qeSeBN-hYUPy0cWywX5RvAXm6cQ"
bot = telebot.TeleBot(API_TOKEN)


def generate_dpop(
    url: str,
    method: str,
    key: SigningKey,
    extra_payload: Optional[Dict[str, str]] = None,
) -> str:
    payload = {
        "iat": int(time()),
        "jti": str(UUID(int=random.getrandbits(128))),
        "htu": url,
        "htm": method,
        **extra_payload,
    }

    ec_key = ECDSAECKey(key, ALGORITHMS.ES256)
    headers = {
        "typ": "dpop+jwt",
        "alg": "ES256",
        "jwk": {k: ec_key.to_dict()[k] for k in ["crv", "kty", "x", "y"]},
    }

    return jws.sign(payload, key, headers, ALGORITHMS.ES256)


def create_headers_dpop(method, url):
    dpop = generate_dpop(
        url=url,
        method=method,
        key=ecdsa.SigningKey.generate(curve=ecdsa.NIST256p),
        extra_payload={"uuid": str(uuid4())},
    )
    return dpop


def create_headers(method, url):
    headers = {
        "DPoP": create_headers_dpop(method, url),
        "X-Platform": "web",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "python-mercari",
    }
    return headers


def extract_item_id(text):
    match = re.match(r"m\d+|https://jp.mercari.com/item/(m\d+)", text)
    if match:
        return match.group(1) if match.group(1) else match.group(0)
    return None


def timestamp_to_datetime(timestamp):
    # 将时间戳转换为 datetime 对象
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


@bot.message_handler(func=lambda message: True)
def process_message(message):
    item_id = extract_item_id(message.text)
    if item_id:
        url = f"https://api.mercari.jp/items/get?id={item_id}"
        headers = create_headers("GET", url)
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            buyer_id = data.get("data", {}).get("buyer", {}).get("id")
            if buyer_id:
                profile_url = f"https://jp.mercari.com/user/profile/{buyer_id}"
                # 获取并转换时间戳
                updated = timestamp_to_datetime(data.get("data", {}).get("updated"))
                created = timestamp_to_datetime(data.get("data", {}).get("created"))
                reply_message = (
                    f"买家主页: {profile_url}\n更新时间: {updated}\n创建时间: {created}"
                )
                bot.reply_to(message, reply_message)
                return
        bot.reply_to(
            message,
            "Failed to retrieve item information. Please check the item ID or try again later.",
        )
    else:
        bot.reply_to(message, "Please send a valid Mercari item ID or link.")


if __name__ == "__main__":
    bot.polling(none_stop=True)
