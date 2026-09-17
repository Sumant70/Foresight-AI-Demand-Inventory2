"""
CSV Exporter Module for Foresight AI.
Python Standard Library only.
Generates RFC 4180 compliant CSV streams for client data downloads.
"""

import io
import csv
from typing import List, Dict, Any


class CSVExporter:
    """Generates standard CSV content strings for business tables."""

    @staticmethod
    def export_products(products_list: List[Dict[str, Any]]) -> str:
        """Exports product master catalog and demand metrics."""
        output = io.StringIO()
        headers = [
            "SKU", "Product_Name", "Category", "Subcategory",
            "Cost_Price", "Selling_Price", "Gross_Margin",
            "Total_Units_Sold", "Total_Revenue", "Current_Stock",
            "Days_of_Inventory", "Status", "ABC_Class", "XYZ_Class"
        ]
        writer = csv.writer(output)
        writer.writerow(headers)

        for p in products_list:
            writer.writerow([
                p.get("sku", ""),
                p.get("product_name", p.get("name", "")),
                p.get("category", ""),
                p.get("subcategory", ""),
                p.get("cost_price", ""),
                p.get("selling_price", ""),
                p.get("gross_margin", ""),
                p.get("total_units_sold", p.get("total_units", "")),
                p.get("total_revenue", ""),
                p.get("current_stock", ""),
                p.get("days_of_inventory", ""),
                p.get("status", p.get("stock_status", "")),
                p.get("abc_class", ""),
                p.get("xyz_class", ""),
            ])
        return output.getvalue()

    @staticmethod
    def export_inventory(inventory_list: List[Dict[str, Any]]) -> str:
        """Exports inventory health matrix."""
        output = io.StringIO()
        headers = [
            "SKU", "Product_Name", "Category", "Current_Stock", "On_Order",
            "Avg_Daily_Demand", "Avg_Weekly_Demand", "Days_of_Inventory",
            "Reorder_Point", "Safety_Stock", "Lead_Time_Days",
            "Inventory_Value", "Status"
        ]
        writer = csv.writer(output)
        writer.writerow(headers)

        for item in inventory_list:
            writer.writerow([
                item.get("sku", ""),
                item.get("product_name", ""),
                item.get("category", ""),
                item.get("current_stock", ""),
                item.get("on_order", ""),
                item.get("avg_daily_demand", ""),
                item.get("avg_weekly_demand", ""),
                item.get("days_of_inventory", ""),
                item.get("reorder_point", ""),
                item.get("safety_stock", ""),
                item.get("lead_time_days", ""),
                item.get("inventory_value", ""),
                item.get("status", ""),
            ])
        return output.getvalue()

    @staticmethod
    def export_stockout(stockout_list: List[Dict[str, Any]]) -> str:
        """Exports stockout risk assessment table."""
        output = io.StringIO()
        headers = [
            "SKU", "Product_Name", "Category", "Current_Stock",
            "Avg_Daily_Demand", "Forecast_Demand_14d", "Lead_Time_Days",
            "Days_Until_Stockout", "Estimated_Stockout_Date", "Risk_Level", "Explanation"
        ]
        writer = csv.writer(output)
        writer.writerow(headers)

        for item in stockout_list:
            writer.writerow([
                item.get("sku", ""),
                item.get("product_name", ""),
                item.get("category", ""),
                item.get("current_stock", ""),
                item.get("avg_daily_demand", ""),
                item.get("forecast_demand_14d", ""),
                item.get("lead_time_days", ""),
                item.get("days_until_stockout", ""),
                item.get("estimated_stockout_date", ""),
                item.get("risk_level", ""),
                item.get("explanation", ""),
            ])
        return output.getvalue()

    @staticmethod
    def export_reorder(reorder_list: List[Dict[str, Any]]) -> str:
        """Exports replenishment purchase orders and recommendations."""
        output = io.StringIO()
        headers = [
            "SKU", "Product_Name", "Category", "Cost_Price",
            "Current_Stock", "On_Order", "Lead_Time_Days",
            "Avg_Daily_Demand", "Lead_Time_Demand", "Statistical_Safety_Stock",
            "Reorder_Point", "Reorder_Needed", "Recommended_Quantity",
            "Suggested_Reorder_Date", "Estimated_Order_Cost", "Urgency"
        ]
        writer = csv.writer(output)
        writer.writerow(headers)

        for item in reorder_list:
            writer.writerow([
                item.get("sku", ""),
                item.get("product_name", ""),
                item.get("category", ""),
                item.get("cost_price", ""),
                item.get("current_stock", ""),
                item.get("on_order", ""),
                item.get("lead_time_days", ""),
                item.get("avg_daily_demand", ""),
                item.get("lead_time_demand", ""),
                item.get("statistical_safety_stock", ""),
                item.get("calculated_reorder_point", item.get("reorder_point", "")),
                "YES" if item.get("reorder_needed") else "NO",
                item.get("recommended_quantity", 0),
                item.get("suggested_reorder_date", ""),
                item.get("estimated_order_cost", 0.0),
                item.get("urgency", ""),
            ])
        return output.getvalue()
