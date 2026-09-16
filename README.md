# 🇮🇳 MakeMeRich — Indian Equity Intelligence Platform

An AI-assisted Indian equity research platform that combines historical, technical, fundamental, and current-market evidence to produce transparent opportunity analyses using Multi-Agent LLM architecture (LangGraph) and Quantitative Machine Learning (XGBoost).

> **This is a decision-support system, not a profit-guarantee engine.**

---

## 🏗️ Architecture

```text
MakeMeRich/
├── apps/web/                ← Next.js 15 frontend (React, Tailwind)
├── apps/mobile/             ← React Native (Expo) mobile app
├── services/api/            ← FastAPI backend (Python)
├── services/market_data/    ← Market data ingestion pipeline (Angel One, Yahoo Finance)
├── services/feature_engine/ ← Technical indicators, Market regime, XGBoost Model
├── packages/shared_types/   ← Shared Pydantic schemas
├── data/migrations/         ← Alembic DB migrations
├── infra/docker/            ← Docker Compose for local dev (Postgres, Redis)
├── infra/terraform/         ← AWS Infrastructure as Code (ECS, RDS, S3, ElastiCache)
└── docs/                    ← Architecture docs + dev log
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.14 + FastAPI + Uvicorn |
| **Database** | PostgreSQL 16 + TimescaleDB |
| **Cache / PubSub** | Redis 7 |
| **Task Queue** | Celery 5 (Worker & Beat) |
| **Web Frontend** | Next.js 15 + React + TypeScript + Tailwind CSS |
| **Mobile App** | React Native + Expo |
| **AI / NLP** | LangGraph + LangChain + OpenAI/Anthropic |
| **Quant / ML** | XGBoost + Pandas + scikit-learn |
| **Infrastructure** | Docker + AWS (ECS Fargate, RDS, S3) + Terraform |

## 🚀 Quick Start

### 1. Start Infrastructure (Database & Redis)
```bash
cd infra/docker
docker compose up -d
```

### 2. Set up environment
```bash
cp services/api/.env.example services/api/.env
# Edit .env and add your broker API keys (Angel One) and OpenAI/Anthropic Keys
```

### 3. Run DB migrations
```bash
cd data
alembic upgrade head
```

### 4. Start API Server
```bash
cd services/api
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Start Background Workers (in separate terminals)
```bash
cd services/api
celery -A core.celery_app worker --loglevel=info
celery -A core.celery_app beat --loglevel=info
```

### 6. Start Web Frontend
```bash
cd apps/web
npm install
npm run dev
```

### 7. Start Mobile App
```bash
cd apps/mobile
npm install
npx expo start
```

## 📈 Development Phases

| Phase | Status | Description |
|---|---|---|
| **V1** | ✅ Done | Data + Analytics foundation (TimescaleDB, PiT screening) |
| **V2** | ✅ Done | Multi-agent AI analysis (LangGraph evidence & critic pipeline) |
| **V3** | ✅ Done | Opportunity Engine & XGBoost Ranking |
| **V4** | ✅ Done | Platform expansion (Web & Mobile Apps, Celery, CI/CD, Terraform) |
| **V5** | ⏳ Planned | F&O (Futures & Options) expansion |

## 📚 Documentation

- [System Design Document](Indian_Equity_Intelligence_Platform_System_Design.md)
- [Status Tracking](project_status.md)
