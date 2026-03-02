# Instructor Notes (How to teach this segment)

## Suggested class flow (2–3 lessons)

1. Show students baseline RAG works (ingest, retrieve, chat).
2. Explain why security work needs reference grounding.
3. Have students ingest a security corpus (or use the sample corpus).
4. Have students run `/memory/query` and inspect results.
5. Give a "security review" exercise:
   - Dockerfile
   - docker-compose
   - NGINX config
   - FastAPI input validation

Students propose minimal diffs and validate the lab still works.

## Assessment ideas

- Students must cite retrieved chunks when explaining a fix
- Students must keep the system functional
- Students must explain trade-offs (lab vs production)

## If you want to keep the repo small

Include only small excerpts and link to official sources for the full text.
