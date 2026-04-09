from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import DecisionAudit
from app.db.session import get_session


class DecisionAuditStore:
    def record(
        self,
        *,
        decision_type: str,
        symbol: str,
        status: str,
        cycle_id: str | None,
        goal_snapshot: dict | None,
        context_snapshot: dict | None,
        allocation_snapshot: dict | None,
        governor_snapshot: dict | None,
        execution_snapshot: dict | None,
        explainability_snapshot: dict | None,
    ) -> str:
        audit_id = uuid.uuid4().hex
        with get_session() as db:
            db.add(
                DecisionAudit(
                    audit_id=audit_id,
                    timestamp=datetime.now(tz=timezone.utc),
                    decision_type=decision_type,
                    symbol=symbol.upper(),
                    status=status,
                    cycle_id=cycle_id,
                    goal_snapshot=json.dumps(goal_snapshot or {}),
                    context_snapshot=json.dumps(context_snapshot or {}),
                    allocation_snapshot=json.dumps(allocation_snapshot or {}),
                    governor_snapshot=json.dumps(governor_snapshot or {}),
                    execution_snapshot=json.dumps(execution_snapshot or {}),
                    explainability_snapshot=json.dumps(explainability_snapshot or {}),
                )
            )
        return audit_id

    def list_recent(self, *, limit: int = 50, symbol: str | None = None, status: str | None = None) -> list[dict]:
        with get_session() as db:
            stmt = select(DecisionAudit).order_by(DecisionAudit.timestamp.desc()).limit(limit)
            if symbol:
                stmt = stmt.where(DecisionAudit.symbol == symbol.upper())
            if status:
                stmt = stmt.where(DecisionAudit.status == status.upper())
            rows = db.execute(stmt).scalars().all()

        return [self._to_dict(row, include_payload=False) for row in rows]

    def get_by_id(self, audit_id: str) -> dict | None:
        with get_session() as db:
            row = db.execute(select(DecisionAudit).where(DecisionAudit.audit_id == audit_id)).scalar_one_or_none()
        if not row:
            return None
        return self._to_dict(row, include_payload=True)

    def _to_dict(self, row: DecisionAudit, *, include_payload: bool) -> dict:
        payload = {
            "audit_id": row.audit_id,
            "timestamp": row.timestamp,
            "decision_type": row.decision_type,
            "symbol": row.symbol,
            "status": row.status,
            "cycle_id": row.cycle_id,
        }
        if include_payload:
            payload.update(
                {
                    "goal_snapshot": json.loads(row.goal_snapshot or "{}"),
                    "context_snapshot": json.loads(row.context_snapshot or "{}"),
                    "allocation_snapshot": json.loads(row.allocation_snapshot or "{}"),
                    "governor_snapshot": json.loads(row.governor_snapshot or "{}"),
                    "execution_snapshot": json.loads(row.execution_snapshot or "{}"),
                    "explainability_snapshot": json.loads(row.explainability_snapshot or "{}"),
                }
            )
        return payload


decision_audit_store = DecisionAuditStore()
