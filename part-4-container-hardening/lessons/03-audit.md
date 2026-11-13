# Lesson 3: Auditing the Containers

Before changing anything, measure. `bin/audit.py` inspects every running container in this lab and checks nine things.

---

## Run the audit

```bash
python3 bin/audit.py --explain
```

### What you will see

```
Project: secure-ai-weaviate-part4

CONTAINER          non-root     no-caps no-escalate   read-only no-env-keys   mem-limit   pid-limit       ports      pinned   SCORE
-----------------------------------------------------------------------------------------------------------------------------------
rag-api                FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
rag-nginx              FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
rag-ollama             FAIL        FAIL        FAIL        FAIL        pass        pass        FAIL        pass        FAIL     3/9
rag-ui                 FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
rag-weaviate           FAIL        FAIL        FAIL        FAIL        pass        pass        pass        pass        FAIL     4/9
-----------------------------------------------------------------------------------------------------------------------------------
Total: 13 of 45 checks pass (28%)
```

followed by an explanation of every failure.

---

## The nine checks

| Check | Passes when | Where the setting lives |
|---|---|---|
| `non-root` | The container starts as a user other than root | `user:` in compose, or `USER` in a Dockerfile |
| `no-caps` | Every Linux capability is dropped | `cap_drop: [ALL]` |
| `no-escalate` | Processes cannot gain privileges | `security_opt: ["no-new-privileges:true"]` |
| `read-only` | The container's own filesystem cannot be changed | `read_only: true` |
| `no-env-keys` | No secret-looking value is in an environment variable | Secrets mounted as files |
| `mem-limit` | A memory limit is set | `mem_limit:` |
| `pid-limit` | A process-count limit is set | `pids_limit:` |
| `ports` | Nothing is published, or only to `127.0.0.1` | `ports:` |
| `pinned` | The image is pinned by digest | `image: name@sha256:...` |

The audit reads only what Docker reports (`docker inspect`). It changes nothing.

---

## What the baseline tells you

- **Two checks already pass everywhere:** memory limits and localhost-only ports. Both were set in Part 3
- **Weaviate** passes `pid-limit` because Part 3 gave it one; the others never got one
- **Every container runs as root**, keeps its capabilities, and has a writable filesystem
- **Three containers** (`rag-api`, `rag-nginx`, `rag-ui`) have `EDGE_API_KEY` in their environment

### A false alarm worth understanding

The audit skips one variable on purpose:

```python
NOT_SECRET = {"GPG_KEY", "AUTHENTICATION_APIKEY_ENABLED", "AUTHENTICATION_APIKEY_USERS"}
```

- The official Python image sets `GPG_KEY` to the **public** fingerprint used to verify the Python download. Its name matches the "secret" pattern, but its value is meant to be public.
- Weaviate's `AUTHENTICATION_APIKEY_ENABLED` is an on/off switch (`true`), and `AUTHENTICATION_APIKEY_USERS` is a list of user **names** (`admin,rag-writer,rag-reader`). Both contain "KEY" in their names, but neither holds a key. The real keys are read from a secret file at startup (Part 3, Lesson 2).

Check this for yourself instead of trusting the list:

```bash
docker inspect rag-weaviate --format '{{range .Config.Env}}{{println .}}{{end}}' | grep APIKEY
```

The first version of this lab's audit flagged Weaviate for both. Reading the values showed they were safe. Every security tool needs rules like this, and each one should say **why** it exists, so the next person does not have to guess.

---

## Start a scoreboard

| Layers on | Audit score |
|---|---|
| None | 13 of 45 (28%) |
| + 1 non-root | |
| + 2 capabilities | |
| + 3 read-only | |
| + 4 secrets | |
| + 5 internal TLS | |
| + 6 pinned | |

Next: [Thinking Like an Attacker Inside a Container](04-attacker-demo.md)
