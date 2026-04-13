import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Platform Features | GHOST ALPHA TERMINAL",
  description: "Explore platform capabilities, safety controls, and operator automation features.",
};

const featureCards = [
  {
    title: "Market Discovery + Ranking",
    body: "Scans broad symbol universes, pre-filters setups, and ranks opportunities with risk-adjusted scores.",
  },
  {
    title: "Multi-Agent Decision Engine",
    body: "Combines specialized agents with confidence calibration, consensus logic, and explainability output.",
  },
  {
    title: "Execution Safety Layer",
    body: "Supports simulation, paper, and live modes with policy gates, kill switch, and risk governors.",
  },
  {
    title: "AI Copilot Controls",
    body: "Natural-language control for safe adjustments with confirmation contracts and auditability.",
  },
  {
    title: "Runtime + Launch Telemetry",
    body: "Tracks reliability and conversion funnel in one ops pulse view to support fast operator decisions.",
  },
  {
    title: "Broker Connectivity",
    body: "OAuth-first broker workflows with explicit status, capability mapping, and staged route controls.",
  },
];

const trustItems = [
  "Session hardening (HttpOnly, SameSite, secure cookie policy)",
  "CSRF protection for state-changing authenticated requests",
  "Scoped API guardrails and request rate controls",
  "Security headers and CSP hardening on frontend and backend",
  "Decision and auth telemetry trails for operational traceability",
  "Execution mode gating with autonomous and kill-switch controls",
];

export default function FeaturesPage() {
  return (
    <main className="min-h-screen px-4 py-8 md:px-10 md:py-10 lg:px-16">
      <section className="mx-auto max-w-6xl rounded-3xl border border-terminal-line bg-terminal-panel/70 p-5 md:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-terminal-line/40 pb-4">
          <div>
            <h1 className="text-3xl font-semibold text-slate-100 md:text-4xl">Platform Features + Trust Center</h1>
            <p className="mt-2 text-sm text-slate-300">A clear view of what the SaaS does, how it operates, and how it stays safe.</p>
          </div>
          <Link href="/" className="rounded border border-terminal-line px-3 py-2 text-xs text-slate-200 hover:border-terminal-accent/60 hover:text-terminal-accent">
            Back to Home
          </Link>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <article className="overflow-hidden rounded-xl border border-terminal-line/60 bg-black/25 md:col-span-2">
            <Image
              src="/images/control-tower.svg"
              alt="Control tower showing growth and operations lanes"
              width={1200}
              height={700}
              className="h-auto w-full"
            />
          </article>
          <article className="overflow-hidden rounded-xl border border-terminal-line/60 bg-black/25">
            <Image
              src="/images/security-shield.svg"
              alt="Security shield with trust controls"
              width={1200}
              height={700}
              className="h-auto w-full"
            />
          </article>
        </div>

        <section className="mt-6">
          <h2 className="text-lg font-semibold text-terminal-accent">Core Capabilities</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {featureCards.map((card) => (
              <article key={card.title} className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
                <h3 className="text-sm font-semibold text-slate-100">{card.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-300">{card.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          <article className="overflow-hidden rounded-xl border border-terminal-line/60 bg-black/25">
            <Image
              src="/images/agent-observability.svg"
              alt="Agent observability matrix"
              width={1200}
              height={700}
              className="h-auto w-full"
            />
          </article>
          <article className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
            <h2 className="text-lg font-semibold text-terminal-accent">Trust + Security Highlights</h2>
            <div className="mt-3 grid gap-2 text-xs text-slate-300">
              {trustItems.map((item) => (
                <div key={item} className="rounded border border-terminal-line/50 bg-black/25 px-3 py-2">
                  {item}
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/cybersecurity" className="rounded border border-terminal-accent/60 bg-terminal-accent/10 px-3 py-2 text-xs text-terminal-accent hover:bg-terminal-accent/20">
                Read Cybersecurity Practices
              </Link>
              <Link href="/signup" className="rounded border border-cyan-300/60 bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950 hover:brightness-110">
                Try the Platform
              </Link>
            </div>
          </article>
        </section>

        <section className="mt-6 rounded-xl border border-terminal-line/60 bg-black/20 p-4 text-xs text-slate-300">
          <h2 className="text-base font-semibold text-slate-100">Documentation</h2>
          <p className="mt-2">
            Technical and launch documentation is maintained in repository docs, including platform capabilities, go-live checklist, and operator runbook.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded border border-terminal-line/60 bg-black/25 px-2 py-1">CAPABILITIES.md</span>
            <span className="rounded border border-terminal-line/60 bg-black/25 px-2 py-1">GO_LIVE_CHECKLIST.md</span>
            <span className="rounded border border-terminal-line/60 bg-black/25 px-2 py-1">OPERATOR_RUNBOOK.md</span>
          </div>
        </section>
      </section>
    </main>
  );
}
