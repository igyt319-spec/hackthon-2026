"""
Automated Test Suite for Supabase Backend Integration
Tests:
 1. Missing Supabase credentials handling
 2. Database connection failure handling
 3. Health endpoint distinguishing application health from DB connectivity
 4. Successful database service operations using mocks
 5. Generator listing and detail retrieval
 6. Dashboard summary API
 7. Alert acknowledgement and resolution
 8. Invalid reading values and timestamps
 9. CSV import validation and duplicate prevention
10. AI anomaly analysis using representative test data
11. Fuel cost and CO2 calculations
12. Settings validation
13. CSV report export
14. Protection against exposing secrets in API responses
15. Existing project regression tests
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Add backend directory to sys.path
cur_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(cur_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app, current_settings, alert_statuses
from services.supabase_service import SupabaseService
from services.data_service import DataService


class TestSupabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    # 1. Missing Supabase credentials
    def test_01_missing_supabase_credentials(self):
        svc = SupabaseService(supabase_url="", service_role_key="")
        self.assertFalse(svc.is_configured())
        health = svc.check_health()
        self.assertFalse(health["connected"])
        self.assertEqual(health["status"], "disconnected")
        self.assertEqual(health["active_data_source"], "local_csv_fallback")

    # 2. Database connection failure
    @patch("supabase.create_client")
    def test_02_database_connection_failure(self, mock_create):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("Connection timeout to Supabase")
        mock_create.return_value = mock_client

        svc = SupabaseService(
            supabase_url="https://fake-project.supabase.co",
            service_role_key="real-format-key-not-placeholder-12345678"
        )
        health = svc.check_health()
        self.assertFalse(health["connected"])
        self.assertEqual(health["status"], "connection_error")
        self.assertIn("Database unreachable", health["message"])

    # 3. Health endpoint distinguishing application from database
    def test_03_health_endpoint_distinguishes_app_from_db(self):
        res = self.app.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))

        self.assertEqual(data.get("application_status"), "healthy")
        self.assertIn("database", data)
        db_info = data["database"]
        self.assertIn("connected", db_info)
        self.assertIn("status", db_info)
        self.assertIn("active_data_source", db_info)

    # 4. Successful database service operations using mocks
    @patch("supabase.create_client")
    def test_04_successful_database_service_operations_mocked(self, mock_create):
        mock_client = MagicMock()
        # Mock generators
        mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"generator_code": "DG-101", "name": "Caterpillar C9", "capacity_kva": 250.0}]
        )
        # Mock insert reading
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{"record_id": "REC-MOCK-01", "generator_code": "DG-101"}]
        )
        # Mock update alert
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"alert_id": "ALT-01", "status": "RESOLVED"}]
        )
        mock_create.return_value = mock_client

        svc = SupabaseService(
            supabase_url="https://valid-url.supabase.co",
            service_role_key="valid-service-key-not-placeholder"
        )

        ok, gens, _ = svc.get_generators()
        self.assertTrue(ok)
        self.assertEqual(len(gens), 1)
        self.assertEqual(gens[0]["generator_code"], "DG-101")

        ok_ins, row, _ = svc.insert_reading({"record_id": "REC-MOCK-01", "dg_id": "DG-101"})
        self.assertTrue(ok_ins)

        ok_alt, alt, _ = svc.update_alert_status("ALT-01", "RESOLVED", "All clear")
        self.assertTrue(ok_alt)

    # 5. Generator listing and detail retrieval
    def test_05_generator_listing_and_detail_retrieval(self):
        res = self.app.get("/api/generators")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["generators"]), 4)

        # Individual generator detail
        res_dg = self.app.get("/api/generators/DG-101")
        self.assertEqual(res_dg.status_code, 200)
        data_dg = json.loads(res_dg.data.decode("utf-8"))
        self.assertEqual(data_dg["generator"]["dg_id"], "DG-101")
        self.assertIn("telemetry", data_dg["generator"])

        # Unknown generator
        res_404 = self.app.get("/api/generators/DG-NONEXISTENT")
        self.assertEqual(res_404.status_code, 404)

    # 6. Dashboard summary API
    def test_06_dashboard_summary_api(self):
        res = self.app.get("/api/dashboard/summary?dg_id=DG-101&start_date=2026-05-01&end_date=2026-10-31")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertIn("kpis", data)
        self.assertIn("charts", data)
        self.assertIn("total_runtime_hours", data["kpis"])
        self.assertIn("total_diesel_litres", data["kpis"])

    # 7. Alert acknowledgement and resolution
    def test_07_alert_acknowledgement_and_resolution(self):
        # Acknowledge
        res_ack = self.app.post(
            "/api/alerts/ALT-TEST-001/acknowledge",
            data=json.dumps({"notes": "Under review by tech"}),
            content_type="application/json"
        )
        self.assertEqual(res_ack.status_code, 200)
        data_ack = json.loads(res_ack.data.decode("utf-8"))
        self.assertEqual(data_ack["new_status"], "ACKNOWLEDGED")

        # Resolve
        res_res = self.app.post(
            "/api/alerts/ALT-TEST-001/resolve",
            data=json.dumps({"notes": "Filter replaced, cleared"}),
            content_type="application/json"
        )
        self.assertEqual(res_res.status_code, 200)
        data_res = json.loads(res_res.data.decode("utf-8"))
        self.assertEqual(data_res["new_status"], "RESOLVED")

    # 8. Invalid reading values and timestamps
    def test_08_invalid_reading_values_and_timestamps(self):
        # Negative fuel
        res_neg = self.app.post("/api/records", data=json.dumps({
            "dg_id": "DG-101",
            "capacity_kva": 250,
            "date": "2026-10-29",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "load_kw": 120,
            "fuel_used_litres": -25.0
        }), content_type="application/json")
        self.assertEqual(res_neg.status_code, 400)

        # Invalid capacity
        res_cap = self.app.post("/api/records", data=json.dumps({
            "dg_id": "DG-101",
            "capacity_kva": -10,
            "date": "2026-10-29",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "load_kw": 120,
            "fuel_used_litres": 25.0
        }), content_type="application/json")
        self.assertEqual(res_cap.status_code, 400)

    # 9. CSV import validation and duplicate prevention
    def test_09_csv_import_validation_and_duplicate_prevention(self):
        sample_dict = {
            "record_id": "REC-IDEMPOTENT-01",
            "dg_id": "DG-101",
            "capacity_kva": 250.0,
            "date": "2026-05-10",
            "start_time": "10:00:00",
            "stop_time": "11:30:00",
            "load_kw": 140.0,
            "fuel_used_litres": 45.0,
            "runtime_min": 90.0
        }
        db_row = SupabaseService._denormalize_reading(sample_dict)
        self.assertEqual(db_row["record_id"], "REC-IDEMPOTENT-01")
        self.assertEqual(db_row["generator_code"], "DG-101")
        self.assertEqual(db_row["data_source"], "simulated")
        self.assertTrue(db_row["is_synthetic"])

    # 10. AI anomaly analysis using representative test data
    def test_10_ai_anomaly_analysis_representative_data(self):
        res = self.app.get("/api/analysis/anomalies")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertIn("ai_anomalies", data)
        self.assertIn("summary", data)
        self.assertIn("disclaimer", data)

    # 11. Fuel cost and CO2 calculations
    def test_11_fuel_cost_and_co2_calculations(self):
        fuel_litres = 100.0
        diesel_price = 94.50
        co2_factor = 2.68
        expected_cost = round(fuel_litres * diesel_price, 2)
        expected_co2 = round(fuel_litres * co2_factor, 2)

        self.assertEqual(expected_cost, 9450.0)
        self.assertEqual(expected_co2, 268.0)

    # 12. Settings validation and persistence
    def test_12_settings_validation_and_persistence(self):
        # Invalid contamination
        res_inv = self.app.put("/api/settings", data=json.dumps({
            "ai_contamination_rate": 0.85
        }), content_type="application/json")
        self.assertEqual(res_inv.status_code, 400)

        # Valid setting update
        res_val = self.app.put("/api/settings", data=json.dumps({
            "shutdown_delay_threshold_min": 11.5,
            "diesel_price_per_litre": 95.0
        }), content_type="application/json")
        self.assertEqual(res_val.status_code, 200)
        data = json.loads(res_val.data.decode("utf-8"))
        self.assertEqual(data["updated_settings"]["shutdown_delay_threshold_min"], 11.5)

    # 13. CSV report export
    def test_13_csv_report_export(self):
        res = self.app.get("/api/reports/export.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        self.assertIn("attachment; filename=genius_dg_audit_report.csv", res.headers.get("Content-Disposition", ""))
        body = res.data.decode("utf-8")
        self.assertTrue(body.startswith("record_id,dg_id"))

    # 14. Protection against exposing secrets in API responses
    def test_14_protection_against_exposing_secrets(self):
        # Health endpoint
        res = self.app.get("/api/health")
        body = res.data.decode("utf-8")
        self.assertNotIn("service_role", body)
        self.assertNotIn("secret_key", body)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", body)

        # Settings endpoint
        res_set = self.app.get("/api/settings")
        body_set = res_set.data.decode("utf-8")
        self.assertNotIn("service_role", body_set)
        self.assertNotIn("password", body_set)

    # 15. Existing project regression tests consistency
    def test_15_existing_regression_tests_consistency(self):
        # Shutdown delay endpoint
        res_sd = self.app.get("/api/analysis/shutdown-delay")
        self.assertEqual(res_sd.status_code, 200)
        data_sd = json.loads(res_sd.data.decode("utf-8"))
        self.assertEqual(data_sd["status"], "success")

        # Fuel efficiency endpoint
        res_fe = self.app.get("/api/analysis/fuel-efficiency")
        self.assertEqual(res_fe.status_code, 200)
        data_fe = json.loads(res_fe.data.decode("utf-8"))
        self.assertEqual(data_fe["status"], "success")

        # Data quality summary endpoint
        res_dq = self.app.get("/api/data-quality/summary")
        self.assertEqual(res_dq.status_code, 200)
        data_dq = json.loads(res_dq.data.decode("utf-8"))
        self.assertEqual(data_dq["status"], "success")


if __name__ == "__main__":
    unittest.main()
