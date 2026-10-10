"""
Unit Tests for Specialized Agents and Coordinator Multi-Agent Consensus
Zero-Waste Grocery · GDGoC HITAM
Uses small, controlled example datasets to verify agent logic, constraints,
and evidence-based recommendations without external API dependencies.
"""
import pytest
import pandas as pd
from agents.config import (
    AgentWorkflowPolicy,
    FreshnessPolicy,
    DiscountPolicy,
    ReplenishmentPolicy,
    StoreTransferPolicy
)
from agents.demand_agent import DemandAgent
from agents.freshness_agent import FreshnessAgent
from agents.discount_agent import DiscountAgent
from agents.replenishment_agent import ReplenishmentAgent
from agents.transfer_agent import StoreTransferAgent
from agents.coordinator import CoordinatorAgent
from agents.llm_explainer import explain_recommendation_in_plain_language

# ----------------- 1. DEMAND AGENT TESTS -----------------

def test_demand_agent_with_recorded_velocity():
    agent = DemandAgent()
    batch = {
        "sku": "SKU-001",
        "product_name": "Organic Whole Milk",
        "category": "Dairy",
        "current_stock": 20,
        "avg_daily_sales": 5.0,
        "days_to_expiry": 3
    }
    res = agent.evaluate(batch)
    assert res["base_velocity"] == 5.0
    assert res["cumulative_demand_p50"] > 0
    assert res["p10_confidence"] <= res["cumulative_demand_p50"] <= res["p90_confidence"]
    rec = res["recommendation"]
    assert rec["proposed_action"] == "FORECAST_UPDATED"
    assert rec["supporting_evidence"]["base_daily_velocity"] == 5.0

def test_demand_agent_with_unrecorded_velocity():
    agent = DemandAgent()
    batch = {
        "sku": "SKU-002",
        "product_name": "Fresh Strawberries",
        "category": "Produce",
        "current_stock": 16,
        "avg_daily_sales": None, # Unrecorded!
        "days_to_expiry": 2
    }
    res = agent.evaluate(batch)
    assert len(res["missing_information_or_assumptions"]) > 0
    assert "Sales velocity was unrecorded" in res["missing_information_or_assumptions"][0]
    assert res["recommendation"]["confidence"] < 0.85

# ----------------- 2. FRESHNESS AGENT TESTS -----------------

def test_freshness_agent_expired_item():
    agent = FreshnessAgent()
    batch = {
        "sku": "SKU-003",
        "product_name": "Greek Yogurt",
        "current_stock": 10,
        "days_to_expiry": 0, # Expired today
        "unit_cost": 2.0,
        "base_price": 4.0
    }
    res = agent.evaluate(batch)
    rec = res["recommendation"]
    assert rec["priority"] == "CRITICAL"
    assert rec["proposed_action"] == "EXPIRED_FLAGGED"
    assert rec["supporting_evidence"]["days_to_expiry"] == 0

def test_freshness_agent_unspecified_expiry():
    agent = FreshnessAgent()
    batch = {
        "sku": "SKU-004",
        "product_name": "Sourdough Bread",
        "current_stock": 12,
        "days_to_expiry": None # Missing expiry date
    }
    res = agent.evaluate(batch)
    rec = res["recommendation"]
    assert rec["priority"] == "LOW"
    assert rec["proposed_action"] == "MONITOR_EXPIRY"
    assert len(res["missing_information_or_assumptions"]) > 0
    assert any("unspecified" in a.lower() for a in res["missing_information_or_assumptions"])

# ----------------- 3. DISCOUNT AGENT TESTS -----------------

def test_discount_agent_policy_disabled():
    policy = AgentWorkflowPolicy(discount=DiscountPolicy(enabled=False))
    agent = DiscountAgent(policy=policy)
    batch = {
        "sku": "SKU-005",
        "product_name": "Fresh Spinach",
        "current_stock": 25,
        "days_to_expiry": 1,
        "base_price": 3.99,
        "unit_cost": 1.50
    }
    demand_out = {"cumulative_demand_p50": 5.0}
    res = agent.evaluate(batch, demand_output=demand_out)
    assert res["proposal"]["action"] == "NO_MARKDOWN"
    assert "disabled" in res["proposal"]["reasoning"].lower()
    assert res["recommendation"]["proposed_action"] == "NO_MARKDOWN"

