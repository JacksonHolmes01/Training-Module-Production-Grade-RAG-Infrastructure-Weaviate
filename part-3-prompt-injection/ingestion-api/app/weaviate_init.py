"""
weaviate_init.py: one-time setup, run by the weaviate-init container.

This is the ONLY code that ever holds Weaviate's admin key. It waits for
Weaviate, then makes sure these exist (creating any that are missing):

  - the LabDocs collection, with multi-tenancy on and no built-in
    vectorizer (the API sends its own embeddings)
  - this deployment's tenant (APP_TENANT)
  - two roles, scoped to that one tenant:
      tenant_<name>_reader  read objects
      tenant_<name>_writer  create objects (nothing else: no read, no delete)
  - those roles assigned to the rag-reader and rag-writer users

After it exits, nothing running holds the admin key.
"""

import os
import sys
import time

import httpx

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_CA_CERT = os.getenv("WEAVIATE_CA_CERT", "")
APP_TENANT = os.getenv("APP_TENANT", "lab")
COLLECTION = "LabDocs"

with open("/run/secrets/weaviate_admin_key", encoding="utf-8") as f:
    headers = {"Authorization": "Bearer " + f.read().strip()}


def ok(r: httpx.Response, *allowed: int) -> None:
    if r.status_code >= 300 and r.status_code not in allowed:
        sys.exit(f"{r.request.method} {r.request.url.path} failed: HTTP {r.status_code} {r.text[:300]}")


with httpx.Client(base_url=WEAVIATE_URL, headers=headers, timeout=10,
                  verify=WEAVIATE_CA_CERT or True) as c:
    for _ in range(60):
        try:
            if c.get("/v1/.well-known/ready").status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(2)
    else:
        sys.exit("Weaviate did not become ready.")

    # 1. The collection
    if c.get(f"/v1/schema/{COLLECTION}").status_code != 200:
        text = {"dataType": ["text"]}
        ok(c.post("/v1/schema", json={
            "class": COLLECTION,
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "multiTenancyConfig": {"enabled": True},
            "properties": [
                {"name": "title", **text}, {"name": "url", **text}, {"name": "source", **text},
                {"name": "published_date", **text}, {"name": "tags", "dataType": ["text[]"]},
                {"name": "content", **text},
            ],
        }))
        print(f"Created collection {COLLECTION} (multi-tenant, cosine).")

    # 2. The tenant
    tenants = {t["name"] for t in c.get(f"/v1/schema/{COLLECTION}/tenants").json()}
    if APP_TENANT not in tenants:
        ok(c.post(f"/v1/schema/{COLLECTION}/tenants", json=[{"name": APP_TENANT}]))
        print(f"Created tenant {APP_TENANT}.")

    # 3. The roles, each limited to this one tenant
    scope = {"collection": COLLECTION, "tenant": APP_TENANT}
    # GraphQL search asks Weaviate for the schema of every collection
    # ("introspection"), so the reader may READ collection definitions.
    # That shows collection names and fields, never any data.
    roles = {
        f"tenant_{APP_TENANT}_reader": [
            {"action": "read_data", "data": scope},
            {"action": "read_collections", "collections": {"collection": "*"}},
        ],
        f"tenant_{APP_TENANT}_writer": [
            {"action": "create_data", "data": scope},
            {"action": "read_collections", "collections": {"collection": COLLECTION}},
        ],
    }
    for name, permissions in roles.items():
        if c.get(f"/v1/authz/roles/{name}").status_code != 200:
            ok(c.post("/v1/authz/roles", json={"name": name, "permissions": permissions}))
            print(f"Created role {name}.")

    # 4. Give each API user its role
    for user, role in [("rag-reader", f"tenant_{APP_TENANT}_reader"),
                       ("rag-writer", f"tenant_{APP_TENANT}_writer")]:
        ok(c.post(f"/v1/authz/users/{user}/assign", json={"roles": [role], "userType": "db"}))
    print("Roles assigned: rag-reader (read), rag-writer (create only).")
