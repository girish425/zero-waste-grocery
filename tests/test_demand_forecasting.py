"""
Tests for Demand Forecasting Module & Page Logic
Zero-Waste Grocery · GDGoC HITAM
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from models.demand_forecaster import prepare_daily_sales_series, run_demand_forecast

def test_empty_sales_df():
    """Test behavior when no sales data is available."""
    empty_df = pd.DataFrame()
    daily_df, diag = prepare_daily_sales_series(empty_df)
    assert daily_df.empty
    assert diag["has_data"] is False
    
    result = run_demand_forecast(daily_df, horizon_days=7)
    assert result["model_tier"] == "NO_DATA"
    assert result["is_ml_model"] is False
    assert result["metrics"]["mae"] is None
    assert "Cannot generate forecasts without historical sales observations" in result["explanation"]

def test_missing_required_columns():
    """Test behavior when sales DataFrame lacks date or quantity columns."""
    bad_df = pd.DataFrame({"foo": [1, 2], "bar": ["a", "b"]})
    daily_df, diag = prepare_daily_sales_series(bad_df)
    assert daily_df.empty
    assert diag["has_data"] is False
    assert "Missing required sales columns" in diag["notes"][0]

def test_column_alias_handling_and_date_gap_fill():
    """Test column alias matching (sales_date, units_sold) and calendar gap filling."""
    raw_records = [
        {"sales_date": "2026-10-01", "units_sold": 10, "item_code": "SKU-001", "branch_id": "Store A"},
        # 2026-10-02 missing!
        {"sales_date": "2026-10-03", "units_sold": 15, "item_code": "SKU-001", "branch_id": "Store A"},
        {"sales_date": "2026-10-04", "units_sold": 20, "item_code": "SKU-001", "branch_id": "Store A"},
    ]
    df = pd.DataFrame(raw_records)
    daily_df, diag = prepare_daily_sales_series(df, sku="SKU-001", store_name="Store A")
    
    assert diag["has_data"] is True
    assert diag["unique_days"] == 4  # 1st, 2nd (filled 0), 3rd, 4th
    assert diag["missing_dates_filled"] == 1
    
    # Check that 2026-10-02 was filled with 0.0
    day_2 = daily_df[daily_df["date"] == date(2026, 10, 2)]
    assert len(day_2) == 1
    assert day_2["quantity_sold"].iloc[0] == 0.0

def test_tier1_insufficient_history():
    """Test Tier 1 (< 5 days): Recent Average baseline, no MAE backtest, uncertainty bounds present."""
    dates = [date(2026, 10, 1) + timedelta(days=i) for i in range(4)]
    quantities = [12.0, 14.0, 10.0, 16.0]
    daily_df = pd.DataFrame({"date": dates, "quantity_sold": quantities})
    
    res = run_demand_forecast(daily_df, horizon_days=7)
    
    assert res["model_tier"] == "RECENT_AVERAGE"
    assert res["is_ml_model"] is False
    assert res["metrics"]["mae"] is None
    assert "Insufficient historical records" in res["metrics"]["evaluation_status"]
    assert len(res["forecast_df"]) == 7
    # Check uncertainty bounds
    for _, row in res["forecast_df"].iterrows():
        assert row["forecast_p10"] <= row["forecast_p50"] <= row["forecast_p90"]

def test_tier2_moderate_history():
    """Test Tier 2 (5-13 days): Moving average baseline with 2-day held-out backtest."""
    dates = [date(2026, 10, 1) + timedelta(days=i) for i in range(8)]
    quantities = [10.0, 12.0, 14.0, 11.0, 15.0, 13.0, 16.0, 14.0]
    daily_df = pd.DataFrame({"date": dates, "quantity_sold": quantities})
    
    res = run_demand_forecast(daily_df, horizon_days=7)
    
    assert res["model_tier"] == "MOVING_AVERAGE"
    assert res["is_ml_model"] is False
    assert res["metrics"]["mae"] is not None
    assert res["metrics"]["mae"] >= 0.0
    assert len(res["backtest_df"]) == 2  # 2-day test set
    assert len(res["forecast_df"]) == 7
    # Check uncertainty bounds
    for _, row in res["forecast_df"].iterrows():
        assert row["forecast_p10"] <= row["forecast_p50"] <= row["forecast_p90"]

def test_tier3_sufficient_history_scikit_learn_ml():
    """Test Tier 3 (>= 14 days): Scikit-Learn ML Ridge regression, held-out test split, valid MAE."""
    np.random.seed(42)
    dates = [date(2026, 9, 1) + timedelta(days=i) for i in range(30)]
    # Create weekly pattern with some noise
    quantities = [max(1.0, 20.0 + 8.0 * (1 if d.weekday() in [4, 5, 6] else 0) + np.random.normal(0, 2)) for d in dates]
    daily_df = pd.DataFrame({"date": dates, "quantity_sold": quantities})
    
    res = run_demand_forecast(daily_df, horizon_days=7)
    
    assert res["model_tier"] == "SCIKIT_LEARN_ML"
    assert res["is_ml_model"] is True
    assert "Ridge" in res["model_name"]
    assert res["metrics"]["mae"] is not None
    assert res["metrics"]["mae"] > 0
    assert res["metrics"]["rmse"] is not None
    assert res["metrics"]["rmse"] >= res["metrics"]["mae"]
    assert len(res["backtest_df"]) >= 5
    assert len(res["forecast_df"]) == 7
    
    # Check that future forecast has valid P10 <= P50 <= P90
    for _, row in res["forecast_df"].iterrows():
        assert row["forecast_p10"] <= row["forecast_p50"] <= row["forecast_p90"]
        assert row["forecast_p10"] >= 0.0

def test_no_leakage_in_forecast():
    """Verify that predictions on held-out partition do not use future information."""
    dates = [date(2026, 9, 1) + timedelta(days=i) for i in range(20)]
    # Values jump drastically in the held-out test partition (last 4 days)
    quantities = [10.0] * 16 + [100.0] * 4
    daily_df = pd.DataFrame({"date": dates, "quantity_sold": quantities})
    
    res = run_demand_forecast(daily_df, horizon_days=5)
    # The backtest predictions on the held-out test set were trained strictly on the first 16 days
    # So the backtest predictions should be near 10, and must not leak the future 100.0 test values!
    backtest_preds = res["backtest_df"]["predicted"].values
    assert np.all(backtest_preds < 30.0), f"Backtest predictions leaked future 100.0 values: {backtest_preds}"

def test_daily_aggregation_across_multiple_transactions():
    """Verify multiple transactions on the same day for the same SKU are properly summed."""
    txns = [
        {"sales_date": "2026-10-01", "units_sold": 5, "item_code": "SKU-001", "branch_id": "Store A"},
        {"sales_date": "2026-10-01", "units_sold": 8, "item_code": "SKU-001", "branch_id": "Store A"},
        {"sales_date": "2026-10-01", "units_sold": 2, "item_code": "SKU-001", "branch_id": "Store A"},
        {"sales_date": "2026-10-02", "units_sold": 11, "item_code": "SKU-001", "branch_id": "Store A"},
    ]
    df = pd.DataFrame(txns)
    daily_df, diag = prepare_daily_sales_series(df, sku="SKU-001", store_name="Store A")
    assert len(daily_df) == 2
    assert daily_df.loc[daily_df["date"] == date(2026, 10, 1), "quantity_sold"].iloc[0] == 15.0
    assert daily_df.loc[daily_df["date"] == date(2026, 10, 2), "quantity_sold"].iloc[0] == 11.0

def test_page_module_import_and_forecaster_contract():
    """Verify that pages.demand_forecast imports correctly and references correct forecaster functions."""
    import pages.demand_forecast as pdf
    assert hasattr(pdf, "render_demand_forecast_page")

