# Journal RAG Chat

Simple chat app with a FastAPI backend and a Next.js frontend.

Current backend APIs:

```text
POST /chat
GET /journals
POST /journals
DELETE /journals/{document_id}
```

## Spec

- Backend: FastAPI
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
- LLM: OpenAI `gpt-5-mini`
- Main chat endpoint: `/chat`
- Backend port: `8000`
- Frontend port: `3000`
- Frontend proxy: `/chat` is forwarded to `http://127.0.0.1:8000/chat`
- Related scholarly reference lookup: Tavily through LangGraph
- Tracing: Langfuse Python SDK with LangChain/LangGraph callbacks

## API Spec

Request:

```json
{
  "message": "Hello",
  "thread_id": "local-session-id",
  "document_id": "selected-document-id"
}
```

Response:

```text
SSE stream with message events and a final done event.
```

If the message asks for journal references, research papers, academic papers,
related studies, literature recommendations, or Indonesian equivalents like
`referensi jurnal`, `/chat` returns up to 5 related scholarly references from
trusted scholarly domains.
Otherwise, `/chat` answers from the selected uploaded journal.

Trusted lookup domains:

```text
arxiv.org
pubmed.ncbi.nlm.nih.gov
semanticscholar.org
aclanthology.org
frontiersin.org
```

## Environment

Create `.env` in the project root:

```env
OPENAI_API_KEY=your_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENVIRONMENT=development
```

Langfuse traces are created for `/chat` requests. Each trace uses the session
header as the Langfuse session id and includes nested observations for the
LangGraph run, retrieval, query rewriting, and response generation.

## Run Backend

From the project root:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/health
```

## Run Frontend

From `frontend`:

```powershell
npm install
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

## Verify

Backend:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```
