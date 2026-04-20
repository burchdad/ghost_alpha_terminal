from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class IntentType(str, Enum):
    NORMAL_OPERATIONAL = "normal_operational"
    OPTIMIZATION = "optimization"
    UNREALISTIC_GAIN = "unrealistic_gain"
    DANGEROUS = "dangerous"


@dataclass
class IntentClassification:
    intent_type: IntentType
    guardrail_reply: str | None = None
    guardrail_options: list[str] = field(default_factory=list)
    required_return_rate: float | None = None


# Patterns that indicate an attempt to override all risk controls.
_DANGEROUS_PATTERNS: list[str] = [
    r"\ball[\s-]in\b",
    r"\bgo\s+all[\s-]in\b",
    r"\bmax(?:imum)?\s+leverage\b",
    r"\bbet\s+everything\b",
    r"\byolo\b",
    r"\bmax\s+position\b",
    r"\bignore\s+(?:all\s+)?risk\s+(?:limits?|controls?)\b",
    r"\bremove\s+(?:all\s+)?risk\s+(?:limits?|controls?)\b",
    r"\bdisable\s+(?:all\s+)?risk\s+(?:limits?|controls?)\b",
    r"\bno\s+(?:risk\s+)?limits?\b",
    r"\bunlimited\s+(?:risk|exposure|leverage)\b",
]

# Multiplier keywords and their implied total-return multiple.
_MULTIPLIER_PATTERNS: list[tuple[str, float]] = [
    (r"\b100x\b", 100.0),
    (r"\b50x\b", 50.0),
    (r"\b20x\b", 20.0),
    (r"\b10x\b", 10.0),
    (r"\b5x\b", 5.0),
    (r"\b4x\b", 4.0),
    (r"\b3x\b|\btriple\b", 3.0),
    (r"\b2x\b|\bdouble\b", 2.0),
]

# Unrealistic short-timeframe threshold: required total return > this value.
_UNREALISTIC_RETURN_THRESHOLD = 0.50  # 50% gain


def _extract_days(text: str) -> int | None:
    """Pull the first explicit timeframe from text and return days."""
    m = re.search(
        r"(?:in|within|by|over|this)\s+(?:a\s+)?(?:(one|two|three|\d+)\s+)?"
        r"(day|days|week|weeks?|month|months?)\b",
        text,
    )
    if not m:
        return None
    word = m.group(1) or ""
    unit = m.group(2).rstrip("s")
    _words: dict[str, int] = {"one": 1, "two": 2, "three": 3}
    n = _words.get(word, int(word) if word.isdigit() else 1)
    if unit == "day":
        return n
    if unit == "week":
        return n * 7
    if unit == "month":
        return n * 30
    return None


def _extract_turn_amounts(text: str) -> tuple[float | None, float | None]:
    """Detect 'turn $X into $Y' patterns."""
    m = re.search(
        r"turn\s+\$?\s*([0-9,]+(?:\.[0-9]+)?)\s+into\s+\$?\s*([0-9,]+(?:\.[0-9]+)?)",
        text,
    )
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    return None, None


def _extract_gain_request(text: str) -> float | None:
    """Detect 'make / earn / generate $X' patterns and return the dollar amount."""
    m = re.search(
        r"(?:make|earn|generate|need|get)\s+\$?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:fast|quick|quickly|asap|right away|today|this week)?",
        text,
    )
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _guardrail_reply(balance: float, required_rate: float, days: int | None) -> str:
    pct = required_rate * 100.0
    balance_str = f"${balance:,.2f}" if balance > 0 else "your current balance"
    timeframe_str = f" in {days} day{'s' if days != 1 else ''}" if days else " in that timeframe"

    return (
        f"That goal requires a {pct:.0f}% return{timeframe_str} — "
        f"which is extreme high-risk territory with {balance_str}.\n\n"
        f"Standard risk controls exist to prevent this level of exposure. "
        f"A more realistic path with your current balance is execution validation and controlled compounding.\n\n"
        f"If you still want aggressive growth, I can configure High-Risk Sprint mode — "
        f"but this may result in losing most or all of your capital.\n\n"
        f"How would you like to proceed?"
    )


