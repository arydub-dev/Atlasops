# Contributing to ATLASOPS

Thank you for your interest in contributing. This guide covers how to set up the project,
the standards we follow, and the pull request process.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you
agree to uphold it.

## Getting started

1. Fork and clone the repository.
2. Follow the local setup in the [README](README.md#running-locally). The fastest path is:
   ```bash
   ./start.sh
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/short-description
   ```

## Development workflow

### Backend (FastAPI)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the test suite before submitting:

```bash
cd backend && PYTHONPATH=. pytest
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run build       # verify a production build succeeds
```

## Coding standards

- **Backend:** Follow the thin-controller, rich-service pattern. Business logic belongs in
  `app/services/` (plain, testable functions), not in routers. Validate all I/O with
  Pydantic schemas. Keep ORM models the single source of truth for the schema.
- **Frontend:** Use TypeScript throughout. Prefer the existing UI primitives in
  `components/ui` and shared widgets in `components/shared`. Keep components composable and
  accessible. Avoid `console.log` in committed code.
- **Naming:** Use `ATLASOPS` consistently in user-facing text. Keep API, database, and
  folder naming consistent with existing conventions.
- **No secrets.** Never commit credentials, API keys, or `.env` files. Use
  `.env.example` for documenting configuration.

## Commit messages

Use clear, imperative commit messages (e.g. `add pipeline retry handling`). Conventional
Commit prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) are encouraged
but not required.

## Pull requests

1. Ensure tests, linting, type checks, and the production build pass.
2. Keep PRs focused and reasonably small; describe the motivation and approach.
3. Update documentation when behavior or configuration changes.
4. Reference any related issues.
5. Note any database schema changes and include the corresponding Alembic migration.

## Database changes

After modifying ORM models:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Commit the generated migration alongside the model change.

## Reporting issues

- **Bugs:** Open an issue with steps to reproduce, expected vs. actual behavior, and
  environment details.
- **Security:** Do not open a public issue. Follow [SECURITY.md](SECURITY.md).
