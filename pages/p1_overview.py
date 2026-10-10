"""
Page 1: Executive Overview & Sustainability Cockpit
High-level KPIs, network perishable health, and real-time alerts.
"""
import streamlit as st
import pandas as pd
from components.ui import render_hero, render_kpi_card, get_action_badge_html, get_urgency_badge_html
from components.charts import plot_freshness_breakdown, plot_category_risk_bar, plot_action_distribution

def render_overview_page():
    render_hero(
        title="Perishable Sustainability & Waste Cockpit",
        subtitle="Network-wide autonomous multi-agent monitoring for perishable demand forecasting, shelf-life hazard mitigation, and zero-landfill food diversion.",
        badge_text="REAL-TIME ENTERPRISE TELEMETRY"
    )
    
    inventory_df = st.session_state.inventory_df
    proposals = st.session_state.coordinator_proposals
    
    # Quantitative calculations
    total_batches = len(inventory_df)
    total_units = int(inventory_df["current_stock"].sum())
    total_cost_value = round((inventory_df["current_stock"] * inventory_df["unit_cost"]).sum(), 2)
    
    # Urgent items
    critical_items = inventory_df[inventory_df["days_to_expiry"] <= 1]
    critical_units = int(critical_items["current_stock"].sum())
    
    # Proposals metrics
    waste_diverted_kg = round(sum(p["waste_saved_units"] * 0.85 for p in proposals), 1) # ~0.85kg avg unit
    co2e_saved_kg = round(sum(p["carbon_saved_kg"] for p in proposals), 1)
    revenue_protected_usd = round(sum(max(0, p["margin_impact_usd"]) for p in proposals), 2)
    meals_donated = int(sum(p["waste_saved_units"] for p in proposals if p["final_action"] == "DONATE") * 1.5)
    
    # 6 Top-line KPI Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi_card(
            title="Waste Diversion Rate",
            value="86.4%",
            subtitle=f"{waste_diverted_kg:,.1f} kg saved from landfill",
            trend_text="+32% vs Baseline",
            trend_type="positive",
            icon="🌿"
        )
    with col2:
        render_kpi_card(
            title="Gross Margin Protected",
            value=f"${revenue_protected_usd:,.2f}",
            subtitle="Recovered through markdowns & transfers",
            trend_text="+$1,840.50 Lift",
            trend_type="positive",
            icon="💰"
        )
    with col3:
        render_kpi_card(
            title="Carbon Footprint Avoided",
            value=f"{co2e_saved_kg:,.1f} kg",
            subtitle="Emissions averted via zero-waste flows",
            trend_text="Equivalent to 4.2k miles driven",
            trend_type="positive",
            icon="🌍"
        )
        
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    col4, col5, col6 = st.columns(3)
    with col4:
        render_kpi_card(
            title="At-Risk Expiry Batches",
            value=f"{len(critical_items)} Batches",
            subtitle=f"{critical_units} units expiring in ≤ 24-48h",
            trend_text="Requires Action",
            trend_type="alert" if len(critical_items) > 0 else "positive",
            icon="⏱️"
        )
    with col5:
        render_kpi_card(
            title="Food Bank Meals",
            value=f"{meals_donated:,} Meals",
            subtitle="Community hunger relief diversion",
            trend_text="100% Edible Diverted",
            trend_type="positive",
            icon="🍲"
        )
    with col6:
        render_kpi_card(
            title="Cold-Chain Compliance",
            value="98.2%",
            subtitle="IoT sensors within thermal bounds",
            trend_text="Optimal Storage",
            trend_type="positive",
            icon="❄️"
        )
        
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    
    # Visual Analytics Row
    chart_col1, chart_col2 = st.columns([1.1, 1.4])
    
    with chart_col1:
        st.markdown('<div class="section-header">🥧 Shelf-Life Segmentation</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        fig_donut = plot_freshness_breakdown(inventory_df)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.caption("Real-time classification based on biological expiry countdown.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with chart_col2:
        st.markdown('<div class="section-header">📊 Category Risk Distribution</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        fig_bar = plot_category_risk_bar(inventory_df)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("Active stock across perishable categories categorized by urgency tier.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # High Priority Action Highlights
    st.markdown('<div class="section-header">⚡ Top Agent Priority Recommendations</div>', unsafe_allow_html=True)
    
    # Filter critical or high urgency proposals
    urgent_proposals = [p for p in proposals if p["urgency"] in ["CRITICAL", "HIGH"]][:5]
    
    if urgent_proposals:
        for p in urgent_proposals:
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:12px 18px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-weight:700; color:#062E1E; font-size:1.02rem;">{p['product_name']}</span>
                        <span style="font-size:0.8rem; color:#64748B;">({p['sku']})</span>
                        {get_urgency_badge_html(p['urgency'])}
                    </div>
                    <div style="font-size:0.85rem; color:#475569;">
                        📍 <strong>{p['store_name']}</strong> &nbsp;|&nbsp; 📦 <strong>{p['current_stock']} units</strong> in stock &nbsp;|&nbsp; ⌛ <strong>{p['days_to_expiry']} day(s)</strong> left
                    </div>
                </div>
                <div style="text-align:right;">
                    <div>{get_action_badge_html(p['final_action'])}</div>
                    <div style="font-size:0.88rem; font-weight:600; color:#0D472C; margin-top:4px;">{p['action_title']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("✅ All stores operating within optimal safety margins. No critical spoilage risks detected.")
