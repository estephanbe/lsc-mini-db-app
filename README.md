# LSC Mini DB App

A tiny public FastAPI service backed by managed Postgres, deployed on DigitalOcean
App Platform. Each page load records a visit in the database and shows the running
total + the most recent visits — proving a public app + database end-to-end.

## Endpoints
- `GET /` — records a visit, renders the count and recent visits.
- `GET /health` — JSON liveness + database connectivity check.

## Stack
- FastAPI + uvicorn (Python buildpack)
- Postgres via the `DATABASE_URL` env var injected by App Platform's managed DB.

## Deploy
Deployed from this repo via `doctl apps create --spec .do/app.yaml`. The app spec
attaches a dev Postgres database and wires `DATABASE_URL` into the service.
