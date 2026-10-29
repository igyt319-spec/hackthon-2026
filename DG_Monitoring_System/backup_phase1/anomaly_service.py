"""
AI Anomaly Detection and Rule-Based Verification Service
College Mini-Project: AI-Powered Diesel Generator Usage Monitoring System

Dual-Engine Architecture:
- Primary Engine: Scikit-learn Isolation Forest (when binary C-extensions are permitted)
- Resilient Pure-Python Engine: Complete implementation of Liu, Ting & Zhou (IEEE 2008)
  Isolation Forest algorithm (handles environments where Windows AppLocker / WDAC
  restricts external compiled DLLs).
- Feature preparation: runtime_min, fuel_used_litres, load_kw, capacity_kva,
  plus derived engineering features (fuel_per_hour, load_factor).
- Pinpoints triggering variables that warrant human inspection.
- Evaluates model performance (Precision, Recall, F1, Confusion Matrix).
- Separately implements deterministic rule-based checks for generator shutdown delays.
"""

import math
import random
from typing import List, Dict, Any, Optional, Tuple

# Attempt to load Scikit-Learn if environment allows native DLL execution
SKLEARN_AVAILABLE = False
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
    SKLEARN_AVAILABLE = True
except (ImportError, Exception):
    SKLEARN_AVAILABLE = False


# ============================================================================
# PURE-PYTHON ISOLATION FOREST IMPLEMENTATION (Liu, Ting, Zhou - IEEE ICDM 2008)
# ============================================================================

class IsolationTreeNode:
    def __init__(self, left=None, right=None, split_feature=None, split_val=None, size=1):
        self.left = left
        self.right = right
        self.split_feature = split_feature
        self.split_val = split_val
        self.size = size  # Number of instances at leaf
        self.is_leaf = (left is None and right is None)

