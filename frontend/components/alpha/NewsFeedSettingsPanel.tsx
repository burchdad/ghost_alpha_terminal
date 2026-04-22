"use client";

import { useEffect, useState } from "react";

type NewsFeedSource = {
  source: string;
  url: string;
  enabled: boolean;
  weight: number;
};

type NewsFeedSettings = {
  sources: NewsFeedSource[];
  refresh_seconds: number;
  updated_at: string | null;
};

type Props = {
  settings: NewsFeedSettings | null;
  onSave: (payload: { enabled_sources: string[]; source_weights: Record<string, number> }) => Promise<void>;
};

export default function NewsFeedSettingsPanel({ settings, onSave }: Props) {
  const [draftSources, setDraftSources] = useState<NewsFeedSource[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraftSources(settings?.sources ?? []);
  }, [settings]);

  if (!settings) {
    return (
      <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 text-xs text-slate-400">
        Loading news feed settings...
      </section>
    );
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave({
        enabled_sources: draftSources.filter((item) => item.enabled).map((item) => item.source),
        source_weights: Object.fromEntries(draftSources.map((item) => [item.source, item.weight])),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-terminal-accent">News Feed Settings</h3>
        <span className="text-[10px] text-slate-500">Refresh {settings.refresh_seconds}s</span>
      </div>

      <div className="space-y-2">
        {draftSources.map((item, index) => (
          <div key={item.source} className="rounded border border-terminal-line bg-black/20 p-2 text-[11px] text-slate-300">
            <div className="flex items-start justify-between gap-2">
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={item.enabled}
                  onChange={(event) => {
                    const next = [...draftSources];
                    next[index] = { ...item, enabled: event.target.checked };
                    setDraftSources(next);
                  }}
                  className="mt-0.5"
                />
                <span>
                  <span className="block font-semibold text-slate-100">{item.source.replaceAll("_", " ")}</span>
                  <span className="block truncate text-[10px] text-slate-500">{item.url}</span>
                </span>
              </label>
              <label className="flex items-center gap-2 text-[10px] text-slate-500">
                Weight
                <input
                  type="number"
                  min={0.1}
                  max={10}
                  step={0.1}
                  value={item.weight}
                  onChange={(event) => {
                    const next = [...draftSources];
                    next[index] = { ...item, weight: Number(event.target.value) };
                    setDraftSources(next);
                  }}
                  className="w-16 rounded border border-terminal-line bg-black/40 px-2 py-1 text-right text-[11px] text-slate-200"
                />
              </label>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 text-[10px] text-slate-500">
        <span>{settings.updated_at ? `Updated ${new Date(settings.updated_at).toLocaleString()}` : "Using defaults"}</span>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="rounded border border-terminal-accent bg-terminal-accent/10 px-2 py-1 text-[11px] text-terminal-accent disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Feed Tuning"}
        </button>
      </div>
    </section>
  );
}