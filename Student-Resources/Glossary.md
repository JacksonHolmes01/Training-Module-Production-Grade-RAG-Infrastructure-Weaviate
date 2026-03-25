# RAG Infrastructure Lab — Glossary

A reference for every technical term used across the labs. Terms are organized by category.

---

## RAG & AI Concepts

**RAG (Retrieval-Augmented Generation)**
A system design pattern that combines a retriever (search system), a knowledge store (database), and a language model (LLM). Instead of answering from training data alone, the system first retrieves relevant documents, injects them into the prompt, and generates a grounded answer.

**Embedding / Vector**
A list of floating point numbers (e.g. 384 or 768 values) that represents the semantic meaning of a piece of text. Similar texts produce vectors that are close together mathematically. Embeddings enable semantic search.

**Semantic Search**
Finding documents based on meaning rather than exact keyword matches. "Car" and "automobile" would return similar results in semantic search even though the words differ. Powered by comparing vectors using distance or similarity metrics.

**Grounding**
Constraining the LLM to answer using only the documents you provide in the prompt. Grounded answers are traceable to a specific source. Ungrounded answers come from the model's training data alone and cannot be audited.

**Chunking**
Splitting large documents into smaller overlapping pieces before embedding them. Smaller chunks improve retrieval precision. Overlap (e.g. 200 characters) prevents important context from being cut off at chunk boundaries.

**Chunk Overlap**
The number of characters shared between adjacent chunks. Prevents important sentences from being split across two separate chunks and losing context.

**Top-K (RAG_TOP_K)**
The number of documents retrieved from the vector database per query. Higher values provide more context but increase prompt size and can add noise. Configured via `RAG_TOP_K` in `.env`.

**Hallucination**
When an LLM generates confident-sounding but incorrect or fabricated information. RAG reduces hallucination by grounding the model in retrieved documents, but doesn't eliminate it entirely.

**Prompt Engineering**
Designing the structure and instructions of the text sent to the LLM. In this lab, the prompt includes a system instruction, the user question, and retrieved source excerpts. Prompt construction is done in `rag.py`.

**Context Window**
The maximum amount of text an LLM can process in a single prompt. Very large prompts (many retrieved chunks + long user question) may exceed the model's context window, causing truncation or errors.

---

## Vector Database Concepts

**Collection (Qdrant)**
A named container in Qdrant that stores points (vectors + payloads). Equivalent to a table in a relational database but without a rigid schema. This lab uses `LabDoc` for the main dataset and `ExpandedVSCodeMemory` for security memory.

**Class (Weaviate)**
A named container in Weaviate that stores objects with a defined schema. Unlike Qdrant collections, Weaviate classes require property types to be declared upfront. Cannot be modified after creation.

**Point (Qdrant)**
A single record in Qdrant consisting of a vector (the embedding) and a payload (metadata like title, url, tags, text). The vector enables similarity search. The payload provides context.

**Object (Weaviate)**
A single record in Weaviate consisting of typed property values and an auto-generated vector embedding. Equivalent to a Qdrant point.

**Payload (Qdrant)**
The metadata stored alongside a vector in Qdrant. Can be any JSON — no schema required. Includes fields like title, url, source, tags, text, published_date.

**Schema (Weaviate)**
The typed definition of a Weaviate class — what properties it has and what types they are (text, text[], int, etc.). Must be defined before any objects are inserted. Immutable after creation.

**Similarity Score (Qdrant)**
A value between 0 and 1 indicating how semantically similar a retrieved document is to the query. Higher is better — a score of 0.9 means a very strong match.

**Distance Score (Weaviate)**
A value indicating how far apart two vectors are geometrically. Lower is better — a distance of 0.05 means a very strong match. This is the OPPOSITE scale from Qdrant's similarity score. Distance 0.9 in Weaviate is a mediocre result, not a good one.

**nearText (Weaviate)**
Weaviate's GraphQL query type for semantic search. You pass a text string and Weaviate automatically embeds it and finds the closest matching objects. Equivalent to a vector similarity search in Qdrant.

**HNSW (Hierarchical Navigable Small World)**
The indexing algorithm used by both Qdrant and Weaviate for fast approximate nearest-neighbor search. Allows semantic search to scale to millions of vectors efficiently.

**Upsert**
Insert a record if it doesn't exist, or update it if it does. Qdrant uses upsert for the security memory collection so re-running ingestion doesn't create duplicates.

---

## Docker & Infrastructure Concepts

**Container**
A lightweight, isolated runtime environment for software. Each service in this lab (Qdrant, FastAPI, Ollama, etc.) runs as a separate container. Containers share the host OS kernel but are otherwise isolated.

**Docker Compose**
A tool for defining and running multi-container Docker applications. The `docker-compose.yml` file defines all 6 services, their networks, volumes, and resource limits for this lab.

**Image**
A read-only template used to create containers. Built from a `Dockerfile`. When you run `docker compose up --build`, Docker builds images from local code and pulls others from Docker Hub.

**Volume**
A persistent storage location that survives container restarts and rebuilds. This lab uses `qdrant_data` (or `weaviate_data`) for database storage and `ollama_data` for downloaded models.

**Internal Network**
A Docker network where containers can communicate with each other by service name (e.g. `http://qdrant:6333`) but are not accessible from outside Docker. All services except NGINX and Gradio are on the internal network.

