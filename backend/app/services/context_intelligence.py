from __future__ import annotations

from app.services.news.news_intelligence import news_intelligence
from app.services.signal_validation_engine import signal_validation_engine


class ContextIntelligenceService:
    """Combines validated news/sentiment/event context into bounded strategy modifiers."""

    def get_context(self, symbol: str) -> dict:
        news = news_intelligence.analyze_symbol(symbol)

        sentiment = float(news["sentiment_score"])
        momentum = float(news["news_momentum_score"])
        event_strength = float(news["event_strength"])
        classification = str(news["data_classification"])

        validation = signal_validation_engine.validate(
            symbol=symbol,
            sources_used=list(news["sources_used"]),
            sentiment_score=sentiment,
            news_momentum_score=momentum,
            event_strength=event_strength,
        )
        reaction = signal_validation_engine.market_reaction_correlation(
            symbol=symbol,
            sentiment_score=sentiment,
            news_momentum_score=momentum,
            event_strength=event_strength,
        )

        validated_strength = float(validation["validated_signal_strength"])
        reaction_score = float(reaction["correlation_score"])
        actionability = float(reaction["actionability_multiplier"])

        confidence_modifier = max(
            0.8,
            min(
                1.25,
                1.0
                + sentiment * 0.05
                + validated_strength * 0.13
                + reaction_score * 0.09,
            ),
        )
        risk_modifier = max(
            0.72,
            min(
                1.25,
                1.0
                - sentiment * 0.03
                + (1.0 - validated_strength) * 0.09
                + max(0.0, -reaction_score) * 0.08,
            ),
        )
        opportunity_boost = max(
            -0.14,
            min(
                0.24,
                sentiment * 0.08
                + momentum * 0.04
                + event_strength * 0.03
                + validated_strength * 0.12
                + max(0.0, reaction_score) * 0.08,
            ),
        )

        # Actionable price reaction confirms whether information has translated into market behavior.
        confidence_modifier *= actionability
        opportunity_boost *= actionability

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
            "signal_validation": validation,
            "market_reaction": reaction,
            "modifiers": {
                "confidence_modifier": round(confidence_modifier, 6),
                "risk_modifier": round(risk_modifier, 6),
                "opportunity_boost": round(opportunity_boost, 6),
            },
            "rationale": (
                "Context modifiers apply source credibility, recency decay, and multi-source confirmation, "
                "then cross-check with market reaction correlation before influencing allocation."
            ),
        }


context_intelligence = ContextIntelligenceService()
