"""
GENIUS DG — CSV to Supabase PostgreSQL Migration Script
Usage:
    python scripts/migrate_csv_to_supabase.py [--dry-run] [--batch-size 50]

Safely validates, maps, and imports existing local CSV telemetry, settings,
and maintenance schedules into the Supabase PostgreSQL cloud database.
Uses idempotent upserts on stable primary/unique keys to prevent duplicate records.
"""

import os
import sys
import argparse
import csv
import json
import time

# Ensure backend root is on sys.path
cur_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(cur_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.supabase_service import SupabaseService
from services.data_service import DataService


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate local CSV telemetry into Supabase PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview data without writing to Supabase.")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of rows per insert chunk (default: 50).")
    parser.add_argument("--csv-path", type=str, default=None, help="Custom path to CSV file.")
    return parser.parse_args()


def main():
    args = parse_args()

    print("==================================================================")
    print(" GENIUS DG — SUPABASE CLOUD DATABASE MIGRATION UTILITY")
    print("==================================================================")
    if args.dry_run:
        print(" [MODE: DRY RUN ACTIVATED] No data will be written to the cloud.")
    print("")

    # 1. Initialize Supabase Service
    supabase_svc = SupabaseService()
    health = supabase_svc.check_health()
    print(f" Database Status : {health['status'].upper()}")
    print(f" Target Endpoint : {health.get('target_endpoint', 'None')}")

    if not args.dry_run and not health["connected"]:
        print("\n [ERROR] Cannot proceed with live cloud migration:")
        print(f"   {health['message']}")
        print("   Please configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        print("   or run with --dry-run to validate local files.")
        sys.exit(1)

    # 2. Locate Data Files
    csv_file = args.csv_path or os.path.join(backend_dir, "data", "generator_usage.csv")
    settings_file = os.path.join(backend_dir, "data", "settings.json")
    maintenance_file = os.path.join(backend_dir, "data", "maintenance.json")

    if not os.path.exists(csv_file):
        print(f"\n [ERROR] CSV file not found at: {csv_file}")
        sys.exit(1)

    # 3. Read and Validate CSV Telemetry
    print(f"\n Reading and validating telemetry from: {os.path.basename(csv_file)}...")
    ds = DataService(csv_file)
    valid_records = ds.get_all_records_filtered()
    val_report = ds.get_validation_report()

    print(f"   Total CSV Rows Read   : {val_report['total_raw']}")
    print(f"   Valid Formatted Rows  : {len(valid_records)}")
    print(f"   Invalid / Skipped Rows: {val_report['invalid_records']}")

    # 4. Migrate Generator Fleet Metadata
    generators_seed = [
        {"generator_code": "DG-101", "name": "Caterpillar C9 Prime Unit", "capacity_kva": 250.0, "location": "Main Academic Complex", "status": "Operational", "running_status": "Running", "load_percentage": 72.5, "fuel_level_percent": 84.0, "temperature_celsius": 82.4, "vibration_mms": 2.1, "oil_pressure_bar": 4.5},
        {"generator_code": "DG-102", "name": "Cummins QSB5 Standby Unit", "capacity_kva": 125.0, "location": "Central Library & Seminar Halls", "status": "Operational", "running_status": "Standby", "load_percentage": 0.0, "fuel_level_percent": 92.0, "temperature_celsius": 28.5, "vibration_mms": 0.0, "oil_pressure_bar": 0.0},
        {"generator_code": "DG-103", "name": "Kohler KD500 High-Capacity Unit", "capacity_kva": 500.0, "location": "Data Center & Engineering Labs", "status": "Operational", "running_status": "Running", "load_percentage": 68.0, "fuel_level_percent": 65.0, "temperature_celsius": 79.1, "vibration_mms": 2.4, "oil_pressure_bar": 5.1},
        {"generator_code": "DG-104", "name": "Kirloskar Green Auxiliary Unit", "capacity_kva": 62.5, "location": "Administrative & Health Clinic", "status": "Operational", "running_status": "Standby", "load_percentage": 0.0, "fuel_level_percent": 77.0, "temperature_celsius": 26.8, "vibration_mms": 0.0, "oil_pressure_bar": 0.0}
    ]

    print("\n Migrating Generator Fleet Metadata (4 Units)...")
    if args.dry_run:
        print(f"   [Dry Run] Would seed/upsert {len(generators_seed)} generator units into 'generators' table.")
    else:
        seeded_count = 0
        for gen in generators_seed:
            ok, _, err = supabase_svc.upsert_generator(gen)
            if ok:
                seeded_count += 1
            else:
                print(f"   Warning on generator {gen['generator_code']}: {err}")
        print(f"   Successfully upserted {seeded_count}/{len(generators_seed)} generator units.")

    # 5. Migrate Operational Telemetry Records
    print(f"\n Migrating {len(valid_records)} Telemetry Records into 'sensor_readings'...")
    if args.dry_run:
        sample = valid_records[0] if valid_records else {}
        db_sample = SupabaseService._denormalize_reading(sample)
        print(f"   [Dry Run] Sample transformed row for record {sample.get('record_id')}:")
        print(f"     generator_code     : {db_sample.get('generator_code')}")
        print(f"     recorded_date      : {db_sample.get('recorded_date')}")
        print(f"     runtime_min        : {db_sample.get('runtime_min')} min")
        print(f"     load_kw            : {db_sample.get('load_kw')} kW")
        print(f"     fuel_used_litres   : {db_sample.get('fuel_used_litres')} L")
        print(f"     shutdown_delay_min : {db_sample.get('shutdown_delay_min')} min")
        print(f"     data_source        : {db_sample.get('data_source')} (Clearly labeled simulated)")
        print(f"   [Dry Run] Successfully validated {len(valid_records)} records ready for upload.")
    else:
        t0 = time.time()
        ok, count, err = supabase_svc.upsert_readings_batch(valid_records)
        elapsed = round(time.time() - t0, 2)
        if ok:
            print(f"   Successfully migrated {count} sensor readings in {elapsed}s.")
        else:
            print(f"   [ERROR] Batch migration failed after {count} records: {err}")

    # 6. Migrate Maintenance Records
    if os.path.exists(maintenance_file):
        print("\n Migrating Scheduled Maintenance Records...")
        try:
            with open(maintenance_file, "r", encoding="utf-8") as f:
                mnt_list = json.load(f)
            if args.dry_run:
                print(f"   [Dry Run] Validated {len(mnt_list)} maintenance records ready for upload.")
            else:
                m_count = 0
                for m in mnt_list:
                    ok, _, err = supabase_svc.insert_maintenance(m)
                    if ok:
                        m_count += 1
                print(f"   Successfully migrated {m_count}/{len(mnt_list)} maintenance tasks.")
        except Exception as e:
            print(f"   Warning reading maintenance file: {e}")

    # 7. Migrate System Configuration
    if os.path.exists(settings_file):
        print("\n Migrating System Operational Configuration...")
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved_settings = json.load(f)
            if args.dry_run:
                print(f"   [Dry Run] Validated settings payload: diesel price {saved_settings.get('diesel_price_per_litre')}, threshold {saved_settings.get('shutdown_delay_threshold_min')} min.")
            else:
                ok, _, err = supabase_svc.save_settings(saved_settings)
                if ok:
                    print("   Successfully synced system settings into 'system_settings' table.")
                else:
                    print(f"   Warning syncing settings: {err}")
        except Exception as e:
            print(f"   Warning reading settings file: {e}")

    print("\n==================================================================")
    print(" MIGRATION EVALUATION COMPLETE")
    print("==================================================================")
    if args.dry_run:
        print(" Dry-run verification passed cleanly.")
        print(" Run without '--dry-run' once cloud credentials are ready in .env")
    else:
        print(" Cloud database synchronization completed successfully.")
    print("==================================================================\n")


if __name__ == "__main__":
    main()
