# FORESIGHT AI — Demand & Inventory Intelligence Platform

**Executive Supply Chain & Merchandise Intelligence System**  
Built strictly with Python 3 Standard Library, Vanilla HTML5/CSS3/JavaScript, and HTML5 Canvas.  
*Zero external packages, zero npm/Node.js dependencies, zero external CDNs, and strictly zero SVG.*

---

## 1. Project Overview

**FORESIGHT AI** is a production-grade, offline-capable enterprise analytics platform engineered to ingest real transactional sales records, physical inventory snapshots, SKU catalog attributes, and calendar events to deliver high-precision demand forecasting, inventory health tracking, stockout risk mitigation, replenishment scheduling, and ABC-XYZ product portfolio segmentation.

The platform provides an executive Single Page Application (SPA) dashboard powered by a lightweight, zero-dependency Python HTTP server running locally on `http://localhost:8000`.

---

## 2. Business Objective

Modern multi-category retailers and distributors face severe margin degradation from two opposing inventory risks:
1. **Stockouts & Under-stocking:** Lost sales revenue, broken service-level agreements, and churned customers due to replenishment orders placed later than supplier lead times.
2. **Overstocking & Inventory Holding Drag:** Working capital trapped in slow-moving merchandise, driving up warehouse holding costs, financing charges, and risk of deadstock obsolescence.

**FORESIGHT AI** bridges this gap by unifying transactional demand history with physical inventory snapshots, generating forward-looking daily projections, calculating statistical safety stock buffers, flagging imminent stockout risks, and prescribing automated reorder recommendations.

---

## 3. Dataset Description

The system runs exclusively on verified client business datasets located in `data/raw/`:

1. **`sku_master.csv`** (50 SKUs):
   - Comprehensive master catalog covering 5 distinct categories: *Furniture, Home Decor, Kitchen, Lighting, and Storage* (10 SKUs each).
   - Contains launch dates, unit cost prices, retail selling prices, and gross margins per unit.
2. **`sales_daily.csv`** (36,550 records):
   - Daily transactional records spanning 731 continuous calendar days (2024-01-01 to 2025-12-31, including the 2024 leap year).
   - 50 SKUs &times; 731 days = exactly 36,550 uninterrupted rows with verified units sold, gross revenue, selling price, and promotional flags.
3. **`inventory_snapshots.csv`** (4,800 records):
   - 24 monthly warehouse inventory snapshot intervals (first day of each month from 2024-01-01 to 2025-12-01).
   - Tracks physical on-hand current stock, incoming on-order units, supplier lead times (3 to 14 days), safety stock, and reorder points.
4. **`calendar.csv`** (731 records):
   - Complete 2-year calendar dimension providing year, month, quarter, week, day of week, weekend flags, seasonal designations, holiday markers, and promotional event names.

*Note on Missing Dimensions:* Dimensions not present in the source files (e.g. *Store, Warehouse, Region, Location, Supplier*) are never fabricated and are explicitly reported in the UI as `"Data not available in source dataset"`.

---

## 4. Architecture

The codebase adheres to a modular, decoupled architecture where data processing, forecasting algorithms, inventory math, and analytics engines exist in isolated modules:

