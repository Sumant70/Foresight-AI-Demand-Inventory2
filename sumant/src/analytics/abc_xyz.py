"""
ABC and XYZ Product Classification Module for Foresight AI.
Python Standard Library only.
Implements ABC Analysis (Pareto Revenue Contribution) and
XYZ Analysis (Demand Volatility Coefficient of Variation).
Builds a 9-box strategic inventory decision matrix.
"""

import math
import statistics
from typing import Dict, List, Any


class ABCXYZAnalyzer:
    """Classifies products into ABC (Value) and XYZ (Variability) matrices."""

    # ABC thresholds (cumulative revenue percentages)
    ABC_A_THRESHOLD = 70.0
    ABC_B_THRESHOLD = 90.0

    # XYZ thresholds (Coefficient of Variation: std_dev / mean)
    XYZ_X_THRESHOLD = 0.50  # Stable
    XYZ_Y_THRESHOLD = 0.80  # Variable (above 0.80 is volatile)

    STRATEGIC_ACTIONS = {
        "AX": "High Value, Stable Demand: Automate replenishment (JIT), high service level (98%), minimal safety stock buffer.",
        "AY": "High Value, Moderate Demand: Monitor closely, maintain statistical safety stock, weekly replenishment reviews.",
        "AZ": "High Value, Volatile Demand: Critical risk item. Frequent managerial reviews, flexible supplier contracts, buffer carefully.",
        "BX": "Medium Value, Stable Demand: Standard automated ROP reordering, batch ordering, low administrative effort.",
        "BY": "Medium Value, Moderate Demand: Standard safety stock buffering, monthly reorder reviews.",
        "BZ": "Medium Value, Volatile Demand: Maintain buffer stock, review order frequency, consider safety lead-time.",
        "CX": "Low Value, Stable Demand: Bulk purchase to minimize ordering costs, automatic replenishment, simple visual controls.",
        "CY": "Low Value, Moderate Demand: Bulk ordering, periodic review, higher safety stock without significant capital risk.",
        "CZ": "Low Value, Volatile Demand: Order on demand or maintain very small buffer stock. Avoid excess holding.",
    }

    def __init__(self, processor):
        self.processor = processor
        self.products_analysis = []
        self.matrix_9box = {}
        self.abc_summary = {}
        self.xyz_summary = {}

    def analyze(self):
        """Runs full ABC and XYZ classification on all SKUs."""
        if not self.processor:
            return

        total_revenue = sum(s["revenue"] for s in self.processor.sales)
        sku_metrics = []

        for sku_id, info in self.processor.skus.items():
            sales_list = self.processor.sales_by_sku.get(sku_id, [])
            sku_rev = sum(s["revenue"] for s in sales_list)
            units = [float(s["units_sold"]) for s in sales_list]
            total_units = sum(units)

            # Volatility (Coefficient of Variation)
            mean_demand = total_units / len(units) if units else 0.0
            if len(units) > 1:
                variance = sum((x - mean_demand) ** 2 for x in units) / (len(units) - 1)
                sigma = math.sqrt(variance)
            else:
                sigma = 0.0

            cv = (sigma / mean_demand) if mean_demand > 0 else 0.0

            sku_metrics.append({
                "sku": sku_id,
                "product_name": info["product_name"],
                "category": info["category"],
                "cost_price": info["cost_price"],
                "selling_price": info["selling_price"],
                "total_units": int(total_units),
                "total_revenue": round(sku_rev, 2),
                "mean_daily_demand": round(mean_demand, 2),
                "std_dev_demand": round(sigma, 2),
                "cv": round(cv, 3),
            })

        # --- ABC Classification (Rank by revenue descending) ---
        sku_metrics.sort(key=lambda x: x["total_revenue"], reverse=True)
        running_rev = 0.0
        abc_counts = {"A": 0, "B": 0, "C": 0}
        abc_revenue = {"A": 0.0, "B": 0.0, "C": 0.0}

        for item in sku_metrics:
            running_rev += item["total_revenue"]
            contrib_pct = (item["total_revenue"] / total_revenue * 100.0) if total_revenue > 0 else 0.0
            cum_pct = (running_rev / total_revenue * 100.0) if total_revenue > 0 else 0.0

            if cum_pct <= self.ABC_A_THRESHOLD or (len(sku_metrics) > 0 and item == sku_metrics[0]):
                abc_class = "A"
            elif cum_pct <= self.ABC_B_THRESHOLD:
                abc_class = "B"
            else:
                abc_class = "C"

            item["revenue_contribution_pct"] = round(contrib_pct, 2)
            item["cumulative_revenue_pct"] = round(cum_pct, 2)
            item["abc_class"] = abc_class
            abc_counts[abc_class] += 1
            abc_revenue[abc_class] += item["total_revenue"]

        # --- XYZ Classification (Based on CV) ---
        xyz_counts = {"X": 0, "Y": 0, "Z": 0}

        for item in sku_metrics:
            cv = item["cv"]
            if cv <= self.XYZ_X_THRESHOLD:
                xyz_class = "X"
            elif cv <= self.XYZ_Y_THRESHOLD:
                xyz_class = "Y"
            else:
                xyz_class = "Z"

            item["xyz_class"] = xyz_class
            item["abc_xyz_class"] = f"{item['abc_class']}{xyz_class}"
            item["strategic_recommendation"] = self.STRATEGIC_ACTIONS.get(item["abc_xyz_class"], "Standard review")
            xyz_counts[xyz_class] += 1

        # --- Build 9-Box Grid ---
        matrix = {f"{a}{x}": {"count": 0, "revenue": 0.0, "skus": [], "strategy": self.STRATEGIC_ACTIONS[f"{a}{x}"]}
                  for a in ["A", "B", "C"] for x in ["X", "Y", "Z"]}

        for item in sku_metrics:
            key = item["abc_xyz_class"]
            matrix[key]["count"] += 1
            matrix[key]["revenue"] = round(matrix[key]["revenue"] + item["total_revenue"], 2)
            matrix[key]["skus"].append(item["sku"])

        self.products_analysis = sku_metrics
        self.matrix_9box = matrix
        self.abc_summary = {
            "total_revenue": round(total_revenue, 2),
            "counts": abc_counts,
            "revenue": {k: round(v, 2) for k, v in abc_revenue.items()},
            "revenue_share": {k: round(v / total_revenue * 100.0, 1) for k, v in abc_revenue.items()},
            "thresholds": {"A": f"Top {self.ABC_A_THRESHOLD}%", "B": f"Next {self.ABC_B_THRESHOLD - self.ABC_A_THRESHOLD}%", "C": "Remaining"}
        }
        self.xyz_summary = {
            "counts": xyz_counts,
            "thresholds": {"X": f"CV <= {self.XYZ_X_THRESHOLD} (Stable)", "Y": f"{self.XYZ_X_THRESHOLD} < CV <= {self.XYZ_Y_THRESHOLD} (Moderate)", "Z": f"CV > {self.XYZ_Y_THRESHOLD} (Volatile)"}
        }
        return sku_metrics
