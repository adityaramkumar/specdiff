---
id: contracts/models
version: "1.0.0"
status: approved
---

## Inventory models

Module `inventory_models.py` defines the shared types.

- `Item`: a frozen dataclass with fields `sku: str`, `name: str`, `quantity: int`.
  - `sku` must match `^[A-Z]{3}-\d{4}$`, else `ValueError(f"invalid sku: {sku}")`.
  - `quantity` must be `>= 0`, else `ValueError("quantity must be non-negative")`.
- `InventoryError(Exception)`: base class for inventory failures.
- `UnknownSku(InventoryError)` and `InsufficientStock(InventoryError)`.
