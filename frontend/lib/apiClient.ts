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

export async function apiFetch(input: string, options: ApiFetchOptions = {}): Promise<Response> {
  const apiBase = options.apiBase ?? DEFAULT_API_BASE;
  const { apiBase: _apiBase, headers, ...rest } = options;
  void _apiBase;

  const baseInit: RequestInit = {
    credentials: "include",
    ...rest,
    headers,
  };

  const firstResponse = await fetch(input, baseInit);
  if (firstResponse.status !== 401 || typeof window === "undefined") {
    return firstResponse;
  }

  const path = toPath(input, apiBase);
  if (!shouldAttemptRefresh(path)) {
    return firstResponse;
  }

  const refreshResponse = await fetch(`${apiBase}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });

  if (!refreshResponse.ok) {
    return firstResponse;
  }

  return fetch(input, baseInit);
}
