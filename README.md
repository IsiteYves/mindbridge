# MindBridge

MindBridge is a web platform for ALU Rwanda students. It imports Canvas
assignments, turns rubric requirements into dated milestones a student can
freely edit and reorder, and helps keep a plan realistic: a daily focus
timer and a small "today" checklist, a workload heatmap showing how work is
spread across the month, reminder emails before a deadline and if something
slips, and an optional AI-assisted second opinion on a plan's balance against
its rubric.

MindBridge supports schedule planning. It does not diagnose or treat mental
health. Its plan reviewer is advisory only: it never writes a milestone or
changes a date by itself. Every suggestion is applied one at a time, only
when the student chooses to.

## Structure

```
mindbridge/
├── backend/     Flask REST API and PostgreSQL access
│   └── app/
│       ├── api/         routes
│       ├── services/    business logic with no Flask dependency
│       │   └── agent/   the plan-review graph (LangGraph); see its own docstrings
│       └── cli.py       `flask reminders send`, `flask canvas sync-all`
├── frontend/    React (TypeScript, Vite) web client
└── docs/
    └── diagrams/  Architecture, class and use case diagrams
```

## Running locally

Requirements: Python 3.12 or newer, Node.js 20.9+, and PostgreSQL.

### Backend

```bash
cd backend
python -m venv .venv

#macOS / Linux
source .venv/bin/activate
cp .env.example .env

#Windows 
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env

pip install -r requirements-dev.txt

```

Create the role and database `.env.example` expects (use the password
`mindbridge` for local development):

```bash
createuser -P mindbridge
createdb -O mindbridge mindbridge
createdb -O mindbridge mindbridge_test   # used by the tests
```
```
psql -U postgres
```
Then, at the `postgres=#` prompt:

```sql 
CREATE USER mindbridge WITH PASSWORD 'mindbridge';
CREATE DATABASE mindbridge OWNER mindbridge;
CREATE DATABASE mindbridge_test OWNER mindbridge;
\q
```

Apply every migration:

```bash
flask --app app db upgrade
```

This brings a fresh database to the current schema in one step. If you are
instead upgrading a database that already has rows in it, read each
migration's own docstring first — a few are destructive by design (for
example, dropping a table whose feature was removed) and say so up front.

Then run the server:

```bash
flask --app app run --port 5001
```

Check `http://127.0.0.1:5001/api/v1/health`. It returns `503` when the
database is unreachable.

Set `TEST_DATABASE_URL` in `backend/.env` (see `.env.example`), then run the
tests with `python -m pytest` from `backend/`. They run against PostgreSQL in
the `mindbridge_test` database, which is dropped and recreated on each run,
so never point `TEST_DATABASE_URL` at the development database. The tests do not work with SQLite(sign-in code checks fail on time zones), and the database name must contain `test`.

To set it for one Powershell session instead of using `.env`:

```
$env:TEST_DATABASE_URL = "postgresql+psycopg://mindbridge:mindbridge@localhost:5432/mindbridge_test"
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Every value below is read from `backend/.env`; see `backend/.env.example`
for the exact keys. Only `DATABASE_URL` and `SECRET_KEY` are required to run
at all — everything past that is a feature that degrades cleanly when its own
configuration is left unset.

| Setting | Required for | What happens if it's unset |
|---|---|---|
| `DATABASE_URL`, `SECRET_KEY` | everything | the app refuses to start. `SECRET_KEY` signs every sign-in token, so use a long random string. |
| `SMTP_HOST` and friends | sending any email (signup codes, password resets, reminders) | email sending fails with a clear error; nothing silently pretends to have sent anything |
| `CANVAS_BASE_URL` | importing or connecting Canvas | Canvas routes answer 503, "not configured" |
| `TOKEN_ENCRYPTION_KEY` | a **persistent** Canvas connection (`/canvas/connect`, `/canvas/sync`) | those routes answer 503; a one-shot `/canvas/import` (token pasted every time, never stored) still works without it. Generate a key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ANTHROPIC_API_KEY`, `AGENT_MODEL` | the AI-assisted half of plan review | the rule-based half of plan review (rubric balance, slipped milestones, a replan suggestion) still runs for free; the review's summary says plainly that the AI pass did not run |

## Scheduled jobs

Two commands run one pass and exit, meant to be triggered by whatever free
scheduler is available — a system cron entry, a scheduled CI workflow, a
platform's free cron-job tier — rather than run as an always-on worker
process, which on most hosts is the one thing that costs money:

```bash
flask --app app reminders send    # daily: send every reminder due today
flask --app app canvas sync-all   # daily: re-sync every connected Canvas account
```

Reminders cover a deadline or milestone 5, 2 or 1 day before it and on the
day itself (each togglable per student in Settings), plus a reminder once a
day for anything overdue and one the moment a Canvas import adds something
new — those last two are not optional.

## Security notes

- Passwords are hashed (never stored in plain text) and checked for basic
  strength at signup.
- Sign-in is rate-limited per account: five wrong passwords lock the account
  for 15 minutes. A locked account and a wrong password get the identical
  response, so neither can be used to find out which emails are registered
  or which accounts are currently locked out.
- Email verification codes and password-reset codes are single-use, expire
  after 10 minutes, and are themselves attempt-limited.
- A stored Canvas token is encrypted at rest (`TOKEN_ENCRYPTION_KEY`,
  Fernet/AES-128) and is never returned in any API response once connected.
- The plan reviewer's AI-assisted pass is sent rubric titles and milestone
  titles only — never a student's name, email, or anything from a wellness
  check-in.
- `SECRET_KEY` must be at least 32 characters; the app refuses to start
  otherwise, since every sign-in token is signed with it.

## Documentation

`docs/diagrams/` has the architecture, class and use case diagrams. Several
backend modules carry a module-level docstring explaining a non-obvious
design choice in more depth — `app/services/agent/` (why the plan reviewer
works without any AI provider configured), `app/services/reminders.py` (how
a reminder is claimed exactly once), and `app/api/canvas.py` (why a manual
milestone add never sends a notification but a Canvas import does) are
worth reading before changing any of the three.
