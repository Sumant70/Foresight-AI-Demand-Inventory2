"""
Unit Tests for Data Processing Pipeline.
Python Standard Library unittest only.
"""

import unittest
from pathlib import Path
from src.data_processing.loader import DataLoader
from src.data_processing.detector import DatasetDetector
from src.data_processing.processor import DataProcessor


class TestDataProcessing(unittest.TestCase):

    def setUp(self):
        self.raw_dir = Path("data/raw")

    def test_type_inference(self):
        self.assertEqual(DataLoader.infer_type("123"), "integer")
        self.assertEqual(DataLoader.infer_type("-45"), "integer")
        self.assertEqual(DataLoader.infer_type("12.34"), "float")
        self.assertEqual(DataLoader.infer_type("-0.5"), "float")
        self.assertEqual(DataLoader.infer_type("2024-01-01"), "date")
        self.assertEqual(DataLoader.infer_type("01-01-2024"), "date")
        self.assertEqual(DataLoader.infer_type(""), "null")
        self.assertEqual(DataLoader.infer_type("None"), "null")
        self.assertEqual(DataLoader.infer_type("N/A"), "null")
        self.assertEqual(DataLoader.infer_type("Chair"), "string")

    def test_date_standardization(self):
        self.assertEqual(DataLoader.standardize_date("2024-05-01"), "2024-05-01")
        self.assertEqual(DataLoader.standardize_date("01-05-2024"), "2024-05-01")
        self.assertIsNone(DataLoader.standardize_date(""))

    def test_raw_files_exist_and_load(self):
        for fname in ["calendar.csv", "sku_master.csv", "sales_daily.csv", "inventory_snapshots.csv"]:
            fpath = self.raw_dir / fname
            self.assertTrue(fpath.exists(), f"Missing file: {fname}")
            data = DataLoader.load_csv(fpath)
            self.assertGreater(data["row_count"], 0)
            self.assertGreater(len(data["headers"]), 0)

    def test_dataset_detector_mapping(self):
        detector = DatasetDetector(raw_dir=self.raw_dir)
        results = detector.run_full_profiling()
        self.assertIn("sales_daily.csv", results["profiles"])
        self.assertIn("sku_master.csv", results["profiles"])
        self.assertIn("inventory_snapshots.csv", results["profiles"])
        self.assertIn("calendar.csv", results["profiles"])

        # Check column mapping
        sales_map = results["mappings"]["sales_daily.csv"]
        self.assertEqual(sales_map["quantity"]["source_column"], "Units_Sold")
        self.assertEqual(sales_map["revenue"]["source_column"], "Revenue")
        self.assertEqual(sales_map["date"]["source_column"], "Date")

        # Location not present in source dataset
        self.assertEqual(sales_map["location"]["status"], "Data not available in source dataset")

    def test_data_processor_pipeline(self):
        proc = DataProcessor(raw_dir=self.raw_dir, processed_dir=Path("data/processed")).run_pipeline()
        self.assertEqual(len(proc.skus), 50)
        self.assertEqual(len(proc.sales), 36550)
        self.assertEqual(len(proc.dates_sequence), 731)
        self.assertEqual(len(proc.inventory_snapshots), 4800)


if __name__ == "__main__":
    unittest.main()
