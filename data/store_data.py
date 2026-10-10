"""
Store and Perishable Catalog Metadata
Realistic configurations for multi-store grocery network.
"""
import pandas as pd
from datetime import datetime, date

# Multi-Store Grocery Network Configuration
STORES = {
    "STR-001": {
        "store_id": "STR-001",
        "name": "GreenGrocer Downtown Flagship",
        "city": "Metropolis Central",
        "type": "Urban Flagship",
        "daily_footfall": 4200,
        "cold_storage_capacity_m3": 180,
        "distance_to_hub_km": 12.5,
        "affluence_index": 1.25, # willingness to buy premium & organic
    },
    "STR-002": {
        "store_id": "STR-002",
        "name": "Organic Pantry Suburbia",
        "city": "Meadow Park",
        "type": "Suburban Hypermarket",
        "daily_footfall": 3100,
        "cold_storage_capacity_m3": 250,
        "distance_to_hub_km": 28.0,
        "affluence_index": 1.10,
    },
    "STR-003": {
        "store_id": "STR-003",
        "name": "FreshDaily Express Transit",
        "city": "Grand Central Station",
        "type": "Transit Convenience",
        "daily_footfall": 5800,
        "cold_storage_capacity_m3": 95,
        "distance_to_hub_km": 8.0,
        "affluence_index": 0.95,
    },
    "STR-004": {
        "store_id": "STR-004",
        "name": "Valley Harvest Community Mart",
        "city": "River Valley",
        "type": "Neighborhood Grocery",
        "daily_footfall": 2400,
        "cold_storage_capacity_m3": 140,
        "distance_to_hub_km": 35.5,
        "affluence_index": 1.05,
    },
    "STR-005": {
        "store_id": "STR-005",
        "name": "Harbor Bay Green Market",
        "city": "Seaside District",
        "type": "Coastal Boutique",
        "daily_footfall": 1950,
        "cold_storage_capacity_m3": 110,
        "distance_to_hub_km": 42.0,
        "affluence_index": 1.30,
    }
}

