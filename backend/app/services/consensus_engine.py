from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import AgentDecision, ConsensusDecision, SwarmResponse
from app.services.agent_scorer import agent_scorer


class ConsensusEngine:
    def _bias_to_score(self, bias: str) -> float:
        if bias == "BULLISH":
            return 1.0
        if bias == "BEARISH":
            return -1.0
        return 0.0

    def _score_agents(self, *, symbol: str, outputs: list[AgentDecision]) -> list[AgentDecision]:
        scored: list[AgentDecision] = []
        for output in outputs:
            metrics = agent_scorer.get_metrics(output.agent_name, symbol=symbol)
            return_boost = max(0.0, min(1.0, 0.5 + metrics.avg_return * 10))
            raw_confidence = output.confidence
            adjusted_confidence = max(0.0, min(1.0, raw_confidence * metrics.confidence_calibration))
            weighted_confidence = round(
                adjusted_confidence * 0.5 + metrics.composite_score * 0.4 + return_boost * 0.1,
                3,
            )
            scored.append(
                output.model_copy(
                    update={
                        "confidence": round(adjusted_confidence, 3),
                        "raw_confidence": round(raw_confidence, 3),
                        "adjusted_confidence": round(adjusted_confidence, 3),
                        "performance": metrics,
                        "weighted_confidence": weighted_confidence,
                    }
                )
            )
        return scored

    def generate_consensus(self, symbol: str, outputs: list[AgentDecision]) -> SwarmResponse:
        scored_outputs = self._score_agents(symbol=symbol, outputs=outputs)
        total_weight = sum(item.weighted_confidence or 0 for item in scored_outputs) or 1.0

        bias_score = sum(
            self._bias_to_score(item.bias) * (item.weighted_confidence or 0) for item in scored_outputs
        ) / total_weight

        directional_weight = sum(
            (item.weighted_confidence or 0) for item in scored_outputs if item.bias != "NEUTRAL"
        ) / total_weight

        # Reduce the neutral dead-zone so the engine can express directional bias
        # when multiple agents align with moderate confidence.
        if bias_score > 0.12:
            final_bias = "BULLISH"
        elif bias_score < -0.12:
            final_bias = "BEARISH"
        else:
            final_bias = "NEUTRAL"

        strategy_scores: dict[str, float] = {}
        for item in scored_outputs:
            strategy_scores[item.suggested_strategy] = strategy_scores.get(item.suggested_strategy, 0.0) + (
                item.weighted_confidence or 0
            )

        top_strategy = max(strategy_scores, key=strategy_scores.get)
        strategy_concentration = max(strategy_scores.values()) / total_weight
        base_confidence = (
            abs(bias_score) * 0.62
            + strategy_concentration * 0.24
            + directional_weight * 0.19
        )
        if final_bias == "NEUTRAL":
            confidence = max(0.5, min(0.9, base_confidence))
        else:
            directional_floor = 0.54 + min(0.18, directional_weight * 0.12 + abs(bias_score) * 0.28)
            confidence = max(directional_floor, min(0.95, base_confidence + 0.1))

        consensus = ConsensusDecision(
            final_bias=final_bias,
            confidence=round(confidence, 3),
            top_strategy=top_strategy,
        )

        return SwarmResponse(
            symbol=symbol.upper(),
            consensus=consensus,
            agent_breakdown=sorted(
                scored_outputs,
                key=lambda x: x.performance.composite_score if x.performance else 0,
                reverse=True,
            ),
            recommended_trade=top_strategy,
            generated_at=datetime.now(tz=timezone.utc),
        )


consensus_engine = ConsensusEngine()
