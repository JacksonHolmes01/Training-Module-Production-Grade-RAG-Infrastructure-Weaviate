# Lab 2 — Weaviate RAG Infrastructure: Quiz Questions

Self-graded quiz for all 10 lessons. Answers are at the bottom of each lesson section.

---

## Lesson 1 — Lab Overview

**Q1.** What does RAG stand for and how does Weaviate's role differ from Qdrant's in the same architecture?

**Q2.** In this lab, only two ports are exposed to your laptop. What are they and what service runs on each one?

**Q3.** True or False: Weaviate automatically generates embeddings when you insert a document, without any manual embedding call in your code.

**Q4.** What is the role of `text2vec-transformers` in this system and what happens if it goes down?

**Q5.** What is a Weaviate "class" and how is it different from a Qdrant "collection"?

<details>
<summary>Answers</summary>

1. Retrieval-Augmented Generation. In Qdrant (Lab 1) the ingestion API manually generates embeddings and stores them. In Weaviate (Lab 2), Weaviate automatically calls text2vec-transformers to generate embeddings on insert and query — the embedding step is handled by the database layer.
2. Port 7860 (Gradio UI) and port 8088 (NGINX gateway).
3. True. Weaviate is configured with `text2vec-transformers` as its vectorizer — it calls the service automatically on every insert and nearText query.
4. `text2vec-transformers` generates vector embeddings from text. If it goes down, Weaviate cannot embed new documents on insert or embed queries for search. Existing stored vectors can still be retrieved but new operations requiring embedding will fail.
5. A Weaviate class is a typed schema container — like a database table with defined property types. A Qdrant collection is more flexible — it stores vectors alongside arbitrary JSON payloads with no schema enforcement.

</details>

---

## Lesson 2 — Setup & First Boot

**Q1.** What command do you run to start all services in the background and rebuild local images?

**Q2.** Why should you never commit your `.env` file to GitHub?

**Q3.** Why does Weaviate take longer to initialize than Qdrant on first startup?

**Q4.** You run `docker compose up -d --build` and the API health check returns `weaviate: false`. What is the most likely cause?

**Q5.** What is the minimum recommended RAM to run this lab and why does running both Weaviate and text2vec-transformers increase memory requirements?

<details>
<summary>Answers</summary>

1. `docker compose up -d --build`
2. The `.env` file contains secrets like `EDGE_API_KEY`. Committing it to GitHub would expose those secrets publicly.
3. On first startup, `text2vec-transformers` must download and load its sentence-transformer model. Weaviate depends on this service being healthy before it can vectorize. This download takes additional time compared to Qdrant which has no equivalent dependency.
4. Either Weaviate is still initializing, or `text2vec-transformers` hasn't finished loading its model. Wait 60-120 seconds and check `docker compose logs text2vec-transformers` to confirm the model loaded successfully.
5. 16 GB RAM is recommended. Both Weaviate and text2vec-transformers need memory simultaneously — text2vec loads a sentence-transformer model into memory, and Weaviate stores vectors and handles queries. Running both alongside Ollama puts significant pressure on available RAM.

</details>

---

## Lesson 3 — Compose Architecture & Resource Limits

**Q1.** What environment variable in `docker-compose.yml` wires Weaviate to the text2vec-transformers service for automatic embedding?

**Q2.** What are the three top-level sections in `docker-compose.yml` and what does each one define?

**Q3.** What two Docker volumes are used in this lab and what does each one store?

**Q4.** What is the startup dependency chain in this lab and why does it matter for troubleshooting?

**Q5.** If you run `docker compose down`, is your Weaviate class schema and data deleted?

<details>
<summary>Answers</summary>

1. `TRANSFORMERS_INFERENCE_API=http://text2vec-transformers:8080` — this tells Weaviate where to send text for vectorization.
2. `services:` defines containers and their configuration; `networks:` defines how containers communicate; `volumes:` defines where persistent data is stored.
3. `weaviate_data` stores Weaviate class schemas, objects, and vectors. `ollama_data` stores downloaded Ollama models.
4. text2vec-transformers must be healthy first → Weaviate depends on it for embedding → ingestion-api depends on Weaviate to create the schema and ingest documents. If you see ingestion failures on first run, check text2vec-transformers health before anything else.
5. No — `docker compose down` stops containers but preserves volumes. The `weaviate_data` volume retains the class schema, all objects, and all vectors until you explicitly delete it with `./bin/reset_all.sh`.

</details>

---

## Lesson 4 — Edge Authentication with NGINX

**Q1.** What HTTP status code does NGINX return when the `X-API-Key` header is missing entirely?

**Q2.** What HTTP status code does NGINX return when the `X-API-Key` header is present but contains the wrong value?

**Q3.** What is "defense in depth" and how does this lab implement it for API authentication?

**Q4.** Where does NGINX get the value of the API key to compare against incoming requests?

**Q5.** The `/health` endpoint in the Weaviate lab returns a field indicating database health. What field is this and what does it show?

