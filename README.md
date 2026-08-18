# llm-orchestration

Конструктор AI-агентов с визуальным редактором графа: вы собираете workflow из нод (триггеры, LLM, инструменты, действия, RAG, HITL), деплоите его и запускаете через API/UI с логами в реальном времени.

Технологии:
- **Backend:** Flask + Socket.IO (`backend/`)
- **Frontend:** React + Vite (`frontend/`)

## Основной функционал

- Визуальный canvas для сборки графа агента (drag-and-drop ноды + связи).
- CRUD графов: создание, сохранение, загрузка, обновление, удаление.
- Запуск графа по API и из интерфейса.
- Live-логи выполнения через WebSocket (Socket.IO).
- Поддержка RAG: загрузка файлов и использование их в цепочке.
- Human-in-the-loop (HITL): узлы с участием человека в процессе выполнения.
- Telegram/Widget интеграции (роутеры и статический виджет в backend).
- Работа в mock-режиме без ключей и в real-режиме с `OPENAI_API_KEY` / `NVIDIA_API_KEY`.

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

## Что можно улучшить

- Добавить Docker Compose для запуска backend/frontend одной командой.
- Вынести URL API/Socket в `.env` фронтенда (`VITE_API_URL`, `VITE_SOCKET_URL`) вместо хардкода `localhost:8000`.
- Добавить полноценные e2e-тесты (например, Playwright) для ключевых пользовательских сценариев.
- Усилить валидацию графов и обработку ошибок API (единый формат ошибок, кодов и сообщений).
- Настроить CI (lint + tests + build) и pre-commit hooks для стабильного качества.
- Добавить базовую авторизацию и разграничение доступа к графам/запускам.
- Улучшить README скриншотами/диаграммой архитектуры и примерами использования.

## Notes
- Do not commit secrets from `backend/.env`.
- Generated files (`node_modules`, `venv`, `*.db`, uploads, logs, build artifacts) are ignored by `.gitignore`.