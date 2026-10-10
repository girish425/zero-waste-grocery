"""
Data Normalization & Schema Validation Engine
Supports alias matching for diverse supermarket ERPs, validates types,
detects duplicates, explains errors in plain English, and never assumes missing expiry/sales data.
"""
import re
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional

# Canonical Internal Schema Definitions with explicit required/optional tagging
CANONICAL_FIELDS = {
    "sku": {
        "label": "Product Identifier (SKU)",
        "required": True,
        "type": "str",
        "description": "Unique product code or SKU identifier"
    },
    "current_stock": {
        "label": "Current Stock Quantity",
        "required": True,
        "type": "int",
        "description": "Available inventory units on hand"
    },
    "product_name": {
        "label": "Product Name",
        "required": False,
        "type": "str",
        "description": "Readable title or description of item"
    },
    "category": {
        "label": "Category",
        "required": False,
        "type": "str",
        "description": "Department or food classification"
    },
    "expiry_date": {
        "label": "Expiry Date",
        "required": False,
        "type": "date",
        "description": "Best-before / use-by calendar date (never assumed if missing)"
    },
    "unit_cost": {
        "label": "Unit Wholesale Cost ($)",
        "required": False,
        "type": "float",
        "description": "Acquisition cost per unit"
    },
    "base_price": {
        "label": "Retail Base Price ($)",
        "required": False,
        "type": "float",
        "description": "Normal shelf selling price"
    },
    "avg_daily_sales": {
        "label": "Average Daily Sales Velocity",
        "required": False,
        "type": "float",
        "description": "Historical sales volume per day (never assumed if missing)"
    },
    "sales_date": {
        "label": "Sales / Transaction Date",
        "required": False,
        "type": "date",
        "description": "Transaction or order date for sales logs"
    },
    "sales_quantity": {
        "label": "Sales Quantity Sold",
        "required": False,
        "type": "int",
        "description": "Number of units sold in transaction"
    },
    "store_id": {
        "label": "Store Identifier",
        "required": False,
        "type": "str",
        "description": "Branch code or location ID"
    },
    "store_name": {
        "label": "Store Name",
        "required": False,
        "type": "str",
        "description": "Readable supermarket branch name"
    },
    "batch_code": {
        "label": "Batch / Lot Code",
        "required": False,
        "type": "str",
        "description": "Lot or RFID batch tracking code"
    },
    "storage_temp_c": {
        "label": "Storage Sensor Temp (°C)",
        "required": False,
        "type": "float",
        "description": "Observed cold-chain sensor reading"
    },
    "target_temp_c": {
        "label": "Target Storage Temp (°C)",
        "required": False,
        "type": "float",
        "description": "Target nominal refrigeration temperature"
    },
    "lead_time_days": {
        "label": "Supplier Lead Time (Days)",
        "required": False,
        "type": "int",
        "description": "Supplier restock lead time in days"
    }
}

