"""
Stockout Risk Module for Foresight AI.
Python Standard Library only.
Calculates estimated burn-down days, projected stockout calendar date,
lead-time replenishment exposure, and risk level.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any


class StockoutEngine:
    """Evaluates stockout exposure and dates across all products."""

    def __init__(self, inventory_intel, forecast_engine=None):
        self.inventory_intel = inventory_intel
        self.forecast_engine = forecast_engine
        self.risk_results = []
        self.risk_summary = {}

    def analyze_stockout_risks(self):
        """Analyzes all products for stockout vulnerability."""
        inv_matrix = self.inventory_intel.inventory_matrix
        if not inv_matrix:
            inv_matrix = self.inventory_intel.compute_inventory_health()

        latest_date_str = self.inventory_intel.kpi_summary.get("latest_snapshot_date", "2025-12-01")
        try:
            base_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
        except ValueError:
            base_date = datetime(2025, 12, 1)

        results = []
        risk_counts = {"High": 0, "Medium": 0, "Low": 0}

        for item in inv_matrix:
            sku = item["sku"]
            current_stock = item["current_stock"]
            lead_time = item["lead_time_days"]
            avg_daily = item["avg_daily_demand"]

            # Pull forecast demand if available (default 14 days)
            forecast_14d = 0.0
            if self.forecast_engine and sku in self.forecast_engine.sku_forecasts:
                sku_f = self.forecast_engine.sku_forecasts[sku]
                forecast_14d = sku_f["horizons"].get("14", {}).get("total_expected_demand", round(avg_daily * 14, 1))
            else:
                forecast_14d = round(avg_daily * 14, 1)

            # Days until stockout calculation
            if current_stock == 0:
                days_until = 0.0
                stockout_date = base_date.strftime("%Y-%m-%d")
                risk_level = "High"
                explanation = "Stock is currently depleted (0 units on hand)."
            elif avg_daily > 0:
                days_until = round(current_stock / avg_daily, 1)
                est_date = base_date + timedelta(days=int(days_until))
                stockout_date = est_date.strftime("%Y-%m-%d")

                # Transparent Risk Level Rule:
                # High Risk: Stockout occurs within Lead Time (replenishment cannot arrive before run-out) OR <= 7 days
                # Medium Risk: Stockout occurs within (Lead Time + 7 days)
                # Low Risk: Stockout is safely beyond (Lead Time + 7 days)
                if days_until <= lead_time or days_until <= 7.0:
                    risk_level = "High"
                    explanation = f"Coverage ({days_until}d) is at or below Lead Time ({lead_time}d). Immediate stockout threat."
                elif days_until <= (lead_time + 7.0):
                    risk_level = "Medium"
                    explanation = f"Coverage ({days_until}d) is approaching Lead Time window ({lead_time}d + 7d buffer)."
                else:
                    risk_level = "Low"
                    explanation = f"Coverage ({days_until}d) is comfortably above Lead Time requirement ({lead_time}d)."
            else:
                days_until = 999.0
                stockout_date = "No projected stockout (zero velocity)"
                risk_level = "Low"
                explanation = "No sales velocity detected in historical period."

            risk_counts[risk_level] += 1

            results.append({
                "sku": sku,
                "product_name": item["product_name"],
                "category": item["category"],
                "current_stock": current_stock,
                "avg_daily_demand": avg_daily,
                "forecast_demand_14d": forecast_14d,
                "lead_time_days": lead_time,
                "days_until_stockout": days_until,
                "estimated_stockout_date": stockout_date,
                "risk_level": risk_level,
                "explanation": explanation,
            })

        # Sort primarily by Risk urgency (High, Medium, Low) then days_until_stockout ascending
        risk_rank = {"High": 1, "Medium": 2, "Low": 3}
        results.sort(key=lambda x: (risk_rank.get(x["risk_level"], 4), x["days_until_stockout"]))

        self.risk_results = results
        self.risk_summary = {
            "total_evaluated": len(results),
            "high_risk_count": risk_counts["High"],
            "medium_risk_count": risk_counts["Medium"],
            "low_risk_count": risk_counts["Low"],
            "disclaimer": "Predictions based on historical sales velocity and expected run-out. Not a guarantee of stockout.",
        }
        return results
