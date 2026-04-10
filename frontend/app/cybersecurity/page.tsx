import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cybersecurity & Security Practices | GHOST ALPHA TERMINAL",
  description: "Cybersecurity protections, risks, and security practices for GHOST ALPHA TERMINAL",
};

export default function CybersecurityPage() {
  return (
    <main className="min-h-screen px-5 py-8 md:px-10 md:py-10 lg:px-16">
      <section className="mx-auto max-w-4xl rounded-2xl border border-terminal-line bg-terminal-panel/70 p-6 md:p-8">
        <div className="mb-8 flex items-center justify-between gap-4 border-b border-terminal-line/40 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-100">CYBERSECURITY & SECURITY PRACTICES</h1>
            <p className="mt-2 text-xs uppercase tracking-wider text-slate-400">Ghost Alpha Terminal</p>
          </div>
          <Link href="/" className="text-xs text-terminal-accent hover:underline">
            Back to Home
          </Link>
        </div>

        <div className="mb-6 bg-black/30 p-4 rounded-lg border border-terminal-line/40">
          <p className="text-xs text-slate-400"><strong>Last Updated:</strong> April 9, 2026</p>
          <p className="text-xs text-slate-400 mt-2"><strong>Classification:</strong> Security & Compliance Documentation</p>
        </div>

        <div className="space-y-8 text-sm leading-relaxed text-slate-300">
          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">1. INTRODUCTION</h2>
            
            <p className="mb-3">
              Ghost Alpha Terminal ("Platform") recognizes that cybersecurity is critical to protecting user data, financial information, platform integrity, and trading activity. This document describes our security architecture, protections, known risks, and best practices.
            </p>
            <p>
              This document is for informational purposes and does not constitute a warranty of absolute security or compliance with specific regulatory frameworks. Organizations should conduct independent security assessments and risk evaluations.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">2. SECURITY ARCHITECTURE AND CONTROLS</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.1 Encryption in Transit</h3>
                <p>
                  All network communications are protected using TLS 1.2 or higher. Connections between client browsers, frontend servers, and backend services use authenticated, encrypted channels. API communications enforce certificate validation and secure handshakes.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.2 Encryption at Rest</h3>
                <p>
                  Sensitive data including credentials, API tokens, and session information are encrypted at rest using industry-standard algorithms (AES-256). Database encryption is enabled for supported storage tiers.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.3 Authentication and Authorization</h3>
                <p>
                  The Platform implements session-based authentication with secure cookie management (HttpOnly, Secure, SameSite flags). Multi-factor authentication (MFA) support is available. Role-based access control (RBAC) enforces field-level and resource-level authorization.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.4 OAuth Integration</h3>
                <p>
                  Broker connections utilize OAuth 2.0 flows where available, preventing direct credential exposure. Refresh tokens are stored securely and rotated according to broker policies. Access tokens are never logged or cached in plaintext.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.5 API Security</h3>
                <p>
                  API endpoints enforce rate limiting, input validation, and output encoding to prevent abuse and injection attacks. API keys are hashed before storage. Cross-Origin Resource Sharing (CORS) policies restrict requests to authorized domains.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.6 Input Validation and Output Encoding</h3>
                <p>
                  All user inputs are validated and sanitized to prevent SQL injection, cross-site scripting (XSS), and command injection attacks. Output encoding is applied contextually (HTML, URL, JavaScript).
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.7 Web Application Firewall (WAF)</h3>
                <p>
                  Where applicable, a Web Application Firewall is deployed to detect and block common attack patterns (SQL injection, XSS, DDoS, etc.) before they reach the application.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.8 Logging and Monitoring</h3>
                <p>
                  Security events, authentication attempts, API calls, and system activities are logged with timestamps and audit trails. Logs are centralized, encrypted, and retained for compliance periods. Real-time alerting is configured for suspicious activities.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.9 Infrastructure Security</h3>
                <p>
                  Infrastructure is deployed on isolated, network-segmented environments with strict firewall rules. Virtual private networks (VPNs) and bastion hosts control administrative access. Infrastructure uses publicly disclosed, patched versions of operating systems and dependencies.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">2.10 Secrets Management</h3>
                <p>
                  API keys, database credentials, and other secrets are managed through secure vaults (not stored in code repositories or configuration files). Automatic rotation policies are implemented for long-lived credentials.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">3. VULNERABILITY MANAGEMENT</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.1 Dependency Scanning</h3>
                <p>
                  Third-party dependencies are scanned for known vulnerabilities using automated vulnerability scanners (OWASP, Snyk, etc.). Vulnerable dependencies are flagged and remediation is prioritized.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.2 Code Review and SAST</h3>
                <p>
                  All code changes undergo peer review before deployment. Static Application Security Testing (SAST) tools scan for common programming errors and security flaws in source code.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.3 Penetration Testing</h3>
                <p>
                  Regular penetration tests are conducted by internal teams or qualified third-party security firms to identify exploitable vulnerabilities before attackers discover them.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.4 Security Patching</h3>
                <p>
                  Security updates and patches are applied promptly to all systems, libraries, and infrastructure components. Patch management processes prioritize critical and high-severity vulnerabilities.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">3.5 Responsible Disclosure</h3>
                <p>
                  Security researchers and users who discover vulnerabilities are encouraged to report them through responsible disclosure channels. Reports are triaged, investigated, and patched prior to public disclosure.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">4. DATA PROTECTION AND PRIVACY</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.1 Minimal Data Collection</h3>
                <p>
                  Only data necessary for Platform operation is collected. Users should never transmit sensitive personal information through unsecured channels.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.2 Data Retention Limits</h3>
                <p>
                  Personal and operational data are retained only as long as needed. Logs are purged according to retention schedules. Backup data includes encrypted, air-gapped copies.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.3 Access Controls</h3>
                <p>
                  Access to user data is restricted to authorized personnel on a need-to-know basis. Database access is audited and logged. Administrative access requires MFA and is subject to approval workflows.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">4.4 Data Integrity Verification</h3>
                <p>
                  Database integrity is verified through checksums, hashing, and cryptographic signatures where applicable. Unauthorized modifications trigger alerts.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">5. KNOWN SECURITY RISKS AND LIMITATIONS</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.1 No System Is 100% Secure</h3>
                <p>
                  Despite robust controls, no system can guarantee absolute protection against all threats. Zero-day vulnerabilities, advanced persistent threats (APTs), and sophisticated social engineering may bypass technical controls.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.2 Broker API Risks</h3>
                <p>
                  When connecting to external brokers via OAuth or API, those integrations inherit the security characteristics of the partner broker. API rate limits, service availability, and broker-side breaches may impact Platform functionality.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.3 User Credential Compromise</h3>
                <p>
                  If a user's login credentials are compromised (password leak, phishing, keylogger), an attacker can access the user's account. Users who reuse passwords across platforms are at higher risk.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.4 API Key and Token Exposure</h3>
                <p>
                  If API keys, broker tokens, or OAuth tokens are exposed (logged in plaintext, checked into version control, shared via email), an attacker can impersonate the user or pivot to connected systems.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.5 Social Engineering and Phishing</h3>
                <p>
                  Attackers may impersonate Ghost Alpha Terminal or brokers to trick users into revealing credentials, API keys, or personal information. No technical control can fully prevent user error.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.6 Cloud Infrastructure Risk</h3>
                <p>
                  If the Platform is deployed on cloud infrastructure, inherited risks from the cloud provider (compromised hypervisor, misconfigured storage buckets, insider threats) may apply.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.7 Insider Threats</h3>
                <p>
                  Malicious or compromised employees with Platform access could potentially exfiltrate data, modify trading logic, or launch attacks. Background checks, security training, and activity monitoring mitigate but do not eliminate this risk.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.8 Third-Party Dependency Risks</h3>
                <p>
                  The Platform relies on open-source and commercial libraries. Vulnerabilities, malware, or supply-chain attacks in dependencies could compromise the Platform despite our scanning efforts.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.9 Network-Level Attacks</h3>
                <p>
                  Man-in-the-middle (MITM), DNS hijacking, or BGP hijacking attacks could intercept or redirect Platform traffic. While encryption and certificate pinning mitigate these, sophisticated attackers may still evade defenses.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">5.10 Unpatched Systems</h3>
                <p>
                  If users access the Platform from unpatched computers (outdated OS, missing security updates), their devices could be compromised even if the Platform is secure.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">6. INCIDENT RESPONSE</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.1 Incident Detection</h3>
                <p>
                  Security monitoring systems, intrusion detection systems (IDS), and alerting rules continuously monitor for suspicious activities. Anomalies are escalated automatically.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.2 Response Team and Playbook</h3>
                <p>
                  A dedicated incident response team follows established playbooks for various threat scenarios. Response procedures include isolation, forensics, containment, eradication, and recovery steps.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.3 Communication and Notification</h3>
                <p>
                  In the event of a confirmed data breach, affected users will be notified as required by applicable law. Regulatory bodies and partner organizations will be informed according to contractual and legal obligations.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">6.4 Forensics and Post-Incident Analysis</h3>
                <p>
                  After an incident, forensic analysis is conducted to determine root cause, scope of compromise, and remediation steps. Findings are documented and used to improve preventive controls.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">7. COMPLIANCE AND STANDARDS</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.1 Regulatory Compliance</h3>
                <p>
                  The Platform is designed to support compliance with applicable regulations including data protection laws (GDPR, CCPA), financial regulations (SOX, MiFID II), and cybersecurity frameworks (NIST, CIS).
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.2 Security Standards</h3>
                <p>
                  Security practices align with industry standards including OWASP Top 10, SANS Top 25, and cloud security best practices. The Platform supports SOC 2, ISO 27001, and similar certification frameworks.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">7.3 Regular Audits</h3>
                <p>
                  Security controls are subject to regular internal audits and periodic third-party assessments. Findings are tracked and remediated according to risk levels.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">8. USER SECURITY BEST PRACTICES</h2>
            
            <div className="ml-4 space-y-4">
              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.1 Strong Passwords</h3>
                <p>
                  Use unique, complex passwords (16+ characters, mixed case, numbers, symbols) for your Platform account. Never reuse passwords across multiple services. Consider using a password manager.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.2 Multi-Factor Authentication (MFA)</h3>
                <p>
                  Enable MFA (TOTP, hardware keys, or SMS) on your account. This significantly reduces the risk of unauthorized access even if your password is compromised.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.3 Phishing Awareness</h3>
                <p>
                  Be suspicious of unsolicited emails, messages, or pop-ups asking you to enter credentials or API keys. Verify URLs before entering sensitive information. Contact support directly if unsure.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.4 API Key Management</h3>
                <p>
                  Never share API keys, bearer tokens, or OAuth refresh tokens. Treat them like passwords. Rotate API keys regularly. Revoke compromised keys immediately.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.5 Device Security</h3>
                <p>
                  Keep your computer and mobile devices updated with the latest OS and security patches. Use antivirus software and a firewall. Be cautious with downloaded files and browser extensions.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.6 Network Security</h3>
                <p>
                  Avoid accessing the Platform over unsecured public WiFi networks. Use a VPN if available. Don't assume any public network is secure.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.7 Session Management</h3>
                <p>
                  Log out of your account when finished, especially on shared devices. Monitor active sessions and revoke any unrecognized logins.
                </p>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-2">8.8 Breach Response</h3>
                <p>
                  If you suspect your account or credentials have been compromised, change your password immediately, enable MFA, and contact support. Review your account activity for unauthorized transactions.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">9. SECURITY RESEARCH AND DISCLOSURE</h2>
            
            <p className="mb-3">
              We welcome security researchers and the community to identify and report vulnerabilities responsibly. Please do not publicly disclose vulnerabilities before we have had time to patch them. All vulnerability reports are treated confidentially and investigated promptly.
            </p>
            <p>
              Individuals who responsibly disclose vulnerabilities that are not already known may be acknowledged by the Platform.
            </p>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-bold text-terminal-accent border-b border-terminal-line/40 pb-2">10. CONTACT AND QUESTIONS</h2>
            
            <p>
              For security questions, vulnerability reports, or concerns, contact your platform administrator or security team. For enterprise deployments, refer to your service agreement for security contacts.
            </p>
          </section>

          <div className="mt-8 p-4 border border-terminal-line/40 rounded-lg bg-black/20">
            <p className="text-xs text-slate-400">
              <strong>Important Disclaimer:</strong> This document describes the security architecture and practices of Ghost Alpha Terminal. It is not a guarantee of complete protection against all threats. Security is a continuous process, and threat landscapes evolve. Organizations should conduct independent risk assessments, security audits, and consult with security professionals before deploying the Platform for critical trading operations. No warranty or indemnification is provided regarding the effectiveness of these security measures.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
