from typing import Dict

import toml
import os
from . import config_default


class Config:
    def __init__(self, user: str, notify_config: Dict[str, str], websites):
        self.user = user
        self.notify_config = notify_config
        self.websites = websites
        self.validate_notify_config()

    def validate_notify_config(self):
        """验证通知配置的有效性并设置默认值"""
        # 使用默认值进行安全检查
        for key in ["tg_send_type", "we_send_type"]:
            self.notify_config[key] = config_default.SEND_TYPE_MAPPING.get(
                self.notify_config.get(key, ""), config_default.DEFAULT_SEND_TYPE  # type: ignore
            )

        # 确保至少提供了一个有效的通知用户ID
        if not any(
            self.notify_config.get(key) for key in ["wecom_user_id", "telegram_chat_id"]
        ):
            raise ValueError(
                "Error: Either 'wecom_user_id' or 'telegram_chat_id' must be provided in notify configuration."
            )

    @staticmethod
    def merge_dicts(base_dict: Dict, new_dict: Dict) -> Dict:
        """合并两个字典，特别处理嵌套字典和列表。"""
        for key, value in new_dict.items():
            if key in base_dict:
                if isinstance(base_dict[key], dict) and isinstance(value, dict):
                    base_dict[key] = Config.merge_dicts(base_dict[key], value)
                elif isinstance(base_dict[key], list) and isinstance(value, list):
                    base_dict[key].extend(value)
                else:
                    base_dict[key] = value
            else:
                base_dict[key] = value
        return base_dict

    @staticmethod
    def read_and_merge_toml_files(directory: str):
        """从指定目录读取所有 TOML 文件并合并配置。"""
        combined_config = {}

        for file in os.listdir(directory):
            if file.endswith(".toml"):
                file_path = os.path.join(directory, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    config_data = toml.load(f)
                    combined_config = Config.merge_dicts(combined_config, config_data)

        return combined_config

    @staticmethod
    def get_config_value(configs, key, default_value):
        # 按顺序尝试获取配置值，并返回第一个找到的值或默认值
        for config in configs:
            value = config.get(key)
            if value is not None:
                return value
        return default_value

    @staticmethod
    def check_search_config(search_config):
        """检查搜索配置的必要键"""
        required_keys = ["keyword", "notify"]
        missing_keys = [
            key
            for key in required_keys
            if key not in search_config or not search_config[key]
        ]

        if missing_keys:
            raise ValueError(
                f"Error: Missing required keys in search configurations: {', '.join(missing_keys)}"
            )

        # 这里假设 NOTIFY_MAPPING 是一个预定义的字典
        search_config["notify"] = config_default.NOTIFY_MAPPING.get(
            search_config.get("notify"), "default_mapped_value"
        )
        return search_config

    @classmethod
    def from_toml(cls, user_dir: str) -> "Config":
        try:
            parsed_toml = cls.read_and_merge_toml_files(user_dir)
        except toml.TomlDecodeError as e:
            raise ValueError(f"Error parsing TOML configuration: {e}")

        # 配置文件分为三部分
        notify_config = parsed_toml.get("notify", {})
        common_config = parsed_toml.get("common", {})
        websites_config = parsed_toml.get("websites", {})

        websites = []

        # 遍历网站配置
        for website_name, website_config in websites_config.items():
            searches = []
            searches.append(website_name)
            for search_config in website_config.get("searches", []):
                search_config.setdefault("website_name", website_name)
                # 为每个配置定义一个值列表
                config_sources = [search_config, website_config, common_config]

                # 获取并设置'delay'
                delay = cls.get_config_value(
                    config_sources, "delay", config_default.DEFAULT_DELAY
                )
                search_config.setdefault("delay", delay)

                # 获取并设置'exchange_rate'
                exchange_rate = cls.get_config_value(
                    config_sources, "exchange_rate", config_default.EXCHANGE_RATE
                )
                search_config.setdefault("exchange_rate", exchange_rate)

                # 获取并设置'push_price_changes'
                push_price_changes = cls.get_config_value(
                    config_sources,
                    "push_price_changes",
                    config_default.PUSH_PRICE_CHANGES,
                )
                search_config.setdefault("push_price_changes", push_price_changes)

                # 获取并设置'user_max_pages'
                user_max_pages = cls.get_config_value(
                    config_sources,
                    "user_max_pages",
                    config_default.USER_DEFAULT_MAX_PAGES,
                )
                search_config.setdefault("user_max_pages", user_max_pages)

                # 获取并设置'max_concurrency'
                max_concurrency = cls.get_config_value(
                    config_sources, "max_concurrency", config_default.MAX_CONCURRENCY
                )
                search_config.setdefault("max_concurrency", max_concurrency)

                # 获取并设置'msg_tpl'
                msg_tpl = cls.get_config_value(
                    config_sources, "msg_tpl", config_default.MESSAGE_TEMPLATE
                )
                search_config.setdefault("msg_tpl", msg_tpl)

                search_config.setdefault("filter", {})
                search_config = cls.check_search_config(search_config)

                searches.append(search_config)

            websites.append(searches)

        # 创建 Config 对象
        return cls(
            user=notify_config.get("user", config_default.DEFAULT_USER),
            notify_config=notify_config,
            websites=websites,
        )
