from __future__ import annotations


def build_explainability(
    *,
    reasoning: str,
    confidence: float,
    risk_level: str,
    expected_value: float,
    accepted: bool,
    safeguards: list[str] | None = None,
    inputs: dict | None = None,
) -> dict:
    return {
        "accepted": accepted,
        "reasoning": reasoning,
        "confidence": round(float(confidence), 4),
        "risk_level": risk_level,
        "expected_value": round(float(expected_value), 6),
        "safeguards": safeguards or [],
        "inputs": inputs or {},
    }
