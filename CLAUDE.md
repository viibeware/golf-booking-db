# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Self-hosted Flask + SQLite web app for collecting golf resort customer intake information. Shipped as a Docker image (`viibeware/golf-booking-db`). Version tracked in `CHANGELOG.md` and rendered in-app as release notes.

## Commands

```bash
# Run locally via Docker (builds from source)
docker compose up -d --build

# View logs / restart
docker compose logs -f
docker compose restart

# Backup / restore the SQLite DB (volume: golfdb_data -> /data)
docker cp golf-booking-db:/data/golf_booking_db.db ./backup.db
docker cp ./backup.db golf-booking-db:/data/golf_booking_db.db && docker compose restart

# Reset admin password
docker exec -it golf-booking-db python3 -c "from werkzeug.security import generate_password_hash; import sqlite3; c=sqlite3.connect('/data/golf_booking_db.db'); c.execute('UPDATE users SET password_hash=? WHERE username=?',(generate_password_hash('newpass'),'admin')); c.commit()"
```

No test suite, linter, or build step beyond Docker. `.env` (copied from `.env.example`) must set `SECRET_KEY` before deploying.

## Architecture

Single-file Flask app — **all routes, auth, DB access, and PDF generation live in `app.py`** (~1150 lines). Templates in `templates/`, vanilla JS/CSS in `static/`.

Key structural points a newcomer needs to know:

- **DB schema + migrations are in `init_db()` (`app.py:47`).** It runs on every startup and is the *only* migration mechanism — adding a new column means extending `init_db()` with an `ALTER TABLE ... ADD COLUMN` guarded by a column-existence check. There is no Alembic/separate migrations dir. The README promises "auto-migrates on startup"; preserve that contract.
- **Intake numbers** are generated sequentially (GBD1001+) in `generate_intake_number()` — do not rely on `id` for user-facing references.
- **Tee times are a child table.** `save_tee_times()` and `get_booking_with_tees()` handle the one-to-many (bookings → tee_days → tee_time slots) relationship; booking edit/create must go through these, not raw inserts.
- **Authorization has two layers:**
  1. Role gate via `@role_required(...)` / `@login_required` decorators.
  2. Per-editor granular permissions (`delete`, `archive`, `export`, `import`, `view_all`, `print_pdf`) loaded by `get_user_permissions()` and injected into templates through `inject_user()` (context processor). Admins implicitly have all permissions.
  3. Row-level isolation via `can_access_booking()` — editors without `view_all` only see records where `created_by = their user_id`. Every booking-scoped route must call it.
- **CSV export/import** must also respect `view_all` (see `export_csv` at `app.py:1021`). Import assigns fresh intake numbers rather than preserving them.
- **PDF generation** uses ReportLab inline in `export_pdf()` (`app.py:777`, ~240 lines) — two-column branded layout. Any new intake field that should appear on the PDF needs to be added there explicitly; it is not data-driven from the schema.
- **No-cache headers** are applied globally (`add_no_cache_headers`) because the app is updated in place via `docker compose pull`; stale JS/CSS would break users. Don't remove without replacing the cache-busting strategy.
- **Frontend is vanilla.** `static/js/app.js` handles modals, sort, search, bulk select, theme toggle — no build step, no framework. Edit and ship.

## Conventions

- Default admin creds (`DEFAULT_ADMIN_USER` / `DEFAULT_ADMIN_PASS`) are only consulted when the `users` table is empty on first run.
- User-facing version string lives in `CHANGELOG.md` and the About tab; bump both together when releasing.
- The app listens on port 5000 inside the container; `APP_PORT` in `.env` maps to the host.
