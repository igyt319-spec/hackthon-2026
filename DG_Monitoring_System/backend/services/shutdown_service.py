"""
Mains Restoration and Generator Shutdown Delay Intelligence Service
College Mini-Project: AI-Powered Diesel Generator Usage Monitoring System

Calculates and monitors generator operating time after mains grid restoration.
Provides event timelines, avoidable fuel/cost calculations, and handles
ongoing estimated delays for actively running generators.
"""

import datetime
from typing import List, Dict, Any, Optional, Tuple


class ShutdownService:
    def __init__(self, threshold_minutes: float = 10.0, diesel_price: float = 94.50):
        self.threshold_minutes = threshold_minutes
        self.diesel_price = diesel_price

    def set_config(self, threshold_minutes: Optional[float] = None, diesel_price: Optional[float] = None):
        if threshold_minutes is not None and threshold_minutes >= 0:
            self.threshold_minutes = float(threshold_minutes)
        if diesel_price is not None and diesel_price > 0:
            self.diesel_price = float(diesel_price)

    @staticmethod
    def _parse_time(time_str: str) -> Optional[datetime.time]:
        """Safely parses HH:MM:SS or HH:MM time strings."""
        if not time_str or not str(time_str).strip():
            return None
        cleaned = str(time_str).strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.datetime.strptime(cleaned, fmt).time()
            except ValueError:
                continue
        return None

    def analyze_shutdown_delays(
        self,
        records: List[Dict[str, Any]],
        active_generator_states: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes generator shutdown delays across historic records and active states.
        Returns:
            - summary: total events analyzed, delay events count, avoidable fuel & cost
            - events: detailed list with full event timelines and quality flags
            - ongoing_delays: estimated ongoing delays for running units
            - threshold_minutes: configured delay threshold
        """
        events = []
        total_delay_minutes = 0.0
        total_avoidable_fuel = 0.0
        total_avoidable_cost = 0.0
        exceeded_count = 0
        inconsistent_count = 0
        missing_timestamp_count = 0

        for r in records:
            rec_id = str(r.get("record_id", "REC-UNKNOWN"))
            dg_id = str(r.get("dg_id", "DG-UNKNOWN"))
            date_str = str(r.get("date", ""))
            start_str = str(r.get("start_time", ""))
            stop_str = str(r.get("stop_time", ""))
            mains_str = str(r.get("mains_restored_time", ""))
            runtime_min = float(r.get("runtime_min", 0.0))
            fuel_used = float(r.get("fuel_used_litres", 0.0))

            t_start = self._parse_time(start_str)
            t_stop = self._parse_time(stop_str)
            t_mains = self._parse_time(mains_str)

            # Check for missing timestamps
            if not t_stop or not t_mains:
                missing_timestamp_count += 1
                events.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "date": date_str,
                    "start_time": start_str,
                    "stop_time": stop_str or "Missing",
                    "mains_restored_time": mains_str or "Missing",
                    "shutdown_delay_min": None,
                    "delay_status": "INSUFFICIENT_TIMESTAMP_DATA",
                    "exceeds_threshold": False,
                    "quality_note": "Insufficient timestamp data: stop time or mains restored time missing.",
                    "timeline": {
                        "mains_power_lost": start_str or "Unknown",
                        "generator_started": start_str or "Unknown",
                        "mains_power_restored": mains_str or "Missing",
                        "generator_stopped": stop_str or "Missing"
                    },
                    "avoidable_fuel_litres": 0.0,
                    "avoidable_cost": 0.0
                })
                continue

            # Compute difference in minutes
            dt_dummy = datetime.date(2026, 1, 1)
            dt_stop = datetime.datetime.combine(dt_dummy, t_stop)
            dt_mains = datetime.datetime.combine(dt_dummy, t_mains)

            diff_sec = (dt_stop - dt_mains).total_seconds()
            # Handle midnight crossing (if stop is 00:15 and mains restored was 23:55)
            if diff_sec < -72000:  # ~20+ hours negative indicates midnight crossover
                diff_sec += 86400

            delay_min = diff_sec / 60.0

            # Inconsistent timestamps: stop earlier than mains restoration
            if delay_min < 0:
                inconsistent_count += 1
                events.append({
                    "record_id": rec_id,
                    "dg_id": dg_id,
                    "date": date_str,
                    "start_time": start_str,
                    "stop_time": stop_str,
                    "mains_restored_time": mains_str,
                    "shutdown_delay_min": None,
                    "delay_status": "INCONSISTENT_TIMESTAMPS",
                    "exceeds_threshold": False,
                    "quality_note": f"Inconsistent timestamps: generator stop ({stop_str}) earlier than mains restoration ({mains_str}). Review data source.",
                    "timeline": {
                        "mains_power_lost": start_str,
                        "generator_started": start_str,
                        "mains_power_restored": mains_str,
                        "generator_stopped": stop_str
                    },
                    "avoidable_fuel_litres": 0.0,
                    "avoidable_cost": 0.0
                })
                continue

            # Valid positive or zero delay
            delay_min_rounded = round(delay_min, 1)
            exceeds = (delay_min_rounded > self.threshold_minutes)

            avoidable_fuel = 0.0
            avoidable_cost = 0.0
            if exceeds and runtime_min > 0:
                fuel_rate_per_min = fuel_used / runtime_min
                avoidable_fuel = round(fuel_rate_per_min * (delay_min_rounded - self.threshold_minutes), 2)
                avoidable_cost = round(avoidable_fuel * self.diesel_price, 2)
                exceeded_count += 1
                total_delay_minutes += delay_min_rounded
                total_avoidable_fuel += avoidable_fuel
                total_avoidable_cost += avoidable_cost

            # Construct timeline estimation
            timeline = {
                "mains_power_lost": start_str,
                "generator_started": start_str,
                "mains_power_restored": mains_str,
                "generator_stopped": stop_str
            }

            events.append({
                "record_id": rec_id,
                "dg_id": dg_id,
                "date": date_str,
                "start_time": start_str,
                "stop_time": stop_str,
                "mains_restored_time": mains_str,
                "shutdown_delay_min": delay_min_rounded,
                "threshold_min": self.threshold_minutes,
                "delay_status": "EXCESS_DELAY" if exceeds else "NORMAL_COOLDOWN",
                "exceeds_threshold": exceeds,
                "quality_note": (
                    f"Generator ran for {delay_min_rounded:.0f} min post-restoration (threshold: {self.threshold_minutes:.0f} min)."
                    if exceeds else "Cooldown shutdown completed within configured threshold window."
                ),
                "timeline": timeline,
                "avoidable_fuel_litres": avoidable_fuel,
                "avoidable_cost": avoidable_cost
            })

        # Sort events chronologically descending
        events.sort(key=lambda x: (x["date"], x.get("start_time", "")), reverse=True)

        # 2. Check for Ongoing Delays in actively running generators
        ongoing_delays = []
        if active_generator_states:
            now_time = datetime.datetime.now()
            for gen in active_generator_states:
                if gen.get("running_status") == "Running" and gen.get("mains_status") == "RESTORED":
                    mains_res_str = gen.get("mains_restored_time")
                    t_m = self._parse_time(mains_res_str)
                    if t_m:
                        dt_m = datetime.datetime.combine(now_time.date(), t_m)
                        elapsed_min = max(0.0, (now_time - dt_m).total_seconds() / 60.0)
                        if elapsed_min > self.threshold_minutes:
                            ongoing_delays.append({
                                "dg_id": gen["dg_id"],
                                "mains_restored_time": mains_res_str,
                                "elapsed_delay_min": round(elapsed_min, 1),
                                "threshold_min": self.threshold_minutes,
                                "status": "ONGOING_EXCESS_RUN",
                                "label": "Ongoing estimated delay (Generator still running)",
                                "recommended_action": "Initiate AMF cool-down cycle or check automatic transfer switch."
                            })

        return {
            "summary": {
                "total_events_analyzed": len(records),
                "excess_delay_events_count": exceeded_count,
                "inconsistent_timestamp_count": inconsistent_count,
                "missing_timestamp_count": missing_timestamp_count,
                "total_avoidable_fuel_litres": round(total_avoidable_fuel, 2),
                "total_avoidable_cost": round(total_avoidable_cost, 2),
                "configured_threshold_min": self.threshold_minutes,
                "active_ongoing_delays_count": len(ongoing_delays)
            },
            "events": events,
            "ongoing_delays": ongoing_delays
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
    records = ds.get_all_records_filtered()
    svc = ShutdownService(threshold_minutes=10.0, diesel_price=94.50)
    active_states = [
        {"dg_id": "DG-101", "running_status": "Running", "mains_status": "RESTORED", "mains_restored_time": "11:20:00"},
        {"dg_id": "DG-102", "running_status": "Standby", "mains_status": "NORMAL", "mains_restored_time": None}
    ]
    res = svc.analyze_shutdown_delays(records, active_states)
    s = res["summary"]

    print("\n=======================================================")
    print(" GENIUS DG - MAINS RESTORATION & SHUTDOWN DELAYS")
    print("=======================================================")
    print(f" Total Events Checked   : {s['total_events_analyzed']}")
    print(f" Excess Delay Incidents : {s['excess_delay_events_count']}")
    print(f" Configured Threshold   : {s['configured_threshold_min']} min")
    print(f" Avoidable Diesel Wasted: {s['total_avoidable_fuel_litres']:,.1f} Litres")
    print(f" Avoidable Financial Loss: INR {s['total_avoidable_cost']:,.2f}")
    print(f" Ongoing Running Delays : {s['active_ongoing_delays_count']}")
    print("=======================================================\n")
