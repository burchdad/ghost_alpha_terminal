from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
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


class BrokerOAuthConnection(Base):
    __tablename__ = "broker_oauth_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="alpaca")
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
