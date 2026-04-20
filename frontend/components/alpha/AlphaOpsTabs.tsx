import type { ReactNode } from "react";

export type AlphaOpsTab = "portfolio" | "goal" | "audit" | "replay";

type Props = {
  activeTab: AlphaOpsTab;
  onTabChange: (tab: AlphaOpsTab) => void;
  panels: Record<AlphaOpsTab, ReactNode>;
};

const TAB_LABELS: Record<AlphaOpsTab, string> = {
  portfolio: "Portfolio",
  goal: "Goal",
  audit: "Audit",
  replay: "Replay",
};

export default function AlphaOpsTabs({ activeTab, onTabChange, panels }: Props) {
  return (
    <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
      <div className="mb-3 flex flex-wrap gap-2">
        {(Object.keys(TAB_LABELS) as AlphaOpsTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`rounded border px-3 py-1 text-xs transition ${
              activeTab === tab
                ? "border-terminal-accent bg-terminal-accent/15 text-terminal-accent"
                : "border-terminal-line bg-black/20 text-slate-300 hover:border-terminal-accent/50"
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {panels[activeTab]}
    </section>
  );
}
