# Lesson 9: Blind Spots

Two steps remain undetected. One could be caught with better rules. The other cannot be caught with the logs this lab collects at all. Knowing which is which is the point.

---

## R01: Low and slow

A single injection attempt, then silence. Real attackers do this deliberately: one probe per hour, or one per day, from different addresses, so no threshold is ever crossed.

The logs **did** record it:

```bash
python3 bin/logs.py --since 30m --kind input_blocked
```

R01's attempt is there: a single line, a few seconds before the burst of three from R05. (Earlier lines may be your own practice from Lesson 3.) It is in the logs; it just never added up to an alert.

### How defenders catch low-and-slow activity

| Technique | Idea |
|---|---|
| **Longer windows** | Count over 24 hours or 7 days, not 5 minutes |
| **Different grouping** | Group by API key or user account, not address: attackers change addresses more easily than stolen credentials |
| **Daily reports** | A human reviews a summary of every blocked event once a day, no threshold at all |
| **Baselines** | Alert when a key's behavior differs from its own history, even at low volume |

> **Try it:** add a rule D11 to `detections/rules.json` that fires on **1** `input_blocked` within **86400** seconds (one day), with severity `low`. Re-score. Does R01 show up now? What happens to R05, and why?

---

## R12: The attacker inside the container

Look at what R12 actually did:

```
R12  Attacker inside a container    commands inside rag-api -> ['ok', 'blocked', 'blocked', 'ok']
```

It ran `id`, tried to modify the app's code, tried to install packages, and read the process environment. Part 4's hardening blocked the dangerous two. But search the logs:

```bash
python3 bin/logs.py --since 30m --summary
```

There is **nothing** from R12. No request went through NGINX, so the edge did not see it. The API did not handle a request, so the API did not log it. A command run inside a container is invisible to application logs.

### What can see it

| Tool type | Examples | Sees |
|---|---|---|
| **Runtime security** | Falco, Tetragon, cloud runtime protection | Every new process, file write, and network connection inside every container, as it happens |
| **Linux audit logging** | `auditd` | System calls on the host, including those made by containers |
| **Container platform logs** | Kubernetes audit logs | Who ran `exec` into which container |

A typical runtime security rule: "**alert if any process other than `uvicorn` starts inside `rag-api`.**" That one line would have caught every command R12 ran.

Installing and running these tools is beyond this lab, but the lesson stands: **each kind of log has a field of view.** Application logs see requests. They cannot see what happens beside the application.

---

## Final scorecard

| Step | Status | Why |
|---|---|---|
| R02 to R11 | Detected | Logged and covered by an enabled rule |
| R01 | Logged, not alerted | Below every threshold; needs longer windows or daily review |
| R12 | **Not logged at all** | Outside the field of view of application logs; needs runtime security |

The two misses are different kinds of problems. One is a **tuning** problem: the data is there. The other is a **visibility** problem: the data does not exist. Reports should say which is which, because the fixes are completely different.

---

## A third blind spot: the guessed keys

R11 counts as detected, because D10 caught the stolen chat key. But look at what the attacker did **first**: five guessed admin keys. Weaviate refused all five and logged none of them. Prove it:

```bash
bin/weaviate.sh none GET /v1/schema
docker compose logs --since 1m weaviate | grep -c -i -E 'unauthori|invalid api key|anonymous'
```

```
401
0
```

The request was refused, and Weaviate wrote nothing. Every database decides for itself what to log, and here the data simply does not exist, the same kind of problem as R12. A key-guessing attack against Weaviate is invisible unless something else records it.

How would you close it? Two common answers:
- **Put a small proxy in front of the database** that logs every request and its status, the way the NGINX edge does for the API
- **Never let an attacker get that far**: if only `rag-api` and `weaviate-init` can reach Weaviate on the network, guessing requires a compromised container, which runtime security (above) is meant to catch

This is why R11 is a **partial** detection. The scorecard says "detected," and the report should say what the scorecard cannot.

Next: [Writing the Report](10-report.md)
