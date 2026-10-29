"""
Emission Service Module - Carbon Emissions Analysis
Estimates CO2 emissions based on diesel consumption using documented emission factors.
Strictly labels all outputs as model estimations rather than direct physical sensor measurements.
"""

from typing import List, Dict, Any

class EmissionService:
    def __init__(self, default_emission_factor: float = 2.68):
        """
        Default emission factor: 2.68 kg CO2 per litre of diesel.
        Reference: UK DEFRA / IPCC Guidelines for Stationary Combustion of Gas Oil / Diesel.
        """
        self.emission_factor = default_emission_factor

    def set_emission_factor(self, factor: float):
        """Updates the configurable CO2 emission factor."""
        if factor > 0:
            self.emission_factor = float(factor)

    def analyze_emissions(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes carbon emissions analysis:
        - Total estimated CO2 emissions (kg and Metric Tons)
        - Breakdown by generator
        - Daily emissions trend
        - Documentation of assumptions and methodology
        """
        if not records:
            return {
                "total_co2_kg": 0.0,
                "total_co2_tonnes": 0.0,
                "emission_factor_used": self.emission_factor,
                "methodology_disclaimer": (
                    "Notice: These figures are model estimates derived from volumetric diesel usage, "
                    "not direct physical exhaust sensor measurements."
                ),
                "by_generator": [],
                "daily_trend": []
            }

        total_diesel_litres = sum(r["fuel_used_litres"] for r in records)
        total_co2_kg = total_diesel_litres * self.emission_factor
        total_co2_tonnes = total_co2_kg / 1000.0

        # Group by generator
        gen_map: Dict[str, Dict[str, Any]] = {}
        for r in records:
            gid = r["dg_id"]
            if gid not in gen_map:
                gen_map[gid] = {
                    "dg_id": gid,
                    "capacity_kva": r["capacity_kva"],
                    "diesel_litres": 0.0
                }
            gen_map[gid]["diesel_litres"] += r["fuel_used_litres"]

        by_generator = []
        for gid, g in sorted(gen_map.items()):
            g_co2_kg = g["diesel_litres"] * self.emission_factor
            g_co2_tonnes = g_co2_kg / 1000.0
            pct = (g_co2_kg / total_co2_kg * 100.0) if total_co2_kg > 0 else 0.0
            by_generator.append({
                "dg_id": gid,
                "capacity_kva": g["capacity_kva"],
                "fuel_litres": round(g["diesel_litres"], 2),
                "co2_kg": round(g_co2_kg, 2),
                "co2_tonnes": round(g_co2_tonnes, 3),
                "share_percentage": round(pct, 1)
            })

        # Group by Date
        date_map: Dict[str, float] = {}
        for r in records:
            d = r["date"]
            date_map[d] = date_map.get(d, 0.0) + r["fuel_used_litres"]

        daily_trend = []
        for d in sorted(date_map.keys()):
            litres = date_map[d]
            co2_kg = litres * self.emission_factor
            daily_trend.append({
                "date": d,
                "diesel_litres": round(litres, 2),
                "co2_kg": round(co2_kg, 2),
                "co2_tonnes": round(co2_kg / 1000.0, 3)
            })

        # Environmental equivalence (approximate illustrative context)
        # Average urban tree absorbs ~21.77 kg CO2 per year
        tree_equivalent_years = total_co2_kg / 21.77 if total_co2_kg > 0 else 0.0

        return {
            "total_co2_kg": round(total_co2_kg, 2),
            "total_co2_tonnes": round(total_co2_tonnes, 3),
            "total_diesel_litres": round(total_diesel_litres, 2),
            "emission_factor_used": self.emission_factor,
            "unit": "kg CO2 / Litre Diesel",
            "methodology_disclaimer": (
                "Estimated using standard stoichiometric emission factors (DEFRA / IPCC Tier 1). "
                "Calculated as: Diesel Consumed (L) × Emission Factor (kg CO2/L). "
                "Actual emissions may vary depending on engine tuning, load factors, and ambient temperature."
            ),
            "illustrative_equivalence": {
                "tree_years_to_sequester": round(tree_equivalent_years, 1),
                "note": "Approximate tree-years required for biogenic absorption (demonstration metric)."
            },
            "by_generator": by_generator,
            "daily_trend": daily_trend
        }
