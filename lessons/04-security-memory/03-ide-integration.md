# Lesson 4.3 — Using Your Security Memory in an IDE (VS Code / Cursor)

**What you're building:** not another chatbot, but a real workflow where your IDE assistant retrieves the right security references and uses them to produce grounded, citeable fixes to actual lab files.

**Upgraded Capabilities.** Up until now, the AI in this lab could answer cybersecurity questions, explain frameworks, and help you understand concepts. With the memory and API you built in Lessons 4.1 and 4.2, it can now do something more powerful: you can point it at real files in your project — a Dockerfile, a config, or an API handler — and it will review them against actual security standards and suggest specific, sourced improvements.

This lesson teaches a workflow that works in both VS Code and Cursor, even if you have not configured any special integrations.

## Learning Outcomes

By the end of this lesson, you will:

- Understand what "grounded" security review means and why it matters
- Know how to open and use the AI chat panels in VS Code and Cursor
- Use `/memory/query` to retrieve relevant security guidance for a specific file
- Feed that guidance into your IDE assistant using the included prompt library
- Know how to ask follow-up questions and get the most out of the AI
- Apply the workflow to review and propose fixes to real lab files
- Know how to keep your memory up to date as standards evolve
- Understand what "major integration" means in the context of this project

### Important Note regarding Lesson 4.2

You may be wondering where the chatbot you built in this lab fits in. In this lesson, the AI doing the review is Copilot or Cursor through your chosen IDE, not your chatbot. However, your contribution is the retrieval layer — the `/memory/query` endpoint you built in Lesson 4.2 is what fetches the security chunks. Without that, you would just be asking Copilot generic security questions with no grounded references.

Think of it as a division of labour: your API finds the right standards, and the IDE AI uses them to review the code.

If you completed the optional section in Lesson 4.2, your own chatbot can take over the entire workflow. Instead of manually running a curl command and pasting chunks into Copilot, you would just open your chatbot's chat interface at `http://localhost:7860` and ask it to review the file directly. Behind the scenes, your `/chat` endpoint would automatically detect that the question is security-related, call `/memory/query` to fetch the relevant chunks, inject them into the prompt, and send everything to Ollama to generate a grounded response.

# Chat Pipeline Observations

It is possible that when using the chat endpoint you may get sources from example.org or answers from the sample data rather than recently ingested documents

## Things to Improve

- The sources are coming from the main `LabDoc` collection (sample articles like "Supply Chain Risk"), not from `ExpandedVSCodeMemory` — the memory chunks are being injected into the prompt but the RAG sources shown are from the general collection
- The answer is vague and generic, which means the security memory chunks either aren't reaching the model effectively or the model (`llama3.2:1b`) is too small to use them well

## Notes

The source display is expected behavior — `/chat` shows sources from the main RAG retrieval, not from the memory injection. The memory chunks are injected silently into the prompt context.

Overall this is working correctly. The quality of the answer is a model size limitation — `llama3.2:1b` is very small. If you want better answers try pulling a larger model:

```bash
docker exec -i ollama ollama pull llama3.2:3b
```

Then update your `.env`:

```
OLLAMA_MODEL=llama3.2:3b
```

> **Note:** The Gradio UI at `http://localhost:7860` is for demonstrating the chat/RAG pipeline to end users. The `/memory/query` endpoint is a developer tool — it is meant to be called programmatically or from the terminal as part of the workflow shown in these lessons. To test memory retrieval directly, always use the curl commands in the terminal.

---

## 1) What Does "Grounded" Mean and Why Does It Matter?

When you ask an AI assistant "is this Dockerfile secure?", it will give you an answer — but that answer is based entirely on its training data. It might be outdated, vague, or confidently wrong. There is no way to know which specific standard it is drawing from, and you cannot audit it.

**Grounded** means the AI's answer is tied to a specific, retrievable source. Instead of "the AI said so," you get "the AI said so, and here is the CIS Docker Benchmark section it pulled from."

This matters in security work because:
- Security standards are versioned and change over time — you want to know which version you are working from
- In a real organization, "we followed CIS Benchmark v1.6 section 4.1" is auditable; "the AI said it was fine" is not
- It trains you to think in terms of controls and frameworks, not just instinct

Everything you built in Lessons 4.1 and 4.2 was in service of making this possible.

---

## 2) Opening the AI Chat Panel in Your IDE

### In VS Code

VS Code's AI features are powered by GitHub Copilot. If your course account has Copilot enabled:

