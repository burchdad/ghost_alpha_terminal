import { NextRequest, NextResponse } from "next/server";

const UPSTREAM_TIMEOUT_MS = 15000;

function resolveBackendUrl(): string | null {
  const rawInput = process.env.BACKEND_URL?.trim();
  if (!rawInput) {
    return null;
  }

  const raw = rawInput.replace(/\/$/, "");

  // Guard against accidental self-proxy values.
  if (raw === "/api" || raw.endsWith("/api")) {
    return null;
  }

  // Accept bare domains in env vars and default to https.
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }

  return `https://${raw}`;
}

function jsonError(status: number, code: string, message: string): NextResponse {
  return NextResponse.json({ error: code, message }, { status });
}

async function proxy(request: NextRequest, params: { path: string[] }) {
  const backendUrl = resolveBackendUrl();
  if (!backendUrl) {
    return jsonError(
      500,
      "BACKEND_URL_MISSING",
      "Set BACKEND_URL in Vercel project environment variables to your Railway backend URL.",
    );
  }

  const targetPath = params.path.join("/");
  const search = request.nextUrl.search || "";
  const targetUrl = `${backendUrl}/${targetPath}${search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      // Keep upstream redirect responses intact for browser-driven OAuth flows.
      redirect: "manual",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (err) {
    if (err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")) {
      return jsonError(
        504,
        "BACKEND_TIMEOUT",
        `Backend request timed out after ${UPSTREAM_TIMEOUT_MS / 1000}s at ${backendUrl}.`,
      );
    }
    return jsonError(
      502,
      "BACKEND_UNREACHABLE",
      `Failed to reach backend at ${backendUrl}: ${err instanceof Error ? err.message : "unknown error"}`,
    );
  }

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.set("x-proxy-target", backendUrl);

  // Graceful degradation for transient scan backend outages.
  // This keeps dashboard polling stable and avoids noisy failed-resource errors in the browser.
  if (
    request.method === "POST"
    && targetPath === "orchestrator/scan"
    && (upstream.status === 502 || upstream.status === 503)
  ) {
    const nowIso = new Date().toISOString();
    return NextResponse.json(
      {
        candidates: [],
        market_narrative: "Scan temporarily unavailable; using fallback response.",
        regime_summary: {},
        sector_leaders: [],
        scanned_at: nowIso,
        scan_count: 0,
        total_scanned: 0,
        passed_prefilter: 0,
        auto_mode: false,
      },
      {
        status: 200,
        headers: {
          "x-proxy-target": backendUrl,
          "x-proxy-fallback": "orchestrator-scan",
        },
      },
    );
  }

  // When the upstream returns a 5xx with a non-JSON body (e.g. a Railway /
  // nginx HTML error page), pass a structured JSON error so the client can
  // display a meaningful message instead of hitting its fallback string.
  if (upstream.status >= 500) {
    const ct = (upstream.headers.get("content-type") ?? "").toLowerCase();
    if (!ct.includes("application/json")) {
      return jsonError(
        upstream.status,
        "BACKEND_ERROR",
        `Backend returned ${upstream.status}. Check Railway logs for details.`,
      );
    }
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params);
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params);
}

export async function PATCH(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return proxy(request, context.params);
}
