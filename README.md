# 🌿 Zero-Waste Grocery
### An Agentic AI Approach to Perishable Demand & Shelf-Life Management
**GDGoC HITAM · Agentic AI Hackathon (Sustainability Track)**

---

## 🎯 Executive Summary & Problem Context
Perishable grocery items (fresh produce, dairy, bakery, meat & seafood, prepared deli items) have variable, short biological shelf lives. In traditional grocery management:
- **Excess inventory** results in massive food waste ending up in municipal landfills, producing potent methane emissions ($CO_2e$) and causing severe retailer financial losses.
- **Shortages / Stockouts** lead to missed revenue and dissatisfied shoppers.
- **Siloed static planning** (e.g., standard Min/Max reorder rules and naive 50% discount stickers only on expiry morning) fails to balance regional store networks or optimize dynamic pricing across decay windows.

**Zero-Waste Grocery** introduces an autonomous **Multi-Agent Orchestration Engine** that continuously forecasts demand, estimates biological spoilage hazards, and reconciles replenishment, dynamic markdown, inter-store balancing transfers, and food bank donations into **exactly one optimal action per SKU and store for human planner authorization**.

---

## 🏗️ Multi-Agent Architecture

```
                               ┌────────────────────────┐
                               │   Store Telemetry &    │
                               │  Cold-Chain IoT Data   │
                               └───────────┬────────────┘
                                           │
       ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
       ▼                   ▼                               ▼                   ▼
┌──────────────┐    ┌──────────────┐                ┌──────────────┐    ┌──────────────┐
│ Demand Agent │    │Spoilage Agent│                │Restock Agent │    │Markdown Agent│
│  (Velocity & │    │  (Arrhenius  │                │(Safety Stock │    │ (Elasticity  │
│  Elasticity) │    │ Hazard Rate) │                │ & Lead-Time) │    │  Discount)   │
└──────┬───────┘    └──────┬───────┘                └──────┬───────┘    └──────┬───────┘
       │                   │                               │                   │
       └───────────────────┼───────────────┬───────────────┴───────────────────┘
                           │               │
                           ▼               ▼
                 ┌──────────────────────────────────┐
                 │    Inter-Store Transfer Agent    │
                 │   (Regional Network Balancing)   │
                 └─────────────────┬────────────────┘
                                   │
                                   ▼
                 ┌──────────────────────────────────┐
                 │     CHIEF COORDINATOR AGENT      │
                 │ (Arbitration & Single Proposal)  │
                 └─────────────────┬────────────────┘
                                   │
                                   ▼
                 ┌──────────────────────────────────┐
                 │   Planner Review Queue (HITL)    │
                 │   (Approve / Override / Batch)   │
                 └─────────────────┬────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│  POS / ESL   │           │   WMS Hub    │           │   ERP / PO   │
│ Dynamic Tags │           │  Transfers   │           │ Replenishment│
└──────────────┘           └──────────────┘           └──────────────┘
```

### The 6 Specialized Autonomous Agents:
1. **Demand Agent (`DemandAgent`)**:
   - Analyzes actual historical sales transactions and projects multi-horizon consumer velocity.
   - Computes day-of-week seasonality, temperature sensitivity, and probabilistic uncertainty bounds ($P_{10}, P_{50}, P_{90}$).
   - **Data Integrity Rule**: If sales velocity is unrecorded, explicitly documents assumptions without guessing.
2. **Freshness Agent (`FreshnessAgent`)**:
   - Evaluates remaining shelf-life, cold-chain temperature deviations ($Q_{10}$ Arrhenius acceleration), and biological hazard rates.
   - Categorizes inventory into actionable freshness tiers: Expired ($DTE \le 0$), Critical ($DTE \le 1$), Urgent ($DTE \le 2$), Warning ($DTE \le 4$), or Fresh ($DTE > 4$).
   - **Data Integrity Rule**: If expiry dates are missing, transparently flags them as *Unspecified* rather than inventing biological decay.
3. **Discount Agent (`DiscountAgent`)**:
   - Suggests defensible dynamic markdowns ($15\%, 20\%, 30\%, 60\%$) to clear surplus inventory before biological expiry based on price elasticity ($\epsilon = -1.35$).
   - **Strict Constraint**: Only calculates markdowns when an explicit, configurable discount policy is enabled and verified surplus exists. Refuses markdowns if policy is disabled or expiry is unrecorded.
