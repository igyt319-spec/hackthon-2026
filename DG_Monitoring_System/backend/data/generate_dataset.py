"""
Synthetic Dataset Generator for Diesel Generator Usage Monitoring System
College Mini-Project Demonstration Dataset

Generates realistic diesel generator operational data with:
- Multiple generator capacities (62.5 kVA, 125 kVA, 250 kVA, 500 kVA)
- Multi-month power outage cycles (May 2026 - October 2026)
- Normal power-load and fuel-rate curves based on engineering standards
- Distinct anomaly cases:
    1. Fuel overconsumption (leak / injector wear)
    2. Severe overload beyond safe prime rating
    3. Severe underload / wet-stacking inefficiency
    4. Post-mains restoration shutdown delays (rule-based alerts)
- Clear synthetic demonstration labeling on all records
"""

import csv
import datetime
import math
import os
import random

# Generator fleet profiles
GENERATORS = {
    "DG-101": {
        "capacity_kva": 250.0,
        "location": "Main Academic Complex",
        "power_factor": 0.8,
        "base_load_ratio": (0.45, 0.85),  # 45% - 85% of prime rating
        "fuel_curve": lambda kw, hrs: (0.24 * kw + 3.5) * hrs,  # Litres
    },
    "DG-102": {
        "capacity_kva": 125.0,
        "location": "Central Library & Seminar Hall",
        "power_factor": 0.8,
        "base_load_ratio": (0.40, 0.80),
        "fuel_curve": lambda kw, hrs: (0.25 * kw + 2.0) * hrs,
    },
    "DG-103": {
        "capacity_kva": 500.0,
        "location": "Data Center & Engineering Labs",
        "power_factor": 0.8,
        "base_load_ratio": (0.50, 0.90),
        "fuel_curve": lambda kw, hrs: (0.23 * kw + 6.0) * hrs,
    },
    "DG-104": {
        "capacity_kva": 62.5,
        "location": "Administrative Block & Health Clinic",
        "power_factor": 0.8,
        "base_load_ratio": (0.35, 0.75),
        "fuel_curve": lambda kw, hrs: (0.26 * kw + 1.2) * hrs,
    },
}

