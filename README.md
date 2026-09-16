# 🇮🇳 MakeMeRich — Indian Equity Intelligence Platform

An AI-assisted Indian equity research platform that combines historical, technical, fundamental and current-market evidence to produce transparent opportunity analyses.

> **This is a decision-support system, not a profit-guarantee engine.**

---

## Architecture

```
services/api/            ← FastAPI backend (Python)
services/market_data/    ← Market data ingestion pipeline
services/feature_engine/ ← Technical indicators + market regime
apps/web/                ← Next.js 15 frontend
packages/shared_types/   ← Shared Pydantic schemas
data/migrations/         ← Alembic DB migrations
infra/docker/            ← Docker Compose for local dev
docs/                    ← Architecture docs + dev log
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.14 + FastAPI + Uvicorn |
| Database | PostgreSQL 16 + TimescaleDB |
| Cache / Queue | Redis 7 |
| Migrations | Alembic |
| ORM | SQLAlchemy 2.0 (async) |
| Task Queue | Celery 5 |
| Frontend | Next.js 15 + TypeScript |
| AI/ML | LangGraph + LangChain + scikit-learn + PyTorch |
| Containers | Docker + Docker Compose |

## Quick Start

### 1. Start dev services
```bash
cd infra/docker
docker compose up -d
```

### 2. Set up environment
```bash
cp services/api/.env.example services/api/.env
# Edit .env and add your broker API keys
```

### 3. Run DB migrations
```bash
cd data
alembic upgrade head
```

### 4. Start API server
```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Start frontend
```bash
cd apps/web
npm install
npm run dev
```

## Development Phases

| Phase | Status | Description |
|---|---|---|
| V1 | 🔨 In Progress | Data + Analytics foundation |
| V2 | ⏳ Planned | Multi-agent AI analysis |
| V3 | ⏳ Planned | Opportunity Engine |
| V4 | ⏳ Planned | Personal Intelligence |
| V5 | ⏳ Planned | F&O expansion |

## Docs

- [System Design](Indian_Equity_Intelligence_Platform_System_Design.md)
- [Dev Log](docs/dev_log.md)
