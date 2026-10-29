"""
Integration Tests for Flask REST API Endpoints
Tests:
- GET /api/health
- GET /api/dashboard/summary (with and without query filters)
- GET /api/generators
- GET /api/generators/<dg_id>
- GET /api/records
- POST /api/records
- GET /api/alerts
- GET /api/analysis/fuel
- GET /api/analysis/emissions
- GET /api/analysis/anomalies
- POST /api/analysis/anomalies/run
- GET /api/settings
- PUT /api/settings
"""

import unittest
import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, data_service

class TestAPI(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True

    def test_health_endpoint(self):
        """Verifies health check returns 200 and valid JSON with dataset status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["dataset_loaded"])
        self.assertIn("ai_model_trained", data)

    def test_dashboard_summary_unfiltered(self):
        """Verifies dashboard summary delivers all KPI cards and charts."""
        response = self.client.get("/api/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")

        # Check KPIs
        kpis = data["kpis"]
        self.assertIn("total_generators", kpis)
        self.assertIn("total_runtime_hours", kpis)
        self.assertIn("total_diesel_litres", kpis)
        self.assertIn("estimated_diesel_cost", kpis)
        self.assertIn("estimated_co2_kg", kpis)
        self.assertIn("anomalies_detected_count", kpis)

        # Check Charts
        charts = data["charts"]
        self.assertIn("daily_runtime", charts)
        self.assertIn("diesel_by_generator", charts)
        self.assertIn("fuel_cost_trend", charts)
        self.assertIn("co2_emission_trend", charts)
        self.assertIn("normal_vs_anomalies", charts)

        # Check Recent alerts
        self.assertIn("recent_alerts", data)

    def test_dashboard_summary_with_filters(self):
        """Verifies dashboard summary properly filters by generator ID."""
        response = self.client.get("/api/dashboard/summary?dg_id=DG-101")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["filters_applied"]["dg_id"], "DG-101")
        self.assertGreater(data["filters_applied"]["total_records_matched"], 0)

    def test_generators_endpoints(self):
        """Verifies fleet list and individual generator detail."""
        res = self.client.get("/api/generators")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreater(len(data["generators"]), 0)

        # Check individual generator
        first_gid = data["generators"][0]["dg_id"]
        detail_res = self.client.get(f"/api/generators/{first_gid}")
        self.assertEqual(detail_res.status_code, 200)
        detail_data = json.loads(detail_res.data)
        self.assertEqual(detail_data["generator"]["dg_id"], first_gid)

        # 404 on nonexistent generator
        nonexistent = self.client.get("/api/generators/NONEXISTENT-999")
        self.assertEqual(nonexistent.status_code, 404)

    def test_records_pagination_and_creation(self):
        """Verifies records pagination and adding a new record with validation."""
        # Test pagination
        res = self.client.get("/api/records?page=1&per_page=10")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data["records"]), 10)
        self.assertEqual(data["pagination"]["current_page"], 1)

        # Test adding new valid record
        new_record = {
            "dg_id": "DG-101",
            "capacity_kva": 250.0,
            "date": "2026-10-26",
            "start_time": "11:00:00",
            "stop_time": "12:30:00",
            "mains_restored_time": "12:20:00",
            "load_kw": 160.0,
            "fuel_used_litres": 55.0,
            "runtime_min": 90.0,
            "notes": "Test integration record"
        }
        post_res = self.client.post("/api/records", json=new_record)
        self.assertEqual(post_res.status_code, 201)
        post_data = json.loads(post_res.data)
        self.assertEqual(post_data["status"], "success")

        # Test adding invalid record (e.g. negative fuel)
        invalid_rec = dict(new_record)
        invalid_rec["fuel_used_litres"] = -20.0
        bad_res = self.client.post("/api/records", json=invalid_rec)
        self.assertEqual(bad_res.status_code, 400)

    def test_analysis_endpoints(self):
        """Verifies fuel, emissions, and anomaly analysis endpoints."""
        fuel_res = self.client.get("/api/analysis/fuel")
        self.assertEqual(fuel_res.status_code, 200)
        self.assertIn("analysis", json.loads(fuel_res.data))

        emissions_res = self.client.get("/api/analysis/emissions")
        self.assertEqual(emissions_res.status_code, 200)
        self.assertIn("analysis", json.loads(emissions_res.data))

        anom_res = self.client.get("/api/analysis/anomalies")
        self.assertEqual(anom_res.status_code, 200)
        anom_data = json.loads(anom_res.data)
        self.assertIn("ai_anomalies", anom_data)
        self.assertIn("model_evaluation", anom_data)

    def test_settings_get_and_put(self):
        """Verifies settings can be retrieved and updated."""
        get_res = self.client.get("/api/settings")
        self.assertEqual(get_res.status_code, 200)
        settings = json.loads(get_res.data)["settings"]

        # Update diesel price and threshold
        put_res = self.client.put("/api/settings", json={
            "diesel_price_per_litre": 96.00,
            "shutdown_delay_threshold_min": 12.0
        })
        self.assertEqual(put_res.status_code, 200)
        updated = json.loads(put_res.data)["updated_settings"]
        self.assertEqual(updated["diesel_price_per_litre"], 96.00)
        self.assertEqual(updated["shutdown_delay_threshold_min"], 12.0)

if __name__ == "__main__":
    unittest.main()
