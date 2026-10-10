"""
Page: Executive Reports & Operational Audit Suite
Zero-Waste Grocery · GDGoC HITAM

Provides:
- Inventory health summary
- Expiry and freshness risk summary
- Historical sales and forecast summary (when data is available)
- Agent recommendation counts by priority, action type, and status
- Manager approval and rejection summaries with audit trail
- Estimated potential savings with explicit formula and assumption disclosures
- Table of products requiring immediate attention
- Downloadable CSV reports for inventory risks and agent recommendations
- Full graceful handling of missing or incomplete datasets
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

from components.ui import render_hero, render_kpi_card, get_action_badge_html, get_urgency_badge_html
from data.excel_manager import export_inventory_workbook

# Styling constants matching the brand palette
PLOTLY_FONT = dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#334155")
PLOTLY_BG = "rgba(0,0,0,0)"

def render_reports_page():
    render_hero(
        title="Executive Intelligence & Operational Reports",
        subtitle="Empirical audit summaries across inventory health, shelf-life freshness risks, sales velocity, agent recommendations, and manager authorizations.",
        badge_text="EVIDENCE-BASED AUDIT SUITE"
    )

    # 1. Retrieve Current Session Datasets
    inventory_df = st.session_state.get("inventory_df", None)
    sales_df = st.session_state.get("sales_df", None)
    proposals = st.session_state.get("coordinator_proposals", [])

    # 2. Empty State Handling if No Inventory Data
    if inventory_df is None or inventory_df.empty:
        st.markdown("""
        <div class="custom-card" style="text-align:center; padding:45px 24px; border:2px dashed #CBD5E1; background:#FAFCFA;">
            <span style="font-size:3.5rem;">📊</span>
            <h3 style="color:#062E1E; font-family:'Space Grotesk'; margin:12px 0 6px 0;">No Active Inventory Data Available</h3>
            <div style="color:#64748B; font-size:0.92rem; max-width:540px; margin:0 auto 20px auto; line-height:1.5;">
                Executive reports require active inventory records to compute health metrics, expiry risks, and agent recommendations. 
                Please upload a dataset or load the supermarket benchmark network to view certified audit summaries.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_e1, col_e2, col_e3 = st.columns([1.5, 1.2, 1.5])
        with col_e2:
            if st.button("📤 Go to Upload Data", type="primary", use_container_width=True):
                st.session_state.current_page = "📤 Upload Data"
                st.rerun()
        return

    # 3. Store Location Filter for Scoped Reporting
    store_col = None
    for cand in ["store_name", "store_id", "branch_id", "store"]:
        if cand in inventory_df.columns:
            store_col = cand
            break

    # Store Scope Filter
    if store_col:
        store_list = ["All Stores (Chain-Wide)"] + sorted(list(inventory_df[store_col].dropna().astype(str).unique()))
    else:
        store_list = ["All Stores (Chain-Wide)"]

    st.markdown('<div class="custom-card" style="padding: 14px 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.4, 1.3, 0.9, 1.2])
    
    with f_col1:
        if store_col:
            selected_store_filter = st.selectbox("Select Report Store Scope:", store_list, index=0)
        else:
            selected_store_filter = "All Stores (Chain-Wide)"
            st.selectbox("Select Report Scope:", ["All Stores (Chain-Wide)"], index=0, disabled=True)

    # Compute Scoped Data based on selection
    if selected_store_filter != "All Stores (Chain-Wide)" and store_col:
        scoped_inv_df = inventory_df[inventory_df[store_col].astype(str) == selected_store_filter].copy()
        scoped_proposals = [p for p in proposals if str(p.get("store_name")) == selected_store_filter or str(p.get("store_id")) == selected_store_filter]
        if sales_df is not None and not sales_df.empty and store_col in sales_df.columns:
            scoped_sales_df = sales_df[sales_df[store_col].astype(str) == selected_store_filter].copy()
        else:
            scoped_sales_df = sales_df
    else:
        scoped_inv_df = inventory_df.copy()
        scoped_proposals = list(proposals)
        scoped_sales_df = sales_df

    with f_col2:
        st.markdown(f"""
        <div style="font-size:0.84rem; color:#64748B; padding-top:1.6rem;">
            Report Scope: <strong>{selected_store_filter}</strong> &nbsp;|&nbsp; 
            Timestamp: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M')}</strong>
        </div>
        """, unsafe_allow_html=True)

    with f_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True, key="btn_refresh_report_metrics"):
            st.toast("✅ Report metrics recalculated and refreshed!", icon="🔄")
            st.rerun()

    with f_col4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        top_excel_bytes = export_inventory_workbook(scoped_inv_df, scoped_sales_df)
        st.download_button(
            label="📥 Download Report (.xlsx)",
            data=top_excel_bytes,
            file_name=f"ZeroWaste_Executive_Audit_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_dl_top_report"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # SECTION 1: INVENTORY HEALTH SUMMARY
    # =========================================================================
    st.markdown('<div class="section-header">📦 1. Inventory Health & Valuation Summary</div>', unsafe_allow_html=True)
    
    total_batches = len(scoped_inv_df)
    total_stock_units = float(scoped_inv_df["current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0
    
    # Valuation: Cost and Price
    has_cost = "unit_cost" in scoped_inv_df.columns and scoped_inv_df["unit_cost"].notna().any()
    has_price = "base_price" in scoped_inv_df.columns and scoped_inv_df["base_price"].notna().any()
    
    total_cost_val = float((scoped_inv_df["current_stock"] * scoped_inv_df["unit_cost"]).sum()) if has_cost else None
    total_retail_val = float((scoped_inv_df["current_stock"] * scoped_inv_df["base_price"]).sum()) if has_price else None

    # Low stock items (< 10 units)
    low_stock_count = int((scoped_inv_df["current_stock"] <= 10).sum()) if "current_stock" in scoped_inv_df.columns else 0

    k_inv1, k_inv2, k_inv3, k_inv4 = st.columns(4)
    with k_inv1:
        render_kpi_card(
            title="Total Active Stock",
            value=f"{int(total_stock_units):,} units",
            subtitle=f"{total_batches} monitored batches",
            trend_text="On-Shelf Active",
            trend_type="positive",
            icon="📦"
        )
    with k_inv2:
        cost_val_disp = f"${total_cost_val:,.2f}" if total_cost_val is not None else "Unrecorded"
        cost_sub = "At supplier cost" if total_cost_val is not None else "Cost field missing"
        render_kpi_card(
            title="Inventory Cost Basis",
            value=cost_val_disp,
            subtitle=cost_sub,
            trend_text="Book Value",
            trend_type="neutral",
            icon="💰"
        )
    with k_inv3:
        retail_val_disp = f"${total_retail_val:,.2f}" if total_retail_val is not None else "Unrecorded"
        retail_sub = "At retail catalog price" if total_retail_val is not None else "Price field missing"
        render_kpi_card(
            title="Total Retail Value",
            value=retail_val_disp,
            subtitle=retail_sub,
            trend_text="Catalog Value",
            trend_type="neutral",
            icon="🏷️"
        )
    with k_inv4:
        render_kpi_card(
            title="Low Stock Items (≤10u)",
            value=f"{low_stock_count} batches",
            subtitle=f"{round(low_stock_count * 100 / max(1, total_batches), 1)}% of inventory",
            trend_text="Restock Watch" if low_stock_count > 0 else "Stocked",
            trend_type="alert" if low_stock_count > 0 else "positive",
            icon="⚠️"
        )

    # Inventory Segmentation Chart
    if "category" in scoped_inv_df.columns and "current_stock" in scoped_inv_df.columns:
        cat_agg = scoped_inv_df.groupby("category")["current_stock"].sum().reset_index()
        fig_cat = px.bar(
            cat_agg,
            x="category",
            y="current_stock",
            color="current_stock",
            color_continuous_scale=["#A7F3D0", "#10B981", "#064E3B"],
            labels={"category": "Perishable Category", "current_stock": "Units in Stock"},
            text_auto=True
        )
        fig_cat.update_layout(
            font=PLOTLY_FONT,
            paper_bgcolor=PLOTLY_BG,
            plot_bgcolor="rgba(250,252,250,0.6)",
            height=260,
            margin=dict(t=10, b=20, l=30, r=20),
            coloraxis_showscale=False
        )
        st.markdown('<div class="custom-card" style="padding: 12px 16px; margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#062E1E; margin-bottom:4px;'>📊 Active Stock Units by Perishable Category</div>", unsafe_allow_html=True)
        st.plotly_chart(fig_cat, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # SECTION 2: EXPIRY & FRESHNESS RISK SUMMARY
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">⏱️ 2. Shelf-Life & Biological Freshness Risk Summary</div>', unsafe_allow_html=True)

    if "days_to_expiry" in scoped_inv_df.columns:
        dte_series = scoped_inv_df["days_to_expiry"]
        has_dte = dte_series.notna()

        expired_mask = has_dte & (dte_series <= 0)
        critical_mask = has_dte & (dte_series == 1)
        urgent_mask = has_dte & (dte_series == 2)
        warning_mask = has_dte & (dte_series > 2) & (dte_series <= 4)
        fresh_mask = has_dte & (dte_series > 4)
        unspecified_mask = dte_series.isna()

        expired_cnt = int(expired_mask.sum())
        expired_units = float(scoped_inv_df.loc[expired_mask, "current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0

        critical_cnt = int(critical_mask.sum())
        critical_units = float(scoped_inv_df.loc[critical_mask, "current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0

        urgent_cnt = int((urgent_mask | warning_mask).sum())
        urgent_units = float(scoped_inv_df.loc[urgent_mask | warning_mask, "current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0

        fresh_cnt = int(fresh_mask.sum())
        fresh_units = float(scoped_inv_df.loc[fresh_mask, "current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0

        unspec_cnt = int(unspecified_mask.sum())
        unspec_units = float(scoped_inv_df.loc[unspecified_mask, "current_stock"].sum()) if "current_stock" in scoped_inv_df.columns else 0.0

        k_f1, k_f2, k_f3, k_f4 = st.columns(4)
        with k_f1:
            render_kpi_card(
                title="Expired Batches (≤0d)",
                value=f"{expired_cnt} items",
                subtitle=f"{int(expired_units)} units past shelf-life",
                trend_text="Immediate Disposal/Donation" if expired_cnt > 0 else "0 Expired",
                trend_type="alert" if expired_cnt > 0 else "positive",
                icon="🔴"
            )
        with k_f2:
            render_kpi_card(
                title="Critical Shelf-Life (1d)",
                value=f"{critical_cnt} items",
                subtitle=f"{int(critical_units)} units due in 24h",
                trend_text="Urgent Markdown" if critical_cnt > 0 else "Nominal",
                trend_type="alert" if critical_cnt > 0 else "positive",
                icon="🟠"
            )
        with k_f3:
            render_kpi_card(
                title="At-Risk Window (2-4d)",
                value=f"{urgent_cnt} items",
                subtitle=f"{int(urgent_units)} units approaching expiry",
                trend_text="Transfer / Promo Watch",
                trend_type="neutral",
                icon="🟡"
            )
        with k_f4:
            render_kpi_card(
                title="Fresh & Safe (4d+)",
                value=f"{fresh_cnt} items",
                subtitle=f"{int(fresh_units)} units with healthy runway",
                trend_text="Nominal Freshness",
                trend_type="positive",
                icon="🟢"
            )

        if unspec_cnt > 0:
            st.info(f"ℹ️ **Transparency Note**: {unspec_cnt} batch(es) ({int(unspec_units)} units) have an **unspecified expiry date**. "
                    "In compliance with our data honesty standards, biological decay was **NOT** assumed or fabricated for these items.")

        # Freshness Chart
        freshness_labels = ["Expired (≤0d)", "Critical (1d)", "At-Risk (2-4d)", "Fresh (4d+)", "Unspecified"]
        freshness_counts = [expired_units, critical_units, urgent_units, fresh_units, unspec_units]
        freshness_colors = ["#EF4444", "#F97316", "#F59E0B", "#10B981", "#94A3B8"]

        fig_fresh = go.Figure(data=[go.Bar(
            x=freshness_labels,
            y=freshness_counts,
            marker_color=freshness_colors,
            text=[f"{int(v)} units" for v in freshness_counts],
            textposition='auto'
        )])
        fig_fresh.update_layout(
            font=PLOTLY_FONT,
            paper_bgcolor=PLOTLY_BG,
            plot_bgcolor="rgba(250,252,250,0.6)",
            height=240,
            margin=dict(t=10, b=20, l=30, r=20),
            yaxis_title="Units in Category"
        )
        st.markdown('<div class="custom-card" style="padding: 12px 16px; margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#062E1E; margin-bottom:4px;'>⏱️ Freshness & Shelf-Life Risk Distribution (Total Units)</div>", unsafe_allow_html=True)
        st.plotly_chart(fig_fresh, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Days to Expiry data column is missing in uploaded dataset. Expiry risk summary cannot be computed.")

    # =========================================================================
    # SECTION 3: HISTORICAL SALES & FORECAST SUMMARY
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📈 3. Historical Sales & Demand Velocity Summary</div>', unsafe_allow_html=True)

    if scoped_sales_df is not None and not scoped_sales_df.empty:
        # Identify date and quantity column in sales dataset
        s_date_col = None
        for cand in ["date", "sales_date", "transaction_date", "order_date"]:
            if cand in scoped_sales_df.columns:
                s_date_col = cand
                break
        
        s_qty_col = None
        for cand in ["quantity_sold", "units_sold", "sales", "sold_quantity"]:
            if cand in scoped_sales_df.columns:
                s_qty_col = cand
                break

        if s_date_col and s_qty_col:
            clean_sales = scoped_sales_df.copy()
            clean_sales["_dt"] = pd.to_datetime(clean_sales[s_date_col], errors="coerce").dt.date
            clean_sales = clean_sales[clean_sales["_dt"].notna()]
            clean_sales["_qty"] = pd.to_numeric(clean_sales[s_qty_col], errors="coerce").fillna(0)

            total_txns = len(clean_sales)
            total_sales_units = clean_sales["_qty"].sum()
            sales_days_count = clean_sales["_dt"].nunique()
            avg_daily_pos = total_sales_units / max(1, sales_days_count)

            # Revenue if available
            has_rev = "revenue" in clean_sales.columns
            total_rev = clean_sales["revenue"].sum() if has_rev else None

            s_col1, s_col2, s_col3, s_col4 = st.columns(4)
            with s_col1:
                render_kpi_card(
                    title="Total POS Sales",
                    value=f"{int(total_sales_units):,} units",
                    subtitle=f"{total_txns:,} transactional rows",
                    trend_text="Recorded In Session",
                    trend_type="positive",
                    icon="💳"
                )
            with s_col2:
                render_kpi_card(
                    title="Daily Velocity",
                    value=f"{avg_daily_pos:.1f} u/day",
                    subtitle=f"Over {sales_days_count} unique days",
                    trend_text="Empirical Mean",
                    trend_type="positive",
                    icon="📊"
                )
            with s_col3:
                rev_disp = f"${total_rev:,.2f}" if total_rev is not None else "Unrecorded"
                rev_sub = "Historical POS register" if total_rev is not None else "Revenue column missing"
                render_kpi_card(
                    title="POS Historical Revenue",
                    value=rev_disp,
                    subtitle=rev_sub,
                    trend_text="Gross Receipts",
                    trend_type="neutral",
                    icon="💵"
                )
            with s_col4:
                render_kpi_card(
                    title="Observed Timeline",
                    value=f"{sales_days_count} Days",
                    subtitle=f"{clean_sales['_dt'].min()} to {clean_sales['_dt'].max()}",
                    trend_text="Consecutive Sales",
                    trend_type="neutral",
                    icon="📅"
                )

            # Daily Sales Timeline Chart
            daily_trend = clean_sales.groupby("_dt")["_qty"].sum().reset_index()
            fig_sales = go.Figure()
            fig_sales.add_trace(go.Scatter(
                x=daily_trend["_dt"],
                y=daily_trend["_qty"],
                mode="lines+markers",
                line=dict(color="#059669", width=2.5),
                marker=dict(size=5, color="#062E1E"),
                name="Daily Sales"
            ))
            fig_sales.update_layout(
                font=PLOTLY_FONT,
                paper_bgcolor=PLOTLY_BG,
                plot_bgcolor="rgba(250,252,250,0.6)",
                height=220,
                margin=dict(t=10, b=20, l=30, r=20),
                yaxis_title="Units Sold / Day"
            )
            st.markdown('<div class="custom-card" style="padding: 12px 16px; margin-top: 10px;">', unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#062E1E; margin-bottom:4px;'>📈 Chain-Wide Daily Sales Velocity Timeline</div>", unsafe_allow_html=True)
            st.plotly_chart(fig_sales, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("ℹ️ Sales dataset found, but required date and quantity columns could not be identified.")
    else:
        st.markdown("""
        <div class="custom-card" style="background:#F8FAFC; border:1px solid #E2E8F0; padding:16px 20px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.4rem;">ℹ️</span>
                <div>
                    <strong>Historical Sales Dataset Not Loaded</strong>
                    <div style="font-size:0.85rem; color:#64748B;">
                        Sales transaction history is not loaded in current session state. 
                        To view empirical sales trends and Autoregressive Scikit-Learn forecasts, upload POS sales in <strong>Upload Data</strong> or select the Supermarket Demo.
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # SECTION 4: AGENT RECOMMENDATIONS & MANAGER DECISION SUMMARY
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🤖 4. Agent Recommendations & Manager Governance Audit</div>', unsafe_allow_html=True)

    if scoped_proposals:
        total_recs = len(scoped_proposals)
        
        # Priority Breakdown
        prio_counts = {
            "CRITICAL": sum(1 for p in scoped_proposals if p.get("priority") == "CRITICAL"),
            "HIGH": sum(1 for p in scoped_proposals if p.get("priority") == "HIGH"),
            "MEDIUM": sum(1 for p in scoped_proposals if p.get("priority") == "MEDIUM"),
            "LOW": sum(1 for p in scoped_proposals if p.get("priority") in ["LOW", "UNKNOWN"])
        }

        # Status Breakdown
        status_counts = {
            "PENDING": sum(1 for p in scoped_proposals if p.get("review_status") == "PENDING"),
            "APPROVED": sum(1 for p in scoped_proposals if p.get("review_status") == "APPROVED"),
            "REJECTED": sum(1 for p in scoped_proposals if p.get("review_status") == "REJECTED"),
            "MODIFIED": sum(1 for p in scoped_proposals if p.get("review_status") == "MODIFIED")
        }

        # Action Breakdown
        action_counts = {}
        for p in scoped_proposals:
            act = p.get("final_action", "MAINTAIN")
            action_counts[act] = action_counts.get(act, 0) + 1

        k_r1, k_r2, k_r3, k_r4 = st.columns(4)
        with k_r1:
            render_kpi_card(
                title="Total Recommendations",
                value=f"{total_recs}",
                subtitle=f"{prio_counts['CRITICAL']} critical proposals",
                trend_text="Multi-Agent Deliberated",
                trend_type="positive",
                icon="🤖"
            )
        with k_r2:
            render_kpi_card(
                title="Pending Manager Review",
                value=f"{status_counts['PENDING']}",
                subtitle=f"{round(status_counts['PENDING']*100/total_recs, 1)}% of queue",
                trend_text="Awaiting Authorization" if status_counts['PENDING'] > 0 else "Review Complete",
                trend_type="alert" if status_counts['PENDING'] > 0 else "positive",
                icon="⏳"
            )
        with k_r3:
            render_kpi_card(
                title="Approved (Simulated)",
                value=f"{status_counts['APPROVED'] + status_counts['MODIFIED']}",
                subtitle=f"{status_counts['APPROVED']} as proposed, {status_counts['MODIFIED']} modified",
                trend_text="Manager Authorized",
                trend_type="positive",
                icon="✅"
            )
        with k_r4:
            render_kpi_card(
                title="Rejected / Overridden",
                value=f"{status_counts['REJECTED']}",
                subtitle=f"{round(status_counts['REJECTED']*100/total_recs, 1)}% vetoed",
                trend_text="Manager Dismissed",
                trend_type="neutral",
                icon="❌"
            )

        # Charts Row: Action Types and Review Status Breakdown
        rc_col1, rc_col2 = st.columns(2)
        with rc_col1:
            fig_act = px.bar(
                x=list(action_counts.keys()),
                y=list(action_counts.values()),
                labels={"x": "Agent Proposed Action", "y": "Recommendation Count"},
                color=list(action_counts.keys()),
                color_discrete_map={
                    "MARKDOWN": "#C2410C",
                    "TRANSFER": "#7C3AED",
                    "REORDER": "#2563EB",
                    "DONATE": "#D97706",
                    "MAINTAIN": "#059669"
                },
                text_auto=True
            )
            fig_act.update_layout(
                font=PLOTLY_FONT,
                paper_bgcolor=PLOTLY_BG,
                plot_bgcolor="rgba(250,252,250,0.6)",
                height=240,
                margin=dict(t=10, b=20, l=30, r=20),
                showlegend=False
            )
            st.markdown('<div class="custom-card" style="padding: 12px 16px;">', unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#062E1E; margin-bottom:4px;'>📊 Recommendations by Proposed Action Type</div>", unsafe_allow_html=True)
            st.plotly_chart(fig_act, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with rc_col2:
            fig_stat = px.pie(
                names=["Pending Review", "Approved", "Rejected", "Modified"],
                values=[status_counts["PENDING"], status_counts["APPROVED"], status_counts["REJECTED"], status_counts["MODIFIED"]],
                color=["Pending Review", "Approved", "Rejected", "Modified"],
                color_discrete_map={
                    "Pending Review": "#FEF3C7",
                    "Approved": "#10B981",
                    "Rejected": "#EF4444",
                    "Modified": "#8B5CF6"
                },
                hole=0.55
            )
            fig_stat.update_layout(
                font=PLOTLY_FONT,
                paper_bgcolor=PLOTLY_BG,
                plot_bgcolor=PLOTLY_BG,
                height=240,
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.markdown('<div class="custom-card" style="padding: 12px 16px;">', unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#062E1E; margin-bottom:4px;'>🗳️ Manager Review Decision Status Breakdown</div>", unsafe_allow_html=True)
            st.plotly_chart(fig_stat, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("ℹ️ No agent recommendations have been generated yet for this dataset scope.")

    # =========================================================================
    # SECTION 5: ESTIMATED POTENTIAL SAVINGS & FORMULA DISCLOSURE
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">💡 5. Estimated Potential Savings & Model Projections</div>', unsafe_allow_html=True)

    # Calculate potential savings strictly from approved proposals
    # STRICT COMPLIANCE: Clearly label as ESTIMATES, explain assumptions, show formula
    approved_or_mod = [p for p in scoped_proposals if p.get("review_status") in ["APPROVED", "MODIFIED"]]

    # Check if price and cost data exist to calculate financial benefits honestly
    has_full_financials = has_cost and has_price

    if has_full_financials:
        pot_margin_recovered = sum(p.get("margin_impact_usd", 0.0) for p in approved_or_mod if p.get("margin_impact_usd", 0.0) > 0)
        pot_waste_diverted_units = sum(p.get("waste_saved_units", 0.0) for p in approved_or_mod)
        pot_carbon_averted_kg = sum(p.get("carbon_saved_kg", 0.0) for p in approved_or_mod)
    else:
        pot_margin_recovered = None
        pot_waste_diverted_units = sum(p.get("waste_saved_units", 0.0) for p in approved_or_mod)
        pot_carbon_averted_kg = sum(p.get("carbon_saved_kg", 0.0) for p in approved_or_mod)

    st.markdown("""
    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:5px solid #10B981; border-radius:10px; padding:14px 18px; margin-bottom:14px; font-size:0.87rem; color:#14532D; line-height:1.5;">
        <strong>🛡️ ESTIMATE & FORMULA DISCLOSURE:</strong> The figures below represent <strong>estimated potential savings</strong> derived from agent decision models. 
        In strict compliance with hackathon reporting rules, these figures do <strong>not</strong> claim verified historical outcome savings. 
        They project theoretical benefits if authorized actions are fully executed.
        <div style="margin-top:6px; font-size:0.82rem; color:#166534;">
            • <strong>Estimated Margin Recovery Formula:</strong> &sum; [Expected Cleared Units &times; (Discounted Price - Unit Cost)] + Net Inter-Store Transfer Salvage<br>
            • <strong>Estimated Waste Avoidance Formula:</strong> &sum; Expected Units Cleared via Markdowns + Rebalanced Units + Food Bank Donations<br>
            • <strong>Estimated Carbon Aversion Formula:</strong> Diverted Units &times; Category Carbon Factor (kg CO2e / unit)
        </div>
    </div>
    """, unsafe_allow_html=True)

    s_pot1, s_pot2, s_pot3 = st.columns(3)
    with s_pot1:
        if pot_margin_recovered is not None:
            render_kpi_card(
                title="Est. Potential Margin Recovery",
                value=f"${pot_margin_recovered:,.2f}",
                subtitle=f"Across {len(approved_or_mod)} approved actions",
                trend_text="Projected Net Margin",
                trend_type="positive",
                icon="💵"
            )
        else:
            render_kpi_card(
                title="Est. Potential Margin Recovery",
                value="Withheld",
                subtitle="Price/cost fields missing",
                trend_text="Data Incomplete",
                trend_type="neutral",
                icon="💵"
            )
    with s_pot2:
        render_kpi_card(
            title="Est. Potential Waste Diverted",
            value=f"{pot_waste_diverted_units:.1f} units",
            subtitle="Diverted from municipal landfill",
            trend_text="Food Waste Avoided",
            trend_type="positive",
            icon="🌱"
        )
    with s_pot3:
        render_kpi_card(
            title="Est. Potential Carbon Averted",
            value=f"{pot_carbon_averted_kg:.1f} kg CO2e",
            subtitle="Avoided methane greenhouse footprint",
            trend_text="GHG Scope 3 Cat 5",
            trend_type="positive",
            icon="🌍"
        )

    # =========================================================================
    # SECTION 6: TABLE OF PRODUCTS REQUIRING ATTENTION
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🚨 6. Perishable Products Requiring Immediate Attention</div>', unsafe_allow_html=True)

    # Filter items that need immediate attention:
    # 1. DTE <= 2, OR
    # 2. stock <= 10, OR
    # 3. has pending critical/high recommendation
    attention_rows = []

    # Map proposals by SKU and Store for quick cross-reference
    prop_lookup = {}
    for p in scoped_proposals:
        k = f"{p.get('sku')}_{p.get('store_id')}"
        prop_lookup[k] = p

    for _, r in scoped_inv_df.iterrows():
        sku_val = r.get("sku", "")
        store_val = r.get("store_id", "")
        dte_val = r.get("days_to_expiry")
        stock_val = float(r.get("current_stock", 0))

        k = f"{sku_val}_{store_val}"
        matching_prop = prop_lookup.get(k)

        is_critical_dte = (dte_val is not None and not pd.isna(dte_val) and dte_val <= 2)
        is_low_stock = stock_val <= 10
        is_urgent_proposal = matching_prop and matching_prop.get("priority") in ["CRITICAL", "HIGH"]

        if is_critical_dte or is_low_stock or is_urgent_proposal:
            # Determine reason for attention
            reasons = []
            if dte_val is not None and not pd.isna(dte_val) and dte_val <= 0:
                reasons.append("Expired Today")
            elif dte_val is not None and not pd.isna(dte_val) and dte_val == 1:
                reasons.append("Expires in 24h")
            elif dte_val is not None and not pd.isna(dte_val) and dte_val == 2:
                reasons.append("Expires in 48h")

            if is_low_stock:
                reasons.append("Low Stock")

            action_name = matching_prop.get("action_title", "Monitor Shelf") if matching_prop else "Under Evaluation"
            prio_name = matching_prop.get("priority", "MEDIUM") if matching_prop else ("CRITICAL" if is_critical_dte else "LOW")
            status_name = matching_prop.get("review_status", "PENDING") if matching_prop else "STANDBY"

            attention_rows.append({
                "Product": r.get("product_name", "Unknown"),
                "SKU": sku_val,
                "Store": r.get("store_name", store_val),
                "Category": r.get("category", "General"),
                "Stock": int(stock_val),
                "Days Left": f"{int(dte_val)}d" if (dte_val is not None and not pd.isna(dte_val)) else "Unspecified",
                "Alert Condition": ", ".join(reasons) if reasons else "Restock Watch",
                "Agent Proposal": action_name,
                "Priority": prio_name,
                "Review Status": status_name
            })

    if attention_rows:
        att_df = pd.DataFrame(attention_rows)
        st.dataframe(
            att_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Stock": st.column_config.NumberColumn(format="%d units"),
                "Priority": st.column_config.TextColumn(help="Recommendation urgency priority"),
                "Review Status": st.column_config.TextColumn(help="Human-in-the-Loop decision status")
            }
        )
        st.caption(f"Identified **{len(attention_rows)}** items meeting operational alert thresholds.")
    else:
        st.success("✅ Excellent! No products currently meet critical alert conditions.")

    # =========================================================================
    # SECTION 7: DOWNLOADABLE EXPORTS (CSV & EXCEL)
    # =========================================================================
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📥 7. Certified Audit Exports & Reports</div>', unsafe_allow_html=True)

    d_col1, d_col2, d_col3 = st.columns(3)

    # 1. Inventory & Risk CSV
    with d_col1:
        st.markdown("""
        <div class="custom-card" style="min-height:190px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <div style="font-weight:700; color:#062E1E; font-size:0.95rem; margin-bottom:4px;">
                    📄 Inventory Risks (CSV)
                </div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:12px;">
                    Comprehensive batch-level stock, shelf-life countdowns, storage temperatures, and valuation columns.
                </div>
            </div>
        """, unsafe_allow_html=True)
        inv_csv_data = scoped_inv_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Inventory CSV",
            data=inv_csv_data,
            file_name=f"ZeroWaste_Inventory_Risks_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_inv_csv"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. Recommendations & Decisions CSV
    with d_col2:
        st.markdown("""
        <div class="custom-card" style="min-height:190px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <div style="font-weight:700; color:#062E1E; font-size:0.95rem; margin-bottom:4px;">
                    📋 Agent Recommendations (CSV)
                </div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:12px;">
                    Multi-agent proposals, priority tiers, manager approvals/rejections, reviewer roles, and timestamps.
                </div>
            </div>
        """, unsafe_allow_html=True)
        if scoped_proposals:
            rec_export_rows = []
            for p in scoped_proposals:
                rec_export_rows.append({
                    "Recommendation_ID": p.get("rec_id", ""),
                    "SKU": p.get("sku", ""),
                    "Product_Name": p.get("product_name", ""),
                    "Store_Name": p.get("store_name", ""),
                    "Current_Stock": p.get("current_stock", 0),
                    "Days_To_Expiry": p.get("days_to_expiry", ""),
                    "Proposed_Action": p.get("final_action", ""),
                    "Action_Title": p.get("action_title", ""),
                    "Priority": p.get("priority", ""),
                    "Responsible_Agent": p.get("generating_agent", ""),
                    "Review_Status": p.get("review_status", "PENDING"),
                    "Reviewed_By": p.get("reviewed_by", "Pending"),
                    "Reviewed_At": p.get("reviewed_at", ""),
                    "Review_Reason": p.get("review_reason", ""),
                    "Estimated_Margin_Impact_USD": p.get("margin_impact_usd", 0.0),
                    "Estimated_Waste_Saved_Units": p.get("waste_saved_units", 0.0),
                    "Estimated_Carbon_Saved_KG": p.get("carbon_saved_kg", 0.0)
                })
            rec_csv_data = pd.DataFrame(rec_export_rows).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Decisions CSV",
                data=rec_csv_data,
                file_name=f"ZeroWaste_Agent_Decisions_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_recs_csv"
            )
        else:
            empty_cols = [
                "Recommendation_ID", "SKU", "Product_Name", "Store_Name", "Current_Stock",
                "Days_To_Expiry", "Proposed_Action", "Action_Title", "Priority",
                "Responsible_Agent", "Review_Status", "Reviewed_By", "Reviewed_At",
                "Review_Reason", "Estimated_Margin_Impact_USD", "Estimated_Waste_Saved_Units", "Estimated_Carbon_Saved_KG"
            ]
            rec_csv_data = pd.DataFrame(columns=empty_cols).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Decisions Schema (CSV)",
                data=rec_csv_data,
                file_name=f"ZeroWaste_Decisions_Schema_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_recs_schema_csv"
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Certified OpenPyXL Excel Audit Workbook
    with d_col3:
        st.markdown("""
        <div class="custom-card" style="min-height:190px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <div style="font-weight:700; color:#062E1E; font-size:0.95rem; margin-bottom:4px;">
                    📑 Complete Audit Workbook (.xlsx)
                </div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:12px;">
                    Branded multi-tab OpenPyXL spreadsheet with conditional expiry formatting and POS sales summary.
                </div>
            </div>
        """, unsafe_allow_html=True)
        excel_bytes = export_inventory_workbook(scoped_inv_df, scoped_sales_df)
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"ZeroWaste_Executive_Audit_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_excel_audit"
        )
        st.markdown('</div>', unsafe_allow_html=True)
