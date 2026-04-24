export type ApiFetchOptions = RequestInit & {
  apiBase?: string;
};

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

const EXCLUDED_REFRESH_PATHS = new Set([
  "/auth/login",
  "/auth/signup",
  "/auth/signup-complete",
  "/auth/initiate-2fa",
  "/auth/verify-2fa-setup",
  "/auth/resend-2fa-code",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/refresh",
]);

const PROTECTED_ROUTE_PREFIXES = ["/alpha", "/terminal", "/dashboard", "/brokerages"];

function toPath(input: string, apiBase: string): string {
  if (input.startsWith("http://") || input.startsWith("https://")) {
    try {
      const url = new URL(input);
      const api = new URL(apiBase, window.location.origin);
      if (url.origin === api.origin) {
        return url.pathname;
      }
      return "";
    } catch {
      return "";
    }
  }

  if (input.startsWith("/")) {
    return input;
  }

  const normalizedBase = apiBase.replace(/\/$/, "");
  if (input.startsWith(normalizedBase)) {
    return input.slice(normalizedBase.length) || "/";
  }

  return "";
}

function shouldAttemptRefresh(path: string): boolean {
  if (!path.startsWith("/")) {
    return false;
  }
  return !EXCLUDED_REFRESH_PATHS.has(path);
}

function isProtectedClientRoute(pathname: string): boolean {
  return PROTECTED_ROUTE_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function redirectToLoginIfNeeded(): void {
  if (typeof window === "undefined") {
    return;
  }

  if (!isProtectedClientRoute(window.location.pathname)) {
    return;
  }

  if ((window as typeof window & { __ghostAuthRedirecting?: boolean }).__ghostAuthRedirecting) {
    return;
  }

  (window as typeof window & { __ghostAuthRedirecting?: boolean }).__ghostAuthRedirecting = true;
  const next = `${window.location.pathname}${window.location.search}` || "/dashboard";
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

const CSRF_COOKIE_NAME = "ghost_csrf";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readCookie(name: string): string {
  if (typeof document === "undefined") {
    return "";
  }
  const source = `; ${document.cookie}`;
  const parts = source.split(`; ${name}=`);
  if (parts.length < 2) {
    return "";
  }
  return decodeURIComponent(parts.pop()?.split(";").shift() ?? "");
}

function withCsrfHeader(init: RequestInit): RequestInit {
  const method = String(init.method ?? "GET").toUpperCase();
  if (SAFE_METHODS.has(method)) {
    return init;
  }

  const csrfToken = readCookie(CSRF_COOKIE_NAME);
  if (!csrfToken) {
    return init;
  }

  const headers = new Headers(init.headers ?? {});
  if (!headers.has("x-csrf-token")) {
    headers.set("x-csrf-token", csrfToken);
  }

  return {
    ...init,
    headers,
  };
}

export async function apiFetch(input: string, options: ApiFetchOptions = {}): Promise<Response> {
  const apiBase = options.apiBase ?? DEFAULT_API_BASE;
  const { apiBase: _apiBase, headers, ...rest } = options;
  void _apiBase;

  const baseInit: RequestInit = withCsrfHeader({
    credentials: "include",
    ...rest,
    headers,
  });

  const firstResponse = await fetch(input, baseInit);
  if (firstResponse.status !== 401 || typeof window === "undefined") {
    return firstResponse;
  }

  const path = toPath(input, apiBase);
  if (!shouldAttemptRefresh(path)) {
    if (firstResponse.status === 401) {
      redirectToLoginIfNeeded();
    }
    return firstResponse;
  }

  const refreshResponse = await fetch(`${apiBase}/auth/refresh`, withCsrfHeader({
    method: "POST",
    credentials: "include",
  }));

  if (!refreshResponse.ok) {
    redirectToLoginIfNeeded();
    return firstResponse;
  }

  const retryResponse = await fetch(input, baseInit);
  if (retryResponse.status === 401) {
    redirectToLoginIfNeeded();
  }

  return retryResponse;
}
