# EQiLevel UI (Vite + React)

## Table of Contents

- [Getting Started](#getting-started)
- [Pages](#pages)
- [Config](#config)
- [Notes](#notes)
- [DX & Settings](#dx--settings)
- [Linting & Format](#linting--format)
- [End-to-End (Playwright)](#end-to-end-playwright)

---

## Getting Started

- Dev server: `npm install && npm run dev` (http://localhost:5173)
- API base: set `VITE_API_BASE` in shell or `.env` (defaults to http://127.0.0.1:8000)
- Build: `npm run build` - outputs `ui/dist`
- Serve with FastAPI: copy `ui/dist` to `app/web` (e.g., `robocopy ui\\dist app\\web /E` on Windows), then open `http://127.0.0.1:8000/`

## Pages
- Session: start/clear session (stored in `localStorage`)
- Chat: text input and push-to-talk audio (MediaRecorder to `/session`)
- Metrics: KPIs, small charts, and series table from `/api/v1/metrics` and `/api/v1/metrics/series`
- Admin: summary cards (`/api/v1/admin/summary`) and filterable turns table (`/api/v1/admin/turns`). Set `X-Admin-Key` in Settings or via `VITE_ADMIN_KEY`.
- Settings: set API base, admin key, and select microphone (stored as `eqi_api_base`, `eqi_admin_key`, `eqi_mic_id`).

## Config
- `VITE_API_BASE` (example: `http://127.0.0.1:8000`) - default base; can be overridden at runtime via Settings
- `VITE_ADMIN_KEY` (optional) - default admin key; can be overridden in Settings

## Notes
- Audio uploads use `audio/webm;codecs=opus`. FastAPI `/session` handles multipart and JSON.
- For production, build then copy to `app/web` so FastAPI serves the SPA at `/web` and root `/` redirects there.

## DX & Settings
- Header shows API health (OpenAI key + DB). Hover for details.
- Settings page: validate `X-Admin-Key`, pick microphone, tweak VAD (silence threshold/durations), and choose "Use this origin" to bind API base.

## Linting & Format
- Lint: `npm run lint` (fix: `npm run lint:fix`)
- Format: `npm run format` (check: `npm run format:check`)

## End-to-End (Playwright)
- Install Playwright (once): `npx playwright install`
- Ensure API is running (e.g., `./scripts/demo_start.ps1`)
- Run tests: `npm run test:e2e` (headed: `npm run test:e2e:headed`)
- Override base URL: `E2E_BASE=http://127.0.0.1:8000/web npm run test:e2e`

