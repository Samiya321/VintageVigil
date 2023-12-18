class SearchResultItem:
    def __init__(
        self,
        site: str,
        id: str,
        name: str,
        product_url: str,
        image_url: str,
        status: int,
        price: float,
        price_change: int = 0,
        pre_price=None,
        # extra_data=None,
    ):
        self.site = site
        self.id = id
        self.name = name
        self.price = float(price) if price else None
        self.price_change = price_change
        self.pre_price = pre_price
        self.product_url = product_url
        self.image_url = image_url
        self.status = status
        # self.extra_data = extra_data or {}

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, SearchResultItem):
            return NotImplemented
        return (self.id) == (other.id)


class SearchResultItemState:
    SOLD_OUT = 0,
    ON_SALE = 1,
    ON_SALE_OWN = 2,
    ON_SALE_THIRD = 3