```
FORESIGHT-AI/
├── app.py                     # High-performance Python http.server & REST API dispatcher
├── data/
│   ├── raw/                   # Real client datasets (source of truth)
│   │   ├── calendar.csv
│   │   ├── inventory_snapshots.csv
│   │   ├── sales_daily.csv
│   │   └── sku_master.csv
│   └── processed/             # Cleaned, standardized tabular exports & quality audit manifest
│       ├── processed_calendar.csv
│       ├── processed_inventory_snapshots.csv
│       ├── processed_sales_daily.csv
│       ├── processed_sku_master.csv
│       └── data_quality_report.json
├── models/                    # Model validation metadata & benchmark cache
│   └── forecast_benchmark.json
├── reports/                   # Audit summaries for executive review
│   └── data_quality_report.json
├── src/
│   ├── data_processing/
│   │   ├── loader.py          # Encoding-safe reader, type inference, date standardizer
│   │   ├── detector.py        # Automated business schema discovery & data profiler
│   │   └── processor.py       # Master ETL pipeline, data validation, and memory indexing
│   ├── forecasting/
│   │   ├── models.py          # Naive, Seasonal Naive, SMA (7/14/30), SES, Holt's Linear
│   │   ├── evaluation.py      # MAE, RMSE, MAPE, sMAPE, WAPE, temporal holdout split
│   │   └── engine.py          # Multi-horizon forecast projections & model tournament selector
│   ├── inventory/
│   │   ├── intelligence.py    # Velocity run-rate, Days of Inventory (DOI), health status
│   │   ├── stockout.py        # Burn-down runout projection, stockout calendar date estimator
│   │   └── reorder.py         # Statistical safety stock, ROP, ROQ, lead-time simulator
│   └── analytics/
│       ├── abc_xyz.py         # Pareto revenue ABC & demand volatility XYZ 9-box matrix
│       ├── insights.py        # Deterministic executive AI business reasoning engine
│       └── exporter.py        # RFC 4180 CSV export generator
├── templates/
│   └── index.html             # 8-tab SPA enterprise executive interface (zero SVG)
├── static/
│   ├── style.css              # Dark slate executive CSS design system
│   └── app.js                 # Pure Vanilla JS router, HTML5 Canvas chart renderer, state store
├── tests/                     # Comprehensive automated unit & integration test suite (35 tests)
│   ├── test_data_processing.py
│   ├── test_forecasting.py
│   ├── test_inventory.py
│   ├── test_analytics.py
│   ├── test_edge_cases.py
│   └── test_api.py
└── README.md                  # Comprehensive client documentation & data dictionary
```

---

## 5. Data Processing Pipeline

The ETL pipeline (`src/data_processing/`) executes a 16-step robust validation sequence:
1. **Encoding & Ingestion:** Safe CSV streaming supporting UTF-8, UTF-8-BOM, and Latin-1 with automatic dialect and delimiter sniffing (`,`, `;`, `\t`).
2. **Header Detection & Trimming:** Sanitizes and strips whitespace from source headers.
3. **Data Type Inference:** Identifies scalar types (integer, float, date, boolean, string, null).
4. **Date Standardization:** Standardizes multiple calendar date notations (`YYYY-MM-DD`, `DD-MM-YYYY`, `MM/DD/YYYY`) into strict ISO `YYYY-MM-DD`.
5. **Numeric Field Conversion:** Safely casts units, revenues, and prices with zero-fill fallbacks.
6. **Categorical Entity Mapping:** Identifies product hierarchies (Category, Subcategory).
7. **SKU Catalog Keying:** Validates 1-to-1 matching across SKU Master, Daily Sales, and Inventory Snapshots.
8. **Demand Normalization:** Maps units sold and gross transactional revenue.
9. **Inventory Snapshot Aggregation:** Extracts warehouse balance, on-order stock, and supplier lead times.
10. **Null & Missing Value Handling:** Verifies zero null values across all 36,550 sales records.
11. **Row-Level Duplicate Verification:** Validates row uniqueness (0 duplicates detected).
12. **Date Continuity Verification:** Confirms 731 contiguous calendar days without gaps.
13. **Anomaly & Outlier Profiling:** Scans for negative quantities and prices (0 negative records found).
14. **Missing Dimension Identification:** Flags unmapped business dimensions (Location, Supplier) as unobserved in raw datasets.
15. **Source Data Preservation:** Raw files in `data/raw/` are untouched and treated as read-only.
16. **Processed Data Persistence:** Normalized tables and full audit manifest are saved in `data/processed/`.

---

## 6. Forecasting Methodology

Demand forecasting operates on actual historical time-series velocity using time-series-aware validation without lookahead bias:

