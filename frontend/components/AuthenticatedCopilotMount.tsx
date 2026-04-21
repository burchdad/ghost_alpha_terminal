"use client";

import { usePathname } from "next/navigation";

import DashboardCopilot from "./DashboardCopilot";

const COPILOT_PATH_PREFIXES = ["/alpha", "/dashboard", "/terminal", "/brokerages"];

export default function AuthenticatedCopilotMount() {
  const pathname = usePathname();
  const shouldRender = COPILOT_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  if (!shouldRender) {
    return null;
  }

  return <DashboardCopilot />;
}