def test_discount_agent_calculates_markdown_on_surplus():
    agent = DiscountAgent()
    batch = {
        "sku": "SKU-006",
        "product_name": "Artisan Baguette",
        "current_stock": 30,
        "days_to_expiry": 1, # Tomorrow
        "base_price": 4.00,
        "unit_cost": 1.20
    }
    demand_out = {"cumulative_demand_p50": 6.0} # 24 units surplus
    fresh_out = {"risk_metrics": {"expected_surplus_units": 24.0}}
    res = agent.evaluate(batch, demand_output=demand_out, freshness_output=fresh_out)
    assert res["proposal"]["action"] == "DYNAMIC_MARKDOWN"
    assert res["proposal"]["discount_pct"] >= 30
    assert res["proposal"]["discounted_price"] < 4.00
    assert res["recommendation"]["priority"] == "CRITICAL"
    assert res["recommendation"]["supporting_evidence"]["surplus_units"] == 24.0

def test_discount_agent_refuses_when_expiry_unspecified():
    agent = DiscountAgent()
    batch = {
        "sku": "SKU-007",
        "product_name": "Organic Tofu",
        "current_stock": 20,
        "days_to_expiry": None, # Unspecified
        "base_price": 2.50
    }
    res = agent.evaluate(batch)
    assert res["proposal"]["action"] == "NO_MARKDOWN"
    assert "unspecified" in res["proposal"]["reasoning"].lower()

# ----------------- 4. REPLENISHMENT AGENT TESTS -----------------

def test_replenishment_agent_reorder_when_low_stock():
    agent = ReplenishmentAgent()
    batch = {
        "sku": "SKU-008",
        "product_name": "Eggs Free Range",
        "current_stock": 5, # Very low stock
        "avg_daily_sales": 10.0,
        "lead_time_days": 2,
        "unit_cost": 2.50
    }
    # Reorder point: lead_time_demand (20) + safety_stock (~11) = ~31
    res = agent.evaluate(batch)
    assert res["proposal"]["action"] == "REORDER"
    assert res["proposal"]["recommended_order_qty"] >= 10
    assert res["recommendation"]["priority"] in ["CRITICAL", "HIGH"]

def test_replenishment_agent_suppress_on_critical_spoilage():
    agent = ReplenishmentAgent()
    batch = {
        "sku": "SKU-009",
        "product_name": "Fresh Berries",
        "current_stock": 5,
        "avg_daily_sales": 10.0,
        "lead_time_days": 2
    }
    fresh_out = {
        "risk_metrics": {
            "risk_level": "CRITICAL",
            "expected_surplus_units": 8.0 # Impending spoilage
        }
    }
    res = agent.evaluate(batch, freshness_output=fresh_out)
    assert res["proposal"]["action"] == "HOLD_REORDER"
    assert "spoilage" in res["proposal"]["reasoning"].lower()

def test_replenishment_agent_missing_velocity():
    agent = ReplenishmentAgent()
    batch = {
        "sku": "SKU-010",
        "product_name": "Gourmet Cheese",
        "current_stock": 3,
        "avg_daily_sales": None # Velocity missing
    }
    res = agent.evaluate(batch)
    assert res["proposal"]["action"] == "HOLD_REORDER"
    assert len(res["missing_information_or_assumptions"]) > 0

# ----------------- 5. STORE TRANSFER AGENT TESTS -----------------

def test_transfer_agent_refuses_without_multiple_stores():
    agent = StoreTransferAgent()
    batch = {
        "sku": "SKU-011",
        "product_name": "Organic Milk",
        "store_id": "STORE-01",
        "store_name": "Store 1",
        "current_stock": 30,
        "days_to_expiry": 3,
        "base_price": 4.50,
        "unit_cost": 2.00
    }
    # Inventory dataset with only 1 store!
    single_store_df = pd.DataFrame([
        {"store_id": "STORE-01", "sku": "SKU-011", "current_stock": 30, "avg_daily_sales": 2.0}
    ])
    fresh_out = {"risk_metrics": {"expected_surplus_units": 20.0}}
    res = agent.evaluate(batch, all_inventory_df=single_store_df, freshness_output=fresh_out)
    assert res["proposal"]["action"] == "NO_TRANSFER"
    assert "single store" in res["proposal"]["reasoning"].lower()
    assert res["recommendation"]["proposed_action"] == "NO_TRANSFER"