def generate_records(num_records=180, seed=42):
    random.seed(seed)
    records = []
    
    start_date = datetime.date(2026, 5, 1)
    end_date = datetime.date(2026, 10, 25)
    total_days = (end_date - start_date).days
    
    gen_keys = list(GENERATORS.keys())
    
    record_counter = 1
    
    for i in range(num_records):
        dg_id = random.choice(gen_keys)
        profile = GENERATORS[dg_id]
        capacity_kva = profile["capacity_kva"]
        prime_kw = capacity_kva * profile["power_factor"]
        
        # Pick date
        day_offset = random.randint(0, total_days)
        rec_date = start_date + datetime.timedelta(days=day_offset)
        
        # Pick start time (typically during daytime or evening outage)
        start_hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 18, 19, 20])
        start_minute = random.choice([0, 10, 15, 20, 30, 45, 50])
        start_sec = 0
        start_time = datetime.time(start_hour, start_minute, start_sec)
        
        # Runtime between 30 min and 360 min
        runtime_min = random.choice([
            random.randint(35, 60),
            random.randint(65, 120),
            random.randint(125, 240),
            random.randint(245, 330)
        ])
        
        start_dt = datetime.datetime.combine(rec_date, start_time)
        stop_dt = start_dt + datetime.timedelta(minutes=runtime_min)
        
        # Determine scenario type:
        # ~80% normal, ~7% excessive fuel, ~5% shutdown delay, ~4% overload, ~4% underload
        scenario_dice = random.random()
        
        if scenario_dice < 0.80:
            scenario = "NORMAL"
        elif scenario_dice < 0.87:
            scenario = "EXCESSIVE_FUEL"  # Anomaly: potential fuel line leak / injector fault
        elif scenario_dice < 0.92:
            scenario = "SHUTDOWN_DELAY"  # Rule alert: delay after mains restoration
        elif scenario_dice < 0.96:
            scenario = "OVERLOAD"        # Anomaly: load exceeded prime rating
        else:
            scenario = "UNDERLOAD"       # Anomaly: extremely low load with high relative fuel
            
        # Calculate load based on scenario
        if scenario == "OVERLOAD":
            # 105% to 125% of prime rating
            load_kw = round(prime_kw * random.uniform(1.05, 1.25), 1)
        elif scenario == "UNDERLOAD":
            # 10% to 20% of prime rating
            load_kw = round(prime_kw * random.uniform(0.10, 0.20), 1)
        else:
            min_r, max_r = profile["base_load_ratio"]
            load_kw = round(prime_kw * random.uniform(min_r, max_r), 1)
            
        # Calculate fuel used
        runtime_hours = runtime_min / 60.0
        base_fuel = profile["fuel_curve"](load_kw, runtime_hours)
        
        # Add normal operational jitter (+/- 5%)
        noise = random.uniform(0.95, 1.05)
        fuel_used = base_fuel * noise
        
        if scenario == "EXCESSIVE_FUEL":
            # Significant fuel spike: 40% to 80% higher than expected curve
            fuel_used = fuel_used * random.uniform(1.45, 1.85)
        elif scenario == "UNDERLOAD":
            # Specific fuel consumption is worse at low loads
            fuel_used = fuel_used * random.uniform(1.30, 1.55)
            
        fuel_used = round(max(fuel_used, 1.0), 2)
        
        # Determine mains restoration time
        # In a normal run, mains is restored 2-8 minutes before generator shuts down (normal cool-down and transfer)
        if scenario == "SHUTDOWN_DELAY":
            # Significant delay: mains restored 25 to 75 minutes BEFORE generator was turned off
            delay_minutes = random.randint(25, 75)
            mains_restored_dt = stop_dt - datetime.timedelta(minutes=delay_minutes)
        else:
            # Normal shutdown delay: 3 to 10 minutes (cool-down cycle)
            delay_minutes = random.randint(2, 9)
            mains_restored_dt = stop_dt - datetime.timedelta(minutes=delay_minutes)
            
        # Format times
        start_time_str = start_dt.strftime("%H:%M:%S")
        stop_time_str = stop_dt.strftime("%H:%M:%S")
        mains_restored_str = mains_restored_dt.strftime("%H:%M:%S")
        
        # Detailed scenario notes
        if scenario == "EXCESSIVE_FUEL":
            notes = "AI Review: Fuel consumption disproportionately elevated relative to load and runtime. Potential fuel leakage or injector calibration issue."
        elif scenario == "OVERLOAD":
            notes = "AI Review: Operating load exceeded recommended continuous prime rating. Risk of thermal stress and premature alternator degradation."
        elif scenario == "UNDERLOAD":
            notes = "AI Review: Low load operating point (<25% rating) with degraded thermal efficiency; wet-stacking risk."
        elif scenario == "SHUTDOWN_DELAY":
            notes = f"Rule Alert: Generator continued running for {delay_minutes} min after mains power restored. Unnecessary diesel expenditure."
        else:
            notes = "Normal operating parameters within standard load-fuel characteristic curve."
            
        rec = {
            "record_id": f"REC-{record_counter:04d}",
            "dg_id": dg_id,
            "capacity_kva": capacity_kva,
            "date": rec_date.strftime("%Y-%m-%d"),
            "start_time": start_time_str,
            "stop_time": stop_time_str,
            "mains_restored_time": mains_restored_str,
            "load_kw": load_kw,
            "fuel_used_litres": fuel_used,
            "runtime_min": runtime_min,
            "shutdown_delay_min": delay_minutes,
            "ground_truth_label": scenario,
            "is_synthetic": "True (Demonstration Data)",
            "notes": notes
        }
        records.append(rec)
        record_counter += 1
        
    # Sort records chronologically
    records.sort(key=lambda r: (r["date"], r["start_time"]))
    
    # Re-index record_id chronologically
    for idx, r in enumerate(records, start=1):
        r["record_id"] = f"REC-{idx:04d}"
        
    return records

def save_to_csv(records, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames = [
        "record_id",
        "dg_id",
        "capacity_kva",
        "date",
        "start_time",
        "stop_time",
        "mains_restored_time",
        "load_kw",
        "fuel_used_litres",
        "runtime_min",
        "shutdown_delay_min",
        "ground_truth_label",
        "is_synthetic",
        "notes"
    ]
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Successfully generated {len(records)} records in {filepath}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_csv = os.path.join(current_dir, "generator_usage.csv")
    recs = generate_records(num_records=220)
    save_to_csv(recs, output_csv)
