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
        <div className="mb-8 flex items-center justify-between gap-4 border-b border-terminal-line/40 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-100">TERMS OF USE</h1>
            <p className="mt-2 text-xs uppercase tracking-wider text-slate-400">Ghost Alpha Terminal</p>
          </div>
          <Link href="/" className="text-xs text-terminal-accent hover:underline">
            Back to Home
          </Link>
        </div>

        <div className="mb-6 bg-black/30 p-4 rounded-lg border border-terminal-line/40">
          <p className="text-xs text-slate-400"><strong>Last Updated:</strong> April 9, 2026</p>
          <p className="text-xs text-slate-400 mt-2"><strong>Effective Date:</strong> April 9, 2026</p>
        </div>

        <div className="space-y-8 text-sm leading-relaxed text-slate-300">
          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">1. AGREEMENT TO TERMS</h2>
            
            <p className="mb-3">
              These Terms of Use ("Terms," "Agreement") constitute a legally binding agreement between Ghost Alpha Terminal ("Platform," "we," "us," or "our") and you ("User," "you," or "your"). By accessing, browsing, or using the Platform in any manner, you acknowledge that you have read, understood, and agree to be bound by these Terms.
            </p>
            <p>
              If you do not agree to all terms herein, you are not authorized to use the Platform and must immediately discontinue access.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">2. SERVICE DESCRIPTION</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.1 Platform Scope</h3>
                <p>
                  Ghost Alpha Terminal provides an AI-driven market analysis, opportunity ranking, and execution orchestration platform ("Service"). The Service is designed for institutional and sophisticated retail traders to support decision-making, workflow automation, and performance tracking.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.2 Informational Use Only</h3>
                <p>
                  The Service provides analytics, workflow tooling, market intelligence, and operational dashboards for research and decision support. The Platform does not provide, and you agree not to rely upon it as, financial advice, investment recommendations, legal counsel, or tax advisory.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.3 No Fiduciary Relationship</h3>
                <p>
                  We do not act as your broker, financial advisor, or fiduciary. We provide tools and data. You retain all decision-making authority and responsibility for your trading activity.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.4 Platform Role and Brokerage Overlay</h3>
                <p>
                  Ghost Alpha Terminal is a software orchestration layer that may connect to third-party brokerages you authorize. We do not custody funds, clear trades, or execute as a broker-dealer. Your brokerage relationship remains directly between you and the relevant broker.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">3. TRADING AND INVESTMENT RISK DISCLOSURE</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.1 Risk Acknowledgment</h3>
                <p>
                  Trading and investing in securities, derivatives, and other financial instruments involve substantial risk, including potential loss of your entire investment or principal amounts. You acknowledge and accept these risks.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.2 Past Performance</h3>
                <p>
                  Historical trading results, backtests, simulations, and performance metrics presented on the Platform are not indicative of future performance. Any projections or forecasts provided are speculative and highly subject to uncertainty.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.3 Sole Responsibility</h3>
                <p>
                  You are solely responsible for evaluating the risks, appropriateness, and suitability of any trading decision or strategy. You assume full responsibility for all outcomes and losses resulting from your use of the Platform.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.4 Professional Advice</h3>
                <p>
                  We strongly recommend that you consult with independent financial, legal, and tax professionals before making trading or investment decisions.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">4. ACCOUNT AND USER CONDUCT</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.1 Account Creation</h3>
                <p>
                  To use the Platform, you must create an account and provide accurate, complete information. You are responsible for maintaining the confidentiality of your account credentials, API keys, and authentication tokens.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.2 Unauthorized Access</h3>
                <p>
                  You agree to immediately notify us of any unauthorized access to your account or any security breach. You are liable for all activities conducted through your account.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.3 Prohibited Conduct</h3>
                <p>
                  You agree not to: (a) use the Platform for illegal purposes; (b) reverse-engineer, decompile, or attempt to gain unauthorized access to Platform systems; (c) transmit viruses, malware, or harmful code; (d) interfere with Platform operations or availability; (e) engage in market manipulation, insider trading, or securities fraud; (f) violate any applicable laws, regulations, or third-party rights.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.4 Broker Connections</h3>
                <p>
                  When connecting external brokerage accounts, you authorize us to interact with those accounts on your behalf within the scope you authorize. You are responsible for any consequences of such connections and for maintaining valid broker credentials.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.5 API and Automation Restrictions</h3>
                <p>
                  You may not use automated or manual techniques to scrape, replicate, benchmark for publication, or extract model behavior from the Platform or API. You may not resell, rebroadcast, or syndicate Platform-generated signals, rankings, or trade recommendations without express written authorization.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">5. INTELLECTUAL PROPERTY RIGHTS</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.1 Platform IP</h3>
                <p>
                  All content, software, algorithms, designs, trademarks, and intellectual property within the Platform are owned by Ghost Alpha Terminal or our licensors. You acquire no ownership rights.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.2 Limited License</h3>
                <p>
                  We grant you a limited, non-exclusive, non-transferable license to access and use the Platform solely for your personal or authorized business purposes, in compliance with these Terms.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.3 User Content</h3>
                <p>
                  You retain ownership of any content you upload or create on the Platform. By uploading, you grant us a worldwide, royalty-free license to use such content for Platform operation, improvement, and support.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.4 Model and Signal Protection</h3>
                <p>
                  Platform outputs, including but not limited to model scores, strategy rankings, confidence values, and orchestration policies, are protected intellectual property and trade secrets. Any attempt to clone, infer, train on, or recreate substantially similar model behavior from Platform outputs is prohibited.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">6. SERVICE AVAILABILITY AND MODIFICATIONS</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.1 "As Is" Basis</h3>
                <p>
                  The Platform is provided on an "as is" and "as available" basis without warranties of any kind, express or implied. We do not guarantee uninterrupted, error-free, or secure service.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.2 Right to Modify</h3>
                <p>
                  We may modify, suspend, or discontinue any feature, service, or content at any time, with or without notice. We shall not be liable to you for any such modifications or interruptions.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.3 Maintenance and Downtime</h3>
                <p>
                  The Platform may be subject to scheduled or emergency maintenance, updates, or patches. During such periods, the Service may be temporarily unavailable. We strive to minimize disruption but provide no guarantee of continuous availability.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">7. LIMITATION OF LIABILITY AND INDEMNIFICATION</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.1 Exclusion of Damages</h3>
                <p>
                  To the maximum extent permitted by applicable law, Ghost Alpha Terminal shall not be liable for any indirect, incidental, special, consequential, punitive, or exemplary damages (including but not limited to damages for loss of profits, data, business opportunities, or interruption of service), even if advised of the possibility of such damages.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.2 Cap on Liability</h3>
                <p>
                  Our total aggregate liability to you for all claims arising from your use of the Platform shall not exceed the fees, if any, paid by you to us in the 12 months preceding the claim, or $100, whichever is greater.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.3 Assumption of Risk</h3>
                <p>
                  You assume all risk associated with your use of the Platform, including trading losses, system failures, data loss, and security incidents. This includes reliance on Platform-generated forecasts, signals, or rankings.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.4 Indemnification</h3>
                <p>
                  You agree to indemnify and hold harmless Ghost Alpha Terminal, its officers, directors, employees, and agents from any claims, damages, liabilities, and costs (including attorney's fees) arising from your use of the Platform, violation of these Terms, or violation of any applicable law or third-party rights.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">8. THIRD-PARTY SERVICES AND LINKS</h2>
            
            <p className="mb-3">
              The Platform may integrate with or link to third-party services, brokers, and data providers. We are not responsible for the accuracy, legality, or safety of such third-party services. Your interactions with third parties are governed by their respective terms and privacy policies.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">9. COMPLIANCE AND REGULATORY</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">9.1 Regulatory Compliance</h3>
                <p>
                  You are responsible for ensuring your use of the Platform complies with all applicable securities laws, regulations, and trading rules in your jurisdiction.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">9.2 Tax Obligations</h3>
                <p>
                  You are responsible for all tax reporting and obligations related to your trading activity. We provide no tax advice.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">9.3 Sanctions and Export Controls</h3>
                <p>
                  You agree not to use the Platform in any manner that violates export controls, sanctions, or restrictions applicable to Ghost Alpha Terminal or its jurisdictions of operation.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">10. TERMINATION</h2>
            
            <p className="mb-3">
              We may terminate or suspend your account and access to the Platform at any time, with or without cause, with or without notice. Upon termination, your right to use the Platform ceases immediately, but your obligations under these Terms continue.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">11. DISPUTE RESOLUTION</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">11.1 Governing Law</h3>
                <p>
                  These Terms are governed by and construed in accordance with the laws of the jurisdiction in which Ghost Alpha Terminal is established, without regard to its conflict of law principles.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">11.2 Jurisdiction and Venue</h3>
                <p>
                  Any disputes shall be subject to the exclusive jurisdiction of the courts in the applicable legal venue specified in your deployment or service agreement.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">11.3 Arbitration Option</h3>
                <p>
                  Where applicable, disputes may be resolved through binding arbitration in accordance with the rules specified in your service agreement.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">12. CHANGES TO TERMS</h2>
            
            <p>
              We may update these Terms from time to time. Material changes will be communicated via email or prominent notice on the Platform. Your continued use constitutes acceptance of updated Terms.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">13. CONTACT AND LEGAL INQUIRIES</h2>
            
            <p>
              For questions regarding these Terms or to report violations, contact your platform administrator or legal representative. For self-hosted deployments, refer to your deployment documentation.
            </p>
          </section>

          <div className="mt-8 p-4 border border-terminal-line/40 rounded-lg bg-black/20">
            <p className="text-xs text-slate-400">
              <strong>Important Disclaimer:</strong> These Terms represent general legal framework for Platform use. They are not comprehensive legal advice. This document is provided "as is" without warranty. Users should consult with qualified legal counsel regarding their specific rights, obligations, and regulatory responsibilities before using the Platform for trading purposes.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
