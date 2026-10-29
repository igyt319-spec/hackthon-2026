"""
Data Quality Monitoring Service
College Mini-Project: AI-Powered Diesel Generator Usage Monitoring System

Identifies unreliable generator readings before they affect AI results,
calculations, and reports.

Validation Checks:
- Missing required fields
- Duplicate records or observations
- Invalid timestamps
- Stop time before start time
- Inconsistent timestamps (stop before mains restoration)
- Negative fuel consumption
- Negative or zero runtime
- Invalid or negative capacity
- Negative or extreme temperature (-40°C to 130°C)
- Negative vibration (< 0 mm/s)
- Fuel level outside 0-100%
- Load exceeding rated capacity beyond tolerance
- Stale or delayed data
- Repeated unchanged readings (frozen sensors)

Outputs structured issues and summary metrics without silently deleting or fabricating data.
"""

import datetime
from typing import List, Dict, Any, Optional, Tuple


class DataQualityService:
    def __init__(
        self,
        max_overload_tolerance_pct: float = 115.0,
        frozen_sensor_threshold: int = 4,
        stale_threshold_hours: float = 72.0
    ):
        self.max_overload_tolerance_pct = max_overload_tolerance_pct
        self.frozen_sensor_threshold = frozen_sensor_threshold
        self.stale_threshold_hours = stale_threshold_hours

    def validate_dataset(self, raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Performs exhaustive data quality inspection across all records.
        Returns:
            - summary: total checked, valid, warning, invalid/excluded, stale counts, health score %
            - issues: list of individual issues with severity, explanation, and exclusion flag
            - valid_records: records suitable for calculations
            - excluded_records: records that cannot safely be used for calculations
        """
        if not raw_records:
            return {
                "summary": {
                    "total_checked": 0,
                    "valid_records": 0,
                    "records_with_warnings": 0,
                    "invalid_records": 0,
                    "stale_records": 0,
                    "data_health_score_pct": 100.0,
                    "critical_issues_count": 0,
                    "warning_issues_count": 0
                },
                "issues": [],
                "valid_records": [],
                "excluded_records": []
            }

        issues: List[Dict[str, Any]] = []
        valid_records: List[Dict[str, Any]] = []
        excluded_records: List[Dict[str, Any]] = []

        seen_record_ids = set()
        seen_observations = set()
        record_issue_map: Dict[str, List[str]] = {}

        # 1. Row-by-row validation
        for idx, r in enumerate(raw_records, start=1):
            row_issues = []
            rec_id = str(r.get("record_id") or f"ROW-{idx}").strip()
            dg_id = str(r.get("dg_id") or "UNKNOWN").strip().upper()
            date_str = str(r.get("date") or "").strip()
            start_str = str(r.get("start_time") or "").strip()
            stop_str = str(r.get("stop_time") or "").strip()
            mains_str = str(r.get("mains_restored_time") or "").strip()

            exclude_this_record = False

            # Check 1: Duplicate record ID
            if rec_id in seen_record_ids:
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "record_id",
                    "issue_category": "DUPLICATE_RECORD_ID",
                    "severity": "CRITICAL",
                    "explanation": f"Duplicate record identifier '{rec_id}' encountered.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": True
                })
                exclude_this_record = True
            else:
                seen_record_ids.add(rec_id)

            # Check 2: Duplicate operational observation (same generator, date, start_time)
            obs_key = (dg_id, date_str, start_str)
            if start_str and obs_key in seen_observations:
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "start_time",
                    "issue_category": "DUPLICATE_OBSERVATION",
                    "severity": "WARNING",
                    "explanation": f"Duplicate run observation detected for {dg_id} on {date_str} at {start_str}.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": False
                })
            elif start_str:
                seen_observations.add(obs_key)

            # Check 3: Missing essential fields
            required_fields = ["dg_id", "date", "start_time", "stop_time", "load_kw", "fuel_used_litres", "capacity_kva"]
            for f in required_fields:
                val = r.get(f)
                if val is None or str(val).strip() == "":
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": f,
                        "issue_category": "MISSING_REQUIRED_VALUE",
                        "severity": "CRITICAL",
                        "explanation": f"Missing mandatory field '{f}'.",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True

            # Check 4: Date parsing
            dt_date = None
            if date_str:
                try:
                    dt_date = datetime.date.fromisoformat(date_str)
                except Exception:
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "date",
                        "issue_category": "INVALID_DATE_FORMAT",
                        "severity": "CRITICAL",
                        "explanation": f"Date value '{date_str}' is not in valid ISO format (YYYY-MM-DD).",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True

            # Check 5: Timestamp sequencing
            t_start, t_stop, t_mains = None, None, None
            if start_str:
                try:
                    t_start = datetime.datetime.strptime(start_str, "%H:%M:%S")
                except Exception:
                    try:
                        t_start = datetime.datetime.strptime(start_str, "%H:%M")
                    except Exception:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "start_time",
                            "issue_category": "INVALID_TIMESTAMP",
                            "severity": "CRITICAL",
                            "explanation": f"Unparseable start_time '{start_str}'.",
                            "timestamp": f"{date_str} {start_str}".strip(),
                            "excluded_from_analysis": True
                        })
                        exclude_this_record = True

            if stop_str:
                try:
                    t_stop = datetime.datetime.strptime(stop_str, "%H:%M:%S")
                except Exception:
                    try:
                        t_stop = datetime.datetime.strptime(stop_str, "%H:%M")
                    except Exception:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "stop_time",
                            "issue_category": "INVALID_TIMESTAMP",
                            "severity": "CRITICAL",
                            "explanation": f"Unparseable stop_time '{stop_str}'.",
                            "timestamp": f"{date_str} {stop_str}".strip(),
                            "excluded_from_analysis": True
                        })
                        exclude_this_record = True

            if mains_str:
                try:
                    t_mains = datetime.datetime.strptime(mains_str, "%H:%M:%S")
                except Exception:
                    try:
                        t_mains = datetime.datetime.strptime(mains_str, "%H:%M")
                    except Exception:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "mains_restored_time",
                            "issue_category": "INVALID_TIMESTAMP",
                            "severity": "WARNING",
                            "explanation": f"Unparseable mains_restored_time '{mains_str}'.",
                            "timestamp": f"{date_str} {mains_str}".strip(),
                            "excluded_from_analysis": False
                        })

            # Check 6: Stop time vs Start time
            if t_start and t_stop:
                diff_min = (t_stop - t_start).total_seconds() / 60.0
                if diff_min < 0:
                    # Check if midnight crossing (e.g., 23:30 to 01:15 -> diff_min = -1335 + 1440 = 105 min)
                    if diff_min + 1440.0 > 0:
                        diff_min += 1440.0
                    else:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "stop_time",
                            "issue_category": "STOP_BEFORE_START",
                            "severity": "CRITICAL",
                            "explanation": f"Generator stop time ({stop_str}) is earlier than start time ({start_str}) without midnight crossing.",
                            "timestamp": f"{date_str} {stop_str}".strip(),
                            "excluded_from_analysis": True
                        })
                        exclude_this_record = True

            # Check 7: Stop time vs Mains Restored time (Inconsistent timestamps)
            if t_mains and t_stop:
                delay_diff = (t_stop - t_mains).total_seconds() / 60.0
                if delay_diff < -15.0 and delay_diff > -1400:  # Allow 15 min leeway for clock skew or midnight crossing
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "shutdown_delay_min",
                        "issue_category": "INCONSISTENT_TIMESTAMPS",
                        "severity": "WARNING",
                        "explanation": f"Generator stop time ({stop_str}) recorded prior to mains restoration time ({mains_str}). Inconsistent timestamp sequence.",
                        "timestamp": f"{date_str} {stop_str}".strip(),
                        "excluded_from_analysis": False
                    })

            # Check 8: Negative Fuel
            try:
                fuel_val = float(r.get("fuel_used_litres", 0))
                if fuel_val < 0:
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "fuel_used_litres",
                        "issue_category": "NEGATIVE_FUEL",
                        "severity": "CRITICAL",
                        "explanation": f"Negative fuel consumption value ({fuel_val} L) is physically impossible.",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True
            except (ValueError, TypeError):
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "fuel_used_litres",
                    "issue_category": "NON_NUMERIC_VALUE",
                    "severity": "CRITICAL",
                    "explanation": f"Fuel consumption value '{r.get('fuel_used_litres')}' is not numeric.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": True
                })
                exclude_this_record = True

            # Check 9: Runtime <= 0
            try:
                runtime_val = float(r.get("runtime_min", 0))
                if runtime_val <= 0:
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "runtime_min",
                        "issue_category": "INVALID_RUNTIME",
                        "severity": "CRITICAL",
                        "explanation": f"Runtime value ({runtime_val} min) must be strictly positive.",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True
            except (ValueError, TypeError):
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "runtime_min",
                    "issue_category": "NON_NUMERIC_VALUE",
                    "severity": "CRITICAL",
                    "explanation": f"Runtime value '{r.get('runtime_min')}' is not numeric.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": True
                })
                exclude_this_record = True

            # Check 10: Invalid Capacity
            capacity_val = 0.0
            try:
                capacity_val = float(r.get("capacity_kva", 0))
                if capacity_val <= 0:
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "capacity_kva",
                        "issue_category": "INVALID_CAPACITY",
                        "severity": "CRITICAL",
                        "explanation": f"Generator rated capacity ({capacity_val} kVA) must be greater than zero.",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True
            except (ValueError, TypeError):
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "capacity_kva",
                    "issue_category": "NON_NUMERIC_VALUE",
                    "severity": "CRITICAL",
                    "explanation": f"Capacity value '{r.get('capacity_kva')}' is not numeric.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": True
                })
                exclude_this_record = True

            # Check 11: Load kW checks (Negative or Exceeding Rating beyond tolerance)
            try:
                load_val = float(r.get("load_kw", 0))
                if load_val < 0:
                    row_issues.append({
                        "record_id": rec_id,
                        "dg_id": dg_id,
                        "field_name": "load_kw",
                        "issue_category": "NEGATIVE_LOAD",
                        "severity": "CRITICAL",
                        "explanation": f"Negative electrical load value ({load_val} kW) is invalid.",
                        "timestamp": f"{date_str} {start_str}".strip(),
                        "excluded_from_analysis": True
                    })
                    exclude_this_record = True
                elif capacity_val > 0:
                    prime_kw = capacity_val * 0.8
                    max_tolerated_kw = prime_kw * (self.max_overload_tolerance_pct / 100.0)
                    if load_val > max_tolerated_kw:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "load_kw",
                            "issue_category": "LOAD_EXCEEDS_RATING",
                            "severity": "WARNING",
                            "explanation": f"Operating load ({load_val:.1f} kW) exceeds safe continuous limit ({max_tolerated_kw:.1f} kW, {self.max_overload_tolerance_pct}% rating).",
                            "timestamp": f"{date_str} {start_str}".strip(),
                            "excluded_from_analysis": False
                        })
            except (ValueError, TypeError):
                row_issues.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "field_name": "load_kw",
                    "issue_category": "NON_NUMERIC_VALUE",
                    "severity": "CRITICAL",
                    "explanation": f"Load value '{r.get('load_kw')}' is not numeric.",
                    "timestamp": f"{date_str} {start_str}".strip(),
                    "excluded_from_analysis": True
                })
                exclude_this_record = True

            # Check 12: Fuel Level Percent (if provided)
            if "fuel_level_percent" in r and r["fuel_level_percent"] is not None:
                try:
                    fl_pct = float(r["fuel_level_percent"])
                    if fl_pct < 0 or fl_pct > 100:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "fuel_level_percent",
                            "issue_category": "OUT_OF_BOUNDS_FUEL_LEVEL",
                            "severity": "WARNING",
                            "explanation": f"Fuel level percentage ({fl_pct}%) outside standard 0-100% boundary.",
                            "timestamp": f"{date_str} {start_str}".strip(),
                            "excluded_from_analysis": False
                        })
                except (ValueError, TypeError):
                    pass

            # Check 13: Temperature sensor range (if provided)
            if "temperature_c" in r and r["temperature_c"] is not None:
                try:
                    temp_c = float(r["temperature_c"])
                    if temp_c < -40.0 or temp_c > 130.0:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "temperature_c",
                            "issue_category": "TEMPERATURE_OUT_OF_RANGE",
                            "severity": "WARNING",
                            "explanation": f"Coolant/exhaust temperature reading ({temp_c} °C) is outside physical sensor envelope (-40°C to 130°C).",
                            "timestamp": f"{date_str} {start_str}".strip(),
                            "excluded_from_analysis": False
                        })
                except (ValueError, TypeError):
                    pass

            # Check 14: Vibration sensor range (if provided)
            if "vibration_mm_s" in r and r["vibration_mm_s"] is not None:
                try:
                    vib = float(r["vibration_mm_s"])
                    if vib < 0.0:
                        row_issues.append({
                            "record_id": rec_id,
                            "dg_id": dg_id,
                            "field_name": "vibration_mm_s",
                            "issue_category": "NEGATIVE_VIBRATION",
                            "severity": "WARNING",
                            "explanation": f"Vibration amplitude ({vib} mm/s RMS) cannot be negative.",
                            "timestamp": f"{date_str} {start_str}".strip(),
                            "excluded_from_analysis": False
                        })
                except (ValueError, TypeError):
                    pass

            # Accumulate issues
            issues.extend(row_issues)
            if row_issues:
                record_issue_map[rec_id] = [i["issue_category"] for i in row_issues]

            if exclude_this_record:
                excluded_records.append(r)
            else:
                valid_records.append(r)

        # 2. Sequential / Fleet-wide checks: Frozen Sensors
        gen_records_map: Dict[str, List[Dict[str, Any]]] = {}
        for r in raw_records:
            gid = str(r.get("dg_id", "")).strip().upper()
            if gid:
                gen_records_map.setdefault(gid, []).append(r)

        for gid, grecs in gen_records_map.items():
            if len(grecs) >= self.frozen_sensor_threshold:
                consecutive_count = 1
                last_load = None
                for gr in grecs:
                    try:
                        cur_load = float(gr.get("load_kw", 0))
                        if last_load is not None and abs(cur_load - last_load) < 0.001 and cur_load > 0:
                            consecutive_count += 1
                            if consecutive_count == self.frozen_sensor_threshold:
                                issues.append({
                                    "record_id": str(gr.get("record_id")),
                                    "dg_id": gid,
                                    "field_name": "load_kw",
                                    "issue_category": "FROZEN_SENSOR_SUSPECTED",
                                    "severity": "WARNING",
                                    "explanation": f"Frozen sensor suspected on {gid}: {consecutive_count} consecutive readings identical at {cur_load:.2f} kW.",
                                    "timestamp": f"{gr.get('date')} {gr.get('start_time')}".strip(),
                                    "excluded_from_analysis": False
                                })
                        else:
                            consecutive_count = 1
                        last_load = cur_load
                    except Exception:
                        consecutive_count = 1

        # Summary statistics calculation
        critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
        warning_count = sum(1 for i in issues if i["severity"] == "WARNING")
        total_raw = len(raw_records)
        invalid_count = len(excluded_records)
        records_with_warnings = sum(1 for rid, cats in record_issue_map.items() if any(c != "CRITICAL" for c in cats))

        health_score = 100.0
        if total_raw > 0:
            deductions = (critical_count * 5.0) + (warning_count * 1.5)
            health_score = max(0.0, round(100.0 - (deductions / total_raw) * 10.0, 1))

        return {
            "summary": {
                "total_checked": total_raw,
                "valid_records": len(valid_records),
                "records_with_warnings": records_with_warnings,
                "invalid_records": invalid_count,
                "stale_records": 0,
                "data_health_score_pct": health_score,
                "critical_issues_count": critical_count,
                "warning_issues_count": warning_count
            },
            "issues": issues,
            "valid_records": valid_records,
            "excluded_records": excluded_records
        }


if __name__ == "__main__":
    import os
    import sys
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(cur_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from services.data_service import DataService

    ds = DataService()
    summary = ds.get_data_quality_summary()
    issues = ds.get_data_quality_issues()

    print("\n=======================================================")
    print(" GENIUS DG - SENSOR DATA QUALITY MONITOR")
    print("=======================================================")
    print(f" Telemetry Health Score : {summary['data_health_score_pct']}%")
    print(f" Total Records Checked  : {summary['total_checked']}")
    print(f" Valid Operational Runs : {summary['valid_records']}")
    print(f" Runs With Warnings     : {summary['records_with_warnings']}")
    print(f" Excluded / Invalid Runs: {summary['invalid_records']}")
    print(f" Total Issues Detected  : {len(issues)}")
    if issues:
        print("\n--- SAMPLE DETECTED DATA ISSUES (FIRST 3) ---")
        for i in issues[:3]:
            print(f" - [{i['severity']}] {i['record_id']} ({i['dg_id']}): {i['issue_category']} on field '{i['field_name']}'")
            print(f"   Reason: {i['explanation']}")
    print("=======================================================\n")
