# Lessons

- Keep FastAPI route files thin: request/response wiring belongs in `main.py`, while routing, lookup, formatting, and graph behavior belong in dedicated modules.
- When behavior is part of a LangGraph workflow, implement it with graph nodes and conditional edges instead of bypassing the graph from an API route.
- Do not label generic web search results as journals. Use precise wording such as "related scholarly references" unless the source metadata proves the result is a journal article.
- When the backend requires a session header, the frontend must not enable upload/delete/chat actions until the session id has been created.
- For RAG answers, keep source metadata separate from the generated answer when the UI can render it. Group repeated document sources and show compact page ranges instead of repeating the same document name inline.
- When LangGraph event payloads are inspected, validate the runtime output type before reading node-specific fields; event metadata can identify more than one nested event shape.
- When a user changes a diagnosis-only request into an explicit fix request, preserve the diagnosis and implement only the requested correction.
- OpenAI structured-output schemas must match the selected response method; flexible `dict[str, Any]` payloads require an explicit compatible method such as function calling.
- A successful artifact stream can contain intermediate string-valued LangGraph events, so every node-specific event parser must validate mapping output before reading fields.
