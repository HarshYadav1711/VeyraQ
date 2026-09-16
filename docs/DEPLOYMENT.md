# Deployment — VeyraQ on Vercel

Authoritative guide for deploying the **same GitHub monorepo** as **two Vercel projects**.

```text
GitHub monorepo (frontend/ + backend/)
        │
        ├── Vercel project: VeyraQ frontend  (Root = frontend, Vite → CDN)
        │         │
        │         │  VITE_API_BASE_URL
        │         ▼
        └── Vercel project: VeyraQ API       (Root = backend, FastAPI → Python Function)
                  │
                  ├── Neon PostgreSQL  (DATABASE_URL)
                  └── Groq             (GROQ_API_KEY)
```

This is **not** a single-app rewrite. Do not merge the SPA into FastAPI or rewrite the API in JavaScript.

---

## 1. Prerequisites

- GitHub repository pushed (no secrets committed)
- Vercel account linked to that repo
- Neon PostgreSQL database provisioned
- Groq API key
- Local tools for one-time migration: Python 3.12, `pip install -e ".[dev]"` in `backend/`

---

## 2. Backend Vercel project

| Setting | Value |
| --- | --- |
| Project name | e.g. `veyraq-api` |
| Root Directory | `backend` |
| Framework | FastAPI / Python (auto-detect from `pyproject.toml`) |
| Install / Build | Leave default unless Vercel prompts otherwise |

**Entrypoint:** `api/index.py` re-exports the single FastAPI app from `app.main`.

```python
from app.main import app
```

Configured explicitly in `backend/pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "api.index:app"
```

No `vercel.json` is required for the default layout. Do not add legacy `builds` / catch-all routes.

**Public API paths are unchanged** (examples):

- `GET /api/v1/health`
- `GET /api/v1/readiness`
- `POST /api/v1/assistant/process`
- `POST /api/v1/assistant/process-document`
- `POST /api/v1/assistant/investigation`
- `POST /api/v1/complaints/commit`

### Backend environment variables (Production)

| Variable | Example / notes |
| --- | --- |
| `APP_ENV` | `production` |
| `APP_NAME` | `VeyraQ` (optional; has default) |
| `API_V1_PREFIX` | `/api/v1` (optional; keep default) |
| `DATABASE_URL` | Neon URL — prefer pooled/serverless string for app traffic. Provider `postgresql://` / `postgres://` URLs are normalized internally to SQLAlchemy’s `postgresql+psycopg://` dialect |
| `GROQ_API_KEY` | Secret — **server only** |
| `GROQ_MODEL` | `openai/gpt-oss-20b` |
| `GROQ_STRUCTURED_OUTPUT_STRICT` | `true` |
| `CORS_ORIGINS` | Exact frontend origin, comma-separated if multiple. **Format:** `https://veyraq-frontend.vercel.app` (comma-separated list; **not** JSON). Do **not** use `*` |
| `MAX_UPLOAD_BYTES` | `4194304` (4 MiB; default if omitted) |

Scopes: configure **Production** at minimum. Preview is optional; preview frontends are not whitelisted by default.

After changing env vars, **redeploy**.

---

## 3. Frontend Vercel project

| Setting | Value |
| --- | --- |
| Project name | e.g. `veyraq` / `veyraq-frontend` |
| Root Directory | `frontend` |
| Framework | Vite |
| Install Command | `npm install` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

No `vercel.json` required (single-page workspace; no React Router).

### Frontend environment variables (Production)

| Variable | Example / notes |
| --- | --- |
| `VITE_API_BASE_URL` | `https://<veyraq-api>.vercel.app/api/v1` |
| `VITE_MAX_UPLOAD_BYTES` | `4194304` (optional; defaults to 4 MiB) |

**Never** set `GROQ_API_KEY` or `DATABASE_URL` on the frontend project. `VITE_*` values are public.

Local development continues to use `frontend/.env` (see `.env.example`).

---

## 4. CORS format (exact)

Backend `Settings` parses `CORS_ORIGINS` as a **comma-separated** string (not a JSON array).
`NoDecode` is used so values like `https://app.vercel.app` are not passed through `json.loads`.

