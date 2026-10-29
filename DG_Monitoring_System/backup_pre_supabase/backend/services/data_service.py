"""
Data Service Module - Modular Data Access Layer
Supports CSV dataset prototype with clean abstraction for future MySQL integration.
Provides data validation, filtering, pagination, sorting, and statistical aggregations.
"""

import os
import csv
import io
import datetime
from typing import List, Dict, Any, Optional, Tuple
from services.data_quality_service import DataQualityService

class DataService:
    def __init__(self, csv_path: Optional[str] = None):
        if csv_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, "data", "generator_usage.csv")
        self.csv_path = csv_path
        self._records: List[Dict[str, Any]] = []
        self._raw_records: List[Dict[str, Any]] = []
        self._last_loaded: Optional[datetime.datetime] = None
        self.quality_service = DataQualityService()
        self._quality_result: Dict[str, Any] = {
            "summary": {
                "total_checked": 0, "valid_records": 0, "records_with_warnings": 0,
                "invalid_records": 0, "stale_records": 0, "data_health_score_pct": 100.0
            },
            "issues": [],
            "valid_records": [],
            "excluded_records": []
        }
        self._validation_report: Dict[str, Any] = {
            "total_raw": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "issues": []
        }
        self.load_data()

    def load_data(self) -> bool:
        """Loads and validates records from the storage layer (CSV or DB)."""
        if not os.path.exists(self.csv_path):
            self._records = []
            self._raw_records = []
            return False

        records = []
        raw_list = []
        issues = []
        total_raw = 0

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=1):
                total_raw += 1
                raw_dict = dict(row)
                raw_list.append(raw_dict)
                is_valid, cleaned, err = self.validate_and_clean_record(row)
                if is_valid and cleaned is not None:
                    records.append(cleaned)
                else:
                    issues.append(f"Row {row_idx}: {err}")

        self._raw_records = raw_list
        self._records = records
        self._last_loaded = datetime.datetime.now()

        # Run comprehensive data quality evaluation
        self._quality_result = self.quality_service.validate_dataset(raw_list)

        self._validation_report = {
            "total_raw": total_raw,
            "valid_records": len(records),
            "invalid_records": len(issues),
            "issues": issues[:15],
            "quality_summary": self._quality_result["summary"]
        }
        return True

    @staticmethod
    def validate_and_clean_record(raw: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validates individual generator records against physical boundaries.
        Rejects or flags missing, negative or physically impossible values.
        """
        try:
            dg_id = str(raw.get("dg_id", "")).strip().upper()
            if not dg_id:
                return False, None, "Missing dg_id"

            # Parse capacity
            capacity_kva = float(raw.get("capacity_kva", 0))
            if capacity_kva <= 0:
                return False, None, f"Invalid capacity_kva: {capacity_kva}"

            # Parse date
            date_str = str(raw.get("date", "")).strip()
            # Test date parse
            datetime.date.fromisoformat(date_str)

            # Times
            start_time = str(raw.get("start_time", "")).strip()
            stop_time = str(raw.get("stop_time", "")).strip()
            mains_restored_time = str(raw.get("mains_restored_time", "")).strip()

            if not start_time or not stop_time:
                return False, None, "Missing start_time or stop_time"

            # Parse load_kw
            load_kw = float(raw.get("load_kw", 0))
            if load_kw < 0:
                return False, None, f"Negative load_kw: {load_kw}"
            # Extreme load check: > 160% of capacity in kW is physically implausible
            if load_kw > (capacity_kva * 1.6):
                return False, None, f"Physically implausible load_kw {load_kw} for capacity {capacity_kva} kVA"

            # Parse fuel
            fuel_used_litres = float(raw.get("fuel_used_litres", 0))
            if fuel_used_litres < 0:
                return False, None, f"Negative fuel_used_litres: {fuel_used_litres}"

            # Parse runtime_min
            runtime_min = float(raw.get("runtime_min", 0))
            if runtime_min <= 0:
                # Attempt to calculate from start and stop time if missing
                try:
                    t1 = datetime.datetime.strptime(start_time, "%H:%M:%S")
                    t2 = datetime.datetime.strptime(stop_time, "%H:%M:%S")
                    diff = (t2 - t1).total_seconds() / 60.0
                    if diff < 0:
                        diff += 1440.0  # crossed midnight
                    runtime_min = diff
                except Exception:
                    return False, None, "Invalid runtime_min <= 0 and times unparseable"

            # Calculate shutdown delay if mains_restored_time is present
            shutdown_delay_min = 0.0
            if mains_restored_time:
                try:
                    t_stop = datetime.datetime.strptime(stop_time, "%H:%M:%S")
                    t_mains = datetime.datetime.strptime(mains_restored_time, "%H:%M:%S")
                    diff_m = (t_stop - t_mains).total_seconds() / 60.0
                    if diff_m < -720:
                        diff_m += 1440.0
                    shutdown_delay_min = max(0.0, round(diff_m, 1))
                except Exception:
                    shutdown_delay_min = 0.0

            # Optional telemetry fields
            temp_c = None
            if raw.get("temperature_c") is not None and str(raw.get("temperature_c")).strip():
                try:
                    temp_c = round(float(raw.get("temperature_c")), 1)
                except Exception:
                    temp_c = None

            vib_mms = None
            if raw.get("vibration_mm_s") is not None and str(raw.get("vibration_mm_s")).strip():
                try:
                    vib_mms = round(float(raw.get("vibration_mm_s")), 2)
                except Exception:
                    vib_mms = None

            record_id = raw.get("record_id") or f"REC-{hash(date_str + start_time + dg_id) % 100000:05d}"

            cleaned = {
                "record_id": str(record_id),
                "dg_id": dg_id,
                "capacity_kva": round(capacity_kva, 1),
                "date": date_str,
                "start_time": start_time,
                "stop_time": stop_time,
                "mains_restored_time": mains_restored_time,
                "load_kw": round(load_kw, 2),
                "fuel_used_litres": round(fuel_used_litres, 2),
                "runtime_min": round(runtime_min, 1),
                "shutdown_delay_min": round(shutdown_delay_min, 1),
                "temperature_c": temp_c,
                "vibration_mm_s": vib_mms,
                "ground_truth_label": str(raw.get("ground_truth_label", "NORMAL")),
                "is_synthetic": str(raw.get("is_synthetic", "True (Demonstration Data)")),
                "notes": str(raw.get("notes", "Operational log record"))
            }
            return True, cleaned, None
        except Exception as e:
            return False, None, str(e)

    def get_records(
        self,
        dg_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "date",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 25
    ) -> Dict[str, Any]:
        """Filters, sorts, and paginates generator records."""
        filtered = list(self._records)

        # Filter by generator ID
        if dg_id and dg_id != "ALL":
            dg_id_upper = dg_id.strip().upper()
            filtered = [r for r in filtered if r["dg_id"] == dg_id_upper]

        # Filter by date range
        if start_date:
            filtered = [r for r in filtered if r["date"] >= start_date]
        if end_date:
            filtered = [r for r in filtered if r["date"] <= end_date]

        # Search term in id, notes, or date
        if search:
            s_lower = search.lower().strip()
            filtered = [
                r for r in filtered
                if (s_lower in r["record_id"].lower()
                    or s_lower in r["dg_id"].lower()
                    or s_lower in r["date"].lower()
                    or s_lower in r["notes"].lower())
            ]

        # Sorting
        valid_sort_keys = ["date", "runtime_min", "fuel_used_litres", "load_kw", "capacity_kva", "shutdown_delay_min"]
        sort_field = sort_by if sort_by in valid_sort_keys else "date"
        reverse = (sort_order.lower() == "desc")

        try:
            filtered.sort(key=lambda x: x[sort_field], reverse=reverse)
        except Exception:
            filtered.sort(key=lambda x: str(x[sort_field]), reverse=reverse)

        total_count = len(filtered)
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated = filtered[start_idx:end_idx]

        return {
            "records": paginated,
            "pagination": {
                "total_records": total_count,
                "current_page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    def get_all_records_filtered(
        self,
        dg_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns all matching records without pagination for charting and analytics."""
        filtered = list(self._records)
        if dg_id and dg_id != "ALL":
            dg_id_upper = dg_id.strip().upper()
            filtered = [r for r in filtered if r["dg_id"] == dg_id_upper]
        if start_date:
            filtered = [r for r in filtered if r["date"] >= start_date]
        if end_date:
            filtered = [r for r in filtered if r["date"] <= end_date]
        return filtered

    def get_generators(self) -> List[Dict[str, Any]]:
        """Returns fleet summary for each unique generator."""
        gens: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            gid = r["dg_id"]
            if gid not in gens:
                gens[gid] = {
                    "dg_id": gid,
                    "capacity_kva": r["capacity_kva"],
                    "total_runs": 0,
                    "total_runtime_min": 0.0,
                    "total_fuel_litres": 0.0,
                    "load_sum": 0.0,
                    "latest_run": r["date"],
                    "status": "Operational"
                }
            g = gens[gid]
            g["total_runs"] += 1
            g["total_runtime_min"] += r["runtime_min"]
            g["total_fuel_litres"] += r["fuel_used_litres"]
            g["load_sum"] += r["load_kw"]
            if r["date"] > g["latest_run"]:
                g["latest_run"] = r["date"]

        result = []
        for gid, g in sorted(gens.items()):
            runtime_hrs = g["total_runtime_min"] / 60.0
            avg_load = (g["load_sum"] / g["total_runs"]) if g["total_runs"] > 0 else 0
            avg_fuel_hr = (g["total_fuel_litres"] / runtime_hrs) if runtime_hrs > 0 else 0
            result.append({
                "dg_id": gid,
                "capacity_kva": g["capacity_kva"],
                "total_runs": g["total_runs"],
                "total_runtime_hours": round(runtime_hrs, 1),
                "total_fuel_litres": round(g["total_fuel_litres"], 2),
                "avg_load_kw": round(avg_load, 1),
                "avg_fuel_per_hour": round(avg_fuel_hr, 2),
                "latest_run": g["latest_run"],
                "status": "Active & Monitoring"
            })
        return result

    def get_generator_detail(self, dg_id: str) -> Optional[Dict[str, Any]]:
        """Gets detailed statistics and recent operating history for a specific DG."""
        dg_id_upper = dg_id.strip().upper()
        records = [r for r in self._records if r["dg_id"] == dg_id_upper]
        if not records:
            return None

        records.sort(key=lambda r: (r["date"], r["start_time"]), reverse=True)
        total_runs = len(records)
        total_runtime_min = sum(r["runtime_min"] for r in records)
        total_fuel = sum(r["fuel_used_litres"] for r in records)
        avg_load = sum(r["load_kw"] for r in records) / total_runs
        runtime_hrs = total_runtime_min / 60.0

        return {
            "dg_id": dg_id_upper,
            "capacity_kva": records[0]["capacity_kva"],
            "total_runs": total_runs,
            "total_runtime_hours": round(runtime_hrs, 1),
            "total_fuel_litres": round(total_fuel, 2),
            "avg_load_kw": round(avg_load, 1),
            "avg_fuel_per_hour": round(total_fuel / runtime_hrs, 2) if runtime_hrs > 0 else 0,
            "recent_records": records[:10]
        }

    def add_record(self, record_dict: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Adds a new generator record to the dataset and appends to CSV."""
        is_valid, cleaned, err = self.validate_and_clean_record(record_dict)
        if not is_valid or cleaned is None:
            return False, None, err

        self._records.append(cleaned)

        # Append to CSV
        try:
            file_exists = os.path.exists(self.csv_path)
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "record_id", "dg_id", "capacity_kva", "date", "start_time",
                    "stop_time", "mains_restored_time", "load_kw", "fuel_used_litres",
                    "runtime_min", "shutdown_delay_min", "ground_truth_label",
                    "is_synthetic", "notes"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                if not file_exists:
                    writer.writeheader()
                writer.writerow(cleaned)
        except Exception as e:
            return False, None, f"Failed writing to storage: {str(e)}"

        return True, cleaned, None

    def get_validation_report(self) -> Dict[str, Any]:
        return self._validation_report

    def get_data_quality_summary(self) -> Dict[str, Any]:
        """Returns fleet-wide data quality score and counts."""
        return self._quality_result.get("summary", {})

    def get_data_quality_issues(
        self,
        dg_id: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters detailed data quality issue ledger."""
        issues = list(self._quality_result.get("issues", []))
        if dg_id and dg_id != "ALL":
            issues = [i for i in issues if i.get("dg_id") == dg_id.upper()]
        if severity and severity != "ALL":
            issues = [i for i in issues if i.get("severity") == severity.upper()]
        if category and category != "ALL":
            issues = [i for i in issues if i.get("issue_category") == category.upper()]
        return issues

    def export_data_quality_csv(self) -> str:
        """Generates CSV text representation of all detected data quality issues."""
        issues = self._quality_result.get("issues", [])
        output = io.StringIO()
        fieldnames = ["record_id", "dg_id", "timestamp", "field_name", "issue_category", "severity", "explanation", "excluded_from_analysis"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for i in issues:
            writer.writerow({
                "record_id": i.get("record_id", ""),
                "dg_id": i.get("dg_id", ""),
                "timestamp": i.get("timestamp", ""),
                "field_name": i.get("field_name", ""),
                "issue_category": i.get("issue_category", ""),
                "severity": i.get("severity", ""),
                "explanation": i.get("explanation", ""),
                "excluded_from_analysis": i.get("excluded_from_analysis", False)
            })
        return output.getvalue()
