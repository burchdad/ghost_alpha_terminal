import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Use | GHOST ALPHA TERMINAL",
  description: "Terms of use for GHOST ALPHA TERMINAL",
};

export default function TermsOfUsePage() {
  return (
    <main className="min-h-screen px-5 py-8 md:px-10 md:py-10 lg:px-16">
      <section className="mx-auto max-w-4xl rounded-2xl border border-terminal-line bg-terminal-panel/70 p-6 md:p-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold md:text-3xl">Terms of Use</h1>
          <Link href="/" className="text-xs text-terminal-accent hover:underline">
            Back to Home
          </Link>
        </div>

        <p className="mb-4 text-sm text-slate-300">Effective date: April 9, 2026</p>

        <div className="space-y-6 text-sm leading-relaxed text-slate-300">
          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">1. Acceptance of Terms</h2>
            <p>
              By accessing or using this platform, you agree to these terms. If you do not agree, do not use the
              service.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">2. Informational Use Only</h2>
            <p>
              The platform provides analytics and workflow tooling for research and operational support. It does not
              constitute financial, investment, legal, or tax advice.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">3. Trading Risk Disclosure</h2>
            <p>
              Trading and investing involve substantial risk, including potential loss of principal. Past performance is
              not indicative of future results. You are solely responsible for your decisions and outcomes.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">4. Account and Access</h2>
            <p>
              You are responsible for safeguarding your credentials, API keys, and connected account access. You agree
              to notify your administrator of unauthorized use.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">5. Availability and Changes</h2>
            <p>
              We may modify, suspend, or discontinue features at any time. We do not guarantee uninterrupted service or
              error-free operation.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, the platform is provided on an "as is" basis without warranties,
              and we are not liable for indirect, incidental, or consequential damages arising from use of the service.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-terminal-accent">7. Contact</h2>
            <p>
              For legal inquiries, contact your platform administrator or legal contact listed in your deployment
              documentation.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
