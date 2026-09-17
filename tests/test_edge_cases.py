"""
Edge Case and Robustness Tests for Foresight AI.
Python Standard Library unittest only.
Validates zero demand, zero stock, single-item datasets, empty datasets,
and division-by-zero guards across all core engines.
"""

import unittest
from src.forecasting.models import (
    NaiveModel,
    SeasonalNaiveModel,
    MovingAverageModel,
    SingleExpSmoothingModel,
    HoltLinearModel,
)
from src.forecasting.evaluation import calculate_mae, calculate_rmse, calculate_wape, calculate_mape
from src.data_processing.loader import DataLoader


class TestEdgeCases(unittest.TestCase):

    def test_empty_series_forecasting(self):
        models = [
            NaiveModel(),
            SeasonalNaiveModel(),
            MovingAverageModel(),
            SingleExpSmoothingModel(),
            HoltLinearModel(),
        ]
        for m in models:
            m.fit([])
            preds = m.predict(5)
            self.assertEqual(len(preds), 5)
            self.assertEqual(preds, [0.0, 0.0, 0.0, 0.0, 0.0])

    def test_single_element_series(self):
        models = [
            NaiveModel(),
            SeasonalNaiveModel(),
            MovingAverageModel(),
            SingleExpSmoothingModel(),
            HoltLinearModel(),
        ]
        for m in models:
            m.fit([42.0])
            preds = m.predict(3)
            self.assertEqual(len(preds), 3)
            self.assertTrue(all(p >= 0 for p in preds))

    def test_all_zero_demand(self):
        m = MovingAverageModel(window=7)
        m.fit([0, 0, 0, 0, 0, 0, 0])
        preds = m.predict(4)
        self.assertEqual(preds, [0.0, 0.0, 0.0, 0.0])

    def test_metrics_empty_and_zero_division(self):
        self.assertEqual(calculate_mae([], []), 0.0)
        self.assertEqual(calculate_rmse([], []), 0.0)
        self.assertEqual(calculate_wape([], []), 0.0)
        self.assertEqual(calculate_mape([], []), 0.0)

        # All zeros
        self.assertEqual(calculate_wape([0, 0, 0], [0, 0, 0]), 0.0)
        self.assertEqual(calculate_mape([0, 0, 0], [5, 5, 5]), 0.0)

    def test_missing_and_corrupt_data_loader(self):
        self.assertEqual(DataLoader.infer_type(None), "null")
        self.assertEqual(DataLoader.infer_type(""), "null")
        self.assertEqual(DataLoader.infer_type("None"), "null")
        self.assertEqual(DataLoader.infer_type("nan"), "null")
        self.assertEqual(DataLoader.infer_type("NULL"), "null")

    def test_standardize_date_invalid(self):
        self.assertEqual(DataLoader.standardize_date("invalid-date-string"), "invalid-date-string")
        self.assertIsNone(DataLoader.standardize_date(None))
        self.assertIsNone(DataLoader.standardize_date(""))


if __name__ == "__main__":
    unittest.main()
