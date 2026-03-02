# Optional: IDE Tool Integration (MCP / Tools)

This repo already exposes a stable retrieval tool:

```
POST /memory/query
```

And a generation endpoint:

```
POST /chat
```

If your IDE supports custom tools or MCP servers, you can wrap these endpoints.
This is optional; the lab works without it.

## "Lowest friction" approach (works everywhere)

1. Run `/memory/query`
2. Paste retrieved chunks into your IDE prompt
3. Ask for fixes with citations

## If your IDE supports tool calling

Treat `/memory/query` as a tool named `security_memory_search`.

```json
{
  "name": "security_memory_search",
  "input": { "query": "string", "tags": ["string"], "top_k": 6 },
  "output": "results list"
}
```

Then the assistant can call it automatically when needed.
