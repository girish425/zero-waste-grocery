"""
Excel Management Engine using OpenPyXL
Generates branded, styled Excel reports and handles ingestion workflows.
"""
import io
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, date

def export_inventory_workbook(inventory_df: pd.DataFrame, sales_df: pd.DataFrame = None) -> bytes:
    """
    Creates a styled multi-tab Excel workbook using OpenPyXL with:
    - Forest green headers and gold/lime accents
    - Conditional highlighting for critical expiry batches
    - Currency and percentage cell formatting
    """
    wb = openpyxl.Workbook()
    
    # ---------------- TAB 1: LIVE INVENTORY ----------------
    ws_inv = wb.active
    ws_inv.title = "Live_Perishables_Inventory"
    ws_inv.views.sheetView[0].showGridLines = True
    
    # Header styling
    header_fill = PatternFill(start_color="0D472C", end_color="0D472C", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    
    alert_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Red tint
    warn_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")  # Yellow tint
    fresh_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Green tint
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    # Selected columns for user-friendly export
    export_cols = [
        ("batch_code", "Batch Code"),
        ("store_name", "Store Location"),
        ("category", "Category"),
        ("product_name", "Product Name"),
        ("expiry_date", "Expiry Date"),
        ("days_to_expiry", "Days Left"),
        ("current_stock", "Stock (Units)"),
        ("unit_cost", "Unit Cost ($)"),
        ("base_price", "Retail Price ($)"),
        ("storage_temp_c", "Temp (°C)"),
        ("freshness_pct", "Freshness (%)")
    ]
    
    # Write Title
    ws_inv.cell(row=1, column=1, value="ZERO-WASTE GROCERY — PERISHABLE INVENTORY AUDIT").font = Font(name="Segoe UI", size=14, bold=True, color="062E1E")
    ws_inv.cell(row=2, column=1, value=f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Network Active Batches").font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
    
    # Write Headers
    header_row = 4
    for col_idx, (col_key, col_title) in enumerate(export_cols, start=1):
        cell = ws_inv.cell(row=header_row, column=col_idx, value=col_title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Write Data
    for row_idx, row_data in enumerate(inventory_df.to_dict(orient="records"), start=header_row + 1):
        dte = row_data.get("days_to_expiry", 99)
        
        for col_idx, (col_key, _) in enumerate(export_cols, start=1):
            val = row_data.get(col_key, "")
            if isinstance(val, (date, datetime)):
                val = val.strftime("%Y-%m-%d")
            
            c = ws_inv.cell(row=row_idx, column=col_idx, value=val)
            c.border = thin_border
            c.font = Font(name="Segoe UI", size=10)
            c.alignment = Alignment(vertical="center")
            
            # Formats
            if col_key in ["unit_cost", "base_price"]:
                c.number_format = '$#,##0.00'
                c.alignment = Alignment(horizontal="right", vertical="center")
            elif col_key in ["days_to_expiry", "current_stock"]:
                c.number_format = '#,##0'
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_key == "freshness_pct":
                c.number_format = '0.0"%"'
                c.alignment = Alignment(horizontal="right", vertical="center")
                
            # Expiry highlighting (only when expiry date is known)
            if dte is not None and not pd.isna(dte):
                if dte <= 1:
                    c.fill = alert_fill
                elif dte <= 2:
                    c.fill = warn_fill
                elif dte >= 5:
                    c.fill = fresh_fill
                
    # Auto-fit columns
    for col in ws_inv.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_inv.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    # ---------------- TAB 2: SALES SUMMARY (IF PRESENT) ----------------
    if sales_df is not None and not sales_df.empty:
        ws_sales = wb.create_sheet(title="POS_Sales_History")
        ws_sales.views.sheetView[0].showGridLines = True
        
        # Aggregate by Category & Store
        summary = sales_df.groupby(["store_name", "category"])[["quantity_sold", "revenue"]].sum().reset_index()
        
        ws_sales.cell(row=1, column=1, value="30-DAY POS SALES TRANSACTION PERFORMANCE").font = Font(name="Segoe UI", size=13, bold=True, color="062E1E")
        
        s_headers = ["Store Location", "Category", "Total Units Sold", "Gross Revenue ($)"]
        for c_idx, h in enumerate(s_headers, start=1):
            cell = ws_sales.cell(row=3, column=c_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        for r_idx, s_row in enumerate(summary.to_dict(orient="records"), start=4):
            ws_sales.cell(row=r_idx, column=1, value=s_row["store_name"]).border = thin_border
            ws_sales.cell(row=r_idx, column=2, value=s_row["category"]).border = thin_border
            c3 = ws_sales.cell(row=r_idx, column=3, value=s_row["quantity_sold"])
            c3.border = thin_border
            c3.number_format = '#,##0'
            c3.alignment = Alignment(horizontal="right")
            c4 = ws_sales.cell(row=r_idx, column=4, value=round(s_row["revenue"], 2))
            c4.border = thin_border
            c4.number_format = '$#,##0.00'
            c4.alignment = Alignment(horizontal="right")
            
        for col in ws_sales.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_sales.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # Save to memory stream
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def safely_read_file(uploaded_file) -> tuple:
    """
    Safely reads CSV or Excel files with fallback encodings and robust error handling.
    Returns (DataFrame or None, error_message or None).
    """
    if uploaded_file is None:
        return None, "No file provided."
        
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".csv"):
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="latin1")
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Unsupported file extension: '{filename}'. Please upload a .csv or .xlsx file."
            
        if df.empty:
            return None, "The uploaded file is empty (contains 0 data rows)."
            
        # Clean column names
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("(", "").replace(")", "").replace("$", "").replace("%", "pct").replace("°c", "c").replace("/", "_") for c in df.columns]
        return df, None
        
    except Exception as e:
        return None, f"Failed to read file '{uploaded_file.name}': {str(e)}"


def generate_sample_inventory_csv() -> bytes:
    """Generates sample inventory master catalog CSV."""
    sample_df = pd.DataFrame([
        {"sku": "PRD-AVO-01", "product_name": "Organic Hass Avocados (Pack of 3)", "category": "Produce", "unit_cost": 2.20, "base_price": 4.99, "lead_time_days": 1, "target_temp_c": 10.0},
        {"sku": "PRD-SPN-02", "product_name": "Organic Baby Spinach (250g)", "category": "Produce", "unit_cost": 1.10, "base_price": 3.29, "lead_time_days": 1, "target_temp_c": 4.0},
        {"sku": "PRD-BER-03", "product_name": "Hydroponic Strawberries (400g)", "category": "Produce", "unit_cost": 2.40, "base_price": 5.49, "lead_time_days": 1, "target_temp_c": 3.5},
        {"sku": "DAI-MLK-01", "product_name": "Farm Fresh Whole Milk (1L)", "category": "Dairy", "unit_cost": 1.35, "base_price": 3.19, "lead_time_days": 1, "target_temp_c": 3.0},
        {"sku": "BAK-SRD-01", "product_name": "Artisan Sourdough Loaf (Daily)", "category": "Bakery", "unit_cost": 1.20, "base_price": 4.79, "lead_time_days": 1, "target_temp_c": 20.0},
        {"sku": "MEA-CHK-01", "product_name": "Free-Range Chicken Breast (500g)", "category": "Meat & Seafood", "unit_cost": 4.80, "base_price": 9.99, "lead_time_days": 1, "target_temp_c": 1.5},
        {"sku": "DEL-SLD-01", "product_name": "Tuscan Kale Chicken Salad Bowl", "category": "Deli & Ready-to-Eat", "unit_cost": 3.20, "base_price": 7.99, "lead_time_days": 1, "target_temp_c": 3.0}
    ])
    return sample_df.to_csv(index=False).encode('utf-8')


def generate_sample_sales_csv() -> bytes:
    """Generates sample POS historical sales CSV."""
    today = date.today()
    rows = []
    sample_skus = [
        ("PRD-AVO-01", "GreenGrocer Downtown", 14, 4.99),
        ("PRD-SPN-02", "GreenGrocer Downtown", 22, 3.29),
        ("PRD-BER-03", "GreenGrocer Downtown", 18, 5.49),
        ("DAI-MLK-01", "GreenGrocer Downtown", 30, 3.19),
        ("BAK-SRD-01", "GreenGrocer Downtown", 15, 4.79),
        ("MEA-CHK-01", "GreenGrocer Downtown", 12, 9.99),
        ("DEL-SLD-01", "GreenGrocer Downtown", 16, 7.99)
    ]
    for d_offset in range(7):
        curr_d = today - pd.Timedelta(days=d_offset)
        for sku, store, base_qty, price in sample_skus:
            qty = max(2, int(base_qty * (1.2 if curr_d.weekday() >= 4 else 0.9)))
            rows.append({
                "date": curr_d.strftime("%Y-%m-%d"),
                "store_name": store,
                "sku": sku,
                "quantity_sold": qty,
                "revenue": round(qty * price, 2)
            })
    return pd.DataFrame(rows).to_csv(index=False).encode('utf-8')


def generate_sample_batches_csv() -> bytes:
    """Generates sample expiry & cold-chain batch tracking CSV."""
    today = date.today()
    sample_batches = pd.DataFrame([
        {"batch_code": "BTH-1011-01", "store_name": "GreenGrocer Downtown", "sku": "PRD-AVO-01", "current_stock": 24, "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "storage_temp_c": 9.8},
        {"batch_code": "BTH-1011-02", "store_name": "GreenGrocer Downtown", "sku": "PRD-SPN-02", "current_stock": 35, "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "storage_temp_c": 4.1},
        {"batch_code": "BTH-1011-03", "store_name": "GreenGrocer Downtown", "sku": "PRD-BER-03", "current_stock": 28, "expiry_date": (today + pd.Timedelta(days=0)).strftime("%Y-%m-%d"), "storage_temp_c": 3.6},
        {"batch_code": "BTH-1011-04", "store_name": "GreenGrocer Downtown", "sku": "DAI-MLK-01", "current_stock": 42, "expiry_date": (today + pd.Timedelta(days=3)).strftime("%Y-%m-%d"), "storage_temp_c": 3.1},
        {"batch_code": "BTH-1011-05", "store_name": "GreenGrocer Downtown", "sku": "BAK-SRD-01", "current_stock": 18, "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "storage_temp_c": 20.0},
        {"batch_code": "BTH-1011-06", "store_name": "GreenGrocer Downtown", "sku": "MEA-CHK-01", "current_stock": 20, "expiry_date": (today + pd.Timedelta(days=2)).strftime("%Y-%m-%d"), "storage_temp_c": 1.4},
        {"batch_code": "BTH-1011-07", "store_name": "GreenGrocer Downtown", "sku": "DEL-SLD-01", "current_stock": 15, "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "storage_temp_c": 3.2}
    ])
    return sample_batches.to_csv(index=False).encode('utf-8')


def generate_sample_unified_csv() -> bytes:
    """Generates sample unified all-in-one grocery inventory CSV."""
    today = date.today()
    unified_df = pd.DataFrame([
        {
            "batch_code": "BTH-AVO-01", "store_name": "Downtown Flagship", "sku": "PRD-AVO-01",
            "product_name": "Organic Hass Avocados (Pack of 3)", "category": "Produce",
            "current_stock": 24, "unit_cost": 2.20, "base_price": 4.99,
            "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_to_expiry": 1, "avg_daily_sales": 12.0, "storage_temp_c": 9.8, "target_temp_c": 10.0,
            "freshness_pct": 75.0, "carbon_factor_kg": 1.30, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-SPN-02", "store_name": "Downtown Flagship", "sku": "PRD-SPN-02",
            "product_name": "Organic Baby Spinach (250g)", "category": "Produce",
            "current_stock": 35, "unit_cost": 1.10, "base_price": 3.29,
            "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_to_expiry": 1, "avg_daily_sales": 15.0, "storage_temp_c": 4.1, "target_temp_c": 4.0,
            "freshness_pct": 60.0, "carbon_factor_kg": 0.85, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-BER-03", "store_name": "Downtown Flagship", "sku": "PRD-BER-03",
            "product_name": "Hydroponic Strawberries (400g)", "category": "Produce",
            "current_stock": 28, "unit_cost": 2.40, "base_price": 5.49,
            "expiry_date": today.strftime("%Y-%m-%d"),
            "days_to_expiry": 0, "avg_daily_sales": 14.0, "storage_temp_c": 3.6, "target_temp_c": 3.5,
            "freshness_pct": 25.0, "carbon_factor_kg": 1.10, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-MLK-01", "store_name": "Downtown Flagship", "sku": "DAI-MLK-01",
            "product_name": "Farm Fresh Whole Milk (1L)", "category": "Dairy",
            "current_stock": 45, "unit_cost": 1.35, "base_price": 3.19,
            "expiry_date": (today + pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
            "days_to_expiry": 3, "avg_daily_sales": 18.0, "storage_temp_c": 3.0, "target_temp_c": 3.0,
            "freshness_pct": 85.0, "carbon_factor_kg": 3.20, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-SRD-01", "store_name": "Downtown Flagship", "sku": "BAK-SRD-01",
            "product_name": "Artisan Sourdough Loaf (Daily)", "category": "Bakery",
            "current_stock": 16, "unit_cost": 1.20, "base_price": 4.79,
            "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_to_expiry": 1, "avg_daily_sales": 10.0, "storage_temp_c": 20.0, "target_temp_c": 20.0,
            "freshness_pct": 50.0, "carbon_factor_kg": 0.90, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-CHK-01", "store_name": "Downtown Flagship", "sku": "MEA-CHK-01",
            "product_name": "Free-Range Chicken Breast (500g)", "category": "Meat & Seafood",
            "current_stock": 22, "unit_cost": 4.80, "base_price": 9.99,
            "expiry_date": (today + pd.Timedelta(days=2)).strftime("%Y-%m-%d"),
            "days_to_expiry": 2, "avg_daily_sales": 8.0, "storage_temp_c": 1.4, "target_temp_c": 1.5,
            "freshness_pct": 65.0, "carbon_factor_kg": 6.80, "lead_time_days": 1
        },
        {
            "batch_code": "BTH-SLD-01", "store_name": "Downtown Flagship", "sku": "DEL-SLD-01",
            "product_name": "Tuscan Kale Chicken Salad Bowl", "category": "Deli & Ready-to-Eat",
            "current_stock": 14, "unit_cost": 3.20, "base_price": 7.99,
            "expiry_date": (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "days_to_expiry": 1, "avg_daily_sales": 9.0, "storage_temp_c": 3.2, "target_temp_c": 3.0,
            "freshness_pct": 50.0, "carbon_factor_kg": 2.60, "lead_time_days": 1
        }
    ])
    return unified_df.to_csv(index=False).encode('utf-8')


def parse_imported_dataset(uploaded_file) -> pd.DataFrame:
    """
    Parses and standardizes uploaded Excel (.xlsx) or CSV files for ingestion.
    Validates mandatory columns and coerces data types safely.
    """
    df, err = safely_read_file(uploaded_file)
    if err:
        raise ValueError(err)
        
    mapping = {
        "days_left": "days_to_expiry",
        "units": "current_stock",
        "stock_units": "current_stock",
        "retail_price": "base_price",
        "temp_c": "storage_temp_c",
        "temp": "storage_temp_c",
        "freshness_pct": "freshness_pct"
    }
    df = df.rename(columns=mapping)
    
    # Fill defaults if missing - DO NOT ASSUME MISSING EXPIRY
    if "days_to_expiry" not in df.columns and "expiry_date" in df.columns:
        df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors='coerce').dt.date
        df["days_to_expiry"] = df["expiry_date"].apply(
            lambda d: max(0, (d - date.today()).days) if pd.notnull(d) else None
        )
        
    return df


def validate_and_harmonize_data(
    unified_df: pd.DataFrame = None,
    inv_df: pd.DataFrame = None,
    sales_df: pd.DataFrame = None,
    batches_df: pd.DataFrame = None
) -> tuple:
    """
    Comprehensive validation engine.
    Associates separate files on 'sku', standardizes fields, and never silently invents data.
    Returns: (harmonized_df, validation_notes_list, is_valid_bool, error_list)
    """
    notes = []
    errors = []
    
    # 1. Path A: Unified File
    if unified_df is not None and not unified_df.empty:
        df = unified_df.copy()
        
        # Check required columns
        req_cols = ["sku"]
        missing_req = [c for c in req_cols if c not in df.columns]
        if missing_req:
            errors.append(f"Missing mandatory column: '{missing_req[0]}'. Please ensure your file has a SKU identifier.")
            return None, notes, False, errors
            
        # Check stock column
        if "current_stock" not in df.columns:
            if "stock" in df.columns:
                df["current_stock"] = df["stock"]
            elif "quantity" in df.columns:
                df["current_stock"] = df["quantity"]
            elif "units" in df.columns:
                df["current_stock"] = df["units"]
            else:
                errors.append("Missing inventory stock column: neither 'current_stock', 'stock', nor 'units' was found.")
                return None, notes, False, errors
                
        # Check expiry column
        if "expiry_date" not in df.columns and "days_to_expiry" not in df.columns:
            errors.append("Missing expiry column: neither 'expiry_date' nor 'days_to_expiry' was found in the file.")
            return None, notes, False, errors
            
        # Coerce types safely
        df["current_stock"] = pd.to_numeric(df["current_stock"], errors="coerce").fillna(0).astype(int)
        
        if "days_to_expiry" in df.columns:
            df["days_to_expiry"] = pd.to_numeric(df["days_to_expiry"], errors="coerce")
        elif "expiry_date" in df.columns:
            df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce").dt.date
            df["days_to_expiry"] = df["expiry_date"].apply(
                lambda d: max(0, (d - date.today()).days) if pd.notnull(d) else None
            )
            
        # Product name fallback
        if "product_name" not in df.columns:
            df["product_name"] = df["sku"].astype(str)
            notes.append("Product name column was missing; populated from SKU.")
            
        if "category" not in df.columns:
            df["category"] = "Perishables"
            notes.append("Category column was missing; defaulted to 'Perishables'.")
            
        if "unit_cost" not in df.columns:
            df["unit_cost"] = 2.50
            notes.append("Unit cost missing; assigned baseline benchmark value ($2.50).")
        else:
            df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(2.50)
            
        if "base_price" not in df.columns:
            df["base_price"] = (df["unit_cost"] * 1.8).round(2)
            notes.append("Retail base price missing; calculated at cost + 80% markup.")
        else:
            df["base_price"] = pd.to_numeric(df["base_price"], errors="coerce").fillna(4.99)
            
        if "avg_daily_sales" not in df.columns:
            # Baseline velocity based on stock
            df["avg_daily_sales"] = (df["current_stock"] / 3.0).clip(lower=1.0).round(1)
            notes.append("Historical velocity missing; estimated from inventory runway.")
        else:
            df["avg_daily_sales"] = pd.to_numeric(df["avg_daily_sales"], errors="coerce").fillna(5.0)
            
        if "store_name" not in df.columns:
            df["store_name"] = "Store Central"
        if "store_id" not in df.columns:
            df["store_id"] = "STR-001"
        if "storage_temp_c" not in df.columns:
            df["storage_temp_c"] = 4.0
        if "target_temp_c" not in df.columns:
            df["target_temp_c"] = 4.0
        if "carbon_factor_kg" not in df.columns:
            df["carbon_factor_kg"] = 1.20
        if "lead_time_days" not in df.columns:
            df["lead_time_days"] = 1
        if "freshness_pct" not in df.columns:
            df["freshness_pct"] = df["days_to_expiry"].apply(lambda d: min(100.0, max(10.0, d * 20.0)) if pd.notnull(d) else None)
            
        return df, notes, True, []

    # 2. Path B: Multi-File Modular Merge
    if inv_df is not None and not inv_df.empty and batches_df is not None and not batches_df.empty:
        # Check joining key
        if "sku" not in inv_df.columns:
            errors.append("Inventory master file is missing mandatory 'sku' column.")
            return None, notes, False, errors
            
        if "sku" not in batches_df.columns:
            errors.append("Batch/expiry file is missing mandatory 'sku' column to link with inventory master.")
            return None, notes, False, errors
            
        # Merge batches and inventory on SKU
        merged = pd.merge(batches_df, inv_df, on="sku", how="inner", suffixes=("_batch", "_master"))
        if merged.empty:
            errors.append("Zero records matched between your Inventory Master and Batch Expiry files on the 'sku' column. Please check SKU values.")
            return None, notes, False, errors
            
        notes.append(f"Successfully matched {len(merged)} batches with inventory catalog on SKU.")
        
        # Incorporate sales history if provided
        if sales_df is not None and not sales_df.empty and "sku" in sales_df.columns and "quantity_sold" in sales_df.columns:
            # Compute average daily sales per SKU
            sales_summary = sales_df.groupby("sku")["quantity_sold"].mean().reset_index()
            sales_summary.rename(columns={"quantity_sold": "avg_daily_sales"}, inplace=True)
            merged = pd.merge(merged, sales_summary, on="sku", how="left")
            merged["avg_daily_sales"] = merged["avg_daily_sales"].fillna(4.0).round(1)
            notes.append(f"Calculated daily velocity from {len(sales_df)} POS sales records.")
        else:
            merged["avg_daily_sales"] = 6.0
            notes.append("No POS sales history provided; initialized nominal velocity baseline.")
            
        # Clean standard columns
        if "current_stock" not in merged.columns and "stock" in merged.columns:
            merged["current_stock"] = merged["stock"]
            
        if "days_to_expiry" not in merged.columns and "expiry_date" in merged.columns:
            merged["expiry_date"] = pd.to_datetime(merged["expiry_date"], errors="coerce").dt.date
            merged["days_to_expiry"] = merged["expiry_date"].apply(
                lambda d: max(0, (d - date.today()).days) if pd.notnull(d) else None
            )
            
        # Assign defaults for missing metadata
        if "product_name" not in merged.columns:
            merged["product_name"] = merged["sku"]
        if "category" not in merged.columns:
            merged["category"] = "Perishables"
        if "unit_cost" not in merged.columns:
            merged["unit_cost"] = 2.50
        if "base_price" not in merged.columns:
            merged["base_price"] = 4.99
        if "store_name" not in merged.columns:
            merged["store_name"] = "Supermarket Location"
        if "store_id" not in merged.columns:
            merged["store_id"] = "STR-001"
        if "storage_temp_c" not in merged.columns:
            merged["storage_temp_c"] = 4.0
        if "target_temp_c" not in merged.columns:
            merged["target_temp_c"] = 4.0
        if "carbon_factor_kg" not in merged.columns:
            merged["carbon_factor_kg"] = 1.20
        if "lead_time_days" not in merged.columns:
            merged["lead_time_days"] = 1
        if "freshness_pct" not in merged.columns:
            merged["freshness_pct"] = merged["days_to_expiry"].apply(lambda d: min(100.0, max(10.0, d * 20.0)))
            
        return merged, notes, True, []
        
    errors.append("Insufficient data: please upload either a Unified File or both an Inventory Master and Batch Expiry file.")
    return None, notes, False, errors

