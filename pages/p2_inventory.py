"""
Page 2: Live Perishable Inventory & Expiry Monitor
Zero-Waste Grocery · Agentic AI Approach

Features:
- Configurable thresholds for expiry warning window and low-stock safety buffer
- 4 primary summary KPI cards (Total Products, Low Stock, Expiring Soon, Expired Items)
- Color coding: Green (Healthy), Amber (Approaching Expiry/Low Stock), Orange (Urgent action), Red (Expired/Depleted)
- Strict expiry integrity: products with unspecified expiry dates are never assumed or labeled as expired
- Interactive Search, Multi-Filter (Stock, Expiry, Store, Category) & Sorting controls
- Dual Presentation: Full Inventory Table & Urgent Attention Card View
- CSV Export for filtered inventory & OpenPyXL styled multi-tab Excel audit reports
- Resilient graceful empty states and missing column fallbacks
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from components.ui import render_hero, render_overview_card
from data.excel_manager import export_inventory_workbook, safely_read_file
from data.normalizer import normalize_and_validate_inventory
from data.generator import generate_live_inventory, generate_pos_sales_history
from agents.coordinator import CoordinatorAgent

def compute_batch_alert_status(row: dict, expiry_threshold_days: int, low_stock_threshold_units: int) -> dict:
    """
    Evaluates individual batch shelf-life and stock health.
    Strictly preserves data integrity: missing expiry dates are NEVER labeled as expired.
    
    Color Tiers:
    - 'red': Expired (< 0d) or Depleted Out of Stock (0 units)
    - 'orange': Urgent action required (Expiring today or tomorrow, <= 1d)
    - 'amber': Approaching expiry (<= threshold days) or Low Stock (<= threshold units)
    - 'green': Healthy / Fresh shelf life
    - 'neutral': Unspecified / unknown expiry date with healthy stock
    """
    stock = row.get("current_stock")
    stock_val = int(stock) if (pd.notnull(stock) and stock is not None) else 0
    
    dte = row.get("days_to_expiry")
    has_dte = pd.notnull(dte) and dte is not None
    dte_val = int(round(float(dte))) if has_dte else None

    # 1. EXPIRED (Strictly requires verified expiry date < 0)
    if has_dte and dte_val < 0:
        days_past = abs(dte_val)
        return {
            "status": "EXPIRED",
            "status_label": f"Expired ({days_past}d ago)",
            "tier": "red",
            "badge_bg": "#FEE2E2",
            "badge_color": "#991B1B",
            "badge_border": "#FCA5A5",
            "is_urgent": True,
            "alert_reason": f"Product expired {days_past} day(s) ago. Audit immediately for disposal or non-food bio-diversion."
        }

    # 2. CRITICAL EXPIRY (Due today or tomorrow: <= 1 day)
    if has_dte and dte_val <= 1:
        time_desc = "Expires TODAY" if dte_val == 0 else "Expires TOMORROW"
        return {
            "status": "CRITICAL_EXPIRY",
            "status_label": f"Urgent ({time_desc})",
            "tier": "orange",
            "badge_bg": "#FFEDD5",
            "badge_color": "#C2410C",
            "badge_border": "#FDBA74",
            "is_urgent": True,
            "alert_reason": f"Only {dte_val} day(s) remaining before expiration date. Immediate dynamic markdown or food bank donation advised."
        }

    # 3. EXPIRING SOON (Within user-configured warning threshold)
    if has_dte and dte_val <= expiry_threshold_days:
        return {
            "status": "EXPIRING_SOON",
            "status_label": f"Expiring Soon ({dte_val}d left)",
            "tier": "amber",
            "badge_bg": "#FEF3C7",
            "badge_color": "#B45309",
            "badge_border": "#FDE68A",
            "is_urgent": True,
            "alert_reason": f"Within {dte_val} days of expiry (configured threshold ≤ {expiry_threshold_days}d). Apply preventive promotional discount."
        }

    # 4. OUT OF STOCK (Depleted inventory)
    if stock_val <= 0:
        return {
            "status": "OUT_OF_STOCK",
            "status_label": "Out of Stock (0 units)",
            "tier": "red",
            "badge_bg": "#FEE2E2",
            "badge_color": "#991B1B",
            "badge_border": "#FCA5A5",
            "is_urgent": True,
            "alert_reason": "Shelf quantity is completely depleted (0 units). Reorder necessary to prevent lost sales."
        }

    # 5. LOW STOCK (Stock <= configured safety threshold)
    if stock_val <= low_stock_threshold_units:
        return {
            "status": "LOW_STOCK",
            "status_label": f"Low Stock ({stock_val} units)",
            "tier": "amber",
            "badge_bg": "#FEF3C7",
            "badge_color": "#B45309",
            "badge_border": "#FDE68A",
            "is_urgent": True,
            "alert_reason": f"Current stock ({stock_val} units) is at or below safety buffer (≤ {low_stock_threshold_units} units). Restock review advised."
        }

    # 6. UNSPECIFIED EXPIRY (Missing or unrecorded expiry date)
    if not has_dte:
        return {
            "status": "UNSPECIFIED_EXPIRY",
            "status_label": "Expiry Unspecified",
            "tier": "neutral",
            "badge_bg": "#F1F5F9",
            "badge_color": "#475569",
            "badge_border": "#CBD5E1",
            "is_urgent": False,
            "alert_reason": "Expiry date was not recorded in uploaded dataset. Expiration hazard cannot be assumed."
        }

    # 7. HEALTHY / FRESH
    return {
        "status": "HEALTHY",
        "status_label": f"Fresh ({dte_val}d left)",
        "tier": "green",
        "badge_bg": "#DCFCE7",
        "badge_color": "#15803D",
        "badge_border": "#86EFAC",
        "is_urgent": False,
        "alert_reason": f"Sufficient shelf life ({dte_val} days remaining) and adequate stock runway ({stock_val} units)."
    }

def render_inventory_page():
    # 1. Page Header & Introduction
    render_hero(
        title="Live Perishable Inventory & Expiry Monitor",
        subtitle="Batch-level shelf-life tracking, cold-chain telemetry compliance, configurable alert thresholds, and multi-format audit reporting.",
        badge_text="LIVE INVENTORY MANAGEMENT"
    )

    inventory_df = st.session_state.get("inventory_df", None)

    # 2. Graceful Empty State (When no data is uploaded)
    if inventory_df is None or inventory_df.empty:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_overview_card(label="Total Products", is_empty=True, icon="📦", icon_bg="#F1F5F9")
        with c2: render_overview_card(label="Low Stock Items", is_empty=True, icon="⚠️", icon_bg="#F1F5F9")
        with c3: render_overview_card(label="Expiring Soon", is_empty=True, icon="⏱️", icon_bg="#F1F5F9")
        with c4: render_overview_card(label="Expired Items", is_empty=True, icon="🚨", icon_bg="#F1F5F9")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="custom-card" style="border: 2px dashed #94A3B8; text-align:center; padding: 2.5rem 1.5rem; background: #FAFCFA;">
            <div style="font-size: 2.8rem; margin-bottom: 0.5rem;">📂</div>
            <h3 style="color:#062E1E; font-family:'Space Grotesk', sans-serif; margin-bottom: 0.4rem;">
                No Inventory Data Active in Session
            </h3>
            <p style="color:#64748B; font-size: 0.95rem; max-width: 600px; margin: 0 auto 1.5rem auto;">
                Connect your supermarket inventory records by uploading a CSV or Excel spreadsheet, or load our pre-calibrated multi-store benchmark network to evaluate AI agent interventions.
            </p>
        </div>
        """, unsafe_allow_html=True)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("📤 Upload Store Inventory Dataset", type="primary", use_container_width=True, key="empty_go_upload"):
                st.session_state.current_page = "📤 Upload Data"
                st.rerun()
        with btn_c2:
            if st.button("🌱 Load Supermarket Benchmark Network", use_container_width=True, key="empty_load_demo"):
                with st.spinner("Generating supermarket batches and computing multi-agent consensus..."):
                    inv_df = generate_live_inventory()
                    sales_df = generate_pos_sales_history()
                    coord = CoordinatorAgent()
                    proposals = [coord.reconcile_batch(r.to_dict(), inv_df) for _, r in inv_df.iterrows()]
                    st.session_state.inventory_df = inv_df
                    st.session_state.sales_df = sales_df
                    st.session_state.coordinator_proposals = proposals
                    st.session_state.data_refreshed = True
                    st.rerun()
        return

    # Work with copy to preserve original session state
    df = inventory_df.copy()

    # Fallback missing standard columns gracefully
    if "product_name" not in df.columns:
        df["product_name"] = df["sku"] if "sku" in df.columns else "Item"
    if "current_stock" not in df.columns:
        df["current_stock"] = 0
    if "days_to_expiry" not in df.columns:
        df["days_to_expiry"] = None
    if "category" not in df.columns:
        df["category"] = "General Perishables"
    if "store_name" not in df.columns:
        df["store_name"] = "Store Central"
    if "batch_code" not in df.columns:
        df["batch_code"] = [f"LOT-{i+1:04d}" for i in range(len(df))]
    if "unit_cost" not in df.columns:
        df["unit_cost"] = 2.50
    if "base_price" not in df.columns:
        df["base_price"] = 4.50
    if "storage_temp_c" not in df.columns:
        df["storage_temp_c"] = 4.0
    if "expiry_date" not in df.columns:
        df["expiry_date"] = None

    # 3. Configurable Alert Thresholds Bar
    with st.expander("🎛️ Configure Alert Thresholds & Risk Parameters", expanded=False):
        th_col1, th_col2, th_col3 = st.columns([1.5, 1.5, 1.0])
        with th_col1:
            expiry_threshold = st.slider(
                "⏳ Expiry Warning Threshold (Days)",
                min_value=1,
                max_value=7,
                value=2,
                help="Batches expiring within this number of days are flagged in amber/orange as Expiring Soon."
            )
        with th_col2:
            low_stock_threshold = st.slider(
                "📦 Low-Stock Safety Threshold (Units)",
                min_value=1,
                max_value=50,
                value=15,
                help="Products with stock at or below this count trigger Low Stock alerts."
            )
        with th_col3:
            st.markdown(f"""
            <div style="font-size:0.8rem; color:#64748B; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px; margin-top:0.8rem;">
                <strong>Active Criteria:</strong><br>
                • Expiry: ≤ <strong>{expiry_threshold}d</strong><br>
                • Stock: ≤ <strong>{low_stock_threshold}u</strong>
            </div>
            """, unsafe_allow_html=True)

    if "expiry_threshold" not in locals():
        expiry_threshold = 2
    if "low_stock_threshold" not in locals():
        low_stock_threshold = 15

    # Compute alert metadata for every batch
    alert_meta = [
        compute_batch_alert_status(row.to_dict(), expiry_threshold, low_stock_threshold)
        for _, row in df.iterrows()
    ]
    df["alert_status"] = [m["status"] for m in alert_meta]
    df["alert_label"] = [m["status_label"] for m in alert_meta]
    df["alert_tier"] = [m["tier"] for m in alert_meta]
    df["alert_reason"] = [m["alert_reason"] for m in alert_meta]
    df["is_urgent"] = [m["is_urgent"] for m in alert_meta]

    # 4. Summary KPI Cards (Strictly calculated from real uploaded data)
    total_batches = len(df)
    total_skus = df["sku"].nunique() if "sku" in df.columns else total_batches
    total_units = int(df["current_stock"].sum())
    total_inventory_val = float((df["current_stock"] * df["unit_cost"]).sum())

    low_stock_batches = int((df["current_stock"] <= low_stock_threshold).sum())
    low_stock_units = int(df.loc[df["current_stock"] <= low_stock_threshold, "current_stock"].sum())

    has_expiry_mask = df["days_to_expiry"].notna()
    expiring_soon_mask = has_expiry_mask & (df["days_to_expiry"] >= 0) & (df["days_to_expiry"] <= expiry_threshold)
    expiring_soon_count = int(expiring_soon_mask.sum())
    expiring_soon_units = int(df.loc[expiring_soon_mask, "current_stock"].sum()) if expiring_soon_count > 0 else 0

    expired_mask = has_expiry_mask & (df["days_to_expiry"] < 0)
    expired_count = int(expired_mask.sum())
    expired_units = int(df.loc[expired_mask, "current_stock"].sum()) if expired_count > 0 else 0

    unspecified_expiry_count = int((~has_expiry_mask).sum())

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        render_overview_card(
            label="Total Products",
            value=f"{total_skus} SKUs",
            subtext=f"{total_batches} batches ({total_units:,} units | ${total_inventory_val:,.2f})",
            icon="📦",
            icon_bg="#DCFCE7",
            is_empty=False
        )
    with sc2:
        render_overview_card(
            label="Low Stock Items",
            value=f"{low_stock_batches} Batches",
            subtext=f"{low_stock_units} units below safety threshold (≤ {low_stock_threshold}u)",
            icon="⚠️",
            icon_bg="#FEF3C7",
            is_empty=False
        )
    with sc3:
        render_overview_card(
            label="Expiring Soon",
            value=f"{expiring_soon_count} Batches",
            subtext=f"{expiring_soon_units} units due within ≤ {expiry_threshold} days",
            icon="⏱️",
            icon_bg="#FFEDD5",
            is_empty=False
        )
    with sc4:
        render_overview_card(
            label="Expired Items",
            value=f"{expired_count} Batches",
            subtext=f"{expired_units} units past sell-by date" if expired_count > 0 else "0 verified expired items",
            icon="🚨",
            icon_bg="#FEE2E2" if expired_count > 0 else "#DCFCE7",
            is_empty=False
        )

    # Explanation callout for unrecorded expiry dates
    if unspecified_expiry_count > 0:
        st.markdown(f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:8px 14px; margin: 10px 0 14px 0; display:flex; justify-content:space-between; align-items:center; font-size:0.83rem;">
            <div>
                <span style="color:#64748B;">ℹ️ <strong>Expiry Integrity Note:</strong></span> 
                <span style="color:#334155;"><strong>{unspecified_expiry_count}</strong> item(s) have unspecified expiry dates. Their shelf-life status is preserved as Unspecified and was <strong>NOT</strong> assumed or treated as expired.</span>
            </div>
            <span style="background:#E2E8F0; color:#475569; font-size:0.75rem; padding:2px 8px; border-radius:10px; font-weight:600;">{unspecified_expiry_count} Unrecorded</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 5. Search, Filter & Sorting Bar
    st.markdown('<div class="section-header" style="margin-top:0;">🔍 Filter & Inspect Inventory Records</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4, fc5 = st.columns([1.5, 1.2, 1.2, 1.2, 1.3])

    with fc1:
        search_query = st.text_input("Search SKU or Name", placeholder="e.g. Avocado, Salmon, Milk", key="inv_search_q")

    with fc2:
        store_opts = ["All Stores"] + sorted(list(df["store_name"].astype(str).unique()))
        selected_store = st.selectbox("Store Location", store_opts, key="inv_store_sel")

    with fc3:
        cat_opts = ["All Categories"] + sorted(list(df["category"].astype(str).unique()))
        selected_cat = st.selectbox("Category", cat_opts, key="inv_cat_sel")

    with fc4:
        stock_filter = st.selectbox(
            "Stock Status",
            ["All Stock Levels", f"Low Stock (≤ {low_stock_threshold}u)", f"Healthy (> {low_stock_threshold}u)", "Out of Stock (0 units)"],
            key="inv_stock_sel"
        )

    with fc5:
        expiry_filter = st.selectbox(
            "Expiry Risk Window",
            ["All Batches", f"Expiring Soon (≤ {expiry_threshold}d)", "Expired (< 0d)", f"Fresh (> {expiry_threshold}d)", "Unspecified Expiry"],
            key="inv_exp_sel"
        )

    # Secondary sorting row
    sort_c1, sort_c2, sort_spacer = st.columns([1.5, 1.2, 3.3])
    with sort_c1:
        sort_by = st.selectbox(
            "Sort Records By:",
            ["Days to Expiry (Most Urgent First)", "Current Stock (Lowest First)", "Current Stock (Highest First)", "Product Name (A-Z)", "Inventory Value ($ Highest)"],
            key="inv_sort_by"
        )
    with sort_c2:
        view_mode = st.radio(
            "Presentation View:",
            ["📋 Table View", "🚨 Urgent Cards View"],
            horizontal=True,
            key="inv_view_mode"
        )

    # Apply Filtering Logic
    filtered_df = df.copy()

    if selected_store != "All Stores":
        filtered_df = filtered_df[filtered_df["store_name"] == selected_store]

    if selected_cat != "All Categories":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]

    if search_query:
        q = search_query.strip().lower()
        filtered_df = filtered_df[
            filtered_df["product_name"].astype(str).str.lower().str.contains(q) |
            filtered_df["sku"].astype(str).str.lower().str.contains(q) |
            filtered_df["batch_code"].astype(str).str.lower().str.contains(q)
        ]

    # Stock Filter
    if stock_filter == f"Low Stock (≤ {low_stock_threshold}u)":
        filtered_df = filtered_df[filtered_df["current_stock"] <= low_stock_threshold]
    elif stock_filter == f"Healthy (> {low_stock_threshold}u)":
        filtered_df = filtered_df[filtered_df["current_stock"] > low_stock_threshold]
    elif stock_filter == "Out of Stock (0 units)":
        filtered_df = filtered_df[filtered_df["current_stock"] <= 0]

    # Expiry Filter
    f_has_dte = filtered_df["days_to_expiry"].notna()
    if expiry_filter == f"Expiring Soon (≤ {expiry_threshold}d)":
        filtered_df = filtered_df[f_has_dte & (filtered_df["days_to_expiry"] >= 0) & (filtered_df["days_to_expiry"] <= expiry_threshold)]
    elif expiry_filter == "Expired (< 0d)":
        filtered_df = filtered_df[f_has_dte & (filtered_df["days_to_expiry"] < 0)]
    elif expiry_filter == f"Fresh (> {expiry_threshold}d)":
        filtered_df = filtered_df[f_has_dte & (filtered_df["days_to_expiry"] > expiry_threshold)]
    elif expiry_filter == "Unspecified Expiry":
        filtered_df = filtered_df[filtered_df["days_to_expiry"].isna()]

    # Sorting
    if sort_by == "Days to Expiry (Most Urgent First)":
        # Sort so known urgent days come first, None placed at bottom
        filtered_df = filtered_df.sort_values(by="days_to_expiry", ascending=True, na_position="last")
    elif sort_by == "Current Stock (Lowest First)":
        filtered_df = filtered_df.sort_values(by="current_stock", ascending=True)
    elif sort_by == "Current Stock (Highest First)":
        filtered_df = filtered_df.sort_values(by="current_stock", ascending=False)
    elif sort_by == "Product Name (A-Z)":
        filtered_df = filtered_df.sort_values(by="product_name", ascending=True)
    elif sort_by == "Inventory Value ($ Highest)":
        filtered_df["_temp_val"] = filtered_df["current_stock"] * filtered_df["unit_cost"]
        filtered_df = filtered_df.sort_values(by="_temp_val", ascending=False).drop(columns=["_temp_val"])

    # Active Results Metadata Bar
    filtered_val = float((filtered_df["current_stock"] * filtered_df["unit_cost"]).sum()) if not filtered_df.empty else 0.0
    filtered_units = int(filtered_df["current_stock"].sum()) if not filtered_df.empty else 0
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:10px 16px; margin: 12px 0; display:flex; justify-content:space-between; align-items:center;">
        <div>Showing <strong>{len(filtered_df)}</strong> of <strong>{len(df)}</strong> active batches &nbsp;|&nbsp; Matching Units: <strong>{filtered_units:,}</strong></div>
        <div style="color:#059669; font-weight:600;">Inventory Value: ${filtered_val:,.2f} at cost</div>
    </div>
    """, unsafe_allow_html=True)

    # 6. Display Mode: Table View or Urgent Attention Cards
    if filtered_df.empty:
        st.info("ℹ️ No inventory batches match your active search and filter criteria.")
    elif view_mode == "🚨 Urgent Cards View":
        # Card View for Products Requiring Urgent Action
        urgent_df = filtered_df[filtered_df["is_urgent"] == True]
        if urgent_df.empty:
            st.markdown("""
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:2rem; text-align:center; margin:1rem 0;">
                <span style="font-size:2.5rem;">🎉</span>
                <h4 style="color:#166534; font-family:'Space Grotesk'; margin:0.5rem 0 0.2rem 0;">All Clear in Current Selection!</h4>
                <div style="color:#4B5563; font-size:0.9rem;">
                    No batches in this filtered selection meet urgent attention criteria (all batches are within safe shelf-life and stock boundaries).
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**Showing {len(urgent_df)} batches requiring priority attention:**")
            card_cols = st.columns(3)
            for idx, (_, row) in enumerate(urgent_df.iterrows()):
                col_target = card_cols[idx % 3]
                status_color = row["alert_tier"]
                border_color = {"red": "#EF4444", "orange": "#EA580C", "amber": "#F59E0B"}.get(status_color, "#94A3B8")
                badge_bg = {"red": "#FEE2E2", "orange": "#FFEDD5", "amber": "#FEF3C7"}.get(status_color, "#F1F5F9")
                badge_fg = {"red": "#991B1B", "orange": "#C2410C", "amber": "#B45309"}.get(status_color, "#475569")
                
                dte_disp = f"{int(row['days_to_expiry'])}d remaining" if pd.notnull(row["days_to_expiry"]) else "Unspecified Expiry"
                if pd.notnull(row["days_to_expiry"]) and row["days_to_expiry"] < 0:
                    dte_disp = f"⚠️ Expired {abs(int(row['days_to_expiry']))}d ago"

                with col_target:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top: 4px solid {border_color}; border-radius:12px; padding:1rem; margin-bottom:1rem; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                            <span style="font-weight:700; color:#062E1E; font-size:1.02rem; line-height:1.2;">{row['product_name']}</span>
                            <span style="background:{badge_bg}; color:{badge_fg}; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:10px;">{row['alert_label']}</span>
                        </div>
                        <div style="font-size:0.78rem; color:#64748B; margin-bottom:8px;">
                            <code>{row['sku']}</code> &nbsp;•&nbsp; {row['store_name']} &nbsp;•&nbsp; <em>{row['category']}</em>
                        </div>
                        <div style="background:#F8FAFC; border-radius:8px; padding:8px; font-size:0.8rem; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="color:#64748B;">On-Shelf Stock:</span>
                                <strong>{row['current_stock']} units</strong>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                <span style="color:#64748B;">Shelf Life:</span>
                                <strong>{dte_disp}</strong>
                            </div>
                            <div style="display:flex; justify-content:space-between;">
                                <span style="color:#64748B;">Unit Cost / Retail:</span>
                                <span>${row['unit_cost']:.2f} / ${row['base_price']:.2f}</span>
                            </div>
                        </div>
                        <div style="font-size:0.78rem; color:#475569; background:#FFFBEB; border-left:3px solid {border_color}; padding:6px 8px; border-radius:0 6px 6px 0; line-height:1.3;">
                            <strong>Reason:</strong> {row['alert_reason']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        # Table View
        table_cols = [
            "batch_code", "store_name", "product_name", "category",
            "alert_label", "current_stock", "expiry_date", "days_to_expiry",
            "unit_cost", "base_price", "storage_temp_c", "alert_reason"
        ]
        view_df = filtered_df[[c for c in table_cols if c in filtered_df.columns]].copy()
        if "expiry_date" in view_df.columns:
            view_df["expiry_date"] = view_df["expiry_date"].astype(str).replace({"None": "Unspecified", "nan": "Unspecified"})

        st.dataframe(
            view_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "batch_code": st.column_config.TextColumn("Batch Code", width="small"),
                "store_name": st.column_config.TextColumn("Store Location", width="medium"),
                "product_name": st.column_config.TextColumn("Perishable Item", width="large"),
                "category": st.column_config.TextColumn("Category", width="small"),
                "alert_label": st.column_config.TextColumn("Health Status", help="Shelf-life & stock alert category", width="medium"),
                "current_stock": st.column_config.NumberColumn("Stock (Units)", format="%d", width="small"),
                "expiry_date": st.column_config.TextColumn("Expiry Date", width="small"),
                "days_to_expiry": st.column_config.NumberColumn("Days Left", help="Days remaining until use-by date", format="%d d", width="small"),
                "unit_cost": st.column_config.NumberColumn("Cost", format="$%.2f", width="small"),
                "base_price": st.column_config.NumberColumn("Retail", format="$%.2f", width="small"),
                "storage_temp_c": st.column_config.NumberColumn("Sensor Temp", format="%.1f °C", width="small"),
                "alert_reason": st.column_config.TextColumn("Alert Rationale", width="large")
            }
        )

    # 7. Action Row: Multi-Format Data Exports & Re-ingestion
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📁 Data Exports & Enterprise Reporting</div>', unsafe_allow_html=True)

    col_exp_csv, col_exp_xls, col_ingest = st.columns([1.1, 1.1, 1.2])

    with col_exp_csv:
        st.markdown("""
        <div class="custom-card" style="height: 100%; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <h4 style="color:#062E1E; margin-top:0;">CSV Inventory Export</h4>
                <p style="font-size:0.83rem; color:#64748B;">Download current filtered inventory records with all computed shelf-life and stock alert statuses.</p>
            </div>
        """, unsafe_allow_html=True)
        csv_bytes = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered CSV",
            data=csv_bytes,
            file_name=f"ZeroWaste_Inventory_Filtered_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_filtered_csv"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_exp_xls:
        st.markdown("""
        <div class="custom-card" style="height: 100%; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <h4 style="color:#062E1E; margin-top:0;">OpenPyXL Audit Workbook</h4>
                <p style="font-size:0.83rem; color:#64748B;">Multi-tab enterprise workbook (.xlsx) with emerald styling, auto-width headers, and expiry risk formatting.</p>
            </div>
        """, unsafe_allow_html=True)
        sales_df = getattr(st.session_state, "sales_df", None)
        excel_bytes = export_inventory_workbook(filtered_df, sales_df)
        st.download_button(
            label="📥 Download Excel Audit Workbook (.xlsx)",
            data=excel_bytes,
            file_name=f"ZeroWaste_Inventory_Audit_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_dl_audit_xlsx"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ingest:
        st.markdown("""
        <div class="custom-card" style="height: 100%;">
            <h4 style="color:#062E1E; margin-top:0;">Ingest Store Dataset</h4>
            <p style="font-size:0.83rem; color:#64748B;">Upload your grocery chain inventory file to run the multi-agent optimization against custom stock data.</p>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload .xlsx or .csv dataset", type=["xlsx", "csv"], key="inv_upload_quick")
        if uploaded_file is not None:
            raw_df, read_err = safely_read_file(uploaded_file)
            if read_err:
                st.error(f"Error reading uploaded file: {read_err}")
            else:
                res = normalize_and_validate_inventory(raw_df)
                if res["accepted_count"] > 0:
                    valid_df = res["valid_df"]
                    st.success(f"Validated {res['accepted_count']} records!")
                    if res["rejected_count"] > 0:
                        st.warning(f"{res['rejected_count']} rows rejected due to validation issues.")
                    if st.button("Apply Ingested Data to Active Session", type="primary", key="btn_apply_quick_ingest"):
                        coord = CoordinatorAgent()
                        proposals = [coord.reconcile_batch(r.to_dict(), valid_df) for _, r in valid_df.iterrows()]
                        st.session_state.raw_uploaded_df = raw_df.copy()
                        st.session_state.inventory_df = valid_df
                        st.session_state.coordinator_proposals = proposals
                        st.session_state.validation_summary = res
                        st.session_state.data_refreshed = True
                        st.rerun()
                else:
                    st.error(f"Ingestion failed: All {res['rejected_count']} rows failed validation.")
                    for r in res["rejected_details"][:3]:
                        st.error(f"Row {r['row_index']}: {'; '.join(r['reasons'])}")
        st.markdown('</div>', unsafe_allow_html=True)
