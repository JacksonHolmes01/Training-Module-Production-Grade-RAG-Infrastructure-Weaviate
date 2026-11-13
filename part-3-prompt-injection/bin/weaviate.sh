#!/usr/bin/env bash
# Send one request to Weaviate as a given identity, from inside the lab network.
# Weaviate has no published port, so this runs the request from the API container.
#
# Usage: bin/weaviate.sh <admin|writer|reader|none> <METHOD> <path> [json-body]
# Examples:
#   bin/weaviate.sh reader GET /v1/schema/LabDocs
#   bin/weaviate.sh reader DELETE /v1/schema/LabDocs                  (should be refused)
#   bin/weaviate.sh admin  DELETE '/v1/objects/LabDocs/<id>?tenant=lab'
set -euo pipefail
cd "$(dirname "$0")/.."
WHO="${1:?usage: bin/weaviate.sh <admin|writer|reader|none> <METHOD> <path> [json]}"
METHOD="${2:?method}"; P="${3:?path}"; BODY="${4:-}"
case "$WHO" in
  admin)  CRED="$(cat secrets/weaviate_admin_key.txt)" ;;
  writer) CRED="$(cat secrets/weaviate_writer_key.txt)" ;;
  reader) CRED="$(cat secrets/weaviate_reader_key.txt)" ;;
  none)   CRED="" ;;
  *) echo "identity must be admin, writer, reader, or none"; exit 1 ;;
esac
URL="$(docker exec rag-api printenv WEAVIATE_URL)"
CA=""; docker exec rag-api test -f /run/secrets/tls_ca_crt 2>/dev/null && CA=/run/secrets/tls_ca_crt
# The credential travels on stdin (line 1), so it never appears in a process list.
{ printf '%s\n' "$CRED"; printf '%s' "$BODY"; } | docker exec -i rag-api python -c '
import json, sys, httpx
method, url, path, ca = sys.argv[1:5]
cred = sys.stdin.readline().strip()
body = sys.stdin.read()
h = {"Authorization": "Bearer " + cred} if cred else {}
if body:
    h["Content-Type"] = "application/json"
r = httpx.request(method, url + path, headers=h, content=body or None, verify=ca or True, timeout=30)
print(r.status_code)
try:
    print(json.dumps(r.json(), indent=2)[:4000])
except Exception:
    print(r.text[:2000])
' "$METHOD" "$URL" "$P" "$CA"
