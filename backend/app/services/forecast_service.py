"""
Skill-demand forecasting.

Aggregates job postings by (month, skill), then fits a simple linear-trend
model on monthly counts. If there isn't enough historical coverage, we
say so explicitly rather than inventing a forecast.
"""
import numpy as np
from sqlalchemy.orm import Session

from backend.app.services.analytics_service import skill_trend

MIN_MONTHS_REQUIRED = 3


def forecast_skill(db: Session, skill_name: str, periods_ahead: int = 2) -> dict:
    trend = skill_trend(db, skill_name)  # [{"month": "2026-05", "count": 12}, ...]

    if len(trend) < MIN_MONTHS_REQUIRED:
        return {
            "skill": skill_name,
            "status": "insufficient_data",
            "message": (
                f"Only {len(trend)} month(s) of posting history found for '{skill_name}'. "
                f"At least {MIN_MONTHS_REQUIRED} months are needed to forecast a trend. "
                f"Collect more historical postings (a larger or longer-running dataset) "
                f"to enable forecasting for this skill."
            ),
            "history": trend,
            "forecast": [],
        }

    x = np.arange(len(trend))
    y = np.array([t["count"] for t in trend], dtype=float)

    # Baseline: simple moving average (last 2 points)
    ma_baseline = float(np.mean(y[-2:]))

    # Model: linear trend (least squares)
    coeffs = np.polyfit(x, y, deg=1)
    trend_line = np.polyval(coeffs, x)

    # Evaluate both against the actual history (in-sample, documented limitation
    # for such a small demo dataset)
    mae_ma = float(np.mean(np.abs(y[1:] - y[:-1])))  # naive one-step MA error
    mae_linear = float(np.mean(np.abs(y - trend_line)))
    rmse_linear = float(np.sqrt(np.mean((y - trend_line) ** 2)))

    future_x = np.arange(len(trend), len(trend) + periods_ahead)
    future_y = np.polyval(coeffs, future_x)
    future_y = np.clip(future_y, 0, None)  # counts can't go negative

    last_month = trend[-1]["month"]
    future_months = _next_months(last_month, periods_ahead)

    return {
        "skill": skill_name,
        "status": "ok",
        "history": trend,
        "forecast": [
            {"month": m, "predicted_count": round(float(v), 1)}
            for m, v in zip(future_months, future_y)
        ],
        "model": "linear_trend",
        "evaluation": {
            "naive_moving_average_mae": round(mae_ma, 2),
            "linear_trend_mae": round(mae_linear, 2),
            "linear_trend_rmse": round(rmse_linear, 2),
        },
    }


def _next_months(last_month: str, n: int) -> list[str]:
    year, month = map(int, last_month.split("-"))
    out = []
    for _ in range(n):
        month += 1
        if month > 12:
            month = 1
            year += 1
        out.append(f"{year:04d}-{month:02d}")
    return out
