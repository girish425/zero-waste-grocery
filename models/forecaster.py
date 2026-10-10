"""
Demand Forecasting Mathematical Engine
Generates point forecasts, multi-day horizons, and probabilistic uncertainty bounds (P10, P50, P90).
Incorporates day-of-week seasonality, temperature/weather anomalies, and price elasticity.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Tuple

class PerishableDemandForecaster:
    """
    Forecasting model tailored for fast-moving perishables.
    Features:
    - Base demand level with exponential smoothing
    - Day of week cyclical multipliers
    - Weather sensitivity factors
    - Price elasticity curves (log-log formulation)
    - Quantile estimation (P10, P50, P90)
    """
    
    # Category weather sensitivities: positive means hot weather boosts sales
    CATEGORY_WEATHER_SENSITIVITY = {
        "Produce": 0.04,          # +4% demand per +1°C ambient increase
        "Deli & Ready-to-Eat": 0.05,
        "Bakery": -0.01,
        "Dairy": 0.02,
        "Meat & Seafood": -0.02,
    }
    
    # Default price elasticity of demand (typically -1.1 to -1.6 for grocery perishables)
    PRICE_ELASTICITY = -1.35
    
    def __init__(self):
        pass

    def compute_daily_forecast(
        self,
        base_daily_sales: float,
        target_date: date,
        category: str = "Produce",
        price_discount_pct: float = 0.0,
        temp_delta_c: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculates demand forecast for a single target day including confidence intervals.
        """
        base_sales = float(base_daily_sales) if (base_daily_sales is not None and not pd.isna(base_daily_sales)) else 1.0
        dow = target_date.weekday()
        
        # Day of week seasonality factors
        dow_multipliers = {
            0: 0.90,  # Monday
            1: 0.88,  # Tuesday
            2: 0.95,  # Wednesday
            3: 1.05,  # Thursday
            4: 1.25,  # Friday
            5: 1.50,  # Saturday (peak shopping)
            6: 1.35   # Sunday
        }
        dow_factor = dow_multipliers.get(dow, 1.0)
        
        # Weather impact
        weather_factor = 1.0 + (self.CATEGORY_WEATHER_SENSITIVITY.get(category, 0.0) * temp_delta_c)
        weather_factor = max(0.7, min(1.4, weather_factor))
        
        # Price elasticity impact: Q_new / Q_old = (P_new / P_old) ^ epsilon
        # If discount is 20%, P_ratio = 0.80 -> ratio^(-1.35) = 1.35 -> +35% volume
        if price_discount_pct > 0.0:
            price_ratio = max(0.2, 1.0 - (price_discount_pct / 100.0))
            price_factor = (price_ratio) ** self.PRICE_ELASTICITY
        else:
            price_factor = 1.0
            
        # Median (P50) expected units
        expected_p50 = base_sales * dow_factor * weather_factor * price_factor
        expected_p50 = max(0.5, expected_p50)
        
        # Uncertainty bounds based on standard Poisson/overdispersed variance
        sigma = np.sqrt(expected_p50) * 1.15
        p10 = max(0.0, round(expected_p50 - 1.28 * sigma, 1))
        p90 = round(expected_p50 + 1.28 * sigma, 1)
        
        return {
            "date": target_date,
            "p10": p10,
            "p50": round(expected_p50, 1),
            "p90": p90,
            "dow_factor": round(dow_factor, 2),
            "price_factor": round(price_factor, 2),
            "weather_factor": round(weather_factor, 2)
        }

    def generate_horizon_forecast(
        self,
        base_daily_sales: float,
        start_date: date,
        horizon_days: int = 7,
        category: str = "Produce",
        price_discount_pct: float = 0.0,
        temp_delta_c: float = 0.0
    ) -> pd.DataFrame:
        """
        Generates multi-day forecast trajectory.
        """
        records = []
        for i in range(horizon_days):
            target_dt = start_date + timedelta(days=i)
            fc = self.compute_daily_forecast(
                base_daily_sales=base_daily_sales,
                target_date=target_dt,
                category=category,
                price_discount_pct=price_discount_pct,
                temp_delta_c=temp_delta_c
            )
            records.append({
                "day_index": i + 1,
                "date": target_dt.strftime("%Y-%m-%d"),
                "day_name": target_dt.strftime("%a %b %d"),
                "forecast_p10": fc["p10"],
                "forecast_p50": fc["p50"],
                "forecast_p90": fc["p90"],
                "price_multiplier": fc["price_factor"]
            })
            
        df = pd.DataFrame(records)
        df["cumulative_demand_p50"] = df["forecast_p50"].cumsum()
        return df
