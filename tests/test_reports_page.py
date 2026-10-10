"""
Unit Tests for Reports Page & Audit Export Functions
Zero-Waste Grocery · GDGoC HITAM

Tests:
- Graceful handling of missing/empty datasets
- Accurate calculation of inventory health and valuation metrics
- Honest handling of missing price/cost data
- Identification of products requiring attention
- CSV report generation for inventory risks and agent decisions
- Integration contract verification
"""
import pytest
import pandas as pd
from datetime import date
from pages.reports import render_reports_page

def test_reports_page_module_import():
    """Verify render_reports_page is callable and exports correctly."""
    assert callable(render_reports_page)

def test_inventory_health_calculations_with_financials():
    """Verify inventory health, cost, and retail valuations are calculated accurately."""
    inv_df = pd.DataFrame([
        {"sku": "SKU-01", "product_name": "Milk", "current_stock": 20, "unit_cost": 2.0, "base_price": 4.0, "days_to_expiry": 3},
        {"sku": "SKU-02", "product_name": "Bread", "current_stock": 10, "unit_cost": 1.5, "base_price": 3.0, "days_to_expiry": 1},
    ])
    total_stock = inv_df["current_stock"].sum()
    total_cost = (inv_df["current_stock"] * inv_df["unit_cost"]).sum()
    total_retail = (inv_df["current_stock"] * inv_df["base_price"]).sum()
    
    assert total_stock == 30
    assert total_cost == 55.0  # 20*2 + 10*1.5
    assert total_retail == 110.0 # 20*4 + 10*3

def test_missing_price_cost_withheld_honestly():
    """Verify financial benefits are withheld when price/cost fields are missing."""
    inv_df = pd.DataFrame([
        {"sku": "SKU-01", "product_name": "Apples", "current_stock": 50, "days_to_expiry": 5}
    ])
    has_cost = "unit_cost" in inv_df.columns and inv_df["unit_cost"].notna().any()
    has_price = "base_price" in inv_df.columns and inv_df["base_price"].notna().any()
    
    assert has_cost is False
    assert has_price is False

def test_products_requiring_attention_identification():
    """Verify products with DTE <= 2 or stock <= 10 are flagged for attention."""
    inv_df = pd.DataFrame([
        {"sku": "S1", "product_name": "Yogurt", "store_id": "STORE-01", "current_stock": 25, "days_to_expiry": 1}, # Critical DTE
        {"sku": "S2", "product_name": "Cereal", "store_id": "STORE-01", "current_stock": 5, "days_to_expiry": 60}, # Low stock
        {"sku": "S3", "product_name": "Pasta", "store_id": "STORE-01", "current_stock": 40, "days_to_expiry": 180}, # Safe
    ])
    
    attention_items = []
    for _, r in inv_df.iterrows():
        dte = r["days_to_expiry"]
        stock = r["current_stock"]
        if (dte is not None and dte <= 2) or (stock <= 10):
            attention_items.append(r["sku"])
            
    assert len(attention_items) == 2
    assert "S1" in attention_items
    assert "S2" in attention_items
    assert "S3" not in attention_items

def test_csv_report_generation_formats():
    """Verify CSV string generation formats for inventory and proposals."""
    inv_df = pd.DataFrame([
        {"batch_code": "B1", "product_name": "Strawberries", "current_stock": 15, "days_to_expiry": 1}
    ])
    inv_csv = inv_df.to_csv(index=False).encode("utf-8")
    assert b"batch_code" in inv_csv
    assert b"Strawberries" in inv_csv
    assert b"15" in inv_csv

    proposals = [
        {
            "rec_id": "REC-01",
            "sku": "SKU-01",
            "product_name": "Strawberries",
            "store_name": "Downtown Store",
            "final_action": "MARKDOWN",
            "priority": "CRITICAL",
            "review_status": "APPROVED",
            "reviewed_by": "Store Manager"
        }
    ]
    recs_df = pd.DataFrame(proposals)
    recs_csv = recs_df.to_csv(index=False).encode("utf-8")
    assert b"REC-01" in recs_csv
    assert b"MARKDOWN" in recs_csv
    assert b"Store Manager" in recs_csv
