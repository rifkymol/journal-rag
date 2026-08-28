# Render Deploy Fix

- [x] Inspect Render build log and confirm package/runtime failure.
- [x] Pin Render Python runtime away from the 3.14 default.
- [x] Replace full environment freeze with backend runtime dependencies.
- [x] Add Render web service config with `0.0.0.0` and `$PORT`.
- [x] Fix backend import/runtime issues exposed by verification.
- [x] Verify dependency resolution, backend import, Render-style startup, and frontend build.
- [x] Commit and push to GitHub.

## Findings

- Render defaulted to Python 3.14, then tried to build `pydantic_core==2.27.0` from source.
- The old `requirements.txt` was a full local environment freeze and included unused heavy packages such as `pandas`, `pillow`, `pyarrow`, and a direct `pydantic_core` pin.
- The backend also had stale retriever calls after `create_retriever()` became document-scoped.

## Review

- `pip install --dry-run -r requirements.txt` passed.
- `python -m compileall -q app` passed.
- `python -c "import app.main"` passed.
- Render-style backend command with `--host 0.0.0.0 --port $PORT` started successfully.
- `/health` returned `{"status":"ok"}`.
- `frontend` `npm run build` passed.

## Local Restart

- Backend: from project root, run `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend: from `frontend`, run `.\node_modules\.bin\next.cmd start -H 127.0.0.1 -p 3000`.
- Open the app at `http://127.0.0.1:3000`.
