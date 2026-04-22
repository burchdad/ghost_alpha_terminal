"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type Step = {
  id: string;
  title: string;
  description: string;
  action?: string;
  href?: string;
};

const STEPS: Step[] = [
  {
    id: "welcome",
    title: "Welcome to Ghost Alpha Terminal",
    description:
      "This is your mission-control dashboard for autonomous AI-driven trading. Let's walk through the key areas so you can get started quickly.",
  },
  {
    id: "broker",
    title: "Connect a Brokerage",
    description:
      "Navigate to the Brokerages tab in the left rail to connect Alpaca, Tradier, Coinbase, or Schwab. Your API credentials are stored encrypted and never leave the server.",
    action: "Go to Brokerages",
    href: "/brokerages",
  },
  {
    id: "goal",
    title: "Set a Goal",
    description:
      "Open the Goal panel in the dashboard and define a capital target with a deadline. The autonomous runner will calibrate position sizing and risk pressure toward your goal.",
  },
  {
    id: "scan",
    title: "Run Your First Scan",
    description:
      "Use the Opportunity Scanner or type a symbol in the Focus Symbol field to pull live market context, sentiment, and signal scores. Then hit Execute to place a trade.",
  },
  {
    id: "done",
    title: "You're All Set",
    description:
      "Your operator cockpit is ready. The notification bell (top right) will alert you to trade executions, kill-switch changes, and autonomous cycle updates in real time.",
  },
];

type Props = {
  onComplete: () => void;
};

export default function OnboardingWizard({ onComplete }: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [completing, setCompleting] = useState(false);

  const step = STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;

  const handleFinish = useCallback(async () => {
    setCompleting(true);
    try {
      await fetch(`${API_BASE}/auth/onboarding-complete`, {
        method: "POST",
        credentials: "include",
      });
      localStorage.setItem("ghost_onboarding_completed", "1");
    } catch {
      // best-effort; still dismiss the modal
    }
    onComplete();
    setCompleting(false);
  }, [onComplete]);

  // Keyboard: Escape to skip, Right/Enter to advance
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") handleFinish();
      if (e.key === "ArrowRight" || e.key === "Enter") {
        if (isLast) handleFinish();
        else setStepIndex((i) => i + 1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isLast, handleFinish]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="relative mx-4 w-full max-w-lg rounded-xl border border-terminal-line/50 bg-terminal-panel shadow-2xl">
        {/* Close / skip button */}
        <button
          onClick={handleFinish}
          className="absolute right-3 top-3 text-terminal-accent/40 hover:text-terminal-accent/80 transition text-xs"
          aria-label="Skip onboarding"
        >
          Skip
        </button>

        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 pt-6 pb-2">
          {STEPS.map((s, i) => (
            <span
              key={s.id}
              className={`h-1.5 w-1.5 rounded-full transition-all ${
                i === stepIndex
                  ? "bg-terminal-accent w-4"
                  : i < stepIndex
                    ? "bg-terminal-accent/40"
                    : "bg-terminal-line/40"
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="px-8 pb-4 pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-terminal-accent/50 mb-1">
            Step {stepIndex + 1} of {STEPS.length}
          </p>
          <h2 className="text-lg font-semibold text-terminal-accent mb-3">{step.title}</h2>
          <p className="text-sm leading-relaxed text-slate-300">{step.description}</p>

          {step.href && step.action && (
            <a
              href={step.href}
              className="mt-4 inline-block rounded border border-terminal-accent/40 bg-terminal-accent/10 px-3 py-1.5 text-xs text-terminal-accent hover:bg-terminal-accent/20 transition"
            >
              {step.action} →
            </a>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between border-t border-terminal-line/20 px-8 py-4">
          <button
            onClick={() => setStepIndex((i) => i - 1)}
            disabled={isFirst}
            className="text-xs text-terminal-accent/50 hover:text-terminal-accent disabled:opacity-30 transition"
          >
            ← Back
          </button>

          {isLast ? (
            <button
              onClick={handleFinish}
              disabled={completing}
              className="rounded border border-terminal-accent/50 bg-terminal-accent/20 px-4 py-1.5 text-xs font-semibold text-terminal-accent hover:bg-terminal-accent/30 disabled:opacity-50 transition"
            >
              {completing ? "Saving…" : "Launch Terminal →"}
            </button>
          ) : (
            <button
              onClick={() => setStepIndex((i) => i + 1)}
              className="rounded border border-terminal-accent/50 bg-terminal-accent/20 px-4 py-1.5 text-xs font-semibold text-terminal-accent hover:bg-terminal-accent/30 transition"
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
