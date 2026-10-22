---
id: behaviors/inventory
version: "1.0.0"
status: approved
depends_on:
  - contracts/models
---

## Inventory

Module `inventory.py` exposes class `Inventory`, an in-memory store of `Item`s
(from `inventory_models`) keyed by SKU. Each instance starts empty.

- `add(sku: str, name: str, quantity: int) -> Item`: adds stock.
  - `quantity` must be `> 0`, else `ValueError("quantity must be positive")`.
  - New SKU: store `Item(sku, name, quantity)` (which validates the SKU).
  - Existing SKU: `name` must equal the stored name, else
    `ValueError(f"name mismatch for {sku}")`; otherwise increase its quantity.
  - Returns the stored item after the change.
- `remove(sku: str, quantity: int) -> Item`: removes stock.
  - `quantity` must be `> 0`, else `ValueError("quantity must be positive")`.
  - Unknown SKU: `UnknownSku(f"unknown sku: {sku}")`.
  - Not enough stock: `InsufficientStock(f"only {available} of {sku} in stock")`,
    leaving stock unchanged.
  - An item whose quantity reaches 0 stays in the store with quantity 0.
  - Returns the stored item after the change.
- `get(sku: str) -> Item`: the stored item, or `UnknownSku(f"unknown sku: {sku}")`.
- `total_units() -> int`: sum of all quantities.
- `low_stock(threshold: int) -> list[str]`: SKUs with quantity strictly below
  `threshold`, sorted ascending.