**Service Name DNS**
Inside a Docker network, containers can reach each other using their service name as a hostname. The ingestion API calls `http://qdrant:6333` because `qdrant` is the service name in `docker-compose.yml`.

**mem_limit**
A Docker Compose resource constraint that caps how much RAM a container can use. This lab sets `mem_limit: 8g` on Qdrant/Weaviate and Ollama to prevent them from consuming all available memory.

**Health Check**
A command Docker runs periodically inside a container to confirm it's working. If a health check fails, Docker marks the container as unhealthy. The `depends_on` directive uses health checks to control startup order.

**`docker compose down`**
Stops and removes containers but preserves volumes (data survives). Safe for day-to-day use.

**`./bin/reset_all.sh`**
Deletes everything including volumes — all ingested data and downloaded models are lost. Use only when you need a completely clean state.

---

## API & Authentication Concepts

**EDGE_API_KEY**
A shared secret configured in `.env` that all API requests must include as an `X-API-Key` header. Enforced at two layers: NGINX and FastAPI's `require_api_key()` function.

**Defense in Depth**
A security principle where multiple independent layers of protection are used. This lab implements it by checking the API key at both NGINX (edge) and FastAPI (application layer), so a misconfiguration in one layer doesn't expose the system.

**401 Unauthorized**
HTTP status code meaning the API key header is missing entirely from the request.

**403 Forbidden**
HTTP status code meaning the API key header is present but contains the wrong value.

**422 Unprocessable Entity**
HTTP status code meaning the request body failed validation. In this lab it means a required field is missing or has the wrong format (e.g., invalid URL). This is expected behavior — the API is protecting the database.

**Edge Proxy**
A gateway service (NGINX in this lab) that sits in front of all API traffic and enforces authentication before requests reach internal services. In production this role is played by API gateways, load balancers, or cloud edge services.

**FastAPI**
The Python web framework used for the ingestion and RAG API in this lab. Handles request validation (via Pydantic), routing, and async orchestration of the RAG pipeline.

**Pydantic**
A Python data validation library used by FastAPI. Defines the expected shape of request bodies (`ArticleIn`, `ChatIn`). Automatically returns 422 errors for invalid input.

**`/debug/retrieve`**
An endpoint that runs retrieval from the vector database without calling Ollama. Use it to confirm ingestion worked before debugging generation.

**`/debug/prompt`**
An endpoint that returns the exact prompt string that would be sent to Ollama, including retrieved source excerpts. Use it to confirm grounding is correct before debugging generation.

**`/debug/ollama`**
An endpoint that sends a message directly to Ollama without retrieval. Use it to confirm the model is loaded and generation works in isolation.

---

## Security Memory Concepts

**ExpandedVSCodeMemory**
The dedicated vector collection / class used for the security memory corpus. Separate from `LabDoc` to prevent retrieval noise. Contains chunked NIST, CIS, MITRE, OWASP, and CISA documents.

**Security Classifier**
An optional Ollama call added to `main.py` that asks the LLM whether a user message is security-related (YES/NO). Only runs the memory injection step if the answer is YES.

**Memory Injection**
Fetching relevant chunks from `ExpandedVSCodeMemory` and prepending them to the user's message before `build_prompt()` is called. The LLM then has grounded security context without the user needing to do anything manually.

**Tool Contract**
An agreement about the fixed input and output shape of an API endpoint. The `/memory/query` endpoint has a defined request shape (query, tags, top_k) and response shape (results with score, title, source, tags, text). Predictable shapes are required for IDE and LLM tool integrations.

**Grounded Security Review**
A security assessment where every finding is tied to a specific, retrievable standard (e.g. CIS Docker Benchmark section 4.1). Contrast with ungrounded: "the AI said containers should not run as root" with no citation.

**Patches Folder (Weaviate only)**
A folder in the Weaviate repo (`patches/ingestion-api/app/security_memory/`) containing the security memory module. It must be applied to the running container with `docker cp` after every rebuild because it is not baked into the Docker image.

**MCP (Model Context Protocol)**
A standard supported by Cursor IDE for connecting external tools to the AI assistant. Configuring MCP lets the IDE call `/memory/query` automatically whenever a security question is asked, removing the need for manual curl commands.

---

## Ollama & LLM Concepts

**Ollama**
A tool for running large language models locally inside Docker. In this lab it runs `llama3.2:1b` or `llama3.2:3b`. Handles model loading, prompt processing, and text generation entirely on your machine with no external API dependency.

**llama3.2:1b**
A 1-billion parameter language model from Meta. Fast and memory-efficient but produces more generic answers. Recommended for laptops with limited RAM (8 GB Docker allocation).

**llama3.2:3b**
A 3-billion parameter version. Produces noticeably better answers, especially for security questions with injected context. Requires more RAM and takes longer to generate.

**Model Pull**
Downloading a model to Ollama's local storage. Only happens once per model. Run `./bin/pull_model.sh` or `docker exec -it ollama ollama pull llama3.2:1b`. Models persist in the `ollama_data` volume.

**Token Limit**
The maximum number of text tokens a model can process in one request. Very long prompts may exceed this limit. Configured via `OLLAMA_MAX_TOKENS` in `.env`.

**Generation**
The step where Ollama receives the fully constructed prompt and produces a text response. The slowest step in the RAG pipeline — typically 30-120 seconds on a laptop depending on model size and available RAM.
