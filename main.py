"""LSC mini DB app — a tiny public FastAPI service backed by Postgres.

Proves a public app + managed database on DigitalOcean App Platform. It records a
visit on each page load and shows the running total + recent visits, read from the DB.
"""

import os
from datetime import datetime, timezone

import psycopg2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = FastAPI(title="LSC Mini DB App")


def _connect():
    # DO managed Postgres requires SSL; the injected URL already carries sslmode=require.
    return psycopg2.connect(DATABASE_URL)


def _init_schema() -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS visit ("
                " id serial PRIMARY KEY,"
                " at timestamptz NOT NULL DEFAULT now(),"
                " ua text)"
            )
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def _startup() -> None:
    if not DATABASE_URL:
        print("WARN: DATABASE_URL not set")
        return
    try:
        _init_schema()
        print("schema ready")
    except Exception as exc:  # noqa: BLE001
        print(f"schema init failed: {exc}")


@app.get("/health")
def health() -> JSONResponse:
    db_ok = False
    detail = "no DATABASE_URL"
    if DATABASE_URL:
        try:
            conn = _connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                db_ok = True
                detail = "connected"
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)[:120]
    return JSONResponse({"status": "ok", "database": db_ok, "detail": detail})


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    total, recent = 0, []
    if DATABASE_URL:
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO visit DEFAULT VALUES")
                cur.execute("SELECT count(*) FROM visit")
                total = cur.fetchone()[0]
                cur.execute("SELECT at FROM visit ORDER BY at DESC LIMIT 8")
                recent = [r[0] for r in cur.fetchall()]
            conn.commit()
        finally:
            conn.close()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = "".join(
        f"<li>{t.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>" for t in recent
    ) or "<li>no visits yet</li>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>LSC Mini DB App</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
  :root {{ --forest:#123524; --grass:#1f9d52; --lime:#b6f04a; --paper:#f4f1e8; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px;
    font-family:"Plus Jakarta Sans",system-ui,sans-serif; color:#0c1a10;
    background:radial-gradient(900px 500px at 80% -10%,rgba(31,157,82,.18),transparent 60%),
      radial-gradient(700px 400px at -5% 110%,rgba(182,240,74,.16),transparent 55%),var(--paper); }}
  .card {{ width:min(480px,100%); background:#fffdf7; border-radius:24px; padding:34px;
    box-shadow:20px 30px 60px -25px rgba(18,53,36,.35); border:1px solid rgba(255,255,255,.6); }}
  .badge {{ font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--grass);
    font-weight:700; }}
  h1 {{ font-family:"Fraunces",serif; font-weight:700; font-size:30px; margin:6px 0 4px; }}
  p.sub {{ color:#6b7568; margin:0 0 22px; font-size:14px; }}
  .count {{ font-family:"Fraunces",serif; font-weight:700; font-size:64px; line-height:1;
    background:linear-gradient(135deg,var(--grass),var(--forest)); -webkit-background-clip:text;
    background-clip:text; color:transparent; }}
  .count-label {{ color:#6b7568; font-size:13px; margin-top:4px; }}
  ul {{ list-style:none; padding:0; margin:22px 0 0; border-top:1px solid #e6e0d3; padding-top:16px; }}
  li {{ font-size:13px; color:#3a443a; padding:5px 0; font-variant-numeric:tabular-nums; }}
  .foot {{ margin-top:20px; font-size:12px; color:#9aa195; }}
  .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--grass); margin-right:6px; }}
</style></head>
<body>
  <div class="card">
    <div class="badge">Life Sports Club · demo</div>
    <h1>Mini DB App</h1>
    <p class="sub">A tiny public app on DigitalOcean App Platform, backed by managed Postgres.</p>
    <div class="count">{total}</div>
    <div class="count-label">total visits recorded in the database</div>
    <ul>{rows}</ul>
    <div class="foot"><span class="dot"></span>served {now} · refresh to record another visit</div>
  </div>
</body></html>"""
