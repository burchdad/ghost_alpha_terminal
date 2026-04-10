from __future__ import annotations


class StrategyEvolutionService:
    """Generate strategy evolution actions from observed performance."""

    def plan(self, *, strategy_quality: dict) -> dict:
        mutations: list[dict] = []
        clones: list[dict] = []
        reinforcement_weights: dict[str, float] = {}

        for strategy, stats in (strategy_quality or {}).items():
            name = str(strategy or "UNKNOWN").upper()
            settled = int((stats or {}).get("settled", 0) or 0)
            quality = float((stats or {}).get("quality_score", 0.5) or 0.5)
            win_rate = float((stats or {}).get("win_rate", 0.5) or 0.5)

            # Reinforcement-style weighting for scanner ranking and sizing.
            reinforcement_weights[name] = round(max(0.65, min(1.35, 1.0 + (quality - 0.5) * 0.7)), 4)

            if settled < 20:
                continue

            if quality <= 0.44 or win_rate <= 0.44:
                mutations.append(
                    {
                        "strategy": name,
                        "action": "mutate",
                        "changes": {
                            "entry_confidence_floor_delta": 0.03,
                            "risk_budget_multiplier": 0.85,
                            "stop_loss_tightening": 0.90,
                        },
                        "reason": "persistent underperformance",
                    }
                )
            elif quality >= 0.62 and win_rate >= 0.56:
                clones.append(
                    {
                        "strategy": name,
                        "action": "clone",
                        "clone_name": f"{name}_AGGR_V1",
                        "changes": {
                            "risk_budget_multiplier": 1.08,
                            "take_profit_multiplier": 1.10,
                        },
                        "reason": "high-quality edge to exploit",
                    }
                )

        return {
            "mutations": mutations,
            "clones": clones,
            "reinforcement_weights": reinforcement_weights,
            "suggested_experiments": len(mutations) + len(clones),
        }


strategy_evolution_service = StrategyEvolutionService()
