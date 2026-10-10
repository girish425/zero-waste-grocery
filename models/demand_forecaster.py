"""
Demand Forecasting Mathematical & Machine Learning Engine
GDGoC HITAM · Zero-Waste Grocery Application

Supports:
- Actual uploaded sales transaction history
- Date and product aggregation
- Recent-average and moving-average baseline models
- Scikit-Learn autoregressive machine learning models (Ridge regression with lag features)
- Strict temporal backtest validation (held-out test set with zero future leakage)
- Reliable evaluation metrics (MAE, RMSE, WAPE) only when data sufficiency permits
- Uncertainty bounds (P10, P50, P90) to avoid presenting predictions as certain
- Clear communication of data insufficiency and missing dates without fabrication
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sklearn.linear_model import Ridge

def prepare_daily_sales_series(
    sales_df: pd.DataFrame,
    sku: Optional[str] = None,
    store_name: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Extracts and aggregates actual historical sales for a selected product and store.
    Handles column name variations (date, sales_date, quantity_sold, units_sold, sales).
    Fills calendar gaps with zero sales so time series has continuous daily frequency.
    
    Returns:
    - series_df: DataFrame with ['date', 'quantity_sold']
    - metadata: Dict with data quality diagnostics
    """
    if sales_df is None or sales_df.empty:
        return pd.DataFrame(columns=["date", "quantity_sold"]), {
            "has_data": False,
            "record_count": 0,
            "unique_days": 0,
            "missing_dates_filled": 0,
            "notes": ["No sales data records available in session state."]
        }

    df = sales_df.copy()

    # Identify date column
    date_col = None
    for cand in ["date", "sales_date", "transaction_date", "order_date", "day", "txn_date"]:
        if cand in df.columns:
            date_col = cand
            break
            
    # Identify quantity column
    qty_col = None
    for cand in ["quantity_sold", "units_sold", "sales", "sold_quantity", "sales_qty", "qty_sold"]:
        if cand in df.columns:
            qty_col = cand
            break

    if not date_col or not qty_col:
        return pd.DataFrame(columns=["date", "quantity_sold"]), {
            "has_data": False,
            "record_count": len(df),
            "unique_days": 0,
            "missing_dates_filled": 0,
            "notes": [f"Missing required sales columns: date_col='{date_col}', qty_col='{qty_col}'."]
        }

    # Clean dates and quantities
    df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    df = df[df["_parsed_date"].notna()]
    df["_clean_qty"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0).clip(lower=0)

    # Filter by SKU if provided
    sku_col = None
    for cand in ["sku", "product_id", "sku_id", "item_code"]:
        if cand in df.columns:
            sku_col = cand
            break
            
    if sku and sku_col:
        df = df[df[sku_col].astype(str) == str(sku)]

    # Filter by Store if provided and not 'All Stores'
    store_col = None
    for cand in ["store_name", "store_id", "branch_id", "store"]:
        if cand in df.columns:
            store_col = cand
            break
            
    if store_name and store_name != "All Stores" and store_col:
        df = df[df[store_col].astype(str) == str(store_name)]

    if df.empty:
        return pd.DataFrame(columns=["date", "quantity_sold"]), {
            "has_data": False,
            "record_count": 0,
            "unique_days": 0,
            "missing_dates_filled": 0,
            "notes": [f"No sales transactions match SKU='{sku}' and Store='{store_name}'."]
        }

    # Aggregate daily sales
    daily_agg = df.groupby("_parsed_date")["_clean_qty"].sum().reset_index()
    daily_agg.rename(columns={"_parsed_date": "date", "_clean_qty": "quantity_sold"}, inplace=True)
    daily_agg.sort_values("date", inplace=True)

    # Reindex to continuous calendar dates to prevent temporal gaps
    min_date = daily_agg["date"].min()
    max_date = daily_agg["date"].max()
    full_date_idx = pd.date_range(min_date, max_date, freq="D").date
    
    daily_agg.set_index("date", inplace=True)
    daily_reindexed = daily_agg.reindex(full_date_idx, fill_value=0.0).reset_index()
    daily_reindexed.rename(columns={"index": "date"}, inplace=True)
    
    missing_filled = len(daily_reindexed) - len(daily_agg)
    
    return daily_reindexed, {
        "has_data": True,
        "record_count": len(df),
        "unique_days": len(daily_reindexed),
        "start_date": min_date,
        "end_date": max_date,
        "missing_dates_filled": missing_filled,
        "notes": [
            f"Aggregated {len(df)} transactions into {len(daily_reindexed)} consecutive days.",
            f"Filled {missing_filled} missing dates with 0 sales." if missing_filled > 0 else "Continuous daily sales recorded."
        ]
    }