1. Open VS Code and make sure you are signed into your GitHub account (bottom left corner)
2. Open the chat panel:
   - Press `Ctrl+Alt+I` (Windows/Linux) or `Cmd+Option+I` (Mac)
   - Click the chat bubble icon in the left sidebar
   - Go to **View > Chat**

You can also open inline chat directly inside a file by pressing `Ctrl+I` (Windows/Linux) or `Cmd+I` (Mac).

One useful feature: type `@workspace` at the start of a message to tell Copilot to consider all the files in your project. For example: `@workspace review docker-compose.yml for security issues`.

### In Cursor

Cursor is a fork of VS Code with AI built in more deeply:

1. Open Cursor and make sure your project folder is open (**File > Open Folder**)
2. Open the chat panel:
   - Press `Ctrl+L` (Windows/Linux) or `Cmd+L` (Mac) for the chat sidebar
   - Press `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac) for inline chat

Cursor has an **Add to context** feature — you can type `@` followed by a filename to reference it directly. For example, `@docker-compose.yml` attaches that file's contents so the AI can read it without copy-pasting.

### Tips for getting good responses from either IDE

- **Be specific.** "Review this file" is vague. "Review this file for secrets in environment variables, exposed ports, and missing resource limits" gives the AI a clear checklist.
- **Paste context before asking.** Paste retrieved chunks into the chat before your question. Tell the AI: "Use only the references below when identifying issues."
- **Ask follow-up questions.** If a finding is unclear, ask "why does that matter?" or "can you show me what the fix would look like as a diff?"
- **Ask it to explain its reasoning.** If the AI proposes a fix, ask "which specific control does this address?" This forces it to connect the fix back to a standard.
- **Use file context features.** In Cursor, use `@filename`. In VS Code, use `@workspace`.

---

## 3) The Core Workflow

### Step 1 — Retrieve Security Context from Memory

Open the integrated terminal in your IDE (`Ctrl+`` ` or **Terminal > New Terminal**).

Make sure you are in the repo root:
```bash
pwd
```
The output should end with your repo folder name. If not:
```bash
cd /path/to/your/repo
```

Load your API key:
```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

Query the memory API for the topic you want to review:
```bash
curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "docker compose security best practices secrets ports privileged mounts",
    "tags": ["docker", "cis"],
    "top_k": 8
  }' > /tmp/security_context.json
```

Preview what came back:
```bash
cat /tmp/security_context.json | python -m json.tool
```

Look at the `text` fields in each result — these are the actual security reference chunks your AI will use. If they look irrelevant, adjust your query and run it again.

### Step 2 — Use the Context in Your IDE Chat

Open `docker-compose.yml` in your IDE file explorer, then open the AI chat panel.

Paste this prompt into the chat, filling in the placeholders:

---

I am going to give you a set of security reference chunks retrieved from a vector database of security standards. After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of docker-compose.yml here]

---

