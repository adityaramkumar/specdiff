import dataclasses

import pytest
from inventory import Inventory
from inventory_models import InsufficientStock, InventoryError, Item, UnknownSku


def test_item_validation():
    with pytest.raises(ValueError, match="^invalid sku: abc-1234$"):
        Item("abc-1234", "Widget", 1)
    with pytest.raises(ValueError, match="^quantity must be non-negative$"):
        Item("ABC-1234", "Widget", -1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        Item("ABC-1234", "Widget", 1).quantity = 5


def test_error_hierarchy():
    assert issubclass(UnknownSku, InventoryError)
    assert issubclass(InsufficientStock, InventoryError)


def test_add_and_accumulate():
    inv = Inventory()
    assert inv.add("ABC-0001", "Bolt", 5) == Item("ABC-0001", "Bolt", 5)
    assert inv.add("ABC-0001", "Bolt", 3).quantity == 8
    with pytest.raises(ValueError, match="^name mismatch for ABC-0001$"):
        inv.add("ABC-0001", "Nut", 1)
    with pytest.raises(ValueError, match="^quantity must be positive$"):
        inv.add("ABC-0002", "Nut", 0)
    with pytest.raises(ValueError, match="^invalid sku: bad$"):
        inv.add("bad", "Nut", 1)


def test_remove():
    inv = Inventory()
    inv.add("ABC-0001", "Bolt", 5)
    assert inv.remove("ABC-0001", 5).quantity == 0
    assert inv.get("ABC-0001").quantity == 0
    with pytest.raises(InsufficientStock, match="^only 0 of ABC-0001 in stock$"):
        inv.remove("ABC-0001", 1)
    with pytest.raises(UnknownSku, match="^unknown sku: XYZ-9999$"):
        inv.remove("XYZ-9999", 1)
    with pytest.raises(ValueError, match="^quantity must be positive$"):
        inv.remove("ABC-0001", -2)


def test_insufficient_stock_leaves_quantity():
    inv = Inventory()
    inv.add("ABC-0001", "Bolt", 2)
    with pytest.raises(InsufficientStock):
        inv.remove("ABC-0001", 3)
    assert inv.get("ABC-0001").quantity == 2


def test_queries_and_isolation():
    inv = Inventory()
    inv.add("BBB-0002", "B", 1)
    inv.add("AAA-0001", "A", 4)
    inv.add("CCC-0003", "C", 10)
    assert inv.total_units() == 15
    assert inv.low_stock(5) == ["AAA-0001", "BBB-0002"]
    assert Inventory().total_units() == 0
    with pytest.raises(UnknownSku, match="^unknown sku: AAA-0002$"):
        inv.get("AAA-0002")
