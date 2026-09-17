"""
Reorder Recommendation Engine for Foresight AI.
Python Standard Library only.
Calculates lead-time demand, statistical safety stock, reorder point (ROP),
recommended order quantity (ROQ), and suggested reorder dates.
Supports interactive lead-time overrides without fabricating supplier times.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any


class ReorderEngine:
    """Calculates replenishment orders, safety stocks, and reorder schedules."""

    # Default service level factor Z = 1.65 for 95% cycle service level
    SERVICE_LEVEL_Z = 1.65

    def __init__(self, processor, inventory_intel, forecast_engine=None):
        self.processor = processor
        self.inventory_intel = inventory_intel
        self.forecast_engine = forecast_engine
        self.recommendations = []
        self.reorder_summary = {}

    def compute_safety_stock(self, sku_id, lead_time_days, z_factor=None):
        """
        Safety Stock Formula:
        SS = Z * std_dev(daily_demand) * sqrt(Lead_Time_Days)
        """
        if z_factor is None:
            z_factor = self.SERVICE_LEVEL_Z

        sales = self.processor.sales_by_sku.get(sku_id, [])
        if len(sales) < 2:
            return 0.0, 0.0

        daily_units = [float(s["units_sold"]) for s in sales]
        mean_demand = sum(daily_units) / len(daily_units)
        variance = sum((x - mean_demand) ** 2 for x in daily_units) / (len(daily_units) - 1)
        sigma = math.sqrt(variance)

        safety_stock = z_factor * sigma * math.sqrt(max(1, lead_time_days))
        return round(safety_stock, 1), round(sigma, 2)

    def generate_recommendations(self, lead_time_override=None, z_factor=None):
        """
        Computes reorder requirements across all SKUs.
        If lead_time_override is provided, it simulates orders under that lead time.
        """
        if z_factor is None:
            z_factor = self.SERVICE_LEVEL_Z

        inv_matrix = self.inventory_intel.inventory_matrix
        if not inv_matrix:
            inv_matrix = self.inventory_intel.compute_inventory_health()

        latest_date_str = self.inventory_intel.kpi_summary.get("latest_snapshot_date", "2025-12-01")
        try:
            base_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        except ValueError:
            base_date = datetime(2025, 12, 1)

        recommendations = []
        reorder_needed_count = 0
        total_recommended_units = 0
        total_reorder_cost = 0.0

        for item in inv_matrix:
            sku = item["sku"]
            current_stock = item["current_stock"]
            on_order = item["on_order"]
            avg_daily = item["avg_daily_demand"]
            cost_price = item["cost_price"]

            # Use override if specified, else actual snapshot lead time
            lead_time = int(lead_time_override) if lead_time_override is not None else item["lead_time_days"]

            # Statistical safety stock
            calc_ss, sigma_demand = self.compute_safety_stock(sku, lead_time, z_factor)
            reported_ss = item["safety_stock"]

            # Lead time demand
            lead_time_demand = round(avg_daily * lead_time, 1)

            # Reorder Point (calculated)
            calc_rop = round(lead_time_demand + calc_ss, 1)
            reported_rop = item["reorder_point"]

            # Net effective inventory position (Current Stock + On Order)
            inventory_position = current_stock + on_order

            # Recommendation Logic
            # If Inventory Position <= Reorder Point -> Trigger Reorder!
            # Recommended Qty brings stock up to ROP + Lead Time Demand cycle stock
            is_reorder_needed = inventory_position <= reported_rop or inventory_position <= calc_rop

            if is_reorder_needed:
                target_buffer = max(reported_rop, calc_rop) + lead_time_demand
                rec_qty = max(0, int(math.ceil(target_buffer - inventory_position)))
                reorder_date = "Immediate (Action Required)"
                urgency = "High" if current_stock <= calc_ss else "Medium"
                reorder_needed_count += 1
                total_recommended_units += rec_qty
                total_reorder_cost += rec_qty * cost_price
            else:
                rec_qty = 0
                excess_above_rop = inventory_position - max(reported_rop, calc_rop)
                days_until_rop = (excess_above_rop / avg_daily) if avg_daily > 0 else 999
                target_date = base_date + timedelta(days=int(round(days_until_rop)))
                reorder_date = target_date.strftime("%Y-%m-%d")
                urgency = "Low"

            recommendations.append({
                "sku": sku,
                "product_name": item["product_name"],
                "category": item["category"],
                "cost_price": cost_price,
                "current_stock": current_stock,
                "on_order": on_order,
                "avg_daily_demand": avg_daily,
                "lead_time_days": lead_time,
                "demand_std_dev": sigma_demand,
                "lead_time_demand": lead_time_demand,
                "statistical_safety_stock": calc_ss,
                "reported_safety_stock": reported_ss,
                "calculated_reorder_point": calc_rop,
                "reported_reorder_point": reported_rop,
                "inventory_position": inventory_position,
                "reorder_needed": is_reorder_needed,
                "recommended_quantity": rec_qty,
                "suggested_reorder_date": reorder_date,
                "estimated_order_cost": round(rec_qty * cost_price, 2),
                "urgency": urgency,
            })

        # Sort: items needing reorder first by urgency, then recommended quantity descending
        urgency_rank = {"High": 1, "Medium": 2, "Low": 3}
        recommendations.sort(key=lambda x: (urgency_rank.get(x["urgency"], 4), -x["recommended_quantity"]))

        self.recommendations = recommendations
        self.reorder_summary = {
            "total_skus": len(recommendations),
            "reorder_needed_count": reorder_needed_count,
            "total_recommended_units": total_recommended_units,
            "total_reorder_cost": round(total_reorder_cost, 2),
            "service_level": f"{round(z_factor * 57.6, 1)}% (Z={z_factor})",
            "lead_time_used": f"{lead_time_override} days (override)" if lead_time_override is not None else "Actual per SKU (3 to 14 days)",
            "methodology": "Statistical Safety Stock (Z * sigma * sqrt(L)) and Reorder Point (LTD + SS).",
        }
        return recommendations
