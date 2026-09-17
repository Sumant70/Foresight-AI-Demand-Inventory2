"""
Unit Tests for Inventory Intelligence, Stockout Risk, and Reorders.
Python Standard Library unittest only.
"""

import unittest
from pathlib import Path
from src.data_processing.processor import DataProcessor
from src.inventory.intelligence import InventoryIntelligence
from src.inventory.stockout import StockoutEngine
from src.inventory.reorder import ReorderEngine


class TestInventory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.processor = DataProcessor(raw_dir=Path("data/raw"), processed_dir=Path("data/processed")).run_pipeline()
        cls.intel = InventoryIntelligence(cls.processor)
        cls.intel.compute_inventory_health()
        cls.stockout = StockoutEngine(cls.intel)
        cls.stockout.analyze_stockout_risks()
        cls.reorder = ReorderEngine(cls.processor, cls.intel)
        cls.reorder.generate_recommendations()

    def test_inventory_matrix_metrics(self):
        matrix = self.intel.inventory_matrix
        self.assertEqual(len(matrix), 50)
        for item in matrix:
            self.assertIn("sku", item)
            self.assertIn("current_stock", item)
            self.assertIn("days_of_inventory", item)
            self.assertIn(item["status"], ["Healthy", "Low Stock", "Critical", "Overstock", "Out of Stock"])

    def test_stockout_risk_assessment(self):
        risks = self.stockout.risk_results
        self.assertEqual(len(risks), 50)
        for r in risks:
            self.assertIn(r["risk_level"], ["High", "Medium", "Low"])
            self.assertGreaterEqual(r["days_until_stockout"], 0)

    def test_reorder_recommendations(self):
        recs = self.reorder.recommendations
        self.assertEqual(len(recs), 50)
        for r in recs:
            self.assertIn("reorder_needed", r)
            self.assertIn("recommended_quantity", r)
            self.assertIn("statistical_safety_stock", r)
            if r["reorder_needed"]:
                self.assertGreater(r["recommended_quantity"], 0)
                self.assertGreater(r["estimated_order_cost"], 0)

    def test_lead_time_override_simulation(self):
        recs_sim = self.reorder.generate_recommendations(lead_time_override=21)
        # With 21 days lead time, more items should trigger reorders
        sim_count = sum(1 for r in recs_sim if r["reorder_needed"])
        self.assertGreater(sim_count, 0)


if __name__ == "__main__":
    unittest.main()
