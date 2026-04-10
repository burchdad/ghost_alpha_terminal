"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AnimatedContainer,
  AnimatedItem,
  FloatingElement,
  SlideUp,
} from "@/components/AnimatedElements";
import {
  getAssignedVariant,
  trackVariantShown,
  trackCTAClick,
} from "@/lib/copyVariants";
import { heroTitleVariants } from "@/lib/animations";

export default function HomePage() {
  const [copyVariant, setCopyVariant] = useState(
    getAssignedVariant()
  );
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    trackVariantShown(copyVariant.id);
  }, [copyVariant]);

  const handleCTAClick = (label: string) => {
    trackCTAClick(copyVariant.id, label);
  };

  return (
    <main className="relative min-h-screen overflow-hidden px-4 py-6 md:px-10 md:py-10 lg:px-16">
      {/* Ambient animated backgrounds */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -left-24 top-12 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl"
        animate={{
          y: [-20, 20, -20],
          opacity: [0.8, 1, 0.8],
        }}
        transition={{
          duration: 8,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-24 top-40 h-80 w-80 rounded-full bg-amber-400/10 blur-3xl"
        animate={{
          y: [20, -20, 20],
          opacity: [0.9, 0.7, 0.9],
        }}
        transition={{
          duration: 10,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 h-80 w-[42rem] -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl"
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.7, 0.9, 0.7],
        }}
        transition={{
          duration: 12,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />

      <section className="relative mx-auto flex max-w-6xl flex-col gap-6 rounded-3xl border border-terminal-line bg-[#05121ab8] p-5 shadow-glow md:p-8">
        <motion.div
          className="flex flex-wrap items-center justify-between gap-3 border-b border-terminal-line/40 pb-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-widest">
            <motion.span
              className="rounded-full border border-terminal-accent/70 bg-terminal-accent/10 px-3 py-1 text-terminal-accent"
              whileHover={{ scale: 1.05 }}
            >
              GhostAlpha OS
            </motion.span>
            <motion.span
              className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-emerald-300"
              whileHover={{ scale: 1.05 }}
            >
              Market Brain Online
            </motion.span>
            <motion.span
              className="rounded-full border border-fuchsia-400/40 bg-fuchsia-400/10 px-3 py-1 text-fuchsia-300"
              whileHover={{ scale: 1.05 }}
            >
              AI Operator Copilot
            </motion.span>
          </div>
          <nav className="flex items-center gap-4 text-xs text-slate-300">
            <Link href="/login" className="transition hover:text-terminal-accent">
              Login
            </Link>
            <Link href="/signup" className="transition hover:text-terminal-accent">
              Sign Up
            </Link>
            <Link href="/privacy-policy" className="transition hover:text-terminal-accent">
              Privacy
            </Link>
            <Link href="/terms-of-use" className="transition hover:text-terminal-accent">
              Terms
            </Link>
          </nav>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <AnimatedContainer className="space-y-6">
            <motion.h1
              className="text-3xl font-semibold leading-tight md:text-5xl"
              variants={heroTitleVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {isClient && copyVariant.headline}
              <span className="mt-1 block text-terminal-accent">{isClient && (copyVariant.id === "v1" ? "Mission-Driven AI Operator" : copyVariant.id === "v2" ? "One Unified Interface" : "Unified Strategy Execution")}</span>
              <span className="mt-2 block text-base font-medium text-slate-300 md:text-xl">
                {isClient && copyVariant.tagline}
              </span>
            </motion.h1>

            <AnimatedItem>
              <p className="max-w-3xl text-sm text-slate-300 md:text-base">
                Ghost Alpha continuously scans the market, ranks opportunities, routes by strategy, and executes under
                strict risk rails. You set the destination. The system handles the workload.
              </p>
            </AnimatedItem>

            <AnimatedContainer stagger className="grid gap-3 sm:grid-cols-3">
              <AnimatedItem>
                <div className="rounded-xl border border-terminal-line/70 bg-black/30 p-3">
                  <div className="text-[11px] uppercase tracking-wider text-slate-500">Universe Coverage</div>
                  <div className="mt-1 text-2xl font-semibold text-terminal-accent">321</div>
                  <div className="text-xs text-slate-400">Tradables scored per cycle</div>
                </div>
              </AnimatedItem>
              <AnimatedItem>
                <div className="rounded-xl border border-terminal-line/70 bg-black/30 p-3">
                  <div className="text-[11px] uppercase tracking-wider text-slate-500">Control Layers</div>
                  <div className="mt-1 text-lg font-semibold text-cyan-300">Discovery + Risk + Exec</div>
                  <div className="text-xs text-slate-400">Stacked operator protections</div>
                </div>
              </AnimatedItem>
              <AnimatedItem>
                <div className="rounded-xl border border-terminal-line/70 bg-black/30 p-3">
                  <div className="text-[11px] uppercase tracking-wider text-slate-500">Copilot</div>
                  <div className="mt-1 text-lg font-semibold text-emerald-300">Conversational Control</div>
                  <div className="text-xs text-slate-400">Chat-driven actions + simulation</div>
                </div>
              </AnimatedItem>
            </AnimatedContainer>

            <AnimatedItem>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/signup"
                  onClick={() => handleCTAClick("primary_cta")}
                  className="inline-flex items-center rounded-lg border border-cyan-300/60 bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
                >
                  {isClient && copyVariant.primaryCTA}
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center rounded-lg border border-terminal-line px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-terminal-accent/70 hover:text-terminal-accent"
                >
                  {isClient && copyVariant.secondaryCTA}
                </Link>
              </div>
            </AnimatedItem>

            <SlideUp delay={0.3}>
              <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
                <div className="text-[11px] uppercase tracking-wider text-slate-500">What You Unlock After Login</div>
                <div className="mt-3 grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
                  <div className="rounded border border-terminal-line/60 bg-black/30 p-2">Live mission dashboard and execution controls</div>
                  <div className="rounded border border-terminal-line/60 bg-black/30 p-2">AI copilot with safe confirmations and policy gates</div>
                  <div className="rounded border border-terminal-line/60 bg-black/30 p-2">Scenario simulation by chat and by control panel</div>
                  <div className="rounded border border-terminal-line/60 bg-black/30 p-2">Decision replay, telemetry, and performance traceability</div>
                </div>
              </div>
            </SlideUp>
          </AnimatedContainer>

          <SlideUp delay={0.2}>
            <div className="rounded-2xl border border-terminal-line/70 bg-[#031018d1] p-4 md:p-5">
              <div className="mb-3 flex items-center justify-between gap-2 text-xs uppercase tracking-wider text-slate-500">
                <span>Live Preview</span>
                <span className="rounded border border-terminal-accent/40 bg-terminal-accent/10 px-2 py-1 text-[10px] text-terminal-accent">Post-Login Surface</span>
              </div>

              <div className="rounded-xl border border-terminal-line/70 bg-black/35 p-3">
                <div className="mb-3 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Runtime</span>
                  <span className="text-emerald-300">Operator Ready</span>
                </div>

                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded border border-terminal-line/50 bg-black/30 p-2 text-xs text-slate-300">Execution Mode: PAPER_TRADING</div>
                  <div className="rounded border border-terminal-line/50 bg-black/30 p-2 text-xs text-slate-300">Autonomous: ENABLED</div>
                  <div className="rounded border border-terminal-line/50 bg-black/30 p-2 text-xs text-slate-300">Scan Auto: ON</div>
                  <div className="rounded border border-terminal-line/50 bg-black/30 p-2 text-xs text-slate-300">Candidates Ready: 13</div>
                </div>

                <div className="mt-3 rounded border border-fuchsia-400/30 bg-fuchsia-400/10 p-3 text-xs text-fuchsia-100">
                  Copilot: "Simulate additional $5,000 in 30 days and tighten daily risk to 2%."
                </div>

                <div className="mt-2 rounded border border-emerald-400/30 bg-emerald-400/10 p-3 text-xs text-emerald-100">
                  Response: Scenario complete, pressure 1.42x, recommended style BALANCED. Risk limits updated.
                </div>
              </div>
            </div>
          </SlideUp>
        </div>

        <AnimatedContainer className="grid gap-3 border-t border-terminal-line/40 pt-4 text-xs text-slate-400 sm:grid-cols-3">
          <AnimatedItem>
            <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
              01 DISCOVER: Market-wide scan and strategy-fit ranking.
            </div>
          </AnimatedItem>
          <AnimatedItem>
            <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
              02 DECIDE: Mission pressure, risk policy, and execution gates.
            </div>
          </AnimatedItem>
          <AnimatedItem>
            <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
              03 EXECUTE: Controlled order flow with audit lineage.
            </div>
          </AnimatedItem>
        </AnimatedContainer>

        <AnimatedContainer stagger className="grid gap-3 border-t border-terminal-line/40 pt-4 md:grid-cols-3">
          <AnimatedItem>
            <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
              <h3 className="text-sm font-semibold text-terminal-accent">Why It Converts</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-300">
                It replaces scattered tools with one mission cockpit. Less toggle fatigue, faster decision cycles, tighter
                risk discipline.
              </p>
            </div>
          </AnimatedItem>
          <AnimatedItem>
            <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
              <h3 className="text-sm font-semibold text-terminal-accent">What You Keep</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-300">
                Your existing execution stack still applies. We add orchestration, explainability, and chat control on top
                without forcing workflow lock-in.
              </p>
            </div>
          </AnimatedItem>
          <AnimatedItem>
            <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
              <h3 className="text-sm font-semibold text-terminal-accent">Start In Minutes</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-300">
                Create an account, connect broker permissions, and start in paper mode. When comfortable, graduate to live
                under explicit policy and confirmation contracts.
              </p>
            </div>
          </AnimatedItem>
        </AnimatedContainer>

        <SlideUp delay={0.4}>
          <div className="rounded-2xl border border-terminal-line/60 bg-black/20 p-5">
            <motion.div
              className="mb-3 text-center text-[11px] uppercase tracking-wider text-slate-500"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              Final Step
            </motion.div>
            <h2 className="text-center text-2xl font-semibold text-slate-100 md:text-3xl">{isClient && copyVariant.finalHeadline}</h2>
            <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-slate-300">
              Get your mission dashboard, copilot controls, and execution rails in one authenticated workspace.
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/signup"
                onClick={() => handleCTAClick("final_cta")}
                className="inline-flex items-center rounded-lg border border-cyan-300/60 bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
              >
                {isClient && copyVariant.finalCTALabel}
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center rounded-lg border border-terminal-line px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-terminal-accent/70 hover:text-terminal-accent"
              >
                Login
              </Link>
            </div>
          </div>
        </SlideUp>

        <motion.footer
          className="flex flex-wrap items-center justify-between gap-3 border-t border-terminal-line/40 pt-4 text-xs text-slate-400"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <p>Ghost Alpha Terminal - AI-driven market operating system</p>
          <div className="flex items-center gap-4">
            <Link href="/privacy-policy" className="transition hover:text-terminal-accent">
              Privacy Policy
            </Link>
            <Link href="/terms-of-use" className="transition hover:text-terminal-accent">
              Terms of Use
            </Link>
          </div>
        </motion.footer>
      </section>
    </main>
  );
}