# Alias Lookup Dictionary for Diverse Retail Systems & POS Formats
ALIAS_MAP = {
    # Product identifier: product_id, SKU, sku_id, item_code
    "sku": [
        "product_id", "sku", "sku_id", "item_code", "product_code",
        "item_id", "barcode", "upc", "sku_code", "product_sku",
        "item_number", "part_number", "item_no", "article_id", "code"
    ],
    # Stock: stock, current_stock, quantity, inventory_quantity, available_quantity
    "current_stock": [
        "stock", "current_stock", "quantity", "inventory_quantity",
        "available_quantity", "units_on_hand", "on_hand", "qty",
        "inventory", "units", "stock_qty", "qty_on_hand", "balance",
        "closing_stock", "available_stock", "stock_quantity", "stock_level"
    ],
    # Product name: product_name, item_name, product, item, SKU name
    "product_name": [
        "product_name", "item_name", "product", "item", "sku_name",
        "title", "product_title", "description", "item_description",
        "name", "desc", "item_title", "product_desc", "article_name"
    ],
    # Category
    "category": [
        "category", "dept", "department", "aisle", "section", "family",
        "product_category", "group", "class", "commodity", "segment"
    ],
    # Expiry date: expiry_date, expiration_date, best_before, use_by
    "expiry_date": [
        "expiry_date", "expiration_date", "best_before", "use_by", "expiry",
        "exp_date", "expiration", "sell_by", "use_by_date", "best_before_date",
        "expire_date", "bb_date", "exp", "shelf_life_date", "valid_until", "end_date"
    ],
    # Sales date: date, sales_date, transaction_date, order_date
    "sales_date": [
        "sales_date", "transaction_date", "order_date", "date",
        "txn_date", "purchase_date", "day", "sale_date", "invoice_date"
    ],
    # Sales quantity: sales, units_sold, quantity_sold, sold_quantity
    "sales_quantity": [
        "sales", "units_sold", "quantity_sold", "sold_quantity",
        "sales_qty", "qty_sold", "volume_sold", "items_sold", "sold_units"
    ],
    # Store identifier: store_id, branch_id, location_id, store
    "store_id": [
        "store_id", "branch_id", "location_id", "store", "store_code",
        "shop_id", "outlet_id", "site_id", "branch_code", "location_code"
    ],
    # Store name
    "store_name": [
        "store_name", "branch_name", "location_name", "store_location",
        "store_title", "shop_name", "outlet_name"
    ],
    # Unit cost
    "unit_cost": [
        "unit_cost", "cost_price", "cost", "wholesale_price", "unit_cost_usd",
        "purchase_price", "cost_usd", "buying_price", "cogs", "standard_cost"
    ],
    # Base retail price
    "base_price": [
        "base_price", "retail_price", "selling_price", "price", "unit_price",
        "retail", "mrp", "sale_price", "shelf_price", "price_usd", "regular_price"
    ],
    # Average daily sales velocity
    "avg_daily_sales": [
        "avg_daily_sales", "daily_sales", "sales_velocity", "velocity",
        "units_per_day", "sales_per_day", "avg_sales", "daily_run_rate",
        "rate_of_sale", "run_rate"
    ],
    # Batch / Lot code
    "batch_code": [
        "batch_code", "batch_id", "lot_number", "batch", "lot", "lot_id",
        "batch_number", "rfid_tag", "lot_code"
    ],
    # Storage sensor temp
    "storage_temp_c": [
        "storage_temp_c", "temp_c", "temperature", "temp", "storage_temp",
        "actual_temp", "sensor_temp", "temp_reading", "cabinet_temp"
    ],
    # Target storage temp
    "target_temp_c": [
        "target_temp_c", "nominal_temp_c", "optimal_temp", "set_temp", "required_temp"
    ],
    # Lead time
    "lead_time_days": [
        "lead_time_days", "lead_time", "reorder_lead_time", "delivery_days", "supplier_lead_time"
    ]
}

def clean_column_name(col_name: str) -> str:
    """
    Standardizes a column header:
    - Trims leading and trailing spaces
    - Converts to lowercase
    - Replaces punctuation, symbols, and extra spaces with a single underscore
    """
    if col_name is None:
        return ""
    c = str(col_name).strip().lower()
    # Replace whitespace and punctuation with underscores
    c = re.sub(r'[\s\$\(\)\%\/\\\-\.\,\:\;\_]+', '_', c).strip('_')
    return c

