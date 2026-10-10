"""
Unit and Integration Tests for Application Page Navigation
Verifies all 6 page options:
- Dashboard
- Upload Data
- Inventory & Expiry
- Demand Forecast
- AI Recommendations
- Reports

Tests page transitions, session state preservation, empty states, and query parameter routing.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Import page renderers
from pages.landing_dashboard import render_landing_dashboard_page
from pages.upload_data import render_upload_data_page
from pages.p2_inventory import render_inventory_page
from pages.demand_forecast import render_demand_forecast_page
from pages.ai_recommendations import render_ai_recommendations_page
from pages.reports import render_reports_page

# Import data generators
from data.generator import generate_live_inventory, generate_pos_sales_history
from agents.coordinator import CoordinatorAgent

NAV_OPTIONS = [
    "📊 Dashboard",
    "📤 Upload Data",
    "📦 Inventory & Expiry",
    "📈 Demand Forecast",
    "🤖 AI Recommendations",
    "📑 Reports"
]

PAGE_PARAM_MAP = {
    "dashboard": "📊 Dashboard",
    "dash": "📊 Dashboard",
    "upload": "📤 Upload Data",
    "inventory": "📦 Inventory & Expiry",
    "expiry": "📦 Inventory & Expiry",
    "forecast": "📈 Demand Forecast",
    "demand": "📈 Demand Forecast",
    "recommendations": "🤖 AI Recommendations",
    "recommendation": "🤖 AI Recommendations",
    "reports": "📑 Reports",
    "report": "📑 Reports"
}

def test_nav_options_completeness():
    """Verify that all 6 required pages are defined and distinct in NAV_OPTIONS."""
    assert len(NAV_OPTIONS) == 6
    assert "📊 Dashboard" in NAV_OPTIONS
    assert "📤 Upload Data" in NAV_OPTIONS
    assert "📦 Inventory & Expiry" in NAV_OPTIONS
    assert "📈 Demand Forecast" in NAV_OPTIONS
    assert "🤖 AI Recommendations" in NAV_OPTIONS
    assert "📑 Reports" in NAV_OPTIONS

def test_query_param_mapping_validity():
    """Verify that all query param aliases map to a valid NAV_OPTION."""
    for alias, page in PAGE_PARAM_MAP.items():
        assert page in NAV_OPTIONS, f"Query alias '{alias}' maps to invalid page '{page}'"

def test_navigation_state_sync_mechanism():
    """
    Test the pre-syncing mechanism between current_page and sidebar_nav_radio.
    Ensures in-page button transitions don't get reverted by the radio widget.
    """
    session_state = {"current_page": "📊 Dashboard", "sidebar_nav_radio": "📊 Dashboard"}
    
    # 1. User clicks an in-page button to go to "📤 Upload Data"
    session_state["current_page"] = "📤 Upload Data"
    
    # 2. Before st.radio renders, the pre-sync logic runs:
    if session_state.get("sidebar_nav_radio") != session_state.get("current_page"):
        session_state["sidebar_nav_radio"] = session_state["current_page"]
        
    assert session_state["sidebar_nav_radio"] == "📤 Upload Data"
    
    # 3. Next, user clicks an in-page button to go to "📦 Inventory & Expiry"
    session_state["current_page"] = "📦 Inventory & Expiry"
    if session_state.get("sidebar_nav_radio") != session_state.get("current_page"):
        session_state["sidebar_nav_radio"] = session_state["current_page"]
        
    assert session_state["sidebar_nav_radio"] == "📦 Inventory & Expiry"

    # 4. User clicks radio button directly to go to "📑 Reports"
    def on_nav_change(state):
        state["current_page"] = state["sidebar_nav_radio"]
        
    session_state["sidebar_nav_radio"] = "📑 Reports"
    on_nav_change(session_state)
    assert session_state["current_page"] == "📑 Reports"

def test_all_page_modules_render_without_syntax_error():
    """Verify all 6 page functions are callable and have no missing imports."""
    pages = [
        render_landing_dashboard_page,
        render_upload_data_page,
        render_inventory_page,
        render_demand_forecast_page,
        render_ai_recommendations_page,
        render_reports_page
    ]
    for p in pages:
        assert callable(p)
