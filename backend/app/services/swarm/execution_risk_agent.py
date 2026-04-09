from __future__ import annotations

from statistics import pstdev

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class ExecutionRiskAgent(TradingAgent):
    """Execution-focused risk gate for slippage and liquidity anomalies."""

    name = "execution_risk_agent"

    def __init__(self) -> None:
        self._snapshot: MarketSnapshot | None = None
        self._realized_vol: float = 0.0
        self._volume_ratio: float = 1.0

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        prices = snapshot.close_prices
        returns: list[float] = []
        for idx in range(1, len(prices)):
            prev = prices[idx - 1]
            curr = prices[idx]
            if prev <= 0:
                continue
            returns.append((curr / prev) - 1.0)
        self._realized_vol = pstdev(returns) if returns else 0.0

        vols = snapshot.volumes
        if len(vols) >= 2:
            avg = sum(vols[:-1]) / max(len(vols[:-1]), 1)
            self._volume_ratio = (vols[-1] / avg) if avg > 0 else 1.0
        else:
            self._volume_ratio = 1.0

        confidence = 0.9 - min(self._realized_vol * 6, 0.45)
        confidence -= max(0.0, self._volume_ratio - 1.0) * 0.05
        self.confidence_score = round(max(0.35, min(confidence, 0.9)), 3)

    def generate_signal(self) -> SwarmSignal:
        return SwarmSignal(
            agent_name=self.name,
            action="HOLD",
            confidence=self.confidence_score,
            reasoning=(
                f"Execution risk monitor: vol={self._realized_vol:.4f}, "
                f"volume_ratio={self._volume_ratio:.2f}x."
            ),
        )

    def veto(self, *, action: str, qty: float, confidence: float) -> tuple[bool, str]:
        if action == "HOLD":
            return False, ""
        if self._realized_vol > 0.045 and confidence < 0.74:
            return True, (
                f"Execution-risk veto: realized volatility {self._realized_vol:.4f} with "
                f"insufficient confidence {confidence:.2f}."
            )
        if self._volume_ratio > 3.2:
            return True, (
                f"Execution-risk veto: abnormal volume spike {self._volume_ratio:.2f}x suggests unstable fills."
            )
        if qty <= 0:
            return True, "Execution-risk veto: non-positive quantity."
        return False, ""
