"""
Forecast Engine for Foresight AI.
Python Standard Library only.
Coordinates model training, holdout evaluation, model selection,
and forward-looking multi-horizon generation (7, 14, 30 days) with confidence intervals.
"""

import math
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from src.forecasting.models import (
    NaiveModel,
    SeasonalNaiveModel,
    MovingAverageModel,
    SingleExpSmoothingModel,
    HoltLinearModel,
)
from src.forecasting.evaluation import evaluate_temporal_holdout, evaluate_forecast


class ForecastEngine:
    """Manages model benchmarks, best-model selection, and horizon projection."""

    def __init__(self, processor=None):
        self.processor = processor
        self.models_benchmark = {}
        self.sku_forecasts = {}
        self.aggregate_forecast = {}
        self.benchmark_summary = {}

    def get_candidate_models(self):
        return [
            NaiveModel(),
            SeasonalNaiveModel(season_length=7),
            MovingAverageModel(window=7),
            MovingAverageModel(window=14),
            MovingAverageModel(window=30),
            SingleExpSmoothingModel(),
            HoltLinearModel(alpha=0.3, beta=0.1),
        ]

    def run_benchmarks(self, val_days=60):
        """
        Evaluates candidate models across each SKU and aggregate demand using a temporal holdout.
        val_days: number of days at the end of the 731-day period to reserve for validation.
        """
        if not self.processor or not self.processor.sales_by_sku:
            return

        dates = self.processor.dates_sequence
        total_days = len(dates)
        if total_days <= val_days:
            val_days = max(7, total_days // 5)

        split_idx = total_days - val_days
        train_dates = dates[:split_idx]
        val_dates = dates[split_idx:]

        sku_results = {}
        model_leaderboard = {m.name: {"mae_sum": 0.0, "wape_sum": 0.0, "rmse_sum": 0.0, "count": 0}
                             for m in self.get_candidate_models()}

        for sku_id, sales_list in self.processor.sales_by_sku.items():
            # Build continuous series
            val_map = {s["date"]: s["units_sold"] for s in sales_list}
            full_series = [float(val_map.get(d, 0)) for d in dates]
            train_series = full_series[:split_idx]
            val_series = full_series[split_idx:]

            best_model_name = None
            best_wape = float("inf")
            evaluated_models = []

            for model_factory in self.get_candidate_models():
                res = evaluate_temporal_holdout(model_factory, train_series, val_series)
                m_name = res["model_name"]
                m_metrics = res["metrics"]

                evaluated_models.append({
                    "name": m_name,
                    "mae": m_metrics["mae"],
                    "rmse": m_metrics["rmse"],
                    "wape": m_metrics["wape"],
                    "mape": m_metrics["mape"],
                    "smape": m_metrics["smape"],
                })

                model_leaderboard[m_name]["mae_sum"] += m_metrics["mae"]
                model_leaderboard[m_name]["wape_sum"] += m_metrics["wape"]
                model_leaderboard[m_name]["rmse_sum"] += m_metrics["rmse"]
                model_leaderboard[m_name]["count"] += 1

                if m_metrics["wape"] < best_wape:
                    best_wape = m_metrics["wape"]
                    best_model_name = m_name

            # Sort evaluated models by WAPE ascending
            evaluated_models.sort(key=lambda x: x["wape"])

            sku_results[sku_id] = {
                "sku": sku_id,
                "best_model": best_model_name,
                "models": evaluated_models,
                "validation_actuals": val_series[-14:],  # sample last 14 days
                "validation_dates": val_dates[-14:],
            }

        # Aggregate leaderboard
        summary_rows = []
        for m_name, stats in model_leaderboard.items():
            cnt = max(1, stats["count"])
            summary_rows.append({
                "model_name": m_name,
                "avg_mae": round(stats["mae_sum"] / cnt, 2),
                "avg_wape": round(stats["wape_sum"] / cnt, 2),
                "avg_rmse": round(stats["rmse_sum"] / cnt, 2),
                "evaluated_skus": cnt,
            })
        summary_rows.sort(key=lambda x: x["avg_wape"])

        self.models_benchmark = sku_results
        self.benchmark_summary = {
            "train_period": f"{train_dates[0]} to {train_dates[-1]} ({len(train_dates)} days)",
            "validation_period": f"{val_dates[0]} to {val_dates[-1]} ({len(val_dates)} days)",
            "total_skus": len(self.processor.sales_by_sku),
            "leaderboard": summary_rows,
            "overall_best_model": summary_rows[0]["model_name"] if summary_rows else "SMA-7",
        }

        # Save benchmark to models/ directory
        models_dir = Path("models")
        models_dir.mkdir(parents=True, exist_ok=True)
        with open(models_dir / "forecast_benchmark.json", "w", encoding="utf-8") as f:
            json.dump(self.benchmark_summary, f, indent=2)

    def generate_all_forecasts(self, horizons=(7, 14, 30)):
        """
        Generates forward-looking forecasts for each SKU across horizons (7, 14, 30 days)
        trained on 100% of historical data (731 days).
        """
        if not self.processor:
            return

        dates = self.processor.dates_sequence
        last_date_str = dates[-1] if dates else "2025-12-31"
        start_dt = datetime.strptime(last_date_str, "%Y-%m-%d") + timedelta(days=1)

        forecast_store = {}

        for sku_id, sales_list in self.processor.sales_by_sku.items():
            val_map = {s["date"]: s["units_sold"] for s in sales_list}
            full_series = [float(val_map.get(d, 0)) for d in dates]

            # Best model determined from benchmark
            best_model_name = self.models_benchmark.get(sku_id, {}).get("best_model", "Moving Average (SMA-7)")
            model = self._instantiate_model(best_model_name)
            model.fit(full_series)

            # Compute historical residual std dev for confidence interval bounds
            # Residual std dev approximation
            tail_len = min(60, len(full_series))
            recent_series = full_series[-tail_len:]
            mean_demand = sum(recent_series) / max(1, len(recent_series))
            variance = sum((x - mean_demand) ** 2 for x in recent_series) / max(1, len(recent_series) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 1.0

            sku_horizon_forecasts = {}
            for h in horizons:
                preds = model.predict(h)
                future_dates = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(h)]

                forecast_points = []
                for dt_str, p in zip(future_dates, preds):
                    lower = max(0.0, round(p - 1.96 * std_dev, 1))
                    upper = round(p + 1.96 * std_dev, 1)
                    forecast_points.append({
                        "date": dt_str,
                        "forecast": round(p, 1),
                        "lower_bound": lower,
                        "upper_bound": upper,
                    })

                total_expected = sum(p["forecast"] for p in forecast_points)
                sku_horizon_forecasts[str(h)] = {
                    "horizon_days": h,
                    "model_used": best_model_name,
                    "total_expected_demand": round(total_expected, 1),
                    "avg_daily_forecast": round(total_expected / h, 2),
                    "points": forecast_points,
                }

            # Also provide recent 30-day historical actuals for chart continuity
            recent_history = [
                {"date": d, "actual": val_map.get(d, 0)}
                for d in dates[-30:]
            ]

            forecast_store[sku_id] = {
                "sku": sku_id,
                "product_name": self.processor.skus.get(sku_id, {}).get("product_name", sku_id),
                "category": self.processor.skus.get(sku_id, {}).get("category", "Uncategorized"),
                "best_model": best_model_name,
                "benchmark_metrics": self.models_benchmark.get(sku_id, {}).get("models", [{}])[0],
                "recent_history": recent_history,
                "horizons": sku_horizon_forecasts,
            }

        self.sku_forecasts = forecast_store

    def _instantiate_model(self, name):
        if "Naive (Last Value)" in name:
            return NaiveModel()
        if "Seasonal Naive" in name:
            return SeasonalNaiveModel(7)
        if "SMA-7" in name:
            return MovingAverageModel(7)
        if "SMA-14" in name:
            return MovingAverageModel(14)
        if "SMA-30" in name:
            return MovingAverageModel(30)
        if "Holt" in name:
            return HoltLinearModel(alpha=0.3, beta=0.1)
        # Default
        return SingleExpSmoothingModel()

    def get_forecast_for_sku(self, sku_id, horizon=14):
        """Fetches forecast details for a specific SKU."""
        data = self.sku_forecasts.get(sku_id)
        if not data:
            return None
        h_key = str(horizon)
        if h_key not in data["horizons"]:
            h_key = "14"
        return {
            "sku": sku_id,
            "product_name": data["product_name"],
            "category": data["category"],
            "best_model": data["best_model"],
            "metrics": data["benchmark_metrics"],
            "recent_history": data["recent_history"],
            "forecast": data["horizons"][h_key],
        }
