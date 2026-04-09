"use client";

import { useState } from "react";

type GoalStatus = {
  enabled: boolean;
  start_capital: number | null;
  target_capital: number | null;
  timeframe_days: number | null;
  elapsed_days: number;
  remaining_days: number | null;
  required_total_return: number;
  required_daily_return: number;
  required_daily_return_remaining: number;
  trajectory_expected_capital: number | null;
  trajectory_gap_pct: number;
  goal_pressure_multiplier: number;
  success_probability: number;
  stress_level: "LOW" | "MEDIUM" | "HIGH" | "EXTREME";
  target_unrealistic: boolean;
  suggested_target_capital: number | null;
  suggested_timeframe_days: number | null;
  message: string;
};

type Props = {
  goal: GoalStatus | null;
  onSetGoal: (payload: { start_capital: number; target_capital: number; timeframe_days: number }) => Promise<void>;
};

export default function GoalPanel({ goal, onSetGoal }: Props) {
  const [startCapital, setStartCapital] = useState(10000);
  const [targetCapital, setTargetCapital] = useState(15000);
  const [timeframeDays, setTimeframeDays] = useState(30);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitGoal() {
    setIsSubmitting(true);
    try {
      await onSetGoal({
        start_capital: startCapital,
        target_capital: targetCapital,
        timeframe_days: timeframeDays,
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!goal) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading goal engine...</div>;
  }

  const stressClass =
    goal.stress_level === "EXTREME"
      ? "text-terminal-bear"
      : goal.stress_level === "HIGH"
      ? "text-orange-300"
      : goal.stress_level === "MEDIUM"
      ? "text-yellow-300"
      : "text-terminal-bull";

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Goal Dashboard</h3>
        <span className={`text-xs font-semibold ${stressClass}`}>Stress: {goal.stress_level}</span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Pressure: {goal.goal_pressure_multiplier.toFixed(2)}x
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Success Prob: {(goal.success_probability * 100).toFixed(1)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Required Daily: {(goal.required_daily_return_remaining * 100).toFixed(2)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Trajectory Gap: {(goal.trajectory_gap_pct * 100).toFixed(2)}%
        </div>
      </div>

      <p className="mb-3 text-xs text-slate-300">{goal.message}</p>

      {goal.target_unrealistic && (
        <div className="mb-3 rounded border border-terminal-bear/70 bg-terminal-bear/10 p-3 text-xs text-slate-200">
          <p className="mb-1 font-semibold text-terminal-bear">Reality Check</p>
          <p>
            Suggested target: {goal.suggested_target_capital?.toFixed(2) ?? "-"} in {goal.suggested_timeframe_days ?? "-"} days
          </p>
        </div>
      )}

      <div className="space-y-2 text-xs text-slate-300">
        <p className="font-semibold text-slate-400">Set Goal</p>
        <div className="grid grid-cols-1 gap-2">
          <label className="flex items-center justify-between gap-3">
            <span>Start</span>
            <input
              type="number"
              min={1}
              value={startCapital}
              onChange={(event) => setStartCapital(Number(event.target.value) || 0)}
              className="w-40 rounded border border-terminal-line bg-black/20 px-2 py-1 text-right text-slate-200"
            />
          </label>
          <label className="flex items-center justify-between gap-3">
            <span>Target</span>
            <input
              type="number"
              min={1}
              value={targetCapital}
              onChange={(event) => setTargetCapital(Number(event.target.value) || 0)}
              className="w-40 rounded border border-terminal-line bg-black/20 px-2 py-1 text-right text-slate-200"
            />
          </label>
          <label className="flex items-center justify-between gap-3">
            <span>Days</span>
            <input
              type="number"
              min={1}
              value={timeframeDays}
              onChange={(event) => setTimeframeDays(Number(event.target.value) || 0)}
              className="w-40 rounded border border-terminal-line bg-black/20 px-2 py-1 text-right text-slate-200"
            />
          </label>
        </div>

        <button
          onClick={submitGoal}
          disabled={isSubmitting}
          className="mt-2 w-full rounded border border-terminal-accent bg-terminal-accent/10 px-3 py-2 text-xs font-semibold text-terminal-accent transition disabled:opacity-50"
        >
          {isSubmitting ? "Applying Goal..." : "Apply Goal"}
        </button>
      </div>
    </div>
  );
}
