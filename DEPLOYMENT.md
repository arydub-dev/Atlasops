# Deploying ATLASOPS

ATLASOPS is a three-part system: a **PostgreSQL** database, a **FastAPI** backend,
and a **Next.js** frontend.

```
┌────────────┐      HTTPS      ┌──────────────┐      SQL      ┌──────────────┐
│  Next.js   │ ─────────────▶  │   FastAPI    │ ───────────▶  │  PostgreSQL  │
│  frontend  │   /api/v1/...   │   backend    │  DATABASE_URL │   database   │
└────────────┘                 └──────────────┘               └──────────────┘
```

You can deploy it two ways:

- **[Option A — All-in-one on Vercel](#option-a--all-in-one-on-vercel)**: frontend
  and backend in a single Vercel project (Vercel "Services"), plus a managed
  Postgres add-on.
- **[Option B — Render](#option-b--render-blueprint)**: one Blueprint that
  provisions Postgres + backend + frontend together (includes the database).

---

# Option A — All-in-one on Vercel

The repo includes [`vercel.json`](./vercel.json), which uses Vercel
[Services](https://vercel.com/docs/services) to run the Next.js frontend at `/`
and the FastAPI backend at `/api` in the **same project and domain**. Because
they share an origin, the frontend talks to the backend at `/api/v1/...` with no
CORS configuration and no separate backend URL to manage.

Vercel does not host a database, so you add a managed Postgres in a couple of
clicks.

### 1. Create the project

1. In Vercel, **Add New → Project** and import `arydub-dev/Atlasops`.
2. Leave **Root Directory** as the repository root (`./`). Vercel reads
   `vercel.json`, detects the **Services** preset, and shows two services:
   `web` (Next.js) and `api` (FastAPI).
3. Don't deploy yet — add the database first (next step).

### 2. Add a Postgres database

1. In the project, go to **Storage → Create Database → Postgres** (Neon-backed),
   or add **Neon**/**Supabase** from the Marketplace.
2. Connect it to the project for the **Production** environment. This injects the
   connection string env vars automatically (`DATABASE_URL` / `POSTGRES_URL` /
   `POSTGRES_URL_NON_POOLING`). The backend reads whichever is present and
   normalizes the driver — no manual editing needed.

### 3. Set environment variables (backend)

On the project's **Environment Variables**:

| Key | Value |
| --- | --- |
| `JWT_SECRET_KEY` | a long random string (32+ chars) |
| `ENVIRONMENT` | `production` |
| `SEED_ON_STARTUP` | `true` (seeds demo data + logins on first request) |
| `OPENAI_API_KEY` | *(optional — enables OpenAI Copilot; otherwise local advisor)* |

`NEXT_PUBLIC_API_URL` is **not needed** — the frontend calls the backend on the
same origin automatically. `CORS_ORIGINS` is also unnecessary (same origin).

### 4. Deploy & verify

1. Click **Deploy**.
2. Open the deployment URL. The first load triggers a backend cold start that
   seeds the demo dataset (give it a few seconds).
3. **Login** with a demo account: `ops@atlasops.io` / `ops12345`.

### 5. Custom `.online` domain

1. Project → **Settings → Domains → Add** → enter `atlasops.online` (and
   `www.atlasops.online`).
2. Add the DNS records Vercel shows at your registrar, typically:

   | Type | Name | Value |
   | --- | --- | --- |
   | `A` | `@` | `76.76.21.21` |
   | `CNAME` | `www` | `cname.vercel-dns.com` |

   Use the exact values Vercel displays. Both frontend and backend live on this
   one domain (`/` and `/api`), so no extra DNS is needed for the API.

### Notes (Vercel)

- The backend runs as serverless functions (no Docker). The engine uses no
  connection pooling on Vercel and disables psycopg prepared statements so it
  works through Postgres poolers.
- The `backend/Dockerfile` and `render.yaml` are unused on Vercel; they remain
  for the Render path below.
- Hobby plan functions cap at 60s — enough for the trimmed first-boot seed.

---

# Option B — Render (Blueprint)

The included [`render.yaml`](./render.yaml) Blueprint provisions Postgres +
backend + frontend together (the database is included, unlike Vercel).

## 1. Deploy with the Blueprint

1. Push this repository to GitHub (already done).
2. In the [Render Dashboard](https://dashboard.render.com), click
   **New → Blueprint**.
3. Connect the `arydub-dev/Atlasops` repository. Render detects `render.yaml`
   and shows three resources: `atlasops-db`, `atlasops-api`, `atlasops-web`.
4. Click **Apply**. Render builds and deploys everything.

`JWT_SECRET_KEY` is generated automatically, and `DATABASE_URL` is wired to the
managed Postgres instance. On first boot the backend creates all tables and
seeds the demo dataset + demo accounts (`SEED_ON_STARTUP=true`).

## 2. Wire the two services together

Two variables are intentionally left blank (`sync: false`) because each depends
on the other service's final URL.

After the first deploy, note the two service URLs (e.g.
`https://atlasops-api.onrender.com` and `https://atlasops-web.onrender.com`),
then:

1. **Backend** (`atlasops-api` → Environment):
   - `CORS_ORIGINS` = the frontend URL
     (e.g. `https://atlasops-web.onrender.com`).
     Add your custom domain here too once configured (comma-separated).
2. **Frontend** (`atlasops-web` → Environment):
   - `NEXT_PUBLIC_API_URL` = the backend URL
     (e.g. `https://atlasops-api.onrender.com`).
   - ⚠️ This value is **baked in at build time**, so after setting it you must
     **Manual Deploy → Clear build cache & deploy** on `atlasops-web`.

## 3. Verify

- Backend health: `https://atlasops-api.onrender.com/health` → `{"status":"healthy"}`
- Backend docs: `https://atlasops-api.onrender.com/docs`
- Frontend: open the web URL, then **Login** with a demo account:
  - `ops@atlasops.io` / `ops12345`

---

## 4. Connect a custom `.online` domain

You can put the frontend on your apex domain and the backend on an `api`
subdomain.

### In Render

1. **Frontend** (`atlasops-web` → **Settings → Custom Domains**):
   - Add `atlasops.online` and `www.atlasops.online`.
2. **Backend** (`atlasops-api` → **Settings → Custom Domains**):
   - Add `api.atlasops.online`.

Render shows the DNS records to create for each domain.

### At your domain registrar (DNS)

Create these records (use the exact targets Render shows you):

| Type    | Host / Name | Value (from Render)              |
| ------- | ----------- | -------------------------------- |
| `A`     | `@`         | Render's anycast IP (apex)       |
| `CNAME` | `www`       | `atlasops-web.onrender.com`      |
| `CNAME` | `api`       | `atlasops-api.onrender.com`      |

> Some registrars don't allow `CNAME` on the apex (`@`). In that case use
> Render's provided `A` record for the apex, or set the apex as a redirect to
> `www` and point `www` via `CNAME`.

Wait for DNS to propagate; Render auto-provisions TLS certificates.

### Update the two env vars to the custom domains

1. `atlasops-web` → `NEXT_PUBLIC_API_URL` = `https://api.atlasops.online`
   → **Clear build cache & deploy**.
2. `atlasops-api` → `CORS_ORIGINS` =
   `https://atlasops.online,https://www.atlasops.online`
   → save (triggers a redeploy).

---

## Troubleshooting

- **`failed to read dockerfile: open Dockerfile: no such file or directory`**
  Render looked for the Dockerfile at the repo root. This blueprint sets
  `dockerfilePath`/`dockerContext` to the `backend/` and `frontend/`
  subdirectories (paths are relative to the **repo root**), which resolves it.
  If you created the services manually instead of via the Blueprint, set each
  service's **Dockerfile Path** to `backend/Dockerfile` / `frontend/Dockerfile`
  in **Settings**.
- **Applying blueprint changes:** When you push an updated `render.yaml`, open
  the Blueprint in Render and **Sync** (or **Apply**) so the new settings take
  effect on the existing services, then trigger a redeploy.

## Notes & tips

- **Free tier cold starts:** Free Render services sleep after ~15 minutes of
  inactivity and take a few seconds to wake. Upgrade to a paid instance for
  always-on, and to keep the database beyond the free retention window.
- **psycopg driver:** Render hands out `postgresql://` URLs. The app rewrites
  these to `postgresql+psycopg://` automatically (`backend/app/core/database.py`),
  so no manual editing is required.
- **Ports:** The backend binds to Render's injected `$PORT`
  (`backend/Dockerfile`), and the Next.js standalone server honors `$PORT` as
  well — no configuration needed.
- **Re-seeding:** Set `SEED_ON_STARTUP=false` after the first successful seed if
  you don't want the empty-check to run on every boot (it never overwrites
  existing data regardless).