### Algorithmic Models (Python Standard Library)
1. **Persistence Naive:** \(\hat{Y}_{t+h} = Y_t\) (Projects most recent observed daily actual).
2. **Seasonal Naive (7-Day):** \(\hat{Y}_{t+h} = Y_{t+h-7}\) (Repeats weekly day-of-week seasonality).
3. **Simple Moving Average (SMA-7, SMA-14, SMA-30):** \(\hat{Y}_{t+h} = \frac{1}{k} \sum_{i=0}^{k-1} Y_{t-i}\) (Rolling velocity filters).
4. **Single Exponential Smoothing (SES):** \(S_t = \alpha Y_t + (1-\alpha) S_{t-1}\) (Optimized \(\alpha \in [0.1, 0.8]\) minimizing squared error).
5. **Holt's Linear Trend:** Captures underlying level \(L_t\) and linear trajectory \(T_t\) with trend damping.

### Validation Strategy
- **Temporal Holdout Split:** Chronological split reserving the first 671 days (2024-01-01 to 2025-11-01) for training, and the final 60 days (2025-11-02 to 2025-12-31) for out-of-sample validation. No random splitting.
- **Evaluation Metrics:**
  - **WAPE (Weighted Absolute Percentage Error):** \(\frac{\sum |Y - \hat{Y}|}{\sum Y} \times 100\) (Primary ranking criterion; resilient against zero-demand days).
  - **MAE (Mean Absolute Error):** \(\frac{1}{n} \sum |Y - \hat{Y}|\) (Error magnitude in physical units).
  - **RMSE (Root Mean Squared Error):** \(\sqrt{\frac{1}{n} \sum (Y - \hat{Y})^2}\) (Penalizes extreme outliers).
- **Model Tournament Selection:** Automatically selects the winning algorithm per SKU based on validation WAPE.
- **Multi-Horizon Projections:** Generates 7-day, 14-day, and 30-day forward forecasts with 95% confidence intervals (\(\hat{Y} \pm 1.96 \times \sigma_e\)).

---

## 7. Inventory Intelligence Methodology

Extracts stock health and velocity from the latest snapshot (2025-12-01) and historical sales:
- **Average Daily Demand (\(ADD\)):** \(\frac{\text{Total Units Sold}}{\text{Total Calendar Days}}\).
- **Days of Inventory Remaining (\(DOI\)):** \(\frac{\text{Current Stock Units}}{ADD}\).
- **Stock Status Classification:**
  - **Out of Stock:** \(\text{Current Stock} = 0\).
  - **Critical:** \(DOI \le 7\text{ days}\) (Immediate risk of stockout).
  - **Low Stock:** \(7 < DOI \le 15\text{ days}\) (Within typical supplier replenishment window).
  - **Healthy:** \(15 < DOI \le 45\text{ days}\) (Optimal operating coverage).
  - **Overstock:** \(DOI > 45\text{ days}\) (Excess working capital tie-up).

---

## 8. Stockout Risk Methodology

Quantifies replenishment exposure by comparing days of supply against supplier lead times:
- **Days Until Stockout:** \(DOI = \frac{\text{Current Stock}}{ADD}\).
- **Estimated Stockout Date:** \(\text{Snapshot Date} + \text{round}(DOI)\text{ days}\).
- **Risk Level Hierarchy:**
  - **High Risk:** \(DOI \le \text{Lead Time Days}\) or \(DOI \le 7\text{ days}\). (Replenishment cannot arrive before run-out if ordered today).
  - **Medium Risk:** \(\text{Lead Time Days} < DOI \le \text{Lead Time Days} + 7\text{ days}\). (Replenishment window rapidly closing).
  - **Low Risk:** \(DOI > \text{Lead Time Days} + 7\text{ days}\). (Adequate inventory buffer).

---

## 9. Reorder Methodology

Automated purchase order calculation protecting cycle service levels:
- **Lead-Time Demand (\(LTD\)):** \(ADD \times \text{Lead Time Days}\).
- **Statistical Safety Stock (\(SS\)):**
  \[
  SS = Z \times \sigma_{\text{daily}} \times \sqrt{\text{Lead Time Days}}
  \]
  where \(Z = 1.65\) (95% cycle service level), \(\sigma_{\text{daily}}\) is standard deviation of daily demand.
