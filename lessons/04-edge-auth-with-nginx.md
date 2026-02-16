# Lesson 4 — Edge Authentication with NGINX (API Key Gate)

## Learning objectives

By the end of this lesson, you will be able to:

- Explain what an **edge proxy** is and why it exists in production systems.
- Describe how API-key authentication works in this lab (headers + allow/deny).
- Use `curl` to test failure and success cases (401 vs 403 vs 200).
- Explain why we also enforce the API key **inside** the FastAPI service (defense-in-depth).

---

## Step 1 — What is NGINX doing in this lab?

NGINX is acting like a “front door” (gateway) for API requests.

It is the only service exposed on:

- `http://localhost:8088`

Everything else stays internal.

If a request does not include the correct API key, NGINX blocks it.

### Why this is a good production pattern

- You can enforce auth before traffic reaches internal services.
- You can add rate limiting, logging, and TLS termination later.
- You keep your database private.

---

## Step 2 — Where the NGINX rule lives

Open:

- `nginx/templates/default.conf.template`

You will see rules like:

- if no `X-API-Key` header → return **401**
- if header is wrong → return **403**
- if correct → proxy to `ingestion-api:8000`

The key itself comes from your `.env` file as `EDGE_API_KEY`.

---

## Step 3 — Test NGINX in a beginner-friendly way

### 3.1 Check proxy health (no key required)

```bash
curl -i http://localhost:8088/proxy-health
```

Expected:
- status `200`
- body `ok`

This confirms the proxy itself is running.

### 3.2 Test a protected endpoint WITHOUT a key

```bash
curl -i http://localhost:8088/health
```

Expected:
- status `401`

### 3.3 Test with the correct key

First read the key from `.env`:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

Now call:

```bash
curl -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health
```

Expected:
- status `200`
- JSON response like `{ "ok": true, ... }`

---

## Step 4 — 401 vs 403 (super common beginner confusion)

- **401 Unauthorized** = “You didn’t provide credentials.”  
  (Missing `X-API-Key`)

- **403 Forbidden** = “You provided credentials, but they are not allowed.”  
  (Wrong key)

Remember:
- 401 = missing
- 403 = wrong

---

## Step 5 — Defense-in-depth (why the API also checks the key)

NGINX blocks external access, but we also enforce the API key inside the FastAPI service.

Why?

Because production security assumes something can go wrong:

- Someone might misconfigure NGINX.
- A future engineer might expose the API container by accident.
- A compromised container might attempt internal calls.

Having two layers helps you fail closed.

In `ingestion-api/app/main.py`, look for `require_api_key()`.

That function checks the same header.

---

## Step 6 — What you should include in your submission

Take screenshots or record:

- A `curl` call without key (shows 401)
- A `curl` call with wrong key (shows 403)
- A `curl` call with correct key (shows 200)

This proves the boundary is working.

---

## Common issues & fixes

- **You changed `.env` but auth still fails**  
  If `.env` changed after containers started, restart:

  ```bash
  docker compose up -d
  ```

- **You get 403 even with the correct key**  
  Verify the key string has no extra spaces or quotes. Re-copy the value exactly.

---

## Checkpoints (what to prove)

- `/health` returns 401 without a header.
- `/health` returns 403 with an incorrect header.
- `/health` returns 200 with the correct header.
- You can explain why having both NGINX auth and API auth is stronger than only one.
