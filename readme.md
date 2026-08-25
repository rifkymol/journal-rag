# Journal RAG Chat

Simple chat app with a FastAPI backend and a Next.js frontend.

For now, the frontend only uses one API:

```text
POST /chat
```

## Spec

- Backend: FastAPI
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
- LLM: OpenAI `gpt-5-mini`
- Main chat endpoint: `/chat`
- Backend port: `8000`
- Frontend port: `3000`
- Frontend proxy: `/chat` is forwarded to `http://127.0.0.1:8000/chat`

## API Spec

Request:

```json
{
  "message": "Hello",
  "thread_id": "local-session-id"
}
```

Response:

```json
{
  "answer": "Hello! How can I help?"
}
```

## Environment

Create `.env` in the project root:

```env
OPENAI_API_KEY=your_api_key_here
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
