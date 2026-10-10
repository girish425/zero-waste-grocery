"""
Landing & Executive Dashboard Page
Theme: "Smarter Grocery. Less Waste."
Features:
- Premium Sustainability Hero with dual CTA buttons
- 4 Overview Metric Cards (Products Tracked, Low Stock, Expiring Soon, Potential Waste Risk) with graceful empty states
- Visually engaging real-data charts
- "How it works" 3-step workflow
- Sustainability-focused impact section
"""
import streamlit as st
import pandas as pd
import importlib

# Ensure fresh module state in active Streamlit thread
import components.ui
try:
    from components.ui import (
        render_landing_hero_banner,
        render_overview_card,
        render_how_it_works_section,
        render_sustainability_callout
    )
except ImportError:
    importlib.reload(components.ui)
    from components.ui import (
        render_landing_hero_banner,
        render_overview_card,
        render_how_it_works_section,
        render_sustainability_callout
    )

from components.charts import plot_freshness_breakdown, plot_category_risk_bar


def render_landing_dashboard_page():
    # 1. Hero Section
    render_landing_hero_banner()
    
    # Dual Action CTA Buttons directly under hero
    cta_col1, cta_col2, cta_col_spacer = st.columns([1.5, 1.5, 3.5])
    
    with cta_col1:
        if st.button("🚀 Analyze My Inventory", type="primary", use_container_width=True, key="hero_btn_analyze"):
            st.session_state.current_page = "📤 Upload Data"
            st.rerun()
            
    with cta_col2:
        if st.button("📊 Explore Full Analytics", type="secondary", use_container_width=True, key="hero_btn_explore"):
            st.session_state.current_page = "📦 Inventory & Expiry"
            st.rerun()
            
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    
    # 2. Four Attractive Overview Cards (Real calculated data or empty states)
    inventory_df = st.session_state.get("inventory_df", None)
    proposals = st.session_state.get("coordinator_proposals", [])
    has_data = inventory_df is not None and not inventory_df.empty
    
    c1, c2, c3, c4 = st.columns(4)
    
    if has_data:
        # 1. Products Tracked
        unique_skus = inventory_df["sku"].nunique()
        total_batches = len(inventory_df)
        total_units = int(inventory_df["current_stock"].sum())
        
        # 2. Low Stock (Items where velocity is recorded and stock is less than 1.5 days of daily velocity)
        has_vel = inventory_df["avg_daily_sales"].notna()
        low_stock_mask = has_vel & (inventory_df["current_stock"] <= (inventory_df["avg_daily_sales"] * 1.5))
        low_stock_count = int(low_stock_mask.sum())
        low_stock_units = int(inventory_df.loc[low_stock_mask, "current_stock"].sum()) if low_stock_count > 0 else 0
        
        # 3. Expiring Soon (Days to expiry <= 2 days, strictly verified)
        has_dte = inventory_df["days_to_expiry"].notna()
        expiring_soon_mask = has_dte & (inventory_df["days_to_expiry"] <= 2)
        expiring_soon_count = int(expiring_soon_mask.sum())
        expiring_soon_units = int(inventory_df.loc[expiring_soon_mask, "current_stock"].sum()) if expiring_soon_count > 0 else 0
        
        # 4. Potential Waste Risk (Real financial cost at risk from spoilage hazard)
        if proposals:
            total_waste_risk_usd = sum(p.get("financial_risk_usd", 0.0) for p in proposals)
            waste_risk_units = sum(p.get("waste_saved_units", 0.0) for p in proposals)
        else:
            total_waste_risk_usd = float((inventory_df[expiring_soon_mask]["current_stock"] * inventory_df[expiring_soon_mask]["unit_cost"]).sum())
            waste_risk_units = expiring_soon_units
            
        with c1:
            render_overview_card(
                label="Products Tracked",
                value=f"{unique_skus} SKUs",
                subtext=f"{total_batches} active batches ({total_units:,} units)",
                icon="📦",
                icon_bg="#DCFCE7", # Lime/Green tint
                is_empty=False
            )
        with c2:
            render_overview_card(
                label="Low Stock",
                value=f"{low_stock_count} Batches",
                subtext=f"{low_stock_units} units below safety runway",
                icon="⚠️",
                icon_bg="#FEF3C7", # Amber tint
                is_empty=False
            )
        with c3:
            render_overview_card(
                label="Expiring Soon",
                value=f"{expiring_soon_count} Batches",
                subtext=f"{expiring_soon_units} units due within ≤ 48 hours",
                icon="⏱️",
                icon_bg="#FFEDD5", # Coral tint
                is_empty=False
            )
        with c4:
            render_overview_card(
                label="Potential Waste Risk",
                value=f"${total_waste_risk_usd:,.2f}",
                subtext=f"{int(waste_risk_units)} units exposed to spoilage loss",
                icon="📉",
                icon_bg="#FEE2E2", # Light red tint
                is_empty=False
            )
    else:
        # Elegant Empty States as requested
        with c1:
            render_overview_card(label="Products Tracked", is_empty=True, icon="📦", icon_bg="#F1F5F9")
        with c2:
            render_overview_card(label="Low Stock", is_empty=True, icon="⚠️", icon_bg="#F1F5F9")
        with c3:
            render_overview_card(label="Expiring Soon", is_empty=True, icon="⏱️", icon_bg="#F1F5F9")
        with c4:
            render_overview_card(label="Potential Waste Risk", is_empty=True, icon="📉", icon_bg="#F1F5F9")
            
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # 3. Visually Engaging Real Data Chart Area
    st.markdown("""
    <div style="margin: 0.5rem 0 1rem 0;">
        <div style="font-family:'Space Grotesk', sans-serif; font-size:1.45rem; font-weight:700; color:#062E1E; display:flex; align-items:center; gap:8px;">
            📊 Live Inventory Health & Expiry Risk Analytics
        </div>
        <div style="font-size:0.9rem; color:#64748B;">
            Calculated strictly from live on-shelf batch records and store cold-chain telemetry.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if has_data:
        chart_col1, chart_col2 = st.columns([1.1, 1.4])
        with chart_col1:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("<div style='font-weight:700; color:#062E1E; margin-bottom:4px;'>Shelf-Life Status Segmentation</div>", unsafe_allow_html=True)
            fig_fresh = plot_freshness_breakdown(inventory_df)
            st.plotly_chart(fig_fresh, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with chart_col2:
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.markdown("<div style='font-weight:700; color:#062E1E; margin-bottom:4px;'>Category-Wise Expiry Distribution</div>", unsafe_allow_html=True)
            fig_bar = plot_category_risk_bar(inventory_df)
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#F8FAFC; border:2px dashed #CBD5E1; border-radius:16px; padding:3rem 2rem; text-align:center; color:#64748B;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">📊</div>
            <div style="font-family:'Space Grotesk'; font-size:1.25rem; font-weight:700; color:#334155; margin-bottom:0.4rem;">
                No Inventory Data Loaded Yet
            </div>
            <div style="font-size:0.92rem; max-width:480px; margin:0 auto 1.2rem auto;">
                Upload your grocery inventory spreadsheet or click 'Analyze My Inventory' to generate real shelf-life and demand analytics.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # 4. How It Works Section
    render_how_it_works_section()
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # 5. Sustainability Section (Authentic facts without invented statistics)
    render_sustainability_callout()
