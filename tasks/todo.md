# Chat Stream Fix

- [x] Confirm frontend request body includes `message`, `thread_id`, and `document_id`.
- [x] Confirm `document_id` exists in `GET /journals`.
- [x] Confirm direct backend `/chat` returns SSE chunks.
- [x] Confirm frontend proxy `/chat` returns SSE chunks.
- [x] Trace LangGraph stream events.
- [x] Patch frontend SSE parser for CRLF event boundaries.
- [x] Patch backend stream to emit only the final `generate` node.
- [x] Preserve leading token spaces in frontend SSE data parsing.
- [x] Rebuild and restart backend/frontend.
- [x] Verify fixed frontend-proxied `/chat` stream.

## Findings

- Request body was correct: `message`, `thread_id`, and `document_id` were sent.
- Current journal ID exists: `c6cc86ba-53b0-461f-9330-6d016760df12`.
- `thread_id` is created from local storage and sent in the request body.
- Backend returned SSE chunks, so the API/proxy were not the root cause of `No answer was returned.`
- Frontend parser only split on `\n\n`, but the SSE stream uses CRLF-compatible event boundaries.
- Frontend parser was also trimming leading token spaces, which made streamed text run together.
- Backend was also streaming both `rewrite_query` and `generate`; only `generate` should be displayed.

## Review

- `python -m compileall -q app` passed.
- `frontend` `npm run build` passed.
- Parser sanity check produced `What are the journal` from split SSE chunks.
- Restarted backend on `127.0.0.1:8000`.
- Restarted frontend on `127.0.0.1:3000`.
- Frontend proxy `/chat` returned final answer chunks only.

## Local Restart

- Backend: from project root, run `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend: from `frontend`, run `.\node_modules\.bin\next.cmd start -H 127.0.0.1 -p 3000`.
- Open the app at `http://127.0.0.1:3000`.

# Vercel API URL Fix

- [x] Confirm Vercel error cause.
- [x] Patch frontend config so Vercel cannot silently use `127.0.0.1`.
- [x] Document the required Vercel API environment variable.
- [x] Run frontend build verification.

## Findings

- Vercel error `DNS_HOSTNAME_RESOLVED_PRIVATE` happens because the frontend API rewrite falls back to `http://127.0.0.1:8000`.
- On Vercel, `127.0.0.1` means the Vercel runtime itself, not the Render backend.
- Vercel blocks rewrites to private/local addresses, so the deployed frontend must use the public Render backend URL.

## Review

- `frontend` `npm run build` passed.
- Vercel now fails with a clear configuration error if `NEXT_PUBLIC_API_BASE_URL` is missing.
- Local development still defaults to `http://127.0.0.1:8000`.

# Requirements Update

- [x] Review current backend imports.
- [x] Identify missing runtime packages for new journal search/import modules.
- [x] Patch `requirements.txt`.
- [x] Verify backend compile/import health.

## Findings

- `app/journal_import.py` imports `requests`.
- `app/journal_search.py` imports `langchain_tavily`.
- `app/main.py` imports `pydantic.BaseModel` and `langchain_core.messages.HumanMessage` directly.
- The dependency file should stay focused on direct runtime packages, not a full `pip freeze`.

## Review

- Added `requests`, `langchain-tavily`, `pydantic`, and `langchain-core` to `requirements.txt`.
- `.venv\Scripts\python.exe -m compileall -q app` passed.
- `.venv\Scripts\python.exe -m pip check` passed.
- Backend import smoke test passed.

# Fix `/chat` Journal Reference Search

- [x] Write this approved plan into `tasks/todo.md`.
- [x] Refactor journal search into a plain service function plus an optional LangChain tool wrapper.
- [x] Add a deterministic `/chat` check for reference-style prompts.
- [x] For reference prompts, call web journal search directly and stream a clean formatted answer with 5 results.
- [x] Keep normal selected-journal questions routed through the existing RAG graph.
- [x] Fix `/journals/search` so it calls the plain search function, not the LangChain tool object.
- [x] Add/confirm `TAVILY_API_KEY` is documented for local and Render deployment.
- [x] Verify backend compile, import smoke test, `/journals/search`, normal `/chat`, and reference `/chat`.
- [x] Review diff and report any remaining uncommitted files before push.

## Findings

- SSE `ping` lines are keepalive comments from `EventSourceResponse`, not the failure.
- The current graph asks the model to decide whether to call Tavily, so reference search can route unpredictably.
- `/chat` only streams the `generate` node, which is fine for PDF RAG but not enough for a web-reference-only path.

## Review

- `.venv\Scripts\python.exe -m compileall -q app` passed.
- `.venv\Scripts\python.exe -m pip check` passed.
- Backend import smoke test passed.
- `POST /journals/search` returned status 200 with 5 results.
- Reference `POST /chat` returned status 200, included numbered references, and sent `[DONE]`.
- Indonesian reference prompt detection returned true and streamed numbered references.
- Normal selected-journal `POST /chat` returned status 200, streamed message events, and sent `[DONE]`.
- `frontend` `npm run build` passed.
- `git diff --check` passed.

# Langfuse Tracing

- [x] Install Langfuse skill from `github.com/langfuse/skills`.
- [x] Read Langfuse instrumentation guidance.
- [x] Add Langfuse observability helper.
- [x] Instrument `/chat` stream and graph lookup steps.
- [x] Verify backend import and runtime behavior.
- [x] Generate and audit a Langfuse trace.

