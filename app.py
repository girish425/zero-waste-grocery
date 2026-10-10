"""
Zero-Waste Grocery: An Agentic AI Approach to Perishable Demand & Shelf-Life Management
GDGoC HITAM · Agentic AI Hackathon (Sustainability Track)
Main Streamlit Application Entry Point
"""
import streamlit as st
import pandas as pd
from datetime import date

# Configure Streamlit page settings
st.set_page_config(
    page_title="Zero-Waste Grocery · Agentic AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

import importlib
import config
import components.ui
importlib.reload(config)
importlib.reload(components.ui)

# Import Configuration, Styling, Data Generator & Agents
from config import CUSTOM_CSS, APP_TITLE, APP_SUBTITLE, HACKATHON_EVENT, VERSION
from data.generator import generate_live_inventory, generate_pos_sales_history
from agents.coordinator import CoordinatorAgent

# Import Page Renderers
from pages.landing_dashboard import render_landing_dashboard_page

from pages.upload_data import render_upload_data_page
from pages.p2_inventory import render_inventory_page
from pages.demand_forecast import render_demand_forecast_page
from pages.ai_recommendations import render_ai_recommendations_page
from pages.reports import render_reports_page

# Inject Custom Sustainability CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize Session State
def initialize_app_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "📊 Dashboard"
        
    if "inventory_df" not in st.session_state:
        # Generate initial realistic data
        inv_df = generate_live_inventory()
        sales_df = generate_pos_sales_history()
        st.session_state.inventory_df = inv_df
        st.session_state.sales_df = sales_df
        
        # Pre-compute initial agent coordinator proposals
        coord = CoordinatorAgent()
        proposals = []
        for _, row in inv_df.iterrows():
            p = coord.reconcile_batch(row.to_dict(), inv_df)
            proposals.append(p)
            
        st.session_state.coordinator_proposals = proposals
        st.session_state.execution_logs = [
            {
                "timestamp": "2026-10-09 08:00:00",
                "batch_id": "SYS-INIT",
                "action": "TELEMETRY_SYNC",
                "target": "5 Regional Stores",
                "status": "COMPLETED",
                "message": "Cold-chain telemetry sync and POS transaction ingestion successful."
            },
            {
                "timestamp": "2026-10-09 08:02:15",
                "batch_id": "SYS-COORD",
                "action": "CONSENSUS_RUN",
                "target": f"{len(inv_df)} Perishable Batches",
                "status": "COMPLETED",
                "message": f"Autonomous Multi-Agent consensus deliberation completed. Generated {len(proposals)} proposals."
            }
        ]

initialize_app_state()

# Navigation item list exactly matching requirements
NAV_OPTIONS = [
    "📊 Dashboard",
    "📤 Upload Data",
    "📦 Inventory & Expiry",
    "📈 Demand Forecast",
    "🤖 AI Recommendations",
    "📑 Reports"
]

# Ensure valid page in session state
if st.session_state.current_page not in NAV_OPTIONS:
    st.session_state.current_page = "📊 Dashboard"

# Modern Sidebar Navigation
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 10px 0 16px 0; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.8rem;">🌿</span>
            <div style="font-family:'Space Grotesk', sans-serif; font-size:1.3rem; font-weight:700; color:#F8FAFC; line-height:1.1;">
                Zero-Waste<br><span style="color:#A3E635; font-size:1.1rem;">Grocery AI</span>
            </div>
        </div>
        <div style="font-size:0.75rem; color:#94A3B8; margin-top:8px; line-height:1.3;">
            {APP_SUBTITLE}
        </div>
        <div style="display:inline-block; margin-top:8px; background:rgba(132, 204, 22, 0.15); border:1px solid rgba(132, 204, 22, 0.4); color:#D9F99D; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:12px;">
            {HACKATHON_EVENT}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em; color:#94A3B8; font-weight:700; margin-bottom:8px;'>NAVIGATION</div>", unsafe_allow_html=True)
    
    current_index = NAV_OPTIONS.index(st.session_state.current_page)
    selected_nav = st.radio(
        label="Select Workspace:",
        options=NAV_OPTIONS,
        index=current_index,
        label_visibility="collapsed",
        key="sidebar_nav_radio"
    )
    
    # Sync radio choice to session state
    if selected_nav != st.session_state.current_page:
        st.session_state.current_page = selected_nav
        st.rerun()
        
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    # Store Network Status Card
    inventory_df = st.session_state.get("inventory_df", None)
    num_stores = inventory_df["store_id"].nunique() if (inventory_df is not None and not inventory_df.empty) else 0
    num_batches = len(inventory_df) if (inventory_df is not None and not inventory_df.empty) else 0
    
    st.markdown(f"""
    <div style="background: rgba(6, 46, 30, 0.6); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 12px; padding: 12px; font-size: 0.8rem; color: #CBD5E1;">
        <div style="font-weight: 700; color: #F8FAFC; margin-bottom: 6px; display:flex; align-items:center; gap:6px;">
            <span class="status-dot dot-green"></span> Network Telemetry Active
        </div>
        <div>• <strong>{num_stores}</strong> Stores Monitored</div>
        <div>• <strong>{num_batches}</strong> Active Perishable Batches</div>
        <div>• <strong>Telemetry:</strong> IoT Sensors Online</div>
        <div>• <strong>Coordinator:</strong> Multi-Agent AI</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    # Session Reset Action
    if st.button("🔄 Reset / Re-run System", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.markdown(f"<div style='font-size:0.7rem; color:#64748B; text-align:center; margin-top:14px;'>{VERSION}</div>", unsafe_allow_html=True)

# Router Logic based on st.session_state.current_page
active_page = st.session_state.current_page

if active_page == "📊 Dashboard":
    render_landing_dashboard_page()
elif active_page == "📤 Upload Data":
    render_upload_data_page()
elif active_page == "📦 Inventory & Expiry":
    render_inventory_page()
elif active_page == "📈 Demand Forecast":
    render_demand_forecast_page()
elif active_page == "🤖 AI Recommendations":
    render_ai_recommendations_page()
elif active_page == "📑 Reports":
    render_reports_page()

