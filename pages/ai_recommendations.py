"""
Page: AI Recommendations & Multi-Agent Deliberation
Unified portal combining Human-in-the-Loop Planner Approvals, Multi-Agent Reasoning Trails,
and Simulated Downstream Execution.
"""
import streamlit as st
from pages.p4_planner_review import render_planner_review_page
from pages.p3_agent_hub import render_agent_hub_page
from pages.p5_simulated_execution import render_simulated_execution_page
from pages.p7_scenario_simulator import render_scenario_simulator_page

def render_ai_recommendations_page():
    tab_review, tab_agents, tab_exec, tab_stress = st.tabs([
        "📋 Planner Approval Queue (HITL)",
        "🤖 Multi-Agent Reasoning & Consensus",
        "🔄 Downstream Execution (POS/WMS/ERP)",
        "⚡ What-If Disruption Simulator"
    ])
    
    with tab_review:
        render_planner_review_page()
        
    with tab_agents:
        render_agent_hub_page()
        
    with tab_exec:
        render_simulated_execution_page()
        
    with tab_stress:
        render_scenario_simulator_page()
