"""
FORESIGHT AI - Demand & Inventory Intelligence Platform
Production Backend Server
Built strictly with Python 3 Standard Library.
No external packages, no Node.js, no npm, no SVG.
"""

import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pathlib import Path

from src.data_processing.processor import DataProcessor
from src.forecasting.engine import ForecastEngine
from src.inventory.intelligence import InventoryIntelligence
from src.inventory.stockout import StockoutEngine
from src.inventory.reorder import ReorderEngine
from src.analytics.abc_xyz import ABCXYZAnalyzer
from src.analytics.insights import InsightsEngine
from src.analytics.exporter import CSVExporter

# Directory constants
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


class CoreApplicationState:
    """Master application state holding initialized analytical engines."""

    def __init__(self):
        print("[CoreState] Initializing Foresight AI Intelligence Pipeline...")
        # 1. Ingestion & Normalization
        self.processor = DataProcessor(
            raw_dir=BASE_DIR / "data" / "raw",
            processed_dir=BASE_DIR / "data" / "processed",
        ).run_pipeline()

        # 2. Inventory Intelligence
        self.inventory_intel = InventoryIntelligence(self.processor)
        self.inventory_intel.compute_inventory_health()

        # 3. Forecasting Engine
        self.forecast_engine = ForecastEngine(self.processor)
        self.forecast_engine.run_benchmarks(val_days=60)
        self.forecast_engine.generate_all_forecasts()

        # 4. Stockout Risk Engine
        self.stockout_engine = StockoutEngine(self.inventory_intel, self.forecast_engine)
        self.stockout_engine.analyze_stockout_risks()

        # 5. Reorder Engine
        self.reorder_engine = ReorderEngine(self.processor, self.inventory_intel, self.forecast_engine)
        self.reorder_engine.generate_recommendations()

        # 6. ABC / XYZ Analytics
        self.abc_xyz = ABCXYZAnalyzer(self.processor)
        self.abc_xyz.analyze()

        # 7. AI Business Insights
        self.insights_engine = InsightsEngine(
            self.processor,
            self.inventory_intel,
            self.stockout_engine,
            self.reorder_engine,
            self.abc_xyz,
        )

        # Build merged catalog for Product Analytics
        self.merged_products = self._build_merged_product_catalog()

        # Build executive overview payload
        self.overview_payload = self._build_overview_payload()

        print("[CoreState] Platform ready! All 8 analytical domains fully initialized.")

    def _build_merged_product_catalog(self):
        """Merges SKU master, sales, inventory, ABC/XYZ, and reorder into a unified product record."""
        merged = []
        abc_map = {x["sku"]: x for x in self.abc_xyz.products_analysis}
        inv_map = {x["sku"]: x for x in self.inventory_intel.inventory_matrix}
        stockout_map = {x["sku"]: x for x in self.stockout_engine.risk_results}
        reorder_map = {x["sku"]: x for x in self.reorder_engine.recommendations}

        for sku_id, sku_info in sorted(self.processor.skus.items()):
            abc = abc_map.get(sku_id, {})
            inv = inv_map.get(sku_id, {})
            so = stockout_map.get(sku_id, {})
            ro = reorder_map.get(sku_id, {})

            merged.append({
                "sku": sku_id,
                "product_name": sku_info["product_name"],
                "category": sku_info["category"],
                "subcategory": sku_info["subcategory"],
                "launch_date": sku_info["launch_date"],
                "cost_price": sku_info["cost_price"],
                "selling_price": sku_info["selling_price"],
                "gross_margin": sku_info["gross_margin"],
                "total_units_sold": inv.get("total_units_sold", 0),
                "total_revenue": abc.get("total_revenue", 0.0),
                "avg_daily_demand": inv.get("avg_daily_demand", 0.0),
                "avg_weekly_demand": inv.get("avg_weekly_demand", 0.0),
                "current_stock": inv.get("current_stock", 0),
                "on_order": inv.get("on_order", 0),
                "days_of_inventory": inv.get("days_of_inventory", 0.0),
                "stock_status": inv.get("status", "N/A"),
                "lead_time_days": inv.get("lead_time_days", 7),
                "safety_stock": inv.get("safety_stock", 0),
                "reorder_point": inv.get("reorder_point", 0),
                "inventory_value": inv.get("inventory_value", 0.0),
                "stockout_risk": so.get("risk_level", "Low"),
                "days_until_stockout": so.get("days_until_stockout", 999),
                "estimated_stockout_date": so.get("estimated_stockout_date", "N/A"),
                "reorder_needed": ro.get("reorder_needed", False),
                "recommended_order_quantity": ro.get("recommended_quantity", 0),
                "suggested_reorder_date": ro.get("suggested_reorder_date", "N/A"),
                "abc_class": abc.get("abc_class", "C"),
                "xyz_class": abc.get("xyz_class", "X"),
                "abc_xyz_class": abc.get("abc_xyz_class", "CX"),
                "cv": abc.get("cv", 0.0),
                "best_forecast_model": self.forecast_engine.models_benchmark.get(sku_id, {}).get("best_model", "SMA-7"),
                "location_dimension": "Data not available in source dataset",
                "supplier_dimension": "Data not available in source dataset",
            })

        merged.sort(key=lambda x: x["total_revenue"], reverse=True)
        return merged

    def _build_overview_payload(self):
        """Constructs high-level executive payload for the Overview page."""
        total_units = sum(s["units_sold"] for s in self.processor.sales)
        total_revenue = sum(s["revenue"] for s in self.processor.sales)
        dates = self.processor.dates_sequence

        # Monthly series
        monthly_map = {}
        for s in self.processor.sales:
            mo = s["date"][:7]
            if mo not in monthly_map:
                monthly_map[mo] = {"month": mo, "units": 0, "revenue": 0.0}
            monthly_map[mo]["units"] += s["units_sold"]
            monthly_map[mo]["revenue"] += s["revenue"]

        sorted_monthly = [
            {
                "month": m,
                "units": monthly_map[m]["units"],
                "revenue": round(monthly_map[m]["revenue"], 2),
            }
            for m in sorted(monthly_map.keys())
        ]

        # Category series
        cat_map = {}
        for s in self.processor.sales:
            cat = self.processor.skus.get(s["sku"], {}).get("category", "Uncategorized")
            if cat not in cat_map:
                cat_map[cat] = {"category": cat, "units": 0, "revenue": 0.0, "skus": set()}
            cat_map[cat]["units"] += s["units_sold"]
            cat_map[cat]["revenue"] += s["revenue"]
            cat_map[cat]["skus"].add(s["sku"])

        category_series = []
        for cat, val in cat_map.items():
            category_series.append({
                "category": cat,
                "units": val["units"],
                "revenue": round(val["revenue"], 2),
                "sku_count": len(val["skus"]),
                "revenue_share": round((val["revenue"] / total_revenue * 100.0) if total_revenue > 0 else 0, 1),
            })
        category_series.sort(key=lambda x: x["revenue"], reverse=True)

        inv_summary = self.inventory_intel.kpi_summary
        stockout_summary = self.stockout_engine.risk_summary
        reorder_summary = self.reorder_engine.reorder_summary

        return {
            "kpis": {
                "total_products": len(self.processor.skus),
                "total_skus": len(self.processor.skus),
                "total_records": len(self.processor.sales),
                "total_units_sold": total_units,
                "total_sales_revenue": round(total_revenue, 2),
                "date_range": f"{dates[0]} to {dates[-1]}",
                "min_date": dates[0],
                "max_date": dates[-1],
                "total_days": len(dates),
                "avg_daily_demand": round(total_units / len(dates), 2) if dates else 0,
                "current_inventory_units": inv_summary["total_current_stock"],
                "current_inventory_value": inv_summary["total_inventory_value"],
                "healthy_stock_count": inv_summary["status_counts"]["Healthy"],
                "low_stock_count": inv_summary["status_counts"]["Low Stock"],
                "critical_stock_count": inv_summary["status_counts"]["Critical"],
                "overstock_count": inv_summary["status_counts"]["Overstock"],
                "out_of_stock_count": inv_summary["status_counts"]["Out of Stock"],
                "high_stockout_risk_count": stockout_summary["high_risk_count"],
                "reorder_needed_count": reorder_summary["reorder_needed_count"],
                "location_dimension": "Data not available in source dataset",
                "supplier_dimension": "Data not available in source dataset",
            },
            "monthly_sales": sorted_monthly,
            "category_breakdown": category_series,
            "top_products": self.merged_products[:10],
            "insights": self.insights_engine.generate_insights(),
            "stock_health_distribution": inv_summary["status_counts"],
            "stockout_risk_distribution": {
                "High": stockout_summary["high_risk_count"],
                "Medium": stockout_summary["medium_risk_count"],
                "Low": stockout_summary["low_risk_count"],
            },
        }


