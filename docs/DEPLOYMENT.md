# Deployment Guide

This project is deploy-ready for a split deployment: **frontend on Vercel**, **backend + PostgreSQL on Railway or Render**. It can also run anywhere Docker runs.

---

## Option A — Docker Compose (single host / VPS)

The simplest production-like deployment.

```bash
cp .env.example .env
# set strong secrets:
#   JWT_SECRET_KEY=<random 32+ chars>
#   POSTGRES_PASSWORD=<strong password>
#   OPENAI_API_KEY=<optional>
#   NEXT_PUBLIC_API_URL=https://api.yourdomain.com
#   CORS_ORIGINS=https://app.yourdomain.com
docker compose up --build -d
```

Put a reverse proxy (Caddy/Nginx/Traefik) in front for TLS, routing `app.yourdomain.com → :3000` and `api.yourdomain.com → :8000`.

---

## Option B — Vercel (frontend) + Railway/Render (backend)

### 1. Backend + Database on Railway

1. Create a new Railway project → **Add PostgreSQL** plugin.
2. **New Service → Deploy from repo**, set **Root Directory** to `backend/` (Railway auto-detects the Dockerfile).
3. Set environment variables on the backend service:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}   # convert to postgresql+psycopg://...
   JWT_SECRET_KEY=<random 32+ chars>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   CORS_ORIGINS=https://<your-vercel-app>.vercel.app
   OPENAI_API_KEY=<optional>
   ENVIRONMENT=production
   ```
   > Railway's `DATABASE_URL` uses the `postgresql://` scheme. Change the prefix to `postgresql+psycopg://` so SQLAlchemy uses psycopg 3.
4. Set the start command (or rely on the Dockerfile CMD):
   ```
   python -m app.cli init-db && python -m app.cli seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Deploy and note the public URL, e.g. `https://scc-backend.up.railway.app`.

> **Render** is equivalent: New → **Web Service** from `backend/` (Docker), add a **PostgreSQL** instance, set the same env vars, and use the same start command. Render provides `$PORT` automatically.

### 2. Frontend on Vercel

1. **Import Project** → set **Root Directory** to `frontend/`.
2. Framework preset: **Next.js** (auto-detected).
3. Environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://scc-backend.up.railway.app
   ```
4. Deploy. Vercel builds and hosts the Next.js app.

### 3. Wire CORS

Make sure the backend `CORS_ORIGINS` includes your Vercel domain (and any custom domain). Redeploy the backend after changing it.

---

## Production checklist

- [ ] **Secrets:** strong `JWT_SECRET_KEY` and DB password; never commit `.env`.
- [ ] **Seeding:** run `seed --if-empty` once. For a clean production system, create real users via `python -m app.cli create-user ...` and skip synthetic data (`SEED_ON_STARTUP=false`).
- [ ] **Migrations:** prefer `alembic upgrade head` over `init-db` for schema changes.
- [ ] **CORS:** restrict `CORS_ORIGINS` to known frontends.
- [ ] **HTTPS:** terminate TLS at the platform/proxy.
- [ ] **AI:** set `OPENAI_API_KEY` to enable OpenAI; otherwise the local engine is used.
- [ ] **Observability:** enable platform logs/metrics; `/health` is a ready-made liveness probe.
- [ ] **Scaling:** backend is stateless (JWT) and can run multiple replicas; size the DB connection pool accordingly.

---

## Environment variables reference

### Backend

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | local compose DB | SQLAlchemy URL (`postgresql+psycopg://…`) |
| `JWT_SECRET_KEY` | dev placeholder | **Change in production** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `OPENAI_API_KEY` | _(empty)_ | Enables OpenAI advisor |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `SEED_ON_STARTUP` | `false` | Seed synthetic data on boot |
| `ENVIRONMENT` | `development` | Environment label |

### Frontend

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL (no trailing slash) |
