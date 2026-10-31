# MindBridge

MindBridge is a web platform we developed for ALU Rwanda students. It imports Canvas assignments, turns rubric requirements into dated milestones, and adjusts the study schedule using a short daily wellness check-in.

MindBridge supports schedule planning. It does not diagnose or treat mental health.

## Structure

```
mindbridge/
├── backend/     Flask REST API and PostgreSQL access
├── frontend/    Next.js (TypeScript) web client
└── docs/
    └── diagrams/  Architecture, class and use case diagrams
```

## Running locally

Requirements: Python 3.12, Node.js 20.9+, and PostgreSQL.

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # adjust DATABASE_URL if needed
flask --app app run --port 5001
```

Before the first run, create the role and database that `.env.example` expects (use the password `mindbridge` for local development):

```bash
createuser -P mindbridge
createdb -O mindbridge mindbridge
createdb -O mindbridge mindbridge_test   # used by the tests
```

Then check `http://127.0.0.1:5001/api/v1/health`. It returns `503` when the database is unreachable.

Run the tests with `python -m pytest` from `backend/`. They run against PostgreSQL in the `mindbridge_test` database, which is dropped and recreated on each run, so never point `TEST_DATABASE_URL` at the development database.

### Frontend

```bash
cd frontend
npm install
npm run dev
```
