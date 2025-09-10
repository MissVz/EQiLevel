# EQiLevel UI (Vite + React)

- Dev server: `npm install && npm run dev` (opens http://localhost:5173)
- API base: set `VITE_API_BASE` in `.env` or shell (defaults to http://127.0.0.1:8000)
- Build: `npm run build` → outputs `ui/dist`
- Serve with FastAPI: copy `ui/dist` → `app/web` (e.g., `robocopy ui\\dist app\\web /E` on Windows), then open `http://127.0.0.1:8000/`

Pages
- Session: start/clear session (stored in `localStorage`)
- Chat: text input and push-to-talk audio (MediaRecorder → `/session`)
- Metrics: link to existing `/api/v1/metrics/dashboard`
- Admin: filter + table from `/api/v1/admin/turns` (set `X-Admin-Key` in Settings field on page or via `VITE_ADMIN_KEY`)
- Settings: set API base, admin key, and select microphone (stored in `localStorage` as `eqi_api_base`, `eqi_admin_key`, `eqi_mic_id`).

Config
- `VITE_API_BASE` (example: `http://127.0.0.1:8000`) — default base; may be overridden at runtime via Settings.
- Optional `VITE_ADMIN_KEY` — default admin key; may be overridden at runtime via Settings.

Notes
- Audio uploads use `audio/webm;codecs=opus`. FastAPI `/session` handles multipart and JSON.
- For production, build then copy to `app/web` so FastAPI serves the SPA at `/web` and root `/` redirects there.