- **Reorder Point (\(ROP\)):** \(LTD + SS\).
- **Inventory Position (\(IP\)):** \(\text{Current Stock} + \text{On Order}\).
- **Reorder Trigger:** Triggers purchase order when \(IP \le ROP\).
- **Recommended Order Quantity (\(ROQ\)):** \(\max(0, \lceil ROP - IP + LTD \rceil)\).
- **Suggested Reorder Date:** `"Immediate (Action Required)"` if \(IP \le ROP\); otherwise projected forward based on daily burn rate.
- **Interactive Lead Time Simulator:** Allows simulating uniform supplier lead times (5, 7, 10, 14, 21 days) without corrupting source data.

---

## 10. ABC/XYZ Portfolio Methodology

Combines commercial revenue Pareto importance with demand variability:

### ABC Analysis (Revenue Contribution)
- SKUs sorted by total gross revenue descending:
  - **Class A:** Top 70% of cumulative revenue (High-value commercial drivers).
  - **Class B:** Next 20% of cumulative revenue (70% to 90% cumulative).
  - **Class C:** Remaining 10% of revenue (90% to 100% cumulative).

### XYZ Analysis (Demand Volatility)
- Evaluates demand predictability via Coefficient of Variation:
  \[
  CV = \frac{\sigma_{\text{demand}}}{\mu_{\text{demand}}}
  \]
  - **Class X (Stable):** \(CV \le 0.50\) (Constant demand, highly predictable).
  - **Class Y (Moderate):** \(0.50 < CV \le 0.80\) (Moderate seasonal/promotional variability).
  - **Class Z (Volatile):** \(CV > 0.80\) (Erratic, episodic demand).

### 9-Box Decision Grid
- Strategic inventory policies mapped to each of the 9 quadrants (e.g. **AX** = Automated Just-in-Time replenishment; **AZ** = Managerial oversight and flexible contracts; **CX** = Bulk batch purchasing; **CZ** = On-demand or zero-stocking).

---

## 11. KPI Definitions

| KPI Metric | Formulation | Business Meaning |
| :--- | :--- | :--- |
| **Total Products / SKUs** | \(\text{Count}(\text{Unique SKUs})\) | Active commercial merchandise count (50 SKUs) |
| **Total Units Sold** | \(\sum \text{Units\_Sold}\) | Physical units purchased across entire 2-year window (377,294 units) |
| **Total Sales Revenue** | \(\sum \text{Revenue}\) | Cumulative gross transactional sales volume ($142.7M) |
| **Current Inventory Valuation** | \(\sum (\text{Current\_Stock} \times \text{Cost\_Price})\) | Total liquid capital tied in warehouse physical stock ($42.2M) |
| **Average Daily Demand** | \(\frac{\text{Total Units}}{\text{Total Days}}\) | System-wide sales velocity (516.13 units/day) |
| **Days of Inventory (DOI)** | \(\frac{\text{Current Stock}}{ADD}\) | Number of days on-hand stock can satisfy demand without replenishment |
| **Safety Stock Buffer** | \(1.65 \times \sigma_d \times \sqrt{L}\) | Statistical buffer shielding against stockout during replenishment lead time |
| **Reorder Point (ROP)** | \((ADD \times L) + SS\) | Stock balance threshold that triggers a purchase order |
| **WAPE Accuracy** | \(\frac{\sum \|Actual - Forecast\|}{\sum Actual} \times 100\) | Normalized forecast error percentage across products |

---

## 12. Assumptions

1. **Continuous Calendar:** Historical sales cover 731 contiguous calendar days (2024-01-01 to 2025-12-31).
2. **Snapshot Timing:** Monthly inventory snapshots reflect physical stock at the start of each month (most recent: 2025-12-01).
3. **Normal Demand Distribution for Safety Stock:** Safety stock formula assumes approximately normally distributed daily sales velocity during supplier lead times.
4. **Service Level Target:** Default safety stock calculation targets a 95% cycle service level (\(Z = 1.65\)).
5. **No Lookahead Bias:** Forecasting evaluation uses strictly historical holdout validation (first 671 days train, final 60 days validation).

