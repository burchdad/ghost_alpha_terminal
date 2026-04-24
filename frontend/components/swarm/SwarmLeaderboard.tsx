"use client";

import { useMemo } from "react";

import type { MarketRegime, SwarmCycleResponse } from "../../types/swarm";

type Props = {
  decisions: SwarmCycleResponse[];
};

type LeaderRow = {
  agent_name: string;
  win_rate: number;
  confidence_accuracy: number;
  avg_pnl_contribution: number;
  by_regime: Record<MarketRegime, number>;
};

const regimes: MarketRegime[] = ["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"];

export default function SwarmLeaderboard({ decisions }: Props) {
  const rows = useMemo<LeaderRow[]>(() => {
    const agentMap = new Map<string, {
      matches: number;
      allMatches: number;
      directionalTotal: number;
      confidenceDeltaSum: number;
      total: number;
      pnlContributionSum: number;
      pnlContributionCount: number;
      regimeMatches: Record<MarketRegime, number>;
      regimeTotals: Record<MarketRegime, number>;
    }>();

    for (const cycle of decisions) {
      const attribution = new Map(
        (cycle.agent_attribution ?? []).map((a) => [a.agent_name, a]),
      );

      for (const sig of cycle.agent_signals) {
        const current = agentMap.get(sig.agent_name) ?? {
          matches: 0,
          allMatches: 0,
          directionalTotal: 0,
          confidenceDeltaSum: 0,
          total: 0,
          pnlContributionSum: 0,
          pnlContributionCount: 0,
          regimeMatches: {
            TRENDING: 0,
            RANGE_BOUND: 0,
            HIGH_VOLATILITY: 0,
          },
          regimeTotals: {
            TRENDING: 0,
            RANGE_BOUND: 0,
            HIGH_VOLATILITY: 0,
          },
        };

        const attr = attribution.get(sig.agent_name);
        const directional = cycle.final_action !== "HOLD";
        const matched = typeof attr?.correct === "boolean" ? attr.correct : sig.action === cycle.final_action;

        current.total += 1;
        if (matched) {
          current.allMatches += 1;
        }
        if (directional) {
          current.directionalTotal += 1;
          if (matched) {
            current.matches += 1;
          }
        }

        current.confidenceDeltaSum += 1 - Math.abs(sig.confidence - cycle.final_confidence);
        if (typeof attr?.pnl_contribution === "number") {
          current.pnlContributionSum += attr.pnl_contribution;
          current.pnlContributionCount += 1;
        }
        current.regimeTotals[cycle.regime] += 1;
        if (matched) {
          current.regimeMatches[cycle.regime] += 1;
        }

        agentMap.set(sig.agent_name, current);
      }
    }

    return [...agentMap.entries()]
      .map(([agent_name, raw]) => {
        const by_regime = {
          TRENDING: raw.regimeTotals.TRENDING ? raw.regimeMatches.TRENDING / raw.regimeTotals.TRENDING : 0,
          RANGE_BOUND: raw.regimeTotals.RANGE_BOUND ? raw.regimeMatches.RANGE_BOUND / raw.regimeTotals.RANGE_BOUND : 0,
          HIGH_VOLATILITY: raw.regimeTotals.HIGH_VOLATILITY
            ? raw.regimeMatches.HIGH_VOLATILITY / raw.regimeTotals.HIGH_VOLATILITY
            : 0,
        };

        return {
          agent_name,
          win_rate: raw.directionalTotal ? raw.matches / raw.directionalTotal : (raw.total ? raw.allMatches / raw.total : 0),
          confidence_accuracy: raw.total ? raw.confidenceDeltaSum / raw.total : 0,
          avg_pnl_contribution: raw.pnlContributionCount ? raw.pnlContributionSum / raw.pnlContributionCount : 0,
          by_regime,
        };
      })
      .sort((a, b) => b.win_rate - a.win_rate || b.avg_pnl_contribution - a.avg_pnl_contribution);
  }, [decisions]);

  return (
    <div className="panel rounded-xl p-4">
      <h3 className="mb-3 text-sm font-semibold text-terminal-accent">Agent Leaderboard</h3>
      {decisions.length === 0 && (
        <div className="mb-3 rounded border border-terminal-line bg-black/20 px-3 py-2 text-xs text-slate-400">
          No swarm cycles yet. Run cycles to populate live leaderboard metrics.
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Agent</th>
              <th className="px-2 py-1">Win Rate*</th>
              <th className="px-2 py-1">Confidence Accuracy</th>
              <th className="px-2 py-1">Avg PnL Contribution</th>
              <th className="px-2 py-1">TRENDING</th>
              <th className="px-2 py-1">RANGE</th>
              <th className="px-2 py-1">HIGH VOL</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.agent_name} className="border-t border-terminal-line text-slate-300">
                <td className="px-2 py-2 font-semibold">{row.agent_name}</td>
                <td className="px-2 py-2">{Math.round(row.win_rate * 100)}%</td>
                <td className="px-2 py-2">{Math.round(row.confidence_accuracy * 100)}%</td>
                <td className="px-2 py-2">{row.avg_pnl_contribution.toFixed(3)}</td>
                {regimes.map((regime) => (
                  <td key={`${row.agent_name}-${regime}`} className="px-2 py-2">
                    {Math.round(row.by_regime[regime] * 100)}%
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[11px] text-slate-400">
        *Win rate prefers directional agreement; when no directional actions exist yet it falls back to overall agreement. PnL columns refine once outcomes are linked per cycle.
      </p>
    </div>
  );
}
