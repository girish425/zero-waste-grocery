"""
Page: Upload Data - Bring Your Grocery Data to Life
Empowers grocery operators to ingest unified or modular datasets (CSV/Excel),
supports case-insensitive alias mapping, manual mapping overrides, plain-language validation,
detects duplicates/negative values, and never assumes missing expiry/sales data.
"""
import streamlit as st
import pandas as pd
from datetime import date
from components.ui import render_hero
from data.excel_manager import (
    safely_read_file,
    generate_sample_inventory_csv,
    generate_sample_sales_csv,
    generate_sample_batches_csv,
    generate_sample_unified_csv,
    validate_and_harmonize_data
)
from data.normalizer import (
    CANONICAL_FIELDS,
    suggest_column_mappings,
    normalize_and_validate_inventory
)
from data.generator import generate_live_inventory, generate_pos_sales_history
from agents.coordinator import CoordinatorAgent

def render_upload_data_page():
    # 1. Welcoming Hero Section
    st.markdown("""
    <div class="landing-hero" style="margin-bottom: 1.5rem; padding: 2.2rem 2.5rem;">
        <div class="hero-tag">📂 ROBUST DATA NORMALIZATION & VALIDATION</div>
        <div class="landing-title" style="font-size: 2.3rem;">
            Bring Your Grocery Data <span class="landing-highlight">to Life.</span>
        </div>
        <div class="landing-subtitle" style="font-size: 1.05rem; margin-bottom: 0;">
            Upload your store inventory, historical POS transactions, and batch-level cold-chain readings. 
            The normalization engine maps diverse store column names (e.g., <em>item_name</em>, <em>available_quantity</em>, <em>use_by</em>), 
            validates types, flags anomalies in plain language, and triggers autonomous AI agents to prevent food waste.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Upload Mode Tabs
    tab_unified, tab_modular, tab_instant = st.tabs([
        "📄 File Ingestion & Auto-Mapping (Recommended)",
        "🗂️ Multi-File Modular Ingestion",
        "⚡ One-Click Supermarket Demo"
    ])

    # ---------------- TAB 1: FILE INGESTION & AUTO-MAPPING ----------------
    with tab_unified:
        st.markdown("""
        <div style="margin: 0.5rem 0 1rem 0;">
            <h4 style="color:#062E1E; font-family:'Space Grotesk'; margin-bottom:4px;">
                Upload Grocery Inventory Spreadsheet
            </h4>
            <div style="font-size:0.88rem; color:#64748B;">
                Upload a CSV or Excel file (.csv, .xlsx). Columns will be automatically matched to the canonical schema with manual override support.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_u1, col_u2 = st.columns([1.6, 1.0])

        with col_u1:
            st.markdown('<div class="custom-card" style="border: 2px dashed #10B981; background: #FAFCFA;">', unsafe_allow_html=True)
            unified_file = st.file_uploader(
                "Drop your grocery inventory file (.csv or .xlsx):",
                type=["csv", "xlsx"],
                key="uploader_unified",
                help="Supports exports from any POS or WMS system. Automatic alias matching detects common names."
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with col_u2:
            st.markdown("""
            <div class="custom-card" style="height: 100%;">
                <div style="font-weight:700; color:#062E1E; font-size:0.95rem; margin-bottom:6px;">
                    📥 Sample Download
                </div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:12px;">
                    Need a reference format? Download our pre-built sample template with aliases:
                </div>
            """, unsafe_allow_html=True)
            sample_u_csv = generate_sample_unified_csv()
            st.download_button(
                label="📥 Download Sample Unified CSV",
                data=sample_u_csv,
                file_name="sample_unified_grocery_inventory.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_sample_unified_csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # Handle Unified File Inspection
        if unified_file is not None:
            df_raw, read_err = safely_read_file(unified_file)
            if read_err:
                st.error(f"❌ Read Error: {read_err}")
            else:
                # Store original raw uploaded dataset for reference
                st.session_state.raw_uploaded_df = df_raw.copy()

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:10px 16px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; color:#166534;">✓ File Loaded:</span> 
                        <code style="color:#0F172A; background:#FFFFFF; padding:2px 6px; border-radius:4px;">{unified_file.name}</code>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <span class="badge" style="background:#DCFCE7; color:#15803D;">{len(df_raw)} Data Rows</span>
                        <span class="badge" style="background:#EDE9FE; color:#6D28D9;">{len(df_raw.columns)} Columns Detected</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Auto-suggest column mappings
                # Auto-suggest column mappings with ambiguity detection
                suggested_map, unmapped_cols, metadata = suggest_column_mappings(list(df_raw.columns))
                ambiguities = metadata.get("ambiguities", {})
                is_ambiguous = metadata.get("is_ambiguous", False)

                if is_ambiguous:
                    st.warning(
                        "⚠️ **Ambiguous Column Matching Detected**: Multiple source columns matched one or more canonical fields. "
                        "Please verify or adjust the auto-selected mappings below before running validation."
                    )

                # Interactive Column Mapping Interface
                with st.expander("📋 Review & Customize Column Mapping (Auto-Detected Aliases)", expanded=True):
                    st.caption("Our normalization engine mapped your headers to standard internal attributes. Adjust any dropdown if your store uses different naming:")
                    
                    available_headers = ["-- None / Not Provided --"] + list(df_raw.columns)
                    user_mapping = {}

                    # 1. REQUIRED ATTRIBUTES
                    st.markdown("""
                    <div style="font-weight:700; color:#991B1B; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.04em; margin: 6px 0 8px 0; display:flex; align-items:center; gap:6px;">
                        <span>🔴 Mandatory Attributes</span>
                        <span style="font-size:0.75rem; background:#FEE2E2; color:#991B1B; padding:2px 8px; border-radius:10px;">Required for Ingestion</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    req_fields = {k: v for k, v in CANONICAL_FIELDS.items() if v["required"]}
                    req_cols = st.columns(len(req_fields))
                    for idx, (canonical_key, meta) in enumerate(req_fields.items()):
                        with req_cols[idx]:
                            default_choice = suggested_map.get(canonical_key, "-- None / Not Provided --")
                            sel_index = available_headers.index(default_choice) if default_choice in available_headers else 0
                            amb_tag = " ⚠️ (Multiple Matches)" if canonical_key in ambiguities else ""
                            chosen = st.selectbox(
                                f"{meta['label']} *(Required)*{amb_tag}",
                                options=available_headers,
                                index=sel_index,
                                key=f"map_sel_req_{canonical_key}",
                                help=meta.get("description", "")
                            )
                            if chosen != "-- None / Not Provided --":
                                user_mapping[canonical_key] = chosen

                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                    # 2. OPTIONAL ATTRIBUTES
                    st.markdown("""
                    <div style="font-weight:700; color:#166534; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.04em; margin: 8px 0 8px 0; display:flex; align-items:center; gap:6px;">
                        <span>🟢 Optional Attributes</span>
                        <span style="font-size:0.75rem; background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:10px;">Enriches Multi-Agent Precision</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    opt_fields = {k: v for k, v in CANONICAL_FIELDS.items() if not v["required"]}
                    opt_cols = st.columns(3)
                    for idx, (canonical_key, meta) in enumerate(opt_fields.items()):
                        col_idx = idx % 3
                        with opt_cols[col_idx]:
                            default_choice = suggested_map.get(canonical_key, "-- None / Not Provided --")
                            sel_index = available_headers.index(default_choice) if default_choice in available_headers else 0
                            amb_tag = " ⚠️ (Multiple Matches)" if canonical_key in ambiguities else ""
                            chosen = st.selectbox(
                                f"{meta['label']} *(Optional)*{amb_tag}",
                                options=available_headers,
                                index=sel_index,
                                key=f"map_sel_opt_{canonical_key}",
                                help=meta.get("description", "")
                            )
                            if chosen != "-- None / Not Provided --":
                                user_mapping[canonical_key] = chosen

                    if unmapped_cols:
                        st.caption(f"Unmapped source columns: {', '.join(unmapped_cols)}")

                with st.expander("🔍 Original Uploaded Raw Data Preview (Preserved for Reference)", expanded=False):
                    st.caption("The original uploaded data is preserved unmutated for compliance and audit traceability.")
                    st.dataframe(df_raw.head(10), use_container_width=True)

                # Validation & Action Button
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Validate and Analyze Data", type="primary", use_container_width=True, key="btn_validate_unified"):
                    with st.spinner("Executing schema normalization, constraint verification & Multi-Agent deliberation..."):
                        val_results = normalize_and_validate_inventory(
                            raw_df=df_raw,
                            column_mapping=user_mapping
                        )
                        
                        accepted = val_results["accepted_count"]
                        rejected = val_results["rejected_count"]
                        valid_df = val_results["valid_df"]
                        warnings = val_results["warnings"]
                        rejected_details = val_results["rejected_details"]
                        
                        if accepted == 0:
                            st.error(f"❌ Ingestion Failed: All {rejected} rows failed validation checks.")
                            for r in rejected_details[:5]:
                                st.error(f"Row {r['row_index']}: {'; '.join(r['reasons'])}")
                        else:
                            # Run Multi-Agent Coordinator on clean valid rows
                            coord = CoordinatorAgent()
                            proposals = []
                            for _, row in valid_df.iterrows():
                                p = coord.reconcile_batch(row.to_dict(), valid_df)
                                proposals.append(p)

                            # Persist in session state for use across all pages
                            st.session_state.inventory_df = valid_df
                            st.session_state.raw_uploaded_df = df_raw.copy()
                            st.session_state.coordinator_proposals = proposals
                            st.session_state.validation_summary = val_results
                            st.session_state.data_refreshed = True

                            # Display Validation Summary Cards
                            st.markdown("### 📊 Ingestion & Validation Summary")
                            s_col1, s_col2, s_col3, s_col4 = st.columns(4)
                            s_col1.metric("Accepted Records", f"{accepted} rows", delta="Valid & Normalized", delta_color="normal")
                            s_col2.metric("Rejected Records", f"{rejected} rows", delta="Excluded from analysis" if rejected > 0 else "0 errors", delta_color="inverse")
                            s_col3.metric("Validation Warnings", f"{len(warnings)} notes", delta=f"{val_results['missing_expiry_count']} missing expiries" if val_results['has_missing_expiry'] else "Clean")
                            s_col4.metric("Stores Identified", f"{valid_df['store_name'].nunique()} Supermarkets")

                            # Transparency Callouts
                            if val_results["has_missing_expiry"]:
                                st.warning(f"⚠️ **Note on Expiry Integrity**: {val_results['missing_expiry_count']} product(s) have no expiry date specified. "
                                           "Their shelf-life status is marked as **Unspecified** and was **NOT** assumed or fabricated.")
                                
                            if val_results.get("has_unrecorded_sales", False):
                                st.info(f"ℹ️ **Note on Sales Velocity**: {val_results['unrecorded_sales_count']} product(s) have unrecorded sales velocity. "
                                        "Consumption rate was **NOT** assumed or fabricated.")
                                
                            if val_results["duplicate_count"] > 0:
                                st.info(f"ℹ️ **Duplicates Detected**: {val_results['duplicate_count']} duplicate records were identified and processed as separate batch lots.")

                            if rejected > 0:
                                with st.expander(f"⚠️ View Plain-Language Reasons for {rejected} Rejected Row(s)", expanded=True):
                                    for r in rejected_details:
                                        st.markdown(f"- **Row {r['row_index']}**: {'; '.join(r['reasons'])}")

                            if warnings:
                                with st.expander("ℹ️ Data Normalization Notes", expanded=False):
                                    for w in warnings:
                                        st.caption(f"• {w}")

                            st.success(f"🎉 Successfully normalized {accepted} inventory items and generated AI recommendations!")
                            st.toast(f"🎉 Normalized {accepted} items & generated {len(proposals)} AI proposals!", icon="🚀")

                            nav_col1, nav_col2 = st.columns(2)
                            with nav_col1:
                                if st.button("📊 View Results on Dashboard", key="to_dash_norm"):
                                    st.toast("📊 Opening Dashboard...", icon="📊")
                                    st.session_state.current_page = "📊 Dashboard"
                                    st.rerun()
                            with nav_col2:
                                if st.button("📦 Inspect in Inventory & Expiry Monitor", key="to_inv_norm"):
                                    st.toast("📦 Opening Inventory & Expiry Monitor...", icon="📦")
                                    st.session_state.current_page = "📦 Inventory & Expiry"
                                    st.rerun()

    # ---------------- TAB 2: MULTI-FILE MODULAR INGESTION ----------------
    with tab_modular:
        st.markdown("""
        <div style="margin: 0.5rem 0 1rem 0;">
            <h4 style="color:#062E1E; font-family:'Space Grotesk'; margin-bottom:4px;">
                Multi-Source Departmental Ingestion
            </h4>
            <div style="font-size:0.88rem; color:#64748B;">
                Upload separate files for your Master Catalog, POS Sales Transactions, and Batch Expiry Telemetry. The engine links them seamlessly on SKU.
            </div>
        </div>
        """, unsafe_allow_html=True)

        m_col1, m_col2, m_col3 = st.columns(3)

        # File 1: Inventory Master
        with m_col1:
            st.markdown("""
            <div class="custom-card" style="border-top: 4px solid #10B981; min-height: 280px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:700; color:#062E1E; font-size:0.95rem;">📦 Inventory Master</span>
                        <span>🏷️</span>
                    </div>
                    <div style="font-size:0.8rem; color:#64748B; margin-bottom:10px;">
                        SKU, Product Name, Category, Unit Cost, Base Price.
                    </div>
            """, unsafe_allow_html=True)
            f_inv = st.file_uploader("Upload Inventory CSV/XLSX", type=["csv", "xlsx"], key="up_inv_master")
            s_inv_csv = generate_sample_inventory_csv()
            st.download_button("📥 Sample Inventory CSV", s_inv_csv, "sample_inventory_master.csv", "text/csv", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        # File 2: POS Sales History
        with m_col2:
            st.markdown("""
            <div class="custom-card" style="border-top: 4px solid #0284C7; min-height: 280px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:700; color:#062E1E; font-size:0.95rem;">📈 POS Sales History</span>
                        <span>💳</span>
                    </div>
                    <div style="font-size:0.8rem; color:#64748B; margin-bottom:10px;">
                        Date, Store Name, SKU, Quantity Sold, Revenue.
                    </div>
            """, unsafe_allow_html=True)
            f_sales = st.file_uploader("Upload POS Sales CSV/XLSX", type=["csv", "xlsx"], key="up_sales_history")
            s_sales_csv = generate_sample_sales_csv()
            st.download_button("📥 Sample Sales CSV", s_sales_csv, "sample_pos_sales.csv", "text/csv", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        # File 3: Batch Expiry Telemetry
        with m_col3:
            st.markdown("""
            <div class="custom-card" style="border-top: 4px solid #EA580C; min-height: 280px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:700; color:#062E1E; font-size:0.95rem;">⏱️ Expiry & Batches</span>
                        <span>❄️</span>
                    </div>
                    <div style="font-size:0.8rem; color:#64748B; margin-bottom:10px;">
                        Batch Code, SKU, Current Stock, Expiry Date, Temp °C.
                    </div>
            """, unsafe_allow_html=True)
            f_batches = st.file_uploader("Upload Expiry Batches CSV/XLSX", type=["csv", "xlsx"], key="up_batches_exp")
            s_batches_csv = generate_sample_batches_csv()
            st.download_button("📥 Sample Batches CSV", s_batches_csv, "sample_batch_expiry.csv", "text/csv", use_container_width=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

        # Process Multi-File Upload
        df_inv_loaded = None
        df_sales_loaded = None
        df_batches_loaded = None

        if f_inv:
            df_inv_loaded, e1 = safely_read_file(f_inv)
            if e1: st.error(f"Inventory Master Error: {e1}")
        if f_sales:
            df_sales_loaded, e2 = safely_read_file(f_sales)
            if e2: st.error(f"Sales History Error: {e2}")
        if f_batches:
            df_batches_loaded, e3 = safely_read_file(f_batches)
            if e3: st.error(f"Expiry Batches Error: {e3}")

        # Summary of files detected
        files_present = sum(1 for x in [df_inv_loaded, df_sales_loaded, df_batches_loaded] if x is not None)
        if files_present > 0:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.info(f"📁 **{files_present} file(s) attached**: " +
                    (f"Inventory ({len(df_inv_loaded)} rows) " if df_inv_loaded is not None else "") +
                    (f"| Sales ({len(df_sales_loaded)} rows) " if df_sales_loaded is not None else "") +
                    (f"| Batches ({len(df_batches_loaded)} rows)" if df_batches_loaded is not None else ""))

            # Action Button
            if st.button("🚀 Merge, Validate and Analyze Multi-File Data", type="primary", use_container_width=True, key="btn_validate_multi"):
                with st.spinner("Harmonizing multi-file datasets on SKU & executing Agent Coordinator..."):
                    harmonized, notes, is_valid, errs = validate_and_harmonize_data(
                        inv_df=df_inv_loaded,
                        sales_df=df_sales_loaded,
                        batches_df=df_batches_loaded
                    )
                    if not is_valid:
                        for e in errs:
                            st.error(f"⚠️ Validation Issue: {e}")
                    else:
                        coord = CoordinatorAgent()
                        proposals = []
                        for _, row in harmonized.iterrows():
                            p = coord.reconcile_batch(row.to_dict(), harmonized)
                            proposals.append(p)

                        st.session_state.inventory_df = harmonized
                        if df_inv_loaded is not None:
                            st.session_state.raw_uploaded_df = df_inv_loaded.copy()
                        if df_sales_loaded is not None:
                            st.session_state.sales_df = df_sales_loaded
                        st.session_state.coordinator_proposals = proposals
                        st.session_state.data_refreshed = True

                        st.success(f"🎉 Successfully merged and deliberated on {len(harmonized)} active perishable batches!")
                        st.toast(f"🎉 Merged records & deliberated on {len(harmonized)} batches!", icon="🚀")
                        with st.expander("ℹ️ Harmonization Audit Trail", expanded=True):
                            for n in notes:
                                st.write(f"• {n}")
                            st.dataframe(harmonized.head(5), use_container_width=True)

                        nav_col1, nav_col2 = st.columns(2)
                        with nav_col1:
                            if st.button("📊 View Dashboard Overview", key="to_dash_m"):
                                st.toast("📊 Opening Dashboard...", icon="📊")
                                st.session_state.current_page = "📊 Dashboard"
                                st.rerun()
                        with nav_col2:
                            if st.button("📋 Review Agent Proposals", key="to_prop_m"):
                                st.toast("📋 Opening AI Recommendations...", icon="🤖")
                                st.session_state.current_page = "🤖 AI Recommendations"
                                st.rerun()

    # ---------------- TAB 3: ONE-CLICK DEMO DATASET ----------------
    with tab_instant:
        st.markdown("""
        <div class="custom-card" style="margin-top: 0.5rem;">
            <h4 style="color:#062E1E; font-family:'Space Grotesk'; margin-top:0;">
                ⚡ Instantly Load Calibrated Supermarket Network
            </h4>
            <p style="font-size:0.88rem; color:#475569;">
                Evaluating the platform during the hackathon? Load our production-grade benchmark network of:
            </p>
            <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:1rem; font-size:0.85rem; color:#1E293B;">
                <span class="badge" style="background:#DCFCE7; color:#15803D;">5 Supermarkets Online</span>
                <span class="badge" style="background:#E0E7FF; color:#4338CA;">15 Perishable Fresh SKUs</span>
                <span class="badge" style="background:#FEF3C7; color:#B45309;">30-Day POS Sales History</span>
                <span class="badge" style="background:#FFEDD5; color:#C2410C;">Real IoT Cold-Chain Telemetry</span>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🌱 Load Supermarket Benchmark Network & Run AI Agents", type="primary", use_container_width=True, key="btn_load_demo"):
            with st.spinner("Generating supermarket batches and computing multi-agent consensus..."):
                inv_df = generate_live_inventory()
                sales_df = generate_pos_sales_history()
                
                coord = CoordinatorAgent()
                proposals = []
                for _, row in inv_df.iterrows():
                    p = coord.reconcile_batch(row.to_dict(), inv_df)
                    proposals.append(p)

                st.session_state.inventory_df = inv_df
                st.session_state.sales_df = sales_df
                st.session_state.coordinator_proposals = proposals
                st.session_state.data_refreshed = True
                
            st.toast("✅ Loaded 5-Store Supermarket Network & executed AI Agents!", icon="🌱")
            st.success("✅ Supermarket dataset loaded! Redirecting to Dashboard...")
            st.session_state.current_page = "📊 Dashboard"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
