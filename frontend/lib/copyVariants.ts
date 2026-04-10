// Copy A/B variant system for landing page conversion testing

export interface CopyVariants {
  id: "v1" | "v2" | "v3";
  headline: string;
  tagline: string;
  primaryCTA: string;
  secondaryCTA: string;
  finalHeadline: string;
  finalCTALabel: string;
}

export const copyVariantSets: Record<string, CopyVariants> = {
  v1: {
    id: "v1",
    headline: "Trade With A Mission-Driven AI Operator",
    tagline: "From market discovery to controlled execution in one command surface.",
    primaryCTA: "Start Free Operator Setup",
    secondaryCTA: "Login",
    finalHeadline: "Launch Your AI Trading Operator",
    finalCTALabel: "Create Account",
  },
  v2: {
    id: "v2",
    headline: "Market Intelligence Meets Execution Control",
    tagline: "Scan. Rank. Execute. All under strict risk rails—no scattered tools.",
    primaryCTA: "Begin Free Setup",
    secondaryCTA: "Already Have Account?",
    finalHeadline: "Activate Your Autonomous Trading Cockpit",
    finalCTALabel: "Get Started Free",
  },
  v3: {
    id: "v3",
    headline: "A.I. Trading That Actually Executes Your Strategy",
    tagline: "Continuous market discovery, intelligent ranking, and controlled order flow in one unified interface.",
    primaryCTA: "Setup Free Account",
    secondaryCTA: "Sign In",
    finalHeadline: "Join the Future of AI-Driven Trading",
    finalCTALabel: "Launch Operator Today",
  },
};

/**
 * Deterministically assign a copy variant based on session/time
 * Uses localStorage and rotates through variants
 */
export function getAssignedVariant(): CopyVariants {
  if (typeof window === "undefined") {
    return copyVariantSets.v1;
  }

  const stored = localStorage.getItem("ghost_copy_variant");
  if (stored && copyVariantSets[stored]) {
    return copyVariantSets[stored];
  }

  // Deterministic assignment: use timestamp to rotate
  const variantKeys = Object.keys(copyVariantSets);
  const now = new Date();
  const dayOfMonth = now.getDate();
  const sessionIndex = (dayOfMonth + Math.floor(now.getHours() / 6)) % variantKeys.length;
  const assignedKey = variantKeys[sessionIndex];
  const assignedVariant = copyVariantSets[assignedKey];

  localStorage.setItem("ghost_copy_variant", assignedKey);

  return assignedVariant;
}

/**
 * Track copy variant performance
 * Sends event to telemetry endpoint
 */
export async function trackVariantShown(variantId: string) {
  try {
    await fetch("/api/telemetry/landing-variant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        variant_id: variantId,
        event_type: "variant_shown",
        timestamp: new Date().toISOString(),
      }),
    });
  } catch {
    // Silently fail—telemetry should not block UX
  }
}

/**
 * Track CTA click with variant context
 */
export async function trackCTAClick(variantId: string, ctaLabel: string) {
  try {
    await fetch("/api/telemetry/landing-cta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        variant_id: variantId,
        cta_label: ctaLabel,
        event_type: "cta_click",
        timestamp: new Date().toISOString(),
      }),
    });
  } catch {
    // Silently fail
  }
}
