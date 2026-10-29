"""
GENIUS DG - Intelligent Diesel Generator Usage Monitoring System
Author: Senior Full-Stack, AI & UI/UX Engineer
Enterprise Industrial Control API
"""

import os
import json
import datetime
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS

from services.data_service import DataService
from services.fuel_service import FuelService
from services.emission_service import EmissionService
from services.anomaly_service import AnomalyService
from services.shutdown_service import ShutdownService
from services.efficiency_service import EfficiencyService

# Initialize Flask app
frontend_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app = Flask(__name__, static_folder=frontend_folder, static_url_path="")

# Configure CORS for enterprise frontend
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration state (Persisted in settings.json)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")
ALERT_STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "alert_status.json")
MAINTENANCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "maintenance.json")

DEFAULT_SETTINGS = {
    "diesel_price_per_litre": 94.50,
    "currency_symbol": "₹",
    "co2_emission_factor": 2.68,
    "shutdown_delay_threshold_min": 10.0,
    "ai_contamination_rate": 0.08,
    "max_overload_tolerance_pct": 115.0,
    "frozen_sensor_threshold": 4,
    "last_updated": datetime.datetime.now().isoformat()
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)

def save_settings(settings_dict):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save settings to disk: {e}")

# Alert status persistence
def load_alert_statuses():
    if os.path.exists(ALERT_STATUS_FILE):
        try:
            with open(ALERT_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_alert_statuses(statuses):
    try:
        os.makedirs(os.path.dirname(ALERT_STATUS_FILE), exist_ok=True)
        with open(ALERT_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(statuses, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save alert statuses: {e}")

alert_statuses = load_alert_statuses()

# Maintenance persistence
DEFAULT_MAINTENANCE = [
    {
        "id": "MNT-101-01",
        "dg_id": "DG-101",
        "service_type": "500-Hour Lube Oil & Filter Service",
        "interval_hours": 500,
        "last_serviced_hours": 350.0,
        "current_hours": 420.5,
        "hours_remaining": 79.5,
        "due_date": "2026-11-15",
        "status": "DUE_SOON",
        "assigned_technician": "P. Sharma (Senior Mech)",
        "checklist": ["Replace engine oil 15W-40", "Replace primary fuel filter", "Inspect drive belt tension"]
    },
    {
        "id": "MNT-102-01",
        "dg_id": "DG-102",
        "service_type": "250-Hour Air Induction & Battery Inspection",
        "interval_hours": 250,
        "last_serviced_hours": 210.0,
        "current_hours": 235.0,
        "hours_remaining": 15.0,
        "due_date": "2026-11-05",
        "status": "DUE_SOON",
        "assigned_technician": "K. Raman (Electrical Lead)",
        "checklist": ["Clean air pre-cleaner", "Test starting battery specific gravity", "Check alternator terminals"]
    },
    {
        "id": "MNT-103-01",
        "dg_id": "DG-103",
        "service_type": "Annual Cooling System Flush & Radiator Descaling",
        "interval_hours": 1000,
        "last_serviced_hours": 650.0,
        "current_hours": 710.0,
        "hours_remaining": 290.0,
        "due_date": "2026-12-20",
        "status": "NORMAL",
        "assigned_technician": "Fleet OEM Contractor",
        "checklist": ["Coolant pH analysis", "Hose clamp inspection", "Radiator fin pressure wash"]
    },
    {
        "id": "MNT-104-01",
        "dg_id": "DG-104",
        "service_type": "Valve Clearance Lash & Fuel Injector Calibration",
        "interval_hours": 800,
        "last_serviced_hours": 120.0,
        "current_hours": 165.0,
        "hours_remaining": 635.0,
        "due_date": "2027-02-10",
        "status": "NORMAL",
        "assigned_technician": "A. Verma (Service Tech)",
        "checklist": ["Check rocker arm gap", "Test nozzle opening pressure", "Inspect fuel leak-off pipes"]
    }
]

def load_maintenance():
    if os.path.exists(MAINTENANCE_FILE):
        try:
            with open(MAINTENANCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return list(DEFAULT_MAINTENANCE)

def save_maintenance(records):
    try:
        os.makedirs(os.path.dirname(MAINTENANCE_FILE), exist_ok=True)
        with open(MAINTENANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save maintenance: {e}")

# Simulated Camera Telemetry
CAMERA_EVENTS = [
    {
        "id": "CAM-EVT-01",
        "camera_id": "CAM-BAY-1",
        "dg_id": "DG-101",
        "bay_name": "Generator Bay 1 (Academic Complex)",
        "timestamp": "2026-10-29 11:15:00",
        "event_type": "THERMAL_HOTSPOT_NORMAL",
        "severity": "NORMAL",
        "reading": "74.2 °C (Exhaust Manifold Normal)",
        "status": "Normal Operating Range",
        "is_simulated": True,
        "label": "Demo Simulated Optical/Thermal Feed"
    },
    {
        "id": "CAM-EVT-02",
        "camera_id": "CAM-BAY-2",
        "dg_id": "DG-102",
        "bay_name": "Generator Bay 2 (Library)",
        "timestamp": "2026-10-29 10:40:00",
        "event_type": "EXHAUST_OPACITY",
        "severity": "NORMAL",
        "reading": "Ringelmann 0.2 (Clear Stack)",
        "status": "Clean Combustion",
        "is_simulated": True,
        "label": "Demo Simulated Optical/Thermal Feed"
    },
    {
        "id": "CAM-EVT-03",
        "camera_id": "CAM-BAY-3",
        "dg_id": "DG-103",
        "bay_name": "Generator Bay 3 (Data Center)",
        "timestamp": "2026-10-29 09:20:00",
        "event_type": "FUEL_CAP_MONITOR",
        "severity": "NORMAL",
        "reading": "Sensor Locked / Tamper Seal Intact",
        "status": "Secured",
        "is_simulated": True,
        "label": "Demo Simulated Optical/Thermal Feed"
    },
    {
        "id": "CAM-EVT-04",
        "camera_id": "CAM-BAY-4",
        "dg_id": "DG-104",
        "bay_name": "Generator Bay 4 (Admin)",
        "timestamp": "2026-10-29 08:05:00",
        "event_type": "PERIMETER_CHECK",
        "severity": "NORMAL",
        "reading": "Restricted Zone Clear",
        "status": "No Obstruction",
        "is_simulated": True,
        "label": "Demo Simulated Optical/Thermal Feed"
    }
]

# Load active settings
current_settings = load_settings()

# Initialize Services
data_service = DataService()
fuel_service = FuelService(
    default_diesel_price_per_litre=current_settings["diesel_price_per_litre"],
    currency_symbol=current_settings["currency_symbol"]
)
emission_service = EmissionService(
    default_emission_factor=current_settings["co2_emission_factor"]
)
anomaly_service = AnomalyService(
    contamination=current_settings["ai_contamination_rate"],
    shutdown_delay_threshold_min=current_settings["shutdown_delay_threshold_min"],
    diesel_price=current_settings["diesel_price_per_litre"]
)
shutdown_service = ShutdownService(
    threshold_minutes=current_settings["shutdown_delay_threshold_min"],
    diesel_price=current_settings["diesel_price_per_litre"]
)
efficiency_service = EfficiencyService(
    diesel_price=current_settings["diesel_price_per_litre"],
    currency_symbol=current_settings["currency_symbol"]
)

# Initial AI model training on startup
all_recs = data_service.get_all_records_filtered()
if all_recs:
    anomaly_service.train(all_recs)

def get_query_filters():
    dg_id = request.args.get("dg_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    return dg_id, start_date, end_date

def enrich_alerts_with_status(alerts):
    enriched = []
    for a in alerts:
        aid = a["alert_id"]
        status_info = alert_statuses.get(aid, {"status": "OPEN", "updated_at": None, "notes": None})
        a_copy = dict(a)
        a_copy["status"] = status_info["status"]
        a_copy["updated_at"] = status_info.get("updated_at")
        a_copy["resolution_note"] = status_info.get("notes")
        enriched.append(a_copy)
    return enriched

# --- FRONTEND ROUTING ---
@app.route("/")
def serve_index():
    return send_from_directory(frontend_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(frontend_folder, path)):
        return send_from_directory(frontend_folder, path)
    return send_from_directory(frontend_folder, "index.html")

# --- REST API ENDPOINTS ---

@app.route("/api/health", methods=["GET"])
def health():
    """System health check and diagnostic status."""
    report = data_service.get_validation_report()
    return jsonify({
        "status": "healthy",
        "system": "GENIUS DG - Intelligent Generator Monitoring",
        "version": "2.0.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "dataset_loaded": True if report["valid_records"] > 0 else False,
        "dataset_stats": report,
        "ai_model_trained": anomaly_service._is_trained,
        "active_configuration": current_settings
    }), 200

@app.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    """
    Returns aggregated KPI cards, trend charts, and recent alerts.
    Dynamically responds to dg_id and date range filters.
    """
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)

    # Compute KPI totals
    total_runtime_min = sum(r["runtime_min"] for r in records)
    total_runtime_hours = round(total_runtime_min / 60.0, 1)
    total_fuel_litres = round(sum(r["fuel_used_litres"] for r in records), 2)
    estimated_cost = round(total_fuel_litres * fuel_service.diesel_price_per_litre, 2)
    estimated_co2_kg = round(total_fuel_litres * emission_service.emission_factor, 2)

    # Unique generators in filtered records
    unique_generators = sorted(list(set(r["dg_id"] for r in records)))
    total_generators_count = len(unique_generators) if dg_id != "ALL" and dg_id else len(data_service.get_generators())

    # Running generators count (DG-101 and DG-103 actively on load)
    running_generators_count = 2 if (not dg_id or dg_id in ["ALL", "DG-101", "DG-103"]) else (1 if dg_id in ["DG-101", "DG-103"] else 0)

    # Anomaly and delay calculations
    anomaly_result = anomaly_service.detect_anomalies(records)
    anomalies_count = anomaly_result["summary"]["anomalies"]
    delays = anomaly_service.check_shutdown_delays(records)
    shutdown_delays_count = len(delays)

    # Daily runtime chart
    daily_chart_map = {}
    for r in records:
        d = r["date"]
        if d not in daily_chart_map:
            daily_chart_map[d] = {"runtime_hours": 0.0, "fuel_litres": 0.0, "runs": 0}
        daily_chart_map[d]["runtime_hours"] += (r["runtime_min"] / 60.0)
        daily_chart_map[d]["fuel_litres"] += r["fuel_used_litres"]
        daily_chart_map[d]["runs"] += 1

    daily_runtime_trend = []
    for d in sorted(daily_chart_map.keys()):
        daily_runtime_trend.append({
            "date": d,
            "runtime_hours": round(daily_chart_map[d]["runtime_hours"], 1),
            "fuel_litres": round(daily_chart_map[d]["fuel_litres"], 1),
            "runs_count": daily_chart_map[d]["runs"]
        })

    # Diesel consumption and emissions
    fuel_analysis = fuel_service.analyze_fuel(records)
    emissions_analysis = emission_service.analyze_emissions(records)

    normal_runs = max(0, len(records) - anomalies_count)

    # Recent alerts enriched with acknowledge/resolve state
    unified_alerts = enrich_alerts_with_status(anomaly_service.get_unified_alerts(records))
    active_alerts_count = len([a for a in unified_alerts if a.get("status") != "RESOLVED"])

    return jsonify({
        "status": "success",
        "filters_applied": {
            "dg_id": dg_id or "ALL",
            "start_date": start_date,
            "end_date": end_date,
            "total_records_matched": len(records)
        },
        "kpis": {
            "total_generators": total_generators_count,
            "running_generators": running_generators_count,
            "total_runtime_hours": total_runtime_hours,
            "total_diesel_litres": total_fuel_litres,
            "estimated_diesel_cost": estimated_cost,
            "estimated_co2_kg": estimated_co2_kg,
            "estimated_co2_tonnes": round(estimated_co2_kg / 1000.0, 3),
            "anomalies_detected_count": anomalies_count,
            "shutdown_delays_count": shutdown_delays_count,
            "active_alerts_count": active_alerts_count,
            "currency": fuel_service.currency_symbol,
            "diesel_price_per_litre": fuel_service.diesel_price_per_litre,
            "co2_emission_factor": emission_service.emission_factor
        },
        "charts": {
            "daily_runtime": daily_runtime_trend,
            "diesel_by_generator": fuel_analysis["by_generator"],
            "fuel_cost_trend": fuel_analysis["daily_trend"],
            "co2_emission_trend": emissions_analysis["daily_trend"],
            "normal_vs_anomalies": {
                "normal_count": normal_runs,
                "anomalies_count": anomalies_count,
                "shutdown_delays_count": shutdown_delays_count
            }
        },
        "recent_alerts": unified_alerts[:12]
    }), 200

@app.route("/api/generators", methods=["GET"])
def get_generators():
    """Returns fleet-wide generator statistics enriched with live telemetry."""
    gens = data_service.get_generators()

    # Enrich with live physical sensor simulations
    for g in gens:
        gid = g["dg_id"]
        if gid == "DG-101":
            g["running_status"] = "Running"
            g["load_percentage"] = 72.5
            g["fuel_level_percent"] = 84
            g["temperature_celsius"] = 82.4
            g["vibration_mms"] = 2.1
            g["location"] = "Main Academic Complex"
        elif gid == "DG-102":
            g["running_status"] = "Standby"
            g["load_percentage"] = 0.0
            g["fuel_level_percent"] = 92
            g["temperature_celsius"] = 28.5
            g["vibration_mms"] = 0.0
            g["location"] = "Central Library & Seminar Halls"
        elif gid == "DG-103":
            g["running_status"] = "Running"
            g["load_percentage"] = 68.0
            g["fuel_level_percent"] = 65
            g["temperature_celsius"] = 79.1
            g["vibration_mms"] = 2.4
            g["location"] = "Data Center & Engineering Labs"
        else:
            g["running_status"] = "Standby"
            g["load_percentage"] = 0.0
            g["fuel_level_percent"] = 77
            g["temperature_celsius"] = 26.8
            g["vibration_mms"] = 0.0
            g["location"] = "Administrative & Health Clinic"

    return jsonify({
        "status": "success",
        "total_generators": len(gens),
        "generators": gens
    }), 200

@app.route("/api/generators/<dg_id>", methods=["GET"])
def get_generator_detail(dg_id):
    """Returns detailed history and profile for an individual generator."""
    detail = data_service.get_generator_detail(dg_id)
    if not detail:
        return jsonify({
            "status": "error",
            "message": f"Generator with ID '{dg_id}' was not found in database."
        }), 404

    records = data_service.get_all_records_filtered(dg_id=dg_id)
    anomaly_res = anomaly_service.detect_anomalies(records)
    delays = anomaly_service.check_shutdown_delays(records)

    detail["anomalies_count"] = anomaly_res["summary"]["anomalies"]
    detail["shutdown_delays_count"] = len(delays)
    detail["alerts"] = enrich_alerts_with_status(anomaly_service.get_unified_alerts(records))[:10]

    # Sensor telemetry
    gid = dg_id.upper()
    if gid == "DG-101":
        detail["telemetry"] = {"running": True, "load_pct": 72.5, "fuel_pct": 84, "temp_c": 82.4, "vib_mms": 2.1, "oil_pressure_bar": 4.5}
    elif gid == "DG-102":
        detail["telemetry"] = {"running": False, "load_pct": 0.0, "fuel_pct": 92, "temp_c": 28.5, "vib_mms": 0.0, "oil_pressure_bar": 0.0}
    elif gid == "DG-103":
        detail["telemetry"] = {"running": True, "load_pct": 68.0, "fuel_pct": 65, "temp_c": 79.1, "vib_mms": 2.4, "oil_pressure_bar": 5.1}
    else:
        detail["telemetry"] = {"running": False, "load_pct": 0.0, "fuel_pct": 77, "temp_c": 26.8, "vib_mms": 0.0, "oil_pressure_bar": 0.0}

    return jsonify({
        "status": "success",
        "generator": detail
    }), 200

@app.route("/api/records", methods=["GET"])
def get_records():
    """Searchable, sortable, filterable generator records endpoint."""
    dg_id = request.args.get("dg_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "date")
    sort_order = request.args.get("sort_order", "desc")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))

    result = data_service.get_records(
        dg_id=dg_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    return jsonify({
        "status": "success",
        **result
    }), 200

@app.route("/api/records", methods=["POST"])
def add_record():
    """Adds a new generator operational record with strict physical validation."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request body must be valid JSON."}), 400

    success, cleaned, err = data_service.add_record(data)
    if not success:
        return jsonify({"status": "error", "message": err}), 400

    anomaly_res = anomaly_service.detect_anomalies([cleaned])
    scored_record = anomaly_res["records"][0] if anomaly_res["records"] else cleaned

    return jsonify({
        "status": "success",
        "message": f"Record {cleaned['record_id']} successfully registered.",
        "record": scored_record
    }), 201

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Returns combined AI Anomaly and Rule-Based Shutdown Delay alerts with state management."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    raw_alerts = anomaly_service.get_unified_alerts(records)
    alerts = enrich_alerts_with_status(raw_alerts)

    severity_filter = request.args.get("severity")
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")

    if severity_filter:
        alerts = [a for a in alerts if a.get("severity") == severity_filter.upper()]
    if type_filter:
        alerts = [a for a in alerts if a.get("alert_type") == type_filter.upper()]
    if status_filter:
        alerts = [a for a in alerts if a.get("status") == status_filter.upper()]

    return jsonify({
        "status": "success",
        "total_alerts": len(alerts),
        "alerts": alerts
    }), 200

@app.route("/api/alerts/<alert_id>/status", methods=["PUT"])
def update_alert_status(alert_id):
    """Updates the status of an alert (ACKNOWLEDGED or RESOLVED)."""
    data = request.get_json() or {}
    new_status = data.get("status", "").upper()
    notes = data.get("notes", "")

    if new_status not in ["OPEN", "ACKNOWLEDGED", "RESOLVED"]:
        return jsonify({"status": "error", "message": "Invalid status. Must be OPEN, ACKNOWLEDGED, or RESOLVED"}), 400

    alert_statuses[alert_id] = {
        "status": new_status,
        "updated_at": datetime.datetime.now().isoformat(),
        "notes": notes
    }
    save_alert_statuses(alert_statuses)

    return jsonify({
        "status": "success",
        "message": f"Alert {alert_id} marked as {new_status}",
        "alert_id": alert_id,
        "new_status": new_status,
        "updated_at": alert_statuses[alert_id]["updated_at"]
    }), 200

@app.route("/api/analysis/fuel", methods=["GET"])
def analysis_fuel():
    """Fuel consumption, cost analysis, and illustrative shutdown delay savings."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    analysis = fuel_service.analyze_fuel(records)
    return jsonify({
        "status": "success",
        "analysis": analysis
    }), 200

@app.route("/api/analysis/emissions", methods=["GET"])
def analysis_emissions():
    """Carbon emissions estimation based on diesel consumption."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    analysis = emission_service.analyze_emissions(records)
    return jsonify({
        "status": "success",
        "analysis": analysis
    }), 200

@app.route("/api/analysis/anomalies", methods=["GET"])
def analysis_anomalies():
    """AI Isolation Forest anomaly detection results, explainable summaries, and model metrics."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    result = anomaly_service.detect_anomalies(records)
    rule_delays = shutdown_service.analyze_shutdown_delays(records)["events"]

    return jsonify({
        "status": "success",
        "ai_anomalies": result["anomalies_only"],
        "all_records_scored": result["records"],
        "summary": result["summary"],
        "model_evaluation": result["model_metrics"],
        "rule_based_delays_count": len([d for d in rule_delays if d.get("exceeds_threshold")]),
        "disclaimer": (
            "AI anomalies represent multivariate statistical deviations requiring investigation, "
            "not verified hardware malfunction. Delay rules are deterministic timestamp comparisons."
        )
    }), 200

@app.route("/api/analysis/anomalies/<record_id>", methods=["GET"])
def get_anomaly_explanation(record_id):
    """
    Returns transparent Explainable AI breakdown for a specific record.
    Includes comparison against load-matched baseline, supporting checks,
    and suggested investigation steps.
    """
    all_records = data_service.get_all_records_filtered()
    explanation = anomaly_service.explain_record(record_id, all_records)
    if explanation.get("status") == "error":
        return jsonify(explanation), 404
    return jsonify(explanation), 200

@app.route("/api/analysis/shutdown-delay", methods=["GET"])
def analysis_shutdown_delay():
    """
    Mains Restoration and Shutdown Delay Intelligence.
    Detects prolonged running post-restoration, reconstructs event timelines,
    and quantifies avoidable fuel and cost.
    """
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)

    # Active states for ongoing delay inspection
    active_states = [
        {"dg_id": "DG-101", "running_status": "Running", "mains_status": "RESTORED", "mains_restored_time": "11:20:00"},
        {"dg_id": "DG-102", "running_status": "Standby", "mains_status": "NORMAL", "mains_restored_time": None},
        {"dg_id": "DG-103", "running_status": "Running", "mains_status": "OUTAGE", "mains_restored_time": None},
        {"dg_id": "DG-104", "running_status": "Standby", "mains_status": "NORMAL", "mains_restored_time": None}
    ]
    if dg_id and dg_id != "ALL":
        active_states = [s for s in active_states if s["dg_id"] == dg_id.upper()]

    analysis = shutdown_service.analyze_shutdown_delays(records, active_states)
    return jsonify({
        "status": "success",
        "analysis": analysis
    }), 200

@app.route("/api/analysis/fuel-efficiency", methods=["GET"])
def analysis_fuel_efficiency():
    """
    Fuel Efficiency Analysis relative to generator runtime and load percentage.
    Provides ISO load-bracket benchmarks, comparable-load baselines, and flags statistical outliers.
    """
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    analysis = efficiency_service.analyze_efficiency(records)
    return jsonify({
        "status": "success",
        "analysis": analysis
    }), 200

@app.route("/api/data-quality/summary", methods=["GET"])
def data_quality_summary():
    """Returns data quality health score, valid/invalid counts, and breakdown."""
    summary = data_service.get_data_quality_summary()
    return jsonify({
        "status": "success",
        "data_quality_summary": summary
    }), 200

@app.route("/api/data-quality/issues", methods=["GET"])
def data_quality_issues():
    """Returns filterable list of data quality issues without silently deleting records."""
    dg_id = request.args.get("dg_id")
    severity = request.args.get("severity")
    category = request.args.get("category")
    issues = data_service.get_data_quality_issues(dg_id, severity, category)
    return jsonify({
        "status": "success",
        "total_issues": len(issues),
        "issues": issues
    }), 200

@app.route("/api/data-quality/export", methods=["GET"])
def export_data_quality_issues():
    """Downloads CSV report of all detected data quality issues."""
    csv_content = data_service.export_data_quality_csv()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=genius_dg_data_quality_report.csv"}
    )

@app.route("/api/analysis/anomalies/run", methods=["POST"])
def run_anomaly_model():
    """Retrains the Isolation Forest model on current dataset with custom contamination rate."""
    data = request.get_json() or {}
    new_contamination = data.get("contamination")
    if new_contamination is not None:
        try:
            val = float(new_contamination)
            if 0.01 <= val <= 0.30:
                anomaly_service.contamination = val
                current_settings["ai_contamination_rate"] = val
                save_settings(current_settings)
            else:
                return jsonify({"status": "error", "message": "Contamination must be between 0.01 and 0.30"}), 400
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid contamination value"}), 400

    all_records = data_service.get_all_records_filtered()
    train_result = anomaly_service.train(all_records)
    detection_res = anomaly_service.detect_anomalies(all_records)

    return jsonify({
        "status": "success",
        "message": "AI Isolation Forest re-trained and re-evaluated successfully.",
        "training": train_result,
        "summary": detection_res["summary"],
        "anomalies_count": len(detection_res["anomalies_only"])
    }), 200

# --- MAINTENANCE ENDPOINTS ---
@app.route("/api/maintenance", methods=["GET"])
def get_maintenance():
    """Returns scheduled maintenance tasks and historical logs."""
    dg_id = request.args.get("dg_id")
    records = load_maintenance()
    if dg_id and dg_id != "ALL":
        records = [m for m in records if m["dg_id"] == dg_id.upper()]
    return jsonify({
        "status": "success",
        "total": len(records),
        "maintenance_schedules": records
    }), 200

@app.route("/api/maintenance", methods=["POST"])
def add_maintenance_log():
    """Records a completed service log."""
    data = request.get_json() or {}
    dg_id = data.get("dg_id", "").upper()
    service_type = data.get("service_type", "Standard Preventive Maintenance")
    technician = data.get("technician", "Control Room Specialist")
    notes = data.get("notes", "")

    if not dg_id:
        return jsonify({"status": "error", "message": "dg_id is required"}), 400

    new_id = f"MNT-{dg_id}-{int(datetime.datetime.now().timestamp()) % 10000}"
    new_entry = {
        "id": new_id,
        "dg_id": dg_id,
        "service_type": service_type,
        "interval_hours": int(data.get("interval_hours", 500)),
        "last_serviced_hours": float(data.get("hours", 450.0)),
        "current_hours": float(data.get("hours", 450.0)),
        "hours_remaining": float(data.get("interval_hours", 500)),
        "due_date": (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
        "status": "COMPLETED",
        "assigned_technician": technician,
        "completed_at": datetime.datetime.now().isoformat(),
        "notes": notes,
        "checklist": ["Filters inspected", "Fluids replaced", "Diagnostics verified normal"]
    }

    records = load_maintenance()
    records.insert(0, new_entry)
    save_maintenance(records)

    return jsonify({
        "status": "success",
        "message": f"Maintenance record {new_id} saved successfully.",
        "record": new_entry
    }), 201

# --- CAMERA MONITORING SIMULATION ENDPOINTS ---
@app.route("/api/camera/events", methods=["GET"])
def get_camera_events():
    """Returns simulated optical and thermal camera telemetry for generator bays."""
    return jsonify({
        "status": "success",
        "mode": "Simulated Demonstration Feed",
        "disclaimer": "All optical/thermal camera events are synthetic simulations for demonstration purposes.",
        "events": CAMERA_EVENTS
    }), 200

@app.route("/api/camera/simulate", methods=["POST"])
def simulate_camera_event():
    """Simulates a camera detection event for demonstration."""
    data = request.get_json() or {}
    dg_id = data.get("dg_id", "DG-101").upper()
    event_type = data.get("event_type", "EXHAUST_SMOKE_SPIKE")

    event_titles = {
        "EXHAUST_SMOKE_SPIKE": ("Exhaust Opacity Warning", "Elevated stack smoke density detected (Ringelmann 2.5)", "WARNING"),
        "THERMAL_HOTSPOT": ("Thermal Hotspot Anomaly", "Surface temperature rise on turbocharger: 98.4 °C", "WARNING"),
        "OIL_LEAK_PUDDLE": ("Visual Fluid Pool", "Reflective optical puddle detected beneath sump tray", "CRITICAL"),
        "PERIMETER_ALERT": ("Perimeter Motion Alert", "Personnel detected near active high-voltage alternator", "CRITICAL")
    }

    title, reading, severity = event_titles.get(event_type, ("Visual Camera Flag", "Optical sensor fluctuation", "WARNING"))

    sim_event = {
        "id": f"CAM-SIM-{int(datetime.datetime.now().timestamp()) % 10000}",
        "camera_id": f"CAM-BAY-{dg_id[-1] if dg_id[-1].isdigit() else '1'}",
        "dg_id": dg_id,
        "bay_name": f"Generator Bay {dg_id[-1] if dg_id[-1].isdigit() else '1'}",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "title": title,
        "severity": severity,
        "reading": reading,
        "status": "Operator Inspection Recommended",
        "is_simulated": True,
        "label": "Operator Triggered Simulated Event"
    }
    CAMERA_EVENTS.insert(0, sim_event)

    return jsonify({
        "status": "success",
        "message": f"Simulated camera event '{title}' generated for {dg_id}.",
        "event": sim_event
    }), 201

# --- SETTINGS ENDPOINTS ---
@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Returns current system configuration."""
    return jsonify({
        "status": "success",
        "settings": {
            "diesel_price_per_litre": fuel_service.diesel_price_per_litre,
            "currency_symbol": fuel_service.currency_symbol,
            "co2_emission_factor": emission_service.emission_factor,
            "shutdown_delay_threshold_min": shutdown_service.threshold_minutes,
            "ai_contamination_rate": anomaly_service.contamination,
            "max_overload_tolerance_pct": current_settings.get("max_overload_tolerance_pct", 115.0),
            "frozen_sensor_threshold": current_settings.get("frozen_sensor_threshold", 4),
            "last_updated": current_settings.get("last_updated")
        }
    }), 200

@app.route("/api/settings", methods=["PUT"])
def update_settings():
    """Updates operational settings."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request body must be JSON."}), 400

    updated_fields = []

    # Diesel price
    if "diesel_price_per_litre" in data:
        try:
            p = float(data["diesel_price_per_litre"])
            if p > 0:
                fuel_service.set_diesel_price(p)
                anomaly_service.diesel_price = p
                shutdown_service.set_config(diesel_price=p)
                efficiency_service.set_config(diesel_price=p)
                current_settings["diesel_price_per_litre"] = p
                updated_fields.append("diesel_price_per_litre")
        except ValueError:
            return jsonify({"status": "error", "message": "diesel_price_per_litre must be numeric"}), 400

    # Currency
    if "currency_symbol" in data:
        c = str(data["currency_symbol"]).strip()
        if c:
            fuel_service.currency_symbol = c
            efficiency_service.set_config(currency_symbol=c)
            current_settings["currency_symbol"] = c
            updated_fields.append("currency_symbol")

    # Emission factor
    if "co2_emission_factor" in data:
        try:
            ef = float(data["co2_emission_factor"])
            if ef > 0:
                emission_service.set_emission_factor(ef)
                current_settings["co2_emission_factor"] = ef
                updated_fields.append("co2_emission_factor")
        except ValueError:
            return jsonify({"status": "error", "message": "co2_emission_factor must be numeric"}), 400

    # Shutdown delay threshold
    if "shutdown_delay_threshold_min" in data:
        try:
            th = float(data["shutdown_delay_threshold_min"])
            if th >= 0:
                anomaly_service.shutdown_delay_threshold_min = th
                shutdown_service.set_config(threshold_minutes=th)
                current_settings["shutdown_delay_threshold_min"] = th
                updated_fields.append("shutdown_delay_threshold_min")
        except ValueError:
            return jsonify({"status": "error", "message": "shutdown_delay_threshold_min must be positive number"}), 400

    # Overload tolerance
    if "max_overload_tolerance_pct" in data:
        try:
            ot = float(data["max_overload_tolerance_pct"])
            if ot >= 100.0:
                data_service.quality_service.max_overload_tolerance_pct = ot
                current_settings["max_overload_tolerance_pct"] = ot
                updated_fields.append("max_overload_tolerance_pct")
        except ValueError:
            return jsonify({"status": "error", "message": "max_overload_tolerance_pct must be >= 100"}), 400

    # Frozen sensor threshold count
    if "frozen_sensor_threshold" in data:
        try:
            fst = int(data["frozen_sensor_threshold"])
            if fst >= 2:
                data_service.quality_service.frozen_sensor_threshold = fst
                current_settings["frozen_sensor_threshold"] = fst
                updated_fields.append("frozen_sensor_threshold")
        except ValueError:
            return jsonify({"status": "error", "message": "frozen_sensor_threshold must be integer >= 2"}), 400

    # AI contamination rate
    if "ai_contamination_rate" in data:
        try:
            cr = float(data["ai_contamination_rate"])
            if 0.01 <= cr <= 0.30:
                anomaly_service.contamination = cr
                current_settings["ai_contamination_rate"] = cr
                updated_fields.append("ai_contamination_rate")
                anomaly_service.train(data_service.get_all_records_filtered())
        except ValueError:
            return jsonify({"status": "error", "message": "ai_contamination_rate must be between 0.01 and 0.30"}), 400

    current_settings["last_updated"] = datetime.datetime.now().isoformat()
    save_settings(current_settings)

    return jsonify({
        "status": "success",
        "message": f"Successfully updated settings: {', '.join(updated_fields)}",
        "updated_settings": {
            "diesel_price_per_litre": fuel_service.diesel_price_per_litre,
            "currency_symbol": fuel_service.currency_symbol,
            "co2_emission_factor": emission_service.emission_factor,
            "shutdown_delay_threshold_min": shutdown_service.threshold_minutes,
            "ai_contamination_rate": anomaly_service.contamination,
            "max_overload_tolerance_pct": current_settings.get("max_overload_tolerance_pct", 115.0),
            "frozen_sensor_threshold": current_settings.get("frozen_sensor_threshold", 4),
            "last_updated": current_settings["last_updated"]
        }
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "code": 404, "message": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"status": "error", "code": 500, "message": "Internal server error", "detail": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting GENIUS DG Monitoring System on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
