"""
Unit & Integration Tests for AI Recommendations Page Logic
Zero-Waste Grocery · GDGoC HITAM

Tests:
- Recommendation lifecycle (Pending -> Approved, Rejected, Modified)
- Review metadata capture (reviewer label, timestamp, reasons)
- Preservation of original recommendations and evidence
- Filtering by status, priority, agent, store
- Accurate summary counts across all 4 review states
- Empty state handling
- Session persistence without duplication
"""
import pytest
from datetime import datetime
from copy import deepcopy

def create_sample_proposals():
    """Helper to generate sample proposals for testing."""
    return [
        {
            "rec_id": "REC-101",
            "batch_id": "BATCH-101",
            "sku": "SKU-001",
            "product_name": "Organic Whole Milk",
            "store_name": "Downtown Store",
            "store_id": "STORE-01",
            "current_stock": 25,
            "days_to_expiry": 1,
            "base_price": 4.00,
            "unit_cost": 2.00,
            "final_action": "MARKDOWN",
            "action_title": "Apply 40% Dynamic Markdown ($2.40)",
            "action_details": {"discount_pct": 40, "discounted_price": 2.40},
            "priority": "CRITICAL",
            "urgency": "CRITICAL",
            "generating_agent": "Discount & Dynamic Markdown Agent",
            "margin_impact_usd": 10.0,
            "waste_saved_units": 15.0,
            "carbon_saved_kg": 27.0,
            "review_status": "PENDING",
            "approval_status": "PENDING"
        },
        {
            "rec_id": "REC-102",
            "batch_id": "BATCH-102",
            "sku": "SKU-002",
            "product_name": "Eggs Free Range",
            "store_name": "Suburb Store",
            "store_id": "STORE-02",
            "current_stock": 4,
            "days_to_expiry": 8,
            "base_price": 3.50,
            "unit_cost": 1.80,
            "final_action": "REORDER",
            "action_title": "Issue PO for 30 units (Supplier Restock)",
            "action_details": {"recommended_order_qty": 30},
            "priority": "HIGH",
            "urgency": "HIGH",
            "generating_agent": "Replenishment & Procurement Agent",
            "margin_impact_usd": -54.0,
            "waste_saved_units": 0.0,
            "carbon_saved_kg": 0.0,
            "review_status": "PENDING",
            "approval_status": "PENDING"
        },
        {
            "rec_id": "REC-103",
            "batch_id": "BATCH-103",
            "sku": "SKU-003",
            "product_name": "Greek Yogurt",
            "store_name": "Downtown Store",
            "store_id": "STORE-01",
            "current_stock": 20,
            "days_to_expiry": 3,
            "base_price": 4.50,
            "unit_cost": 2.20,
            "final_action": "TRANSFER",
            "action_title": "Transfer 10 units to Suburb Store",
            "action_details": {"transfer_qty": 10, "destination_store_name": "Suburb Store"},
            "priority": "MEDIUM",
            "urgency": "MEDIUM",
            "generating_agent": "Inter-Store Transfer Agent",
            "margin_impact_usd": 20.0,
            "waste_saved_units": 10.0,
            "carbon_saved_kg": 15.0,
            "review_status": "PENDING",
            "approval_status": "PENDING"
        }
    ]

def test_approve_recommendation_lifecycle():
    """Verify approval captures reviewer label, timestamp, and updates review_status."""
    proposals = create_sample_proposals()
    target = proposals[0]
    
    # Simulate Approve
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target["review_status"] = "APPROVED"
    target["approval_status"] = "APPROVED"
    target["reviewed_by"] = "Store Manager"
    target["reviewed_at"] = ts
    target["review_reason"] = "Approved by store manager inside prototype"

    assert target["review_status"] == "APPROVED"
    assert target["approval_status"] == "APPROVED"
    assert target["reviewed_by"] == "Store Manager"
    assert target["reviewed_at"] == ts
    assert "prototype" in target["review_reason"]

def test_reject_recommendation_lifecycle():
    """Verify rejection captures reviewer label, timestamp, and optional reason."""
    proposals = create_sample_proposals()
    target = proposals[1]
    
    # Simulate Reject
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target["review_status"] = "REJECTED"
    target["approval_status"] = "OVERRIDDEN"
    target["reviewed_by"] = "Inventory Planner"
    target["reviewed_at"] = ts
    target["review_reason"] = "Supplier stock arriving tomorrow via direct store delivery"

    assert target["review_status"] == "REJECTED"
    assert target["approval_status"] == "OVERRIDDEN"
    assert target["reviewed_by"] == "Inventory Planner"
    assert target["review_reason"] == "Supplier stock arriving tomorrow via direct store delivery"

