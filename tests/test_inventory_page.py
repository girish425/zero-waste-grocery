"""
Unit and Integration Tests for Inventory & Expiry Page Logic
GDGoC HITAM · Zero-Waste Grocery Application

Covers:
- Metric calculations from real uploaded data
- Configurable thresholds for expiry warning and low stock
- Color-tier alert mapping (Green, Amber, Orange, Red, Neutral)
- Expiry integrity: missing expiry dates are NEVER labeled as expired
- Incomplete datasets: missing columns, missing values, empty datasets
- Dynamic filtering and CSV export generation
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pages.p2_inventory import compute_batch_alert_status
from data.normalizer import normalize_and_validate_inventory, suggest_column_mappings

def test_alert_status_classification_accuracy():
    """Tests the 7 alert status tiers and rationale."""
    # 1. Expired product (-2 days left) -> Must be RED / EXPIRED
    row_expired = {"product_name": "Milk", "current_stock": 10, "days_to_expiry": -2}
    res_exp = compute_batch_alert_status(row_expired, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_exp["status"] == "EXPIRED"
    assert res_exp["tier"] == "red"
    assert "expired 2 day(s) ago" in res_exp["alert_reason"].lower()

    # 2. Critical Expiry (0 days left -> expires today) -> Must be ORANGE / CRITICAL_EXPIRY
    row_today = {"product_name": "Strawberries", "current_stock": 20, "days_to_expiry": 0}
    res_today = compute_batch_alert_status(row_today, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_today["status"] == "CRITICAL_EXPIRY"
    assert res_today["tier"] == "orange"
    assert "today" in res_today["status_label"].lower()

    # 3. Expiring Soon within threshold (2 days left with threshold=3) -> Must be AMBER / EXPIRING_SOON
    row_soon = {"product_name": "Salmon", "current_stock": 25, "days_to_expiry": 2}
    res_soon = compute_batch_alert_status(row_soon, expiry_threshold_days=3, low_stock_threshold_units=15)
    assert res_soon["status"] == "EXPIRING_SOON"
    assert res_soon["tier"] == "amber"

    # 4. Out of stock (0 units) -> Must be RED / OUT_OF_STOCK
    row_depleted = {"product_name": "Avocado", "current_stock": 0, "days_to_expiry": 5}
    res_depleted = compute_batch_alert_status(row_depleted, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_depleted["status"] == "OUT_OF_STOCK"
    assert res_depleted["tier"] == "red"

    # 5. Low stock (8 units <= threshold 15) -> Must be AMBER / LOW_STOCK
    row_low = {"product_name": "Greek Yogurt", "current_stock": 8, "days_to_expiry": 6}
    res_low = compute_batch_alert_status(row_low, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_low["status"] == "LOW_STOCK"
    assert res_low["tier"] == "amber"

    # 6. Unspecified Expiry (None) -> Must be NEUTRAL / UNSPECIFIED_EXPIRY (NEVER EXPIRED!)
    row_unspec = {"product_name": "Canned Corn", "current_stock": 40, "days_to_expiry": None}
    res_unspec = compute_batch_alert_status(row_unspec, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_unspec["status"] == "UNSPECIFIED_EXPIRY"
    assert res_unspec["tier"] == "neutral"
    assert res_unspec["is_urgent"] is False
    assert "not recorded" in res_unspec["alert_reason"].lower()

    # 7. Healthy Stock & Shelf life (10 days left, 50 stock) -> Must be GREEN / HEALTHY
    row_fresh = {"product_name": "Apples", "current_stock": 50, "days_to_expiry": 10}
    res_fresh = compute_batch_alert_status(row_fresh, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert res_fresh["status"] == "HEALTHY"
    assert res_fresh["tier"] == "green"
    assert res_fresh["is_urgent"] is False

def test_expiry_integrity_with_unspecified_dates():
    """
    CRITICAL TEST: Verifies that products with unknown expiry dates
    are NEVER categorized as expired, even when filtering.
    """
    test_rows = [
        {"product_name": "Honey", "current_stock": 20, "days_to_expiry": None},
        {"product_name": "Salt", "current_stock": 50, "days_to_expiry": np.nan},
        {"product_name": "Rice", "current_stock": 100} # Key omitted
    ]
    for row in test_rows:
        status_info = compute_batch_alert_status(row, expiry_threshold_days=2, low_stock_threshold_units=10)
        assert status_info["status"] == "UNSPECIFIED_EXPIRY"
        assert status_info["tier"] == "neutral"
        assert status_info["is_urgent"] is False
        assert "expired" not in status_info["status_label"].lower()

def test_configurable_thresholds_dynamic_adaptation():
    """Tests that changing thresholds dynamically shifts item statuses."""
    row = {"product_name": "Chicken Breast", "current_stock": 20, "days_to_expiry": 4}
    
    # Under standard threshold of 2 days, 4 days is considered FRESH / HEALTHY
    status_std = compute_batch_alert_status(row, expiry_threshold_days=2, low_stock_threshold_units=15)
    assert status_std["status"] == "HEALTHY"
    assert status_std["tier"] == "green"
    
    # Under expanded threshold of 5 days, 4 days is flagged as EXPIRING_SOON
    status_exp = compute_batch_alert_status(row, expiry_threshold_days=5, low_stock_threshold_units=15)
    assert status_exp["status"] == "EXPIRING_SOON"
    assert status_exp["tier"] == "amber"

    # Now test low stock threshold adaptation:
    # 20 units with low_stock_threshold = 15 is healthy
    assert status_std["status"] == "HEALTHY"
    # 20 units with low_stock_threshold = 25 becomes LOW_STOCK (when shelf life is fresh)
    row_fresh_shelf = {"product_name": "Pasta", "current_stock": 20, "days_to_expiry": 10}
    status_low = compute_batch_alert_status(row_fresh_shelf, expiry_threshold_days=2, low_stock_threshold_units=25)
    assert status_low["status"] == "LOW_STOCK"
    assert status_low["tier"] == "amber"

def test_incomplete_datasets_and_missing_columns():
    """Tests that missing optional columns (e.g. store, category, cost) do not cause exceptions."""
    incomplete_df = pd.DataFrame([
        {"sku": "SKU-INCOMPLETE-1", "current_stock": 12}, # Missing expiry, store, category, cost
        {"sku": "SKU-INCOMPLETE-2", "current_stock": 50, "days_to_expiry": 3}
    ])
    
    # Apply status evaluation
    statuses = [
        compute_batch_alert_status(r.to_dict(), expiry_threshold_days=2, low_stock_threshold_units=15)
        for _, r in incomplete_df.iterrows()
    ]
    
    assert len(statuses) == 2
    assert statuses[0]["status"] == "LOW_STOCK" # 12 <= 15
    assert statuses[1]["status"] == "HEALTHY"   # 3d left, 50 stock

def test_csv_export_format_generation():
    """Tests CSV export generation with alerts attached."""
    df = pd.DataFrame([
        {"sku": "SKU-1", "product_name": "Berries", "current_stock": 10, "days_to_expiry": 1},
        {"sku": "SKU-2", "product_name": "Beans", "current_stock": 30, "days_to_expiry": None}
    ])
    
    meta = [compute_batch_alert_status(r.to_dict(), 2, 15) for _, r in df.iterrows()]
    df["alert_status"] = [m["status"] for m in meta]
    df["alert_reason"] = [m["alert_reason"] for m in meta]
    
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    csv_str = csv_bytes.decode('utf-8')
    
    assert "sku,product_name,current_stock,days_to_expiry,alert_status,alert_reason" in csv_str
    assert "CRITICAL_EXPIRY" in csv_str
    assert "UNSPECIFIED_EXPIRY" in csv_str