---

## 13. Limitations

1. **Missing Location/Warehouse Dimension:** The source datasets do not contain multi-echelon warehouse, depot, or retail store identifiers. The system explicitly marks location as `"Data not available in source dataset"`.
2. **Missing Supplier Entity:** Supplier vendor names are not present in raw tables. Lead times are sourced directly from inventory snapshot records.
3. **Batch Snapshot Interval:** Inventory balances are snapshot on a monthly cadence rather than real-time perpetual inventory streaming.
4. **Promotion Interaction:** While promotion flags (0 or 1) exist in sales daily, complex causal promotional uplift modeling is bounded by standard library constraints.

---

## 14. How to Run

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.14).
- Standard operating system browser (Chrome, Edge, Firefox, Safari).
- **No Node.js, no npm, no pip packages, and no internet access required.**

### Starting the Server
Open a terminal in the project root directory and execute:

```powershell
python app.py
```

Console output will display:
```
==================================================================
  FORESIGHT AI - Demand & Inventory Intelligence Platform
  Server active at: http://localhost:8000
  Runtime: Python 3 Standard Library (Offline, Zero-dependency, No SVG)
==================================================================
```

Open your browser to:
```
http://localhost:8000
```

### Running Automated Tests
Run the complete 35-test automated test suite using Python's built-in `unittest` runner:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 15. How to Use the Dashboard

The platform features an 8-tab executive navigation sidebar:
1. **Executive Overview:** High-level KPI cards, deterministic AI insights, HTML5 Canvas 24-month demand trend chart, category revenue distribution, and top 10 commercial drivers.
2. **Demand Forecast:** SKU and Category selectors, 7/14/30-day horizon toggles, dual-series Canvas chart (historical actuals + projected forecast with 95% confidence bounds), and day-by-day tabular forecast points.
3. **Inventory Intelligence:** Search and status filtering (Healthy, Low Stock, Critical, Overstock, Out of Stock), physical inventory matrix, DOI run-rate, and CSV export.
4. **Stockout Risk:** Urgency badges (High, Medium, Low risk), estimated stockout dates, operational run-out explanations, and CSV export.
5. **Reorder Recommendations:** Replenishment purchase orders, interactive Lead Time Simulation dropdown, calculated safety stocks, ROP, order quantities, and CSV export.
6. **Product Analytics:** Interactive 9-Box ABC-XYZ segmentation grid (click any box to filter the table!), searchable product catalog, and SKU deep-dive inspection drawer.
7. **Data Quality:** Raw datasets profiling audit (row counts, nulls, duplicates, date spans) and complete Field Mapping Dictionary.
8. **Model Performance:** Algorithm leaderboard comparing candidate models on out-of-sample validation holdout (WAPE, MAE, RMSE) and metric formulations.

---

## 16. Data Dictionary (Verified Client Source Data)

### 1. `sales_daily.csv` (36,550 Rows &times; 6 Columns)
| Source Column | Data Type | Business Meaning | Missing Values | Example Format |
| :--- | :--- | :--- | :--- | :--- |
| `Date` | Date (`YYYY-MM-DD`) | Daily transactional date | 0 (0.0%) | `2024-01-01` |
| `SKU` | String (`SKU001-SKU050`)| Unique stock keeping unit code | 0 (0.0%) | `SKU001` |
| `Units_Sold` | Integer | Daily physical quantity sold | 0 (0.0%) | `5` |
| `Revenue` | Float | Gross daily sales currency amount | 0 (0.0%) | `18320.25` |
| `Price` | Float | Unit selling price on transaction date| 0 (0.0%) | `3664.05` |
| `Promotion` | Integer (`0` or `1`) | Binary flag indicating promotional event| 0 (0.0%) | `0` |

