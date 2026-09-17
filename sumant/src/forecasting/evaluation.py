"""
Forecast Evaluation and Metrics for Foresight AI.
Python Standard Library only.
Implements MAE, RMSE, MAPE, sMAPE, and WAPE with strict zero-division guards.
Provides time-series-aware temporal holdout evaluation.
"""

import math
from typing import List, Dict, Any


def calculate_mae(actuals: List[float], predictions: List[float]) -> float:
    """Mean Absolute Error."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    return round(sum(abs(a - p) for a, p in zip(actuals, predictions)) / len(actuals), 3)


def calculate_rmse(actuals: List[float], predictions: List[float]) -> float:
    """Root Mean Squared Error."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    mse = sum((a - p) ** 2 for a, p in zip(actuals, predictions)) / len(actuals)
    return round(math.sqrt(mse), 3)


def calculate_mape(actuals: List[float], predictions: List[float]) -> float:
    """Mean Absolute Percentage Error (computed on non-zero actuals)."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    valid_pairs = [(a, p) for a, p in zip(actuals, predictions) if a > 0]
    if not valid_pairs:
        return 0.0
    mape = sum(abs(a - p) / a for a, p in valid_pairs) / len(valid_pairs)
    return round(mape * 100.0, 2)


def calculate_smape(actuals: List[float], predictions: List[float]) -> float:
    """Symmetric Mean Absolute Percentage Error."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    total = 0.0
    count = 0
    for a, p in zip(actuals, predictions):
        denom = (abs(a) + abs(p)) / 2.0
        if denom > 0:
            total += abs(a - p) / denom
            count += 1
    if count == 0:
        return 0.0
    return round((total / count) * 100.0, 2)


def calculate_wape(actuals: List[float], predictions: List[float]) -> float:
    """
    Weighted Absolute Percentage Error:
    WAPE = sum(|actual - pred|) / sum(actual) * 100
    Highly robust when dealing with sporadic zero-demand days.
    """
    if not actuals or len(actuals) != len(predictions):
        return 0.0
    total_actual = sum(actuals)
    if total_actual == 0:
        return 0.0
    total_abs_err = sum(abs(a - p) for a, p in zip(actuals, predictions))
    return round((total_abs_err / total_actual) * 100.0, 2)


def evaluate_forecast(actuals: List[float], predictions: List[float]) -> Dict[str, float]:
    """Returns dictionary of all standard forecasting metrics."""
    return {
        "mae": calculate_mae(actuals, predictions),
        "rmse": calculate_rmse(actuals, predictions),
        "mape": calculate_mape(actuals, predictions),
        "smape": calculate_smape(actuals, predictions),
        "wape": calculate_wape(actuals, predictions),
        "sample_size": len(actuals),
    }


def evaluate_temporal_holdout(model, train_series: List[float], test_series: List[float]) -> Dict[str, Any]:
    """
    Fits model on train_series and predicts horizon equal to len(test_series).
    Returns metrics and predictions.
    """
    model.fit(train_series)
    preds = model.predict(len(test_series))
    metrics = evaluate_forecast(test_series, preds)
    return {
        "model_name": model.name,
        "metrics": metrics,
        "predictions": preds,
        "actuals": test_series,
    }
