# SensorHub Analytics

SensorHub Analytics is a dashboard for managing and analyzing sensor data files from wearable devices (Watch and Ring). It provides a unified interface for uploading raw data, monitoring processing status, and inspecting signal quality.

## Features

- **Dashboard**: Real-time overview of file statistics, today's uploads, and storage usage.
- **Quick Upload**: Dedicated upload areas for Watch (`.rawdata`) and Ring (`.rawdata`) files with drag-and-drop support.
- **Data Management**: Searchable and filterable table of all sensor files.
  - Filter by Device Type (Watch/Ring) and Status (Idle/Ready/Processing/Failed).
  - Inline editing for notes and test types.
  - Packet inspection popover for quick quality checks.
- **Visual Feedback**: Status badges and signal presence indicators (ACC, PPG, GYRO, etc.).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Vue 3 + Vite + TypeScript |
| State Management | Pinia |
| Styling | Tailwind CSS |
| Icons | Lucide Vue Next |
| Backend | FastAPI + Python |
| Database | SQLite |
| HTTP Client | Axios |

## Project Structure

```
SensorHub/
├── frontend/               # Vue 3 frontend application
│   ├── components/         # Vue components
│   ├── stores/             # Pinia stores
│   ├── services/           # API service layer
│   └── types.ts            # TypeScript types
├── backend/                # FastAPI backend application
│   ├── main.py             # API endpoints
│   └── database.py         # SQLite database operations
└── README.md
```

---

## Run Locally

### Prerequisites

- **Node.js** (v18+)
- **Python** (v3.10+)
- **uv** (Python package manager) - Install via `pip install uv` or `pipx install uv`

---

### Backend (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create virtual environment and install dependencies:
   ```bash
   uv sync
   ```

3. Start the backend server:
   ```bash
   uv run uvicorn main:app --reload
   ```

4. The API will be available at:
   - **API**: http://localhost:8000
   - **Swagger Docs**: http://localhost:8000/docs

---

### Frontend (Vue 3)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. The app will be available at: http://localhost:5173

---

## Development Mode Configuration

The frontend can work in two modes:

| Mode | Description | Configuration |
|------|-------------|---------------|
| **Mock Mode** | Uses local mock data | Set `USE_MOCK = true` in `frontend/services/fileService.ts` |
| **API Mode** | Connects to backend | Set `USE_MOCK = false` in `frontend/services/fileService.ts` |

> **Note**: In Mock Mode, changes are not persisted after page refresh. Use API Mode for full persistence.


---

## Database Environment

You can switch between **Test** (mock data) and **Production** modes via `backend/config.json`.

### configuration (`backend/config.json`)

```json
"database": {
    "directory": "database",
    "use_test_db": true,  // true = test.db, false = sensorhub.db
    "echo": false
}
```

### Database Utilities

1. **Initialize Test Database**
   Creates `database/test.db` and populates it with mock data (if it doesn't exist).
   ```bash
   uv run python backend/test_db.py
   ```

2. **Check Database Connection**
   Verifies which database the app is currently using and prints stats.
   ```bash
   uv run python backend/check_db.py
   ```

---


## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/files` | Get all sensor files |
| GET | `/api/files/{id}` | Get a single file |
| PATCH | `/api/files/{id}` | Update file metadata |
| DELETE | `/api/files/{id}` | Delete a file |
| POST | `/api/files/batch-delete` | Delete multiple files |
