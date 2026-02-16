import os
import httpx
import gradio as gr

API_BASE_URL = os.getenv("API_BASE_URL", "http://nginx:8088")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")

def call_api(path: str, payload: dict):
    if not EDGE_API_KEY:
        return {"error": "EDGE_API_KEY is not set for the UI container."}
    headers = {"X-API-Key": EDGE_API_KEY}
    with httpx.Client(timeout=120) as client:
        r = client.post(f"{API_BASE_URL}{path}", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

def chat_fn(message, history):
    data = call_api("/chat", {"message": message})
    if "error" in data:
        return f"Error: {data['error']}"
    answer = (data.get("answer") or "").strip()
    sources = data.get("sources") or []

    if sources:
        answer += "\n\n---\n**Sources (retrieved from Weaviate):**\n"
        for i, s in enumerate(sources, start=1):
            title = s.get("title") or "Untitled"
            url = s.get("url") or ""
            dist = s.get("distance")
            answer += f"{i}. {title} — {url} (distance={dist})\n"
    return answer

def health_text():
    if not EDGE_API_KEY:
        return "UI misconfigured: EDGE_API_KEY is missing."
    headers = {"X-API-Key": EDGE_API_KEY}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE_URL}/health", headers=headers)
            return f"{r.status_code}: {r.text}"
    except Exception as e:
        return f"Health check failed: {e}"

with gr.Blocks(title="Lab 2 — Chat with Weaviate (RAG)") as demo:
    gr.Markdown(
        "# Lab 2 — Chat with Your Dataset (RAG)\n"
        "This UI chats with your dataset using:\n"
        "- Retrieval from Weaviate\n"
        "- A local LLM via Ollama\n"
        "- An API layer behind an authenticated NGINX proxy\n"
    )

    with gr.Row():
        with gr.Column(scale=2):
            gr.ChatInterface(chat_fn)
        with gr.Column(scale=1):
            gr.Markdown("## System status")
            btn = gr.Button("Refresh health")
            out = gr.Textbox(label="API /health output", lines=10)
            btn.click(fn=health_text, outputs=out)

demo.launch(server_name="0.0.0.0", server_port=7860)
