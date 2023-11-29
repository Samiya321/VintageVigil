class SearchResultItem:
    def __init__(
        self,
        id: str,
        name: str = None,
        price: float = None,
        image_url: str = None,
        product_url: str = None,
        price_change: int = 0,
        site: str = None,
        pre_price=None,
        # extra_data=None,
    ):
        self.id = id
        self.name = name
        self.price = float(price) if price is not None else None
        self.image_url = image_url
        self.product_url = product_url
        self.price_change = price_change
        self.site = site
        self.pre_price = pre_price
        # self.extra_data = extra_data or {}

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, SearchResultItem):
            return NotImplemented
        return (self.id) == (other.id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "price_change": self.price_change,
            "site": self.site,
            # "extra_data": self.extra_data,
        }
