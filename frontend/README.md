# Chatbot Frontend

Minimal Next.js UI for the FastAPI chatbot backend.

## Stack

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- lucide-react

## Setup

```bash
npm install
```

Create `.env.local` if the backend URL is different:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Run

Start the FastAPI backend first from the repository root:

```bash
uvicorn app.main:app --reload
```

Then start the frontend:

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

## Verify

```bash
npm run lint
npm run build
```
