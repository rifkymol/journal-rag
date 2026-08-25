# Frontend /chat Simplification

- [x] Confirm backend `/chat` request and response shape.
- [x] Replace the frontend with a minimal chat-only UI.
- [x] Proxy frontend `/chat` requests to the Python backend.
- [x] Run verification and start the frontend.

## Review

- `npm run lint` passed.
- `npm run build` passed.
- Backend started with `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend started with `npm run start -- --hostname 127.0.0.1 --port 3000`.
- Backend health check returned `{"status":"ok"}` and frontend returned HTTP 200.
