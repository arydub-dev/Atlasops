"""Pure inventory math used by both APIs and the synthetic data engine."""
from __future__ import annotations

from app.models import Inventory


def days_of_supply(quantity: int, avg_daily_demand: float) -> float:
    if avg_daily_demand <= 0:
        return 999.0
    return round(quantity / avg_daily_demand, 1)


def inventory_status(item: Inventory) -> str:
    """Classify an inventory line into a status bucket."""
    if item.quantity <= 0:
        return "stockout"
    if item.quantity <= item.reorder_point:
        return "low_stock"
    if item.max_stock and item.quantity >= item.max_stock:
        return "overstock"
    return "ok"


def reorder_recommendation(item: Inventory) -> int:
    """Suggest a reorder quantity to bring stock up to max_stock when below the reorder point."""
    status = inventory_status(item)
    if status in ("low_stock", "stockout"):
        target = item.max_stock or (item.reorder_point * 2)
        return max(target - item.quantity, 0)
    return 0
