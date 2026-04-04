# BK-SAMs AI Agent 🤖

**BK-SAMs-Agent** is the core AI Service for the Social Activity Management System. It is an AI Agent built with **FastAPI**, **Pydantic AI**, **PostgreSQL**, **LogFire** specifically optimized for orchestrating social activities and assisting users through natural language.

---

## 🚀 Technical Stack
* **Framework:** FastAPI (Python 3.14)
* **AI Orchestration:** Pydantic AI
* **Database:** PostgreSQL (via `asyncpg` for high-concurrency)
* **LLM Provider:** OpenAI model provided by Groq (primary model is openai/gpt-oss-120b)
* **Deployment:** Fly.io (Dockerized)
* **Observability:** Pydantic Logfire

---

## 🛠️ Installation & Local Development

### 1. Prerequisites
* Install [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
* Python 3.12+

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/your-username/BK-SAMs-Agent.git
cd BK-SAMs-Agent

# Install dependencies using uv
uv sync
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/bksams
GROQ_API_KEY=your_api_key_here
LOGFIRE_TOKEN=your_token_here
```

### 4. Running the App
```bash
uv run uvicorn main:app 
```

---

## 🚢 Deployment (Fly.io)

However you can try it at this endpoint:
https://bk-sams-fe.vercel.app/chat-ai

And the API docs can be accessed via: https://bk-sams-agent-bqdopa.fly.dev/docs

---

## 📡 API Endpoints
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System health check (used by Fly.io Proxy) |
| `/chat/ws` | `WS` | WebSocket endpoint for real-time AI Chat |
| `/docs` | `GET` | Interactive Swagger API documentation |

---

## 🛡️ License
This project is part of the **Capstone Project (HK252)** at **Ho Chi Minh City University of Technology (HCMUT)**. All rights reserved.
