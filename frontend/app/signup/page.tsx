"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import QRCode from "react-qr-code";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type SignupStep = "info" | "twofa" | "agreements" | "complete";
type TwoFAMethod = "totp" | "sms" | "email";

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<SignupStep>("info");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 1: Account Info
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  // Step 2: 2FA Setup
  const [twoFAMethod, setTwoFAMethod] = useState<TwoFAMethod>("totp");
  const [totpSecret, setTotpSecret] = useState("");
  const [totpQRCode, setTotpQRCode] = useState("");
  const [twoFAVerificationCode, setTwoFAVerificationCode] = useState("");

  async function handleResendCode() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/auth/resend-2fa-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          twoFAMethod,
          phoneNumber,
        }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        setError(parseApiError(payload, "Failed to resend code"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  // Step 3: Agreements
  const [agreePrivacy, setAgreePrivacy] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [agreeRisk, setAgreeRisk] = useState(false);

  function parseApiError(payload: unknown, fallback: string): string {
    if (!payload || typeof payload !== "object") return fallback;
    const asRecord = payload as Record<string, unknown>;
    const detail = asRecord.detail;
    const message = asRecord.message;
    const errorCode = asRecord.error;

    if (typeof detail === "string" && detail.trim()) return detail;
    if (typeof message === "string" && message.trim()) return message;
    if (typeof errorCode === "string" && errorCode.trim()) return errorCode;
    return fallback;
  }

  // Step 1: Submit account info and move to 2FA
  async function handleAccountInfoSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    if (!fullName.trim()) {
      setError("Full name is required");
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      setLoading(false);
      return;
    }

    if (password !== passwordConfirm) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    if (twoFAMethod === "sms" && !phoneNumber.trim()) {
      setError("Phone number is required when SMS 2FA is selected");
      setLoading(false);
      return;
    }

    try {
      // Initialize 2FA setup
      const res = await fetch(`${API_BASE}/auth/initiate-2fa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, twoFAMethod, phoneNumber }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        setError(parseApiError(payload, "Failed to initialize 2FA"));
        setLoading(false);
        return;
      }

      const data = await res.json();
      setTotpSecret(data.secret || "");
      setTotpQRCode(data.qr_code || "");
      setStep("twofa");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Verify 2FA and move to agreements
  async function handleTwoFAVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    if (!twoFAVerificationCode.trim()) {
      setError("Verification code is required");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/verify-2fa-setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          twoFAMethod,
          verificationCode: twoFAVerificationCode,
        }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        setError(parseApiError(payload, "Invalid or expired code"));
        setLoading(false);
        return;
      }

      setStep("agreements");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  // Step 3: Create account with all data
  async function handleAccountCreation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    if (!agreePrivacy || !agreeTerms || !agreeRisk) {
      setError("You must agree to all policies to continue");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/signup-complete`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName,
          email,
          phoneNumber,
          password,
          twoFAMethod,
          agreePrivacy,
          agreeTerms,
          agreeRisk,
        }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        setError(parseApiError(payload, "Failed to create account"));
        setLoading(false);
        return;
      }

      setStep("complete");
      setTimeout(() => router.push("/brokerages"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-8 bg-slate-950 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/60 p-6 md:p-8">
        {step === "info" && (
          <>
            <h1 className="text-2xl font-bold text-slate-100 mb-6">Create Account</h1>
            <form onSubmit={handleAccountInfoSubmit} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  placeholder="John Trader"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  placeholder="you@example.com"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Phone Number (Optional)
                </label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-3">
                  2FA Method
                </label>
                <div className="space-y-2">
                  {(["totp", "sms", "email"] as const).map((method) => (
                    <label key={method} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="radio"
                        name="twofa_method"
                        value={method}
                        checked={twoFAMethod === method}
                        onChange={(e) => setTwoFAMethod(e.target.value as TwoFAMethod)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm text-slate-300 capitalize">
                        {method === "totp" && "Authenticator App (Recommended)"}
                        {method === "sms" && "Text Message (SMS)"}
                        {method === "email" && "Email Code"}
                      </span>
                    </label>
                  ))}
                </div>
                {twoFAMethod === "sms" && !phoneNumber.trim() ? (
                  <p className="mt-2 text-xs text-amber-300">Phone number is required for SMS verification.</p>
                ) : null}
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Password (8+ characters)
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  placeholder="••••••••"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500"
                  placeholder="••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-6 rounded-lg border border-emerald-600 bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
              >
                {loading ? "Setting up..." : "Next: Configure 2FA"}
              </button>

              <p className="text-center text-xs text-slate-400 mt-4">
                Already have an account?{" "}
                <Link href="/login" className="text-emerald-400 hover:underline">
                  Sign In
                </Link>
              </p>
            </form>
          </>
        )}

        {step === "twofa" && (
          <>
            <h1 className="text-2xl font-bold text-slate-100 mb-6">Set Up 2FA</h1>
            <p className="text-sm text-slate-300 mb-4">
              Two-factor authentication adds an extra layer of security to your account.
            </p>

            <form onSubmit={handleTwoFAVerify} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Selected 2FA Method
                </label>
                <p className="text-sm text-slate-300 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2">
                  {twoFAMethod === "totp" && "Authenticator App"}
                  {twoFAMethod === "sms" && "Text Message (SMS)"}
                  {twoFAMethod === "email" && "Email Code"}
                </p>
              </div>

              {twoFAMethod === "totp" && totpQRCode && (
                <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-700/40">
                  <p className="text-xs text-slate-400 mb-3">
                    Scan this QR code with your authenticator app (Google Authenticator, Authy, Microsoft Authenticator):
                  </p>
                  <div className="bg-white p-4 rounded inline-block mb-3">
                    <QRCode value={totpQRCode} size={160} />
                  </div>
                  <p className="text-xs text-slate-400">
                    Or enter manually: <code className="text-emerald-400 text-[10px]">{totpSecret}</code>
                  </p>
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
                  Verification Code
                </label>
                <input
                  type="text"
                  value={twoFAVerificationCode}
                  onChange={(e) => setTwoFAVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-slate-100 focus:outline-none focus:border-emerald-500 text-center tracking-widest"
                  placeholder="000000"
                  maxLength={6}
                  required
                />
                <p className="text-xs text-slate-500 mt-2">
                  Enter the 6-digit code from your {twoFAMethod === "totp" ? "authenticator app" : twoFAMethod}
                </p>
              </div>

              {twoFAMethod !== "totp" ? (
                <button
                  type="button"
                  onClick={() => void handleResendCode()}
                  disabled={loading}
                  className="w-full rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-600 disabled:opacity-50"
                >
                  {loading ? "Sending..." : "Resend Code"}
                </button>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-6 rounded-lg border border-emerald-600 bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
              >
                {loading ? "Verifying..." : "Verify & Continue"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("info");
                  setError("");
                }}
                className="w-full rounded-lg border border-slate-700 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-600"
              >
                Back
              </button>
            </form>
          </>
        )}

        {step === "agreements" && (
          <>
            <h1 className="text-2xl font-bold text-slate-100 mb-6">Review Agreements</h1>
            <p className="text-sm text-slate-300 mb-4">
              Please review and agree to our policies before creating your account.
            </p>

            <div className="space-y-4 max-h-96 overflow-y-auto pr-2 mb-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 text-sm">
                  {error}
                </div>
              )}

              <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-4 space-y-3">
                <div className="text-xs text-slate-400">
                  <p className="font-semibold mb-2">Privacy Policy</p>
                  <p className="leading-relaxed">
                    We collect account information, usage analytics, and configuration data necessary to operate the platform. Your data is encrypted and protected with industry-standard controls.
                  </p>
                </div>
                <label className="flex items-start gap-3 cursor-pointer mt-3">
                  <input
                    type="checkbox"
                    checked={agreePrivacy}
                    onChange={(e) => setAgreePrivacy(e.target.checked)}
                    className="w-5 h-5 mt-0.5"
                  />
                  <span className="text-sm text-slate-300">I agree to the Privacy Policy</span>
                </label>
                <Link href="/privacy-policy" target="_blank" className="text-xs text-emerald-400 hover:underline">
                  Read full policy →
                </Link>
              </div>

              <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-4 space-y-3">
                <div className="text-xs text-slate-400">
                  <p className="font-semibold mb-2">Terms of Use</p>
                  <p className="leading-relaxed">
                    This platform is for informational and operational use only. You assume all responsibility for trading decisions and losses.
                  </p>
                </div>
                <label className="flex items-start gap-3 cursor-pointer mt-3">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="w-5 h-5 mt-0.5"
                  />
                  <span className="text-sm text-slate-300">I agree to the Terms of Use</span>
                </label>
                <Link href="/terms-of-use" target="_blank" className="text-xs text-emerald-400 hover:underline">
                  Read full terms →
                </Link>
              </div>

              <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-4 space-y-3">
                <div className="text-xs text-slate-400">
                  <p className="font-semibold mb-2">Risk Disclosure</p>
                  <p className="leading-relaxed">
                    Trading involves substantial risk including potential loss of principal. Past performance is not indicative of future results. You are solely responsible for your decisions and outcomes.
                  </p>
                </div>
                <label className="flex items-start gap-3 cursor-pointer mt-3">
                  <input
                    type="checkbox"
                    checked={agreeRisk}
                    onChange={(e) => setAgreeRisk(e.target.checked)}
                    className="w-5 h-5 mt-0.5"
                  />
                  <span className="text-sm text-slate-300">I understand and accept the trading risks</span>
                </label>
                <Link href="/cybersecurity" target="_blank" className="text-xs text-emerald-400 hover:underline">
                  Security details →
                </Link>
              </div>
            </div>

            <form onSubmit={handleAccountCreation} className="space-y-3">
              <button
                type="submit"
                disabled={loading || !agreePrivacy || !agreeTerms || !agreeRisk}
                className="w-full rounded-lg border border-emerald-600 bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
              >
                {loading ? "Creating Account..." : "Create My Account"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("twofa");
                  setError("");
                }}
                className="w-full rounded-lg border border-slate-700 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-600"
              >
                Back
              </button>
            </form>
          </>
        )}

        {step === "complete" && (
          <div className="text-center space-y-4">
            <div className="text-4xl">✓</div>
            <h1 className="text-2xl font-bold text-slate-100">Account Created!</h1>
            <p className="text-sm text-slate-300">
              Your account is ready. Redirecting to brokerage setup...
            </p>
            <p className="text-xs text-slate-500">Redirecting in 2 seconds...</p>
          </div>
        )}
      </div>
    </main>
  );
}
