"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";

export default function LoginPage() {
  const router = useRouter();
  const [nextPath, setNextPath] = useState("/dashboard");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotMessage, setForgotMessage] = useState("");
  const [forgotError, setForgotError] = useState("");
  const [forgotCaptchaRequired, setForgotCaptchaRequired] = useState(false);
  const [forgotCaptchaToken, setForgotCaptchaToken] = useState("");

  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState("");
  const [resetError, setResetError] = useState("");

  function parseApiError(payload: unknown, fallback: string): string {
    if (!payload || typeof payload !== "object") {
      return fallback;
    }
    const asRecord = payload as Record<string, unknown>;
    const detail = asRecord.detail;
    const message = asRecord.message;
    const errorCode = asRecord.error;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (typeof message === "string" && message.trim()) {
      return message;
    }
    if (typeof errorCode === "string" && errorCode.trim()) {
      return errorCode;
    }
    return fallback;
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const value = params.get("next");
    const token = params.get("reset_token");
    if (value && value.startsWith("/")) {
      setNextPath(value);
    }
    if (token) {
      setResetToken(token);
    }
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch(`${API_BASE}/auth/login`, {
        apiBase: API_BASE,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(parseApiError(payload, "Login failed"));
      }
      router.replace(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function onForgotPasswordSubmit() {
    setForgotLoading(true);
    setForgotError("");
    setForgotMessage("");

    try {
      const res = await apiFetch(`${API_BASE}/auth/forgot-password`, {
        apiBase: API_BASE,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: forgotEmail, captchaToken: forgotCaptchaToken || null }),
      });
      const payload = await res.json().catch(() => null);
      if (!res.ok) {
        const parsedError = parseApiError(payload, "Could not start password reset");
        if (parsedError.toLowerCase().includes("captcha")) {
          setForgotCaptchaRequired(true);
        }
        throw new Error(parsedError);
      }
      setForgotCaptchaRequired(false);
      setForgotCaptchaToken("");
      setForgotMessage(parseApiError(payload, "If that email is registered, a reset link has been sent."));
    } catch (err) {
      setForgotError(err instanceof Error ? err.message : "Could not start password reset");
    } finally {
      setForgotLoading(false);
    }
  }

  async function onResetPasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResetLoading(true);
    setResetError("");
    setResetMessage("");

    if (newPassword !== confirmNewPassword) {
      setResetError("Passwords do not match");
      setResetLoading(false);
      return;
    }

    try {
      const res = await apiFetch(`${API_BASE}/auth/reset-password`, {
        apiBase: API_BASE,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: resetToken, newPassword }),
      });
      const payload = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(parseApiError(payload, "Could not reset password"));
      }
      setResetMessage("Password reset successful. You can now sign in.");
      setNewPassword("");
      setConfirmNewPassword("");
      setResetToken("");
      const url = new URL(window.location.href);
      url.searchParams.delete("reset_token");
      window.history.replaceState({}, "", url.toString());
    } catch (err) {
      setResetError(err instanceof Error ? err.message : "Could not reset password");
    } finally {
      setResetLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-slate-100">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h1 className="text-2xl font-semibold">Login</h1>
        <p className="mt-2 text-sm text-slate-400">Access Ghost Alpha Terminal</p>
        <p className="mt-1 text-xs text-slate-500">Use your existing account or create one below.</p>

        {resetToken ? (
          <form className="mt-5 space-y-3 rounded-lg border border-emerald-700/50 bg-emerald-900/20 p-4" onSubmit={onResetPasswordSubmit}>
            <h2 className="text-sm font-semibold text-emerald-200">Reset password</h2>
            <p className="text-xs text-emerald-100/80">Set a new password for your account.</p>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              placeholder="New password"
              className="w-full rounded-md border border-emerald-700/60 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-400"
            />
            <input
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Confirm new password"
              className="w-full rounded-md border border-emerald-700/60 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-400"
            />
            {resetError ? (
              <p className="rounded-md border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-200" role="alert">
                {resetError}
              </p>
            ) : null}
            {resetMessage ? (
              <p className="rounded-md border border-emerald-700/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200" role="status">
                {resetMessage}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={resetLoading}
              className="w-full rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {resetLoading ? "Updating password..." : "Update password"}
            </button>
          </form>
        ) : null}

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm text-slate-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="password" className="block text-sm text-slate-300">
                Password
              </label>
              <button
                type="button"
                onClick={() => {
                  setShowForgotPassword((current) => !current);
                  setForgotEmail(email);
                  setForgotError("");
                  setForgotMessage("");
                }}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300"
              >
                Forgot password?
              </button>
            </div>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            />
          </div>

          {showForgotPassword ? (
            <div className="space-y-2 rounded-md border border-slate-700 bg-slate-950/70 p-3">
              <p className="text-xs text-slate-300">Send a reset link to your email.</p>
              <input
                type="email"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                required
                placeholder="you@company.com"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              />
              {forgotCaptchaRequired ? (
                <div className="space-y-1">
                  <label className="block text-xs text-slate-300">Captcha token required</label>
                  <input
                    type="text"
                    value={forgotCaptchaToken}
                    onChange={(e) => setForgotCaptchaToken(e.target.value)}
                    placeholder={TURNSTILE_SITE_KEY ? "Paste Turnstile token" : "Captcha token"}
                    className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                  />
                  <p className="text-[11px] text-slate-400">
                    Repeated reset attempts require captcha verification before another link can be sent.
                  </p>
                </div>
              ) : null}
              {forgotError ? (
                <p className="rounded-md border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-200" role="alert">
                  {forgotError}
                </p>
              ) : null}
              {forgotMessage ? (
                <p className="rounded-md border border-emerald-700/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200" role="status">
                  {forgotMessage}
                </p>
              ) : null}
              <button
                type="button"
                onClick={onForgotPasswordSubmit}
                disabled={forgotLoading}
                className="w-full rounded-md bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-100 disabled:opacity-50"
              >
                {forgotLoading ? "Sending link..." : "Send reset link"}
              </button>
            </div>
          ) : null}

          {error ? (
            <p className="rounded-md border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-200" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-400">
          No account yet? <Link href="/signup" className="text-emerald-400 hover:text-emerald-300">Sign up</Link>
        </p>
      </div>
    </main>
  );
}