<details>
<summary>Answers</summary>

1. 401 Unauthorized — the key is missing.
2. 403 Forbidden — the key is wrong.
3. Defense in depth means using multiple independent security layers. This lab implements it by checking the API key in both NGINX and inside FastAPI's `require_api_key()` function — two independent failure points.
4. NGINX reads `EDGE_API_KEY` from the `.env` file, injected into the NGINX config template at container startup.
5. The `weaviate` field — it shows `true` if Weaviate is reachable and healthy, `false` if not. This is distinct from the Qdrant lab which uses an `ok` field with uptime information.

</details>

---

## Lesson 5 — Weaviate Schema & Vectorization

**Q1.** What is a Weaviate class schema and why is it immutable after creation?

**Q2.** How does Weaviate's schema approach differ from Qdrant's approach to storing document fields?

**Q3.** You need to add a `tags` property to the `LabDoc` class but the class already exists without it. What must you do?

**Q4.** What function in `weaviate_client.py` creates the LabDoc class if it doesn't exist, and when is it called?

**Q5.** True or False: You can add a new property to an existing Weaviate class by simply updating the Pydantic model in `schemas.py` and rebuilding the API.

<details>
<summary>Answers</summary>

1. A class schema defines the typed properties that every object in that class must conform to. It is immutable after creation because Weaviate's internal storage and indexing structures are built around the schema — changing it after data has been ingested would corrupt existing data.
2. Qdrant stores whatever JSON payload you send alongside the vector with no schema enforcement. Weaviate requires properties to be declared upfront in the class definition — any property not in the schema cannot be stored.
3. You must drop the existing class (which deletes all data), update the class definition in `weaviate_client.py` to include the `tags` property, wipe the `weaviate_data` volume, restart, and re-ingest all documents.
4. `ensure_schema()` — it is called at the start of the `/ingest` endpoint before any document is stored, creating the class if it doesn't already exist.
5. False. The Pydantic model only controls API validation in FastAPI. The Weaviate class schema is a separate definition in `weaviate_client.py`. Both must be updated, and if the class already exists without the property, it must be recreated.

</details>

---

## Lesson 6 — Ingestion API

**Q1.** When you POST a document to `/ingest`, what does Weaviate do automatically that Qdrant does not?

**Q2.** What HTTP status code does the API return when you submit a document with an invalid URL?

**Q3.** What is the purpose of the `ensure_schema()` call at the start of every ingest request?

**Q4.** What does `./bin/ingest_sample.sh` do?

**Q5.** You ingest a document and get a 200 response, but `/debug/retrieve` returns empty results. What should you check first?

<details>
<summary>Answers</summary>

1. Weaviate automatically calls text2vec-transformers to generate a vector embedding for the document text before storing it. In Qdrant, the ingestion API generates the embedding manually and explicitly passes it to Qdrant.
2. 422 Unprocessable Entity — the Pydantic model validation rejected the malformed URL.
3. `ensure_schema()` creates the LabDoc class in Weaviate if it doesn't already exist. This ensures the class is always present before any insertion attempt, preventing errors on first run.
4. It reads `data/sample_articles.jsonl` and sends each document to the `/ingest` endpoint, populating the Weaviate `LabDoc` class with the cybersecurity dataset.
5. Check that `text2vec-transformers` is healthy — `docker compose logs text2vec-transformers --tail=50`. If it wasn't running during ingestion, embeddings may not have been generated correctly, making documents unsearchable.

</details>

---

## Lesson 7 — RAG Chat

**Q1.** What type of query does Weaviate use for semantic search and how does it differ from a keyword search?

**Q2.** Weaviate returns a distance score with each result. What does a distance of 0.08 mean compared to a distance of 1.4?

**Q3.** What is the correct debugging order when `/chat` returns a poor or empty answer?

**Q4.** True or False: A Weaviate distance score of 0.9 means the result is a 90% match and is therefore a strong result.

**Q5.** What does the `/debug/prompt` endpoint help you verify and why should you use it before calling `/chat`?

<details>
<summary>Answers</summary>

1. Weaviate uses a `nearText` GraphQL query. It converts the query string into a vector using text2vec-transformers and finds stored objects whose vectors are geometrically closest. Keyword search matches exact words. nearText matches meaning — "car" and "automobile" would return similar results even though the words differ.
2. Distance 0.08 means the result is an excellent semantic match — the vectors are very close together. Distance 1.4 means the result is a poor match — semantically distant. Lower is better in Weaviate, which is the opposite of Qdrant's similarity scores.
3. Check retrieval first (`/debug/retrieve`), then prompt construction (`/debug/prompt`), then Ollama generation (`/debug/ollama`). Never debug generation before confirming retrieval works.
4. False. In Weaviate, distance scores are NOT percentages. Distance 0.9 is actually a mediocre match. An excellent match has a distance near 0. This is the opposite of Qdrant where a similarity score of 0.9 would be excellent.
5. `/debug/prompt` shows the exact prompt string that would be sent to Ollama, including retrieved source excerpts and grounding instructions. It confirms that Weaviate retrieval is working and that the prompt is correctly constructed before you spend time waiting for LLM generation.

