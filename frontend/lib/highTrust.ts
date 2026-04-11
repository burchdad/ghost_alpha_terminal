import { apiFetch } from "./apiClient";

export type EnsureHighTrustOptions = {
  apiBase: string;
  trustDeviceByDefault?: boolean;
};

type HighTrustStatusResponse = {
  high_trust?: boolean;
};

type HighTrustChallengeResponse = {
  challenge_required?: boolean;
  method?: string;
};

type ApiErrorPayload = {
  detail?: string;
};

function methodLabel(method: string | undefined): string {
  if (method === "totp") {
    return "authenticator app";
  }
  if (method === "sms") {
    return "SMS";
  }
  if (method === "email") {
    return "email";
  }
  return "2FA";
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload?.detail && typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // ignore parse errors
  }
  return `Request failed (${response.status})`;
}

export async function ensureHighTrust(options: EnsureHighTrustOptions): Promise<boolean> {
  const statusRes = await apiFetch(`${options.apiBase}/auth/session/high-trust-status`, { apiBase: options.apiBase });

  if (statusRes.status === 401) {
    throw new Error("Authentication required");
  }
  if (!statusRes.ok) {
    throw new Error(await readErrorDetail(statusRes));
  }

  const status = (await statusRes.json()) as HighTrustStatusResponse;
  if (status.high_trust) {
    return true;
  }

  const challengeRes = await apiFetch(`${options.apiBase}/auth/2fa/challenge`, {
    apiBase: options.apiBase,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

  if (challengeRes.status === 401) {
    throw new Error("Authentication required");
  }
  if (!challengeRes.ok) {
    throw new Error(await readErrorDetail(challengeRes));
  }

  const challenge = (await challengeRes.json()) as HighTrustChallengeResponse;
  if (!challenge.challenge_required || challenge.method === "trusted_device") {
    return true;
  }

  if (typeof window === "undefined") {
    throw new Error("2FA verification requires a browser context");
  }

  const code = window.prompt(`Enter your ${methodLabel(challenge.method)} verification code`);
  if (!code || !code.trim()) {
    return false;
  }

  const trustDevice = window.confirm("Trust this device for future secure actions?");
  const verifyRes = await apiFetch(`${options.apiBase}/auth/2fa/verify`, {
    apiBase: options.apiBase,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      verificationCode: code.trim(),
      trustDevice: options.trustDeviceByDefault ? true : trustDevice,
    }),
  });

  if (verifyRes.status === 401) {
    throw new Error("Authentication required");
  }
  if (!verifyRes.ok) {
    throw new Error(await readErrorDetail(verifyRes));
  }

  return true;
}