4. **Replenishment Agent (`ReplenishmentAgent`)**:
   - Monitors safety stock runways, supplier lead times, and cycle service levels ($Z = 1.65$ for 95% service level) to compute optimal reorder points.
   - **Conflict Prevention**: Strictly suppresses purchase orders if a batch faces near-term expiry or if sales velocity is unrecorded, preventing inventory bulking and downstream waste.
5. **Store Transfer Agent (`StoreTransferAgent`)**:
   - Scans the store network to identify high-velocity sister stores with low days of cover that can absorb surplus inventory at full retail price.
   - **Strict Multi-Store Constraint**: Refuses to propose transfers unless multiple store locations exist in the dataset and remaining shelf-life is $\ge 2$ days for transit feasibility. Calculates net salvage after handling and fuel costs.
6. **Chief Coordinator Agent (`CoordinatorAgent`)**:
   - Synthesizes findings from all 5 specialist agents, removes duplicate or conflicting proposals, assigns priority tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and generates a unified, reconciled action list for human planner review.

---

## 📊 Canonical Data Schema & Supported Aliases

The platform features an intelligent schema normalization engine that case-insensitively maps diverse retailer column headers to internal canonical attributes:

| Canonical Field | Type | Required? | Accepted Aliases | Description |
| :--- | :---: | :---: | :--- | :--- |
| `sku` | String | **Required** | `sku`, `product_id`, `sku_id`, `item_code`, `code` | Unique item identifier |
| `product_name` | String | **Required** | `product_name`, `item_name`, `product`, `item`, `sku_name`, `name` | Human-readable product name |
| `current_stock` | Float | **Required** | `stock`, `current_stock`, `quantity`, `inventory_quantity`, `available_quantity`, `qty` | Units available on shelf/backroom |
| `expiry_date` | Date | *Optional* | `expiry_date`, `expiration_date`, `best_before`, `use_by`, `expiry`, `exp_date` | Shelf-life limit (ISO / US / EU formats) |
| `sales_date` | Date | *Optional* | `date`, `sales_date`, `transaction_date`, `order_date` | Date of POS transaction record |
| `units_sold` | Float | *Optional* | `sales`, `units_sold`, `quantity_sold`, `sold_quantity`, `qty_sold` | Number of units purchased |
| `store_id` | String | *Optional* | `store_id`, `branch_id`, `location_id`, `store`, `branch` | Store / location code |
| `store_name` | String | *Optional* | `store_name`, `branch_name`, `location`, `supermarket` | Human-readable branch name |
| `category` | String | *Optional* | `category`, `dept`, `department`, `food_group` | Department (Produce, Dairy, Bakery, Meat) |
| `unit_cost` | Float | *Optional* | `unit_cost`, `cost`, `cogs`, `wholesale_cost` | Supplier acquisition cost ($) |
| `base_price` | Float | *Optional* | `base_price`, `price`, `retail_price`, `mrp`, `selling_price` | Standard customer retail price ($) |
| `avg_daily_sales`| Float | *Optional* | `avg_daily_sales`, `daily_sales`, `velocity`, `run_rate` | Baseline daily units velocity |

### Example Unified CSV Format:
```csv
SKU,Item Name,Category,Quantity,Use By Date,Price,Cost,Branch
SKU-101,Organic Hass Avocados,Produce,42,2026-10-12,2.49,1.20,Downtown Store
SKU-102,Artisan Sourdough Loaf,Bakery,18,2026-10-10,4.99,1.80,Downtown Store
SKU-103,Greek Whole Milk Yogurt,Dairy,65,2026-10-15,3.89,2.10,Westside Market
SKU-104,Wild Atlantic Salmon Fillet,Meat & Seafood,14,2026-10-11,12.99,7.50,Downtown Store
```

---

## 🖥️ Application Pages Overview

1. **📊 Dashboard**:
   - Executive hero banner (*"Smarter Grocery. Less Waste."*) with dual CTAs.
   - 4 primary overview cards (*Products Tracked*, *Low Stock Items*, *Expiring Soon*, *Potential Waste Risk*) with dynamic calculation and graceful empty states.
   - Interactive Plotly visualizations: *Category Inventory Distribution* and *Shelf-Life Expiry Distribution*.
   - 3-step *How It Works* workflow tiles and *Sustainability Impact* ESG disclosures.

2. **📤 Upload Data**:
   - Dual ingestion modes: Single Unified Spreadsheet (CSV/XLSX) with automatic alias matching, and Multi-File Modular Ingestion (Catalog, Sales, Batches).
   - Ambiguity detection and interactive manual mapping override dropdowns.
   - 1-Click calibrated 5-Store Supermarket Benchmark Network loader for instant evaluation.
   - Plain-language validation logs detailing accepted rows, rejected anomalies, and missing field integrity notes.

