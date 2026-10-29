"""
AI-Powered Diesel Generator Usage Monitoring System - Flask REST API
Author: Senior Full-Stack & AI Engineer
College Mini-Project Backend
"""

import os
import json
import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from services.data_service import DataService
from services.fuel_service import FuelService
from services.emission_service import EmissionService
from services.anomaly_service import AnomalyService

# Initialize Flask app
frontend_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app = Flask(__name__, static_folder=frontend_folder, static_url_path="")

# Configure CORS for local development
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration state (Persisted in settings.json)
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")

DEFAULT_SETTINGS = {
    "diesel_price_per_litre": 94.50,
    "currency_symbol": "₹",
    "co2_emission_factor": 2.68,
    "shutdown_delay_threshold_min": 10.0,
    "ai_contamination_rate": 0.08,
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

# Initial AI model training on startup
all_recs = data_service.get_all_records_filtered()
if all_recs:
    anomaly_service.train(all_recs)

# Helper to apply query parameter filters
def get_query_filters():
    dg_id = request.args.get("dg_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    return dg_id, start_date, end_date

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
        "system": "AI-Powered Diesel Generator Usage Monitoring System",
        "version": "1.0.0",
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

    # Diesel consumption by generator
    fuel_analysis = fuel_service.analyze_fuel(records)
    emissions_analysis = emission_service.analyze_emissions(records)

    # Normal vs Anomalies vs Delay breakdown
    normal_runs = max(0, len(records) - anomalies_count)

    # Get recent unified alerts (Top 10)
    unified_alerts = anomaly_service.get_unified_alerts(records)[:10]

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
            "total_runtime_hours": total_runtime_hours,
            "total_diesel_litres": total_fuel_litres,
            "estimated_diesel_cost": estimated_cost,
            "estimated_co2_kg": estimated_co2_kg,
            "estimated_co2_tonnes": round(estimated_co2_kg / 1000.0, 3),
            "anomalies_detected_count": anomalies_count,
            "shutdown_delays_count": shutdown_delays_count,
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
        "recent_alerts": unified_alerts
    }), 200

@app.route("/api/generators", methods=["GET"])
def get_generators():
    """Returns fleet-wide generator statistics."""
    gens = data_service.get_generators()
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

    # Run anomaly detector on this generator's records
    records = data_service.get_all_records_filtered(dg_id=dg_id)
    anomaly_res = anomaly_service.detect_anomalies(records)
    delays = anomaly_service.check_shutdown_delays(records)

    detail["anomalies_count"] = anomaly_res["summary"]["anomalies"]
    detail["shutdown_delays_count"] = len(delays)
    detail["alerts"] = anomaly_service.get_unified_alerts(records)[:10]

    return jsonify({
        "status": "success",
        "generator": detail
    }), 200

@app.route("/api/records", methods=["GET"])
def get_records():
    """
    Searchable, sortable, filterable generator records endpoint.
    Supports query parameters: dg_id, start_date, end_date, search, sort_by, sort_order, page, per_page.
    """
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

    # Score new record with anomaly model
    anomaly_res = anomaly_service.detect_anomalies([cleaned])
    scored_record = anomaly_res["records"][0] if anomaly_res["records"] else cleaned

    return jsonify({
        "status": "success",
        "message": f"Record {cleaned['record_id']} successfully registered.",
        "record": scored_record
    }), 201

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Returns combined AI Anomaly and Rule-Based Shutdown Delay alerts."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    alerts = anomaly_service.get_unified_alerts(records)

    # Optional severity and type filters
    severity_filter = request.args.get("severity")
    type_filter = request.args.get("type")

    if severity_filter:
        alerts = [a for a in alerts if a.get("severity") == severity_filter.upper()]
    if type_filter:
        alerts = [a for a in alerts if a.get("alert_type") == type_filter.upper()]

    return jsonify({
        "status": "success",
        "total_alerts": len(alerts),
        "alerts": alerts
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
    """AI Isolation Forest anomaly detection results and model metrics."""
    dg_id, start_date, end_date = get_query_filters()
    records = data_service.get_all_records_filtered(dg_id, start_date, end_date)
    result = anomaly_service.detect_anomalies(records)
    rule_delays = anomaly_service.check_shutdown_delays(records)

    return jsonify({
        "status": "success",
        "ai_anomalies": result["anomalies_only"],
        "all_records_scored": result["records"],
        "summary": result["summary"],
        "model_evaluation": result["model_metrics"],
        "rule_based_delays_count": len(rule_delays),
        "disclaimer": (
            "AI anomalies represent multivariate statistical deviations requiring investigation, "
            "not verified hardware malfunction. Delay rules are deterministic timestamp comparisons."
        )
    }), 200

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

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Returns current system configuration."""
    return jsonify({
        "status": "success",
        "settings": {
            "diesel_price_per_litre": fuel_service.diesel_price_per_litre,
            "currency_symbol": fuel_service.currency_symbol,
            "co2_emission_factor": emission_service.emission_factor,
            "shutdown_delay_threshold_min": anomaly_service.shutdown_delay_threshold_min,
            "ai_contamination_rate": anomaly_service.contamination,
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
                current_settings["diesel_price_per_litre"] = p
                updated_fields.append("diesel_price_per_litre")
        except ValueError:
            return jsonify({"status": "error", "message": "diesel_price_per_litre must be numeric"}), 400

    # Currency
    if "currency_symbol" in data:
        c = str(data["currency_symbol"]).strip()
        if c:
            fuel_service.currency_symbol = c
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
                current_settings["shutdown_delay_threshold_min"] = th
                updated_fields.append("shutdown_delay_threshold_min")
        except ValueError:
            return jsonify({"status": "error", "message": "shutdown_delay_threshold_min must be positive number"}), 400

    # AI contamination rate
    if "ai_contamination_rate" in data:
        try:
            cr = float(data["ai_contamination_rate"])
            if 0.01 <= cr <= 0.30:
                anomaly_service.contamination = cr
                current_settings["ai_contamination_rate"] = cr
                updated_fields.append("ai_contamination_rate")
                # Retrain
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
            "shutdown_delay_threshold_min": anomaly_service.shutdown_delay_threshold_min,
            "ai_contamination_rate": anomaly_service.contamination,
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
    print(f"Starting Diesel Generator Monitoring System on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
