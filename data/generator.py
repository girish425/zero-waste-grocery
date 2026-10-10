"""
Data Generation Engine for Zero-Waste Grocery
Generates realistic multi-store inventory, POS sales histories, and cold-chain sensor readings.
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from data.store_data import STORES, CATALOG, CATALOG_BY_SKU

# Seed for reproducible realistic behavior while allowing dynamic refreshes
DEFAULT_SEED = 42

def generate_live_inventory(current_date: date = None, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """
    Generates realistic live perishable batches across all stores in the network.
    Includes inventory quantities, expiry dates, batch tracking, and storage telemetry.
    """
    if current_date is None:
        current_date = date.today()
        
    random.seed(seed)
    np.random.seed(seed)
    
    rows = []
    
    for store_id, store_info in STORES.items():
        footfall_ratio = store_info["daily_footfall"] / 3500.0
        affluence = store_info["affluence_index"]
        
        for item in CATALOG:
            sku = item["sku"]
            cat = item["category"]
            nominal_life = item["nominal_shelf_life"]
            
            # Base daily velocity is proportional to footfall and item popularity
            base_daily_velocity = max(2.0, (15.0 / (nominal_life ** 0.5)) * footfall_ratio * affluence)
            
            # Decide how many active batches are on shelf (1 to 3 batches with different expiry)
            # High turnover items usually have multiple staggered batches
            num_batches = 2 if nominal_life <= 3 else random.choice([1, 2, 3])
            
            for b_idx in range(num_batches):
                # Stagger remaining days to expiry: some urgent (<2 days), some medium, some fresh
                if b_idx == 0:
                    # Urgent or near-term batch
                    remaining_days = random.choice([0, 1, 1, 2, 2, 3])
                elif b_idx == 1:
                    # Mid-life batch
                    remaining_days = min(nominal_life, random.choice([2, 3, 4, max(3, nominal_life - 1)]))
                else:
                    # Freshly received batch
                    remaining_days = nominal_life
                
                expiry_dt = current_date + timedelta(days=remaining_days)
                received_dt = expiry_dt - timedelta(days=nominal_life)
                
                # Batch quantity based on daily velocity and remaining days
                if remaining_days <= 1:
                    # Often some residual stock that didn't clear
                    stock_units = int(max(3, np.random.normal(loc=base_daily_velocity * 1.4, scale=base_daily_velocity * 0.3)))
                else:
                    stock_units = int(max(6, np.random.normal(loc=base_daily_velocity * 2.8, scale=base_daily_velocity * 0.5)))
                
                # Sensor simulation: cold chain temperature
                target_temp = item["storage_temp_c"]
                temp_variance = np.random.normal(0.0, 0.4)
                actual_temp = round(target_temp + temp_variance, 1)
                
                # Batch Code
                batch_code = f"BTH-{expiry_dt.strftime('%m%d')}-{random.randint(100, 999)}"
                
                # Freshness score percentage (100% when received, 0% on expiry)
                age_days = (current_date - received_dt).days
                freshness_pct = max(0.0, min(100.0, round(((nominal_life - age_days) / nominal_life) * 100.0, 1)))
                
                rows.append({
                    "batch_id": f"{store_id}-{sku}-{b_idx}",
                    "batch_code": batch_code,
                    "store_id": store_id,
                    "store_name": store_info["name"],
                    "sku": sku,
                    "product_name": item["name"],
                    "category": cat,
                    "received_date": received_dt,
                    "expiry_date": expiry_dt,
                    "days_to_expiry": remaining_days,
                    "current_stock": stock_units,
                    "unit_cost": item["cost_price"],
                    "base_price": item["base_price"],
                    "current_price": item["base_price"], # Default before agent markdown
                    "avg_daily_sales": round(base_daily_velocity, 1),
                    "storage_temp_c": actual_temp,
                    "target_temp_c": target_temp,
                    "carbon_factor_kg": item["carbon_factor_kg"],
                    "unit": item["unit"],
                    "freshness_pct": freshness_pct,
                    "lead_time_days": item["reorder_lead_time_days"]
                })
                
    df = pd.DataFrame(rows)
    return df

def generate_pos_sales_history(days: int = 30, end_date: date = None, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """
    Generates 30-day realistic POS transactional history with day-of-week patterns,
    weekend spikes, and category variances for training & forecasting models.
    """
    if end_date is None:
        end_date = date.today()
        
    random.seed(seed)
    np.random.seed(seed)
    
    date_range = [end_date - timedelta(days=i) for i in reversed(range(days))]
    sales_records = []
    
    for dt in date_range:
        dow = dt.weekday() # 0 = Monday, 6 = Sunday
        # Weekend boost (Friday = 1.25, Saturday = 1.45, Sunday = 1.35)
        dow_multiplier = 1.45 if dow == 5 else (1.35 if dow == 6 else (1.20 if dow == 4 else 0.95))
        
        for store_id, store_info in STORES.items():
            store_mult = (store_info["daily_footfall"] / 3500.0) * store_info["affluence_index"]
            
            for item in CATALOG:
                sku = item["sku"]
                nominal_life = item["nominal_shelf_life"]
                base_vel = (15.0 / (nominal_life ** 0.5)) * store_mult * dow_multiplier
                
                # Add random noise and zero truncation
                sold_qty = max(0, int(np.random.poisson(lam=base_vel)))
                revenue = round(sold_qty * item["base_price"], 2)
                
                sales_records.append({
                    "date": dt,
                    "day_of_week": dt.strftime("%A"),
                    "store_id": store_id,
                    "store_name": store_info["name"],
                    "sku": sku,
                    "product_name": item["name"],
                    "category": item["category"],
                    "quantity_sold": sold_qty,
                    "revenue": revenue,
                    "unit_price": item["base_price"]
                })
                
    return pd.DataFrame(sales_records)
