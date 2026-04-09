from __future__ import annotations

from app.services.agents import MeanReversionAgent, MomentumAgent, OptionsAgent, VolatilityAgent


def get_registered_agents() -> list:
    return [
        MomentumAgent(),
        VolatilityAgent(),
        MeanReversionAgent(),
        OptionsAgent(),
    ]
