"""
Page: Perishable Demand Forecast Studio
Zero-Waste Grocery · GDGoC HITAM
Predict Demand Before It Happens.

Provides:
- Modern analytics experience using Plotly charts and brand visual design system
- Summary cards: Historical Sales, Forecast Period, Products Forecasted, Forecast Quality
- Product, store, date-range, and forecast horizon selectors
- Rigorous forecasting pipeline:
    * Tier 1: Recent Average baseline (<5 days history)
    * Tier 2: Moving Average baseline with 2-day backtest (5-13 days)
    * Tier 3: Scikit-Learn Autoregressive Ridge Regression (>=14 days) with held-out temporal validation
- Strict zero future-information leakage
- Reliable evaluation metrics (MAE, RMSE, WAPE) only when calculable
- Probabilistic uncertainty bands (P10, P50, P90)
- Clear communication of missing dates, data insufficiency, and unavailable sales
- No fabrication of historical sales, forecasts, or model accuracy
- Interactive scenario testing for sufficient and insufficient sales history
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from components.ui import render_hero, render_kpi_card
from models.demand_forecaster import prepare_daily_sales_series, run_demand_forecast
from data.generator import generate_pos_sales_history

def render_demand_forecast_page():
    # 1. Page Hero Banner
    render_hero(
        title="Predict Demand Before It Happens.",
        subtitle="Dynamic multi-horizon demand forecasting powered by autoregressive machine learning and moving-average baselines with strict empirical validation and probabilistic uncertainty bounds.",
        badge_text="AUTONOMOUS DEMAND FORECASTING"
    )

    # 2. Retrieve Data from Session State
    sales_df = st.session_state.get("sales_df", None)
    inventory_df = st.session_state.get("inventory_df", None)

    # 3. Interactive Scenario Testing Toolbar
    with st.expander("🧪 Scenario Testing: Evaluate Sufficient vs. Insufficient Sales History", expanded=False):
        st.markdown("""
        <div style="font-size:0.86rem; color:#475569; margin-bottom:8px;">
            Test the demand forecasting engine under varying data conditions to verify that models, 
            charts, and evaluation metrics dynamically adapt without fabricating data:
        </div>
        """, unsafe_allow_html=True)
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            if st.button("🟢 Full 30-Day POS History\n(Sufficient Data → Scikit-Learn ML)", use_container_width=True, key="btn_test_30d"):
                st.session_state.sales_df = generate_pos_sales_history(days=30)
                st.session_state.scenario_name = "Full 30-Day POS History"
                st.rerun()
        with col_t2:
            if st.button("🟡 Moderate 8-Day History\n(Moderate Data → Moving Average)", use_container_width=True, key="btn_test_8d"):
                st.session_state.sales_df = generate_pos_sales_history(days=8)
                st.session_state.scenario_name = "Moderate 8-Day History"
                st.rerun()
        with col_t3:
            if st.button("🔴 Sparse 3-Day History\n(Insufficient Data → Recent Average)", use_container_width=True, key="btn_test_3d"):
                st.session_state.sales_df = generate_pos_sales_history(days=3)
                st.session_state.scenario_name = "Sparse 3-Day History"
                st.rerun()
        with col_t4:
            if st.button("⚪ Clear Sales History\n(Simulate Unavailable Sales Data)", use_container_width=True, key="btn_test_0d"):
                st.session_state.sales_df = pd.DataFrame()
                st.session_state.scenario_name = "No Sales Data"
                st.rerun()

    # 4. Check for Sales History Availability
    if sales_df is None or sales_df.empty:
        # Display Empty State & Guidance
        st.markdown("""
        <div class="custom-card" style="border-left: 5px solid #EA580C; background: #FFFDFB; padding: 20px 24px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.8rem;">⚠️</span>
                <div>
                    <h4 style="margin:0; color:#062E1E; font-family:'Space Grotesk';">No Historical Sales Records Available in Session State</h4>
                    <div style="font-size:0.88rem; color:#64748B; margin-top:4px;">
                        Demand forecasting models require empirical sales transaction history to learn patterns and calculate evaluation metrics.
                        Historical sales are <strong>never fabricated</strong>.
                    </div>
                </div>
            </div>
            <div style="margin-top:16px; font-size:0.85rem; color:#334155;">
                <strong>Next Steps:</strong>
                <ul style="margin-top:6px; margin-bottom:12px; padding-left:20px;">
                    <li>Upload your POS sales CSV/Excel in the <strong>Upload Data</strong> workspace.</li>
                    <li>Or click <strong>"Full 30-Day POS History"</strong> in the Scenario Testing toolbar above to explore the demonstration network.</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_e1, col_e2, col_e3 = st.columns([1.5, 1.2, 1.5])
        with col_e2:
            if st.button("📤 Go to Upload Data", type="primary", use_container_width=True, key="btn_forecast_go_upload"):
                st.session_state.current_page = "📤 Upload Data"
                st.rerun()

        # Empty Summary Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card("Historical Sales", "0 Units", "No transactions recorded", "Data Unavailable", "alert", "📉")
        with c2:
            render_kpi_card("Forecast Period", "N/A", "Awaiting sales data", "Standby", "neutral", "⏱️")
        with c3:
            render_kpi_card("Products Forecasted", "0 Products", "No sales in session", "None", "neutral", "📦")
        with c4:
            render_kpi_card("Forecast Quality", "Uncalculable", "Requires historical sales", "N/A", "neutral", "🎯")
        return

    # 5. Extract Product & Store Metadata
    # Detect SKU column
    sku_col = None
    for cand in ["sku", "product_id", "sku_id", "item_code"]:
        if cand in sales_df.columns:
            sku_col = cand
            break

    # Detect Product Name column
    pname_col = None
    for cand in ["product_name", "item_name", "product", "item"]:
        if cand in sales_df.columns:
            pname_col = cand
            break

    # Detect Store column
    store_col = None
    for cand in ["store_name", "store_id", "branch_id", "store"]:
        if cand in sales_df.columns:
            store_col = cand
            break

    # Build Product Options
    product_options = {}
    if sku_col and pname_col:
        unique_prods = sales_df[[sku_col, pname_col]].drop_duplicates().sort_values(pname_col)
        for _, r in unique_prods.iterrows():
            label = f"{r[pname_col]} ({r[sku_col]})"
            product_options[label] = {"sku": str(r[sku_col]), "name": str(r[pname_col])}
    elif sku_col:
        for s in sorted(sales_df[sku_col].astype(str).unique()):
            product_options[f"Product {s}"] = {"sku": s, "name": f"Product {s}"}
    elif pname_col:
        for p in sorted(sales_df[pname_col].astype(str).unique()):
            product_options[p] = {"sku": p, "name": p}
    else:
        product_options["All Sales Records (Combined)"] = {"sku": None, "name": "All Items"}

    # Build Store Options
    store_options = ["All Stores (Aggregated)"]
    if store_col:
        unique_stores = sorted(sales_df[store_col].astype(str).unique())
        store_options.extend(unique_stores)

    # 6. Filter & Selector Row
    st.markdown('<div class="custom-card" style="padding: 16px 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.6, 1.2, 1.2, 1.0])

    with f_col1:
        selected_prod_label = st.selectbox(
            "🍎 Select Product to Forecast:",
            options=list(product_options.keys()),
            index=0,
            help="Select the perishable SKU or product name to analyze."
        )
        selected_prod_info = product_options[selected_prod_label]
        target_sku = selected_prod_info["sku"]
        target_name = selected_prod_info["name"]

    with f_col2:
        selected_store = st.selectbox(
            "🏬 Store Location:",
            options=store_options,
            index=0,
            help="Filter sales history by individual store branch or analyze chain-wide aggregated sales."
        )

    with f_col3:
        # Date Lookback Selector
        lookback_options = [
            "All Available History",
            "Last 14 Days",
            "Last 7 Days"
        ]
        selected_lookback = st.selectbox(
            "📅 Historical Lookback:",
            options=lookback_options,
            index=0,
            help="Select temporal observation window for model training."
        )

    with f_col4:
        horizon_days = st.slider(
            "⏱️ Horizon:",
            min_value=3,
            max_value=14,
            value=7,
            step=1,
            help="Number of future days to forecast (out-of-sample prediction)."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # 7. Aggregate and Prepare Daily Time Series
    store_filter_arg = selected_store if selected_store != "All Stores (Aggregated)" else None
    daily_df, diag = prepare_daily_sales_series(
        sales_df=sales_df,
        sku=target_sku,
        store_name=store_filter_arg
    )

    if not diag["has_data"] or daily_df.empty:
        st.warning(f"⚠️ No sales history found matching **{target_name}** at **{selected_store}**.")
        return

    # Apply historical lookback filter if requested
    if selected_lookback == "Last 14 Days" and len(daily_df) > 14:
        daily_df = daily_df.tail(14).copy()
    elif selected_lookback == "Last 7 Days" and len(daily_df) > 7:
        daily_df = daily_df.tail(7).copy()

    # 8. Execute Multi-Tier Forecasting Pipeline
    forecast_results = run_demand_forecast(
        daily_df=daily_df,
        horizon_days=horizon_days,
        test_split_ratio=0.20
    )

    hist_df = forecast_results["historical_df"]
    backtest_df = forecast_results["backtest_df"]
    fc_df = forecast_results["forecast_df"]
    metrics = forecast_results["metrics"]
    model_name = forecast_results["model_name"]
    model_tier = forecast_results["model_tier"]
    explanation = forecast_results["explanation"]
    data_days = forecast_results["data_days"]

    # Calculate Summary Card Values
    total_hist_units = hist_df["quantity_sold"].sum() if not hist_df.empty else 0.0
    avg_hist_daily = hist_df["quantity_sold"].mean() if not hist_df.empty else 0.0
    
    fc_start_str = fc_df["date"].iloc[0].strftime("%b %d") if not fc_df.empty else "TBD"
    fc_end_str = fc_df["date"].iloc[-1].strftime("%b %d, %Y") if not fc_df.empty else "TBD"
    forecast_period_str = f"{horizon_days} Days"
    forecast_period_sub = f"{fc_start_str} – {fc_end_str}"

    total_products_count = len(product_options)

    # Forecast Quality Metrics
    mae_val = metrics.get("mae")
    rmse_val = metrics.get("rmse")
    wape_val = metrics.get("wape")

    if mae_val is not None:
        quality_val = f"MAE: {mae_val:.1f} units"
        quality_sub = f"RMSE: {rmse_val:.1f} | WAPE: {wape_val:.1f}%"
        quality_trend = "Empirically Validated"
        quality_type = "positive"
    else:
        quality_val = "Uncalculable"
        quality_sub = metrics.get("evaluation_status", "Insufficient history")
        quality_trend = "Data Sparse"
        quality_type = "alert" if data_days < 5 else "neutral"

    # 9. Render Summary KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            title="Historical Sales",
            value=f"{int(total_hist_units):,} units",
            subtitle=f"{data_days} days ({avg_hist_daily:.1f} u/day avg)",
            trend_text="Actual Recorded",
            trend_type="positive",
            icon="📊"
        )
    with c2:
        render_kpi_card(
            title="Forecast Period",
            value=forecast_period_str,
            subtitle=forecast_period_sub,
            trend_text="Out-of-Sample",
            trend_type="neutral",
            icon="⏱️"
        )
    with c3:
        render_kpi_card(
            title="Products Forecasted",
            value="1 Active SKU",
            subtitle=f"{target_name[:24]} ({total_products_count} catalog total)",
            trend_text="Target Scope",
            trend_type="neutral",
            icon="📦"
        )
    with c4:
        render_kpi_card(
            title="Forecast Quality",
            value=quality_val,
            subtitle=quality_sub,
            trend_text=quality_trend,
            trend_type=quality_type,
            icon="🎯"
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 10. Construct High-Aesthetic Plotly Line Chart
    fig = go.Figure()

    # Trace 1: Historical Actual Sales (Solid line with circular markers)
    fig.add_trace(go.Scatter(
        x=hist_df["date"],
        y=hist_df["quantity_sold"],
        mode="lines+markers",
        name="Historical Actual Sales",
        line=dict(color="#062E1E", width=2.5),
        marker=dict(size=6, color="#059669", symbol="circle"),
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Actual Sales: <b>%{y:.1f} units</b><extra></extra>"
    ))

    # Trace 2: Held-Out Backtest Predictions (if available)
    if not backtest_df.empty:
        fig.add_trace(go.Scatter(
            x=backtest_df["date"],
            y=backtest_df["predicted"],
            mode="lines+markers",
            name="Backtest Model Prediction (Held-Out Test)",
            line=dict(color="#7C3AED", width=2.2, dash="dash"),
            marker=dict(size=7, color="#8B5CF6", symbol="square"),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Backtest Prediction: <b>%{y:.1f} units</b><br>Actual: %{customdata:.1f} units<extra></extra>",
            customdata=backtest_df["actual"]
        ))

    # Trace 3 & 4: Future Uncertainty Band (P90 Upper and P10 Lower Shaded Fill)
    # Anchor to the last historical point for continuous visual flow
    last_hist_date = hist_df["date"].iloc[-1]
    last_hist_qty = hist_df["quantity_sold"].iloc[-1]

    band_dates = [last_hist_date] + list(fc_df["date"])
    band_p90 = [last_hist_qty] + list(fc_df["forecast_p90"])
    band_p10 = [last_hist_qty] + list(fc_df["forecast_p10"])
    band_p50 = [last_hist_qty] + list(fc_df["forecast_p50"])

    # P90 line (invisible upper boundary)
    fig.add_trace(go.Scatter(
        x=band_dates,
        y=band_p90,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))

    # P10 line with filled band
    fig.add_trace(go.Scatter(
        x=band_dates,
        y=band_p10,
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(16, 185, 129, 0.16)",
        name="80% Uncertainty Band (P10–P90)",
        hoverinfo="skip"
    ))

    # Trace 5: Future Forecast Demand (P50 Expected Velocity - Dashed Vibrant Green)
    fig.add_trace(go.Scatter(
        x=band_dates,
        y=band_p50,
        mode="lines+markers",
        name="Future Forecast Demand (P50 Expected)",
        line=dict(color="#10B981", width=3, dash="dot"),
        marker=dict(size=7, color="#059669", symbol="diamond"),
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Forecast (P50): <b>%{y:.1f} units</b><extra></extra>"
    ))

    # Vertical Cutoff Marker Line (Distinguishing Historical Observations from Future Predictions)
    fig.add_vline(
        x=last_hist_date,
        line_width=1.8,
        line_dash="dash",
        line_color="#94A3B8",
        annotation_text="Forecast Origin (Today)",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#475569", family="Plus Jakarta Sans")
    )

    # Chart Styling
    fig.update_layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#334155"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(250,252,250,0.6)",
        height=420,
        margin=dict(t=35, b=30, l=40, r=25),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#E2E8F0",
            borderwidth=1
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            title=None,
            tickformat="%b %d"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            title="Daily Sales & Demand (Units)",
            rangemode="tozero"
        )
    )

    st.markdown('<div class="custom-card" style="padding: 16px 20px;">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 11. Transparent Forecasting Method Explanation & Diagnostics
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    tier_badge_color = {
        "SCIKIT_LEARN_ML": "#DCFCE7; color:#15803D; border:1px solid #86EFAC;",
        "MOVING_AVERAGE": "#FEF3C7; color:#B45309; border:1px solid #FDE68A;",
        "RECENT_AVERAGE": "#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5;",
        "NO_DATA": "#F1F5F9; color:#475569; border:1px solid #CBD5E1;"
    }.get(model_tier, "#F1F5F9; color:#475569;")

    st.markdown(f"""
    <div class="custom-card" style="padding: 18px 22px; border-left: 5px solid #10B981;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
            <div style="font-size:1.05rem; font-weight:700; color:#062E1E; font-family:'Space Grotesk';">
                🧠 Forecasting Methodology & Model Governance
            </div>
            <span style="font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:12px; background:{tier_badge_color}">
                {model_name}
            </span>
        </div>
        <div style="font-size:0.88rem; color:#334155; line-height:1.5;">
            {explanation}
        </div>
        <div style="margin-top:12px; padding-top:10px; border-top:1px solid #F1F5F9; font-size:0.82rem; color:#64748B; display:flex; gap:20px; flex-wrap:wrap;">
            <span>📅 <strong>Historical Days Analyzed:</strong> {data_days} days</span>
            <span>🧩 <strong>Calendar Gaps Filled:</strong> {diag['missing_dates_filled']} day(s) with 0 units</span>
            <span>🛡️ <strong>Leakage Guarantee:</strong> Zero future lookahead during model training & backtest</span>
            <span>📊 <strong>Confidence Level:</strong> 80% (P10–P90 Interval)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 12. Detailed Daily Horizon Breakdown & CSV Export
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    with st.expander("📋 Detailed Horizon Breakdown Table & Export", expanded=False):
        # Prepare merged inspection table
        table_rows = []
        for _, r in fc_df.iterrows():
            f_dt = r["date"]
            dow_name = f_dt.strftime("%A")
            table_rows.append({
                "Date": f_dt.strftime("%Y-%m-%d"),
                "Day": dow_name,
                "Conservative (P10)": round(r["forecast_p10"], 1),
                "Expected Demand (P50)": round(r["forecast_p50"], 1),
                "Optimistic (P90)": round(r["forecast_p90"], 1),
                "Uncertainty Spread": round(r["forecast_p90"] - r["forecast_p10"], 1)
            })

        table_df = pd.DataFrame(table_rows)
        st.dataframe(table_df, use_container_width=True, hide_index=True)

        # CSV Download Button
        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Horizon Forecast CSV",
            data=csv_data,
            file_name=f"demand_forecast_{target_sku or 'all'}_{date.today().isoformat()}.csv",
            mime="text/csv"
        )
