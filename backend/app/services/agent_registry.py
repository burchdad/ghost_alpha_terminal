from __future__ import annotations

from app.services.agents import (
    BreakoutAgent,
    LiquidityFlowAgent,
    MeanReversionAgent,
    MomentumAgent,
    OptionsAgent,
    TermStructureAgent,
    TrendPullbackAgent,
    VolatilityAgent,
)


def get_registered_agents() -> list:
    return [
        MomentumAgent(),
        VolatilityAgent(),
        MeanReversionAgent(),
        OptionsAgent(),
        TrendPullbackAgent(),
        BreakoutAgent(),
        TermStructureAgent(),
        LiquidityFlowAgent(),
    ]
