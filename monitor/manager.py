from website import *


def fetch_scraper(website_name):
    """
    Create and return a scraper object based on the website name.
    """
    scrapers = {
        "jumpshop": JumpShop,
        "lashinbang": Lashinbang,
        "mercapi": MercariMercapi,
        "mercari": MercariSearch,
        "mercari_user": MercariItems,
        "paypay": Paypay,
        "fril": Fril,
        "suruga": Suruga,
    }
    return scrapers.get(website_name)()