## Review

- Installed local Codex skill `langfuse` from `github.com/langfuse/skills`.
- Used Langfuse Python SDK `4.15.1`.
- `.venv\Scripts\python.exe -m compileall -q app` passed.
- `.venv\Scripts\python.exe -m pip check` passed.
- Backend import smoke test passed.
- Direct `/chat` stream smoke test returned message events and final `[DONE]`.
- Final Langfuse trace id: `aec0974d1b702ca93adc958bd27ab525`.
- Final audit confirmed root input/output, session id, stable operation names, retriever observation, LLM generation observations, usage, latency, and cost.

# Backup And Clean Master

- [x] Create and push backup branch from current committed `HEAD`.
- [x] Remove disabled public journal import feature.
- [x] Stop tracking runtime data and log files.
- [x] Update `.gitignore` for `data/` and `*.log`.
- [x] Remove stale README endpoints.
- [x] Run backend/frontend verification.
- [x] Commit cleanup on `master`.
- [x] Push cleaned `master`.

## Findings

- Backup branch: `codex/backup-master-before-cleanup-2026-08-28`.
- Kept deterministic Tavily journal references on `/chat`.
- Removed only the disabled import feature and runtime artifacts from tracking.
- Cleanup commit: `3b81802`.
- Pushed cleaned `master` to GitHub.

## Review

- `git ls-files data '*.log'` returned no tracked runtime files.
- `.venv\Scripts\python.exe -m compileall -q app` passed.
- `.venv\Scripts\python.exe -m pip check` passed.
- Backend import smoke test passed.
- `/journals/search` returned status 200 with 5 results.
- Reference `/chat` returned status 200 with numbered results and `[DONE]`.
- Normal selected-journal `/chat` returned status 200 with streamed message events and `[DONE]`.
- `frontend` `npm run build` passed.
- `git diff --check` passed.

# Clean LangGraph Journal Lookup

- [x] Capture correction in `tasks/lessons.md`.
- [x] Remove the direct `main.py` web-search path and `/journals/search`.
- [x] Replace `app/journal_search.py` with `app/journal_lookup.py`.
- [x] Move `/chat` SSE streaming into `app/chat_stream.py`.
- [x] Add LangGraph `route_request` conditional routing.
- [x] Keep Tavily lookup limited to trusted scholarly domains.
- [x] Update frontend send behavior for lookup without selected journal.
- [x] Update requirements, Render config, and README.
- [x] Verify backend/frontend behavior.
- [x] Commit and push.

## Review

- Old direct-main search symbols and `/journals/search` references are gone.
- `.venv\Scripts\python.exe -m compileall -q app` passed.
- Backend imports passed with `TAVILY_API_KEY` removed from the process.
- `.venv\Scripts\python.exe -m pip check` passed.
- Reference prompt routed through LangGraph and returned related scholarly references.
- Missing selected journal routed through LangGraph and returned a user-facing message.
- Normal selected-journal `/chat` still streamed message events and `[DONE]`.
- `frontend` `npm run build` passed.
- `git diff --check` passed.
- Cleanup/refactor commit: `85603a8`.
- Pushed `master` to GitHub.

# Limit PDF Uploads

- [x] Add backend per-session max 3 PDF validation.
- [x] Add frontend counter, disabled upload state, and validation message.
- [x] Verify backend rejects the 4th upload for a session.
- [x] Verify frontend build passes.
- [ ] Commit and push to `master`.

## Requirement

- Users can upload at most 3 PDFs per session.
- When the user reaches the limit, the frontend must show the limit and prevent more uploads.
- Do not change unrelated features.

## Review

- Backend allows upload when a session has fewer than 3 PDFs.
- Backend rejects upload when a session already has 3 PDFs.
- Frontend shows `current/3` journal count.
- Frontend disables upload at the limit and shows a warning message.
- `.venv\Scripts\python.exe -m compileall -q app` passed.
- `.venv\Scripts\python.exe -m pip check` passed.
- Backend import smoke test passed.
- `frontend` `npm run build` passed.
- `git diff --check` passed.

# Study Research Copilot

## Plan

- [x] Baseline branch and verification
- [x] Add typed source, study mode, language, and artifact contracts
- [x] Add generic PDF and pasted-text source services and compatibility aliases
- [x] Add multi-source LangGraph retrieval and structured study modes
- [x] Extend chat SSE events while preserving legacy requests
- [x] Refactor the frontend into a study workspace
- [x] Add local-first persistence, notes, and export/import
- [x] Add backend and frontend tests
- [x] Run final verification and review unrelated-file changes

## Review

- Branch: `codex/study-research-copilot`
- Backend compile and frontend build passed on the baseline.
- No automated test suite was present on the baseline.
- `npm run lint` did not complete in the available verification window.

## Implementation Review

- Backend compile passed.
- `pip check` passed.
- `pytest -q` passed: 10 tests.
- `frontend` `npm run lint` passed.
- `frontend` `npm run build` passed.
- `git diff --check` passed.
- FastAPI smoke test passed for `/health` and session-scoped `/sources`.
- Only study-copilot backend, frontend, documentation, dependency, test, and task files changed.
- Remaining warnings are upstream deprecations for `langchain-community` PDF loading and FastAPI `on_event`.
- Fixed the chat SSE retrieve-event type mismatch that caused the generic study-assistant error.
- Direct graph-path smoke test now returns streamed messages, sources, and `done`.
