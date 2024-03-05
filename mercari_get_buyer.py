import os
import re
import requests
from uuid import uuid4
import ecdsa
from datetime import datetime
from jose import jws
from jose.constants import ALGORITHMS
from telebot import TeleBot
from typing import Optional, Dict

# Use an environment variable for the API token
TG_TOKEN =  ""
API_TOKEN = os.getenv("MERCARI_BOT_API_TOKEN") | TG_TOKEN
bot = TeleBot(API_TOKEN)

# Constants
MERCARI_API_URL = "https://api.mercari.jp/items/get?id={}"
USER_PROFILE_URL = "https://jp.mercari.com/user/profile/{}"
ALGORITHM = ALGORITHMS.ES256


def generate_dpop(
    url: str,
    method: str,
    key: ecdsa.SigningKey,
    extra_payload: Optional[Dict[str, str]] = None,
) -> str:
    payload = {
        "iat": int(datetime.now().timestamp()),
        "jti": str(uuid4()),
        "htu": url,
        "htm": method,
        **(extra_payload or {}),
    }

    headers = {
        "typ": "dpop+jwt",
        "alg": ALGORITHM,
        "jwk": key.get_verifying_key().to_jwk(),
    }

    return jws.sign(payload, key, headers, ALGORITHM)


def create_headers(method: str, url: str) -> Dict[str, str]:
    key = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
    dpop_token = generate_dpop(url, method, key, extra_payload={"uuid": str(uuid4())})
    return {
        "DPoP": dpop_token,
        "X-Platform": "web",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "python-mercari",
    }


def extract_item_id(text: str) -> Optional[str]:
    match = re.search(r"(?<=item/)(m\d+)", text)
    return match.group(1) if match else None


def timestamp_to_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


@bot.message_handler(func=lambda message: True)
def process_message(message):
    item_id = extract_item_id(message.text)
    if item_id:
        try:
            url = MERCARI_API_URL.format(item_id)
            headers = create_headers("GET", url)
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # This will raise an exception for HTTP errors
            data = response.json()
            buyer_id = data.get("data", {}).get("buyer", {}).get("id")
            if buyer_id:
                profile_url = USER_PROFILE_URL.format(buyer_id)
                updated = timestamp_to_datetime(data.get("data", {}).get("updated"))
                created = timestamp_to_datetime(data.get("data", {}).get("created"))
                reply_message = f"Buyer profile: {profile_url}\nUpdated at: {updated}\nCreated at: {created}"
                bot.reply_to(message, reply_message)
        except requests.RequestException as e:
            bot.reply_to(
                message,
                "Failed to retrieve item information. Please check the item ID or try again later.",
            )
    else:
        bot.reply_to(message, "Please send a valid Mercari item ID or link.")


if __name__ == "__main__":
    bot.polling(none_stop=True)
