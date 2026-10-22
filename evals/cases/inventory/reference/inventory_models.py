import re
from dataclasses import dataclass

_SKU = re.compile(r"^[A-Z]{3}-\d{4}$")


@dataclass(frozen=True)
class Item:
    sku: str
    name: str
    quantity: int

    def __post_init__(self):
        if not _SKU.match(self.sku):
            raise ValueError(f"invalid sku: {self.sku}")
        if self.quantity < 0:
            raise ValueError("quantity must be non-negative")


class InventoryError(Exception):
    pass


class UnknownSku(InventoryError):
    pass


class InsufficientStock(InventoryError):
    pass
