"""
Unit Tests for ABC/XYZ Segmentation, Insights Engine, and CSV Exporter.
Python Standard Library unittest only.
"""

import unittest
from pathlib import Path
from src.data_processing.processor import DataProcessor
from src.inventory.intelligence import InventoryIntelligence
from src.inventory.stockout import StockoutEngine
from src.inventory.reorder import ReorderEngine
from src.analytics.abc_xyz import ABCXYZAnalyzer
from src.analytics.insights import InsightsEngine
from src.analytics.exporter import CSVExporter


class TestAnalytics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.processor = DataProcessor(raw_dir=Path("data/raw"), processed_dir=Path("data/processed")).run_pipeline()
        cls.intel = InventoryIntelligence(cls.processor)
        cls.intel.compute_inventory_health()
        cls.stockout = StockoutEngine(cls.intel)
        cls.stockout.analyze_stockout_risks()
        cls.reorder = ReorderEngine(cls.processor, cls.intel)
        cls.reorder.generate_recommendations()
        cls.abc_xyz = ABCXYZAnalyzer(cls.processor)
        cls.analysis = cls.abc_xyz.analyze()
        cls.insights_engine = InsightsEngine(
            cls.processor, cls.intel, cls.stockout, cls.reorder, cls.abc_xyz
        )

    def test_abc_classification(self):
        self.assertEqual(len(self.analysis), 50)
        a_count = self.abc_xyz.abc_summary["counts"]["A"]
        b_count = self.abc_xyz.abc_summary["counts"]["B"]
        c_count = self.abc_xyz.abc_summary["counts"]["C"]
        self.assertEqual(a_count + b_count + c_count, 50)

    def test_xyz_classification(self):
        x_count = self.abc_xyz.xyz_summary["counts"]["X"]
        y_count = self.abc_xyz.xyz_summary["counts"]["Y"]
        z_count = self.abc_xyz.xyz_summary["counts"]["Z"]
        self.assertEqual(x_count + y_count + z_count, 50)

    def test_9box_matrix(self):
        matrix = self.abc_xyz.matrix_9box
        total_skus = sum(cell["count"] for cell in matrix.values())
        self.assertEqual(total_skus, 50)

    def test_deterministic_insights(self):
        insights = self.insights_engine.generate_insights()
        self.assertGreater(len(insights), 0)
        for ins in insights:
            self.assertIn("headline", ins)
            self.assertIn("detail", ins)
            self.assertIn("severity", ins)

    def test_csv_exporter(self):
        csv_prod = CSVExporter.export_products(self.analysis)
        self.assertIn("SKU,Product_Name", csv_prod)
        self.assertGreater(len(csv_prod.splitlines()), 50)

        csv_inv = CSVExporter.export_inventory(self.intel.inventory_matrix)
        self.assertIn("SKU,Product_Name,Category,Current_Stock", csv_inv)

        csv_so = CSVExporter.export_stockout(self.stockout.risk_results)
        self.assertIn("SKU,Product_Name,Category,Current_Stock", csv_so)

        csv_ro = CSVExporter.export_reorder(self.reorder.recommendations)
        self.assertIn("SKU,Product_Name,Category,Cost_Price", csv_ro)


if __name__ == "__main__":
    unittest.main()
