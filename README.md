# TechServe CRM — AI-Enhanced CRM & Ticket Management System

**Course:** Artificial Intelligence (CS-4XX) — Major Project  
**Team:** [Member 1 Name] · [Member 2 Name] · [Member 3 Name]  
**Student IDs:** [ID1] · [ID2] · [ID3]

---

## Overview

Full-stack mini-Zendesk CRM with JWT authentication, customer and ticket management, Groq-powered AI categorization and sentiment analysis, and Gmail/Telegram notifications.

## Tech Stack

- **Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy
- **Frontend:** React + Vite + Tailwind CSS
- **AI:** Groq API (`llama3-8b-8192`) — auto-categorization + sentiment analysis
- **Messaging:** Gmail SMTP + Telegram Bot

## Features

- [x] User authentication (JWT, Agent + Manager roles)
- [x] Customer CRUD with search/filter
- [x] Ticket management (create, assign, update, resolve)
- [x] AI auto-categorization and sentiment analysis (Groq)
- [x] Auto-escalation on frustrated sentiment
- [x] AI conversation summary on resolution
- [x] Gmail SMTP email notifications
- [x] Telegram bot notifications
- [x] Activity log / comment threads
- [x] Dashboard with charts

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

## Database Setup

```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE crm_db;"
```

Tables are created automatically on first backend startup via SQLAlchemy `create_all`.

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn app.main:app --reload
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql://postgres:password@localhost:5432/crm_db` |
| `SECRET_KEY` | Yes | Random 64-char hex string for JWT signing |
| `ALGORITHM` | Yes | JWT algorithm — use `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Token lifetime in minutes — use `60` |
| `GROQ_API_KEY` | No | From [console.groq.com](https://console.groq.com) — starts with `gsk_`. AI features degrade gracefully without it |
| `GMAIL_USER` | No | Your Gmail address. Email notifications disabled if not set |
| `GMAIL_APP_PASSWORD` | No | Gmail App Password (16 chars, not regular password) |
| `TELEGRAM_BOT_TOKEN` | No | From @BotFather on Telegram. Telegram notifications disabled if not set |
| `TELEGRAM_CHAT_ID` | No | Group/channel chat ID (negative integer for groups) |

### Gmail App Password

1. Enable 2FA on your Google account
2. Go to [myaccount.google.com](https://myaccount.google.com) → Security → App Passwords
3. Create a password for "Mail"

### Telegram Bot

1. Message @BotFather → `/newbot`
2. Copy the bot token
3. Add bot to a group/channel as admin
4. Get chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Manager | admin@crm.com | admin123 |
| Agent | sarah@crm.com | agent123 |

## Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

## Docker (optional)

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

## API Documentation

With backend running, interactive Swagger docs available at:  
- http://localhost:8000/docs — Swagger UI  
- http://localhost:8000/redoc — ReDoc

## Screenshots

Key screens: Login → Dashboard → Customers → Create Ticket → Ticket Detail (with AI Analysis card) → Users Page

See `demo.mp4` in the project root for a full walkthrough of all features.

## Test Results

```
backend/tests/test_integration.py      29 tests
backend/tests/test_messaging_service.py  17 tests
backend/tests/test_dashboard.py        12 tests
Total: 58 tests
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── models/      # SQLAlchemy models
│   │   ├── routers/     # API endpoints
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # AI + messaging
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/
│       └── components/
└── docker-compose.yml
```
