import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | GHOST ALPHA TERMINAL",
  description: "Privacy policy for GHOST ALPHA TERMINAL",
};

export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen px-5 py-8 md:px-10 md:py-10 lg:px-16">
      <section className="mx-auto max-w-4xl rounded-2xl border border-terminal-line bg-terminal-panel/70 p-6 md:p-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold md:text-3xl">Privacy Policy</h1>
          <Link href="/" className="text-xs text-terminal-accent hover:underline">
            Back to Home
          </Link>
        </div>

        <p className="mb-4 text-sm text-slate-300">Effective date: April 9, 2026</p>

        <div className="space-y-6 text-sm leading-relaxed text-slate-300">
          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">1. Information We Collect</h2>
            <p>
              We may collect account identifiers, usage analytics, configuration inputs, and trading-related preferences
              necessary to operate the platform. We do not intentionally collect sensitive personal information unless
              explicitly provided by you.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">2. How We Use Information</h2>
            <p>
              We use collected information to provide, secure, maintain, and improve the platform, troubleshoot issues,
              and deliver requested features such as market scanning, execution workflows, and audit replay.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">3. Data Sharing</h2>
            <p>
              We do not sell personal data. Data may be shared with infrastructure providers or integrated brokerage
              services only as needed to provide core functionality, subject to contractual and security safeguards.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">4. Data Retention</h2>
            <p>
              We retain information for as long as needed to operate the service, comply with legal obligations, and
              resolve disputes. You may request deletion of eligible data where required by applicable law.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">5. Security</h2>
            <p>
              We apply reasonable technical and organizational controls to protect data. No system can guarantee
              absolute security, so users should also follow best practices for account and key management.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">6. Contact</h2>
            <p>
              For privacy inquiries, contact your platform administrator or legal contact listed in your deployment
              documentation.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