def _c(n: int) -> float:
    """Average path length of unsuccessful search in BST for sample size n."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    euler_mascheroni = 0.5772156649
    return 2.0 * (math.log(n - 1) + euler_mascheroni) - (2.0 * (n - 1) / n)

class IsolationTree:
    def __init__(self, max_height: int):
        self.max_height = max_height
        self.root: Optional[IsolationTreeNode] = None

    def fit(self, X: List[List[float]], current_height: int = 0) -> IsolationTreeNode:
        n_samples = len(X)
        if n_samples <= 1 or current_height >= self.max_height:
            return IsolationTreeNode(size=n_samples)

        n_features = len(X[0])
        # Randomly select a feature
        feature_idx = random.randint(0, n_features - 1)
        feat_vals = [row[feature_idx] for row in X]
        min_v = min(feat_vals)
        max_v = max(feat_vals)

        if min_v == max_v:
            return IsolationTreeNode(size=n_samples)

        # Random split point between min and max
        split_val = random.uniform(min_v, max_v)

        left_X = [row for row in X if row[feature_idx] < split_val]
        right_X = [row for row in X if row[feature_idx] >= split_val]

        if not left_X or not right_X:
            return IsolationTreeNode(size=n_samples)

        left_node = self.fit(left_X, current_height + 1)
        right_node = self.fit(right_X, current_height + 1)

        return IsolationTreeNode(
            left=left_node,
            right=right_node,
            split_feature=feature_idx,
            split_val=split_val,
            size=n_samples
        )

    def path_length(self, x: List[float], node: IsolationTreeNode, current_depth: int = 0) -> float:
        if node.is_leaf:
            return current_depth + _c(node.size)
        feat_idx = node.split_feature
        if x[feat_idx] < node.split_val:
            return self.path_length(x, node.left, current_depth + 1)
        else:
            return self.path_length(x, node.right, current_depth + 1)

class PurePythonIsolationForest:
    def __init__(self, n_estimators: int = 100, contamination: float = 0.08, random_state: int = 42):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.trees: List[IsolationTree] = []
        self.threshold: float = 0.5
        self.sample_size: int = 256

    def fit(self, X: List[List[float]]):
        random.seed(self.random_state)
        n_samples = len(X)
        self.sample_size = min(n_samples, 256)
        max_height = math.ceil(math.log2(max(self.sample_size, 2)))
        self.trees = []

        for _ in range(self.n_estimators):
            # Subsample
            if n_samples > self.sample_size:
                subsample = random.sample(X, self.sample_size)
            else:
                subsample = list(X)
            tree = IsolationTree(max_height)
            tree.root = tree.fit(subsample)
            self.trees.append(tree)

        # Compute anomaly scores for training set to determine threshold
        scores = self.compute_anomaly_scores(X)
        sorted_scores = sorted(scores)
        # Contamination percentile cutoff
        cutoff_idx = int(len(sorted_scores) * (1.0 - self.contamination))
        cutoff_idx = max(0, min(cutoff_idx, len(sorted_scores) - 1))
        self.threshold = sorted_scores[cutoff_idx]
        return self

    def compute_anomaly_scores(self, X: List[List[float]]) -> List[float]:
        n_samples = len(X)
        c_factor = _c(self.sample_size)
        if c_factor <= 0:
            c_factor = 1.0

        scores = []
        for x in X:
            avg_path = sum(t.path_length(x, t.root) for t in self.trees) / len(self.trees)
            # Anomaly score formula: s = 2 ^ (- avg_path / c)
            score = 2.0 ** (- avg_path / c_factor)
            scores.append(score)
        return scores

    def predict(self, X: List[List[float]]) -> List[int]:
        scores = self.compute_anomaly_scores(X)
        # Returns 1 for normal, -1 for anomaly (matching Scikit-learn API)
        return [-1 if s >= self.threshold else 1 for s in scores]


# ============================================================================
# ANOMALY SERVICE MODULE
# ============================================================================

class AnomalyService:
    def __init__(
        self,
        contamination: float = 0.08,
        shutdown_delay_threshold_min: float = 10.0,
        diesel_price: float = 94.50
    ):
        self.contamination = contamination
        self.shutdown_delay_threshold_min = shutdown_delay_threshold_min
        self.diesel_price = diesel_price
        self.feature_names = [
            "runtime_min",
            "fuel_used_litres",
            "load_kw",
            "capacity_kva",
            "fuel_per_hour",
            "load_factor"
        ]
        self._last_metrics: Dict[str, Any] = {}
        self._is_trained = False
        self._means: List[float] = []
        self._stds: List[float] = []

        # Model instances
        self.sklearn_model = None
        self.sklearn_scaler = None
        self.pure_model: Optional[PurePythonIsolationForest] = None
        self.active_engine = "Scikit-Learn IsolationForest" if SKLEARN_AVAILABLE else "Pure-Python IsolationForest (Liu et al. 2008)"

    def set_config(
        self,
        contamination: Optional[float] = None,
        shutdown_delay_threshold_min: Optional[float] = None,
        diesel_price: Optional[float] = None
    ):
        if contamination is not None and 0.01 <= contamination <= 0.30:
            self.contamination = float(contamination)
        if shutdown_delay_threshold_min is not None and shutdown_delay_threshold_min >= 0:
            self.shutdown_delay_threshold_min = float(shutdown_delay_threshold_min)
        if diesel_price is not None and diesel_price > 0:
            self.diesel_price = float(diesel_price)

    def _extract_feature_rows(self, records: List[Dict[str, Any]]) -> List[List[float]]:
        """Extracts engineered numerical feature vector for each record."""
        rows = []
        for r in records:
            runtime = float(r.get("runtime_min", 60.0))
            fuel = float(r.get("fuel_used_litres", 10.0))
            load = float(r.get("load_kw", 50.0))
            capacity = float(r.get("capacity_kva", 125.0))

            runtime_hrs = max(runtime / 60.0, 0.1)
            fuel_per_hour = fuel / runtime_hrs

            nominal_prime_kw = max(capacity * 0.8, 10.0)
            load_factor = load / nominal_prime_kw

            rows.append([runtime, fuel, load, capacity, fuel_per_hour, load_factor])
        return rows

    def train(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Trains Isolation Forest model on representative records."""
        if not records or len(records) < 10:
            return {
                "status": "error",
                "message": "Insufficient records to train Isolation Forest (minimum 10 required)."
            }

        X = self._extract_feature_rows(records)
        n_features = len(self.feature_names)

        # Calculate fleet feature means and standard deviations
        self._means = [sum(row[j] for row in X) / len(X) for j in range(n_features)]
        self._stds = []
        for j in range(n_features):
            variance = sum((row[j] - self._means[j]) ** 2 for row in X) / len(X)
            self._stds.append(max(math.sqrt(variance), 1e-4))

        # Train with Scikit-learn if available, otherwise pure Python engine
        trained_with_sklearn = False
        if SKLEARN_AVAILABLE:
            try:
                self.sklearn_scaler = StandardScaler()
                X_scaled = self.sklearn_scaler.fit_transform(X)
                self.sklearn_model = IsolationForest(
                    n_estimators=100,
                    contamination=self.contamination,
                    random_state=42
                )
                self.sklearn_model.fit(X_scaled)
                trained_with_sklearn = True
                self.active_engine = "Scikit-Learn IsolationForest"
            except Exception:
                trained_with_sklearn = False

        if not trained_with_sklearn:
            self.pure_model = PurePythonIsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=42
            )
            self.pure_model.fit(X)
            self.active_engine = "Pure-Python IsolationForest (Liu et al. 2008)"

        self._is_trained = True

        # Evaluate on training records
        detection_res = self.detect_anomalies(records)
        preds = [1 if r["ai_status"] == "NORMAL" else -1 for r in detection_res["records"]]

        # Ground truth evaluation metrics
        evaluation = {"has_ground_truth": False, "metrics": None}
        has_labels = any("ground_truth_label" in r for r in records)

        if has_labels:
            tp, fp, tn, fn = 0, 0, 0, 0
            for idx, r in enumerate(records):
                is_true_anomaly = r.get("ground_truth_label") in ["EXCESSIVE_FUEL", "OVERLOAD", "UNDERLOAD"]
                y_true = -1 if is_true_anomaly else 1
                y_p = preds[idx]

                if y_true == -1 and y_p == -1:
                    tp += 1
                elif y_true == 1 and y_p == -1:
                    fp += 1
                elif y_true == 1 and y_p == 1:
                    tn += 1
                elif y_true == -1 and y_p == 1:
                    fn += 1

            precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            evaluation = {
                "has_ground_truth": True,
                "metrics": {
                    "precision": round(precision, 3),
                    "recall": round(recall, 3),
                    "f1_score": round(f1, 3),
                    "true_negatives_normal": tn,
                    "false_positives_flagged": fp,
                    "false_negatives_missed": fn,
                    "true_positives_detected": tp
                }
            }

        anomalies_count = sum(1 for p in preds if p == -1)
        normal_count = len(records) - anomalies_count

        self._last_metrics = {
            "engine": self.active_engine,
            "trained_records_count": len(records),
            "contamination_parameter": self.contamination,
            "features_used": self.feature_names,
            "anomalies_detected_count": anomalies_count,
            "normal_records_count": normal_count,
            "evaluation": evaluation
        }

        return {
            "status": "success",
            "message": f"Isolation Forest successfully trained on {len(records)} records using {self.active_engine}.",
            "metrics": self._last_metrics
        }

    def detect_anomalies(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs anomaly detection on records.
        Returns detailed results including anomaly status, score,
        and specific triggering variables that warrant human inspection.
        """
        if not records:
            return {
                "records": [],
                "anomalies_only": [],
                "summary": {"total": 0, "anomalies": 0, "normal": 0, "anomaly_rate_percent": 0.0},
                "model_metrics": self._last_metrics
            }

        if not self._is_trained or (self.sklearn_model is None and self.pure_model is None):
            self.train(records)

        X = self._extract_feature_rows(records)

        # Get predictions and raw scores
        if self.sklearn_model is not None and self.sklearn_scaler is not None:
            try:
                X_scaled = self.sklearn_scaler.transform(X)
                preds = self.sklearn_model.predict(X_scaled)
                raw_scores = self.sklearn_model.decision_function(X_scaled)
            except Exception:
                # Fallback to pure model
                if self.pure_model is None:
                    self.pure_model = PurePythonIsolationForest(contamination=self.contamination)
                    self.pure_model.fit(X)
                preds = self.pure_model.predict(X)
                raw_scores = self.pure_model.compute_anomaly_scores(X)
        else:
            if self.pure_model is None:
                self.pure_model = PurePythonIsolationForest(contamination=self.contamination)
                self.pure_model.fit(X)
            preds = self.pure_model.predict(X)
            raw_scores = self.pure_model.compute_anomaly_scores(X)

        enriched_records = []
        anomaly_list = []

        means = self._means if self._means else [sum(row[j] for row in X)/len(X) for j in range(len(self.feature_names))]
        stds = self._stds if self._stds else [1.0] * len(self.feature_names)

        for idx, rec in enumerate(records):
            is_anomaly = bool(preds[idx] == -1)
            raw_s = float(raw_scores[idx])

            # Severity computation
            if self.sklearn_model is not None:
                # Scikit-learn: decision_function negative is anomaly
                severity = max(0.0, min(100.0, round((0.15 - raw_s) * 160.0, 1))) if is_anomaly else 0.0
            else:
                # Pure-Python: score ranges 0.0 to 1.0; > threshold is anomaly
                severity = max(0.0, min(100.0, round(raw_s * 100.0, 1))) if is_anomaly else 0.0

            # Feature deviation analysis
            trigger_factors = []
            fuel_rate = X[idx][4]
            load_factor = X[idx][5]
            load_kw = X[idx][2]
            cap_kva = X[idx][3]

            z_fuel_rate = (fuel_rate - means[4]) / stds[4] if stds[4] > 0 else 0
            z_runtime = (X[idx][0] - means[0]) / stds[0] if stds[0] > 0 else 0

            if z_fuel_rate > 1.6:
                trigger_factors.append(f"Elevated fuel rate ({fuel_rate:.1f} L/h vs fleet avg {means[4]:.1f} L/h)")
            if load_factor > 1.05:
                trigger_factors.append(f"Operating overload ({load_kw:.0f} kW on {cap_kva:.0f} kVA DG, {load_factor*100:.0f}% rating)")
            elif load_factor < 0.22:
                trigger_factors.append(f"Underloaded wet-stacking risk ({load_factor*100:.0f}% rating)")
            if abs(z_runtime) > 2.0:
                trigger_factors.append(f"Atypical run duration ({X[idx][0]:.0f} min)")

            if not trigger_factors and is_anomaly:
                trigger_factors.append("Multivariate anomaly correlation across fuel, load, and runtime")

            rec_aug = dict(rec)
            rec_aug["ai_status"] = "ANOMALY" if is_anomaly else "NORMAL"
            rec_aug["is_anomaly"] = is_anomaly
            rec_aug["anomaly_score"] = round(raw_s, 4)
            rec_aug["anomaly_severity_percent"] = severity
            rec_aug["fuel_per_hour"] = round(fuel_rate, 2)
            rec_aug["load_factor"] = round(load_factor, 2)
            rec_aug["trigger_reasons"] = trigger_factors
            rec_aug["investigation_note"] = (
                "Notice: Statistical multivariate anomaly flagged for operator review. "
                "Does not constitute confirmed mechanical failure or fuel theft."
                if is_anomaly else "Operating within normal baseline distribution."
            )

            enriched_records.append(rec_aug)
            if is_anomaly:
                anomaly_list.append(rec_aug)

        anomalies_count = len(anomaly_list)
        normal_count = len(records) - anomalies_count

        return {
            "records": enriched_records,
            "anomalies_only": anomaly_list,
            "summary": {
                "total": len(records),
                "anomalies": anomalies_count,
                "normal": normal_count,
                "anomaly_rate_percent": round((anomalies_count / len(records)) * 100.0, 1) if records else 0.0
            },
            "model_metrics": self._last_metrics
        }

    def check_shutdown_delays(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deterministic Rule-Based Evaluation:
        Checks for post-mains restoration shutdown delays.
        Kept strictly distinct from AI Isolation Forest anomalies.
        """
        delay_alerts = []

        for rec in records:
            delay = float(rec.get("shutdown_delay_min", 0.0))
            if delay >= self.shutdown_delay_threshold_min:
                runtime = float(rec.get("runtime_min", 1.0))
                fuel_used = float(rec.get("fuel_used_litres", 0.0))

                burn_rate_per_min = (fuel_used / runtime) if runtime > 0 else 0.0
                avoidable_litres = round(burn_rate_per_min * delay, 2)
                avoidable_cost = round(avoidable_litres * self.diesel_price, 2)

                if delay >= 45:
                    severity = "CRITICAL"
                elif delay >= 20:
                    severity = "HIGH"
                else:
                    severity = "MEDIUM"

                alert = {
                    "alert_id": f"DELAY-{rec['record_id']}",
                    "record_id": rec["record_id"],
                    "dg_id": rec["dg_id"],
                    "date": rec["date"],
                    "stop_time": rec["stop_time"],
                    "mains_restored_time": rec["mains_restored_time"],
                    "delay_minutes": delay,
                    "threshold_minutes": self.shutdown_delay_threshold_min,
                    "estimated_avoidable_fuel_litres": avoidable_litres,
                    "estimated_avoidable_cost": avoidable_cost,
                    "alert_type": "RULE_BASED_SHUTDOWN_DELAY",
                    "severity": severity,
                    "description": (
                        f"Generator {rec['dg_id']} continued running for {delay:.0f} minutes after grid "
                        f"mains was restored at {rec['mains_restored_time']}."
                    ),
                    "recommended_action": (
                        "Inspect automatic mains failure (AMF) panel timer or instruct operators "
                        "to initiate normal cool-down shutdown within 5-10 minutes of grid restoration."
                    )
                }
                delay_alerts.append(alert)

        delay_alerts.sort(key=lambda x: (x["date"], x["delay_minutes"]), reverse=True)
        return delay_alerts

    def get_unified_alerts(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combines AI Anomaly detections and Rule-Based Shutdown Delay alerts
        into a unified, prioritized alert feed.
        """
        detection_res = self.detect_anomalies(records)
        anomalies = detection_res["anomalies_only"]
        delays = self.check_shutdown_delays(records)

        unified = []

        for anom in anomalies:
            severity = "HIGH" if anom["anomaly_severity_percent"] > 60 else "MEDIUM"
            triggers_str = "; ".join(anom.get("trigger_reasons", [])) or "Operational deviation"

            unified.append({
                "alert_id": f"AI-{anom['record_id']}",
                "record_id": anom["record_id"],
                "dg_id": anom["dg_id"],
                "date": anom["date"],
                "time": anom["start_time"],
                "alert_type": "AI_ANOMALY_DETECTION",
                "severity": severity,
                "description": f"AI Isolation Forest flagged unusual pattern: {triggers_str}.",
                "recommended_action": (
                    "Review generator log sheet, inspect fuel flow sensors, and check "
                    "air/fuel filters and injector calibration if repeated."
                ),
                "ai_score": anom.get("anomaly_score"),
                "ai_severity_percent": anom.get("anomaly_severity_percent")
            })

        for d in delays:
            unified.append({
                "alert_id": d["alert_id"],
                "record_id": d["record_id"],
                "dg_id": d["dg_id"],
                "date": d["date"],
                "time": d["mains_restored_time"],
                "alert_type": "RULE_BASED_SHUTDOWN_DELAY",
                "severity": d["severity"],
                "description": d["description"],
                "recommended_action": d["recommended_action"],
                "delay_minutes": d["delay_minutes"],
                "estimated_avoidable_fuel_litres": d["estimated_avoidable_fuel_litres"],
                "estimated_avoidable_cost": d["estimated_avoidable_cost"]
            })

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        unified.sort(key=lambda a: (a["date"], -severity_order.get(a["severity"], 4)), reverse=True)
        return unified
