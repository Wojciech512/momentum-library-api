# Library API

REST API for tracking a library's books: add, delete, list and record borrow/return events.

## Run

```bash
docker compose up
```

API docs: <http://localhost:8001/docs#/>

Add `--watch` for live reload: code changes sync into the running container and restart it, dependency changes trigger a rebuild.

## About the project

A library information system backend for library staff: the API registers books, lists the collection and records who borrowed a book and when. Each book is identified by a staff-entered six-digit serial number and carries a title, an author and its borrow state: the borrower's six-digit card number and a server-set timestamp, or neither when the book is available.

The service exposes four operations (`POST /books`, `GET /books`, `DELETE /books/{serial}` and `PATCH /books/{serial}/status` with `borrowed` / `available`) with strict validation (`^[0-9]{6}$` identifiers, schema-enforced borrow/return payloads) and loud failure semantics: invalid transitions return `409` with the row unchanged, malformed input returns `422`. Consistency is anchored in the database itself: a `CHECK` constraint makes half-borrowed rows unrepresentable and row locking serializes concurrent borrows.

Technologies:

- Python 3.14
- FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async), asyncpg, Alembic
- PostgreSQL 18
- pytest, pytest-asyncio, httpx
- Ruff
- uv with `uv.lock`
- Docker multi-stage build, Docker Compose (healthchecks, tmpfs test database, watch mode)
- watchfiles

## Tests

The test runner is part of the stack: it starts alongside the API, runs lint and the 40-test suite once, and re-runs them automatically on every source change on the host. No local Python is needed. One-shot run (CI, pre-push; exit code propagates):

```bash
docker compose run --build --rm test-once
```

## Design decisions

**Six-digit numbers are strings, not integers.** The serial number is entered by staff, so its text form is the identity: an integer column would turn `000123` into `123` and an integer schema would reject it outright. The pattern is `^[0-9]{6}$` rather than `^\d{6}$`, because `\d` in Pydantic v2 matches Unicode digits, so Arabic-Indic `١٢٣٤٥٦` would otherwise become a valid, distinct primary key for "the same" number. The same type validates path parameters, so `DELETE /books/12a456` is a `422`, consistent with the request body.

**The serial number is the primary key.** It is unique, user-supplied and already the natural identifier, so it appears directly in URLs and uniqueness is enforced by the database constraint, not by an application-side check that loses every race. A duplicate insert surfaces as a unique violation and is mapped to `409`.

**Borrowed state is derived, not stored.** There is no `is_borrowed` column: a book is borrowed exactly when `borrowed_at` is set, and a table-level `CHECK` keeps `borrowed_at` and `borrower_card_number` both set or both null. A stored boolean can drift from the fields it summarizes; a derived one cannot, and inconsistent rows are unrepresentable rather than merely unlikely.

**One status endpoint with a discriminated union.** `PATCH /books/{serial}/status` takes `{"status": "borrowed", "borrower_card_number": "..."}` or `{"status": "available"}`. The discriminator makes a missing card number on borrow a schema-level `422` instead of a hand-written if, and `extra="forbid"` on the return variant rejects a card number where it is meaningless. The borrow timestamp is set by the server in UTC: the API records when the borrow happened, so the client does not get to back-date it.

**Invalid transitions are `409`, never silent no-ops.** Borrowing a borrowed book and returning an available one both fail loudly with the row unchanged. For a staff-facing tool, an operation that reports success while changing nothing is worse than an error. The update selects the row `FOR UPDATE`, so two concurrent borrow requests cannot both observe an available book.

**Robustness beyond the happy path.** A NUL byte in `title`/`author` passes length checks but is rejected by PostgreSQL after the request handler, so the schema forbids it (`^[^\x00]+$`) and the client gets a `422` instead of an unhandled `500`. Wrong JSON types (`true`, `123456` as numbers) are pinned by tests as `422`: Pydantic v2 does not coerce them, and the tests keep it that way.

**Migrations run in the container entrypoint.** `alembic upgrade head` executes before `uvicorn` starts, so a clean clone boots a fully migrated database and the schema has exactly one owner. The app never calls `create_all` at runtime, because import-time DDL hides migration drift until it hurts.

**Compose is the whole runbook.** The `db` service has a `pg_isready -h 127.0.0.1` healthcheck, probing over TCP because the official postgres image runs a temporary init-phase server on the Unix socket that answers before the real one is up, and `api` starts only on `service_healthy`, eliminating cold-start connection races. Data lives in a named volume and all services sit on an explicit bridge network; the database publishes no host port at all; only the API's port (host `8001`) is exposed, and it is bound to `127.0.0.1`, so nothing collides with a locally installed PostgreSQL, the database never faces the host and the unauthenticated API is reachable only from the local machine.

**Multi-stage image, locked dependencies, non-root runtime.** Dependencies install from `uv.lock` with `uv sync --frozen`: the lock is cross-platform and hash-pinned, so the container gets bit-for-bit the dependency set that was tested, not whatever `>=` floors resolve to on build day. The dependency layer installs before the source is copied (`--no-install-project`), so code changes do not invalidate the dependency cache, and uv's download cache is mounted at build time rather than baked into layers. The `test` stage adds dev dependencies and the test suite; the `runtime` stage contains neither, copies only the synced virtualenv and the sources — so the uv binary itself ships only in build and test images — and runs as an unprivileged user.

**`uv` with `uv.lock` over `requirements.txt`.** One tool owns the environment, the lockfile and the sync; a `requirements.in`/`requirements.lock.txt` pair would duplicate what `pyproject.toml` already declares and, compiled with pip-tools, would be resolved only for the platform that ran the compile. `uv.lock` resolves for all platforms at once with hashes always included, and `uv export --format requirements.txt` remains available if a pip-only consumer ever needs it.

**Tests run against an ephemeral real PostgreSQL.** No SQLite substitution: the suite exercises the actual `CHECK` constraint, `FOR UPDATE` and asyncpg behavior. A dedicated `db-test` instance backed by `tmpfs` runs beside the dev database: its data lives in RAM and the dev database is never touched by tests. The runner is a live sidecar (`watchfiles` re-runs lint and the suite on every source change through read-only bind mounts), and a separate `test-once` service, defined via `extends` with the entrypoint swapped for the one-shot runner, serves CI with a single command and a propagated exit code. Each test additionally runs inside an outer transaction that is rolled back, so tests are order-independent without truncation — with one honest exception: the concurrency test commits real rows through its own engine, because `FOR UPDATE` cannot be exercised inside a single session, and cleans the table itself. The whole suite is runnable with Docker alone, so reviewing the project requires no local Python at all.

**Live reload is opt-in, the delivered image stays production-like.** The `api` service carries a `develop.watch` section (sync and restart on source changes, full rebuild when `pyproject.toml` or `uv.lock` change) that is completely inert under plain `docker compose up`: the reviewer runs the same non-root image with no bind mounts and no reload flags, and `--watch` enables the development loop without a separate compose file.

**Shell lives in scripts, not in YAML.** Every shell pipeline (`entrypoint.sh` for migrations plus server start, `run-tests.sh` for the lint-migrate-test sequence, `watch-tests.sh` for the watch loop) is a file under `api/scripts/`, mounted and copied as a unit. Compose entrypoints reference the scripts by name, so there are no inline `sh -c` one-liners to maintain in two places.

**One tool for lint and format.** Ruff covers linting, import sorting and formatting in a single config, and runs inside the test container ahead of the suite, so the same command gates style and behavior; findings were fixed rather than suppressed (the router uses `Annotated` dependencies instead of silencing `B008`), and the Alembic template was modernized so future autogenerated migrations come out clean.
