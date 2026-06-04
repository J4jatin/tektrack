# TekTrack — Internal Photomask Production Operations Tracker

A full-stack internal operations tool for tracking photomask production orders through their lifecycle — from initial receipt through mask writing, quality check, approval, and delivery.

Built as a portfolio project demonstrating Python, UNIX/Linux Shell scripting, SQL databases, XML data ingestion, FastAPI REST API design, and lightweight frontend development.

[![CI](https://github.com/YOUR_USERNAME/tektrack/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/tektrack/actions)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python · FastAPI · Pydantic |
| Database | SQLite · SQL · XML ingestion |
| Frontend | Streamlit |
| Testing | pytest (30 tests) |
| CI/CD | GitHub Actions (Ubuntu Linux, Python 3.10/3.11/3.12) |
| Scripting | Bash Shell (setup, ingest, backup) |
| Version Control | Git |

## Production Order Lifecycle

```
ORDER_RECEIVED → DESIGN_REVIEW → MASK_WRITING → QUALITY_CHECK → APPROVED → SHIPPED → DELIVERED
```

State transitions are enforced on both the API layer and database level — invalid transitions return HTTP 400.

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/YOUR_USERNAME/tektrack.git
cd tektrack
bash scripts/setup_env.sh

# 2. Start the API
source .venv/bin/activate
uvicorn main:app --reload

# 3. Start the dashboard (new terminal)
source .venv/bin/activate
streamlit run frontend/app.py

# 4. Run tests
pytest tests/ -v
```

## Project Structure

```
tektrack/
├── .github/workflows/ci.yml     # GitHub Actions CI — Python 3.10/3.11/3.12 on Ubuntu
├── backend/
│   ├── database.py              # SQLite setup, XML ingestion, SQL queries
│   ├── models.py                # Pydantic validation models
│   ├── routes/
│   │   ├── orders.py            # CRUD + state machine endpoints
│   │   └── analytics.py        # Summary, pipeline, throughput endpoints
│   └── data/
│       └── sample_orders.xml    # Seed data (8 photomask orders)
├── frontend/
│   └── app.py                   # Streamlit dashboard
├── scripts/
│   ├── setup_env.sh             # Environment setup (venv, deps, DB init)
│   ├── ingest.sh                # XML → SQLite ingestion script
│   └── backup_db.sh             # Timestamped DB backup (cron-ready)
├── tests/
│   ├── conftest.py              # pytest fixtures (tmp DB, seeded client)
│   ├── test_database.py         # Unit tests: XML ingestion, SQL, state machine
│   ├── test_orders_api.py       # Integration tests: CRUD, transitions
│   └── test_analytics_api.py    # Integration tests: analytics endpoints
├── main.py                      # FastAPI app entry point
├── requirements.txt
└── .gitignore
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/orders/` | List all orders (filterable by status, priority, customer) |
| GET | `/orders/{id}` | Get single order |
| POST | `/orders/` | Create new order |
| PATCH | `/orders/{id}/status` | Advance status (state machine enforced) |
| GET | `/orders/{id}/log` | Full status change history |
| DELETE | `/orders/{id}` | Delete (ORDER_RECEIVED only) |
| GET | `/analytics/summary` | Aggregate counts by status/priority/customer |
| GET | `/analytics/pipeline` | Orders grouped by status |
| GET | `/analytics/throughput` | Delivered orders by week |

## Shell Scripts

```bash
# Set up environment from scratch
bash scripts/setup_env.sh

# Ingest a new XML orders file
bash scripts/ingest.sh path/to/new_orders.xml

# Backup the database (add to cron for daily backups)
bash scripts/backup_db.sh
# Cron: 0 2 * * * bash /path/to/tektrack/scripts/backup_db.sh
```

## Deployment

- **Backend:** [Render.com](https://render.com) — connect GitHub repo, set start command to `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Frontend:** [Streamlit Cloud](https://streamlit.io/cloud) — connect GitHub repo, set main file to `frontend/app.py`, set `API_BASE` env var

## Author

**Jattin Shah** — MSc Applied AI, Technische Universität Dresden
