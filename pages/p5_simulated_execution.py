"""
Page 5: Simulated ERP, WMS, POS Execution Engine & Live Logs
Downstream execution simulation showing how approved agent decisions dispatch to retail endpoints.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from components.ui import render_hero

def render_simulated_execution_page():
    render_hero(
        title="Simulated ERP, WMS & POS Execution Engine",
        subtitle="Downstream operational execution for approved actions: Electronic Shelf Labels (POS), Transfer Manifests (WMS), and Restock Orders (ERP).",
        badge_text="DOWNSTREAM ENTERPRISE CONNECTORS"
    )
    
    proposals = st.session_state.get("coordinator_proposals", [])
    approved_proposals = [p for p in proposals if p.get("approval_status") == "APPROVED"]
    logs = st.session_state.get("execution_logs", [])

    
    # 3 System Status Tabs
    tab_pos, tab_wms, tab_erp, tab_logs = st.tabs([
        "🏷️ POS / Electronic Shelf Labels",
        "🚚 WMS Transfer Manifests",
        "📦 ERP Purchase Orders",
        "📜 Live System Audit Stream"
    ])
    
    # ---------------- TAB 1: POS / ESL ----------------
    with tab_pos:
        st.markdown('<div class="section-header">🏷️ Electronic Shelf Label (ESL) Dynamic Price Broadcast</div>', unsafe_allow_html=True)
        st.caption("IoT digital price tags instantly synchronize dynamic markdown discounts at the store shelves.")
        
        pos_items = [p for p in approved_proposals if p["final_action"] == "MARKDOWN"]
        if pos_items:
            pos_records = []
            for p in pos_items:
                details = p.get("action_details", {})
                pos_records.append({
                    "Store Location": p["store_name"],
                    "Product": p["product_name"],
                    "ESL Tag ID": f"ESL-{p['sku'][:7]}-09",
                    "Original Price": f"${p.get('action_details', {}).get('original_price', 4.99):.2f}",
                    "Dynamic Price": f"${p.get('action_details', {}).get('discounted_price', 2.99):.2f}",
                    "Markdown Tier": f"{p.get('action_details', {}).get('discount_pct', 30)}% OFF",
                    "Broadcast Status": "🟢 LIVE ON SHELF",
                    "Sync Time": p.get("approved_at", "Just now")
                })
            st.dataframe(pd.DataFrame(pos_records), use_container_width=True, hide_index=True)
        else:
            st.info("No approved dynamic markdowns yet. Approve markdowns in the Planner Queue to push prices to POS shelf tags.")
            
    # ---------------- TAB 2: WMS TRANSFERS ----------------
    with tab_wms:
        st.markdown('<div class="section-header">🚚 WMS Inter-Store Transfer Logistics Manifests</div>', unsafe_allow_html=True)
        st.caption("Warehouse Management System dispatch orders for cross-balancing inventory before expiry.")
        
        transfer_items = [p for p in approved_proposals if p["final_action"] == "TRANSFER"]
        if transfer_items:
            wms_records = []
            for p in transfer_items:
                det = p.get("action_details", {})
                wms_records.append({
                    "Transfer Manifest #": f"TRF-2026-{p['sku'][:6]}",
                    "Source Store": p["store_name"],
                    "Destination Store": det.get("destination_store_name", "Metro Flagship"),
                    "Product": p["product_name"],
                    "Transfer Units": det.get("transfer_qty", 10),
                    "Transit Cost": f"${det.get('transit_cost_usd', 4.50):.2f}",
                    "Logistics Status": "🟡 Dispatched / Van En Route",
                    "Dispatch Time": p.get("approved_at", "Just now")
                })
            st.dataframe(pd.DataFrame(wms_records), use_container_width=True, hide_index=True)
        else:
            st.info("No inter-store transfers approved yet. Approve transfer proposals in the Planner Queue.")
            
    # ---------------- TAB 3: ERP REORDERS ----------------
    with tab_erp:
        st.markdown('<div class="section-header">📦 ERP Automated Restock Purchase Orders</div>', unsafe_allow_html=True)
        st.caption("Enterprise Procurement integration generating supplier EDI purchase orders for depleted stock.")
        
        reorder_items = [p for p in approved_proposals if p["final_action"] == "REORDER"]
        if reorder_items:
            erp_records = []
            for p in reorder_items:
                det = p.get("action_details", {})
                erp_records.append({
                    "PO Number": f"PO-8829-{p['sku'][:6]}",
                    "Store": p["store_name"],
                    "Product": p["product_name"],
                    "Quantity Ordered": f"{det.get('recommended_order_qty', 20)} units",
                    "Lead Time": "24-48 Hours",
                    "EDI Status": "🟢 Confirmed with Supplier",
                    "Generated": p.get("approved_at", "Just now")
                })
            st.dataframe(pd.DataFrame(erp_records), use_container_width=True, hide_index=True)
        else:
            st.info("No replenishment purchase orders approved yet.")
            
    # ---------------- TAB 4: LIVE LOGS ----------------
    with tab_logs:
        st.markdown('<div class="section-header">📜 Real-Time Audit Event Stream</div>', unsafe_allow_html=True)
        st.caption("Immutable system audit trail logging all agent arbitration events and planner authorization timestamps.")
        
        if logs:
            log_df = pd.DataFrame(logs)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            
            # Download JSON logs
            json_str = json.dumps(logs, indent=2)
            st.download_button(
                label="📥 Export System Audit Logs (JSON)",
                data=json_str,
                file_name=f"ZeroWaste_AuditLogs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.info("Audit log is currently empty. Actions taken in the Planner Review queue will populate live event streams.")
