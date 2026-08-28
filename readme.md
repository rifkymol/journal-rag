# Journal RAG Chat

Simple chat app with a FastAPI backend and a Next.js frontend.

For now, the frontend only uses one API:

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
- Journal reference search: Tavily

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
`referensi jurnal`, `/chat` returns up to 5 public web journal references.
Otherwise, `/chat` answers from the selected uploaded journal.

## Environment

Create `.env` in the project root:

```env
OPENAI_API_KEY=your_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

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

## Extra Backend Endpoints

These exist, but the frontend does not use them right now:

- `POST /rag-chat`
- `POST /graph-chat`
- `POST /stream-chat`
- `POST /ingest`
- `GET /test-pdf`
- `GET /test-chunks`
