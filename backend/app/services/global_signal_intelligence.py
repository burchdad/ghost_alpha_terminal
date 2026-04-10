from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Iterable


class GlobalSignalIntelligenceService:
    """
    Cross-system learning layer that aggregates signal intelligence across agents,
    strategies, and system-mode domains.

    Any subsystem can contribute signal observations here; the layer builds a
    cross-domain precision map so that signals corroborated by multiple domains
    receive amplified weight and shared intelligence is available to every subsystem.

    Design principles:
    - Pure in-memory, no DB dependency — fast and always available.
    - Thread-safe with a single internal lock.
    - Soft-decay ensures recent experience weighs more than stale history.
    - Consumers call shared_signal_weights() for a nudge multiplier on their own weights.
    """

    PRECISION_DECAY = 0.93          # per-ingest soft-decay on stored stats
    MIN_SUPPORT_FOR_WEIGHT = 2      # min total firings before a signal affects cross-domain output
    MAX_EVENT_BUFFER = 400          # rolling event log size
    CROSS_DOMAIN_BONUS = 0.18       # extra precision credit for signals corroborated across domains

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # domain -> signal_name -> {hits: float, total: float}
        self._domain_registry: dict[str, dict[str, dict[str, float]]] = {}
        # Aggregated cross-domain precision per signal name
        self._cross_domain_precision: dict[str, float] = {}
        # Which domains contributed data so far
        self._contributing_domains: set[str] = set()
        # Recent event log (for summary / inspection)
        self._events: deque[dict] = deque(maxlen=self.MAX_EVENT_BUFFER)

    # ------------------------------------------------------------------
    # Ingestion API
    # ------------------------------------------------------------------

    def record_signal(
        self,
        *,
        domain: str,
        signal_name: str,
        fired: bool,
        outcome_positive: bool,
    ) -> None:
        """
        Record a single signal observation from any domain.

        Parameters
        ----------
        domain : str
            Identifying label for the subsystem (e.g. 'system_mode', 'opportunity_scanner').
        signal_name : str
            The signal key (matches PREDICTIVE_SIGNAL_BASE_WEIGHTS names or any custom name).
        fired : bool
            Whether the signal was active / triggered this cycle.
        outcome_positive : bool
            True if a real degradation / bad outcome followed (True = signal was warranted).
        """
        if not domain or not signal_name:
            return
        with self._lock:
            domain_map = self._domain_registry.setdefault(domain, {})
            stats = domain_map.setdefault(signal_name, {"hits": 0.0, "total": 0.0})
            # Soft-decay to give more weight to recent observations
            stats["hits"] = stats["hits"] * self.PRECISION_DECAY
            stats["total"] = stats["total"] * self.PRECISION_DECAY
            if fired:
                stats["total"] += 1.0
                if outcome_positive:
                    stats["hits"] += 1.0
            self._contributing_domains.add(domain)
            self._events.append(
                {
                    "domain": domain,
                    "signal": signal_name,
                    "fired": fired,
                    "outcome_positive": outcome_positive,
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            self._recompute_cross_domain()

    def ingest_domain_signal_quality(
        self,
        *,
        domain: str,
        signal_quality: dict[str, dict],
    ) -> None:
        """
        Bulk-ingest a pre-computed signal quality map from a subsystem.

        Accepts dicts of the form {signal_name: {precision: float, support: float, ...}}
        as produced by SystemModeService._predictive_tuning_snapshot() signal_quality output.
        """
        if not domain or not signal_quality:
            return
        with self._lock:
            domain_map = self._domain_registry.setdefault(domain, {})
            for sig_name, profile in (signal_quality or {}).items():
                if not sig_name or not isinstance(profile, dict):
                    continue
                precision = float(profile.get("precision", 0.5) or 0.5)
                support = float(profile.get("support", 0.0) or 0.0)
                if support < self.MIN_SUPPORT_FOR_WEIGHT:
                    continue
                # Treat the bulk ingest as a synthetic observation set:
                # hits = precision * support, total = support — with decay on existing.
                stats = domain_map.setdefault(sig_name, {"hits": 0.0, "total": 0.0})
                stats["hits"] = stats["hits"] * self.PRECISION_DECAY + precision * support
                stats["total"] = stats["total"] * self.PRECISION_DECAY + support
            self._contributing_domains.add(domain)
            self._recompute_cross_domain()

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def shared_signal_weights(self, signal_names: Iterable[str]) -> dict[str, float]:
        """
        Return a cross-domain precision estimate for the given signal names.
        Values are in [0, 1] and represent cross-domain precision.
        Use as a nudge multiplier on per-domain weights.
        Returns 0.5 (neutral) for unknown signals.
        """
        with self._lock:
            return {
                name: round(self._cross_domain_precision.get(name, 0.5), 4)
                for name in signal_names
            }

    def summary(self) -> dict:
        """Full structured summary for embedding in mission intelligence snapshots."""
        with self._lock:
            total_events = len(self._events)
            domain_count = len(self._contributing_domains)
            top_signals = sorted(
                self._cross_domain_precision.items(),
                key=lambda kv: kv[1],
                reverse=True,
            )[:8]
            # Per-domain view
            domain_summaries: dict[str, dict] = {}
            for domain, smap in self._domain_registry.items():
                domain_summaries[domain] = {
                    sig: {
                        "precision": round(
                            stats["hits"] / max(stats["total"], 1e-6), 4
                        ),
                        "support": round(stats["total"], 2),
                    }
                    for sig, stats in smap.items()
                    if stats.get("total", 0.0) >= self.MIN_SUPPORT_FOR_WEIGHT
                }
            return {
                "total_events_logged": total_events,
                "contributing_domains": sorted(self._contributing_domains),
                "domain_count": domain_count,
                "cross_domain_precision": dict(self._cross_domain_precision),
                "top_signals_by_precision": [
                    {"signal": s, "precision": p} for s, p in top_signals
                ],
                "domain_summaries": domain_summaries,
                "learning_active": domain_count >= 1 and bool(self._cross_domain_precision),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recompute_cross_domain(self) -> None:
        """
        Aggregate per-domain signal stats into cross-domain precision.
        Signals corroborated by multiple domains receive a bonus.
        Must be called inside self._lock.
        """
        aggregated: dict[str, list[float]] = {}
        for domain_data in self._domain_registry.values():
            for sig_name, stats in domain_data.items():
                total = float(stats.get("total", 0.0) or 0.0)
                hits = float(stats.get("hits", 0.0) or 0.0)
                if total < self.MIN_SUPPORT_FOR_WEIGHT:
                    continue
                precision = hits / total
                aggregated.setdefault(sig_name, []).append(precision)

        result: dict[str, float] = {}
        for sig, precisions in aggregated.items():
            avg_precision = sum(precisions) / len(precisions)
            # Bonus when multiple domains independently confirm the same signal
            domain_count = len(precisions)
            cross_domain_boost = min((domain_count - 1) * self.CROSS_DOMAIN_BONUS, 0.36)
            result[sig] = round(min(avg_precision + cross_domain_boost, 1.0), 4)

        self._cross_domain_precision = result

    def reset(self) -> None:
        """Reset all learning state (admin use)."""
        with self._lock:
            self._domain_registry.clear()
            self._cross_domain_precision.clear()
            self._contributing_domains.clear()
            self._events.clear()


global_signal_intelligence = GlobalSignalIntelligenceService()
