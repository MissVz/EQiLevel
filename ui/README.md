# EQiLevel UI (Vite + React)

- Dev server: `npm install && npm run dev` (opens http://localhost:5173)
- API base: set `VITE_API_BASE` in `.env` or shell (defaults to http://127.0.0.1:8000)
- Build: `npm run build` → outputs `ui/dist`
- Serve with FastAPI: copy `ui/dist` → `app/web` (e.g., `robocopy ui\\dist app\\web /E` on Windows), then open `http://127.0.0.1:8000/`

Pages
- Session: start/clear session (stored in `localStorage`)
- Chat: text input and push-to-talk audio (MediaRecorder → `/session`)
- Metrics: link to existing `/api/v1/metrics/dashboard`

Config
- `VITE_API_BASE` (example: `http://127.0.0.1:8000`)
- Optional `VITE_ADMIN_KEY` (sent manually when you add admin views)

Notes
- Audio uploads use `audio/webm;codecs=opus`. FastAPI `/session` handles multipart and JSON.
- For production, build then copy to `app/web` so FastAPI serves the SPA at `/web` and root `/` redirects there.
