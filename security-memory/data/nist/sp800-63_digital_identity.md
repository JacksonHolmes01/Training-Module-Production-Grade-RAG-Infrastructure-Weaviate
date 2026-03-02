# NIST SP 800-63 — Digital Identity Guidelines

**Source:** https://pages.nist.gov/800-63-3/
**Covers:** Identity proofing, authentication, and federation for digital services.

---

## Authentication Assurance Levels (AAL)

### AAL1 — Single-Factor Authentication
- Provides confidence that the claimant controls an authenticator registered to the subscriber.
- Permitted authenticators: memorized secrets (passwords), single-factor OTP, etc.
- Suitable for low-risk applications.

### AAL2 — Two-Factor Authentication (Recommended for most applications)
- Provides high confidence that the claimant controls authenticators registered to the subscriber.
- Requires two different authentication factors.
- Permitted: MFA cryptographic devices, OTP devices, out-of-band authentication.
- Required for applications handling sensitive data or transactions.

### AAL3 — Hardware-Based Authentication
- Provides very high confidence.
- Requires hardware-based authenticator and verifier impersonation resistance.
- Required for high-value transactions and privileged access.

---

## Password Best Practices (NIST SP 800-63B)

### What NIST Recommends
- **Minimum length:** 8 characters; allow up to at least 64 characters.
- **Allow all printable ASCII characters** including spaces.
- **Check passwords against known compromised password lists** (Have I Been Pwned, etc.).
- **Do NOT require periodic password changes** unless compromise is suspected.
- **Do NOT require complexity rules** (uppercase, numbers, symbols) — these reduce security.
- **Allow password managers** — do not block paste functionality.
- **Limit failed authentication attempts** to prevent brute force attacks.

### What NIST Says to Stop Doing
- Stop requiring mandatory password rotation on a schedule.
- Stop requiring complex composition rules.
- Stop using security questions as a recovery method.
- Stop using SMS as the only MFA option (it is allowed but not preferred).

---

## Account Recovery Best Practices
- Use secure out-of-band channels for account recovery.
- Require identity re-proofing for sensitive account recovery actions.
- Do not use knowledge-based questions (mother's maiden name, first pet) — they are prohibited.
- Notify users of account recovery attempts via a verified secondary channel.
- Implement rate limiting and anomaly detection on recovery flows.

---

## Multi-Factor Authentication (MFA) Guidance
- **Preferred MFA methods (most secure to least):**
  1. Hardware security keys (FIDO2/WebAuthn) — phishing resistant
  2. Authenticator apps (TOTP like Google Authenticator, Authy)
  3. Push notifications (Duo, Microsoft Authenticator)
  4. SMS/email OTP — allowed but vulnerable to SIM swapping and interception
- Enable MFA on all accounts, especially email, financial, and administrative accounts.
- Backup codes should be treated like passwords — store securely.
