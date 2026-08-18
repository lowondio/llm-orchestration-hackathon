# llm-orchestration

`llm-orchestration` is a visual AI workflow builder for creating and running agent-based automations.  
Instead of writing orchestration logic from scratch, you compose a graph of nodes (trigger, LLM, tools, actions, RAG, human-in-the-loop), deploy it, and execute it through UI or API.

The project is designed for fast prototyping of multi-step AI flows with real-time observability: every run can stream execution logs live over WebSocket, making debugging and iteration much easier.

<img width="2559" height="1271" alt="Screenshot 2026-08-19 012039" src="https://github.com/user-attachments/assets/de78b4f1-51d1-4949-b718-726049c6283d" />

## Tech Stack

- **Backend:** Flask + Flask-SocketIO (`backend/`)
- **Frontend:** React + Vite (`frontend/`)
- **Data/State:** local DB files for graph/runtime storage

## Core Functionality

- Visual graph editor (drag-and-drop nodes and edges)
- Graph lifecycle management (create, save, load, update, delete)
- Graph deployment and execution via REST API
- Real-time execution logs via Socket.IO
- RAG support (file upload + retrieval in workflow)
- Human-in-the-loop (HITL) interaction steps
- Integrations layer (Telegram routes and embeddable widget assets)
- Dual operation modes:
  - **Mock mode** (no API keys, test responses)
  - **Real mode** (`OPENAI_API_KEY` and/or `NVIDIA_API_KEY`)

## How It Works

1. Build a workflow graph in the frontend canvas.
2. Persist/deploy the graph through backend API endpoints.
3. Execute a graph run with input payload.
4. Track logs and status updates live in the frontend console.
5. Iterate on node configuration and graph topology.

## Local Development

### 1) Start Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend URL: `http://localhost:8000`

### 2) Start Frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

## Environment Variables

Backend reads variables from `backend/.env`.

Common keys:
- `OPENAI_API_KEY` (optional, enables OpenAI runtime)
- `NVIDIA_API_KEY` (optional, enables NVIDIA runtime)
- `WEBHOOK_BASE_URL` (optional, defaults to local backend URL in code)

If no valid provider key is set, the app falls back to mock behavior.

## Suggested Improvements

- Add **Docker Compose** for one-command startup
- Move API/Socket endpoints to frontend env variables (`VITE_API_URL`, `VITE_SOCKET_URL`)
- Add end-to-end tests (Playwright/Cypress) for critical user flows
- Standardize API error schema and validation messages
- Add CI pipeline (lint, tests, build) + pre-commit hooks
- Add authentication and access control for graphs/runs

## Repository Notes

- Never commit secrets from `backend/.env`
- Generated artifacts (`node_modules`, `venv`, `*.db`, uploads, logs, build outputs) are intentionally ignored by `.gitignore`
