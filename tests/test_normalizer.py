"""
Comprehensive Unit & Integration Test Suite for Data Normalization & Validation Module
GDGoC HITAM · Zero-Waste Grocery Application

Covers:
- All prompt-specified aliases across multiple store ERP naming conventions
- Case-insensitivity, leading/trailing whitespace, and punctuation resilience
- Ambiguity detection and user mapping overrides
- Strict distinction between required and optional fields
- Plain-language validation error explanations for malformed data
- Integrity for missing expiry dates (never assumed or fabricated)
- Integrity for missing sales quantities (never assumed or fabricated)
- Preservation of original uploaded data
- Duplicate record detection with lot isolation
- Multi-Agent deliberation resilience on normalized data
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from data.normalizer import (
    CANONICAL_FIELDS,
    ALIAS_MAP,
    suggest_column_mappings,
    normalize_and_validate_inventory,
    clean_column_name,
    parse_date_safely
)
from agents.coordinator import CoordinatorAgent
from agents.demand_agent import DemandForecastingAgent
from agents.spoilage_agent import SpoilageRiskAgent
from agents.markdown_agent import MarkdownPricingAgent
from agents.transfer_agent import InventoryTransferAgent
from agents.replenishment_agent import ReplenishmentAgent

# ==============================================================================
# 1. TEST MULTIPLE STORE ALIAS CONVENTIONS (PROMPT SPECIFIED)
# ==============================================================================

def test_prompt_specified_aliases_across_store_formats():
    """
    Validates all aliases specified in prompt requirements:
    Product name: product_name, item_name, product, item, SKU name.
    Product identifier: product_id, SKU, sku_id, item_code.
    Stock: stock, current_stock, quantity, inventory_quantity, available_quantity.
    Sales date: date, sales_date, transaction_date, order_date.
    Sales quantity: sales, units_sold, quantity_sold, sold_quantity.
    Expiry date: expiry_date, expiration_date, best_before, use_by.
    Store identifier: store_id, branch_id, location_id, store.
    """
    # Convention 1: Supermarket Chain Alpha
    headers_alpha = ["product_name", "product_id", "stock", "sales_date", "sales", "expiry_date", "store_id"]
    map_alpha, unmapped_alpha, _ = suggest_column_mappings(headers_alpha)
    assert map_alpha["product_name"] == "product_name"
    assert map_alpha["sku"] == "product_id"
    assert map_alpha["current_stock"] == "stock"
    assert map_alpha["sales_date"] == "sales_date"
    assert map_alpha["sales_quantity"] == "sales"
    assert map_alpha["expiry_date"] == "expiry_date"
    assert map_alpha["store_id"] == "store_id"
    assert len(unmapped_alpha) == 0

    # Convention 2: Supermarket Chain Beta (Retail ERP)
    headers_beta = ["item_name", "SKU", "current_stock", "transaction_date", "units_sold", "expiration_date", "branch_id"]
    map_beta, unmapped_beta, _ = suggest_column_mappings(headers_beta)
    assert map_beta["product_name"] == "item_name"
    assert map_beta["sku"] == "SKU"
    assert map_beta["current_stock"] == "current_stock"
    assert map_beta["sales_date"] == "transaction_date"
    assert map_beta["sales_quantity"] == "units_sold"
    assert map_beta["expiry_date"] == "expiration_date"
    assert map_beta["store_id"] == "branch_id"
    assert len(unmapped_beta) == 0

    # Convention 3: Fresh Market Gamma (WMS System)
    headers_gamma = ["product", "sku_id", "quantity", "order_date", "quantity_sold", "best_before", "location_id"]
    map_gamma, unmapped_gamma, _ = suggest_column_mappings(headers_gamma)
    assert map_gamma["product_name"] == "product"
    assert map_gamma["sku"] == "sku_id"
    assert map_gamma["current_stock"] == "quantity"
    assert map_gamma["sales_date"] == "order_date"
    assert map_gamma["sales_quantity"] == "quantity_sold"
    assert map_gamma["expiry_date"] == "best_before"
    assert map_gamma["store_id"] == "location_id"
    assert len(unmapped_gamma) == 0

    # Convention 4: Regional Grocer Delta (POS Terminal)
    headers_delta = ["item", "item_code", "inventory_quantity", "date", "sold_quantity", "use_by", "store"]
    map_delta, unmapped_delta, _ = suggest_column_mappings(headers_delta)
    assert map_delta["product_name"] == "item"
    assert map_delta["sku"] == "item_code"
    assert map_delta["current_stock"] == "inventory_quantity"
    assert map_delta["sales_date"] == "date"
    assert map_delta["sales_quantity"] == "sold_quantity"
    assert map_delta["expiry_date"] == "use_by"
    assert map_delta["store_id"] == "store"
    assert len(unmapped_delta) == 0

    # Convention 5: Specialty SKU naming convention
    headers_epsilon = ["SKU name", "item_code", "available_quantity", "use_by"]
    map_epsilon, unmapped_epsilon, _ = suggest_column_mappings(headers_epsilon)
    assert map_epsilon["product_name"] == "SKU name"
    assert map_epsilon["sku"] == "item_code"
    assert map_epsilon["current_stock"] == "available_quantity"
    assert map_epsilon["expiry_date"] == "use_by"

# ==============================================================================
# 2. TEST CASE-INSENSITIVITY, WHITESPACE, AND PUNCTUATION RESILIENCE
# ==============================================================================

def test_case_insensitivity_and_whitespace_cleaning():
    """Tests noisy whitespace, tabs, mixed casings, and symbol separators."""
    headers_noisy = [
        "   PRODUCT_ID   ",
        "  Item_Title  ",
        "AVAILABLE  QUANTITY",
        "best.before.date",
        "SHOP-ID",
        "  Cost  Price ($)  ",
        "Shelf Price (USD)"
    ]
    mapping, unmapped, _ = suggest_column_mappings(headers_noisy)
    assert mapping["sku"] == "   PRODUCT_ID   "
    assert mapping["product_name"] == "  Item_Title  "
    assert mapping["current_stock"] == "AVAILABLE  QUANTITY"
    assert mapping["expiry_date"] == "best.before.date"
    assert mapping["store_id"] == "SHOP-ID"
    assert mapping["unit_cost"] == "  Cost  Price ($)  "
    assert mapping["base_price"] == "Shelf Price (USD)"
    assert len(unmapped) == 0

def test_clean_column_name_function():
    """Unit tests for clean_column_name standardization helper."""
    assert clean_column_name("  Item Name  ") == "item_name"
    assert clean_column_name("PRODUCT-ID") == "product_id"
    assert clean_column_name("Stock (Units)") == "stock_units"
    assert clean_column_name("Use_By_Date") == "use_by_date"
    assert clean_column_name("best.before") == "best_before"
    assert clean_column_name(None) == ""

# ==============================================================================
# 3. TEST AMBIGUITY DETECTION AND USER MAPPING OVERRIDES
# ==============================================================================

def test_ambiguity_detection_and_manual_override():
    """Tests detection of multiple candidate columns and manual mapping resolution."""
    # A dataset with two columns that both match 'sku'
    ambiguous_headers = ["product_id", "sku_code", "current_stock", "best_before"]
    mapping, unmapped, meta = suggest_column_mappings(ambiguous_headers)
    
    # Should detect ambiguity on sku
    assert meta["is_ambiguous"] is True
    assert "sku" in meta["ambiguities"]
    assert "product_id" in meta["ambiguities"]["sku"]
    assert "sku_code" in meta["ambiguities"]["sku"]
    
    # User manually overrides mapping to pick 'sku_code' instead of 'product_id'
    user_override = mapping.copy()
    user_override["sku"] = "sku_code"
    
    df = pd.DataFrame([
        {"product_id": "IGNORE-01", "sku_code": "CHOSEN-SKU-99", "current_stock": 50, "best_before": "2026-10-20"}
    ])
    
    res = normalize_and_validate_inventory(df, column_mapping=user_override)
    assert res["accepted_count"] == 1
    assert res["valid_df"].iloc[0]["sku"] == "CHOSEN-SKU-99"

# ==============================================================================
# 4. TEST REQUIRED VS OPTIONAL FIELD DISTINCTION
# ==============================================================================

def test_required_vs_optional_fields_enforcement():
    """Tests that missing required fields reject dataset while missing optional fields succeed."""
    # Scenario A: Missing required 'sku' in mapping
    df_no_sku = pd.DataFrame([{"stock": 100, "item_name": "Organic Milk"}])
    mapping_no_sku, _, _ = suggest_column_mappings(list(df_no_sku.columns))
    res_a = normalize_and_validate_inventory(df_no_sku, mapping_no_sku)
    assert res_a["accepted_count"] == 0
    assert res_a["rejected_count"] == 1
    assert "Required column mapping missing" in res_a["rejected_details"][0]["reasons"][0]

    # Scenario B: Missing required 'current_stock' in mapping
    df_no_stock = pd.DataFrame([{"product_id": "SKU-MILK", "item_name": "Organic Milk"}])
    mapping_no_stock, _, _ = suggest_column_mappings(list(df_no_stock.columns))
    res_b = normalize_and_validate_inventory(df_no_stock, mapping_no_stock)
    assert res_b["accepted_count"] == 0
    assert "Required column mapping missing" in res_b["rejected_details"][0]["reasons"][0]

    # Scenario C: Minimal dataset with ONLY required fields (sku, stock) - MUST PASS
    df_minimal = pd.DataFrame([{"sku": "SKU-MIN-01", "stock": 45}])
    mapping_min, _, _ = suggest_column_mappings(list(df_minimal.columns))
    res_c = normalize_and_validate_inventory(df_minimal, mapping_min)
    assert res_c["accepted_count"] == 1
    assert res_c["rejected_count"] == 0
    valid_row = res_c["valid_df"].iloc[0]
    assert valid_row["sku"] == "SKU-MIN-01"
    assert valid_row["current_stock"] == 45
    assert valid_row["product_name"] == "SKU-MIN-01" # Graceful fallback to SKU
    assert valid_row["expiry_date"] is None
    assert valid_row["days_to_expiry"] is None
    assert valid_row["expiry_status"] == "UNKNOWN_EXPIRY"

# ==============================================================================
# 5. TEST MALFORMED INPUTS & PLAIN-LANGUAGE EXPLANATIONS
# ==============================================================================

def test_malformed_inputs_and_plain_language_rejections():
    """Tests negative stock, non-numeric strings, missing identifiers with clear explanations."""
    df_malformed = pd.DataFrame([
        {"product_id": "SKU-VALID-1", "stock": 50, "use_by": "2026-10-15"},
        {"product_id": "SKU-NEG-2", "stock": -25, "use_by": "2026-10-15"},       # Negative stock
        {"product_id": "SKU-STR-3", "stock": "INVALID_NUMBER", "use_by": "2026-10-15"}, # Non-numeric stock
        {"product_id": "", "stock": 20, "use_by": "2026-10-15"},                 # Blank SKU
        {"product_id": None, "stock": 10, "use_by": "2026-10-15"},               # Null SKU
        {"product_id": "SKU-NAN-4", "stock": None, "use_by": "2026-10-15"}       # Missing stock
    ])
    
    mapping, _, _ = suggest_column_mappings(list(df_malformed.columns))
    res = normalize_and_validate_inventory(df_malformed, mapping)
    
    assert res["accepted_count"] == 1
    assert res["rejected_count"] == 5
    
    # Validate plain language explanations
    reasons_flat = [r for detail in res["rejected_details"] for r in detail["reasons"]]
    assert any("Negative stock quantity" in r for r in reasons_flat)
    assert any("Invalid stock value" in r for r in reasons_flat)
    assert any("Missing product identifier" in r for r in reasons_flat)
    assert any("Stock quantity is missing" in r for r in reasons_flat)

def test_empty_dataframe_handling():
    """Tests that completely empty or None DataFrames return structured safe responses."""
    res_none = normalize_and_validate_inventory(None)
    assert res_none["accepted_count"] == 0
    assert "0 rows" in res_none["warnings"][0]

    res_empty = normalize_and_validate_inventory(pd.DataFrame())
    assert res_empty["accepted_count"] == 0

# ==============================================================================
# 6. TEST DATE PARSING & EXPIRY DATE INTEGRITY (NEVER ASSUME MISSING EXPIRY)
# ==============================================================================

def test_diverse_date_formats_parsing():
    """Tests ISO, US, European, timestamp, and string date variations."""
    today = date.today()
    assert parse_date_safely("2026-10-15") == date(2026, 10, 15)
    assert parse_date_safely("10/15/2026") == date(2026, 10, 15)
    assert parse_date_safely("15/10/2026") == date(2026, 10, 15)
    assert parse_date_safely("2026/10/15") == date(2026, 10, 15)
    assert parse_date_safely("15-10-2026") == date(2026, 10, 15)
    assert parse_date_safely("2026-10-15 08:30:00") == date(2026, 10, 15)
    assert parse_date_safely(pd.Timestamp("2026-10-15")) == date(2026, 10, 15)
    assert parse_date_safely(date(2026, 10, 15)) == date(2026, 10, 15)

    # Invalid / Missing
    assert parse_date_safely(None) is None
    assert parse_date_safely("") is None
    assert parse_date_safely("   ") is None
    assert parse_date_safely("nan") is None
    assert parse_date_safely("null") is None
    assert parse_date_safely("not_a_valid_date") is None

def test_missing_expiry_date_integrity():
    """
    CRITICAL REQUIREMENT:
    - Do not assume a missing expiry date.
    - Do not treat a product's expiry status as known if its expiry date is missing.
    """
    df_no_exp = pd.DataFrame([
        {"sku": "SKU-APPLES-01", "quantity": 30, "product": "Gala Apples"}, # Expiry column omitted
        {"sku": "SKU-MILK-02", "quantity": 12, "product": "Whole Milk 1L", "expiry_date": None}, # Null value
        {"sku": "SKU-BREAD-03", "quantity": 18, "product": "Sourdough", "expiry_date": ""}, # Empty string
        {"sku": "SKU-YOGURT-04", "quantity": 25, "product": "Greek Yogurt", "expiry_date": "unspecified"} # Unparseable
    ])
    
    mapping, _, _ = suggest_column_mappings(list(df_no_exp.columns))
    res = normalize_and_validate_inventory(df_no_exp, mapping)
    
    assert res["accepted_count"] == 4
    assert res["has_missing_expiry"] is True
    assert res["missing_expiry_count"] == 4
    
    valid_df = res["valid_df"]
    # Verify days_to_expiry is None across all rows
    assert valid_df["days_to_expiry"].isna().all()
    # Verify freshness_pct is None and NOT a fabricated percentage
    assert valid_df["freshness_pct"].isna().all()
    # Verify expiry_status is strictly UNKNOWN_EXPIRY
    assert (valid_df["expiry_status"] == "UNKNOWN_EXPIRY").all()

# ==============================================================================
# 7. TEST SALES QUANTITY & VELOCITY INTEGRITY (NEVER ASSUME MISSING SALES)
# ==============================================================================

def test_missing_sales_quantity_not_assumed():
    """
    CRITICAL REQUIREMENT:
    - Do not assume a missing sales quantity.
    """
    df_no_sales = pd.DataFrame([
        {"sku": "SKU-CIDER-01", "stock": 40, "sales_velocity": None},
        {"sku": "SKU-CIDER-02", "stock": 20, "sales_velocity": ""},
        {"sku": "SKU-CIDER-03", "stock": 15} # sales column completely omitted
    ])
    mapping, _, _ = suggest_column_mappings(list(df_no_sales.columns))
    res = normalize_and_validate_inventory(df_no_sales, mapping)
    
    assert res["accepted_count"] == 3
    assert res["has_unrecorded_sales"] is True
    assert res["unrecorded_sales_count"] == 3
    valid_df = res["valid_df"]
    assert valid_df["avg_daily_sales"].isna().all()

# ==============================================================================
# 8. TEST DUPLICATE RECORD DETECTION
# ==============================================================================

def test_duplicate_record_handling_and_warning():
    """Tests that duplicate SKU/Store/Batch records generate warnings without dropping data."""
    df_dupes = pd.DataFrame([
        {"sku": "SKU-DUP-1", "stock": 20, "batch": "LOT-99", "store": "Store North"},
        {"sku": "SKU-DUP-1", "stock": 15, "batch": "LOT-99", "store": "Store North"}, # Exact Duplicate
        {"sku": "SKU-DUP-2", "stock": 40, "batch": "LOT-100", "store": "Store North"}
    ])
    
    mapping, _, _ = suggest_column_mappings(list(df_dupes.columns))
    res = normalize_and_validate_inventory(df_dupes, mapping)
    
    assert res["accepted_count"] == 3
    assert res["duplicate_count"] == 1
    assert any("Duplicate record detected" in w for w in res["warnings"])
    
    # Verify both lots received distinct internal batch IDs
    valid_df = res["valid_df"]
    assert valid_df["batch_id"].nunique() == 3

# ==============================================================================
# 9. TEST PRESERVATION OF ORIGINAL UPLOADED DATA
# ==============================================================================

def test_original_data_preservation():
    """Tests that original raw DataFrame is preserved unmutated for reference."""
    df_raw = pd.DataFrame([
        {"Item Code": "SKU-A", "Product Name": "Organic Bananas", "Available_Quantity": 35, "Use_By": "2026-10-18"}
    ])
    raw_copy = df_raw.copy()
    
    mapping, _, _ = suggest_column_mappings(list(df_raw.columns))
    res = normalize_and_validate_inventory(df_raw, mapping)
    
    # Verify raw_df in results matches input exactly
    pd.testing.assert_frame_equal(res["raw_df"], raw_copy)

# ==============================================================================
# 10. TEST MULTI-AGENT DELIBERATION ON NORMALIZED DATA
# ==============================================================================

def test_coordinator_and_all_agents_on_normalized_records():
    """
    Tests that Multi-Agent system (Coordinator, Demand, Spoilage, Markdown, Transfer, Replenish)
    operates safely without exceptions on normalized data with missing expiry or sales.
    """
    df_sample = pd.DataFrame([
        # Item 1: Expiring today with verified date
        {
            "item_code": "SKU-EXP-TODAY",
            "available_quantity": 25,
            "item_name": "Fresh Strawberries",
            "use_by": date.today().strftime("%Y-%m-%d"),
            "cost": 2.00,
            "price": 4.50,
            "sales": 8.0
        },
        # Item 2: Missing expiry date and unrecorded sales
        {
            "item_code": "SKU-NO-EXP",
            "available_quantity": 18,
            "item_name": "Canned Navy Beans",
            "use_by": None,
            "cost": 1.20,
            "price": 2.50,
            "sales": None
        }
    ])
    
    mapping, _, _ = suggest_column_mappings(list(df_sample.columns))
    res = normalize_and_validate_inventory(df_sample, mapping)
    valid_df = res["valid_df"]
    assert len(valid_df) == 2
    
    # 1. Test Specialist Agents directly
    demand_agent = DemandForecastingAgent()
    spoilage_agent = SpoilageRiskAgent()
    markdown_agent = MarkdownPricingAgent()
    transfer_agent = InventoryTransferAgent()
    replen_agent = ReplenishmentAgent()
    
    row_no_exp = valid_df.iloc[1].to_dict()
    demand_out = demand_agent.evaluate(row_no_exp)
    assert demand_out["cumulative_demand_p50"] > 0
    
    spoilage_out = spoilage_agent.evaluate(row_no_exp, demand_out)
    assert spoilage_out["risk_metrics"]["risk_level"] == "UNKNOWN"
    assert spoilage_out["risk_metrics"]["expected_spoiled_units"] == 0.0
    
    markdown_out = markdown_agent.evaluate(row_no_exp, demand_out, spoilage_out)
    assert markdown_out["proposal"]["action"] == "NO_MARKDOWN"
    
    transfer_out = transfer_agent.evaluate(row_no_exp, valid_df, spoilage_out)
    assert transfer_out["proposal"]["action"] == "NO_TRANSFER"
    
    replen_out = replen_agent.evaluate(row_no_exp, demand_out, spoilage_out)
    assert replen_out["proposal"]["action"] == "HOLD_REORDER"
    
    # 2. Test Chief Coordinator reconciliation
    coord = CoordinatorAgent()
    proposals = []
    for _, row in valid_df.iterrows():
        p = coord.reconcile_batch(row.to_dict(), valid_df)
        proposals.append(p)
        
    assert len(proposals) == 2
    
    # Product 1 (Expiring today) -> Must trigger waste mitigation (Markdown or Donate)
    assert proposals[0]["final_action"] in ["MARKDOWN", "DONATE"]
    assert proposals[0]["urgency"] == "CRITICAL"
    
    # Product 2 (Unspecified expiry) -> Must NOT assume critical expiry!
    assert proposals[1]["final_action"] == "MAINTAIN"
    assert proposals[1]["urgency"] == "UNKNOWN"
    assert "Unspecified" in proposals[1]["action_title"]
    assert proposals[1]["waste_saved_units"] == 0.0

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_normalizer.py"])