def classify(message: str, state: dict) -> IntentClassification:
    """
    Classify the user's message intent and return a guardrail if needed.

    Returns IntentClassification with:
      - intent_type: one of the IntentType enum values
      - guardrail_reply: a ready-to-send reply string if guardrailed, else None
      - guardrail_options: list of option keys for the frontend to render as action buttons
      - required_return_rate: computed return ratio when applicable
    """
    text = message.lower()
    balance = float(state.get("account_balance", 0.0) or 0.0)

    # ── 1. Dangerous override check ─────────────────────────────────────────
    for pat in _DANGEROUS_PATTERNS:
        if re.search(pat, text):
            return IntentClassification(
                intent_type=IntentType.DANGEROUS,
                guardrail_reply=(
                    "That directive would override all risk controls and expose your entire capital. "
                    "I won't execute this without an explicit risk acknowledgment.\n\n"
                    "If you're intentionally targeting an aggressive sprint, "
                    "High-Risk Sprint mode is the structured way to do that — "
                    "with defined targets and capital limits still in place."
                ),
                guardrail_options=["enable_high_risk_mode", "simulate_strategy", "set_realistic_goal"],
            )

    # ── 2. Multiplier keywords (double/triple/10x …) ────────────────────────
    for pat, multiplier in _MULTIPLIER_PATTERNS:
        if re.search(pat, text):
            days = _extract_days(text)
            required_rate = multiplier - 1.0
            # Flag if: high multiplier, OR short timeframe with any multiplier >= 2x
            if multiplier >= 3.0 or (multiplier >= 2.0 and (days is None or days <= 30)):
                return IntentClassification(
                    intent_type=IntentType.UNREALISTIC_GAIN,
                    guardrail_reply=_guardrail_reply(balance, required_rate, days),
                    guardrail_options=["simulate_strategy", "enable_high_risk_mode", "set_realistic_goal"],
                    required_return_rate=required_rate,
                )

    # ── 3. "Turn $X into $Y" ────────────────────────────────────────────────
    from_amt, to_amt = _extract_turn_amounts(text)
    if from_amt is not None and to_amt is not None and to_amt > from_amt:
        required_rate = (to_amt - from_amt) / from_amt
        if required_rate >= _UNREALISTIC_RETURN_THRESHOLD:
            days = _extract_days(text)
            return IntentClassification(
                intent_type=IntentType.UNREALISTIC_GAIN,
                guardrail_reply=_guardrail_reply(from_amt, required_rate, days),
                guardrail_options=["simulate_strategy", "enable_high_risk_mode", "set_realistic_goal"],
                required_return_rate=required_rate,
            )

    # ── 4. "Make / earn $X fast / this week" ────────────────────────────────
    if balance > 0:
        gain = _extract_gain_request(text)
        if gain is not None:
            required_rate = gain / balance
            days = _extract_days(text)
            # Flag if required return >= 50% AND (short timeframe or no timeframe w/ urgency words)
            urgent_words = any(
                w in text for w in ("fast", "quick", "quickly", "asap", "right away", "today", "this week")
            )
            if required_rate >= _UNREALISTIC_RETURN_THRESHOLD and (
                (days is not None and days <= 14) or urgent_words
            ):
                return IntentClassification(
                    intent_type=IntentType.UNREALISTIC_GAIN,
                    guardrail_reply=_guardrail_reply(balance, required_rate, days),
                    guardrail_options=["simulate_strategy", "enable_high_risk_mode", "set_realistic_goal"],
                    required_return_rate=required_rate,
                )

    return IntentClassification(intent_type=IntentType.NORMAL_OPERATIONAL)
