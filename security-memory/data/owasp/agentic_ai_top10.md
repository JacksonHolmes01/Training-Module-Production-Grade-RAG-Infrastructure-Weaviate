# OWASP Top 10 for Agentic AI Applications (ASI) — December 2025
**Source:** https://owasp.org/www-project-agentic-security/

## ASI-01: Prompt Injection in Agentic Contexts
Malicious inputs manipulate autonomous agents to perform unauthorized actions or exfiltrate data.

## ASI-02: Inadequate Human Oversight
Agents taking high-impact or irreversible actions without human-in-the-loop checkpoints.

## ASI-03: Excessive Tool Access
Agents granted broader tool/API access than required, violating least privilege.

## ASI-04: Memory and Context Manipulation
Attacks targeting agent memory systems to corrupt reasoning or inject persistent malicious instructions.

## ASI-05: Multi-Agent Trust Exploitation
Malicious agents impersonating trusted orchestrators to inject instructions into pipelines.

## ASI-06: Unbounded Resource Consumption
Agents entering infinite loops, spawning excessive sub-agents, or consuming disproportionate resources.

## ASI-07: Sensitive Data Exfiltration via Agent Actions
Agents covertly exfiltrating sensitive information through tool calls or generated outputs.

## ASI-08: Insecure Inter-Agent Communication
Lack of authentication and integrity checks between agents in multi-agent systems.

## ASI-09: Cascading Failures in Agent Pipelines
A failure in one agent propagating through an entire agentic workflow.

## ASI-10: Goal Misalignment and Reward Hacking
Agents pursuing objectives in unintended ways that satisfy goal specifications but violate intent.
