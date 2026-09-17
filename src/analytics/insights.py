"""
Deterministic AI Business Insights Generator for Foresight AI.
Python Standard Library only.
Synthesizes verified data points from sales, inventory, stockout risks,
reorders, and ABC/XYZ matrices into clear executive intelligence statements.
"""

from typing import Dict, List, Any


class InsightsEngine:
    """Generates grounded, auditable executive business insights."""

    def __init__(self, processor, inventory_intel, stockout_engine, reorder_engine, abc_xyz):
        self.processor = processor
        self.inventory_intel = inventory_intel
        self.stockout_engine = stockout_engine
        self.reorder_engine = reorder_engine
        self.abc_xyz = abc_xyz

    def generate_insights(self) -> List[Dict[str, str]]:
        """Synthesizes deterministic observations across all platform modules."""
        insights = []

        # 1. Revenue Concentration (Pareto Principle)
        if self.abc_xyz.products_analysis:
            total_rev = self.abc_xyz.abc_summary.get("total_revenue", 1)
            top_5 = self.abc_xyz.products_analysis[:5]
            top_5_rev = sum(x["total_revenue"] for x in top_5)
            top_5_pct = round(top_5_rev / total_rev * 100.0, 1)
            top_names = ", ".join([f"{x['sku']} ({x['product_name']})" for x in top_5[:3]])
            insights.append({
                "type": "revenue_concentration",
                "category": "Revenue Driver",
                "severity": "info",
                "headline": f"Top 5 SKUs Drive {top_5_pct}% of Total Revenue",
                "detail": f"High commercial concentration in key products including {top_names}. Maintaining service levels for these SKUs is vital to business revenue stability.",
                "metric": f"{top_5_pct}% concentration",
            })

        # 2. Urgent Stockout Vulnerability
        high_risk_stockouts = [r for r in self.stockout_engine.risk_results if r["risk_level"] == "High"]
        if high_risk_stockouts:
            skus_flagged = [r["sku"] for r in high_risk_stockouts[:3]]
            insights.append({
                "type": "stockout_risk",
                "category": "Supply Vulnerability",
                "severity": "critical",
                "headline": f"{len(high_risk_stockouts)} SKUs Facing Imminent Stockout Threat",
                "detail": f"Coverage for SKUs {', '.join(skus_flagged)} is at or below supplier replenishment lead times. Replenishment orders must be expedited immediately to avoid unfulfilled customer orders.",
                "metric": f"{len(high_risk_stockouts)} SKUs Critical",
            })

        # 3. Capital Tied in Overstock
        overstocked = [i for i in self.inventory_intel.inventory_matrix if i["status"] == "Overstock"]
        if overstocked:
            tied_capital = sum(i["inventory_value"] for i in overstocked)
            insights.append({
                "type": "working_capital",
                "category": "Capital Optimization",
                "severity": "warning",
                "headline": f"${tied_capital:,.2f} Tied in Overstock Inventory",
                "detail": f"{len(overstocked)} SKUs hold more than 45 days of supply. Consider promotional clearance or reallocating purchasing capital to high-velocity lines.",
                "metric": f"${tied_capital/1e6:.2f}M Working Capital",
            })

        # 4. Reorder Replenishment Action
        reorder_needed = [r for r in self.reorder_engine.recommendations if r["reorder_needed"]]
        if reorder_needed:
            total_qty = sum(r["recommended_quantity"] for r in reorder_needed)
            total_cost = sum(r["estimated_order_cost"] for r in reorder_needed)
            insights.append({
                "type": "reorder_action",
                "category": "Procurement Schedule",
                "severity": "warning",
                "headline": f"{len(reorder_needed)} SKUs Require Immediate Purchase Orders",
                "detail": f"Inventory positions have breached verified reorder points (ROP). Recommended purchase volume is {total_qty:,} units with an estimated procurement expenditure of ${total_cost:,.2f}.",
                "metric": f"{total_qty:,} Units Needed",
            })

        # 5. Demand Trend Year-Over-Year
        if self.processor and self.processor.sales:
            sales_2024 = sum(s["units_sold"] for s in self.processor.sales if s["date"].startswith("2024"))
            sales_2025 = sum(s["units_sold"] for s in self.processor.sales if s["date"].startswith("2025"))
            if sales_2024 > 0:
                yoy_growth = round(((sales_2025 - sales_2024) / sales_2024) * 100.0, 2)
                direction = "increased" if yoy_growth >= 0 else "decreased"
                insights.append({
                    "type": "demand_trend",
                    "category": "Market Trajectory",
                    "severity": "info",
                    "headline": f"Demand {direction.capitalize()} by {abs(yoy_growth)}% in 2025 vs 2024",
                    "detail": f"Annual volume transitioned from {sales_2024:,} units in 2024 to {sales_2025:,} units in 2025 across identical product catalogs.",
                    "metric": f"{'+' if yoy_growth >= 0 else ''}{yoy_growth}% YoY",
                })

        # 6. Demand Volatility (XYZ Segmentation)
        z_items = [p for p in self.abc_xyz.products_analysis if p["xyz_class"] == "Z"]
        if z_items:
            insights.append({
                "type": "demand_volatility",
                "category": "Forecasting Volatility",
                "severity": "info",
                "headline": f"{len(z_items)} SKUs Exhibit High Demand Volatility (Class Z)",
                "detail": f"Coefficient of variation (CV) exceeds 0.80 for {len(z_items)} products, indicating irregular purchasing cycles. Statistical safety buffers and dynamic reorder monitoring are recommended.",
                "metric": f"{len(z_items)} Volatile SKUs",
            })

        return insights
