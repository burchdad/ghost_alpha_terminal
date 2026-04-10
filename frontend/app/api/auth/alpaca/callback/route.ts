import { NextRequest, NextResponse } from "next/server";

function resolveBackendUrl(): string | null {
  const rawInput = process.env.BACKEND_URL?.trim();
  if (!rawInput) {
    return null;
  }

  const raw = rawInput.replace(/\/$/, "");
  if (raw === "/api" || raw.endsWith("/api")) {
    return null;
  }

  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }

  return `https://${raw}`;
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl;
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");
  const errorDescription = url.searchParams.get("error_description");

  if (error) {
    const next = new URL("/alpha", url.origin);
    next.searchParams.set("alpaca_oauth", "error");
    next.searchParams.set("reason", errorDescription ?? error);
    return NextResponse.redirect(next);
  }

  if (!code || !state) {
    const next = new URL("/alpha", url.origin);
    next.searchParams.set("alpaca_oauth", "error");
    next.searchParams.set("reason", "Missing OAuth code/state");
    return NextResponse.redirect(next);
  }

  const backendUrl = resolveBackendUrl();
  if (!backendUrl) {
    const next = new URL("/alpha", url.origin);
    next.searchParams.set("alpaca_oauth", "error");
    next.searchParams.set("reason", "BACKEND_URL_MISSING");
    return NextResponse.redirect(next);
  }

  try {
    const exchangeRes = await fetch(
      `${backendUrl}/alpaca/oauth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
      {
        method: "GET",
        cache: "no-store",
        redirect: "manual",
      },
    );

    const redirectLocation = exchangeRes.headers.get("location");
    if (redirectLocation) {
      return NextResponse.redirect(new URL(redirectLocation, url.origin));
    }

    if (!exchangeRes.ok) {
      const text = await exchangeRes.text();
      const next = new URL("/alpha", url.origin);
      next.searchParams.set("alpaca_oauth", "error");
      next.searchParams.set("reason", `Exchange failed: ${text.slice(0, 160)}`);
      return NextResponse.redirect(next);
    }

    const payload = (await exchangeRes.json().catch(() => null)) as { connected?: boolean; next?: string } | null;
    const nextPath = payload?.next && payload.next.startsWith("/") ? payload.next : "/alpha";
    const next = new URL(nextPath, url.origin);
    next.searchParams.set("alpaca_oauth", payload?.connected ? "connected" : "error");
    return NextResponse.redirect(next);
  } catch (err) {
    const next = new URL("/alpha", url.origin);
    next.searchParams.set("alpaca_oauth", "error");
    next.searchParams.set("reason", err instanceof Error ? err.message : "unknown");
    return NextResponse.redirect(next);
  }
}