# Global initialized application instance
app_state = CoreApplicationState()


class ForesightHTTPHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP Server delivering HTML, CSS, JS, and full REST API."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        url = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        try:
            # Static & Template Routes
            if url == "/" or url == "/index.html":
                self.serve_file(TEMPLATES_DIR / "index.html", "text/html; charset=utf-8")
            elif url == "/static/style.css":
                self.serve_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            elif url == "/static/app.js":
                self.serve_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")

            # REST API Routes
            elif url == "/api/summary" or url == "/api/overview":
                self.serve_json(app_state.overview_payload)

            elif url == "/api/products":
                # Filter by sku or category if requested
                sku_q = query_params.get("sku", [None])[0]
                cat_q = query_params.get("category", [None])[0]
                prods = app_state.merged_products
                if sku_q:
                    prods = [p for p in prods if p["sku"].lower() == sku_q.lower()]
                if cat_q and cat_q != "ALL":
                    prods = [p for p in prods if p["category"].lower() == cat_q.lower()]
                self.serve_json(prods)

            elif url == "/api/sales":
                # Detailed sales aggregations
                period = query_params.get("period", ["monthly"])[0]
                if period == "daily":
                    daily_list = [
                        {"date": d, "units": app_state.processor.sales_by_date[d]["units"], "revenue": round(app_state.processor.sales_by_date[d]["revenue"], 2)}
                        for d in app_state.processor.dates_sequence
                    ]
                    self.serve_json(daily_list)
                else:
                    self.serve_json({
                        "monthly": app_state.overview_payload["monthly_sales"],
                        "categories": app_state.overview_payload["category_breakdown"],
                        "date_range": app_state.overview_payload["kpis"]["date_range"],
                        "total_units": app_state.overview_payload["kpis"]["total_units_sold"],
                        "total_revenue": app_state.overview_payload["kpis"]["total_sales_revenue"],
                    })

            elif url == "/api/inventory":
                self.serve_json({
                    "summary": app_state.inventory_intel.kpi_summary,
                    "matrix": app_state.inventory_intel.inventory_matrix,
                })

            elif url == "/api/forecast":
                sku = query_params.get("sku", ["SKU001"])[0]
                horizon = int(query_params.get("horizon", [14])[0])
                forecast_res = app_state.forecast_engine.get_forecast_for_sku(sku, horizon)
                if forecast_res:
                    self.serve_json(forecast_res)
                else:
                    self.serve_json({"error": "SKU not found", "available_skus": list(app_state.processor.skus.keys())})

            elif url == "/api/stockout":
                self.serve_json({
                    "summary": app_state.stockout_engine.risk_summary,
                    "risks": app_state.stockout_engine.risk_results,
                })

            elif url == "/api/reorder":
                lead_override = query_params.get("lead_time", [None])[0]
                if lead_override is not None:
                    try:
                        lead_override = int(lead_override)
                        recs = app_state.reorder_engine.generate_recommendations(lead_time_override=lead_override)
                        summary = app_state.reorder_engine.reorder_summary
                    except ValueError:
                        recs = app_state.reorder_engine.recommendations
                        summary = app_state.reorder_engine.reorder_summary
                else:
                    recs = app_state.reorder_engine.recommendations
                    summary = app_state.reorder_engine.reorder_summary
                self.serve_json({"summary": summary, "recommendations": recs})

            elif url == "/api/analytics" or url == "/api/abc_xyz":
                self.serve_json({
                    "abc_summary": app_state.abc_xyz.abc_summary,
                    "xyz_summary": app_state.abc_xyz.xyz_summary,
                    "matrix_9box": app_state.abc_xyz.matrix_9box,
                    "products": app_state.abc_xyz.products_analysis,
                })

            elif url == "/api/insights":
                self.serve_json(app_state.insights_engine.generate_insights())

            elif url == "/api/quality":
                self.serve_json(app_state.processor.quality_manifest)

            elif url == "/api/models":
                self.serve_json(app_state.forecast_engine.benchmark_summary)

            # CSV Export Endpoints
            elif url.startswith("/api/export/"):
                export_type = url.replace("/api/export/", "")
                if export_type == "products":
                    csv_str = CSVExporter.export_products(app_state.merged_products)
                    self.serve_csv_download(csv_str, "foresight_products_catalog.csv")
                elif export_type == "inventory":
                    csv_str = CSVExporter.export_inventory(app_state.inventory_intel.inventory_matrix)
                    self.serve_csv_download(csv_str, "foresight_inventory_health.csv")
                elif export_type == "stockout":
                    csv_str = CSVExporter.export_stockout(app_state.stockout_engine.risk_results)
                    self.serve_csv_download(csv_str, "foresight_stockout_risks.csv")
                elif export_type == "reorder":
                    csv_str = CSVExporter.export_reorder(app_state.reorder_engine.recommendations)
                    self.serve_csv_download(csv_str, "foresight_reorder_recommendations.csv")
                else:
                    self.send_error(400, f"Unsupported export type: {export_type}")

            elif url == "/api/health":
                self.serve_json({
                    "status": "online",
                    "service": "FORESIGHT AI Platform Engine",
                    "timestamp": datetime.now().isoformat(),
                    "skus": len(app_state.processor.skus),
                    "environment": "Python 3 Standard Library",
                })

            else:
                self.send_error(404, "Endpoint or asset not found")

        except Exception as e:
            print(f"[Foresight HTTP Error] {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def serve_file(self, filepath, content_type):
        if not filepath.exists():
            self.send_error(404, f"File not found: {filepath.name}")
            return
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def serve_json(self, data_obj):
        json_bytes = json.dumps(data_obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(json_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json_bytes)

    def serve_csv_download(self, csv_str, filename):
        csv_bytes = csv_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

    def log_message(self, format, *args):
        # Keep server log clean
        pass


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, ForesightHTTPHandler)
    print("=" * 66)
    print("  FORESIGHT AI - Demand & Inventory Intelligence Platform")
    print(f"  Server active at: http://localhost:{port}")
    print("  Runtime: Python 3 Standard Library (Offline, Zero-dependency, No SVG)")
    print("=" * 66)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Foresight AI] Server stopped by operator.")


if __name__ == "__main__":
    run_server()
