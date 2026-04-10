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
        <div className="mb-8 flex items-center justify-between gap-4 border-b border-terminal-line/40 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-100">PRIVACY POLICY</h1>
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
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">1. INTRODUCTION AND SCOPE</h2>
            <p className="mb-3">
              Ghost Alpha Terminal ("Platform," "we," "us," or "our") is committed to protecting the privacy and security of user information. This Privacy Policy ("Policy") describes our practices regarding the collection, use, retention, and protection of personal and non-personal data.
            </p>
            <p>
              This Policy applies to all individuals and entities ("Users," "you," or "your") who access or use the Platform, whether as registered users, administrators, or casual visitors. By accessing or using the Platform, you consent to the practices described herein.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">2. INFORMATION WE COLLECT</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.1 Account and Authentication Data</h3>
                <p>
                  When you register an account, we collect your account credentials, email address, organizational affiliation, and authentication preferences. This information is necessary to establish and maintain your account access.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.2 Configuration and Preference Data</h3>
                <p>
                  We collect your trading configuration inputs, execution preferences, risk parameters, broker connection settings, and operational preferences necessary to customize and operate the Platform for your use case.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.3 Usage and Telemetry Data</h3>
                <p>
                  We automatically collect information about your interaction with the Platform, including feature usage, workflow activation, decision audit trails, simulation activity, and non-identifying technical metrics (IP address, user agent, browser type, session duration).
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.4 Broker-Provided Data</h3>
                <p>
                  Through authorized OAuth connections, we may receive account identifiers, portfolio holdings, order history, and execution status from connected brokerage services. We do not directly store broker credentials.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.5 Data You Do Not Provide</h3>
                <p>
                  We do not intentionally collect sensitive personal information (e.g., social security numbers, passport information, payment card data) unless explicitly authorized and required for specific functionality. Users should not share such information through unsecured channels.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">3. HOW WE USE INFORMATION</h2>
            
            <p className="mb-3">We use collected information for the following purposes:</p>
            <ul className="ml-6 space-y-2 list-disc">
              <li><strong>Service Delivery:</strong> To provide, maintain, and operate the Platform</li>
              <li><strong>Security:</strong> To detect, prevent, and address fraud, abuse, and security incidents</li>
              <li><strong>Functionality:</strong> To enable market scanning, opportunity ranking, execution workflows, and decision audit replay</li>
              <li><strong>Personalization:</strong> To customize your experience and deliver relevant features</li>
              <li><strong>Improvement:</strong> To analyze usage patterns and improve Platform performance and features</li>
              <li><strong>Communication:</strong> To send service updates, security alerts, and administrative notices (where applicable)</li>
              <li><strong>Compliance:</strong> To meet legal, regulatory, and contractual obligations</li>
              <li><strong>Analytics:</strong> To measure conversion, engagement, and feature adoption (non-identifying)</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">4. DATA SHARING AND DISCLOSURE</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.1 Third-Party Service Providers</h3>
                <p>
                  We may share data with third-party service providers (infrastructure hosts, analytics providers, brokerage integrations) only as necessary to deliver core Platform functionality. These providers are bound by confidentiality agreements and security obligations.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.2 Brokerage Partners</h3>
                <p>
                  To execute trades and retrieve market data, we share relevant order directives and account information with connected broker platforms. Each broker's privacy practices are governed by their respective terms.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.3 No Sale of Personal Data</h3>
                <p>
                  We do not sell, rent, lease, or otherwise disclose personal data to third parties for marketing or commercial purposes.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.4 Legal Compliance</h3>
                <p>
                  We may disclose information when required by law, court order, subpoena, or governmental request, or when necessary to protect the rights, safety, and property of Ghost Alpha Terminal, users, or the public.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.5 Business Transitions</h3>
                <p>
                  In the event of merger, acquisition, bankruptcy, or sale of assets, user data may be transferred as part of that transaction. We will notify users of any material changes to this Policy via email or prominent notice on the Platform.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">5. DATA RETENTION</h2>
            
            <p className="mb-3">
              We retain information for as long as necessary to operate the Platform, fulfill contractual obligations, comply with legal and regulatory requirements, and resolve disputes. Retention periods vary by data type:
            </p>
            <ul className="ml-6 space-y-2 list-disc">
              <li><strong>Account Data:</strong> Retained for the duration of your account and as required by law</li>
              <li><strong>Transaction Records:</strong> Retained for audit, compliance, and tax purposes (typically 7 years)</li>
              <li><strong>Usage Logs:</strong> Retained for 90 days unless needed for security investigations</li>
              <li><strong>Telemetry Data:</strong> Retained for aggregate analysis (typically 12-24 months)</li>
            </ul>
            <p className="mt-3">
              You may request deletion of eligible personal data in accordance with applicable privacy laws. We will respond to verified requests within the timeframe specified by law.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">6. SECURITY AND DATA PROTECTION</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.1 Technical Controls</h3>
                <p>
                  We implement industry-standard security measures including encryption in transit (TLS/SSL), session authentication, access controls, and regular security testing. See our Cybersecurity Policy for detailed technical protections.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.2 Organizational Controls</h3>
                <p>
                  We maintain security policies, staff training, incident response procedures, and vendor management practices. Access to user data is restricted to authorized personnel on a need-to-know basis.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.3 Limitation of Warranties</h3>
                <p>
                  While we implement reasonable security measures, no system is completely secure. We cannot guarantee absolute protection against all potential security threats. Users are responsible for safeguarding their credentials, API keys, and account access.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">7. USER RIGHTS AND CHOICES</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.1 Access and Portability</h3>
                <p>
                  You may request access to the personal data we hold about you and, where applicable, request data portability in structured format.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.2 Correction and Deletion</h3>
                <p>
                  You may request correction of inaccurate data or deletion of your account. Some data may be retained for legal or operational reasons.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.3 Opt-Out</h3>
                <p>
                  You may opt out of non-essential communications (marketing, feature announcements) through account settings. Essential service notifications cannot be disabled.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">8. CHILDREN AND MINORS</h2>
            
            <p>
              The Platform is not intended for individuals under 18 years of age. We do not knowingly collect data from minors. If we learn that we have collected such data, we will take prompt steps to delete it.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">9. INTERNATIONAL DATA TRANSFERS</h2>
            
            <p>
              Your data may be processed and stored in multiple jurisdictions. By using the Platform, you consent to transfer of your information to countries other than your country of residence, which may have different data protection rules.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">10. POLICY UPDATES</h2>
            
            <p>
              We may update this Privacy Policy from time to time. Material changes will be communicated via email or prominent Platform notice. Your continued use of the Platform constitutes acceptance of the updated Policy.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">11. CONTACT AND INQUIRIES</h2>
            
            <p>
              For privacy inquiries, data requests, or concerns, please contact your platform administrator or legal representative. For self-hosted deployments, refer to your deployment documentation for privacy contact information.
            </p>
          </section>

          <div className="mt-8 p-4 border border-terminal-line/40 rounded-lg bg-black/20">
            <p className="text-xs text-slate-400">
              <strong>Disclaimer:</strong> This Privacy Policy is provided for informational purposes. It is not legal advice. Specific privacy rights and obligations may vary by jurisdiction. Users should consult with legal counsel regarding their specific privacy requirements and obligations.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
