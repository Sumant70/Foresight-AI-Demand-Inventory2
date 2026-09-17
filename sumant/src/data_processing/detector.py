"""
Data Detector & Profiler Module for Foresight AI.
Python Standard Library only.
Automatically inspects raw CSV files, maps columns to business concepts,
profiles distributions, checks for anomalies, nulls, duplicates, and verifies coverage.
"""

import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from src.data_processing.loader import DataLoader


class DatasetDetector:
    """Automated schema discovery, semantic mapping, and data quality profiler."""

    # Conceptual entity patterns for automated matching
    CONCEPT_PATTERNS = {
        "date": ["date", "day", "snapshot_date", "time", "period"],
        "sku": ["sku", "item_code", "product_code", "product_id", "item_id"],
        "product_name": ["product_name", "product", "item_name", "name", "title"],
        "category": ["category", "cat", "product_category", "dept", "department"],
        "subcategory": ["subcategory", "sub_cat", "sub_category", "class"],
        "quantity": ["units_sold", "quantity", "demand", "qty", "sales_units", "volume", "sold"],
        "revenue": ["revenue", "sales", "sales_amount", "gross_sales", "turnover", "total_price"],
        "price": ["selling_price", "price", "unit_price", "retail_price"],
        "cost": ["cost_price", "cost", "unit_cost", "cogs"],
        "gross_margin": ["gross_margin", "gross_margin_per_unit", "margin", "unit_margin"],
        "current_stock": ["current_stock", "stock", "inventory", "on_hand", "qty_on_hand", "stock_level"],
        "on_order": ["on_order", "incoming", "pending_order", "open_order"],
        "lead_time": ["lead_time", "lead_time_days", "supplier_lead_time", "delivery_days"],
        "safety_stock": ["safety_stock", "buffer_stock", "reserve_stock"],
        "reorder_point": ["reorder_point", "rop", "order_point"],
        "inventory_value": ["inventory_value", "stock_value", "holding_value"],
        "promotion": ["promotion", "promo", "is_promotion", "promo_flag", "promotion_event"],
        "holiday": ["holiday", "is_holiday"],
        # Missing dimensions in client dataset:
        "location": ["location", "store", "warehouse", "region", "site", "depot"],
        "supplier": ["supplier", "vendor", "manufacturer"],
    }

    def __init__(self, raw_dir="data/raw"):
        self.raw_dir = Path(raw_dir)
        self.files_detected = {}
        self.column_mapping = {}
        self.quality_report = {}

    def scan_files(self):
        """Discovers all CSV files in raw directory."""
        if not self.raw_dir.exists():
            raise FileNotFoundError(f"Raw data directory does not exist: {self.raw_dir}")
        csv_files = sorted(list(self.raw_dir.glob("*.csv")))
        self.files_detected = {f.name: f for f in csv_files}
        return self.files_detected

    def profile_file(self, filepath):
        """Performs deep profiling on a CSV file."""
        data = DataLoader.load_csv(filepath)
        headers = data["headers"]
        rows = data["rows"]
        row_count = len(rows)

        col_types = {}
        null_counts = {h: 0 for h in headers}
        negative_counts = {h: 0 for h in headers}
        zero_counts = {h: 0 for h in headers}
        unique_values = {h: set() for h in headers}
        min_values = {}
        max_values = {}
        date_values = []

        seen_tuples = set()
        duplicates = 0

        for r in rows:
            # Check row-level duplicate
            row_tup = tuple(r.get(h, "") for h in headers)
            if row_tup in seen_tuples:
                duplicates += 1
            else:
                seen_tuples.add(row_tup)

            for h in headers:
                val_raw = r.get(h, "")
                t = DataLoader.infer_type(val_raw)
                if h not in col_types and t != "null":
                    col_types[h] = t

                if t == "null":
                    null_counts[h] += 1
                else:
                    unique_values[h].add(val_raw)

                    if t in ("integer", "float"):
                        try:
                            num = float(val_raw)
                            if num < 0:
                                negative_counts[h] += 1
                            if num == 0:
                                zero_counts[h] += 1
                            if h not in min_values or num < min_values[h]:
                                min_values[h] = num
                            if h not in max_values or num > max_values[h]:
                                max_values[h] = num
                        except ValueError:
                            pass
                    elif t == "date":
                        iso_dt = DataLoader.standardize_date(val_raw)
                        if iso_dt:
                            date_values.append(iso_dt)

        date_summary = None
        if date_values:
            sorted_dates = sorted(set(date_values))
            date_summary = {
                "min_date": sorted_dates[0],
                "max_date": sorted_dates[-1],
                "distinct_dates": len(sorted_dates),
            }

        return {
            "filename": Path(filepath).name,
            "filepath": str(filepath),
            "row_count": row_count,
            "column_count": len(headers),
            "columns": headers,
            "column_types": col_types,
            "null_counts": null_counts,
            "unique_counts": {h: len(vals) for h, vals in unique_values.items()},
            "negative_counts": negative_counts,
            "zero_counts": zero_counts,
            "min_values": min_values,
            "max_values": max_values,
            "duplicate_rows": duplicates,
            "date_summary": date_summary,
            "encoding": data["encoding"],
            "delimiter": data["delimiter"],
        }

    def map_columns(self, profile):
        """Automatically matches source column headers to business concepts."""
        cols = profile["columns"]
        mapping = {}

        for concept, patterns in self.CONCEPT_PATTERNS.items():
            matched = None
            for p in patterns:
                for c in cols:
                    c_clean = c.lower().strip()
                    if c_clean == p or c_clean.startswith(f"{p}_") or c_clean.endswith(f"_{p}") or p in c_clean:
                        matched = c
                        break
                if matched:
                    break

            if matched:
                mapping[concept] = {
                    "source_column": matched,
                    "inferred_type": profile["column_types"].get(matched, "string"),
                    "status": "Available in source dataset",
                }
            else:
                mapping[concept] = {
                    "source_column": None,
                    "inferred_type": None,
                    "status": "Data not available in source dataset",
                }

        return mapping

    def run_full_profiling(self):
        """Executes full scan and profiling across all raw files."""
        files = self.scan_files()
        profiles = {}
        mappings = {}

        for fname, fpath in files.items():
            prof = self.profile_file(fpath)
            profiles[fname] = prof
            mappings[fname] = self.map_columns(prof)

        self.quality_report = profiles
        self.column_mapping = mappings

        return {
            "files_found": list(files.keys()),
            "profiles": profiles,
            "mappings": mappings,
            "timestamp": datetime.now().isoformat(),
        }
