"""
Fuel Service Module - Fuel Consumption and Cost Analysis
Calculates fuel totals, fleet distribution, consumption trends, and cost estimations.
Includes clear labeling of illustrative savings scenarios.
"""

from typing import List, Dict, Any, Optional

class FuelService:
    def __init__(self, default_diesel_price_per_litre: float = 94.50, currency_symbol: str = "₹"):
        self.diesel_price_per_litre = default_diesel_price_per_litre
        self.currency_symbol = currency_symbol

    def set_diesel_price(self, price: float, currency: Optional[str] = None):
        """Updates configurable diesel price per litre."""
        if price > 0:
            self.diesel_price_per_litre = float(price)
        if currency:
            self.currency_symbol = currency

    def analyze_fuel(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes comprehensive fuel analytics:
        - Total fuel consumed (litres)
        - Estimated total fuel cost
        - Fuel consumption by generator
        - Fuel consumption by date (trend)
        - Average consumption per runtime hour
        - Illustrative fuel wastage during shutdown delays
        """
        if not records:
            return {
                "total_fuel_litres": 0.0,
                "total_cost": 0.0,
                "price_per_litre": self.diesel_price_per_litre,
                "currency": self.currency_symbol,
                "avg_consumption_per_hour": 0.0,
                "by_generator": [],
                "daily_trend": [],
                "illustrative_delay_wastage": {
                    "total_delay_minutes": 0,
                    "estimated_avoidable_fuel_litres": 0.0,
                    "estimated_avoidable_cost": 0.0,
                    "label": "Illustrative Demonstration Scenario Only"
                }
            }

        total_fuel = sum(r["fuel_used_litres"] for r in records)
        total_runtime_min = sum(r["runtime_min"] for r in records)
        total_runtime_hours = total_runtime_min / 60.0 if total_runtime_min > 0 else 0.0
        avg_per_hour = (total_fuel / total_runtime_hours) if total_runtime_hours > 0 else 0.0

        total_cost = total_fuel * self.diesel_price_per_litre

        # Group by Generator
        gen_map: Dict[str, Dict[str, Any]] = {}
        for r in records:
            gid = r["dg_id"]
            if gid not in gen_map:
                gen_map[gid] = {
                    "dg_id": gid,
                    "capacity_kva": r["capacity_kva"],
                    "fuel_litres": 0.0,
                    "runtime_min": 0.0,
                    "runs_count": 0
                }
            gen_map[gid]["fuel_litres"] += r["fuel_used_litres"]
            gen_map[gid]["runtime_min"] += r["runtime_min"]
            gen_map[gid]["runs_count"] += 1

        by_generator = []
        for gid, g in sorted(gen_map.items()):
            g_runtime_hrs = g["runtime_min"] / 60.0
            g_cost = g["fuel_litres"] * self.diesel_price_per_litre
            pct = (g["fuel_litres"] / total_fuel * 100.0) if total_fuel > 0 else 0.0
            avg_rate = (g["fuel_litres"] / g_runtime_hrs) if g_runtime_hrs > 0 else 0.0

            by_generator.append({
                "dg_id": gid,
                "capacity_kva": g["capacity_kva"],
                "fuel_litres": round(g["fuel_litres"], 2),
                "cost": round(g_cost, 2),
                "share_percentage": round(pct, 1),
                "runtime_hours": round(g_runtime_hrs, 1),
                "avg_litres_per_hour": round(avg_rate, 2),
                "runs_count": g["runs_count"]
            })

        # Group by Date (Chronological trend)
        date_map: Dict[str, Dict[str, float]] = {}
        for r in records:
            d = r["date"]
            if d not in date_map:
                date_map[d] = {"fuel_litres": 0.0, "runtime_min": 0.0}
            date_map[d]["fuel_litres"] += r["fuel_used_litres"]
            date_map[d]["runtime_min"] += r["runtime_min"]

        daily_trend = []
        for d in sorted(date_map.keys()):
            f_litres = date_map[d]["fuel_litres"]
            daily_trend.append({
                "date": d,
                "fuel_litres": round(f_litres, 2),
                "cost": round(f_litres * self.diesel_price_per_litre, 2),
                "runtime_hours": round(date_map[d]["runtime_min"] / 60.0, 1)
            })

        # Illustrative analysis for shutdown delay wastage
        # Calculate fuel burnt during delay after mains restoration
        total_delay_min = 0.0
        avoidable_fuel = 0.0
        for r in records:
            delay = r.get("shutdown_delay_min", 0.0)
            runtime = r.get("runtime_min", 1.0)
            if delay > 0 and runtime > 0:
                total_delay_min += delay
                # Estimated fuel rate for this specific run
                rate_per_min = r["fuel_used_litres"] / runtime
                avoidable_fuel += (rate_per_min * delay)

        avoidable_cost = avoidable_fuel * self.diesel_price_per_litre

        return {
            "total_fuel_litres": round(total_fuel, 2),
            "total_cost": round(total_cost, 2),
            "price_per_litre": self.diesel_price_per_litre,
            "currency": self.currency_symbol,
            "avg_consumption_per_hour": round(avg_per_hour, 2),
            "total_runtime_hours": round(total_runtime_hours, 1),
            "by_generator": by_generator,
            "daily_trend": daily_trend,
            "illustrative_delay_wastage": {
                "total_delay_minutes": round(total_delay_min, 1),
                "estimated_avoidable_fuel_litres": round(avoidable_fuel, 2),
                "estimated_avoidable_cost": round(avoidable_cost, 2),
                "label": "Illustrative Scenario Estimate (Based on Post-Restoration Run Delays)",
                "note": "This estimation represents hypothetical fuel savings if generators were disconnected immediately upon grid restoration."
            }
        }
