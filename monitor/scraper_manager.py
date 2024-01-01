from website import *


def fetch_scraper(website_name, httpx_client):
    """
    Create and return a scraper object based on the website name.

    Args:
        website_name (str): The name of the website for which the scraper object is to be created.
        httpx_client: An HTTP client object used for making HTTP requests.

    Returns:
        Scraper: An instance of the scraper object corresponding to the website name.

    Raises:
        ValueError: If no scraper is found for the given website name.
    """
    scrapers = {
        "jumpshop": JumpShop,
        "lashinbang": Lashinbang,
        "mercari": MercariSearch,
        "mercari_user": MercariItems,
        "paypay": Paypay,
        "fril": Fril,
        "suruga": Suruga,
        "rennigou": Rennigou,
    }
    scraper_class = scrapers.get(website_name)
    if scraper_class:
        return scraper_class(httpx_client)
    else:
        raise ValueError(f"No scraper found for {website_name}")
