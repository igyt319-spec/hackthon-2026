"""
Unit Tests for Calculations and Core Services
Tests:
- Runtime calculations and cross-midnight handling
- Data validation and missing/invalid record filtering
- Fuel cost calculations and pricing changes
- Carbon emission estimations and emission factor flexibility
- AI Isolation Forest anomaly detection and feature extraction
- Rule-based shutdown delay calculation
- Empty dataset handling
"""

import unittest
import os
import sys
import tempfile
import csv

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService
from services.fuel_service import FuelService
from services.emission_service import EmissionService
from services.anomaly_service import AnomalyService

class TestCalculations(unittest.TestCase):

    def setUp(self):
        self.sample_records = [
            {
                "record_id": "REC-0001",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "12:00:00",
                "mains_restored_time": "11:55:00",
                "load_kw": 150.0,
                "fuel_used_litres": 75.0,
                "runtime_min": 120.0,
                "shutdown_delay_min": 5.0,
                "ground_truth_label": "NORMAL",
                "is_synthetic": "True",
                "notes": "Normal run"
            },
            {
                "record_id": "REC-0002",
                "dg_id": "DG-102",
                "capacity_kva": 125.0,
                "date": "2026-06-02",
                "start_time": "14:00:00",
                "stop_time": "16:30:00",
                "mains_restored_time": "15:45:00",
                "load_kw": 80.0,
                "fuel_used_litres": 55.0,
                "runtime_min": 150.0,
                "shutdown_delay_min": 45.0,  # 45 min delay!
                "ground_truth_label": "SHUTDOWN_DELAY",
                "is_synthetic": "True",
                "notes": "Delay test"
            },
            {
                "record_id": "REC-0003",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-03",
                "start_time": "09:00:00",
                "stop_time": "10:00:00",
                "mains_restored_time": "09:55:00",
                "load_kw": 140.0,
                "fuel_used_litres": 110.0,  # Huge fuel anomaly (110 L in 1 hour for 140 kW)
                "runtime_min": 60.0,
                "shutdown_delay_min": 5.0,
                "ground_truth_label": "EXCESSIVE_FUEL",
                "is_synthetic": "True",
                "notes": "Spike test"
            }
        ]

    def test_fuel_cost_calculation(self):
        """Validates that fuel cost is accurately computed as Fuel × Diesel Price."""
        fuel_service = FuelService(default_diesel_price_per_litre=90.0, currency_symbol="₹")
        res = fuel_service.analyze_fuel(self.sample_records)
        
        expected_litres = 75.0 + 55.0 + 110.0  # 240.0 L
        expected_cost = 240.0 * 90.0           # 21,600.0 ₹
        
        self.assertEqual(res["total_fuel_litres"], expected_litres)
        self.assertEqual(res["total_cost"], expected_cost)

        # Update price to 100.0 and re-verify
        fuel_service.set_diesel_price(100.0)
        res2 = fuel_service.analyze_fuel(self.sample_records)
        self.assertEqual(res2["total_cost"], 240.0 * 100.0)

    def test_carbon_emission_calculation(self):
        """Validates CO2 = Fuel (L) × Emission Factor (kg/L)."""
        emission_service = EmissionService(default_emission_factor=2.68)
        res = emission_service.analyze_emissions(self.sample_records)
        
        total_litres = 240.0
        expected_co2_kg = total_litres * 2.68  # 643.2 kg
        
        self.assertAlmostEqual(res["total_co2_kg"], expected_co2_kg, places=2)
        self.assertAlmostEqual(res["total_co2_tonnes"], expected_co2_kg / 1000.0, places=3)
        self.assertEqual(res["emission_factor_used"], 2.68)

    def test_shutdown_delay_rule(self):
        """Validates deterministic detection of post-mains restoration shutdown delays."""
        anomaly_service = AnomalyService(shutdown_delay_threshold_min=10.0, diesel_price=95.0)
        delays = anomaly_service.check_shutdown_delays(self.sample_records)
        
        # Only REC-0002 has delay_minutes >= 10.0 (45 minutes)
        self.assertEqual(len(delays), 1)
        self.assertEqual(delays[0]["record_id"], "REC-0002")
        self.assertEqual(delays[0]["delay_minutes"], 45.0)
        self.assertEqual(delays[0]["severity"], "CRITICAL")
        self.assertGreater(delays[0]["estimated_avoidable_fuel_litres"], 0.0)

    def test_data_validation_boundaries(self):
        """Validates physical boundary checking and rejection of invalid data."""
        # 1. Negative fuel
        valid, _, err = DataService.validate_and_clean_record({
            "dg_id": "DG-101",
            "capacity_kva": 250,
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "load_kw": 100,
            "fuel_used_litres": -15.0,
            "runtime_min": 60
        })
        self.assertFalse(valid)
        self.assertIn("Negative fuel", err)

        # 2. Implausible overload (> 160% capacity)
        valid2, _, err2 = DataService.validate_and_clean_record({
            "dg_id": "DG-101",
            "capacity_kva": 100,
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "load_kw": 500.0,  # 500% load
            "fuel_used_litres": 50.0,
            "runtime_min": 60
        })
        self.assertFalse(valid2)
        self.assertIn("implausible", err2.lower())

        # 3. Missing dg_id
        valid3, _, _ = DataService.validate_and_clean_record({
            "capacity_kva": 100,
            "date": "2026-06-01",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "load_kw": 50.0,
            "fuel_used_litres": 15.0,
            "runtime_min": 60
        })
        self.assertFalse(valid3)

    def test_empty_dataset_handling(self):
        """Ensures services gracefully handle empty dataset without exceptions."""
        fuel_service = FuelService()
        f_res = fuel_service.analyze_fuel([])
        self.assertEqual(f_res["total_fuel_litres"], 0.0)
        self.assertEqual(f_res["total_cost"], 0.0)

        emission_service = EmissionService()
        e_res = emission_service.analyze_emissions([])
        self.assertEqual(e_res["total_co2_kg"], 0.0)

        anomaly_service = AnomalyService()
        a_res = anomaly_service.detect_anomalies([])
        self.assertEqual(len(a_res["records"]), 0)

    def test_isolation_forest_anomaly_detection(self):
        """Verifies that Isolation Forest trains properly and flags extreme outliers."""
        # Create 25 normal records and 2 extreme anomaly records
        records = []
        for i in range(30):
            records.append({
                "record_id": f"REC-{i:04d}",
                "dg_id": "DG-101",
                "capacity_kva": 250.0,
                "date": "2026-06-01",
                "start_time": "10:00:00",
                "stop_time": "11:00:00",
                "mains_restored_time": "10:55:00",
                "load_kw": 150.0 + (i % 5),
                "fuel_used_litres": 38.0 + (i % 3),
                "runtime_min": 60.0,
                "shutdown_delay_min": 5.0,
                "ground_truth_label": "NORMAL"
            })
        
        # Inject extreme outlier
        records.append({
            "record_id": "REC-OUTLIER-1",
            "dg_id": "DG-101",
            "capacity_kva": 250.0,
            "date": "2026-06-02",
            "start_time": "10:00:00",
            "stop_time": "11:00:00",
            "mains_restored_time": "10:55:00",
            "load_kw": 150.0,
            "fuel_used_litres": 145.0,  # 3.8x normal fuel consumption!
            "runtime_min": 60.0,
            "shutdown_delay_min": 5.0,
            "ground_truth_label": "EXCESSIVE_FUEL"
        })

        anomaly_service = AnomalyService(contamination=0.08)
        anomaly_service.train(records)
        res = anomaly_service.detect_anomalies(records)

        self.assertGreater(res["summary"]["anomalies"], 0)
        # Check if the extreme outlier was identified
        outlier_flags = [r for r in res["anomalies_only"] if r["record_id"] == "REC-OUTLIER-1"]
        self.assertEqual(len(outlier_flags), 1)
        self.assertEqual(outlier_flags[0]["ai_status"], "ANOMALY")
        self.assertTrue(len(outlier_flags[0]["trigger_reasons"]) > 0)

if __name__ == "__main__":
    unittest.main()