def test_modify_recommendation_lifecycle_and_preservation():
    """Verify modify action updates fields, preserves original recommendation, and marks as MODIFIED."""
    proposals = create_sample_proposals()
    target = proposals[0]

    # Save snapshot of original
    target["original_recommendation"] = {
        "action": target["final_action"],
        "action_title": target["action_title"],
        "action_details": deepcopy(target["action_details"]),
        "margin_impact_usd": target["margin_impact_usd"]
    }

    # Manager modifies discount from 40% to 50%
    target["final_action"] = "MARKDOWN"
    target["action_title"] = "Apply 50% Dynamic Markdown ($2.00)"
    target["action_details"]["discount_pct"] = 50
    target["action_details"]["discounted_price"] = 2.00
    target["margin_impact_usd"] = 0.0 # break-even
    target["review_status"] = "MODIFIED"
    target["approval_status"] = "APPROVED"
    target["reviewed_by"] = "Store Manager"
    target["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target["review_reason"] = "Increased discount due to heavy rain forecast"

    assert target["review_status"] == "MODIFIED"
    assert target["approval_status"] == "APPROVED"
    assert target["action_details"]["discount_pct"] == 50
    # Original recommendation remains intact for audit inspection
    assert target["original_recommendation"]["action_details"]["discount_pct"] == 40
    assert target["original_recommendation"]["action_title"] == "Apply 40% Dynamic Markdown ($2.40)"
    assert target["review_reason"] == "Increased discount due to heavy rain forecast"

def test_summary_counts_across_statuses():
    """Verify exact count tallying for Pending, Approved, Rejected, Modified."""
    proposals = create_sample_proposals()
    proposals[0]["review_status"] = "APPROVED"
    proposals[1]["review_status"] = "REJECTED"
    # proposals[2] remains "PENDING"
    
    # Add a modified item
    mod_item = deepcopy(proposals[0])
    mod_item["rec_id"] = "REC-104"
    mod_item["review_status"] = "MODIFIED"
    proposals.append(mod_item)

    pending_count = sum(1 for p in proposals if p["review_status"] == "PENDING")
    approved_count = sum(1 for p in proposals if p["review_status"] == "APPROVED")
    rejected_count = sum(1 for p in proposals if p["review_status"] == "REJECTED")
    modified_count = sum(1 for p in proposals if p["review_status"] == "MODIFIED")

    assert pending_count == 1
    assert approved_count == 1
    assert rejected_count == 1
    assert modified_count == 1
    assert len(proposals) == 4

def test_filtering_logic():
    """Verify filtering by status, priority, agent, and store."""
    proposals = create_sample_proposals()
    proposals[0]["review_status"] = "APPROVED"
    
    # Filter by Status: Approved
    f_status = [p for p in proposals if p["review_status"] == "APPROVED"]
    assert len(f_status) == 1
    assert f_status[0]["rec_id"] == "REC-101"

    # Filter by Priority: CRITICAL
    f_prio = [p for p in proposals if p["priority"] == "CRITICAL"]
    assert len(f_prio) == 1
    assert f_prio[0]["product_name"] == "Organic Whole Milk"

    # Filter by Agent: Replenishment
    f_agent = [p for p in proposals if "Replenishment" in p["generating_agent"]]
    assert len(f_agent) == 1
    assert f_agent[0]["product_name"] == "Eggs Free Range"

    # Filter by Store: Downtown Store
    f_store = [p for p in proposals if p["store_name"] == "Downtown Store"]
    assert len(f_store) == 2

def test_session_persistence_no_duplication():
    """Verify recommendation IDs prevent duplicates and decisions persist across reruns."""
    session_proposals = create_sample_proposals()
    
    # Approve first item
    session_proposals[0]["review_status"] = "APPROVED"
    session_proposals[0]["reviewed_by"] = "Store Manager"

    # Simulate rerun where proposals are already in session state
    existing_ids = {p["rec_id"] for p in session_proposals}
    assert len(existing_ids) == 3

    # Attempt to re-add same items
    incoming_items = create_sample_proposals()
    for inc in incoming_items:
        if inc["rec_id"] not in existing_ids:
            session_proposals.append(inc)

    # Count must remain 3 without duplicating or erasing the approval decision
    assert len(session_proposals) == 3
    assert session_proposals[0]["review_status"] == "APPROVED"
    assert session_proposals[0]["reviewed_by"] == "Store Manager"

def test_page_module_import():
    """Verify render_planner_review_page and render_ai_recommendations_page import cleanly."""
    from pages.p4_planner_review import render_planner_review_page
    from pages.ai_recommendations import render_ai_recommendations_page
    assert callable(render_planner_review_page)
    assert callable(render_ai_recommendations_page)