def _alphanumeric_compact(text: str) -> str:
    """Removes all non-alphanumeric characters for fuzzy normalized comparisons."""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def suggest_column_mappings(
    df_columns: List[str]
) -> Tuple[Dict[str, str], List[str], Dict[str, Any]]:
    """
    Analyzes input DataFrame columns and maps them to canonical schema.
    Applies strict exact matching before fallback word-token matching,
    detects ambiguity when multiple columns match a canonical field,
    and never leaves required fields unmapped if a valid candidate exists.

    Returns:
    - best_mapping: {canonical_field: matched_raw_column}
    - unmapped_columns: list of raw columns not mapped
    - metadata_dict: contains 'candidates' (all matches), 'ambiguities' (flagged issues), 'is_ambiguous' (bool)
    """
    cleaned_to_raw = {clean_column_name(col): col for col in df_columns}
    raw_to_cleaned = {col: clean_column_name(col) for col in df_columns}
    
    # Store match scores: candidates[canonical_name] = [(raw_col, score, alias_matched)]
    candidates: Dict[str, List[Tuple[str, int, str]]] = {k: [] for k in CANONICAL_FIELDS}
    
    for raw_col in df_columns:
        cleaned_col = raw_to_cleaned[raw_col]
        col_compact = _alphanumeric_compact(cleaned_col)
        
        for canonical_name, aliases in ALIAS_MAP.items():
            for alias in aliases:
                cleaned_alias = clean_column_name(alias)
                alias_compact = _alphanumeric_compact(cleaned_alias)
                
                # Tier 1: Exact match on cleaned snake_case or compact alphanumeric string
                if cleaned_col == cleaned_alias or (col_compact == alias_compact and len(col_compact) > 0):
                    candidates[canonical_name].append((raw_col, 100, alias))
                    break
                    
                # Tier 2: Word-boundary token match (e.g., '_use_by_' or starts/ends with token)
                # Ensure alias is at least 4 chars to prevent generic short words from false-matching
                elif len(cleaned_alias) >= 4 and re.search(rf'(^|_){re.escape(cleaned_alias)}(_|$)', cleaned_col):
                    candidates[canonical_name].append((raw_col, 75, alias))
                    break
                    
                # Tier 3: Substring match if alias is descriptive (>= 6 chars)
                elif len(cleaned_alias) >= 6 and cleaned_alias in cleaned_col:
                    candidates[canonical_name].append((raw_col, 50, alias))
                    break

    # Prioritize assignment:
    # 1. Exact matches (Score 100) first, starting with Required fields
    best_mapping: Dict[str, str] = {}
    mapped_raw_cols = set()
    ambiguities: Dict[str, List[str]] = {}
    
    # Sort canonical fields so required ones are matched first
    canonical_order = sorted(
        CANONICAL_FIELDS.keys(),
        key=lambda k: (0 if CANONICAL_FIELDS[k]["required"] else 1, k)
    )
    
    # Pass 1: Exact matches (Score 100)
    for canonical_name in canonical_order:
        matches = [m for m in candidates[canonical_name] if m[1] == 100]
        if len(matches) == 1:
            raw = matches[0][0]
            if raw not in mapped_raw_cols:
                best_mapping[canonical_name] = raw
                mapped_raw_cols.add(raw)
        elif len(matches) > 1:
            # Ambiguity: multiple exact matches
            available = [m[0] for m in matches if m[0] not in mapped_raw_cols]
            if available:
                best_mapping[canonical_name] = available[0]
                mapped_raw_cols.add(available[0])
                if len(available) > 1:
                    ambiguities[canonical_name] = available

    # Pass 2: Fuzzy / Word-token matches (Score >= 50) for unmapped fields
    for canonical_name in canonical_order:
        if canonical_name in best_mapping:
            continue
        available_matches = [m for m in candidates[canonical_name] if m[0] not in mapped_raw_cols]
        if available_matches:
            # Sort by score descending
            available_matches.sort(key=lambda x: x[1], reverse=True)
            top_score = available_matches[0][1]
            top_matches = [m[0] for m in available_matches if m[1] == top_score]
            
            best_mapping[canonical_name] = top_matches[0]
            mapped_raw_cols.add(top_matches[0])
            if len(top_matches) > 1:
                ambiguities[canonical_name] = top_matches

    unmapped = [col for col in df_columns if col not in mapped_raw_cols]
    
    # Format candidates dictionary for backward compatibility (list of raw column strings)
    candidates_by_canonical = {
        k: list(dict.fromkeys([m[0] for m in matches]))
        for k, matches in candidates.items()
    }
    
    is_ambiguous = len(ambiguities) > 0
    metadata = {
        "candidates": candidates_by_canonical,
        "ambiguities": ambiguities,
        "is_ambiguous": is_ambiguous
    }
    
    return best_mapping, unmapped, metadata

def parse_date_safely(val: Any) -> Optional[date]:
    """
    Safely parses diverse date representations across retail systems.
    Supports ISO formats, US formats (MM/DD/YYYY), European formats (DD/MM/YYYY),
    timestamps, and date objects.
    Returns datetime.date or None if invalid or missing.
    NEVER fabricates or assumes dates.
    """
    if pd.isna(val) or val is None:
        return None
        
    val_str = str(val).strip()
    if val_str == "" or val_str.lower() in ["nan", "none", "null", "nat", "0", "undefined", "n/a"]:
        return None
        
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val
        
    # Standard format attempts
    formats_to_try = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y"
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(val_str, fmt).date()
        except (ValueError, TypeError):
            continue
            
    # Fallback to pandas parser
    try:
        dt = pd.to_datetime(val_str, errors="coerce")
        if pd.notnull(dt):
            return dt.date()
    except Exception:
        pass
        
    return None

