"""
GENIUS DG — Supabase Cloud Database Client Service
Enterprise PostgreSQL Integration via Supabase Python SDK
Author: Senior Full-Stack & Database Architect

Provides safe, authenticated database connectivity, query routing, connection
diagnostics, and resilient error recovery. Keeps all credentials strictly server-side.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("genius_dg.supabase")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [Supabase] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SupabaseService:
    """
    Manages privileged backend communication with the Supabase PostgreSQL database.
    Operates in dual-mode: connects when credentials are present, otherwise signals
    offline state so the application safely falls back to local data.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        anon_key: Optional[str] = None
    ):
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.environ.get("SUPABASE_URL", "")
        ).strip()
        # Prefer service_role key for backend operations; fallback to anon if provided
        self.service_role_key = (
            service_role_key
            if service_role_key is not None
            else (
                os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
                or (anon_key if anon_key is not None else os.environ.get("SUPABASE_ANON_KEY", ""))
            )
        ).strip()
        self.anon_key = (
            anon_key if anon_key is not None else os.environ.get("SUPABASE_ANON_KEY", "")
        ).strip()

        self._client = None
        self._last_health_check: Optional[Dict[str, Any]] = None
        self._init_client()

    def _init_client(self):
        """Initializes the official Supabase Python client if credentials are configured."""
        if not self.is_configured():
            logger.info("Supabase credentials not configured in environment. Operating in resilient local fallback mode.")
            self._client = None
            return

        try:
            from supabase import create_client, Client
            # Initialize client with backend credentials
            self._client: Optional[Client] = create_client(self.supabase_url, self.service_role_key)
            logger.info(f"Supabase client initialized successfully for target: {self._sanitize_url(self.supabase_url)}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            self._client = None

    def is_configured(self) -> bool:
        """Returns True if the required URL and secret key are set."""
        return bool(
            self.supabase_url
            and self.service_role_key
            and not self.supabase_url.startswith("https://your-project-id")
            and not self.service_role_key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-service-role")
        )

    @property
    def client(self):
        """Lazy client access."""
        if self._client is None and self.is_configured():
            self._init_client()
        return self._client

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Returns a safe representation of the URL without leaking tokens or private domains."""
        if not url:
            return "unconfigured"
        try:
            parts = url.split("://")
            host = parts[-1].split("/")[0]
            return f"https://{host}"
        except Exception:
            return "configured_url"

    def check_health(self) -> Dict[str, Any]:
        """
        Performs a non-destructive database health check and ping.
        Measures connection latency and checks table accessibility.
        Never leaks passwords, keys, or internal tokens.
        """
        url_configured = bool(self.supabase_url)
        key_configured = bool(self.service_role_key)

        if not self.is_configured():
            return {
                "connected": False,
                "status": "disconnected",
                "message": "Supabase credentials are not configured or contain placeholder values.",
                "url_configured": url_configured,
                "key_configured": key_configured,
                "latency_ms": None,
                "target_endpoint": self._sanitize_url(self.supabase_url),
                "active_data_source": "local_csv_fallback",
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        try:
            t0 = time.time()
            # Perform lightweight query on the generators table
            response = self.client.table("generators").select("generator_code").limit(5).execute()
            latency_ms = round((time.time() - t0) * 1000.0, 2)

            data = getattr(response, "data", [])
            health_info = {
                "connected": True,
                "status": "connected",
                "message": "Connected to Supabase PostgreSQL cloud database.",
                "url_configured": True,
                "key_configured": True,
                "latency_ms": latency_ms,
                "target_endpoint": self._sanitize_url(self.supabase_url),
                "active_data_source": "supabase_postgresql",
                "sample_units_available": len(data),
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._last_health_check = health_info
            return health_info

        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Database health check failed: {err_msg}")
            return {
                "connected": False,
                "status": "connection_error",
                "message": f"Database unreachable: {err_msg[:120]}",
                "url_configured": True,
                "key_configured": True,
                "latency_ms": None,
                "target_endpoint": self._sanitize_url(self.supabase_url),
                "active_data_source": "local_csv_fallback",
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    # ==========================================================================
    # 1. GENERATORS FLEET OPERATIONS
    # ==========================================================================
    def get_generators(self) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Retrieves all generator units from the cloud database."""
        if not self.is_configured() or not self.client:
            return False, [], "Supabase client not connected"
        try:
            res = self.client.table("generators").select("*").order("generator_code").execute()
            data = getattr(res, "data", []) or []
            return True, data, None
        except Exception as e:
            return False, [], str(e)

    def get_generator_by_code(self, generator_code: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Retrieves a single generator by its unique code (e.g., 'DG-101')."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            res = self.client.table("generators").select("*").eq("generator_code", generator_code.upper()).execute()
            data = getattr(res, "data", []) or []
            if data:
                return True, data[0], None
            return True, None, "Generator not found"
        except Exception as e:
            return False, None, str(e)

    def upsert_generator(self, gen_dict: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Idempotently creates or updates a generator record."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            res = self.client.table("generators").upsert(
                gen_dict, on_conflict="generator_code"
            ).execute()
            data = getattr(res, "data", [])
            return True, data[0] if data else gen_dict, None
        except Exception as e:
            return False, None, str(e)

    # ==========================================================================
    # 2. SENSOR READINGS OPERATIONS
    # ==========================================================================
    def get_all_readings(
        self,
        generator_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Retrieves unpaginated historical readings for analytics and AI models."""
        if not self.is_configured() or not self.client:
            return False, [], "Supabase client not connected"
        try:
            query = self.client.table("sensor_readings").select("*")
            if generator_code and generator_code != "ALL":
                query = query.eq("generator_code", generator_code.upper())
            if start_date:
                query = query.gte("recorded_date", start_date)
            if end_date:
                query = query.lte("recorded_date", end_date)

            res = query.order("recorded_date", desc=True).order("start_time", desc=True).execute()
            data = getattr(res, "data", []) or []
            # Normalize to match internal dictionary contracts
            normalized = [self._normalize_reading(r) for r in data]
            return True, normalized, None
        except Exception as e:
            return False, [], str(e)

    def get_readings_paginated(
        self,
        generator_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "recorded_date",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 25
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Retrieves paginated, sorted, and filtered readings."""
        if not self.is_configured() or not self.client:
            return False, {}, "Supabase client not connected"
        try:
            query = self.client.table("sensor_readings").select("*", count="exact")

            if generator_code and generator_code != "ALL":
                query = query.eq("generator_code", generator_code.upper())
            if start_date:
                query = query.gte("recorded_date", start_date)
            if end_date:
                query = query.lte("recorded_date", end_date)
            if search:
                s = search.strip()
                query = query.or_(f"record_id.ilike.%{s}%,notes.ilike.%{s}%,ground_truth_label.ilike.%{s}%")

            # Map sort field to PostgreSQL column name
            sort_map = {
                "date": "recorded_date",
                "recorded_date": "recorded_date",
                "runtime_min": "runtime_min",
                "fuel_used_litres": "fuel_used_litres",
                "load_kw": "load_kw",
                "shutdown_delay_min": "shutdown_delay_min"
            }
            col = sort_map.get(sort_by, "recorded_date")
            desc = (sort_order.lower() == "desc")

            offset = (page - 1) * per_page
            res = query.order(col, desc=desc).range(offset, offset + per_page - 1).execute()

            data = getattr(res, "data", []) or []
            total = getattr(res, "count", len(data)) or len(data)
            total_pages = max(1, (total + per_page - 1) // per_page)

            normalized = [self._normalize_reading(r) for r in data]

            return True, {
                "records": normalized,
                "pagination": {
                    "total_records": total,
                    "current_page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }, None
        except Exception as e:
            return False, {}, str(e)

    def insert_reading(self, reading_dict: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Inserts a single verified generator reading."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            db_row = self._denormalize_reading(reading_dict)
            res = self.client.table("sensor_readings").upsert(db_row, on_conflict="record_id").execute()
            data = getattr(res, "data", [])
            ret = self._normalize_reading(data[0]) if data else reading_dict
            return True, ret, None
        except Exception as e:
            return False, None, str(e)

    def upsert_readings_batch(
        self, readings_list: List[Dict[str, Any]]
    ) -> Tuple[bool, int, Optional[str]]:
        """Batch upserts sensor readings idempotently in chunks of 50."""
        if not self.is_configured() or not self.client:
            return False, 0, "Supabase client not connected"
        if not readings_list:
            return True, 0, None

        total_inserted = 0
        chunk_size = 50
        try:
            for i in range(0, len(readings_list), chunk_size):
                chunk = readings_list[i : i + chunk_size]
                db_rows = [self._denormalize_reading(r) for r in chunk]
                res = self.client.table("sensor_readings").upsert(
                    db_rows, on_conflict="record_id"
                ).execute()
                data = getattr(res, "data", [])
                total_inserted += len(data) if data else len(chunk)
            return True, total_inserted, None
        except Exception as e:
            return False, total_inserted, str(e)

    # ==========================================================================
    # 3. AI ANOMALIES PERSISTENCE
    # ==========================================================================
    def save_anomalies_batch(
        self, anomalies: List[Dict[str, Any]]
    ) -> Tuple[bool, int, Optional[str]]:
        """Persists detected AI anomalies with explainable metadata."""
        if not self.is_configured() or not self.client:
            return False, 0, "Supabase client not connected"
        if not anomalies:
            return True, 0, None

        try:
            rows = []
            for a in anomalies:
                rows.append({
                    "reading_id": a.get("record_id"),
                    "generator_code": a.get("dg_id", "DG-101"),
                    "is_anomaly": bool(a.get("is_anomaly", True)),
                    "anomaly_score": float(a.get("score", 0.0)),
                    "anomaly_severity_percent": float(a.get("anomaly_severity_percent", 0.0)),
                    "explainable_summary": a.get("explainable_summary", ""),
                    "supporting_indicators": a.get("supporting_indicators", []),
                    "comparison_context": a.get("comparison_context", {}),
                    "suggested_inspection_steps": a.get("suggested_inspection_steps", []),
                    "model_version": "IsolationForest-v2.0",
                    "data_source": "simulated"
                })

            chunk_size = 50
            total_saved = 0
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i : i + chunk_size]
                res = self.client.table("ai_anomalies").insert(chunk).execute()
                data = getattr(res, "data", [])
                total_saved += len(data) if data else len(chunk)
            return True, total_saved, None
        except Exception as e:
            return False, 0, str(e)

    # ==========================================================================
    # 4. ALERTS & NOTIFICATIONS
    # ==========================================================================
    def get_alerts(
        self,
        generator_code: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Retrieves alerts with active status management."""
        if not self.is_configured() or not self.client:
            return False, [], "Supabase client not connected"
        try:
            query = self.client.table("alerts").select("*")
            if generator_code and generator_code != "ALL":
                query = query.eq("generator_code", generator_code.upper())
            if severity and severity != "ALL":
                query = query.eq("severity", severity.upper())
            if status and status != "ALL":
                query = query.eq("status", status.upper())

            res = query.order("created_at", desc=True).limit(limit).execute()
            data = getattr(res, "data", []) or []
            return True, data, None
        except Exception as e:
            return False, [], str(e)

    def upsert_alert(self, alert_dict: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Creates or updates an operational alert."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            row = {
                "alert_id": alert_dict["alert_id"],
                "generator_code": alert_dict.get("dg_id", "DG-101"),
                "category": alert_dict.get("category", "SYSTEM"),
                "alert_type": alert_dict.get("alert_type", "ANOMALY"),
                "severity": alert_dict.get("severity", "WARNING").upper(),
                "message": alert_dict.get("description") or alert_dict.get("message", "Telemetry alert"),
                "source": alert_dict.get("source", "AI_AND_RULES"),
                "status": alert_dict.get("status", "OPEN").upper(),
                "resolution_note": alert_dict.get("resolution_note") or alert_dict.get("recommended_action")
            }
            res = self.client.table("alerts").upsert(row, on_conflict="alert_id").execute()
            data = getattr(res, "data", [])
            return True, data[0] if data else row, None
        except Exception as e:
            return False, None, str(e)

    def update_alert_status(
        self, alert_id: str, status: str, notes: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Acknowledges or resolves an alert."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            payload = {
                "status": status.upper(),
                "resolution_note": notes
            }
            if status.upper() == "ACKNOWLEDGED":
                payload["acknowledged_at"] = now_iso
            elif status.upper() == "RESOLVED":
                payload["resolved_at"] = now_iso

            res = self.client.table("alerts").update(payload).eq("alert_id", alert_id).execute()
            data = getattr(res, "data", [])
            if data:
                return True, data[0], None
            return True, {"alert_id": alert_id, "status": status.upper()}, None
        except Exception as e:
            return False, None, str(e)

    # ==========================================================================
    # 5. MAINTENANCE SCHEDULES & SERVICE LOGS
    # ==========================================================================
    def get_maintenance(
        self, generator_code: Optional[str] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Retrieves maintenance schedules and completed logs."""
        if not self.is_configured() or not self.client:
            return False, [], "Supabase client not connected"
        try:
            query = self.client.table("maintenance_records").select("*")
            if generator_code and generator_code != "ALL":
                query = query.eq("generator_code", generator_code.upper())
            res = query.order("due_date").execute()
            data = getattr(res, "data", []) or []
            # Normalize to match frontend expected fields
            normalized = []
            for m in data:
                normalized.append({
                    "id": m.get("maintenance_id"),
                    "dg_id": m.get("generator_code"),
                    "service_type": m.get("service_type"),
                    "interval_hours": float(m.get("interval_hours", 500)),
                    "last_serviced_hours": float(m.get("last_serviced_hours", 0)),
                    "current_hours": float(m.get("current_hours", 0)),
                    "hours_remaining": float(m.get("hours_remaining", 0)),
                    "due_date": str(m.get("due_date", "")),
                    "status": m.get("status", "NORMAL"),
                    "assigned_technician": m.get("assigned_technician", ""),
                    "checklist": m.get("checklist") or [],
                    "completed_at": m.get("completed_at"),
                    "notes": m.get("notes")
                })
            return True, normalized, None
        except Exception as e:
            return False, [], str(e)

    def insert_maintenance(
        self, record: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Persists a new maintenance service record."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            row = {
                "maintenance_id": record.get("id"),
                "generator_code": record.get("dg_id"),
                "service_type": record.get("service_type"),
                "interval_hours": float(record.get("interval_hours", 500)),
                "last_serviced_hours": float(record.get("last_serviced_hours", record.get("hours", 0))),
                "current_hours": float(record.get("current_hours", record.get("hours", 0))),
                "hours_remaining": float(record.get("hours_remaining", record.get("interval_hours", 500))),
                "due_date": record.get("due_date", time.strftime("%Y-%m-%d")),
                "status": record.get("status", "COMPLETED"),
                "assigned_technician": record.get("assigned_technician", record.get("technician", "Field Tech")),
                "checklist": record.get("checklist", []),
                "completed_at": record.get("completed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                "notes": record.get("notes", "")
            }
            res = self.client.table("maintenance_records").upsert(row, on_conflict="maintenance_id").execute()
            data = getattr(res, "data", [])
            return True, data[0] if data else row, None
        except Exception as e:
            return False, None, str(e)

    # ==========================================================================
    # 6. SYSTEM SETTINGS
    # ==========================================================================
    def get_settings(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Retrieves global operational configuration from database."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            res = self.client.table("system_settings").select("*").eq("id", 1).execute()
            data = getattr(res, "data", [])
            if data:
                s = data[0]
                return True, {
                    "diesel_price_per_litre": float(s.get("diesel_price_per_litre", 94.50)),
                    "currency_symbol": s.get("currency_symbol", "₹"),
                    "co2_emission_factor": float(s.get("co2_emission_factor", 2.68)),
                    "shutdown_delay_threshold_min": float(s.get("shutdown_delay_threshold_min", 10.0)),
                    "ai_contamination_rate": float(s.get("ai_contamination_rate", 0.08)),
                    "max_overload_tolerance_pct": float(s.get("max_overload_tolerance_pct", 115.0)),
                    "frozen_sensor_threshold": int(s.get("frozen_sensor_threshold", 4)),
                    "last_updated": s.get("updated_at")
                }, None
            return True, None, "Settings not found"
        except Exception as e:
            return False, None, str(e)

    def save_settings(
        self, settings_dict: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Saves operational parameters to system_settings."""
        if not self.is_configured() or not self.client:
            return False, None, "Supabase client not connected"
        try:
            row = {
                "id": 1,
                "diesel_price_per_litre": float(settings_dict.get("diesel_price_per_litre", 94.50)),
                "currency_symbol": str(settings_dict.get("currency_symbol", "₹")),
                "co2_emission_factor": float(settings_dict.get("co2_emission_factor", 2.68)),
                "shutdown_delay_threshold_min": float(settings_dict.get("shutdown_delay_threshold_min", 10.0)),
                "ai_contamination_rate": float(settings_dict.get("ai_contamination_rate", 0.08)),
                "max_overload_tolerance_pct": float(settings_dict.get("max_overload_tolerance_pct", 115.0)),
                "frozen_sensor_threshold": int(settings_dict.get("frozen_sensor_threshold", 4)),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            res = self.client.table("system_settings").upsert(row, on_conflict="id").execute()
            data = getattr(res, "data", [])
            return True, data[0] if data else row, None
        except Exception as e:
            return False, None, str(e)

    # ==========================================================================
    # HELPER MAPPERS (SCHEMA <-> APPLICATION)
    # ==========================================================================
    @staticmethod
    def _normalize_reading(db_row: Dict[str, Any]) -> Dict[str, Any]:
        """Maps PostgreSQL database row to application telemetry dictionary."""
        return {
            "record_id": str(db_row.get("record_id", "")),
            "dg_id": str(db_row.get("generator_code", "")),
            "capacity_kva": float(db_row.get("capacity_kva", 125.0)),
            "date": str(db_row.get("recorded_date", "")),
            "start_time": str(db_row.get("start_time", "")),
            "stop_time": str(db_row.get("stop_time", "")),
            "mains_restored_time": str(db_row.get("mains_restored_time") or ""),
            "load_kw": float(db_row.get("load_kw", 0.0)),
            "fuel_used_litres": float(db_row.get("fuel_used_litres", 0.0)),
            "runtime_min": float(db_row.get("runtime_min", 0.0)),
            "shutdown_delay_min": float(db_row.get("shutdown_delay_min", 0.0)),
            "temperature_c": float(db_row.get("temperature_c")) if db_row.get("temperature_c") is not None else None,
            "vibration_mm_s": float(db_row.get("vibration_mm_s")) if db_row.get("vibration_mm_s") is not None else None,
            "ground_truth_label": str(db_row.get("ground_truth_label", "NORMAL")),
            "is_synthetic": "True (Demonstration Data)" if db_row.get("is_synthetic") else "False (Field Hardware)",
            "data_source": str(db_row.get("data_source", "simulated")),
            "notes": str(db_row.get("notes", "Operational telemetry observation"))
        }

    @staticmethod
    def _denormalize_reading(app_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Maps application telemetry dictionary to PostgreSQL database schema."""
        dg_code = str(app_dict.get("dg_id", "DG-101")).strip().upper()
        cap_map = {"DG-101": 250.0, "DG-102": 125.0, "DG-103": 500.0, "DG-104": 62.5}
        cap = float(app_dict.get("capacity_kva", cap_map.get(dg_code, 125.0)))

        return {
            "record_id": str(app_dict.get("record_id", f"REC-{int(time.time() * 1000) % 1000000}")),
            "generator_code": dg_code,
            "recorded_date": str(app_dict.get("date", time.strftime("%Y-%m-%d"))),
            "start_time": str(app_dict.get("start_time", "08:00:00")),
            "stop_time": str(app_dict.get("stop_time", "09:00:00")),
            "mains_restored_time": str(app_dict.get("mains_restored_time") or "").strip() or None,
            "runtime_min": float(app_dict.get("runtime_min", 60.0)),
            "load_kw": float(app_dict.get("load_kw", 0.0)),
            "fuel_used_litres": float(app_dict.get("fuel_used_litres", 0.0)),
            "shutdown_delay_min": float(app_dict.get("shutdown_delay_min", 0.0)),
            "temperature_c": float(app_dict.get("temperature_c")) if app_dict.get("temperature_c") is not None else None,
            "vibration_mm_s": float(app_dict.get("vibration_mm_s")) if app_dict.get("vibration_mm_s") is not None else None,
            "ground_truth_label": str(app_dict.get("ground_truth_label", "NORMAL")),
            "is_synthetic": True,
            "data_source": "simulated",
            "notes": str(app_dict.get("notes", "Operational telemetry observation"))
        }
