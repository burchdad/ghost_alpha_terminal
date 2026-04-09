from __future__ import annotations

from dataclasses import dataclass

from app.services.news.news_intelligence import news_intelligence


@dataclass
class ContextModifiers:
    confidence_modifier: float
    risk_modifier: float
    opportunity_boost: float


class ContextIntelligenceService:
    """Combines news/sentiment/event context into bounded strategy modifiers."""

    def get_context(self, symbol: str) -> dict:
        news = news_intelligence.analyze_symbol(symbol)

        sentiment = float(news["sentiment_score"])
        momentum = float(news["news_momentum_score"])
        event_strength = float(news["event_strength"])
        classification = str(news["data_classification"])

        confidence_modifier = max(0.85, min(1.15, 1.0 + sentiment * 0.08 + event_strength * 0.05))
        risk_modifier = max(0.75, min(1.2, 1.0 - sentiment * 0.05 + (1.0 - momentum) * 0.03))
        opportunity_boost = max(-0.12, min(0.18, sentiment * 0.09 + momentum * 0.06 + event_strength * 0.05))

        # Compliance guardrail: unknown/restricted data cannot increase risk or confidence.
        if classification in {"RESTRICTED", "UNKNOWN"}:
            confidence_modifier = min(confidence_modifier, 1.0)
            risk_modifier = max(risk_modifier, 1.05)
            opportunity_boost = min(opportunity_boost, 0.0)

        return {
            "symbol": symbol.upper(),
            "data_classification": classification,
            "sources_used": news["sources_used"],
            "sentiment_score": sentiment,
            "news_momentum_score": momentum,
            "event_strength": event_strength,
            "event_flags": news["event_flags"],
            "modifiers": {
                "confidence_modifier": round(confidence_modifier, 6),
                "risk_modifier": round(risk_modifier, 6),
                "opportunity_boost": round(opportunity_boost, 6),
            },
            "rationale": (
                "Context modifiers are derived from public-source sentiment/event signals "
                "and bounded by compliance classification guards."
            ),
        }


context_intelligence = ContextIntelligenceService()
