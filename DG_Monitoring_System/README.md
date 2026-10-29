# AI-POWERED DIESEL GENERATOR USAGE MONITORING SYSTEM (GENIUS DG)

> **College Mini-Project**  
> **Domain:** Smart Energy Monitoring, Anomaly Detection & Environmental Compliance  
> **Backend & Cloud Architecture:** Python Flask REST API & Supabase PostgreSQL Cloud Database  
> **Author:** Full-Stack & AI Engineering Team  

---

## 1. Executive Summary

Diesel Generators (DGs) provide vital backup power for universities, hospitals, data centers, and industrial facilities during public grid power interruptions. However, unmonitored generator operations frequently suffer from:
1. **Unnoticed Mechanical Degradation & Fuel Leakage:** Clogged air/fuel filters, worn injectors, or fuel leaks that cause abnormal fuel consumption.
2. **Post-Mains Restoration Shutdown Delays:** Operators or misconfigured Automatic Mains Failure (AMF) panels running generators for 30–60 minutes after grid electricity has already returned, wasting expensive diesel.
3. **Severe Overloading or Wet-Stacking:** Operating beyond prime rating (>100%) causing thermal stress, or running at extreme underload (<25%) causing carbon buildup and wet-stacking.
4. **Carbon Footprint Compliance Gaps:** Inability to audit Scope 1 stationary combustion CO₂ emissions accurately.
5. **Data Quality & Sensor Anomalies:** Frozen sensors, invalid sequence timestamps, and missing fields compromising monitoring integrity.

This project delivers a **complete, enterprise-grade industrial monitoring platform** that integrates:
- **Clean Energy Dashboard:** Responsive, modern dark/light UI featuring industrial telemetry cards, real-time gauges, and interactive Chart.js visualizations.
- **Flask REST API:** Modular backend with strict physical boundary validation and clean JSON responses.
- **Supabase PostgreSQL Cloud Integration:** Resilient, secure cloud database persistence with Row Level Security (RLS) and transparent local CSV fallback.
- **Explainable AI Anomaly Detection:** Multivariate **Isolation Forest** machine learning algorithm scoring operations across runtime, fuel volume, electrical load, capacity, burn rate, and load factor, benchmarked against ISO 8528 load brackets.
- **Deterministic Shutdown Delay Intelligence:** Reconstructs 4-stage event timelines (`mains_lost` → `started` → `restored` → `stopped`), computes excess delays, and quantifies avoidable fuel and monetary loss.
- **Data Quality Monitor:** 14 automated non-destructive integrity checks, data health score rating (0–100%), and exportable CSV audit report.

---

## 2. Technology Stack

| Layer | Technologies Used | Description |
|---|---|---|
| **Frontend** | HTML5, CSS3 (Vanilla), JavaScript (ES6+) | Single-Page Application (SPA) architecture, responsive layout, custom modals, toast notifications. |
| **Data Visualization** | Chart.js 4.4 | 5 interactive charts: daily runtime, fuel distribution, cost trend, CO₂ trend, normal vs anomaly clusters. |
| **Backend Framework** | Python 3, Flask 3.1, Flask-CORS | REST API with CORS headers, comprehensive error handlers, and static asset serving. |
| **Cloud Database** | **Supabase PostgreSQL** | Cloud-native PostgreSQL with Row Level Security (RLS), performance indexes, and JSONB telemetry storage. |
| **Database Client** | Supabase Python SDK (`supabase>=2.33.0`) | Official client reading credentials from server-side environment variables (`python-dotenv`). |
| **Machine Learning / AI** | Scikit-Learn / Pure-Python Isolation Forest | Dual-engine multivariate Isolation Forest with decision scoring and explainable baseline comparisons. |
| **Storage & Data Access** | Hybrid Data Access Layer (`data_service.py` + `supabase_service.py`) | Dual-mode: queries Supabase when connected; gracefully falls back to local CSV storage when offline. |
| **Testing** | Pytest, Python unittest | 43 automated unit and integration tests covering calculations, boundary validation, Supabase services, and API routes. |

---

## 3. System Architecture & Data Flow