# Perishable Master Catalog
# Includes shelf life in days, standard storage temperatures, CO2 emissions per kg
CATALOG = [
    {
        "sku": "PRD-AVO-01",
        "name": "Organic Hass Avocados (Pack of 3)",
        "category": "Produce",
        "nominal_shelf_life": 5,
        "cost_price": 2.20,
        "base_price": 4.99,
        "storage_temp_c": 10.0,
        "temp_tolerance": 3.0,
        "carbon_factor_kg": 1.30, # kg CO2e per unit
        "unit": "pack",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "PRD-SPN-02",
        "name": "Organic Baby Spinach (250g Clamshell)",
        "category": "Produce",
        "nominal_shelf_life": 4,
        "cost_price": 1.10,
        "base_price": 3.29,
        "storage_temp_c": 4.0,
        "temp_tolerance": 2.0,
        "carbon_factor_kg": 0.85,
        "unit": "tub",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "PRD-BER-03",
        "name": "Hydroponic Sweet Strawberries (400g)",
        "category": "Produce",
        "nominal_shelf_life": 3,
        "cost_price": 2.40,
        "base_price": 5.49,
        "storage_temp_c": 3.5,
        "temp_tolerance": 1.5,
        "carbon_factor_kg": 1.10,
        "unit": "punnet",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "PRD-TOM-04",
        "name": "Vine-Ripened Heirloom Tomatoes (500g)",
        "category": "Produce",
        "nominal_shelf_life": 6,
        "cost_price": 1.80,
        "base_price": 4.49,
        "storage_temp_c": 12.0,
        "temp_tolerance": 3.0,
        "carbon_factor_kg": 0.95,
        "unit": "pack",
        "reorder_lead_time_days": 2
    },
    {
        "sku": "DAI-MLK-01",
        "name": "Farm Fresh Whole Milk (1L Glass Bottle)",
        "category": "Dairy",
        "nominal_shelf_life": 7,
        "cost_price": 1.35,
        "base_price": 3.19,
        "storage_temp_c": 3.0,
        "temp_tolerance": 1.5,
        "carbon_factor_kg": 3.20,
        "unit": "bottle",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "DAI-YOG-02",
        "name": "Authentic Greek Yogurt 0% Fat (500g)",
        "category": "Dairy",
        "nominal_shelf_life": 10,
        "cost_price": 1.90,
        "base_price": 4.29,
        "storage_temp_c": 4.0,
        "temp_tolerance": 2.0,
        "carbon_factor_kg": 2.80,
        "unit": "tub",
        "reorder_lead_time_days": 2
    },
    {
        "sku": "DAI-CHS-03",
        "name": "Artisanal Brie Cheese Wedge (200g)",
        "category": "Dairy",
        "nominal_shelf_life": 12,
        "cost_price": 3.10,
        "base_price": 6.89,
        "storage_temp_c": 5.0,
        "temp_tolerance": 2.5,
        "carbon_factor_kg": 4.90,
        "unit": "wedge",
        "reorder_lead_time_days": 3
    },
    {
        "sku": "BAK-SRD-01",
        "name": "Artisan Sourdough Batard (Daily Bake)",
        "category": "Bakery",
        "nominal_shelf_life": 2,
        "cost_price": 1.20,
        "base_price": 4.79,
        "storage_temp_c": 20.0,
        "temp_tolerance": 5.0,
        "carbon_factor_kg": 0.90,
        "unit": "loaf",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "BAK-CRS-02",
        "name": "French Pure Butter Croissant (Pack of 2)",
        "category": "Bakery",
        "nominal_shelf_life": 2,
        "cost_price": 1.10,
        "base_price": 3.99,
        "storage_temp_c": 20.0,
        "temp_tolerance": 5.0,
        "carbon_factor_kg": 1.15,
        "unit": "pack",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "BAK-BAG-03",
        "name": "Everything New York Bagels (Pack of 4)",
        "category": "Bakery",
        "nominal_shelf_life": 3,
        "cost_price": 1.45,
        "base_price": 4.49,
        "storage_temp_c": 20.0,
        "temp_tolerance": 5.0,
        "carbon_factor_kg": 1.05,
        "unit": "pack",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "MEA-CHK-01",
        "name": "Organic Free-Range Chicken Breast (500g)",
        "category": "Meat & Seafood",
        "nominal_shelf_life": 4,
        "cost_price": 4.80,
        "base_price": 9.99,
        "storage_temp_c": 1.5,
        "temp_tolerance": 1.0,
        "carbon_factor_kg": 6.80,
        "unit": "pack",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "MEA-SAL-02",
        "name": "Wild Atlantic Salmon Fillet (350g)",
        "category": "Meat & Seafood",
        "nominal_shelf_life": 3,
        "cost_price": 6.50,
        "base_price": 13.99,
        "storage_temp_c": 1.0,
        "temp_tolerance": 1.0,
        "carbon_factor_kg": 8.40,
        "unit": "fillet",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "MEA-BEE-03",
        "name": "Grass-Fed Lean Ground Beef 90/10 (450g)",
        "category": "Meat & Seafood",
        "nominal_shelf_life": 3,
        "cost_price": 4.20,
        "base_price": 8.89,
        "storage_temp_c": 1.5,
        "temp_tolerance": 1.0,
        "carbon_factor_kg": 18.20,
        "unit": "pack",
        "reorder_lead_time_days": 2
    },
    {
        "sku": "DEL-SLD-01",
        "name": "Tuscan Kale & Grilled Chicken Salad Bowl",
        "category": "Deli & Ready-to-Eat",
        "nominal_shelf_life": 2,
        "cost_price": 3.20,
        "base_price": 7.99,
        "storage_temp_c": 3.0,
        "temp_tolerance": 1.5,
        "carbon_factor_kg": 2.60,
        "unit": "bowl",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "DEL-SSH-02",
        "name": "Salmon Nigiri & California Roll Combo (12pc)",
        "category": "Deli & Ready-to-Eat",
        "nominal_shelf_life": 1,
        "cost_price": 5.10,
        "base_price": 11.99,
        "storage_temp_c": 2.5,
        "temp_tolerance": 1.0,
        "carbon_factor_kg": 3.90,
        "unit": "box",
        "reorder_lead_time_days": 1
    },
    {
        "sku": "DEL-SND-03",
        "name": "Smoked Turkey & Avocado Baguette",
        "category": "Deli & Ready-to-Eat",
        "nominal_shelf_life": 2,
        "cost_price": 2.80,
        "base_price": 6.99,
        "storage_temp_c": 3.5,
        "temp_tolerance": 1.5,
        "carbon_factor_kg": 2.10,
        "unit": "item",
        "reorder_lead_time_days": 1
    }
]

# Quick lookup dict
CATALOG_BY_SKU = {item["sku"]: item for item in CATALOG}
