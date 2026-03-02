# NIST SP 800-61 Rev 2 — Computer Security Incident Handling Guide

**Source:** https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
**Purpose:** Guidelines for incident handling, particularly for analyzing incident-related data
and determining the appropriate response to each incident.

---

## 1. Incident Response Overview

### Definition of a Computer Security Incident
A computer security incident is a violation or imminent threat of violation of computer security
policies, acceptable use policies, or standard security practices.

### Types of Incidents
- **Denial of Service (DoS/DDoS):** Attacks that prevent or impair authorized use of networks, systems, or applications.
- **Malicious Code:** Viruses, worms, Trojan horses, ransomware, and other attack scripts.
- **Unauthorized Access:** Gaining logical or physical access without permission.
- **Inappropriate Usage:** Violating acceptable use policies (e.g., misuse of systems).
- **Account Compromise / Identity Theft:** Unauthorized use of user or administrator credentials.
- **Phishing and Social Engineering:** Attempts to deceive users into revealing sensitive information.
- **Data Breach:** Unauthorized access to or disclosure of sensitive data.
- **Ransomware:** Malware that encrypts files and demands payment for decryption.

---

## 2. Incident Response Life Cycle

### Phase 1: Preparation
- Establish incident response policy and plan.
- Create incident response team (IRT) with defined roles.
- Establish communications plans including escalation procedures.
- Ensure proper tools and resources are available (forensic workstations, backup systems, etc.).
- Conduct regular training and exercises.
- Establish relationships with external parties (ISPs, law enforcement, legal counsel).

### Phase 2: Detection and Analysis
- Monitor systems using SIEM, IDS/IPS, antivirus, log analysis tools.
- Identify signs of incidents: precursors (indicators something may happen) and indicators (signs incident is occurring).
- Common detection sources: security alerts, log files, error messages, user reports.
- Prioritize incidents based on business impact, data sensitivity, and recoverability.
- Document everything — time, actions taken, evidence found.

**Incident Severity Classification:**
- **Critical:** Threatens life safety, causes significant financial loss, impacts critical infrastructure.
- **High:** Sensitive data compromised, widespread system impact, regulatory reporting required.
- **Medium:** Limited impact, single system affected, no sensitive data exposed.
- **Low:** Minor policy violation, no significant impact.

### Phase 3: Containment, Eradication, and Recovery
**Containment:**
- Short-term: Immediately limit damage (isolate affected systems, disable compromised accounts).
- Long-term: Implement more robust measures (network segmentation, additional monitoring).
- Preserve evidence before containment where possible.

**Eradication:**
- Identify and eliminate root cause of the incident.
- Remove malware, close vulnerabilities, patch systems.
- Verify all affected systems are clean.

**Recovery:**
- Restore systems and data from clean backups.
- Monitor restored systems closely for signs of re-compromise.
- Confirm normal operations are restored.

### Phase 4: Post-Incident Activity
- Conduct lessons-learned meeting within 2 weeks of incident resolution.
- Document what happened, how it was detected, actions taken, costs, and improvements needed.
- Update incident response plan and security controls based on findings.
- Retain evidence per legal and policy requirements.

---

## 3. Incident Response for Specific Attack Types

### Account Compromise Response Steps
1. Immediately lock/disable the compromised account.
2. Force password reset for affected accounts and any accounts that may share credentials.
3. Enable/require multi-factor authentication (MFA).
4. Review account activity logs to understand scope of access.
5. Check for persistence mechanisms (new accounts created, forwarding rules set, API keys issued).
6. Notify affected users and relevant stakeholders.
7. Report to appropriate authorities if required.

### Ransomware Response Steps
1. Isolate infected systems from the network immediately.
2. Identify the scope — which systems are affected.
3. Do NOT pay the ransom without consulting law enforcement and legal counsel.
4. Preserve forensic evidence.
5. Restore from clean, verified backups.
6. Report to FBI IC3 (ic3.gov) and CISA.
7. Investigate the initial attack vector and close it.

### Data Breach Response Steps
1. Contain the breach — stop ongoing unauthorized access.
2. Assess what data was compromised (type, volume, individuals affected).
3. Notify affected individuals as required by law.
4. Report to regulatory bodies per applicable regulations (GDPR, HIPAA, state laws).
5. Engage legal counsel.
6. Offer credit monitoring services to affected individuals if appropriate.
7. Remediate vulnerabilities that allowed the breach.

### Phishing Response Steps
1. Do not click links or open attachments in suspicious emails.
2. Report the phishing attempt to your IT/security team.
3. If credentials were entered, immediately change passwords and enable MFA.
4. If malware may have been installed, isolate the device.
5. Report to the Anti-Phishing Working Group (reportphishing@apwg.org).
6. Report phishing emails impersonating companies to the spoofed organization.