```text
  +-------------------------------------------------------------------------+
  |                        Enterprise Frontend (SPA)                       |
  |             HTML5 + Vanilla CSS + JavaScript ES6+ + Chart.js           |
  +------------------------------------+------------------------------------+
                                       | HTTP / REST (JSON)
                                       v
  +-------------------------------------------------------------------------+
  |                         Flask REST API (app.py)                         |
  |         /api/health | /api/dashboard/summary | /api/generators         |
  |         /api/records | /api/alerts | /api/analysis/* | /api/data-quality|
  +-------------------+--------------------------------+--------------------+
                      |                                |
                      v                                v
  +----------------------------------+   +----------------------------------+
  |      Physical Validation &       |   |       Explainable AI Engine      |
  |      Data Quality Service        |   |       Isolation Forest ML        |
  |      (14 Integrity Checks)       |   |   (ISO 8528 Load-Matched Groups) |
  +-------------------+--------------+   +-----------------+----------------+
                      |                                    |
                      +------------------+-----------------+
                                         |
                                         v
  +-------------------------------------------------------------------------+
  |               Hybrid Data Layer (data_service.py)                       |
  |  - Online Mode: SupabaseService queries PostgreSQL cloud tables         |
  |  - Offline / Dev Mode: Resilient fallback to data/generator_usage.csv   |
  +------------------------------------+------------------------------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v (Connected)                           v (Offline / Fallback)
  +----------------------------------+   +----------------------------------+
  |      Supabase PostgreSQL         |   |    Local Storage (data/)         |
  |  - generators                    |   |  - generator_usage.csv           |
  |  - sensor_readings               |   |  - settings.json                 |
  |  - ai_anomalies                  |   |  - maintenance.json              |
  |  - alerts                        |   |  - alert_status.json             |
  |  - maintenance_records           |   +----------------------------------+
  |  - camera_events                 |
  |  - system_settings               |
  |  [Row Level Security Enabled]    |
  +----------------------------------+
```

---

## 4. Supabase Cloud Database Setup

