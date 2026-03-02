# Prompt 05 — Dependency and Supply Chain Risk Review

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
    "query": "software supply chain security dependency pinning sbom vulnerability scanning container image tags",
    "top_k": 10
  }' > /tmp/supply_chain_refs.json
```

## Step 3: Extract the plain text from the results

```python
python3 -c "
import json
data = json.load(open('/tmp/supply_chain_refs.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

Copy all the text that prints out — you will paste it into the chat in the next step.

## Step 4: Open the IDE chat and paste this prompt

Open your dependency files in your IDE — start with `ingestion-api/requirements.txt`.
Then open the AI chat panel (`Ctrl+Alt+I` in VS Code, `Cmd+L` in Cursor) and paste the following,
replacing the placeholders with the text you copied in Step 3 and the contents of the dependency file:

---

I am going to give you a set of security reference chunks retrieved from a vector database of security standards.
After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix appropriate for a student lab environment
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

Focus especially on: unpinned dependencies, packages with known CVEs, abandoned or transferred packages,
and Docker images using the `latest` tag instead of a specific version.

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of requirements.txt here, or use @requirements.txt in Cursor]

---

You can repeat this for `docker-compose.yml` (to review image tags) and any other dependency files in the repo.

## Step 5: Validate

Unlike other reviews, dependency changes are often optional improvements rather than critical fixes.
Before making any changes, confirm the lab still works after each one:

```bash
docker compose up -d --build
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python -m json.tool
```

If a pinned version causes a build failure, the package may have introduced a breaking change —
revert and note it as a known risk instead.
