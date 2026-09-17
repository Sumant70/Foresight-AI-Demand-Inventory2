"""
Time-Series Forecasting Models for Foresight AI.
Python Standard Library only (math, statistics).
Implements Naive, Seasonal Naive, Simple Moving Average (SMA),
Single Exponential Smoothing (SES), and Holt's Linear Trend.
"""

import math
import statistics


class ForecastModel:
    """Base forecast model interface."""
    name = "BaseModel"

    def fit(self, history):
        """History is a list of float/int demand values."""
        raise NotImplementedError

    def predict(self, horizon):
        """Predicts 'horizon' steps into the future."""
        raise NotImplementedError


class NaiveModel(ForecastModel):
    """Persistence Naive: projects the most recent observed value."""
    name = "Naive (Last Value)"

    def __init__(self):
        self.last_val = 0.0

    def fit(self, history):
        if history:
            self.last_val = float(history[-1])
        return self

    def predict(self, horizon):
        return [max(0.0, round(self.last_val, 2)) for _ in range(horizon)]


class SeasonalNaiveModel(ForecastModel):
    """Seasonal Naive: repeats the pattern from 7 days ago (weekly seasonality)."""
    name = "Seasonal Naive (7-Day)"

    def __init__(self, season_length=7):
        self.season_length = season_length
        self.last_season = []

    def fit(self, history):
        if len(history) >= self.season_length:
            self.last_season = [float(x) for x in history[-self.season_length:]]
        elif history:
            self.last_season = [float(history[-1])] * self.season_length
        else:
            self.last_season = [0.0] * self.season_length
        return self

    def predict(self, horizon):
        preds = []
        for h in range(horizon):
            idx = h % self.season_length
            preds.append(max(0.0, round(self.last_season[idx], 2)))
        return preds


class MovingAverageModel(ForecastModel):
    """Simple Moving Average (SMA) over a sliding window k."""
    def __init__(self, window=7):
        self.window = window
        self.name = f"Moving Average (SMA-{window})"
        self.mean_val = 0.0

    def fit(self, history):
        if not history:
            self.mean_val = 0.0
            return self
        recent = history[-self.window:] if len(history) >= self.window else history
        self.mean_val = sum(recent) / len(recent)
        return self

    def predict(self, horizon):
        return [max(0.0, round(self.mean_val, 2)) for _ in range(horizon)]


class SingleExpSmoothingModel(ForecastModel):
    """Single Exponential Smoothing (SES) with optimal alpha selection."""
    name = "Exponential Smoothing (SES)"

    def __init__(self, alpha=None):
        self.alpha = alpha  # If None, optimized during fit
        self.last_level = 0.0
        self.optimal_alpha = 0.3

    def fit(self, history):
        if not history:
            self.last_level = 0.0
            return self

        if len(history) == 1:
            self.last_level = float(history[0])
            return self

        # Grid search best alpha if not specified
        if self.alpha is None:
            best_alpha = 0.3
            best_sse = float("inf")
            for a_cand in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
                sse = 0.0
                level = float(history[0])
                for val in history[1:]:
                    pred = level
                    sse += (val - pred) ** 2
                    level = a_cand * val + (1.0 - a_cand) * level
                if sse < best_sse:
                    best_sse = sse
                    best_alpha = a_cand
            self.optimal_alpha = best_alpha
        else:
            self.optimal_alpha = self.alpha

        # Fit with chosen alpha
        level = float(history[0])
        for val in history[1:]:
            level = self.optimal_alpha * float(val) + (1.0 - self.optimal_alpha) * level
        self.last_level = level
        return self

    def predict(self, horizon):
        return [max(0.0, round(self.last_level, 2)) for _ in range(horizon)]


class HoltLinearModel(ForecastModel):
    """Holt's Double Exponential Smoothing (Level + Linear Trend)."""
    name = "Holt's Linear Trend"

    def __init__(self, alpha=0.3, beta=0.1):
        self.alpha = alpha
        self.beta = beta
        self.level = 0.0
        self.trend = 0.0

    def fit(self, history):
        if not history:
            self.level = 0.0
            self.trend = 0.0
            return self

        if len(history) < 2:
            self.level = float(history[0])
            self.trend = 0.0
            return self

        # Initialize level and trend
        level = float(history[0])
        trend = float(history[1] - history[0])

        for val in history[1:]:
            prev_level = level
            level = self.alpha * float(val) + (1.0 - self.alpha) * (prev_level + trend)
            trend = self.beta * (level - prev_level) + (1.0 - self.beta) * trend

        # Damping extreme trend runaway
        if abs(trend) > abs(level) * 0.2:
            trend = math.copysign(abs(level) * 0.1, trend)

        self.level = level
        self.trend = trend
        return self

    def predict(self, horizon):
        preds = []
        for h in range(1, horizon + 1):
            val = self.level + h * self.trend
            preds.append(max(0.0, round(val, 2)))
        return preds
