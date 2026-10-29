"""
Phase 1 Advanced Improvements - Automated Unit & Integration Tests
College Mini-Project: AI-Powered Diesel Generator Usage Monitoring System

Verifies:
1. Normal records are processed successfully.
2. Known unusual records can be flagged by the anomaly workflow.
3. Anomaly explanations distinguish AI scores from rule-based findings.
4. Missing features do not crash anomaly analysis.
5. Valid mains restoration and stop timestamps produce the correct delay.
6. Stop time earlier than restoration is handled as inconsistent data.
7. Missing timestamps do not produce a fabricated delay.
8. An ongoing generator uses elapsed time only when valid observations exist.
9. Fuel rate calculations handle zero and missing runtime safely.
10. Load percentage uses compatible units and valid rated capacity.
11. Missing and negative values are reported by data validation.
12. Fuel level outside 0-100% is flagged.
13. Duplicate and stale records are handled according to the configured rules.
14. API responses contain the required fields and valid HTTP status codes.
15. Existing tests and application features continue to work.
"""

import unittest
import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, data_service
from services.anomaly_service import AnomalyService
from services.shutdown_service import ShutdownService
from services.efficiency_service import EfficiencyService
from services.data_quality_service import DataQualityService


class TestPhase1Advanced(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True

        self.normal_records = [
            {
                "record_id": "REC-N001",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "12:00:00",
                "mains_restored_time": "11:55:00",
                "load_kw": 140.0,
                "fuel_used_litres": 70.0,
                "runtime_min": 120.0,
                "shutdown_delay_min": 5.0,
                "ground_truth_label": "NORMAL"
            },
            {
                "record_id": "REC-N002",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-02",
                "start_time": "09:00:00",
                "stop_time": "11:00:00",
                "mains_restored_time": "10:54:00",
                "load_kw": 145.0,
                "fuel_used_litres": 72.0,
                "runtime_min": 120.0,
                "shutdown_delay_min": 6.0,
                "ground_truth_label": "NORMAL"
            },
            {
                "record_id": "REC-N003",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-03",
                "start_time": "14:00:00",
                "stop_time": "16:00:00",
                "mains_restored_time": "15:55:00",
                "load_kw": 138.0,
                "fuel_used_litres": 69.0,
                "runtime_min": 120.0,
                "shutdown_delay_min": 5.0,
                "ground_truth_label": "NORMAL"
            },
            {
                "record_id": "REC-N004",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-04",
                "start_time": "13:00:00",
                "stop_time": "15:00:00",
                "mains_restored_time": "14:52:00",
                "load_kw": 142.0,
                "fuel_used_litres": 71.0,
                "runtime_min": 120.0,
                "shutdown_delay_min": 8.0,
                "ground_truth_label": "NORMAL"
            }
        ]

    # Test 1: Normal records are processed successfully
    def test_normal_records_processing(self):
        anomaly_svc = AnomalyService()
        res = anomaly_svc.detect_anomalies(self.normal_records)
        self.assertIn("records", res)
        self.assertEqual(len(res["records"]), 4)
        for r in res["records"]:
            self.assertIn("ai_status", r)
            self.assertIn("anomaly_score", r)

    # Test 2: Known unusual records can be flagged by anomaly workflow
    def test_flag_known_unusual_records(self):
        anom_record = {
            "record_id": "REC-ANOM-01",
            "dg_id": "DG-101",
            "capacity_kva": 250.0,
            "date": "2026-06-05",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "mains_restored_time": "10:55:00",
            "load_kw": 140.0,
            "fuel_used_litres": 150.0,  # ~4.2x normal consumption
            "runtime_min": 60.0,
            "shutdown_delay_min": 5.0,
            "ground_truth_label": "EXCESSIVE_FUEL"
        }
        dataset = self.normal_records * 5 + [anom_record]
        anomaly_svc = AnomalyService(contamination=0.10)
        anomaly_svc.train(dataset)
        res = anomaly_svc.detect_anomalies(dataset)
        flagged_ids = [r["record_id"] for r in res["anomalies_only"]]
        self.assertIn("REC-ANOM-01", flagged_ids)

    # Test 3: Anomaly explanations distinguish AI scores from rule-based findings
    def test_anomaly_explanations_distinguish_rules(self):
        anom_record = {
            "record_id": "REC-ANOM-02",
            "dg_id": "DG-101",
            "capacity_kva": 250.0,
            "date": "2026-06-05",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "mains_restored_time": "10:55:00",
            "load_kw": 140.0,
            "fuel_used_litres": 140.0,
            "runtime_min": 60.0,
            "shutdown_delay_min": 5.0,
            "temperature_c": 99.5  # Rule threshold breach
        }
        dataset = self.normal_records * 5 + [anom_record]
        anomaly_svc = AnomalyService(contamination=0.10)
        anomaly_svc.train(dataset)
        explanation = anomaly_svc.explain_record("REC-ANOM-02", dataset)

        self.assertEqual(explanation["status"], "success")
        self.assertIn("score_metadata", explanation)
        self.assertIn("supporting_indicators", explanation)
        self.assertIn("disclaimer", explanation)
        # Verify clear statement that Isolation Forest does not prove mechanical fault
        self.assertIn("statistical", explanation["disclaimer"].lower())

    # Test 4: Missing features do not crash anomaly analysis
    def test_missing_features_safe_handling(self):
        sparse_record = {
            "record_id": "REC-SPARSE",
            "dg_id": "DG-102",
            # capacity_kva, temperature_c, vibration_mm_s omitted
            "date": "2026-06-10",
            "start_time": "08:00:00",
            "stop_time": "09:00:00",
            "load_kw": 50.0,
            "fuel_used_litres": 15.0,
            "runtime_min": 60.0
        }
        anomaly_svc = AnomalyService()
        # Must not raise an exception
        res = anomaly_svc.detect_anomalies([sparse_record])
        self.assertEqual(len(res["records"]), 1)
        self.assertIn("ai_status", res["records"][0])

    # Test 5: Valid mains restoration and stop timestamps produce correct delay
    def test_valid_shutdown_delay_calculation(self):
        shutdown_svc = ShutdownService(threshold_minutes=10.0, diesel_price=90.0)
        recs = [{
            "record_id": "REC-D01",
            "dg_id": "DG-101",
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "12:45:00",
            "mains_restored_time": "12:15:00",  # 30 min delay
            "runtime_min": 165.0,
            "fuel_used_litres": 80.0
        }]
        res = shutdown_svc.analyze_shutdown_delays(recs)
        self.assertEqual(res["summary"]["excess_delay_events_count"], 1)
        event = res["events"][0]
        self.assertEqual(event["shutdown_delay_min"], 30.0)
        self.assertTrue(event["exceeds_threshold"])
        self.assertGreater(event["avoidable_fuel_litres"], 0.0)

    # Test 6: Stop time earlier than restoration is handled as inconsistent data
    def test_stop_before_restoration_inconsistent(self):
        shutdown_svc = ShutdownService(threshold_minutes=10.0)
        recs = [{
            "record_id": "REC-INCONSISTENT",
            "dg_id": "DG-101",
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "11:30:00",
            "mains_restored_time": "12:00:00",  # Stop 30 min before restoration
            "runtime_min": 90.0,
            "fuel_used_litres": 45.0
        }]
        res = shutdown_svc.analyze_shutdown_delays(recs)
        event = res["events"][0]
        self.assertEqual(event["delay_status"], "INCONSISTENT_TIMESTAMPS")
        self.assertIsNone(event["shutdown_delay_min"])
        self.assertFalse(event["exceeds_threshold"])

    # Test 7: Missing timestamps do not produce a fabricated delay
    def test_missing_timestamps_safe_handling(self):
        shutdown_svc = ShutdownService(threshold_minutes=10.0)
        recs = [{
            "record_id": "REC-NOTIME",
            "dg_id": "DG-101",
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "",  # Missing stop time
            "mains_restored_time": "11:00:00",
            "runtime_min": 60.0,
            "fuel_used_litres": 30.0
        }]
        res = shutdown_svc.analyze_shutdown_delays(recs)
        event = res["events"][0]
        self.assertEqual(event["delay_status"], "INSUFFICIENT_TIMESTAMP_DATA")
        self.assertIsNone(event["shutdown_delay_min"])
        self.assertEqual(event["avoidable_fuel_litres"], 0.0)

    # Test 8: An ongoing generator uses elapsed time only when valid observations exist
    def test_ongoing_generator_delay_tracking(self):
        shutdown_svc = ShutdownService(threshold_minutes=10.0)
        active_states = [
            {
                "dg_id": "DG-101",
                "running_status": "Running",
                "mains_status": "RESTORED",
                "mains_restored_time": "08:00:00"  # Well in past today
            }
        ]
        res = shutdown_svc.analyze_shutdown_delays([], active_generator_states=active_states)
        self.assertGreaterEqual(len(res["ongoing_delays"]), 1)
        ongoing = res["ongoing_delays"][0]
        self.assertIn("Ongoing estimated delay", ongoing["label"])
        self.assertGreater(ongoing["elapsed_delay_min"], 10.0)

    # Test 9: Fuel rate calculations handle zero and missing runtime safely
    def test_fuel_rate_zero_runtime(self):
        efficiency_svc = EfficiencyService()
        recs = [
            {
                "record_id": "REC-ZEROTIME",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "runtime_min": 0.0,  # Zero runtime
                "fuel_used_litres": 10.0,
                "load_kw": 50.0
            }
        ]
        res = efficiency_svc.analyze_efficiency(recs)
        self.assertEqual(res["summary"]["valid_records_count"], 0)
        self.assertEqual(res["summary"]["excluded_records_count"], 1)

    # Test 10: Load percentage uses compatible units and valid rated capacity
    def test_load_percentage_and_invalid_capacity(self):
        efficiency_svc = EfficiencyService()
        recs = [
            {
                "record_id": "REC-VALID-LOAD",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,  # Prime kW = 200 kW
                "date": "2026-06-01",
                "runtime_min": 60.0,
                "fuel_used_litres": 50.0,
                "load_kw": 100.0  # 50% load
            },
            {
                "record_id": "REC-INVALID-CAP",
                "dg_id": "DG-102",
                "capacity_kva": -50.0,  # Invalid negative capacity
                "date": "2026-06-01",
                "runtime_min": 60.0,
                "fuel_used_litres": 20.0,
                "load_kw": 50.0
            }
        ]
        res = efficiency_svc.analyze_efficiency(recs)
        self.assertEqual(res["summary"]["valid_records_count"], 1)
        self.assertEqual(res["summary"]["excluded_records_count"], 1)
        # Validate 50% load bracket placement
        baselines = {b["bracket_id"]: b for b in res["load_bracket_baselines"]}
        self.assertEqual(baselines["OPTIMAL_PRIME"]["records_count"], 1)

    # Test 11: Missing and negative values reported by data validation
    def test_data_validation_negative_and_missing(self):
        dq_svc = DataQualityService()
        bad_records = [
            {
                "record_id": "REC-NEG-FUEL",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 100.0,
                "fuel_used_litres": -15.0,  # Negative fuel
                "runtime_min": 60.0
            },
            {
                "record_id": "REC-NEG-LOAD",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": -20.0,  # Negative load
                "fuel_used_litres": 30.0,
                "runtime_min": 60.0
            }
        ]
        res = dq_svc.validate_dataset(bad_records)
        categories = [i["issue_category"] for i in res["issues"]]
        self.assertIn("NEGATIVE_FUEL", categories)
        self.assertIn("NEGATIVE_LOAD", categories)
        self.assertEqual(res["summary"]["invalid_records"], 2)

    # Test 12: Fuel level outside 0-100% is flagged
    def test_fuel_level_out_of_bounds(self):
        dq_svc = DataQualityService()
        recs = [
            {
                "record_id": "REC-BAD-FUEL-LVL",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 100.0,
                "fuel_used_litres": 25.0,
                "runtime_min": 60.0,
                "fuel_level_percent": 118.5  # Out of bounds (>100%)
            }
        ]
        res = dq_svc.validate_dataset(recs)
        categories = [i["issue_category"] for i in res["issues"]]
        self.assertIn("OUT_OF_BOUNDS_FUEL_LEVEL", categories)

    # Test 13: Duplicate and frozen sensor records handled according to rules
    def test_duplicate_and_frozen_sensor(self):
        dq_svc = DataQualityService(frozen_sensor_threshold=3)
        recs = [
            {
                "record_id": "REC-DUP-01",
                "dg_id": "DG-103",
                "capacity_kva": 500.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 250.123,
                "fuel_used_litres": 60.0,
                "runtime_min": 60.0
            },
            {
                "record_id": "REC-DUP-01",  # Duplicate ID
                "dg_id": "DG-103",
                "capacity_kva": 500.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 250.123,
                "fuel_used_litres": 60.0,
                "runtime_min": 60.0
            },
            {
                "record_id": "REC-DUP-03",
                "dg_id": "DG-103",
                "capacity_kva": 500.0,
                "date": "2026-06-02",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 250.123,  # Identical load
                "fuel_used_litres": 60.0,
                "runtime_min": 60.0
            },
            {
                "record_id": "REC-DUP-04",
                "dg_id": "DG-103",
                "capacity_kva": 500.0,
                "date": "2026-06-03",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "load_kw": 250.123,  # Identical load (3rd consecutive)
                "fuel_used_litres": 60.0,
                "runtime_min": 60.0
            }
        ]
        res = dq_svc.validate_dataset(recs)
        categories = [i["issue_category"] for i in res["issues"]]
        self.assertIn("DUPLICATE_RECORD_ID", categories)
        self.assertIn("FROZEN_SENSOR_SUSPECTED", categories)

    # Test 14: API responses contain required fields and valid HTTP status codes
    def test_new_api_endpoints_status_and_schema(self):
        # 1. Shutdown delay endpoint
        res1 = self.client.get("/api/analysis/shutdown-delay")
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        self.assertIn("summary", data1["analysis"])
        self.assertIn("events", data1["analysis"])
        self.assertIn("ongoing_delays", data1["analysis"])

        # 2. Fuel efficiency endpoint
        res2 = self.client.get("/api/analysis/fuel-efficiency")
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertIn("summary", data2["analysis"])
        self.assertIn("generator_efficiency", data2["analysis"])
        self.assertIn("load_bracket_baselines", data2["analysis"])

        # 3. Data quality summary endpoint
        res3 = self.client.get("/api/data-quality/summary")
        self.assertEqual(res3.status_code, 200)
        data3 = json.loads(res3.data)
        self.assertIn("data_quality_summary", data3)
        self.assertIn("data_health_score_pct", data3["data_quality_summary"])

        # 4. Data quality issues endpoint
        res4 = self.client.get("/api/data-quality/issues")
        self.assertEqual(res4.status_code, 200)
        data4 = json.loads(res4.data)
        self.assertIn("issues", data4)

        # 5. Data quality export endpoint (CSV)
        res5 = self.client.get("/api/data-quality/export")
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(res5.mimetype, "text/csv")
        self.assertIn("record_id", res5.data.decode("utf-8"))

        # 6. Anomaly explanation endpoint
        first_rec = data_service._records[0]["record_id"]
        res6 = self.client.get(f"/api/analysis/anomalies/{first_rec}")
        self.assertEqual(res6.status_code, 200)
        data6 = json.loads(res6.data)
        self.assertEqual(data6["record_id"], first_rec)
        self.assertIn("comparison_context", data6)
        self.assertIn("supporting_indicators", data6)

    # Test 15: Existing tests and application features continue to work
    def test_existing_features_backward_compatibility(self):
        # Health
        res_h = self.client.get("/api/health")
        self.assertEqual(res_h.status_code, 200)
        # Dashboard summary
        res_d = self.client.get("/api/dashboard/summary")
        self.assertEqual(res_d.status_code, 200)
        # Settings
        res_s = self.client.get("/api/settings")
        self.assertEqual(res_s.status_code, 200)
        settings = json.loads(res_s.data)["settings"]
        self.assertIn("diesel_price_per_litre", settings)
        self.assertIn("max_overload_tolerance_pct", settings)


if __name__ == "__main__":
    unittest.main()