3. **📦 Inventory & Expiry**:
   - Summary cards with real data counts: *Total Products*, *Low Stock Items*, *Expiring Soon*, and *Expired Items*.
   - Configurable expiry warning threshold slider (days) and low-stock threshold slider (units).
   - Dynamic filters by Stock Health, Expiry Risk, Department, and Store Location.
   - Clean data table with color-coded status badges and CSV / formatted Excel downloaders.

4. **📈 Demand Forecast**:
   - 7-Day probabilistic forecast trajectory ($P_{10}$, $P_{50}$, $P_{90}$) rendered in Plotly.
   - 3-tier forecasting engine: Tier 1 Baseline Moving Average (<14 days), Tier 2 Day-of-Week Seasonality (14-30 days), and Tier 3 Scikit-Learn ML Regression (30+ days).
   - Scenarios and elasticity simulation toolbar ($\epsilon = -1.35$) with ambient temperature anomaly testing.
   - Honest evaluation metrics ($MAE$, $RMSE$, $R^2$) with train/test validation splits.

5. **🤖 AI Recommendations**:
   - Human-in-the-Loop (HITL) review workspace with color-coded cards for Urgent ($\le 24h$), High ($\le 48h$), Medium, and Low priorities.
   - Summary KPI counts for *Pending Review*, *Approved*, *Rejected*, and *Modified*.
   - Reviewer role selector (e.g., *"Store Manager"*), one-click approve, rejection with reason capture, and interactive modification drawer (adjust markdown %, reorder qty, transfer destination).
   - Multi-agent voting matrix and data sufficiency assumption transparency drawers.
   - Prototype governance disclaimer clearly displayed.

6. **📑 Reports**:
   - Executive Audit Suite: Inventory Health & Capital Value, Freshness & Expiry Risk, Historical Sales & Forecast Run-rate, Agent Deliberations Breakdown, and Manager Approval Audit.
   - Products Requiring Immediate Attention priority queue table.
   - Formula and assumption disclosures for all potential savings estimations.
   - Instant downloadable CSV reports for Inventory Health, Expiry Risk, and Governance Decisions.

---

## 🛠️ Local Installation & Testing

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Git

### 2. Clone Repository & Install Dependencies
```bash
git clone https://github.com/your-username/zero-waste-grocery.git
cd zero-waste-grocery
pip install -r requirements.txt
```

### 3. Run Automated Test Suite
```bash
python -m pytest tests/ -v
```
All **55 unit and integration tests** across 6 test modules should pass in under 3 seconds.

### 4. Launch Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deployment Guide: Streamlit Community Cloud

Zero-Waste Grocery is architected to be 100% cloud-ready with zero external API dependencies required for standard execution:

### Step 1: Push Repository to GitHub
1. Create a new public repository on GitHub (e.g. `zero-waste-grocery`).
2. Initialize and push your code:
   ```bash
   git init
   git add .
   git commit -m "feat: Zero-Waste Grocery production release"
   git branch -M main
   git remote add origin https://github.com/<your-username>/zero-waste-grocery.git
   git push -u origin main
   ```

### Step 2: Deploy on Streamlit Community Cloud
1. Navigate to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
2. Click **"New app"** (or **"Create app"**).
3. Select your repository: `<your-username>/zero-waste-grocery`.
4. Set **Branch**: `main`.
5. Set **Main file path**: `app.py`.
6. Click **"Deploy!"**.

### Step 3: (Optional) LLM Synthesis Secrets
The platform operates deterministically out of the box. If you wish to enable the optional natural language explainer:
1. In your Streamlit Cloud app settings, click **Settings** -> **Secrets**.
2. Add your key:
   ```toml
   GEMINI_API_KEY = "your-google-ai-studio-api-key"
   ```
3. Save changes.

---

## 🛡️ Security, Honesty & Governance Constraints

- **Zero Fabricated Metrics**: If price or cost columns are missing in user-uploaded data, financial totals and savings valuations are withheld. If expiry dates are missing, shelf-life is reported as *Unspecified* rather than assuming decay.
- **Zero Committed Secrets**: The repository contains **0** hardcoded API keys, passwords, or cloud credentials. All optional API keys are consumed via environment variables or Streamlit secrets.
- **Prototype Simulation Disclaimer**: Downstream dispatch to electronic shelf tags (POS), warehouse transfers (WMS), and purchase orders (ERP) are simulated within the local runtime. The system does not claim live integration with production enterprise ERP systems.
