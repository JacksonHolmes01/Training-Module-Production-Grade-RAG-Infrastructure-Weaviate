# Prompt 02 — docker-compose.yml Security Review

## Step 1: Make sure you are in the repo root

Open your terminal in VS Code or Cursor (`` Ctrl+` `` or **Terminal > New Terminal**).

Confirm you are in the repo root by running `pwd` — the output should end with your repo folder name.
If not, run `cd /path/to/your/repo` to navigate there.

## Step 2: Retrieve security references

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "docker compose security best practices secrets ports privileged mounts networks resource limits",
    "tags": ["docker","cis"],
    "top_k": 10
  }' > /tmp/compose_security_refs.json
```

## Step 3: Extract the plain text from the results

```python
python3 -c "
import json
data = json.load(open('/tmp/compose_security_refs.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

Copy all the text that prints out — you will paste it into the chat in the next step.

## Step 4: Open the IDE chat and paste this prompt

Open `docker-compose.yml` in your IDE by clicking it in the file explorer.
Then open the AI chat panel (`Ctrl+Alt+I` in VS Code, `Cmd+L` in Cursor) and paste the following,
replacing the placeholders with the text you copied in Step 3 and the contents of your docker-compose.yml:

---

I am going to give you a set of security reference chunks retrieved from a vector database of security standards.
After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

Focus especially on: exposed ports, plaintext secrets, privileged mode, host volume mounts,
network exposure, and missing resource limits.

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of docker-compose.yml here, or use @docker-compose.yml in Cursor]

---

## Step 5: Implement and validate

Apply the fixes the AI proposes one at a time. After each fix, run:

```bash
docker compose up -d
```

Then confirm all services are healthy:

```bash
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python -m json.tool
```

If something breaks, revert the last change and move on to the next finding.
