"""
Page 7: Scenario Simulator & Stress-Testing Studio
Interactive what-if disruption generator to stress-test agent adaptability during climate and supply chain shocks.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from components.ui import render_hero
from agents.coordinator import CoordinatorAgent

def render_scenario_simulator_page():
    render_hero(
        title="Disruption Simulator & Stress-Testing Studio",
        subtitle="Simulate acute climate spikes, cold-chain refrigeration malfunctions, and regional supply chain bottlenecks to observe agent self-healing adaptation.",
        badge_text="WHAT-IF STRESS TESTING ENGINE"
    )
    
    st.markdown('<div class="section-header">⚡ Select a Preconfigured Hackathon Disruption Scenario</div>', unsafe_allow_html=True)
    
    scenarios = {
        "heatwave": {
            "title": "☀️ Scenario A: Regional Summer Heatwave (+5°C)",
            "desc": "Ambient heatwave accelerates fruit & dairy degradation while increasing salad & beverage velocity by +35%.",
            "temp_delta": 4.5,
            "footfall_mult": 1.15,
            "lead_time_mult": 1.0
        },
        "supplier_delay": {
            "title": "🚢 Scenario B: Critical Supplier Shutdown & Transit Delay (+48h)",
            "desc": "Wholesale distribution hub delayed by 2 days. Replenishment Agent must guard safety runway while Transfer Agent balances sister stores.",
            "temp_delta": 0.0,
            "footfall_mult": 1.0,
            "lead_time_mult": 2.5
        },
        "festival_surge": {
            "title": "🎉 Scenario C: Downtown Urban Festival Footfall Spike (+60%)",
            "desc": "Massive weekend footfall surge at Metro Flagship store causing rapid stockout hazards unless stock is transferred from suburban stores.",
            "temp_delta": 1.0,
            "footfall_mult": 1.60,
            "lead_time_mult": 1.0
        },
        "chiller_fail": {
            "title": "🚨 Scenario D: Cold-Chain Sensor & Chiller Breach (+6°C at Store 03)",
            "desc": "Transit store refrigerator temperature rises to 9.5°C. Spoilage Agent must immediately intervene before biological spoilage occurs.",
            "temp_delta": 5.5,
            "footfall_mult": 0.95,
            "lead_time_mult": 1.0
        }
    }
    
    selected_scen_key = st.radio(
        "Choose Stress Scenario:",
        list(scenarios.keys()),
        format_func=lambda k: scenarios[k]["title"]
    )
    
    curr_scen = scenarios[selected_scen_key]
    st.info(f"📋 **Scenario Description:** {curr_scen['desc']}")
    
    # Custom Parameter Sliders
    with st.expander("🎛️ Fine-Tune Environmental Parameters", expanded=True):
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            temp_delta = st.slider("Temperature Shock (°C)", min_value=-5.0, max_value=8.0, value=curr_scen["temp_delta"], step=0.5)
        with p_col2:
            footfall_mult = st.slider("Store Traffic Multiplier", min_value=0.5, max_value=2.0, value=curr_scen["footfall_mult"], step=0.05)
        with p_col3:
            lead_time_mult = st.slider("Supplier Lead Time Multiplier", min_value=1.0, max_value=3.0, value=curr_scen["lead_time_mult"], step=0.5)
            
    # Execute Test Button
    if st.button("🚀 Run Multi-Agent Network Simulation Under Disruption", type="primary", use_container_width=True):
        with st.spinner("Simulating multi-agent network reaction under simulated shock..."):
            # Clone inventory and apply shocks
            sim_df = st.session_state.inventory_df.copy()
            sim_df["avg_daily_sales"] = (sim_df["avg_daily_sales"] * footfall_mult).round(1)
            sim_df["storage_temp_c"] = (sim_df["storage_temp_c"] + temp_delta).round(1)
            sim_df["lead_time_days"] = (sim_df["lead_time_days"] * lead_time_mult).astype(int)
            
            # Re-run Coordinator on network
            coord = CoordinatorAgent()
            new_proposals = []
            for _, row in sim_df.iterrows():
                b_dict = row.to_dict()
                p = coord.reconcile_batch(b_dict, sim_df, temp_delta_c=temp_delta)
                new_proposals.append(p)
                
            # Store in session state
            st.session_state.simulated_proposals = new_proposals
            st.session_state.last_scenario_run = curr_scen["title"]
            
        st.success(f"Simulation completed across {len(new_proposals)} batches!")
        
    # Render Simulation Results if run
    if "simulated_proposals" in st.session_state:
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="section-header">📈 Simulation Impact Results: {st.session_state.get("last_scenario_run", "Active Scenario")}</div>', unsafe_allow_html=True)
        
        sim_proposals = st.session_state.simulated_proposals
        
        # Summary metrics
        sim_critical = sum(1 for p in sim_proposals if p["urgency"] == "CRITICAL")
        sim_markdowns = sum(1 for p in sim_proposals if p["final_action"] == "MARKDOWN")
        sim_transfers = sum(1 for p in sim_proposals if p["final_action"] == "TRANSFER")
        sim_reorders = sum(1 for p in sim_proposals if p["final_action"] == "REORDER")
        sim_donations = sum(1 for p in sim_proposals if p["final_action"] == "DONATE")
        
        r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
        r_col1.metric("Critical Alerts", sim_critical, delta=f"{sim_critical} urgent batches", delta_color="inverse")
        r_col2.metric("Dynamic Markdowns", sim_markdowns, delta="Price tags altered")
        r_col3.metric("Network Transfers", sim_transfers, delta="Cross-store dispatch")
        r_col4.metric("Restock Orders", sim_reorders, delta="Supply reorders")
        r_col5.metric("Food Bank Rescue", sim_donations, delta="Zero food waste")
        
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        # Action table
        st.markdown("**Simulated Autonomous Agent Action Adjustments:**")
        sim_records = []
        for p in sim_proposals[:12]:
            sim_records.append({
                "Store": p["store_name"],
                "Product": p["product_name"],
                "Urgency": p["urgency"],
                "Reconciled Action": p["final_action"],
                "Proposed Execution": p["action_title"],
                "Financial Delta": f"{'+' if p['margin_impact_usd'] >= 0 else ''}${p['margin_impact_usd']:,.2f}",
                "Waste Prevented": f"{p['waste_saved_units']} units"
            })
            
        st.dataframe(pd.DataFrame(sim_records), use_container_width=True, hide_index=True)
        
        # Option to apply simulation results back to planner queue
        if st.button("📥 Apply Simulated Actions to Planner Approval Queue", type="secondary"):
            st.session_state.coordinator_proposals = sim_proposals
            st.session_state.execution_logs.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "batch_id": "SCENARIO-APPLY",
                "action": "SCENARIO_INJECT",
                "target": st.session_state.get("last_scenario_run", "Scenario"),
                "status": "APPLIED",
                "message": f"Applied simulation actions to active planner queue."
            })
            st.success("Active planner queue updated with simulated proposals!")
            st.rerun()
