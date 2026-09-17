"""
Unit Tests for Forecasting Engine and Models.
Python Standard Library unittest only.
"""

import unittest
from src.forecasting.models import (
    NaiveModel,
    SeasonalNaiveModel,
    MovingAverageModel,
    SingleExpSmoothingModel,
    HoltLinearModel,
)
from src.forecasting.evaluation import (
    calculate_mae,
    calculate_rmse,
    calculate_mape,
    calculate_smape,
    calculate_wape,
)


class TestForecasting(unittest.TestCase):

    def test_naive_model(self):
        m = NaiveModel()
        m.fit([10, 12, 14, 16])
        preds = m.predict(3)
        self.assertEqual(preds, [16.0, 16.0, 16.0])

    def test_seasonal_naive_model(self):
        m = SeasonalNaiveModel(season_length=3)
        m.fit([1, 2, 3, 4, 5, 6])
        preds = m.predict(4)
        self.assertEqual(preds, [4.0, 5.0, 6.0, 4.0])

    def test_moving_average_model(self):
        m = MovingAverageModel(window=3)
        m.fit([10, 20, 30])
        preds = m.predict(2)
        self.assertEqual(preds, [20.0, 20.0])

    def test_single_exp_smoothing(self):
        m = SingleExpSmoothingModel(alpha=0.5)
        m.fit([10, 20, 10, 20])
        preds = m.predict(3)
        self.assertEqual(len(preds), 3)
        self.assertTrue(all(p > 0 for p in preds))

    def test_holt_linear_model(self):
        m = HoltLinearModel(alpha=0.5, beta=0.2)
        m.fit([10, 12, 14, 16, 18])
        preds = m.predict(3)
        self.assertEqual(len(preds), 3)
        # Should project upward trend
        self.assertGreater(preds[1], preds[0])

    def test_evaluation_metrics(self):
        actuals = [10.0, 20.0, 30.0]
        preds = [12.0, 18.0, 33.0]

        mae = calculate_mae(actuals, preds)
        self.assertAlmostEqual(mae, 2.333, places=2)

        rmse = calculate_rmse(actuals, preds)
        self.assertGreater(rmse, 0)

        wape = calculate_wape(actuals, preds)
        # sum abs err = 2 + 2 + 3 = 7. sum actual = 60. 7/60 * 100 = 11.67%
        self.assertAlmostEqual(wape, 11.67, places=2)

    def test_zero_division_guard(self):
        self.assertEqual(calculate_wape([0, 0], [0, 0]), 0.0)
        self.assertEqual(calculate_mape([0, 0], [1, 2]), 0.0)


if __name__ == "__main__":
    unittest.main()