def normalize_and_validate_inventory(
    raw_df: pd.DataFrame,
    column_mapping: Dict[str, str] = None,
    current_date: date = None
) -> Dict[str, Any]:
    """
    Normalizes input DataFrame into canonical schema and validates records rigorously.
    
    Requirements fulfilled:
    - Normalizes recognized columns to consistent internal schema
    - Distinguishes required fields from optional fields
    - Explains validation problems in plain language
    - Validates data types, dates, missing values, negative quantities, duplicates
    - Does NOT assume a missing expiry date or sales quantity
    - Does NOT treat a product's expiry status as known if expiry date is missing
    - Preserves original raw uploaded data for reference
    
    Returns structured results:
    - 'valid_df': DataFrame of accepted rows in canonical schema
    - 'raw_df': Original unmutated DataFrame
    - 'accepted_count': int
    - 'rejected_count': int
    - 'rejected_details': List[Dict] with row_index, reasons, raw row data
    - 'warnings': List[str]
    - 'has_missing_expiry': bool (true if any accepted products lack expiry date)
    - 'missing_expiry_count': int
    - 'has_unrecorded_sales': bool
    - 'unrecorded_sales_count': int
    - 'duplicate_count': int
    - 'is_ambiguous': bool
    """
    if current_date is None:
        current_date = date.today()
        
    if raw_df is None or raw_df.empty:
        return {
            "valid_df": pd.DataFrame(),
            "raw_df": raw_df,
            "accepted_count": 0,
            "rejected_count": 0,
            "rejected_details": [{"row_index": 0, "reasons": ["Uploaded file is completely empty."]}],
            "warnings": ["The provided dataset contains 0 rows."],
            "has_missing_expiry": False,
            "missing_expiry_count": 0,
            "has_unrecorded_sales": False,
            "unrecorded_sales_count": 0,
            "duplicate_count": 0,
            "is_ambiguous": False
        }
        
    # Auto-detect mappings if none provided
    is_ambiguous = False
    if column_mapping is None:
        column_mapping, _, meta = suggest_column_mappings(list(raw_df.columns))
        is_ambiguous = meta.get("is_ambiguous", False)
        
    # Check presence of required fields in mapping
    missing_required = []
    for req_field, meta_field in CANONICAL_FIELDS.items():
        if meta_field["required"]:
            mapped_col = column_mapping.get(req_field)
            if not mapped_col or mapped_col not in raw_df.columns:
                missing_required.append(f"{meta_field['label']} ('{req_field}')")
                
    if missing_required:
        return {
            "valid_df": pd.DataFrame(),
            "raw_df": raw_df,
            "accepted_count": 0,
            "rejected_count": len(raw_df),
            "rejected_details": [{
                "row_index": 1,
                "reasons": [
                    f"Required column mapping missing: {', '.join(missing_required)}. "
                    f"Please map these required columns. Available columns in your file: {list(raw_df.columns)}"
                ]
            }],
            "warnings": [f"Cannot process dataset: missing mandatory column mappings for {', '.join(missing_required)}."],
            "has_missing_expiry": False,
            "missing_expiry_count": 0,
            "has_unrecorded_sales": False,
            "unrecorded_sales_count": 0,
            "duplicate_count": 0,
            "is_ambiguous": True
        }
        
    accepted_rows = []
    rejected_details = []
    warnings = []
    missing_expiry_count = 0
    unrecorded_sales_count = 0
    seen_identifiers = set()
    duplicate_count = 0
    
    sku_col = column_mapping.get("sku")
    stock_col = column_mapping.get("current_stock")
    expiry_col = column_mapping.get("expiry_date")
    name_col = column_mapping.get("product_name")
    cat_col = column_mapping.get("category")
    cost_col = column_mapping.get("unit_cost")
    price_col = column_mapping.get("base_price")
    sales_col = column_mapping.get("avg_daily_sales") or column_mapping.get("sales_quantity")
    store_col = column_mapping.get("store_name")
    store_id_col = column_mapping.get("store_id")
    batch_col = column_mapping.get("batch_code")
    temp_col = column_mapping.get("storage_temp_c")
    target_temp_col = column_mapping.get("target_temp_c")
    lead_time_col = column_mapping.get("lead_time_days")
    
    for idx, raw_row in raw_df.iterrows():
        display_idx = idx + 1 # 1-indexed for plain language display to users
        rejection_reasons = []
        
        # 1. Validate Product Identifier (SKU) - REQUIRED
        raw_sku = raw_row.get(sku_col) if sku_col else None
        if pd.isna(raw_sku) or str(raw_sku).strip() == "" or str(raw_sku).lower() in ["nan", "none", "null"]:
            rejection_reasons.append("Missing product identifier (SKU is empty or blank).")
            sku_val = None
        else:
            sku_val = str(raw_sku).strip()
            
        # 2. Validate Stock Quantity - REQUIRED
        raw_stock = raw_row.get(stock_col) if stock_col else None
        if pd.isna(raw_stock) or str(raw_stock).strip() == "":
            rejection_reasons.append("Stock quantity is missing or blank.")
            stock_val = None
        else:
            try:
                stock_float = float(raw_stock)
                if np.isnan(stock_float):
                    rejection_reasons.append("Stock value is NaN.")
                    stock_val = None
                elif stock_float < 0:
                    rejection_reasons.append(f"Negative stock quantity ({stock_float}). Inventory cannot be negative.")
                    stock_val = None
                else:
                    stock_val = int(round(stock_float))
            except (ValueError, TypeError):
                rejection_reasons.append(f"Invalid stock value '{raw_stock}'. Must be a non-negative number.")
                stock_val = None
                
        # If mandatory constraints failed, reject row immediately
        if rejection_reasons:
            rejected_details.append({
                "row_index": display_idx,
                "reasons": rejection_reasons,
                "data": {str(k): str(v) for k, v in raw_row.items()}
            })
            continue
            
        # 3. Check Duplicate Records (by SKU + Store + Batch)
        store_id_val = str(raw_row.get(store_id_col)).strip() if (store_id_col and pd.notnull(raw_row.get(store_id_col))) else "STR-001"
        store_val = str(raw_row.get(store_col)).strip() if (store_col and pd.notnull(raw_row.get(store_col))) else "Metro Supermarket"
        batch_val = str(raw_row.get(batch_col)).strip() if (batch_col and pd.notnull(raw_row.get(batch_col))) else f"BTH-{display_idx:04d}"
        
        row_id_key = (sku_val, store_id_val, batch_val)
        if row_id_key in seen_identifiers:
            duplicate_count += 1
            warnings.append(
                f"Row {display_idx}: Duplicate record detected for SKU '{sku_val}' at '{store_val}' "
                f"(Batch: '{batch_val}'). Ingested as separate batch lot."
            )
        else:
            seen_identifiers.add(row_id_key)
            
        # 4. Validate Expiry Date - OPTIONAL (DO NOT ASSUME OR FABRICATE!)
        raw_expiry = raw_row.get(expiry_col) if expiry_col else None
        parsed_exp = parse_date_safely(raw_expiry)
        
        if parsed_exp is None:
            # Expiry date is genuinely missing or omitted
            missing_expiry_count += 1
            days_to_expiry = None
            freshness_pct = None
            expiry_status = "UNKNOWN_EXPIRY"
            if raw_expiry is not None and str(raw_expiry).strip() != "" and str(raw_expiry).lower() not in ["nan", "none", "null"]:
                warnings.append(
                    f"Row {display_idx}: Expiry date '{raw_expiry}' could not be parsed as a valid calendar date. "
                    "Shelf-life status treated as Unspecified."
                )
        else:
            days_to_expiry = (parsed_exp - current_date).days
            if days_to_expiry < 0:
                expiry_status = "EXPIRED"
            elif days_to_expiry == 0:
                expiry_status = "DUE_TODAY"
            elif days_to_expiry <= 2:
                expiry_status = "URGENT"
            else:
                expiry_status = "SAFE"
                
            nominal_life = max(3, days_to_expiry + 2)
            freshness_pct = max(0.0, min(100.0, round((days_to_expiry / nominal_life) * 100.0, 1)))
            
        # 5. Validate Unit Cost and Base Price
        raw_cost = raw_row.get(cost_col) if cost_col else None
        try:
            cost_val = float(raw_cost) if pd.notnull(raw_cost) and str(raw_cost).strip() != "" else 2.50
            if cost_val < 0:
                warnings.append(f"Row {display_idx}: Negative wholesale cost (${cost_val:.2f}) corrected to $0.00.")
                cost_val = 0.0
        except (ValueError, TypeError):
            cost_val = 2.50
            warnings.append(f"Row {display_idx}: Non-numeric unit cost '{raw_cost}' assigned default baseline ($2.50).")
            
        raw_price = raw_row.get(price_col) if price_col else None
        try:
            price_val = float(raw_price) if pd.notnull(raw_price) and str(raw_price).strip() != "" else round(cost_val * 1.8, 2)
            if price_val < 0:
                warnings.append(f"Row {display_idx}: Negative retail price (${price_val:.2f}) corrected to $0.00.")
                price_val = 0.0
        except (ValueError, TypeError):
            price_val = round(cost_val * 1.8, 2)
            
        # 6. Validate Average Daily Sales Velocity - OPTIONAL (DO NOT ASSUME IF MISSING)
        raw_sales = raw_row.get(sales_col) if sales_col else None
        if raw_sales is None or pd.isna(raw_sales) or str(raw_sales).strip() == "" or str(raw_sales).lower() in ["nan", "none", "null"]:
            sales_val = None
            unrecorded_sales_count += 1
        else:
            try:
                sales_float = float(raw_sales)
                if sales_float < 0:
                    warnings.append(f"Row {display_idx}: Negative sales quantity ({sales_float}) corrected to 0.")
                    sales_val = 0.0
                else:
                    sales_val = sales_float
            except (ValueError, TypeError):
                sales_val = None
                unrecorded_sales_count += 1
                warnings.append(f"Row {display_idx}: Unparseable sales velocity '{raw_sales}' treated as unrecorded.")
                
        # 7. Other Optional Metadata
        name_val = str(raw_row.get(name_col)).strip() if (name_col and pd.notnull(raw_row.get(name_col))) else sku_val
        cat_val = str(raw_row.get(cat_col)).strip() if (cat_col and pd.notnull(raw_row.get(cat_col))) else "General Perishables"
        
        try:
            temp_val = float(raw_row.get(temp_col)) if (temp_col and pd.notnull(raw_row.get(temp_col))) else 4.0
        except (ValueError, TypeError):
            temp_val = 4.0
            
        try:
            target_temp_val = float(raw_row.get(target_temp_col)) if (target_temp_col and pd.notnull(raw_row.get(target_temp_col))) else temp_val
        except (ValueError, TypeError):
            target_temp_val = 4.0
            
        try:
            lead_time_val = int(raw_row.get(lead_time_col)) if (lead_time_col and pd.notnull(raw_row.get(lead_time_col))) else 1
        except (ValueError, TypeError):
            lead_time_val = 1

        # Build Standardized Canonical Record
        accepted_rows.append({
            "batch_id": f"{store_id_val}-{sku_val}-{display_idx}",
            "batch_code": batch_val,
            "store_id": store_id_val,
            "store_name": store_val,
            "sku": sku_val,
            "product_name": name_val,
            "category": cat_val,
            "current_stock": stock_val,
            "expiry_date": parsed_exp,
            "days_to_expiry": days_to_expiry,
            "expiry_status": expiry_status,
            "unit_cost": round(cost_val, 2),
            "base_price": round(price_val, 2),
            "current_price": round(price_val, 2),
            "avg_daily_sales": round(sales_val, 1) if sales_val is not None else None,
            "storage_temp_c": round(temp_val, 1),
            "target_temp_c": round(target_temp_val, 1),
            "freshness_pct": freshness_pct,
            "carbon_factor_kg": 1.20,
            "lead_time_days": lead_time_val,
            "unit": "unit"
        })

    valid_df = pd.DataFrame(accepted_rows)
    
    return {
        "valid_df": valid_df,
        "raw_df": raw_df,
        "accepted_count": len(valid_df),
        "rejected_count": len(rejected_details),
        "rejected_details": rejected_details,
        "warnings": warnings,
        "has_missing_expiry": missing_expiry_count > 0,
        "missing_expiry_count": missing_expiry_count,
        "has_unrecorded_sales": unrecorded_sales_count > 0,
        "unrecorded_sales_count": unrecorded_sales_count,
        "duplicate_count": duplicate_count,
        "is_ambiguous": is_ambiguous
    }
