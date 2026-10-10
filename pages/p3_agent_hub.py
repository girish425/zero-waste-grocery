"""
Page 3: Agentic Multi-Agent Decision Hub
Deep inspection into agent reasoning, consensus arbitration, and live XAI explainability.
"""
import streamlit as st
import pandas as pd
from components.ui import render_hero, render_agent_thought_step, get_action_badge_html, get_urgency_badge_html
from components.charts import plot_forecast_trajectory, plot_biological_decay
from agents.coordinator import CoordinatorAgent

def render_agent_hub_page():
    render_hero(
        title="Agentic Multi-Agent Decision & Arbitration Hub",
        subtitle="Transparent inspection into autonomous agent personas: Demand Forecaster, Spoilage Evaluator, Restock Agent, Dynamic Markdown Agent, and Inter-Store Transfer Agent.",
        badge_text="SPECIALIZED AGENT ARCHITECTURE"
    )
    
    inventory_df = st.session_state.get("inventory_df", None)
    if inventory_df is None or inventory_df.empty:
        st.info("ℹ️ No active inventory records available to inspect agent consensus. Please upload store data or load the supermarket benchmark network.")
        if st.button("📤 Go to Upload Data", type="primary", key="btn_hub_upload"):
            st.session_state.current_page = "📤 Upload Data"
            st.rerun()
        return
    
    # Batch Selector
    st.markdown('<div class="section-header">🔍 Inspect Batch Multi-Agent Reasoning</div>', unsafe_allow_html=True)
    
    # Create descriptive batch labels for easy selection
    options = []
    for idx, row in inventory_df.iterrows():
        dte = row['days_to_expiry']
        urgency_tag = "🔴 [DUE TODAY]" if dte <= 0 else ("🟠 [1 DAY LEFT]" if dte == 1 else f"[{dte}d left]")
        label = f"{urgency_tag} {row['product_name']} | {row['store_name']} ({row['current_stock']} units)"
        options.append((idx, label))
        
    selected_idx = st.selectbox(
        "Choose a batch to inspect agent consensus:",
        options=options,
        format_func=lambda x: x[1]
    )[0]
    
    batch_row = inventory_df.loc[selected_idx].to_dict()
    
    # Interactive parameter adjustment for "What-If" live agent testing
    with st.expander("🛠️ Interactive Agent Sensitivity Parameters (Simulate Environmental Shocks)", expanded=False):
        param_col1, param_col2 = st.columns(2)
        with param_col1:
            temp_delta = st.slider("Simulate Ambient Temperature Delta (°C)", min_value=-5.0, max_value=8.0, value=0.0, step=0.5,
                                  help="Increases produce/salad velocity while accelerating biological decay")
        with param_col2:
            custom_stock = st.slider("Override Batch Inventory Level (Units)", min_value=1, max_value=100, value=int(batch_row["current_stock"]),
                                    help="Test how agents react to sudden overstock or low inventory")
            
    # Apply temporary adjustments
    test_batch = batch_row.copy()
    test_batch["current_stock"] = custom_stock
    test_batch["storage_temp_c"] = test_batch.get("storage_temp_c", 4.0) + temp_delta
    
    # Run Coordinator live on selected batch
    coord = CoordinatorAgent()
    with st.spinner("Executing multi-agent deliberation..."):
        reconciled = coord.reconcile_batch(
            batch_data=test_batch,
            all_inventory_df=inventory_df,
            temp_delta_c=temp_delta
        )
        
    # Reconciled Decision Banner
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%); border: 2px solid #8B5CF6; border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.08);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="agent-pill">🤖 COORDINATOR ARBITRATION CONSENSUS</span>
                <div style="font-family:'Space Grotesk', sans-serif; font-size:1.45rem; font-weight:700; color:#4C1D95; margin-top:6px;">
                    {reconciled['action_title']}
                </div>
                <div style="font-size:0.92rem; color:#5B21B6; margin-top:4px;">
                    Selected for <strong>{reconciled['product_name']}</strong> at <strong>{reconciled['store_name']}</strong> &nbsp;|&nbsp; Urgency: {get_urgency_badge_html(reconciled['urgency'])}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.82rem; color:#6B21A8; text-transform:uppercase; font-weight:600;">Net Financial Impact</div>
                <div style="font-size:1.6rem; font-family:'Space Grotesk'; font-weight:700; color:{'#15803D' if reconciled['margin_impact_usd'] >= 0 else '#B91C1C'};">
                    {'+' if reconciled['margin_impact_usd'] >= 0 else ''}${reconciled['margin_impact_usd']:,.2f}
                </div>
                <div style="font-size:0.8rem; color:#6D28D9;">Diverts {reconciled['waste_saved_units']} units ({reconciled['carbon_saved_kg']} kg CO2e)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Agent Consensus Voting Matrix
    st.markdown('<div class="section-header">🗳️ Agent Specialist Voting Matrix</div>', unsafe_allow_html=True)
    
    v_col1, v_col2, v_col3, v_col4, v_col5 = st.columns(5)
    
    with v_col1:
        st.markdown(f"""
        <div class="custom-card" style="border-top:3px solid #0284C7; height:100%;">
            <div style="font-size:0.75rem; color:#0369A1; font-weight:700;">DEMAND AGENT</div>
            <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin:6px 0;">{reconciled['agent_votes']['Demand']}</div>
            <div style="font-size:0.78rem; color:#64748B;">Poisson & elasticity projection</div>
        </div>
        """, unsafe_allow_html=True)
        
    with v_col2:
        st.markdown(f"""
        <div class="custom-card" style="border-top:3px solid #EA580C; height:100%;">
            <div style="font-size:0.75rem; color:#C2410C; font-weight:700;">SPOILAGE AGENT</div>
            <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin:6px 0;">{reconciled['agent_votes']['Spoilage']}</div>
            <div style="font-size:0.78rem; color:#64748B;">Arrhenius hazard curve</div>
        </div>
        """, unsafe_allow_html=True)
        
    with v_col3:
        st.markdown(f"""
        <div class="custom-card" style="border-top:3px solid #4338CA; height:100%;">
            <div style="font-size:0.75rem; color:#3730A3; font-weight:700;">RESTOCK AGENT</div>
            <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin:6px 0;">{reconciled['agent_votes']['Replenishment']}</div>
            <div style="font-size:0.78rem; color:#64748B;">Lead-time safety runway</div>
        </div>
        """, unsafe_allow_html=True)
        
    with v_col4:
        st.markdown(f"""
        <div class="custom-card" style="border-top:3px solid #F97316; height:100%;">
            <div style="font-size:0.75rem; color:#EA580C; font-weight:700;">MARKDOWN AGENT</div>
            <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin:6px 0;">{reconciled['agent_votes']['Markdown']}</div>
            <div style="font-size:0.78rem; color:#64748B;">Elasticity discount tier</div>
        </div>
        """, unsafe_allow_html=True)
        
    with v_col5:
        st.markdown(f"""
        <div class="custom-card" style="border-top:3px solid #7C3AED; height:100%;">
            <div style="font-size:0.75rem; color:#6D28D9; font-weight:700;">TRANSFER AGENT</div>
            <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin:6px 0;">{reconciled['agent_votes']['Transfer']}</div>
            <div style="font-size:0.78rem; color:#64748B;">Network transit arbitrage</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    
    # Detailed Mathematical Visualizations
    v_chart1, v_chart2 = st.columns([1.3, 1.1])
    
    with v_chart1:
        st.markdown('<div class="section-header">📈 Demand Trajectory & Uncertainty</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        # Generate 7-day forecast for visualization
        fc_df = coord.demand_agent.forecaster.generate_horizon_forecast(
            base_daily_sales=test_batch["avg_daily_sales"],
            start_date=pd.to_datetime(test_batch.get("received_date", "2026-10-09")).date(),
            horizon_days=7,
            category=test_batch.get("category", "Produce"),
            temp_delta_c=temp_delta
        )
        fig_fc = plot_forecast_trajectory(fc_df, test_batch["current_stock"], test_batch["product_name"])
        st.plotly_chart(fig_fc, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with v_chart2:
        st.markdown('<div class="section-header">🔬 Biological Shelf Decay Curve</div>', unsafe_allow_html=True)
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        nom_days = max(3, test_batch["days_to_expiry"] + 3)
        fig_decay = plot_biological_decay(nom_days)
        st.plotly_chart(fig_decay, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Explainable AI (XAI) Reasoning Trail
    st.markdown('<div class="section-header">🧠 Explainable AI (XAI) Chain-of-Thought Trail</div>', unsafe_allow_html=True)
    st.caption("Full chronological audit trace of how the autonomous agents deliberated, cross-checked constraints, and converged on the final action.")
    
    st.markdown('<div class="custom-card" style="max-height: 400px; overflow-y: auto;">', unsafe_allow_html=True)
    for thought in reconciled["reasoning_trace"]:
        render_agent_thought_step(
            step=thought["step"],
            agent_name=thought["agent_name"],
            thought=thought["thought"],
            timestamp=thought["timestamp"]
        )
    st.markdown('</div>', unsafe_allow_html=True)
