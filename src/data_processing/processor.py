"""
Data Processor Module for Foresight AI.
Python Standard Library only.
Cleans, validates, links, and persists normalized datasets into data/processed/.
Provides unified data models for forecasting, inventory intelligence, and executive analytics.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from src.data_processing.loader import DataLoader
from src.data_processing.detector import DatasetDetector


class DataProcessor:
    """ETL Pipeline: Raw ingestion -> Cleaning/Linking -> Processed persistence -> In-memory indexing."""

    def __init__(self, raw_dir="data/raw", processed_dir="data/processed"):
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.detector = DatasetDetector(raw_dir=self.raw_dir)
        self.quality_manifest = {}

        # Master in-memory data store
        self.skus = {}                    # sku_id -> dict
        self.sales = []                   # list of normalized dicts
        self.sales_by_sku = defaultdict(list)  # sku_id -> list of daily sales sorted by date
        self.sales_by_date = defaultdict(lambda: {"units": 0, "revenue": 0.0})
        self.inventory_snapshots = []     # list of snapshot dicts
        self.latest_inventory_by_sku = {} # sku_id -> latest snapshot dict
        self.inventory_by_sku_date = {}   # (sku_id, date) -> dict
        self.calendar = {}                # date -> calendar dict
        self.dates_sequence = []          # sorted list of all sales dates

    def run_pipeline(self):
        """Runs complete ingestion, verification, saving of processed tables, and indexing."""
        print("[DataProcessor] Scanning and profiling raw data...")
        self.quality_manifest = self.detector.run_full_profiling()

        # 1. Process SKU Master
        self._process_sku_master()

        # 2. Process Calendar
        self._process_calendar()

        # 3. Process Sales Daily
        self._process_sales_daily()

        # 4. Process Inventory Snapshots
        self._process_inventory_snapshots()

        # 5. Persist processed datasets and quality report
        self._save_processed_files()

        print(f"[DataProcessor] Ingestion complete: {len(self.skus)} SKUs, {len(self.sales):,} sales rows, "
              f"{len(self.dates_sequence)} unique dates, {len(self.inventory_snapshots):,} inventory records.")
        return self

    def _process_sku_master(self):
        sku_path = self.raw_dir / "sku_master.csv"
        if not sku_path.exists():
            raise FileNotFoundError(f"Missing master file: {sku_path}")

        data = DataLoader.load_csv(sku_path)
        for r in data["rows"]:
            sku_id = r["SKU"].strip()
            self.skus[sku_id] = {
                "sku": sku_id,
                "product_name": r.get("Product_Name", sku_id).strip(),
                "category": r.get("Category", "Uncategorized").strip(),
                "subcategory": r.get("Subcategory", "General").strip(),
                "launch_date": DataLoader.standardize_date(r.get("Launch_Date", "")),
                "cost_price": float(r.get("Cost_Price", 0.0)),
                "selling_price": float(r.get("Selling_Price", 0.0)),
                "gross_margin": float(r.get("Gross_Margin_Per_Unit", 0.0)),
            }

    def _process_calendar(self):
        cal_path = self.raw_dir / "calendar.csv"
        if not cal_path.exists():
            return

        data = DataLoader.load_csv(cal_path)
        for r in data["rows"]:
            dt = DataLoader.standardize_date(r.get("date", ""))
            if dt:
                self.calendar[dt] = {
                    "date": dt,
                    "year": int(r.get("year", dt[:4])),
                    "month": int(r.get("month", dt[5:7])),
                    "quarter": r.get("quarter", ""),
                    "week": int(r.get("week", 1)),
                    "day_of_week": r.get("day_of_week", ""),
                    "is_weekend": int(r.get("is_weekend", 0)),
                    "season": r.get("season", ""),
                    "holiday": r.get("holiday", "None"),
                    "is_holiday": int(r.get("is_holiday", 0)),
                    "promotion_event": r.get("promotion_event", "None"),
                }

    def _process_sales_daily(self):
        sales_path = self.raw_dir / "sales_daily.csv"
        if not sales_path.exists():
            raise FileNotFoundError(f"Missing sales file: {sales_path}")

        data = DataLoader.load_csv(sales_path)
        dates_set = set()

        for r in data["rows"]:
            sku_id = r["SKU"].strip()
            dt = DataLoader.standardize_date(r.get("Date", ""))
            units = int(float(r.get("Units_Sold", 0)))
            revenue = float(r.get("Revenue", 0.0))
            price = float(r.get("Price", 0.0))
            promo = int(float(r.get("Promotion", 0)))

            rec = {
                "date": dt,
                "sku": sku_id,
                "units_sold": units,
                "revenue": revenue,
                "price": price,
                "promotion": promo,
            }

            self.sales.append(rec)
            self.sales_by_sku[sku_id].append(rec)
            self.sales_by_date[dt]["units"] += units
            self.sales_by_date[dt]["revenue"] += revenue
            dates_set.add(dt)

        # Sort each SKU's series by date
        for sku_id in self.sales_by_sku:
            self.sales_by_sku[sku_id].sort(key=lambda x: x["date"])

        self.dates_sequence = sorted(list(dates_set))

    def _process_inventory_snapshots(self):
        inv_path = self.raw_dir / "inventory_snapshots.csv"
        if not inv_path.exists():
            return

        data = DataLoader.load_csv(inv_path)
        all_snapshots = []
        dates_seen = set()

        for r in data["rows"]:
            dt = DataLoader.standardize_date(r.get("Snapshot_Date", ""))
            sku_id = r["SKU"].strip()
            stock = int(float(r.get("Current_Stock", 0)))
            on_order = int(float(r.get("On_Order", 0)))
            lead_time = int(float(r.get("Lead_Time_Days", 7)))
            safety_stock = int(float(r.get("Safety_Stock", 0)))
            rop = int(float(r.get("Reorder_Point", 0)))
            inv_val = float(r.get("Inventory_Value", 0.0))

            rec = {
                "snapshot_date": dt,
                "sku": sku_id,
                "current_stock": stock,
                "on_order": on_order,
                "lead_time_days": lead_time,
                "safety_stock": safety_stock,
                "reorder_point": rop,
                "inventory_value": inv_val,
            }
            all_snapshots.append(rec)
            self.inventory_by_sku_date[(sku_id, dt)] = rec
            dates_seen.add(dt)

        self.inventory_snapshots = all_snapshots
        sorted_dates = sorted(list(dates_seen))
        latest_date = sorted_dates[-1] if sorted_dates else None

        if latest_date:
            for rec in all_snapshots:
                if rec["snapshot_date"] == latest_date:
                    self.latest_inventory_by_sku[rec["sku"]] = rec

    def _save_processed_files(self):
        """Writes processed CSV files and data quality JSON report into data/processed/."""
        # 1. Processed SKU Master
        sku_out = self.processed_dir / "processed_sku_master.csv"
        with open(sku_out, "w", newline="", encoding="utf-8") as f:
            headers = ["SKU", "Product_Name", "Category", "Subcategory", "Launch_Date", "Cost_Price", "Selling_Price", "Gross_Margin"]
            writer = csv.writer(f)
            writer.writerow(headers)
            for sku_id, info in sorted(self.skus.items()):
                writer.writerow([
                    sku_id, info["product_name"], info["category"], info["subcategory"],
                    info["launch_date"], info["cost_price"], info["selling_price"], info["gross_margin"]
                ])

        # 2. Processed Sales Daily
        sales_out = self.processed_dir / "processed_sales_daily.csv"
        with open(sales_out, "w", newline="", encoding="utf-8") as f:
            headers = ["Date", "SKU", "Units_Sold", "Revenue", "Price", "Promotion"]
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in self.sales:
                writer.writerow([r["date"], r["sku"], r["units_sold"], f"{r['revenue']:.2f}", f"{r['price']:.2f}", r["promotion"]])

        # 3. Processed Inventory Snapshots
        inv_out = self.processed_dir / "processed_inventory_snapshots.csv"
        with open(inv_out, "w", newline="", encoding="utf-8") as f:
            headers = ["Snapshot_Date", "SKU", "Current_Stock", "On_Order", "Lead_Time_Days", "Safety_Stock", "Reorder_Point", "Inventory_Value"]
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in self.inventory_snapshots:
                writer.writerow([
                    r["snapshot_date"], r["sku"], r["current_stock"], r["on_order"],
                    r["lead_time_days"], r["safety_stock"], r["reorder_point"], f"{r['inventory_value']:.2f}"
                ])

        # 4. Processed Calendar
        cal_out = self.processed_dir / "processed_calendar.csv"
        with open(cal_out, "w", newline="", encoding="utf-8") as f:
            headers = ["Date", "Year", "Month", "Quarter", "Week", "Day_of_Week", "Is_Weekend", "Season", "Holiday", "Is_Holiday", "Promotion_Event"]
            writer = csv.writer(f)
            writer.writerow(headers)
            for dt, c in sorted(self.calendar.items()):
                writer.writerow([
                    c["date"], c["year"], c["month"], c["quarter"], c["week"],
                    c["day_of_week"], c["is_weekend"], c["season"], c["holiday"],
                    c["is_holiday"], c["promotion_event"]
                ])

        # 5. Quality Report
        report_out = self.processed_dir / "data_quality_report.json"
        with open(report_out, "w", encoding="utf-8") as f:
            json.dump(self.quality_manifest, f, indent=2)

        # Also copy to reports/ directory for executive report accessibility
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        with open(reports_dir / "data_quality_report.json", "w", encoding="utf-8") as f:
            json.dump(self.quality_manifest, f, indent=2)