### 2. `sku_master.csv` (50 Rows &times; 8 Columns)
| Source Column | Data Type | Business Meaning | Missing Values | Example Format |
| :--- | :--- | :--- | :--- | :--- |
| `SKU` | String (`SKU001-SKU050`)| Unique stock keeping unit code | 0 (0.0%) | `SKU001` |
| `Product_Name` | String | Commercial catalog merchandise name | 0 (0.0%) | `Product 001` |
| `Category` | String | Primary retail department (5 distinct) | 0 (0.0%) | `Furniture` |
| `Subcategory` | String | Granular merchandise grouping | 0 (0.0%) | `Chair` |
| `Launch_Date` | Date (`YYYY-MM-DD`) | Initial market launch date | 0 (0.0%) | `2022-04-09` |
| `Cost_Price` | Float | Procurement unit cost | 0 (0.0%) | `1758.45` |
| `Selling_Price`| Float | Standard retail selling price | 0 (0.0%) | `3664.05` |
| `Gross_Margin_Per_Unit` | Float | Unit commercial margin (Selling - Cost)| 0 (0.0%) | `1905.60` |

### 3. `inventory_snapshots.csv` (4,800 Rows &times; 8 Columns)
| Source Column | Data Type | Business Meaning | Missing Values | Example Format |
| :--- | :--- | :--- | :--- | :--- |
| `Snapshot_Date`| Date (`YYYY-MM-DD`) | Monthly warehouse balance audit date | 0 (0.0%) | `2024-01-01` |
| `SKU` | String | Unique stock keeping unit code | 0 (0.0%) | `SKU001` |
| `Current_Stock`| Integer | Units physically available in warehouse| 0 (0.0%) | `16` |
| `On_Order` | Integer | Units pending delivery from supplier | 0 (0.0%) | `23` |
| `Lead_Time_Days`| Integer | Supplier order-to-delivery lead time | 0 (0.0%) | `11` |
| `Safety_Stock` | Integer | Reported baseline buffer stock | 0 (0.0%) | `7` |
| `Reorder_Point`| Integer | Reported inventory replenishment trigger| 0 (0.0%) | `18` |
| `Inventory_Value`| Float | Valuation of on-hand physical stock | 0 (0.0%) | `58420.96` |

### 4. `calendar.csv` (731 Rows &times; 11 Columns)
| Source Column | Data Type | Business Meaning | Missing Values | Example Format |
| :--- | :--- | :--- | :--- | :--- |
| `date` | Date (`YYYY-MM-DD`) | Calendar date identifier | 0 (0.0%) | `2024-01-01` |
| `year` | Integer | Calendar year | 0 (0.0%) | `2024` |
| `month` | Integer | Calendar month index (1 to 12) | 0 (0.0%) | `1` |
| `quarter` | String | Calendar quarter (`Q1` to `Q4`) | 0 (0.0%) | `Q1` |
| `week` | Integer | Week number of the year (1 to 53) | 0 (0.0%) | `1` |
| `day_of_week` | String | Name of the weekday | 0 (0.0%) | `Monday` |
| `is_weekend` | Integer (`0` or `1`) | Flag for Saturday / Sunday | 0 (0.0%) | `0` |
| `season` | String | Climatological season | 0 (0.0%) | `Winter` |
| `holiday` | String | Name of designated holiday or `None` | 0 (0.0%) | `None` |
| `is_holiday` | Integer (`0` or `1`) | Flag indicating official holiday | 0 (0.0%) | `0` |
| `promotion_event`| String | Commercial campaign tag or `None` | 0 (0.0%) | `None` |

---

## 17. Future Enhancements

1. **Perpetual Inventory Streaming:** Ingestion of real-time point-of-sale (POS) message queues to update stock balances continuously between monthly audits.
2. **Multi-Echelon Network Modeling:** Extending inventory intelligence to multi-warehouse topologies when store and distribution center dimensions become available.
3. **Supplier Performance Tracking:** Measuring supplier OTIF (On-Time In-Full) delivery variance to adjust dynamic safety stock formulas.
4. **Price Elasticity Simulation:** Simulating promotional discounting impact on demand velocity and clearance of overstocked items.
