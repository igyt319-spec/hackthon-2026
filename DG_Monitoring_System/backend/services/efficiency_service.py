"""
Fuel Efficiency Analysis Service
College Mini-Project: AI-Powered Diesel Generator Usage Monitoring System

Calculates and analyzes fuel consumption relative to generator runtime and load.
Implements:
- Fuel consumption rate per operating hour (L/h)
- Generator load percentage against rated capacity
- Load-bracket benchmarking (Underload, Light, Prime, Heavy, Overload)
- Transparent anomaly flagging within comparable load brackets
- Robust handling of zero runtime, missing fuel, and invalid capacity with tracking of excluded records.
"""

import math
from typing import List, Dict, Any, Optional, Tuple


class EfficiencyService:
    def __init__(self, diesel_price: float = 94.50, currency_symbol: str = "₹"):
        self.diesel_price = diesel_price
        self.currency_symbol = currency_symbol

        # Standard ISO 8528 load brackets
        self.load_brackets = [
            {"id": "UNDERLOAD", "name": "Underload (<25% Rating)", "min_pct": 0.0, "max_pct": 25.0, "efficiency_desc": "Poor thermal efficiency; wet-stacking risk"},
            {"id": "LIGHT", "name": "Light Load (25-50% Rating)", "min_pct": 25.0, "max_pct": 50.0, "efficiency_desc": "Sub-optimal specific fuel consumption"},
            {"id": "OPTIMAL_PRIME", "name": "Optimal Prime (50-75% Rating)", "min_pct": 50.0, "max_pct": 75.0, "efficiency_desc": "Design sweet-spot for specific fuel efficiency"},
            {"id": "HEAVY_PRIME", "name": "High Prime (75-100% Rating)", "min_pct": 75.0, "max_pct": 100.0, "efficiency_desc": "High power output; nominal fuel consumption curve"},
            {"id": "OVERLOAD", "name": "Overload (>100% Rating)", "min_pct": 100.0, "max_pct": 999.0, "efficiency_desc": "Exceeds continuous prime rating; thermal stress risk"}
        ]

    def set_config(self, diesel_price: Optional[float] = None, currency_symbol: Optional[str] = None):
        if diesel_price is not None and diesel_price > 0:
            self.diesel_price = float(diesel_price)
        if currency_symbol:
            self.currency_symbol = currency_symbol

    def analyze_efficiency(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes records and performs comprehensive fuel efficiency analysis.
        Returns:
            - summary: overall fuel, runtime, average fleet L/h, valid vs excluded record count
            - generator_efficiency: per-generator specific fuel rate and average load
            - load_bracket_baselines: statistical baseline for each load bracket
            - unusual_consumption_records: records flagged for elevated fuel relative to comparable load
            - excluded_records: details of records excluded from efficiency calculations
        """
        valid_records = []
        excluded_records = []

        # 1. Validate and compute derived efficiency metrics for each record
        for r in records:
            rec_id = str(r.get("record_id", "REC-UNKNOWN"))
            dg_id = str(r.get("dg_id", "UNKNOWN"))
            fuel = r.get("fuel_used_litres")
            runtime_min = r.get("runtime_min")
            load_kw = r.get("load_kw")
            cap_kva = r.get("capacity_kva")

            # Check fuel validity
            try:
                fuel_val = float(fuel) if fuel is not None else -1
            except (ValueError, TypeError):
                fuel_val = -1

            # Check runtime validity
            try:
                runtime_val = float(runtime_min) if runtime_min is not None else 0
            except (ValueError, TypeError):
                runtime_val = 0

            # Check load validity
            try:
                load_val = float(load_kw) if load_kw is not None else -1
            except (ValueError, TypeError):
                load_val = -1

            # Check capacity validity
            try:
                cap_val = float(cap_kva) if cap_kva is not None else 0
            except (ValueError, TypeError):
                cap_val = 0

            # Determine exclusion reasons
            exclusion_reasons = []
            if fuel_val < 0:
                exclusion_reasons.append("Missing or negative fuel consumption")
            if runtime_val <= 0:
                exclusion_reasons.append("Zero or negative runtime duration")
            if cap_val <= 0:
                exclusion_reasons.append("Missing or invalid rated capacity")
            if load_val < 0:
                exclusion_reasons.append("Missing or negative load reading")

            if exclusion_reasons:
                excluded_records.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "date": r.get("date"),
                    "reasons": exclusion_reasons
                })
                continue

            # Valid computation
            runtime_hours = runtime_val / 60.0
            fuel_rate_lph = round(fuel_val / runtime_hours, 2)
            prime_kw = cap_val * 0.8  # Standard 0.8 PF
            load_pct = round((load_val / prime_kw) * 100.0, 1) if prime_kw > 0 else 0.0

            # Specific fuel consumption (litres per kWh generated)
            kwh_generated = load_val * runtime_hours
            sfc_litres_per_kwh = round(fuel_val / kwh_generated, 3) if kwh_generated > 0 else 0.0

            # Determine load bracket
            bracket_id = "OPTIMAL_PRIME"
            bracket_name = "Optimal Prime (50-75% Rating)"
            for b in self.load_brackets:
                if b["min_pct"] <= load_pct < b["max_pct"]:
                    bracket_id = b["id"]
                    bracket_name = b["name"]
                    break

            r_calc = dict(r)
            r_calc["runtime_hours"] = round(runtime_hours, 2)
            r_calc["fuel_rate_lph"] = fuel_rate_lph
            r_calc["load_pct"] = load_pct
            r_calc["prime_kw"] = round(prime_kw, 1)
            r_calc["kwh_generated"] = round(kwh_generated, 1)
            r_calc["sfc_l_per_kwh"] = sfc_litres_per_kwh
            r_calc["load_bracket_id"] = bracket_id
            r_calc["load_bracket_name"] = bracket_name
            valid_records.append(r_calc)

        # 2. Build Load-Bracket Baselines (Comparable-Load Groups)
        bracket_baselines = {}
        for b in self.load_brackets:
            b_records = [r for r in valid_records if r["load_bracket_id"] == b["id"]]
            count = len(b_records)
            if count > 0:
                rates = [r["fuel_rate_lph"] for r in b_records]
                avg_rate = sum(rates) / count
                sorted_rates = sorted(rates)
                median_rate = sorted_rates[count // 2]
                variance = sum((x - avg_rate) ** 2 for x in rates) / count
                std_rate = math.sqrt(variance)

                bracket_baselines[b["id"]] = {
                    "bracket_id": b["id"],
                    "bracket_name": b["name"],
                    "efficiency_desc": b["efficiency_desc"],
                    "records_count": count,
                    "avg_fuel_rate_lph": round(avg_rate, 2),
                    "median_fuel_rate_lph": round(median_rate, 2),
                    "std_fuel_rate_lph": round(std_rate, 2),
                    "min_fuel_rate_lph": min(rates),
                    "max_fuel_rate_lph": max(rates),
                    "avg_load_pct": round(sum(r["load_pct"] for r in b_records) / count, 1)
                }
            else:
                bracket_baselines[b["id"]] = {
                    "bracket_id": b["id"],
                    "bracket_name": b["name"],
                    "efficiency_desc": b["efficiency_desc"],
                    "records_count": 0,
                    "avg_fuel_rate_lph": 0.0,
                    "median_fuel_rate_lph": 0.0,
                    "std_fuel_rate_lph": 0.0,
                    "min_fuel_rate_lph": 0.0,
                    "max_fuel_rate_lph": 0.0,
                    "avg_load_pct": 0.0
                }

        # 3. Identify Unusual Fuel Consumption by comparing against comparable-load baseline
        unusual_records = []
        for r in valid_records:
            b_info = bracket_baselines.get(r["load_bracket_id"])
            if b_info and b_info["records_count"] >= 3:
                median = b_info["median_fuel_rate_lph"]
                threshold = median * 1.35  # 35% higher than median for that load group
                if r["fuel_rate_lph"] > threshold:
                    dev_pct = round(((r["fuel_rate_lph"] - median) / median) * 100.0, 1) if median > 0 else 0
                    unusual_records.append({
                        "record_id": r["record_id"],
                        "dg_id": r["dg_id"],
                        "date": r["date"],
                        "load_kw": r["load_kw"],
                        "load_pct": r["load_pct"],
                        "fuel_used_litres": r["fuel_used_litres"],
                        "runtime_hours": r["runtime_hours"],
                        "fuel_rate_lph": r["fuel_rate_lph"],
                        "comparison_group": b_info["bracket_name"],
                        "group_median_rate_lph": median,
                        "deviation_percent": f"+{dev_pct}%",
                        "status": "STATISTICAL_FUEL_ELEVATION",
                        "note": (
                            f"Fuel consumption rate ({r['fuel_rate_lph']} L/h) is {dev_pct}% above the median "
                            f"({median} L/h) for similar load operating records ({b_info['bracket_name']}). "
                            "Inspect fuel flow sensor, load metering, or fuel system weepage."
                        ),
                        "disclaimer": "Statistical variance only. Does not confirm equipment failure or theft."
                    })

        # 4. Generator-wise aggregation
        gen_stats = {}
        for r in valid_records:
            gid = r["dg_id"]
            if gid not in gen_stats:
                gen_stats[gid] = {
                    "dg_id": gid,
                    "capacity_kva": r["capacity_kva"],
                    "total_fuel_litres": 0.0,
                    "total_runtime_hours": 0.0,
                    "total_kwh_generated": 0.0,
                    "load_pct_sum": 0.0,
                    "runs_count": 0
                }
            gen_stats[gid]["total_fuel_litres"] += r["fuel_used_litres"]
            gen_stats[gid]["total_runtime_hours"] += r["runtime_hours"]
            gen_stats[gid]["total_kwh_generated"] += r["kwh_generated"]
            gen_stats[gid]["load_pct_sum"] += r["load_pct"]
            gen_stats[gid]["runs_count"] += 1

        generator_efficiency_list = []
        for gid, g in sorted(gen_stats.items()):
            hrs = g["total_runtime_hours"]
            kwh = g["total_kwh_generated"]
            avg_lph = round(g["total_fuel_litres"] / hrs, 2) if hrs > 0 else 0.0
            avg_load = round(g["load_pct_sum"] / g["runs_count"], 1) if g["runs_count"] > 0 else 0.0
            avg_sfc = round(g["total_fuel_litres"] / kwh, 3) if kwh > 0 else 0.0

            generator_efficiency_list.append({
                "dg_id": gid,
                "capacity_kva": g["capacity_kva"],
                "total_fuel_litres": round(g["total_fuel_litres"], 2),
                "total_runtime_hours": round(hrs, 1),
                "total_kwh_generated": round(kwh, 1),
                "avg_fuel_rate_lph": avg_lph,
                "avg_load_pct": avg_load,
                "specific_fuel_consumption_l_per_kwh": avg_sfc,
                "runs_count": g["runs_count"]
            })

        # Total fleet summary
        total_fleet_fuel = sum(r["fuel_used_litres"] for r in valid_records)
        total_fleet_hours = sum(r["runtime_hours"] for r in valid_records)
        fleet_avg_lph = round(total_fleet_fuel / total_fleet_hours, 2) if total_fleet_hours > 0 else 0.0

        return {
            "summary": {
                "total_records_analyzed": len(records),
                "valid_records_count": len(valid_records),
                "excluded_records_count": len(excluded_records),
                "total_fuel_litres": round(total_fleet_fuel, 2),
                "total_runtime_hours": round(total_fleet_hours, 1),
                "fleet_average_litres_per_hour": fleet_avg_lph,
                "unusual_fuel_records_count": len(unusual_records),
                "diesel_price_per_litre": self.diesel_price,
                "currency_symbol": self.currency_symbol
            },
            "generator_efficiency": generator_efficiency_list,
            "load_bracket_baselines": list(bracket_baselines.values()),
            "unusual_consumption_records": unusual_records,
            "data_quality_notes": {
                "valid_records_count": len(valid_records),
                "excluded_records_count": len(excluded_records),
                "exclusions_detail": excluded_records[:20]
            }
        }


if __name__ == "__main__":
    import os
    import sys
    # Add backend folder to sys.path so services can resolve
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(cur_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from services.data_service import DataService

    ds = DataService()
    records = ds.get_all_records_filtered()
    
    svc = EfficiencyService(diesel_price=94.50, currency_symbol="INR")
    result = svc.analyze_efficiency(records)

    summary = result["summary"]
    print("\n=======================================================")
    print(" GENIUS DG - FUEL EFFICIENCY & LOAD BRACKET ANALYSIS")
    print("=======================================================")
    print(f" Total Records Checked : {summary['total_records_analyzed']}")
    print(f" Valid Operational Runs: {summary['valid_records_count']}")
    print(f" Excluded Records      : {summary['excluded_records_count']}")
    print(f" Fleet Total Fuel      : {summary['total_fuel_litres']:,.1f} Litres")
    print(f" Fleet Total Runtime   : {summary['total_runtime_hours']:,.1f} Hours")
    print(f" Fleet Avg Burn Rate   : {summary['fleet_average_litres_per_hour']} L/h")
    print(f" Unusual Outlier Runs  : {summary['unusual_fuel_records_count']}")

    print("\n--- ISO 8528 LOAD-BRACKET BASELINES ---")
    for b in result["load_bracket_baselines"]:
        rate_str = f"{b['median_fuel_rate_lph']} L/h" if b['median_fuel_rate_lph'] > 0 else "N/A"
        print(f" - {b['bracket_name']:<24}: {b['records_count']:>3} runs | Avg Load: {b['avg_load_pct']:>5}% | Median: {rate_str}")

    print("\n--- GENERATOR UNIT BREAKDOWN ---")
    for g in result["generator_efficiency"]:
        print(f" [{g['dg_id']}] {g['capacity_kva']} kVA | {g['runs_count']} runs | {g['total_runtime_hours']} hrs | {g['total_fuel_litres']:,.1f} L | Avg Rate: {g['avg_fuel_rate_lph']} L/h | Avg SFC: {g['specific_fuel_consumption_l_per_kwh']} L/kWh")

    if result["unusual_consumption_records"]:
        print("\n--- STATISTICAL UNUSUAL FUEL CONSUMPTION (FIRST 3) ---")
        for u in result["unusual_consumption_records"][:3]:
            print(f" - Record {u['record_id']} ({u['dg_id']}): {u['fuel_rate_lph']} L/h vs median {u['group_median_rate_lph']} L/h ({u['deviation_percent']})")
    print("=======================================================\n")
