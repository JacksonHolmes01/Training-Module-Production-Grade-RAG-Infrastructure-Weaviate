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
# Mode 644: in Part 4 the containers run as non-root users (10001), so the
# files must be readable by a user other than you. See lessons/08-secrets.md
# for the trade-off.
chmod 644 secrets/*.txt

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

# ---------------------------------------------------------------
# Edge API key: lives in .env for your own scripts (curl, the attack
# harness), and in secrets/ as files for the containers (Lesson 8).
# ---------------------------------------------------------------
KEY="$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)"
printf '%s' "$KEY" > secrets/edge_api_key.txt
printf '"%s" 1;\n' "$KEY" > secrets/edge_key.map
chmod 644 secrets/edge_api_key.txt secrets/edge_key.map
echo "  wrote    secrets/edge_api_key.txt and secrets/edge_key.map"

# ---------------------------------------------------------------
# A private certificate authority (CA) and a certificate for Weaviate,
# used for encrypted, verified API-to-database traffic (Lesson 9).
# ---------------------------------------------------------------
if [[ -s secrets/tls_ca.crt && -s secrets/weaviate_server.crt ]]; then
  echo "  kept     TLS certificates"
else
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=Secure AI Lab CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout secrets/tls_ca.key -out secrets/tls_ca.crt 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -subj "/CN=weaviate" \
    -keyout secrets/weaviate_server.key -out secrets/weaviate_server.csr 2>/dev/null
  printf 'subjectAltName=DNS:weaviate\nextendedKeyUsage=serverAuth\n' > secrets/weaviate_server.ext
  openssl x509 -req -in secrets/weaviate_server.csr -CA secrets/tls_ca.crt -CAkey secrets/tls_ca.key \
    -CAcreateserial -days 365 -extfile secrets/weaviate_server.ext -out secrets/weaviate_server.crt 2>/dev/null
  rm -f secrets/weaviate_server.csr secrets/weaviate_server.ext secrets/tls_ca.srl
  chmod 600 secrets/tls_ca.key
  chmod 644 secrets/tls_ca.crt secrets/weaviate_server.crt secrets/weaviate_server.key
  echo "  created  TLS certificate authority and Weaviate certificate"
fi

# Parts 3, 4, and 5 share one model volume, so models download only once
docker volume create secure-ai-weaviate_ollama_data >/dev/null
echo "  ready    model volume secure-ai-weaviate_ollama_data"
echo "Secrets ready."
