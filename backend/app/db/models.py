from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ForecastHistory(Base):
    __tablename__ = "forecast_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    volatility: Mapped[str] = mapped_column(String(16))


class SignalHistory(Base):
    __tablename__ = "signal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    signal: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AgentPrediction(Base):
    __tablename__ = "agent_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    bias: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    strategy: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class TradeOutcome(Base):
    __tablename__ = "trade_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy: Mapped[str] = mapped_column(String(64), index=True)
    regime: Mapped[str] = mapped_column(String(32), index=True, default="RANGE_BOUND")
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float, index=True)
    outcome: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class DecisionAudit(Base):
    __tablename__ = "decision_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audit_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )
    decision_type: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    cycle_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    goal_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    context_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    allocation_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    governor_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    execution_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    explainability_snapshot: Mapped[str] = mapped_column(Text, default="{}")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class CopilotConversationMessage(Base):
    __tablename__ = "copilot_conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)  # user | assistant | system
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class CopilotTelemetryEvent(Base):
    __tablename__ = "copilot_telemetry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode_assigned: Mapped[str] = mapped_column(String(32), index=True, default="rule-based")
    parser_used: Mapped[str] = mapped_column(String(32), index=True, default="rule")
    action_detected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    action_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action_applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_excerpt: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class ExecutionPolicyState(Base):
    __tablename__ = "execution_policy_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="global")
    live_only_during_market_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    market_timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    market_open_hhmm: Mapped[str] = mapped_column(String(8), default="09:30")
    market_close_hhmm: Mapped[str] = mapped_column(String(8), default="16:00")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class BrokerOAuthConnection(Base):
    __tablename__ = "broker_oauth_connections"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_broker_oauth_user_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True, default="alpaca")
    connected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    obtained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class LaunchMetricDaily(Base):
    __tablename__ = "launch_metric_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    metric_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class ExecutionJournalDB(Base):
    __tablename__ = "execution_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    regime: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(16), index=True)
    strategy: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    allocation_pct: Mapped[float] = mapped_column(Float)
    qty: Mapped[float] = mapped_column(Float)
    notional: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(32), index=True)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )
    outcome_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)


class LiveExperimentModeState(Base):
    __tablename__ = "live_experiment_mode_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="global")
    variant: Mapped[str] = mapped_column(String(64), index=True, default="evolution_on_compounding_on")
    source: Mapped[str] = mapped_column(String(128), default="default")
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class MetaRiskCooldownState(Base):
    __tablename__ = "meta_risk_cooldown_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="global")
    mode: Mapped[str] = mapped_column(String(32), default="normal")
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exposure_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    disable_evolution_temporarily: Mapped[bool] = mapped_column(Boolean, default=False)
    frozen_strategies_json: Mapped[str] = mapped_column(Text, default="[]")
    last_transitions_24h: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )


class SystemModeState(Base):
    __tablename__ = "system_mode_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="global")
    confirmed_mode: Mapped[str] = mapped_column(String(32), default="BALANCED")
    pending_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pending_confirmation_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmation_required: Mapped[int] = mapped_column(Integer, default=2)
    last_evaluation_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mode_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), index=True
    )