To extract just the chunk text:
```bash
python3 -c "
import json
data = json.load(open('/tmp/security_context.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

Copy all that text and paste it where it says `[paste your retrieved chunks here]`.

> **Why "say so explicitly — do not invent citations"?** Without this instruction the AI will happily cite frameworks it was not given, or make up section numbers. Explicitly telling it to flag unsupported claims forces honesty and helps you separate grounded findings from general suggestions.

---

## 4) The Prompt Library

Rather than constructing prompts from scratch every time, this repo includes ready-made prompt templates for the most common review scenarios. They live at:

```
security-memory/prompts/
```

| File | What it reviews |
|---|---|
| `01-dockerfile-review.md` | Dockerfile — base images, root user, secrets, health checks |
| `02-compose-review.md` | docker-compose.yml — ports, secrets, privileged mode, resource limits |
| `03-nginx-review.md` | nginx/templates/default.conf.template — auth, headers, rate limiting |
| `04-api-auth-review.md` | ingestion-api/app/main.py — input validation, auth, secret leakage |
| `05-dependency-risk-review.md` | requirements.txt and image tags — pinning, CVEs, supply chain |

### Step-by-step for any template

1. Decide which file you want to review and open it in your IDE
2. Run the appropriate memory query in your terminal (example queries are at the top of each template)
3. Preview the results with `cat /tmp/security_context.json | python -m json.tool` to confirm the chunks look relevant
4. Open the prompt template from `security-memory/prompts/` in your IDE
5. Read the instructions at the top of the template, then copy the prompt body
6. Open your IDE chat panel, paste the prompt, then paste your memory chunks and the file being reviewed
7. Read through the AI's findings carefully — don't implement everything without thinking
8. Ask follow-up questions for anything unclear
9. Implement fixes **one at a time**
10. After each fix, re-run the lab with `docker compose up` and confirm it still works before moving to the next fix

Step 10 is not optional: security hardening that breaks the lab is not a success.

### Getting more out of the AI with follow-up questions

- "Which CIS Benchmark section specifically says that?" — forces precision, or admission that there isn't one
- "Show me that fix as a unified diff" — you get exact lines to change
- "If I make that change, will anything else in the lab break?" — prompts the AI to think through dependencies
- "Are there any fixes that are nice-to-have versus actually required by the standard?" — helps prioritize
- "Rank these findings by severity" — useful when there are many findings

---

## 5) What "Major Integration" Means for This Project

A major integration in this context means four things working together:

1. **A working vector database memory:** Weaviate is running, the `ExpandedVSCodeMemory` class exists, and it contains real security reference documents. This is what you built in Lesson 4.1.

2. **A stable, queryable API tool:** the `/memory/query` endpoint is live, authenticated, and returns structured results. This is what you built in Lesson 4.2.

3. **Instructions and prompts that make it useful:** without a clear workflow and prompt library, the memory is just a database nobody uses. The prompts and workflow in this lesson turn it into a practical security tool.

4. **Optionally, IDE or tool integration:** configuring your IDE to call the memory API automatically. This is covered in Section 6 and is a nice-to-have, not a requirement.

You are not being asked to invent new AI or build something from scratch. You are being asked to connect the pieces you have already built into something genuinely useful for security work.

---

## 6) Optional: MCP / Automatic Tool Integration (Advanced)

Right now the workflow requires you to manually run a curl command and paste the results into your IDE. The next level is configuring your IDE to call `/memory/query` automatically via MCP (Model Context Protocol), which Cursor supports.

When configured, the IDE calls your memory API as a tool in the background, retrieves the relevant chunks, and injects them into the prompt — no manual steps needed.

The endpoints you already built are exactly the right shape for this. If you want to explore this, the repo includes optional notes under:

```
security-memory/mcp/
```

This is not required to complete the lesson.

---

## 7) Keeping Your Memory Up to Date

Security standards evolve. CIS Benchmarks get new versions, OWASP updates its Top 10, and MITRE ATT&CK adds new techniques.

### How to add or update documents

1. Add or replace `.md` or `.txt` files under `security-memory/data/`
2. Re-run ingestion:
   ```bash
   docker exec -i ingestion-api python -m app.security_memory.ingest
   ```

Ingestion uses deterministic UUIDs (upserts), so it updates existing chunks if content changed and adds new ones without creating duplicates. Safe to re-run as many times as needed.

### When do you need to create a new class entirely?

Most updates are safe to ingest into the existing `ExpandedVSCodeMemory` class. However, you **must** create a new class if you change:

- The **embedding model** — different models produce vectors in different spaces; mixing them produces nonsense search results
- The **embedding dimension** — Weaviate will reject vectors of the wrong length
- The **distance metric** — switching from cosine to dot product makes existing scores meaningless

To create a new class, delete the old one and re-ingest with a versioned name:

```bash
# Delete old class
curl -X DELETE http://localhost:8080/v1/schema/ExpandedVSCodeMemory

# Update .env to point to new class name
# SECURITY_CLASS=ExpandedVSCodeMemory_v2

# Re-ingest
docker exec -i ingestion-api python -m app.security_memory.ingest
```

This keeps the old class intact in case you need to roll back.

---

## 8) What You Are Actually Learning Here

When you run a memory query, pick a prompt template, and ask your IDE to review a `docker-compose.yml`, you are practicing things that matter in real security work:

- **Retrieval grounding:** always anchoring security claims to a specific source — how professional security assessments work
- **Controls frameworks:** NIST, CIS, OWASP, and MITRE are the shared vocabulary that security teams use to communicate, prioritize, and audit
- **Secure configuration review:** reviewing a Dockerfile or `nginx.conf` against a benchmark — a real skill used in penetration testing, cloud security audits, and DevSecOps pipelines
- **Change management:** the requirement to re-run the lab after every fix teaches you that security changes have to be validated; hardening that breaks functionality is not hardening, it is an outage

---

## Checkpoint

You are done when you can:

- [ ] Open the AI chat panel in VS Code or Cursor
- [ ] Retrieve relevant security standards via `/memory/query` for a specific file
- [ ] Use the prompt library to produce a grounded security review in your IDE
- [ ] Implement at least one fix and confirm the lab still runs correctly after the change

---

[← Lesson 2](02-security-tool-api.md)