```text
CORS_ORIGINS=https://veyraq-frontend.vercel.app
```

Multiple origins:

```text
CORS_ORIGINS=https://veyraq-frontend.vercel.app,http://localhost:5173
```

Not JSON arrays. Not wildcards.

**Preview deployments:** a Vercel preview origin will not call the production API successfully unless that exact origin is listed. That is intentional for the assessment. Production frontend → production backend must work.

---

## 5. Database migration (manual / explicit)

**Do not** run Alembic on every serverless invocation. **Do not** run migrations on app import.

After Neon is ready and `DATABASE_URL` is known:

```bash
cd backend
# Windows PowerShell example:
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require"
alembic upgrade head
```

Optional fictional demo history (idempotent; not automatic):

```bash
python -m app.scripts.seed_demo_complaints
```

SQLAlchemy already uses `pool_pre_ping=True`. Prefer Neon’s pooled connection string for application traffic when available.

VeyraQ normalizes provider-supplied standard PostgreSQL URLs (`postgres://`, `postgresql://`) to SQLAlchemy’s explicit psycopg 3 dialect (`postgresql+psycopg://`) internally. Existing `postgresql+psycopg://` URLs are left unchanged.

---

## 6. Upload limits (Vercel-compatible)

| Limit | Value |
| --- | --- |
| Max upload bytes | **4 MiB** (`4194304`) |
| PDF pages | 20 |
| Extracted characters | 20,000 |
| Formats | PDF, TXT, EML |

Vercel’s request-body ceiling is below the historical 8 MB local limit. Frontend and backend both default to 4 MiB so the UI does not advertise a size the platform will reject.

---

## 7. Production verification

### Curl smoke (no secrets)

Replace hosts with your deployments:

```bash
curl -sS https://<veyraq-api>.vercel.app/api/v1/health
curl -sS https://<veyraq-api>.vercel.app/api/v1/readiness
```

Expect health `200`. Expect readiness ready when Neon is reachable.

AI/document/commit flows should be verified in the UI (they require Groq + CORS + migrations).

### Checklist

**Backend**

- [ ] Deployment succeeds
- [ ] `GET /api/v1/health` returns 200
- [ ] `GET /api/v1/readiness` reports database connected
- [ ] OpenAPI `/docs` loads (if left enabled)
- [ ] Text assistant request reaches Groq
- [ ] Document upload works under 4 MiB
- [ ] Investigation assistance works

**Frontend**

- [ ] Page loads
- [ ] Production `VITE_API_BASE_URL` is used (Network tab)
- [ ] No CORS error
- [ ] Text complaint populates form
- [ ] Correction updates only intended fields
- [ ] Document upload works
- [ ] Related complaints render after seed
- [ ] Commit works
- [ ] Complaint number appears

---

## 8. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Browser CORS error | `CORS_ORIGINS` missing exact frontend origin, or typo / trailing slash mismatch |
| Readiness fails | Wrong `DATABASE_URL`, Neon paused, SSL params, or migrations not applied |
| Assistant 503 | Missing/invalid `GROQ_API_KEY` or model unavailable |
| Upload fails before API | File &gt; 4 MiB or Vercel body limit; confirm both sides use 4 MiB |
| Frontend calls localhost | `VITE_API_BASE_URL` not set for Production; rebuild/redeploy after setting |
| Preview UI cannot call prod API | Preview origin not in `CORS_ORIGINS` (expected) |
| AI timeout | Raise Function `maxDuration` in Vercel project settings only if needed (start at 60s) |

---

## 9. Security reminders

- No secrets in the GitHub repo or frontend env
- Logs must not include complaint bodies, extracted text, evidence, keys, or DB URLs
- Document intake remains **in-memory only**
- Migrations and seed remain **manual**

---

## 10. Local vs production

| Concern | Local | Vercel production |
| --- | --- | --- |
| Frontend | `npm run dev` + `frontend/.env` | Vite build on Vercel |
| Backend | `uvicorn app.main:app` | `api.index:app` Python Function |
| Database | Local PostgreSQL | Neon |
| Upload limit | 4 MiB (same default) | 4 MiB |
| CORS | `http://localhost:5173` | Production frontend URL |
