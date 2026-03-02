# CISA Cybersecurity Guidance

**Source:** https://www.cisa.gov/cybersecurity

---

## Shields Up — General Guidance for All Organizations

CISA's Shields Up guidance recommends all organizations — regardless of size — adopt
heightened cybersecurity posture. Key actions:

### Reduce Likelihood of Damaging Intrusion
- Validate all remote access requires MFA.
- Ensure software is up to date, prioritizing CISA's Known Exploited Vulnerabilities catalog.
- Confirm IT personnel have disabled all ports and protocols not essential for business purposes.
- If using cloud services, ensure IT personnel review and implement strong controls.
- Sign up for CISA's free cyber hygiene services including vulnerability scanning.

### Take Steps to Quickly Detect a Potential Intrusion
- Ensure cybersecurity/IT staff are focused on identifying and assessing any unexpected network behavior.
- Enable logging in order to investigate issues or events.
- Confirm that the organization's entire network is protected by antivirus/antimalware software.
- If you have relationships with managed security service providers (MSSPs), confirm they are monitoring for threats.

### Ensure Organization is Prepared to Respond
- Designate a crisis response team with main points of contact.
- Assure availability of key personnel; identify means to provide urgent support.
- Conduct a tabletop exercise to ensure awareness of roles in a cyber incident.
- Review continuity plans to ensure critical business functions can continue during an incident.

### Maximize Resilience
- Test backup procedures and ensure backups are isolated from network connections.
- If using industrial control systems, test manual controls to ensure systems can operate if network unavailable.
- Exercise your incident response plan.

---

## StopRansomware.gov — Ransomware Response Guidance

### Immediate Response to Ransomware Attack
1. **Isolate infected systems** — Disconnect from the network immediately. Do not shut down (preserves forensic evidence in memory).
2. **Identify the scope** — Determine which systems are affected.
3. **Preserve evidence** — Take forensic images before remediation.
4. **Do not pay the ransom** — Payment does not guarantee data recovery and funds criminal activity.
5. **Report immediately:**
   - CISA: report.cisa.gov
   - FBI: ic3.gov
   - Secret Service (if financial sector)
6. **Restore from clean backups** — Verify backups are clean before restoring.
7. **Identify and remediate the initial access vector** to prevent reinfection.

### Ransomware Prevention Best Practices
- Maintain offline, encrypted backups of data and test recovery regularly.
- Create, maintain, and exercise a cyber incident response plan.
- Keep all operating systems, software, and firmware up to date.
- Segment networks to prevent spread of ransomware.
- Use MFA for all remote access and administrative accounts.
- Implement application allowlisting.
- Disable unnecessary services (RDP if not needed, etc.).
- Implement email filtering and web filtering.
- Train employees on phishing and social engineering.

---

## Free CISA Services Available to Organizations
- **Cyber Hygiene Vulnerability Scanning:** Free external vulnerability scanning for internet-facing systems.
- **Phishing Campaign Assessment:** Simulated phishing exercises.
- **Remote Penetration Testing:** For critical infrastructure sectors.
- **Incident Response:** Free assistance for significant incidents.
- **Cybersecurity Advisories:** Sign up at cisa.gov/uscert for alerts.
- **CyberSentry:** Network monitoring for critical infrastructure.

---

## CISA Alert: Common Initial Access Vectors
Based on CISA incident response data, the most common ways attackers gain initial access:
1. Phishing (email with malicious link or attachment)
2. Exploitation of public-facing applications (unpatched vulnerabilities)
3. External remote services (RDP, VPN without MFA)
4. Valid accounts (credential stuffing, purchased credentials)
5. Supply chain compromise
6. Trusted relationships (compromising a third-party with access)
