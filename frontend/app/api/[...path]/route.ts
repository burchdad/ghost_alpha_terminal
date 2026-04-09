import { NextRequest, NextResponse } from "next/server";

function resolveBackendUrl(): string | null {
  const raw = process.env.BACKEND_URL?.trim();
  if (!raw) {
    return null;
  }

  // BACKEND_URL must be absolute (e.g. https://...railway.app), never /api
  if (!raw.startsWith("http://") && !raw.startsWith("https://")) {
    return null;
  }

  return raw.replace(/\/$/, "");
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
    });
  } catch (err) {
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
