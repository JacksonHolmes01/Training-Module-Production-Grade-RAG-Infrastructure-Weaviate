#!/usr/bin/env bash
# Creates every secret this lab needs. Safe to run more than once:
# existing secrets are kept, never overwritten.
#
#   secrets/weaviate_admin_key.txt   Weaviate's admin key (only weaviate-init uses it)
#   secrets/weaviate_writer_key.txt  key for user rag-writer (create objects only)
#   secrets/weaviate_reader_key.txt  key for user rag-reader (read objects only)
#   secrets/weaviate_keys.txt        all three, comma-separated, for Weaviate itself
set -euo pipefail
cd "$(dirname "$0")/.."

gen() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-48; }

mkdir -p secrets
for who in admin writer reader; do
  f="secrets/weaviate_${who}_key.txt"
  if [[ -s "$f" ]]; then echo "  kept     $f"; else gen > "$f"; echo "  created  $f"; fi
done
# Weaviate matches keys to users by position: the first key belongs to the
# first user in AUTHENTICATION_APIKEY_USERS (admin, rag-writer, rag-reader).
printf '%s,%s,%s' "$(cat secrets/weaviate_admin_key.txt)" "$(cat secrets/weaviate_writer_key.txt)" \
  "$(cat secrets/weaviate_reader_key.txt)" > secrets/weaviate_keys.txt
chmod 600 secrets/*.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "  created  .env (from .env.example)"
fi
if ! grep -qE '^EDGE_API_KEY=.{32,}' .env; then
  key="$(gen | cut -c1-40)"
  sed -i.bak "s|^EDGE_API_KEY=.*|EDGE_API_KEY=${key}|" .env && rm -f .env.bak
  echo "  created  EDGE_API_KEY in .env"
else
  echo "  kept     EDGE_API_KEY in .env"
fi
chmod 600 .env
# Parts 3, 4, and 5 share one model volume, so models download only once
docker volume create secure-ai-weaviate_ollama_data >/dev/null
echo "  ready    model volume secure-ai-weaviate_ollama_data"
echo "Secrets ready."