</details>

---

## Lesson 8 — Gradio Chat UI

**Q1.** The Sources section in the Gradio UI shows `distance=0.12` for one result and `distance=0.87` for another. Which result is a stronger match?

**Q2.** The Gradio UI calls NGINX rather than FastAPI directly. Why does this matter for security?

**Q3.** You open the UI and ask "What is the CIA triad?" but the answer is vague and the sources look unrelated. What is the most likely cause?

**Q4.** After the security memory extension is added, what second tab appears in the Gradio UI and what does it let you do?

**Q5.** True or False: The Gradio UI can be used to directly browse and query the Weaviate class schema.

<details>
<summary>Answers</summary>

1. Distance 0.12 is the stronger match — in Weaviate, lower distance means the vectors are closer together, indicating higher semantic similarity.
2. All traffic goes through NGINX which enforces the API key check. If Gradio called FastAPI directly, it could potentially bypass the authentication gateway.
3. The sample dataset may not contain documents about that topic, or the dataset hasn't been ingested. RAG only retrieves from what is stored — if there are no relevant documents, retrieval returns weak matches and the answer will be generic.
4. The Security Memory tab — it lets you directly query the `ExpandedVSCodeMemory` Weaviate class, search for security framework chunks by topic and tags, and see distance scores for each retrieved chunk.
5. False. Gradio only exposes the `/chat` and `/memory/query` endpoints via NGINX. It has no direct access to Weaviate's class schema or raw data.

</details>

---

## Lesson 9 — Operations & Troubleshooting

**Q1.** What is the first thing you should do when something in the lab stops working?

**Q2.** In Failure Drill B (stop Weaviate), what specifically breaks and what still works?

**Q3.** In Failure Drill C (stop text2vec-transformers), does existing retrieval break immediately? Explain why or why not.

**Q4.** What is the difference between `docker compose down` and `./bin/reset_all.sh`?

**Q5.** You need to verify that the Weaviate `LabDoc` class has data after ingestion, but there is no visual dashboard like Qdrant has. What command do you run instead?

<details>
<summary>Answers</summary>

1. Check the logs — `docker compose logs <service> --tail=200`. Do not guess. Logs show the root cause directly.
2. All retrieval breaks — `/debug/retrieve` fails, `/health` reports `weaviate: false`, and `/chat` fails. Ollama and NGINX are unaffected so the proxy health check still passes.
3. No — existing retrieval does not break immediately. Vectors are already stored in Weaviate's `weaviate_data` volume. Weaviate can still perform nearText searches using stored embeddings. However, new ingestion fails because Weaviate cannot embed new document text, and new query embedding may degrade depending on implementation.
4. `docker compose down` stops all containers but preserves data volumes — Weaviate class data and Ollama models survive. `./bin/reset_all.sh` deletes all volumes — a complete wipe including all ingested data and downloaded models.
5. Run a GraphQL Aggregate query from inside the ingestion-api container: `docker exec -i ingestion-api python -c "import httpx; r = httpx.post('http://weaviate:8080/v1/graphql', json={'query': '{ Aggregate { LabDoc { meta { count } } } }'}); print(r.json())"`

</details>

---

## Lesson 10 — Conclusion

**Q1.** Name the five architectural layers of this system in order from edge to generation.

**Q2.** Why is text2vec-transformers a separate container rather than being built into Weaviate directly?

**Q3.** What are three ways this lab's architecture would change in a real production deployment?

**Q4.** What is the key difference in schema discipline between Weaviate and Qdrant, and why does this matter in production?

**Q5.** True or False: Because Weaviate auto-generates embeddings, you have less control over the embedding process than in the Qdrant lab.

<details>
<summary>Answers</summary>

1. NGINX (edge) → FastAPI (orchestration) → Weaviate + text2vec-transformers (retrieval) → Prompt construction → Ollama (generation).
2. Separation of concerns — the embedding model service can be scaled, replaced, or updated independently from the database. This mirrors production patterns where embedding services and storage services are separate infrastructure components.
3. Any three of: Weaviate replaced by a managed cloud vector database; secrets in a secret manager instead of .env; API keys replaced with OAuth/JWT; GPU-backed LLM instead of local Ollama; centralized logging and observability (Prometheus, Grafana); rate limiting at the edge; CI/CD pipeline for schema migrations.
4. Weaviate requires a typed schema defined upfront that cannot be changed after creation. Qdrant accepts flexible JSON payloads with no schema enforcement. In production, Weaviate's constraint enforces data governance and prevents schema drift — teams must be deliberate about data structure changes, which is valuable at scale.
5. True — this is a real tradeoff. In the Qdrant lab, the ingestion API controls exactly when and how embeddings are generated. In the Weaviate lab, embedding is handled automatically by the database layer. This is more convenient but gives you less visibility into the embedding process and makes it harder to debug embedding issues.

</details>