### Step 4.1: Create a Supabase Project
1. Visit **[https://supabase.com](https://supabase.com)** and sign in / sign up.
2. Click **New Project**.
3. Enter project details:
   - **Name:** `genius-dg-monitoring`
   - **Database Password:** (Choose a secure password and save it)
   - **Region:** Select the region closest to you (e.g., `ap-south-1` for Mumbai).
4. Click **Create new project** and wait 1–2 minutes for provisioning.

### Step 4.2: Retrieve API Credentials
1. In your Supabase dashboard, click the **Project Settings** (gear icon) in the bottom-left sidebar.
2. Navigate to **Configuration -> API**.
3. Under **Project URL**, copy the URL (e.g., `https://xyzcompany.supabase.co`).
4. Under **Project API keys**:
   - Find the **`service_role`** key (marked `secret`). Click to reveal and copy it.  
     *(Note: This key grants full server-side access to bypass RLS policies on the Flask backend. Never commit it or send it to the browser).*
   - Optionally copy the **`anon`** `public` key.

### Step 4.3: Configure Server Environment (`.env`)
1. In the `DG_Monitoring_System/backend/` folder, copy `.env.example` to `.env`:
   ```powershell
   cd backend
   copy .env.example .env
   ```
2. Open `backend/.env` in your editor and insert your actual credentials:
   ```ini
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-actual-service-role-key
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-actual-anon-key
   FLASK_ENV=development
   PORT=5000
   ```
3. Note: `.env` is listed in `.gitignore` to prevent leaking credentials.

### Step 4.4: Execute SQL Schema Migration
1. In your Supabase Dashboard, click **SQL Editor** in the left sidebar.
2. Click **New Query**.
3. Open the file `backend/migrations/001_create_supabase_tables.sql` in your project folder.
4. Copy its entire contents and paste it into the Supabase SQL Editor.
5. Click **Run** (green button).
6. Verify in the **Table Editor** that all 7 tables have been created:
   - `generators`
   - `sensor_readings`
   - `ai_anomalies`
   - `alerts`
   - `maintenance_records`
   - `camera_events`
   - `system_settings`

### Step 4.5: Migrate Existing Telemetry Data (CSV to Supabase)
Once the database schema is created and `.env` has credentials:
```powershell
# First test in dry-run mode (validates data without writing):
python scripts/migrate_csv_to_supabase.py --dry-run

# Execute the live cloud migration:
python scripts/migrate_csv_to_supabase.py
```
This utility:
- Upserts the 4 generator fleet profiles (`DG-101`, `DG-102`, `DG-103`, `DG-104`).
- Validates and batch-inserts all 229 operational telemetry records idempotently (`on_conflict="record_id"`).
- Syncs maintenance checklists and operational settings.
- Explicitly flags all demonstration rows as `simulated` / `True (Demonstration Data)`.

---

## 5. Local Installation & Startup (Windows PowerShell)

### Step 5.1: Install Dependencies
```powershell
cd "c:\Users\Iniyan\OneDrive\Desktop\hackthon 2026\DG_Monitoring_System\backend"

# Ensure all dependencies are installed:
pip install -r requirements.txt
```

### Step 5.2: Run Full Automated Test Suite
```powershell
python -m unittest discover -s tests -v
```
*(Confirms that all 43 unit and integration tests pass successfully).*

### Step 5.3: Start the Flask Backend Server
```powershell
python app.py
```
Terminal output:
```text
[2026-10-29 15:57:17] [INFO] [Supabase] Connected to Supabase PostgreSQL cloud database.
Starting GENIUS DG Monitoring System on http://localhost:5000
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

### Step 5.4: Open the Web Application
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 6. How to Verify Data in Supabase

1. **Verify via Supabase Table Editor:**
   - In Supabase Dashboard, click **Table Editor** in the left sidebar.
   - Click `sensor_readings`: You will see all 229 telemetry rows with `record_id`, `runtime_min`, `load_kw`, `fuel_used_litres`, `shutdown_delay_min`, and `data_source = 'simulated'`.
   - Click `generators`: You will see the 4 operational generators with their rated kVA and locations.
   - Click `system_settings`: You will see row `id = 1` with active diesel price and delay thresholds.

2. **Verify via SQL Editor Query:**
   ```sql
   -- Check record counts across tables
   SELECT 'generators' AS table_name, count(*) AS count FROM public.generators
   UNION ALL
   SELECT 'sensor_readings', count(*) FROM public.sensor_readings
   UNION ALL
   SELECT 'alerts', count(*) FROM public.alerts
   UNION ALL
   SELECT 'maintenance_records', count(*) FROM public.maintenance_records;
   ```

3. **Verify via Application Health API:**
   Query `http://127.0.0.1:5000/api/health`:
   ```json
   {
     "status": "healthy",
     "application_status": "healthy",
     "data_source": "supabase_postgresql",
     "database": {
       "connected": true,
       "status": "connected",
       "latency_ms": 142.5,
       "active_data_source": "supabase_postgresql"
     }
   }
   ```

---

## 7. REST API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Application status, Supabase DB connectivity, and dataset diagnostic report. |
| `GET` | `/api/dashboard/summary` | Fleet KPIs, daily trends, fuel distribution, and recent alert feed. |
| `GET` | `/api/generators` | Fleet generator listing enriched with telemetry. |
| `GET` | `/api/generators/<dg_id>` | Detailed history, capacity, and recent runs for an individual generator. |
| `GET` | `/api/records` | Searchable, paginated, and sortable generator telemetry records. |
| `POST` | `/api/records` | Adds a new generator run with physical boundary validation (persists to Supabase & CSV). |
| `GET` | `/api/alerts` | Combined AI and rule-based alerts with status filtering. |
| `POST` | `/api/alerts/<alert_id>/acknowledge` | Acknowledges an active alert (persists to Supabase). |
| `POST` | `/api/alerts/<alert_id>/resolve` | Resolves an active alert with resolution notes (persists to Supabase). |
| `PUT` | `/api/alerts/<alert_id>/status` | Updates alert status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`). |
| `GET` | `/api/analysis/anomalies` | Isolation Forest anomaly detection results and model metrics. |
| `GET` | `/api/analysis/anomalies/<record_id>`| Explainable AI breakdown with peer-bracket comparison and suggested inspection steps. |
| `POST` | `/api/analysis/anomalies/run` | Retrains Isolation Forest with custom contamination and saves anomalies to Supabase. |
| `GET` | `/api/analysis/shutdown-delay` | Post-mains restoration delay intelligence, avoidable fuel wastage, and event timelines. |
| `GET` | `/api/analysis/fuel-efficiency` | ISO 8528 load brackets (0-25%, 25-50%, 50-75%, 75-100%, >100%) and statistical outlier detection. |
| `GET` | `/api/data-quality/summary` | Telemetry health score %, valid count, warning count, and invalid count. |
| `GET` | `/api/data-quality/issues` | Filterable ledger of data quality issues without silently deleting records. |
| `GET` | `/api/data-quality/export` | Downloads the data quality audit report as CSV. |
| `GET` | `/api/maintenance` | Scheduled maintenance tasks and completed service logs. |
| `POST` | `/api/maintenance` | Records a completed maintenance log (persists to Supabase). |
| `GET` | `/api/camera/events` | Simulated optical/thermal camera telemetry feed. |
| `POST` | `/api/camera/simulate` | Simulates an optical anomaly detection event (smoke, thermal hotspot, puddle). |
| `GET` | `/api/settings` | Current operational parameters and validation limits. |
| `PUT` | `/api/settings` | Updates operational settings (persists to Supabase and settings.json). |
| `GET` | `/api/reports/export.csv` | Downloads filtered generator audit records as CSV. |

---

## 8. Database Security & Row Level Security (RLS)

1. **Server-Side Access Only:** The privileged `service_role` key is strictly kept in backend `.env` variables and never sent to the browser or client-side JavaScript.
2. **Row Level Security (RLS) Enabled:** RLS is enabled on all 7 PostgreSQL tables. Policies:
   - `service_role` has full `ALL` access for backend queries and insertions.
   - `anon` and `authenticated` roles have restricted `SELECT` (read-only) access.
3. **No Secret Leakage:** The `/api/health` and `/api/settings` endpoints sanitize all outputs. Passwords, secret keys, and JWT tokens are completely omitted from responses.
4. **Parameter Sanitization:** All queries use the Supabase SDK / PostgREST parameterized builders to prevent SQL injection.

---

## 9. Automated Test Suite Summary (43 Tests)

The automated test suite in `backend/tests/` covers:

- **`test_supabase.py` (15 Tests):**
  - Missing Supabase credentials handling and offline fallback.
  - Connection timeout / network failure recovery.
  - Health check endpoint distinguishing application health from database connectivity.
  - Mocked Supabase CRUD operations (`get_generators`, `insert_reading`, `update_alert_status`).
  - Generator listing and detail endpoints.
  - Filtered dashboard summary.
  - Alert acknowledgement and resolution transitions.
  - Negative fuel / invalid capacity boundary validation rejection.
  - CSV import denormalization and duplicate prevention.
  - AI anomaly analysis and scoring.
  - Fuel cost and CO₂ calculations.
  - Settings boundary validation (rejecting out-of-range contamination).
  - CSV report export headers and format.
  - Protection against leaking secret keys in responses.
  - Existing regression tests backward compatibility.

- **`test_phase1.py` (15 Tests):**
  - Explainable AI anomaly breakdown and peer baseline comparisons.
  - Mains restoration and shutdown delay calculations.
  - Inconsistent timestamps (`stop < mains_restored`).
  - Ongoing generator delay tracking.
  - ISO 8528 load brackets and fuel rate per hour ($L/h$).
  - 14 Data quality checks and health score %.

- **`test_calculations.py` & `test_api.py` (13 Tests):**
  - Stoichiometric CO₂ conversions.
  - Physical boundary validations.
  - Isolation Forest training.
  - Flask route contracts.

Run the entire suite with:
```powershell
python -m unittest discover -s tests -v
```
*(All 43 tests pass in < 0.8s).*

---

## 10. Demonstration Dataset & Academic Integrity

- **Synthetic Data Disclaimer:** In compliance with academic integrity guidelines, all generator operational records in `generator_usage.csv` and Supabase `sensor_readings` are realistic synthetic demonstration data generated via `backend/data/generate_dataset.py`.
- **Labels:** Every record in the database is explicitly tagged with `data_source = 'simulated'` and `is_synthetic = true`.
- **Diagnostic Clarification:** The application explicitly labels AI anomaly detections as statistical deviations warranting operator inspection, rather than definitive confirmation of mechanical failure or fuel theft.
