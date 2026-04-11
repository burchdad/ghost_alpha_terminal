from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class FraudAssessment:
    score: int
    rating: str
    action: str
    reasons: list[str]


class FraudAgent:
    def assess_withdrawal(
        self,
        *,
        trust_score: int,
        anomaly_score: int,
        behavior_score: int,
        destination_is_new: bool,
        session_risk_score: int,
    ) -> FraudAssessment:
        reasons: list[str] = []
        composite = int(round((100 - trust_score) * 0.35 + anomaly_score * 0.45 + behavior_score * 0.20))
        composite += min(20, max(0, int(session_risk_score // 5)))

        if destination_is_new:
            composite += 10
            reasons.append("new_destination")
        if trust_score < 40:
            reasons.append("low_trust")
        if anomaly_score >= 50:
            reasons.append("anomaly_cluster")
        if behavior_score >= 50:
            reasons.append("behavior_shift")

        composite = max(0, min(100, composite))
        if composite >= int(settings.fraud_agent_block_score):
            return FraudAssessment(
                score=composite,
                rating="CRITICAL",
                action="BLOCK",
                reasons=reasons or ["critical_risk"],
            )
        if composite >= int(settings.fraud_agent_escalate_score):
            return FraudAssessment(
                score=composite,
                rating="HIGH",
                action="ESCALATE",
                reasons=reasons or ["high_risk"],
            )
        if composite >= 35:
            return FraudAssessment(
                score=composite,
                rating="MEDIUM",
                action="HOLD",
                reasons=reasons or ["moderate_risk"],
            )
        return FraudAssessment(
            score=composite,
            rating="LOW",
            action="ALLOW",
            reasons=reasons,
        )


fraud_agent = FraudAgent()
