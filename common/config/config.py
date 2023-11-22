from typing import Dict, List, Optional

import toml
from dotenv import load_dotenv

from . import config_default


class SearchConfig:
    def __init__(self, **kwargs: str):
        required_keys = ["keyword", "notify"]
        for key in required_keys:
            if key not in kwargs or not kwargs[key]:
                raise ValueError(
                    f"Error: '{key}' is required in search configurations."
                )

        kwargs["notify"] = config_default.NOTIFY_MAPPING.get(kwargs.get("notify"))

        for key, value in kwargs.items():
            setattr(self, key, value)


class WebsiteCommon:
    def __init__(
            self, website_name: str, delay: float, exchange_rate: float, msg_tpl: str
    ):
        self.website_name = website_name
        self.delay = delay
        self.exchange_rate = exchange_rate
        self.msg_tpl = msg_tpl


class Website:
    def __init__(
            self, common: WebsiteCommon, searches: Optional[List[SearchConfig]] = None
    ):
        self.common = common
        self.searches = searches


class Config:
    def __init__(
            self, user: str, notify_config: Dict[str, str], websites: List[Website]
    ):
        self.user = user
        self.notify_config = notify_config
        self.websites = websites
        self.validate_notify_config()

    def validate_notify_config(self):
        notify_config = self.notify_config

        notify_config["tg_send_type"] = config_default.SEND_TYPE_MAPPING.get(
            notify_config.get("tg_send_type", ""), config_default.DEFAULT_SEND_TYPE
        )
        notify_config["we_send_type"] = config_default.SEND_TYPE_MAPPING.get(
            notify_config.get("we_send_type", ""), config_default.DEFAULT_SEND_TYPE
        )

        if not notify_config.get("wecom_user_id") and not notify_config.get(
                "telegram_chat_id"
        ):
            raise ValueError(
                "Error: Either 'wecom_user_id' or 'telegram_chat_id' must be provided in notify configuration."
            )

    @classmethod
    def from_toml(cls, config_path: str) -> "Config":
        load_dotenv()
        try:
            parsed_toml = toml.load(config_path)
        except toml.TomlDecodeError as e:
            raise ValueError(f"Error parsing TOML configuration: {e}")

        notify_config = parsed_toml.get("notify", {})

        websites_config = parsed_toml.get("websites", {})
        websites = []
        for website_name, website_config in websites_config.items():
            if not website_config.get("enabled", False):
                continue
            searches = [
                SearchConfig(**search_config)
                for search_config in website_config.get("searches", [])
            ]
            website_common = WebsiteCommon(
                website_name=website_name,
                delay=website_config.get("delay", config_default.DEFAULT_DELAY),
                exchange_rate=website_config.get(
                    "exchange_rate", config_default.EXCHANGE_RATE
                ),
                msg_tpl=website_config.get("msg_tpl", config_default.MESSAGE_TEMPLATE),
            )

            websites.append(Website(common=website_common, searches=searches))

        return cls(
            user=parsed_toml.get("user", config_default.DEFAULT_USER),
            notify_config=notify_config,
            websites=websites,
        )