def run_demand_forecast(
    daily_df: pd.DataFrame,
    horizon_days: int = 7,
    test_split_ratio: float = 0.20
) -> Dict[str, Any]:
    """
    Executes tiered forecasting pipeline based strictly on available history:
    - Tier 1 (< 5 days): Recent Average baseline (held-out validation not possible)
    - Tier 2 (5-13 days): Moving Average baseline with 2-day held-out temporal validation
    - Tier 3 (>= 14 days): Scikit-Learn Autoregressive Machine Learning (Ridge Regression with Lags)
      with held-out test split and reliable MAE / RMSE evaluation.
    
    Zero future leakage: model is trained exclusively on past training partition.
    """
    if daily_df is None or daily_df.empty or len(daily_df) == 0:
        return {
            "model_tier": "NO_DATA",
            "model_name": "No Sales Data",
            "is_ml_model": False,
            "historical_df": pd.DataFrame(columns=["date", "quantity_sold"]),
            "backtest_df": pd.DataFrame(columns=["date", "actual", "predicted"]),
            "forecast_df": pd.DataFrame(columns=["date", "forecast_p50", "forecast_p10", "forecast_p90"]),
            "metrics": {"mae": None, "rmse": None, "wape": None, "evaluation_status": "No historical sales data available."},
            "explanation": "Cannot generate forecasts without historical sales observations.",
            "data_days": 0
        }

    n_days = len(daily_df)
    last_historical_date = daily_df["date"].iloc[-1]
    future_dates = [last_historical_date + timedelta(days=i + 1) for i in range(horizon_days)]

    # ---------------- TIER 1: INSUFFICIENT HISTORY (< 5 DAYS) ----------------
    if n_days < 5:
        mean_sales = float(daily_df["quantity_sold"].mean())
        std_sales = float(daily_df["quantity_sold"].std()) if n_days > 1 else max(1.0, mean_sales * 0.3)
        if np.isnan(std_sales) or std_sales == 0:
            std_sales = max(1.0, mean_sales * 0.3)

        forecast_rows = []
        for f_dt in future_dates:
            p50 = max(0.0, round(mean_sales, 1))
            p10 = max(0.0, round(p50 - 1.28 * std_sales, 1))
            p90 = round(p50 + 1.28 * std_sales, 1)
            forecast_rows.append({
                "date": f_dt,
                "forecast_p50": p50,
                "forecast_p10": p10,
                "forecast_p90": p90
            })

        return {
            "model_tier": "RECENT_AVERAGE",
            "model_name": "Recent Average Baseline",
            "is_ml_model": False,
            "historical_df": daily_df,
            "backtest_df": pd.DataFrame(columns=["date", "actual", "predicted"]),
            "forecast_df": pd.DataFrame(forecast_rows),
            "metrics": {
                "mae": None,
                "rmse": None,
                "wape": None,
                "evaluation_status": f"Insufficient historical records ({n_days} days). Minimum 5 days required for backtesting."
            },
            "explanation": (
                f"With only {n_days} historical sales day(s), complex machine learning or temporal evaluation cannot be reliably computed. "
                f"A recent-average baseline of {mean_sales:.1f} units/day was applied with wide uncertainty bands."
            ),
            "data_days": n_days
        }

    # ---------------- TIER 2: MODERATE HISTORY (5 TO 13 DAYS) ----------------
    if n_days < 14:
        # Hold out the last 2 days as a test set for empirical validation
        test_len = 2
        train_df = daily_df.iloc[:-test_len].copy()
        test_df = daily_df.iloc[-test_len:].copy()

        # Compute 3-day moving average on training set
        rolling_mean = float(train_df["quantity_sold"].tail(3).mean())
        
        # Backtest evaluation on test set (predicting rolling_mean on held-out days)
        test_df["predicted"] = rolling_mean
        test_actual = test_df["quantity_sold"].values
        test_pred = test_df["predicted"].values
        mae = float(np.mean(np.abs(test_actual - test_pred)))
        rmse = float(np.sqrt(np.mean((test_actual - test_pred) ** 2)))
        wape = float(np.sum(np.abs(test_actual - test_pred)) / max(1.0, np.sum(test_actual)))

        # Forecast future points using full dataset 3-day moving average
        full_rolling = float(daily_df["quantity_sold"].tail(3).mean())
        sigma = max(1.0, float(np.std(daily_df["quantity_sold"].values)))
        
        forecast_rows = []
        for f_dt in future_dates:
            dow = f_dt.weekday()
            dow_factor = 1.25 if dow in [4, 5, 6] else 0.95
            p50 = max(0.0, round(full_rolling * dow_factor, 1))
            p10 = max(0.0, round(p50 - 1.28 * sigma, 1))
            p90 = round(p50 + 1.28 * sigma, 1)
            forecast_rows.append({
                "date": f_dt,
                "forecast_p50": p50,
                "forecast_p10": p10,
                "forecast_p90": p90
            })

        backtest_out = test_df[["date", "quantity_sold", "predicted"]].rename(columns={"quantity_sold": "actual"})

        return {
            "model_tier": "MOVING_AVERAGE",
            "model_name": "3-Day Moving Average Baseline with Day-of-Week Seasonality",
            "is_ml_model": False,
            "historical_df": daily_df,
            "backtest_df": backtest_out,
            "forecast_df": pd.DataFrame(forecast_rows),
            "metrics": {
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "wape": round(wape * 100, 1),
                "evaluation_status": f"Evaluated on a 2-day held-out test split ({n_days - 2} days train / 2 days test)."
            },
            "explanation": (
                f"Trained on {n_days} days of sales history. Applied a 3-day moving average baseline with weekend uplift multipliers. "
                f"Model was backtested on the final 2 held-out days with MAE of {mae:.2f} units."
            ),
            "data_days": n_days
        }

    # ---------------- TIER 3: SUFFICIENT HISTORY (>= 14 DAYS) -> SCIKIT-LEARN ML ----------------
    # Hold out the last 3 to 7 days strictly as the held-out test partition
    test_len = min(7, max(3, int(n_days * test_split_ratio)))
    split_idx = n_days - test_len

    # Helper to construct feature vector from historical sequence
    def build_feature_vector(history_vals: List[float], dt: date) -> pd.DataFrame:
        h = pd.Series(history_vals)
        l1 = float(h.iloc[-1])
        l2 = float(h.iloc[-2]) if len(h) >= 2 else l1
        l3 = float(h.iloc[-3]) if len(h) >= 3 else l2
        l7 = float(h.iloc[-7]) if len(h) >= 7 else l3
        rm3 = float(h.tail(3).mean())
        rm7 = float(h.tail(7).mean())
        dow = dt.weekday()
        is_wk = 1 if dow in [4, 5, 6] else 0
        return pd.DataFrame([{
            "lag_1": l1,
            "lag_2": l2,
            "lag_3": l3,
            "lag_7": l7,
            "roll_mean_3": rm3,
            "roll_mean_7": rm7,
            "day_of_week": dow,
            "is_weekend": is_wk
        }])

    # 1. Build Training Dataset strictly from history prior to split_idx
    train_history = list(daily_df["quantity_sold"].iloc[:split_idx].values)
    train_dates = list(daily_df["date"].iloc[:split_idx].values)

    X_train_rows = []
    y_train_rows = []
    # Start at index 7 to have complete lags
    for idx in range(7, len(train_history)):
        sub_hist = train_history[:idx]
        cur_dt = train_dates[idx]
        X_train_rows.append(build_feature_vector(sub_hist, cur_dt).iloc[0].to_dict())
        y_train_rows.append(train_history[idx])

    if len(X_train_rows) < 5:
        # Fallback to moving average if valid feature rows too short
        full_rolling = float(daily_df["quantity_sold"].tail(3).mean())
        sigma = max(1.0, float(np.std(daily_df["quantity_sold"].values)))
        forecast_rows = [{"date": d, "forecast_p50": full_rolling, "forecast_p10": max(0, full_rolling - sigma), "forecast_p90": full_rolling + sigma} for d in future_dates]
        return {
            "model_tier": "MOVING_AVERAGE",
            "model_name": "Moving Average Baseline",
            "is_ml_model": False,
            "historical_df": daily_df,
            "backtest_df": pd.DataFrame(),
            "forecast_df": pd.DataFrame(forecast_rows),
            "metrics": {"mae": None, "rmse": None, "wape": None, "evaluation_status": "Insufficient continuous lag history for ML."},
            "explanation": "Applied moving average fallback due to sparse continuous lag sequence.",
            "data_days": n_days
        }

    X_train = pd.DataFrame(X_train_rows)
    y_train = np.array(y_train_rows)

    # Train backtest model strictly on training partition
    eval_model = Ridge(alpha=5.0)
    eval_model.fit(X_train, y_train)

    # 2. Simulate held-out multi-step forecast recursively without future information
    test_dates = list(daily_df["date"].iloc[split_idx:].values)
    test_actuals = list(daily_df["quantity_sold"].iloc[split_idx:].values)
    
    sim_history = list(train_history)
    backtest_preds = []
    for step in range(test_len):
        step_dt = test_dates[step]
        feat = build_feature_vector(sim_history, step_dt)
        step_pred = float(max(0.0, eval_model.predict(feat)[0]))
        backtest_preds.append(step_pred)
        # In recursive rollout, append step_pred to prevent future lookahead leakage
        sim_history.append(step_pred)

    y_test = np.array(test_actuals)
    y_pred_test = np.array(backtest_preds)

    mae = float(np.mean(np.abs(y_test - y_pred_test)))
    rmse = float(np.sqrt(np.mean((y_test - y_pred_test) ** 2)))
    wape = float(np.sum(np.abs(y_test - y_pred_test)) / max(1.0, np.sum(y_test)))

    backtest_out = pd.DataFrame({
        "date": test_dates,
        "actual": y_test,
        "predicted": np.round(y_pred_test, 1)
    })

    # 3. Train production model on ALL historical data up to date T
    all_history = list(daily_df["quantity_sold"].values)
    all_dates = list(daily_df["date"].values)
    X_full_rows = []
    y_full_rows = []
    for idx in range(7, len(all_history)):
        sub_hist = all_history[:idx]
        cur_dt = all_dates[idx]
        X_full_rows.append(build_feature_vector(sub_hist, cur_dt).iloc[0].to_dict())
        y_full_rows.append(all_history[idx])

    full_model = Ridge(alpha=5.0)
    full_model.fit(pd.DataFrame(X_full_rows), np.array(y_full_rows))

    # 4. Rollout out-of-sample forecast for future horizon
    rolling_future_history = list(all_history)
    forecast_rows = []
    residual_std = max(1.2, float(np.std(y_test - y_pred_test)))

    for step in range(horizon_days):
        f_dt = future_dates[step]
        feat = build_feature_vector(rolling_future_history, f_dt)
        pred_val = float(max(0.0, full_model.predict(feat)[0]))
        rolling_future_history.append(pred_val)

        horizon_uncertainty = residual_std * np.sqrt(1.0 + 0.15 * step)
        p50 = round(pred_val, 1)
        p10 = max(0.0, round(pred_val - 1.28 * horizon_uncertainty, 1))
        p90 = round(pred_val + 1.28 * horizon_uncertainty, 1)

        forecast_rows.append({
            "date": f_dt,
            "forecast_p50": p50,
            "forecast_p10": p10,
            "forecast_p90": p90
        })

    return {
        "model_tier": "SCIKIT_LEARN_ML",
        "model_name": "Scikit-Learn Autoregressive Ridge Regression (Lags 1-7, Rolling Velocity & Seasonality)",
        "is_ml_model": True,
        "historical_df": daily_df,
        "backtest_df": backtest_out,
        "forecast_df": pd.DataFrame(forecast_rows),
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "wape": round(wape * 100, 1),
            "evaluation_status": f"Evaluated on {test_len}-day held-out test partition with 0 lookahead leakage."
        },
        "explanation": (
            f"Trained on {n_days} continuous days of sales records. Engineered autoregressive lag features (t-1, t-2, t-3, t-7), "
            f"3-day and 7-day rolling velocity, and calendar day-of-week seasonality. "
            f"Evaluated on the final {test_len} held-out test days with Mean Absolute Error (MAE) of {mae:.2f} units."
        ),
        "data_days": n_days
    }
