# Lesson 2: Setup

Part 3 is a copy of the Lab 2 chatbot (the main lab in the root of this repository) with the defenses added, all switched off. It also tightens the database:

| Lab 2 | Part 3 |
|---|---|
| Weaviate has no API keys or roles: the API's one connection can read, write, delete, and change the schema | Weaviate refuses any request without a key, and **roles** decide what each key may do |
| One shared collection for everyone | Weaviate's built-in **multi-tenancy**: each tenant's data lives in its own shard, and roles are scoped to one tenant |
| | The API holds two keys: `rag-reader` may only **read** (chat), `rag-writer` may only **create** (ingest). Neither can delete |
| | The **admin key** is used once, by a setup container, then nothing running holds it |
| | Embeddings come from Ollama, so the `text2vec-transformers` container is gone |

---

## Step 1: Stop Lab 2

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate
docker compose down
```

## Step 2: Move into Part 3

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/part-3-prompt-injection
ls
```

```
README.md  attacks  bin  data  docker-compose.yml  gradio-ui  ingestion-api  lessons  nginx  secrets
```

These things are new compared to Lab 2:

| Item | Purpose |
|---|---|
| `attacks/` | The attack cases, the poisoned documents, and `run_attacks.py`, which runs every attack and scores the result |
| `ingestion-api/app/guards.py` | The four defenses |
| `bin/guard.sh` | Turns a defense on or off and restarts the API |
| `bin/weaviate.sh` | Sends one request to Weaviate as `admin`, `writer`, `reader`, or `none`, so you can test what each identity may do |
| `ingestion-api/app/weaviate_init.py` | Creates the collection, the tenant, and the two roles with the admin key, once |

## Step 3: Secrets, build, and start

```bash
bin/setup_secrets.sh
docker compose up -d --build
```

`setup_secrets.sh` creates three Weaviate keys (admin, writer, reader), the NGINX API key, and a model volume that Parts 3, 4, and 5 share.

Check that the setup container did its job and exited:

```bash
docker logs rag-weaviate-init
```

```
Created collection LabDocs (multi-tenant, cosine).
Created tenant lab.
Created role tenant_lab_reader.
Created role tenant_lab_writer.
Roles assigned: rag-reader (read), rag-writer (create only).
```

### Keys without leaking keys

Weaviate only reads its API keys from an environment variable, and anything in a container's environment shows up in `docker inspect`. So `docker-compose.yml` starts Weaviate through a one-line wrapper that reads the keys from a secret file and sets the variable just for the Weaviate process:

```yaml
entrypoint: ["/bin/sh", "-c", "AUTHENTICATION_APIKEY_ALLOWED_KEYS=\"$$(cat /run/secrets/weaviate_keys)\" exec /bin/weaviate \"$$@\"", "--"]
```

Check that no key is visible from outside:

```bash
docker inspect rag-weaviate --format '{{json .Config.Env}}' | grep -c ALLOWED_KEYS
```

```
0
```

### The roles

| User | Role | May |
|---|---|---|
| `admin` | root | Everything. Only `weaviate-init` ever uses it |
| `rag-writer` | `tenant_lab_writer` | **Create** objects in tenant `lab`. Not read, not update, not delete |
| `rag-reader` | `tenant_lab_reader` | **Read** objects in tenant `lab`, and read collection definitions (GraphQL search needs to see the schema). Never data from another tenant |

### Prove the database is locked

```bash
bin/weaviate.sh none GET /v1/schema
bin/weaviate.sh reader GET /v1/schema/LabDocs
bin/weaviate.sh reader DELETE /v1/schema/LabDocs
bin/weaviate.sh writer POST /v1/graphql '{"query":"{Get{LabDocs(tenant:\"lab\",limit:1){title}}}"}'
```

```
401
{"code":401,"message":"anonymous access not enabled. Please authenticate through one of the available methods: [API-keys]"}
200
{"class":"LabDocs", ...}
403
{"error":[{"message":"rbac: authorization, forbidden action: user 'rag-reader' has insufficient permissions to delete_collections ..."}]}
403
{"error":[{"message":"... user 'rag-writer' has insufficient permissions to read_collections ..."}]}
```

No key: refused. The reader can look at the collection but cannot delete it. The writer cannot even read.

## Step 4: Models and sample data

```bash
bin/pull_models.sh
bin/ingest_sample.sh
```

The first time, this downloads about 1.6 GB. Parts 4 and 5 reuse the same download.

```
Total: 12  Success: 12  Failed: 0
```

## Step 5: Confirm every defense is off

```bash
bin/guard.sh status
```

```
GUARD_INPUT=false
GUARD_INGEST=false
GUARD_PROMPT=false
GUARD_OUTPUT=false
```

The API also reports which guards are on:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool | grep -A5 guards
```

```
    "guards": {
        "input": false,
        "ingest": false,
        "prompt": false,
        "output": false
    },
```

---

## One setting that makes experiments fair

```
OLLAMA_TEMPERATURE=0
```

**Temperature** controls randomness. At `0`, the model picks its most likely answer every time, so the same attack against the same setup gives the same result. That lets you compare "before" and "after" honestly.

Next: [Direct Attacks: Talking the Model Out of Its Rules](03-direct-attacks.md)
