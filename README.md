# llm-orchestration

AI Agent Builder with:
- **Backend:** Flask + Socket.IO (`backend/`)
- **Frontend:** React + Vite (`frontend/`)

## Run locally

### 1) Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs on `http://localhost:8000`.

### 2) Frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Notes
- Do not commit secrets from `backend/.env`.
- Generated files (`node_modules`, `venv`, `*.db`, uploads, logs, build artifacts) are ignored by `.gitignore`.