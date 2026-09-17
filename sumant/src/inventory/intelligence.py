"""
Inventory Intelligence Module for Foresight AI.
Python Standard Library only.
Calculates stock velocity, days of inventory remaining (DOI),
inventory status classification, and capital valuation.
"""

import math
import statistics
from typing import Dict, List, Any


class InventoryIntelligence:
    """Computes inventory velocity, coverage days, and health statuses."""

    # Default configurable thresholds (in days of inventory)
    CRITICAL_THRESHOLD_DAYS = 7
    LOW_STOCK_THRESHOLD_DAYS = 15
    HEALTHY_MAX_DAYS = 45

    def __init__(self, processor):
        self.processor = processor
        self.inventory_matrix = []
        self.kpi_summary = {}

    def compute_inventory_health(self):
        """Analyzes all 50 SKUs using latest inventory snapshot (2025-12-01)."""
        if not self.processor:
            return []

        matrix = []
        total_stock = 0
        total_value = 0.0
        status_counts = {
            "Healthy": 0,
            "Low Stock": 0,
            "Critical": 0,
            "Overstock": 0,
            "Out of Stock": 0,
        }

        total_days = len(self.processor.dates_sequence)

        for sku_id, sku_info in sorted(self.processor.skus.items()):
            # Latest snapshot
            inv = self.processor.latest_inventory_by_sku.get(sku_id, {})
            current_stock = inv.get("current_stock", 0)
            on_order = inv.get("on_order", 0)
            lead_time = inv.get("lead_time_days", 7)
            safety_stock = inv.get("safety_stock", 0)
            reorder_point = inv.get("reorder_point", 0)
            inv_value = inv.get("inventory_value", current_stock * sku_info["cost_price"])

            total_stock += current_stock
            total_value += inv_value

            # Historical sales demand velocity
            sales_list = self.processor.sales_by_sku.get(sku_id, [])
            total_units_sold = sum(s["units_sold"] for s in sales_list)
            avg_daily_demand = round(total_units_sold / total_days, 2) if total_days > 0 else 0.0
            avg_weekly_demand = round(avg_daily_demand * 7.0, 1)

            # Days of Inventory (DOI)
            if current_stock == 0:
                doi = 0.0
                status = "Out of Stock"
            elif avg_daily_demand > 0:
                doi = round(current_stock / avg_daily_demand, 1)
                if doi <= self.CRITICAL_THRESHOLD_DAYS:
                    status = "Critical"
                elif doi <= self.LOW_STOCK_THRESHOLD_DAYS:
                    status = "Low Stock"
                elif doi > self.HEALTHY_MAX_DAYS:
                    status = "Overstock"
                else:
                    status = "Healthy"
            else:
                doi = 999.0
                status = "Overstock"

            status_counts[status] += 1

            matrix.append({
                "sku": sku_id,
                "product_name": sku_info["product_name"],
                "category": sku_info["category"],
                "subcategory": sku_info["subcategory"],
                "cost_price": sku_info["cost_price"],
                "selling_price": sku_info["selling_price"],
                "current_stock": current_stock,
                "on_order": on_order,
                "lead_time_days": lead_time,
                "safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "inventory_value": round(inv_value, 2),
                "total_units_sold": total_units_sold,
                "avg_daily_demand": avg_daily_demand,
                "avg_weekly_demand": avg_weekly_demand,
                "days_of_inventory": doi,
                "status": status,
            })

        self.inventory_matrix = matrix
        self.kpi_summary = {
            "total_skus": len(matrix),
            "total_current_stock": total_stock,
            "total_inventory_value": round(total_value, 2),
            "status_counts": status_counts,
            "latest_snapshot_date": self.processor.inventory_snapshots[-1]["snapshot_date"] if self.processor.inventory_snapshots else "N/A",
            "thresholds": {
                "critical_days": self.CRITICAL_THRESHOLD_DAYS,
                "low_stock_days": self.LOW_STOCK_THRESHOLD_DAYS,
                "overstock_days": self.HEALTHY_MAX_DAYS,
            }
        }
        return matrix
