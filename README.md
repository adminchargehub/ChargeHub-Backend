# ChargeHub Backend

FastAPI + PostgreSQL. The booking, payments and device platform for ChargeHub
smart charging stations.

Project context and the prototype audit live in [`../CLAUDE.md`](../CLAUDE.md)
and [`../_reference/PROTOTYPE_AUDIT.md`](../_reference/PROTOTYPE_AUDIT.md).

## Stack

| | |
|---|---|
| Language | Python 3.12+ (verified on 3.13.7) |
| Framework | FastAPI, Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Migrations | Alembic |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose) + bcrypt |
| Tests | pytest + httpx, on in-memory SQLite |

## Quick start

```bash
docker compose up -d
```

```bash
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

```bash
cp .env.example .env && ./.venv/Scripts/python.exe -m alembic upgrade head
```

```bash
./.venv/Scripts/python.exe -m scripts.seed
```

```bash
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive docs at <http://localhost:8000/docs>. Seeded demo login is
`demo@chargehub.ng` / `chargehub123`.

On macOS/Linux the interpreter path is `./.venv/bin/python` instead.

> **Port note.** Postgres is published on host port **55432**, not 5432. This
> machine already has 5432 (the `falcon-postgres` container) and 5433 (a native
> Windows Postgres service) in use. Change `docker-compose.yml` and
> `DATABASE_URL` together if you want a different one.

## Tests

```bash
./.venv/Scripts/python.exe -m pytest
```

18 tests, no Docker required — they run against in-memory SQLite. Anything that
depends on PostgreSQL-specific behaviour (row locks, exclusion constraints)
needs an integration test against a real instance; there are none yet.

```bash
./.venv/Scripts/python.exe -m ruff check .
```

## Layout

```
app/
├─ core/          config, async engine/session, password hashing + JWT
├─ models/        SQLAlchemy — User, Station, Outlet, Plan, Booking
├─ schemas/       Pydantic request/response contracts
├─ services/      business logic (availability engine)
├─ api/
│  ├─ deps.py     DbSession, CurrentUser, require_roles()
│  └─ v1/         auth, stations, availability
└─ main.py
alembic/          migrations
scripts/seed.py   pilot station + plans + demo user
tests/
```

Modules map onto the service decomposition in the platform design doc (Users ·
Stations · Bookings · Payments · Energy · Devices · Notifications · Analytics).
It is a modular monolith on purpose — for one pilot station, splitting into
Lambdas now would cost more than it buys. The seams are drawn so the split is
mechanical later.

## What the scaffold deliberately fixes

Each of these is a defect found in the 2016 prototype (see the audit):

| Prototype | Here |
|---|---|
| `userprofile.password varchar(15)`, plaintext | bcrypt, 72-byte bound enforced rather than silently truncated |
| String-interpolated SQL on a device endpoint | SQLAlchemy parameter binding throughout |
| One table per socket (`socket1`..`socket4`) | `outlets` rows — a station scales to 50 with no schema change |
| Naive local-time comparisons | `UtcDateTime` — every timestamp is tz-aware UTC on both read and write |
| "Earliest free socket" that could not see gaps | gap-aware search, deterministic tie-break on outlet index |
| Power caps as dimensionless accumulator thresholds | real units: `power_cap_w`, `energy_cap_wh` |
| Client/server field-name drift, undetected for years | OpenAPI → generated TS client types (see frontend `gen:api`) |

## Known gaps

- **Booking creation is not implemented.** The availability engine finds a slot;
  nothing writes a `Booking` yet. `is_outlet_free()` exists and is advisory —
  when the write path lands it needs `SELECT ... FOR UPDATE` on the outlet row
  or a PostgreSQL exclusion constraint, or two concurrent requests can
  double-book the same window.
- **No access-code / PIN service.** Deliberate: the legacy 8-digit format
  (`access(5)|duration(1)|socket(1)|power(1)`) cannot address more than 9
  outlets, and the MVP is 8–12. The format has to be redesigned with the
  firmware before this is worth building. See audit §1.
- **No payments, no device/MQTT integration, no WebSocket** — the frontend polls
  every 10 s as a placeholder for the <2 s live-status target.
- **No rate limiting on auth.** The prototype had unlimited PIN attempts; do not
  repeat that here.
- `SECRET_KEY` must be replaced before any deployment — `get_settings()` refuses
  to start with the default when `ENVIRONMENT=production`.
