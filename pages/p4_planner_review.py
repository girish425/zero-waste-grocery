"""
Page 4: Human-in-the-Loop (HITL) AI Recommendation Review & Governance Workspace
Zero-Waste Grocery · GDGoC HITAM

Visual Design:
- Colorful recommendation cards with clear visual treatments for Urgent, Medium, and Low priorities
- Summary KPI cards for Pending Review, Approved, Rejected, and Modified recommendations
- Dynamic filters by Status, Priority, Responsible Agent, and Store Location
- Role selector for reviewer label (e.g. "Store Manager")

Interactions:
- Approve: One-click simulated authorization
- Reject: Rejection with optional reason capture
- Modify: Interactive field editor (discount %, reorder qty, transfer destination) before authorization
- Full audit recording: Review status, reviewer label, timestamp, and justification
- Session persistence: Retains decisions across navigation without duplication
- Expandable evidence inspector showing original recommendations, telemetry, and agent voting

Important Safety & Honesty:
- Prototype simulation disclaimer: no live inventory, POS, or pricing systems are modified
- Informative empty state when data is not loaded
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from copy import deepcopy
from typing import Dict, Any, List

from components.ui import render_hero, render_kpi_card, get_action_badge_html, get_urgency_badge_html

def render_planner_review_page():
    render_hero(
        title="Human-in-the-Loop (HITL) AI Recommendations Workspace",
        subtitle="Review, authorize, modify, or reject autonomous multi-agent recommendations. Every proposal is evidence-grounded and requires manager authorization before simulated execution.",
        badge_text="HUMAN-IN-THE-LOOP AI WORKSPACE"
    )

    # 1. Prototype Governance & Honesty Banner
    st.markdown("""
    <div style="background:#FFFBEB; border:1px solid #FCD34D; border-left:5px solid #F59E0B; border-radius:10px; padding:12px 18px; margin-bottom:18px; font-size:0.87rem; color:#78350F;">
        <strong>🛡️ PROTOTYPE GOVERNANCE NOTICE:</strong> Approvals and modifications recorded in this workspace represent manager authorizations within this prototype demonstration platform only. 
        This application does not connect to live supermarket point-of-sale registers, electronic shelf tags, supplier EDI, or enterprise inventory ERPs. No real-world stock, prices, or orders are altered.
    </div>
    """, unsafe_allow_html=True)

    # 2. Retrieve Proposals from Session State
    proposals = st.session_state.get("coordinator_proposals", [])

    # 3. Empty State Handling
    if not proposals:
        st.markdown("""
        <div class="custom-card" style="text-align:center; padding:45px 24px; border:2px dashed #CBD5E1; background:#FAFCFA;">
            <span style="font-size:3.5rem;">📂</span>
            <h3 style="color:#062E1E; font-family:'Space Grotesk'; margin:12px 0 6px 0;">No Active Recommendations Available</h3>
            <div style="color:#64748B; font-size:0.92rem; max-width:540px; margin:0 auto 20px auto; line-height:1.5;">
                The multi-agent system requires inventory data to generate recommendations. 
                Please upload your store inventory records or load the supermarket benchmark network to run the analysis.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_e1, col_e2, col_e3 = st.columns([1.5, 1.2, 1.5])
        with col_e2:
            if st.button("📤 Go to Upload Data", type="primary", use_container_width=True):
                st.session_state.current_page = "📤 Upload Data"
                st.rerun()
        return

    # 4. Normalize & Ensure Proposal Fields (Prevent Rerun Duplication & Inconsistencies)
    for idx, p in enumerate(proposals):
        # Stable unique identifier
        if "rec_id" not in p:
            p["rec_id"] = f"REC-{p.get('batch_id', 'BATCH')}-{p.get('sku', idx)}-{p.get('store_id', 'STORE')}-{idx}"
        
        # Canonical review status: PENDING, APPROVED, REJECTED, MODIFIED
        if "review_status" not in p:
            current_app = p.get("approval_status", "PENDING")
            if current_app in ["APPROVED", "MODIFIED", "REJECTED", "PENDING"]:
                p["review_status"] = current_app
            elif current_app == "OVERRIDDEN":
                p["review_status"] = "REJECTED"
            else:
                p["review_status"] = "PENDING"
        
        # Ensure approval_status is synced for downstream pages
        if p["review_status"] in ["APPROVED", "MODIFIED"]:
            p["approval_status"] = "APPROVED"
        elif p["review_status"] == "REJECTED":
            p["approval_status"] = "OVERRIDDEN"
        else:
            p["approval_status"] = "PENDING"

        # Canonical Priority
        if "priority" not in p:
            p["priority"] = p.get("urgency", "MEDIUM")

        # Canonical Generating Agent
        if "generating_agent" not in p:
            p["generating_agent"] = p.get("generating_specialist", "Chief Coordinator Agent")

        # Preserve snapshot of original recommendation before any manager modifications
        if "original_recommendation" not in p:
            p["original_recommendation"] = {
                "action": p.get("final_action", "MAINTAIN"),
                "action_title": p.get("action_title", ""),
                "action_details": deepcopy(p.get("action_details", {})),
                "margin_impact_usd": p.get("margin_impact_usd", 0.0),
                "waste_saved_units": p.get("waste_saved_units", 0.0)
            }

    # 5. Summary Counts for the 4 Review States
    pending_count = sum(1 for p in proposals if p["review_status"] == "PENDING")
    approved_count = sum(1 for p in proposals if p["review_status"] == "APPROVED")
    rejected_count = sum(1 for p in proposals if p["review_status"] == "REJECTED")
    modified_count = sum(1 for p in proposals if p["review_status"] == "MODIFIED")

    k_col1, k_col2, k_col3, k_col4 = st.columns(4)
    with k_col1:
        render_kpi_card(
            title="Pending Review",
            value=f"{pending_count}",
            subtitle="Awaiting manager review",
            trend_text="Action Required" if pending_count > 0 else "All Clear",
            trend_type="alert" if pending_count > 0 else "positive",
            icon="⏳"
        )
    with k_col2:
        render_kpi_card(
            title="Approved",
            value=f"{approved_count}",
            subtitle="Authorized for simulation",
            trend_text="Prototype Sign-off",
            trend_type="positive",
            icon="✅"
        )
    with k_col3:
        render_kpi_card(
            title="Rejected",
            value=f"{rejected_count}",
            subtitle="Overridden / Dismissed",
            trend_text="Manager Veto",
            trend_type="neutral",
            icon="❌"
        )
    with k_col4:
        render_kpi_card(
            title="Modified",
            value=f"{modified_count}",
            subtitle="Adjusted parameters",
            trend_text="Manager Custom",
            trend_type="positive",
            icon="✏️"
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 6. Filtering & Reviewer Persona Row
    st.markdown('<div class="custom-card" style="padding: 16px 20px; margin-bottom: 16px;">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.1, 1.1, 1.2, 1.2, 1.1])

    with f_col1:
        status_filter = st.selectbox(
            "Filter Status:",
            options=["All Statuses", "Pending Review", "Approved", "Rejected", "Modified"],
            index=0,
            key="f_status"
        )

    with f_col2:
        priority_filter = st.selectbox(
            "Filter Priority:",
            options=["All Priorities", "CRITICAL (Urgent ≤24h)", "HIGH (≤48h)", "MEDIUM", "LOW (Informational)"],
            index=0,
            key="f_priority"
        )

    with f_col3:
        all_agents = sorted(list(set(str(p.get("generating_agent", "Coordinator")) for p in proposals)))
        agent_filter = st.selectbox(
            "Filter Agent:",
            options=["All Agents"] + all_agents,
            index=0,
            key="f_agent"
        )

    with f_col4:
        all_stores = sorted(list(set(str(p.get("store_name", "All")) for p in proposals)))
        store_filter = st.selectbox(
            "Filter Store:",
            options=["All Stores"] + all_stores,
            index=0,
            key="f_store"
        )

    with f_col5:
        reviewer_label = st.selectbox(
            "Reviewer Role:",
            options=["Store Manager", "Inventory Planner", "Category Lead", "Sustainability Director"],
            index=0,
            key="f_reviewer",
            help="Label stamped on review decisions."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply Filter Predicates
    filtered_proposals = []
    for p in proposals:
        # Status match
        if status_filter == "Pending Review" and p["review_status"] != "PENDING":
            continue
        elif status_filter == "Approved" and p["review_status"] != "APPROVED":
            continue
        elif status_filter == "Rejected" and p["review_status"] != "REJECTED":
            continue
        elif status_filter == "Modified" and p["review_status"] != "MODIFIED":
            continue

        # Priority match
        p_prio = p.get("priority", "MEDIUM")
        if "CRITICAL" in priority_filter and p_prio != "CRITICAL":
            continue
        elif "HIGH" in priority_filter and p_prio != "HIGH":
            continue
        elif "MEDIUM" in priority_filter and p_prio != "MEDIUM":
            continue
        elif "LOW" in priority_filter and p_prio not in ["LOW", "UNKNOWN"]:
            continue

        # Agent match
        if agent_filter != "All Agents" and str(p.get("generating_agent")) != agent_filter:
            continue

        # Store match
        if store_filter != "All Stores" and str(p.get("store_name")) != store_filter:
            continue

        filtered_proposals.append(p)

    # 7. Batch Operations Bar
    b_col1, b_col2, b_col3 = st.columns([1.6, 1.2, 1.2])
    with b_col1:
        st.caption(f"Displaying **{len(filtered_proposals)}** of {len(proposals)} recommendations matching active filters.")

    with b_col2:
        if st.button("⚡ Batch Approve All Urgent (≤ 24h)", use_container_width=True, key="btn_batch_urgent"):
            c_urgent = 0
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for p in proposals:
                if p["priority"] == "CRITICAL" and p["review_status"] == "PENDING":
                    p["review_status"] = "APPROVED"
                    p["approval_status"] = "APPROVED"
                    p["reviewed_by"] = reviewer_label
                    p["reviewed_at"] = ts
                    p["review_reason"] = "Batch authorized: Critical shelf-life expiry"
                    c_urgent += 1
            if c_urgent > 0:
                st.success(f"Batch approved {c_urgent} critical recommendation(s) as {reviewer_label}!")
                st.rerun()
            else:
                st.info("No pending critical recommendations to batch approve.")

    with b_col3:
        if st.button("✅ Approve All Filtered Results", use_container_width=True, type="primary", key="btn_batch_all"):
            c_all = 0
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for p in filtered_proposals:
                if p["review_status"] == "PENDING":
                    p["review_status"] = "APPROVED"
                    p["approval_status"] = "APPROVED"
                    p["reviewed_by"] = reviewer_label
                    p["reviewed_at"] = ts
                    p["review_reason"] = f"Batch authorized filtered queue as {reviewer_label}"
                    c_all += 1
            if c_all > 0:
                st.success(f"Approved {c_all} filtered recommendation(s) as {reviewer_label}!")
                st.rerun()
            else:
                st.info("No pending recommendations in current filter view.")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 8. Render Colorful Recommendation Cards
    if not filtered_proposals:
        st.info("ℹ️ No recommendations match the current filter selection.")
        return

    for idx, p in enumerate(filtered_proposals):
        rec_id = p["rec_id"]
        priority = p.get("priority", "MEDIUM")
        status = p.get("review_status", "PENDING")
        dte = p.get("days_to_expiry")
        dte_str = f"{dte}d" if (dte is not None and not pd.isna(dte)) else "Unspecified"

        # Visual Treatment Colors by Priority
        if priority == "CRITICAL":
            border_left = "6px solid #EF4444"
            card_bg = "#FFFDFD"
            pill_color = "#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5;"
            prio_badge_html = '<span class="badge" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">🔴 CRITICAL (≤ 24h)</span>'
        elif priority == "HIGH":
            border_left = "6px solid #F97316"
            card_bg = "#FFFEFC"
            pill_color = "#FFEDD5; color:#C2410C; border:1px solid #FDBA74;"
            prio_badge_html = '<span class="badge" style="background:#FFEDD5; color:#C2410C; border:1px solid #FDBA74; font-weight:700;">🟠 HIGH (≤ 48h)</span>'
        elif priority == "MEDIUM":
            border_left = "6px solid #7C3AED"
            card_bg = "#FFFFFF"
            pill_color = "#F5F3FF; color:#6D28D9; border:1px solid #DDD6FE;"
            prio_badge_html = '<span class="badge" style="background:#F5F3FF; color:#6D28D9; border:1px solid #DDD6FE; font-weight:700;">🟣 MEDIUM</span>'
        else:
            border_left = "6px solid #10B981"
            card_bg = "#FFFFFF"
            pill_color = "#ECFDF5; color:#047857; border:1px solid #A7F3D0;"
            prio_badge_html = '<span class="badge" style="background:#ECFDF5; color:#047857; border:1px solid #A7F3D0; font-weight:700;">🟢 LOW (Informational)</span>'

        # Status Badge HTML
        if status == "APPROVED":
            status_badge_html = '<span class="badge" style="background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; font-weight:700;">✅ APPROVED (Prototype Only)</span>'
        elif status == "REJECTED":
            status_badge_html = '<span class="badge" style="background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; font-weight:700;">❌ REJECTED</span>'
        elif status == "MODIFIED":
            status_badge_html = '<span class="badge" style="background:#E0E7FF; color:#3730A3; border:1px solid #A5B4FC; font-weight:700;">✏️ MODIFIED & APPROVED</span>'
        else:
            status_badge_html = '<span class="badge" style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-weight:700;">⏳ PENDING REVIEW</span>'

        # Financial and Carbon impact
        impact_usd = p.get("margin_impact_usd", 0.0)
        impact_color = "#15803D" if impact_usd >= 0 else "#B91C1C"
        impact_sign = "+" if impact_usd >= 0 else ""
        waste_saved = p.get("waste_saved_units", 0.0)
        carbon_saved = p.get("carbon_saved_kg", 0.0)

        # Generating Agent
        agent_name = p.get("generating_agent", "Chief Coordinator Agent")

        # Explanation
        explanation_text = p.get("explanation") or p.get("action_title", "Evaluated by multi-agent consensus.")

        st.markdown(f"""
        <div class="custom-card" style="border-left:{border_left}; background:{card_bg}; padding:18px 22px; margin-bottom:14px; box-shadow:0 3px 10px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                <div>
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <span style="font-family:'Space Grotesk'; font-size:1.2rem; font-weight:700; color:#062E1E;">{p['product_name']}</span>
                        <span style="font-size:0.8rem; color:#64748B;">({p['sku']})</span>
                        {prio_badge_html}
                        {status_badge_html}
                    </div>
                    <div style="font-size:0.86rem; color:#475569; margin-top:4px; display:flex; gap:16px; flex-wrap:wrap;">
                        <span>📍 <strong>Store:</strong> {p['store_name']}</span>
                        <span>📦 <strong>Active Stock:</strong> {int(p['current_stock'])} units</span>
                        <span>⌛ <strong>Remaining Shelf-Life:</strong> {dte_str}</span>
                        <span>🤖 <strong>Responsible Agent:</strong> <span style="color:#4338CA; font-weight:600;">{agent_name}</span></span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div>{get_action_badge_html(p['final_action'])}</div>
                    <div style="font-size:1.1rem; font-family:'Space Grotesk'; font-weight:700; color:{impact_color}; margin-top:4px;">
                        {impact_sign}${impact_usd:,.2f} Margin Impact
                    </div>
                    <div style="font-size:0.78rem; color:#64748B;">
                        Diverts {waste_saved:.1f}u ({carbon_saved:.1f} kg CO2e)
                    </div>
                </div>
            </div>
            
            <div style="background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0; padding:12px 14px; margin:12px 0; font-size:0.88rem; line-height:1.45;">
                <div style="font-weight:700; color:#0D472C; font-size:0.95rem; margin-bottom:3px;">
                    {p['action_title']}
                </div>
                <div style="color:#334155;">
                    {explanation_text}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Show reviewer stamp if already reviewed
        if status in ["APPROVED", "REJECTED", "MODIFIED"]:
            rev_by = p.get("reviewed_by", "Store Manager")
            rev_at = p.get("reviewed_at", "Recorded in session")
            rev_note = p.get("review_reason", "")
            note_html = f" &nbsp;|&nbsp; <em>Note: \"{rev_note}\"</em>" if rev_note else ""
            st.markdown(f"""
            <div style="font-size:0.8rem; color:#475569; background:#F1F5F9; border-radius:6px; padding:6px 10px; margin-bottom:10px;">
                👤 <strong>Reviewed by:</strong> {rev_by} &nbsp;|&nbsp; 🕒 <strong>Timestamp:</strong> {rev_at}{note_html}
            </div>
            """, unsafe_allow_html=True)

        # Action Buttons Area
        col_act1, col_act2, col_act3, col_act4 = st.columns([1.2, 1.2, 1.4, 2.2])

        # Interaction 1: APPROVE
        with col_act1:
            if status == "PENDING":
                if st.button("✅ Approve", key=f"btn_app_{rec_id}", type="primary", use_container_width=True):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p["review_status"] = "APPROVED"
                    p["approval_status"] = "APPROVED"
                    p["reviewed_by"] = reviewer_label
                    p["reviewed_at"] = ts
                    p["review_reason"] = "Approved by store manager inside prototype"
                    # Log event
                    if "execution_logs" in st.session_state:
                        st.session_state.execution_logs.append({
                            "timestamp": ts,
                            "batch_id": p.get("batch_id", ""),
                            "action": p["final_action"],
                            "target": f"{p['product_name']} ({p['store_name']})",
                            "status": "APPROVED",
                            "message": f"Manager approved: {p['action_title']}"
                        })
                    st.rerun()

        # Interaction 2: REJECT
        with col_act2:
            if status == "PENDING":
                show_reject_form = st.session_state.get(f"show_reject_{rec_id}", False)
                if not show_reject_form:
                    if st.button("❌ Reject", key=f"btn_rej_toggle_{rec_id}", use_container_width=True):
                        st.session_state[f"show_reject_{rec_id}"] = True
                        st.rerun()
                else:
                    if st.button("Cancel Rejection", key=f"btn_rej_cancel_{rec_id}", use_container_width=True):
                        st.session_state[f"show_reject_{rec_id}"] = False
                        st.rerun()

        # Interaction 3: MODIFY
        with col_act3:
            if status == "PENDING":
                show_mod_form = st.session_state.get(f"show_mod_{rec_id}", False)
                if not show_mod_form:
                    if st.button("✏️ Modify Action", key=f"btn_mod_toggle_{rec_id}", use_container_width=True):
                        st.session_state[f"show_mod_{rec_id}"] = True
                        st.rerun()
                else:
                    if st.button("Cancel Modify", key=f"btn_mod_cancel_{rec_id}", use_container_width=True):
                        st.session_state[f"show_mod_{rec_id}"] = False
                        st.rerun()

        # Interaction 4: Reset to Pending if already decided
        with col_act4:
            if status in ["APPROVED", "REJECTED", "MODIFIED"]:
                if st.button("🔄 Reopen / Reset to Pending", key=f"btn_reset_{rec_id}", use_container_width=False):
                    p["review_status"] = "PENDING"
                    p["approval_status"] = "PENDING"
                    p.pop("reviewed_by", None)
                    p.pop("reviewed_at", None)
                    p.pop("review_reason", None)
                    st.rerun()

        # Render Rejection Input Drawer
        if st.session_state.get(f"show_reject_{rec_id}", False) and status == "PENDING":
            with st.container():
                st.markdown("<div style='background:#FFF5F5; border:1px solid #FEB2B2; border-radius:8px; padding:12px; margin-top:8px;'>", unsafe_allow_html=True)
                rej_reason = st.text_input(
                    "Optional Reason for Rejection:",
                    placeholder="e.g., Customer demand surge expected; hold inventory at full price.",
                    key=f"input_rej_{rec_id}"
                )
                if st.button("Confirm Rejection", key=f"btn_confirm_rej_{rec_id}", type="primary"):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p["review_status"] = "REJECTED"
                    p["approval_status"] = "OVERRIDDEN"
                    p["reviewed_by"] = reviewer_label
                    p["reviewed_at"] = ts
                    p["review_reason"] = rej_reason or "Overridden / Rejected by store manager"
                    st.session_state[f"show_reject_{rec_id}"] = False
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Render Modify Input Drawer
        if st.session_state.get(f"show_mod_{rec_id}", False) and status == "PENDING":
            with st.container():
                st.markdown("<div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:14px; margin-top:8px;'>", unsafe_allow_html=True)
                st.markdown(f"<strong>✏️ Customize Recommendation for {p['product_name']}:</strong>", unsafe_allow_html=True)

                act = p["final_action"]
                act_details = p.get("action_details", {})
                base_price = float(p.get("base_price", 3.99))
                unit_cost = float(p.get("unit_cost", 2.00))

                mod_action_type = st.selectbox(
                    "Proposed Action:",
                    options=["MARKDOWN", "REORDER", "TRANSFER", "DONATE", "MAINTAIN"],
                    index=["MARKDOWN", "REORDER", "TRANSFER", "DONATE", "MAINTAIN"].index(act) if act in ["MARKDOWN", "REORDER", "TRANSFER", "DONATE", "MAINTAIN"] else 0,
                    key=f"mod_act_type_{rec_id}"
                )

                new_title = p["action_title"]
                new_details = deepcopy(act_details)
                new_margin = p.get("margin_impact_usd", 0.0)

                if mod_action_type == "MARKDOWN":
                    current_disc = int(act_details.get("discount_pct", 30))
                    mod_disc = st.slider(
                        "Promotional Markdown Percentage (%):",
                        min_value=5, max_value=75, value=current_disc, step=5,
                        key=f"mod_disc_{rec_id}"
                    )
                    new_price = round(base_price * (1.0 - mod_disc / 100.0), 2)
                    st.caption(f"Adjusted Price: **${new_price:.2f}** (Regular: ${base_price:.2f})")
                    new_title = f"Apply {mod_disc}% Dynamic Markdown (${new_price:.2f})"
                    new_details["discount_pct"] = mod_disc
                    new_details["discounted_price"] = new_price
                    new_margin = round(p["current_stock"] * (new_price - unit_cost), 2)

                elif mod_action_type == "REORDER":
                    cur_qty = int(act_details.get("recommended_order_qty", 20))
                    mod_qty = st.number_input(
                        "Purchase Order Restock Quantity (Units):",
                        min_value=5, max_value=200, value=cur_qty, step=5,
                        key=f"mod_qty_{rec_id}"
                    )
                    new_title = f"Issue PO for {mod_qty} units (Manager Adjusted)"
                    new_details["recommended_order_qty"] = mod_qty
                    new_margin = -round(mod_qty * unit_cost, 2)

                elif mod_action_type == "TRANSFER":
                    cur_t_qty = int(act_details.get("transfer_qty", 10))
                    mod_t_qty = st.number_input(
                        "Inter-Store Transfer Quantity (Units):",
                        min_value=2, max_value=int(p["current_stock"]), value=min(int(p["current_stock"]), cur_t_qty), step=1,
                        key=f"mod_tqty_{rec_id}"
                    )
                    dest_opts = [s for s in all_stores if s != p["store_name"]] or ["Store Regional Hub"]
                    mod_dest = st.selectbox("Recipient Sister Store:", options=dest_opts, key=f"mod_dest_{rec_id}")
                    new_title = f"Transfer {mod_t_qty} units to {mod_dest} (Manager Adjusted)"
                    new_details["transfer_qty"] = mod_t_qty
                    new_details["destination_store_name"] = mod_dest

                elif mod_action_type == "DONATE":
                    new_title = f"Dispatch {int(p['current_stock'])} units to Food Bank Partner"
                    new_details = {"donation_partner": "Local Food Rescue Network", "units": p["current_stock"]}
                    new_margin = round(p["current_stock"] * unit_cost * 0.5, 2)

                else:
                    new_title = "Maintain Current Retail Strategy"
                    new_details = {"status": "Manager Set to Nominal"}
                    new_margin = 0.0

                mod_reason = st.text_input(
                    "Reason for Modification (Optional):",
                    placeholder="e.g., Increased discount due to rainy footfall forecast.",
                    key=f"input_mod_reason_{rec_id}"
                )

                if st.button("💾 Save & Authorize Modified Recommendation", key=f"btn_save_mod_{rec_id}", type="primary"):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p["final_action"] = mod_action_type
                    p["action_title"] = new_title
                    p["action_details"] = new_details
                    p["margin_impact_usd"] = new_margin
                    p["review_status"] = "MODIFIED"
                    p["approval_status"] = "APPROVED"
                    p["reviewed_by"] = reviewer_label
                    p["reviewed_at"] = ts
                    p["review_reason"] = mod_reason or "Modified and approved by store manager"
                    st.session_state[f"show_mod_{rec_id}"] = False
                    st.success(f"Recommendation modified and authorized for {p['product_name']}!")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # Inspection Drawer: View Original Recommendation & Supporting Evidence
        with st.expander(f"🔍 Inspect Evidence & Specialist Telemetry: {p['product_name']}", expanded=False):
            orig = p.get("original_recommendation", {})
            st.markdown(f"""
            <div style="font-size:0.85rem; color:#1E293B; margin-bottom:8px;">
                <strong>Original System Proposal:</strong> <span style="color:#047857; font-weight:700;">{orig.get('action_title', p['action_title'])}</span> &nbsp;|&nbsp; 
                <strong>Original Impact:</strong> ${orig.get('margin_impact_usd', p.get('margin_impact_usd', 0.0)):,.2f}
            </div>
            """, unsafe_allow_html=True)

            e_col1, e_col2 = st.columns(2)
            with e_col1:
                st.markdown("**📊 Supporting Quantitative Metrics:**")
                st.json({
                    "Current Stock": f"{p['current_stock']} units",
                    "Days to Expiry": dte_str,
                    "Sales Velocity": f"{p.get('avg_daily_sales', 'Unrecorded')} u/day",
                    "Estimated Surplus": f"{p.get('action_details', {}).get('surplus_units', p.get('waste_saved_units', 0.0))} units",
                    "Estimated Net Margin": f"${p.get('margin_impact_usd', 0.0):.2f}",
                    "Carbon Diverted": f"{p.get('carbon_saved_kg', 0.0)} kg CO2e"
                })

            with e_col2:
                st.markdown("**🗳️ Multi-Agent Voting Matrix:**")
                votes = p.get("agent_votes", {})
                st.json(votes or {"Status": "Arbitrated by Coordinator"})

            assumptions = p.get("missing_information_or_assumptions", [])
            if assumptions:
                st.markdown("**🛡️ Data Sufficiency & Assumptions:**")
                for a in assumptions:
                    st.write(f"• {a}")

        st.markdown('</div>', unsafe_allow_html=True)