def test_transfer_agent_proposes_transfer_with_sister_store():
    agent = StoreTransferAgent()
    batch = {
        "sku": "SKU-012",
        "product_name": "Fresh Salmon",
        "store_id": "STORE-01",
        "store_name": "Store Downtown",
        "current_stock": 25,
        "days_to_expiry": 3,
        "base_price": 12.00,
        "unit_cost": 6.00
    }
    # Inventory with 2 stores: Store 2 has low stock and high daily sales
    multi_store_df = pd.DataFrame([
        {"store_id": "STORE-01", "store_name": "Store Downtown", "sku": "SKU-012", "current_stock": 25, "avg_daily_sales": 2.0},
        {"store_id": "STORE-02", "store_name": "Store Suburb", "sku": "SKU-012", "current_stock": 2, "avg_daily_sales": 15.0}
    ])
    fresh_out = {"risk_metrics": {"expected_surplus_units": 18.0}}
    res = agent.evaluate(batch, all_inventory_df=multi_store_df, freshness_output=fresh_out)
    assert res["proposal"]["action"] == "INTER_STORE_TRANSFER"
    assert res["proposal"]["destination_store_id"] == "STORE-02"
    assert res["proposal"]["transfer_qty"] > 0
    assert res["proposal"]["projected_salvage_usd"] > 0

def test_transfer_agent_refuses_when_short_shelf_life():
    agent = StoreTransferAgent()
    batch = {
        "sku": "SKU-013",
        "product_name": "Fresh Berries",
        "store_id": "STORE-01",
        "current_stock": 20,
        "days_to_expiry": 1, # Only 1 day remaining; transit takes >= 2
        "base_price": 5.00
    }
    multi_store_df = pd.DataFrame([
        {"store_id": "STORE-01", "sku": "SKU-013", "current_stock": 20},
        {"store_id": "STORE-02", "sku": "SKU-013", "current_stock": 0}
    ])
    res = agent.evaluate(batch, all_inventory_df=multi_store_df)
    assert res["proposal"]["action"] == "NO_TRANSFER"
    assert "insufficient" in res["proposal"]["reasoning"].lower()

# ----------------- 6. COORDINATOR AGENT TESTS -----------------

def test_coordinator_reconciles_single_action_with_full_schema():
    coord = CoordinatorAgent()
    batch = {
        "sku": "SKU-014",
        "product_name": "Greek Yogurt",
        "store_id": "STORE-01",
        "store_name": "Store 1",
        "category": "Dairy",
        "current_stock": 20,
        "days_to_expiry": 1, # Tomorrow
        "avg_daily_sales": 4.0,
        "base_price": 3.50,
        "unit_cost": 1.50,
        "carbon_factor_kg": 1.5
    }
    prop = coord.reconcile_batch(batch)
    
    # Assert exact required keys exist
    assert "product" in prop["recommendation"]
    assert "proposed_action" in prop["recommendation"]
    assert "supporting_evidence" in prop["recommendation"]
    assert "priority" in prop["recommendation"]
    assert "missing_information_or_assumptions" in prop["recommendation"]
    assert "explanation" in prop["recommendation"]
    assert "generating_agent" in prop
    
    # Check decision
    assert prop["final_action"] == "MARKDOWN"
    assert prop["priority"] == "CRITICAL"
    assert prop["margin_impact_usd"] > 0

def test_coordinator_reconcile_all_dataframe():
    coord = CoordinatorAgent()
    df = pd.DataFrame([
        {"sku": "SKU-A", "product_name": "Milk", "store_id": "S1", "store_name": "Store 1", "current_stock": 5, "days_to_expiry": 10, "avg_daily_sales": 10.0, "unit_cost": 2.0, "base_price": 4.0, "carbon_factor_kg": 1.0},
        {"sku": "SKU-B", "product_name": "Salad", "store_id": "S1", "store_name": "Store 1", "current_stock": 15, "days_to_expiry": 0, "avg_daily_sales": 3.0, "unit_cost": 1.5, "base_price": 3.0, "carbon_factor_kg": 0.5}
    ])
    proposals = coord.reconcile_all(df)
    assert len(proposals) == 2
    # Milk should trigger reorder (low stock, safe expiry)
    assert proposals[0]["final_action"] == "REORDER"
    # Salad should trigger donation / markdown (expired)
    assert proposals[1]["final_action"] in ["DONATE", "MARKDOWN"]

# ----------------- 7. LLM EXPLAINER DETERMINISTIC TEST -----------------

def test_llm_explainer_deterministic_fallback():
    rec = {
        "product": {"product_name": "Organic Milk", "sku": "SKU-001", "store_name": "Store A"},
        "proposed_action": "MARKDOWN",
        "supporting_evidence": {"discount_pct": 30, "discounted_price": 2.80, "days_to_expiry": 1},
        "missing_information_or_assumptions": [],
        "priority": "CRITICAL"
    }
    exp = explain_recommendation_in_plain_language(rec, api_key=None)
    assert "Organic Milk" in exp
    assert "30%" in exp
    assert "$2.80" in exp
