from dataclasses import replace

from inventory_models import InsufficientStock, Item, UnknownSku


class Inventory:
    def __init__(self):
        self._items: dict[str, Item] = {}

    def add(self, sku: str, name: str, quantity: int) -> Item:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        current = self._items.get(sku)
        if current is None:
            item = Item(sku, name, quantity)
        elif current.name != name:
            raise ValueError(f"name mismatch for {sku}")
        else:
            item = replace(current, quantity=current.quantity + quantity)
        self._items[sku] = item
        return item

    def remove(self, sku: str, quantity: int) -> Item:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        current = self.get(sku)
        if current.quantity < quantity:
            raise InsufficientStock(f"only {current.quantity} of {sku} in stock")
        self._items[sku] = replace(current, quantity=current.quantity - quantity)
        return self._items[sku]

    def get(self, sku: str) -> Item:
        if sku not in self._items:
            raise UnknownSku(f"unknown sku: {sku}")
        return self._items[sku]

    def total_units(self) -> int:
        return sum(item.quantity for item in self._items.values())

    def low_stock(self, threshold: int) -> list[str]:
        return sorted(sku for sku, item in self._items.items() if item.quantity < threshold)
