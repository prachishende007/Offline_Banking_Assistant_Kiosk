# AI Bank Assistance - Offline-First Banking Assistant

## Overview
AI Bank Assistance is a multilingual banking assistant that answers account and FAQ queries in English, Hindi, and Marathi.

It combines:
- Deterministic banking data from local JSON files
- Vector search over FAQ embeddings
- Optional LLM polish via Gemini or Indic-LLaMA
- Flask backend APIs and two UI options

## What changed
- Banking facts are always loaded from local JSON data
- Account and transaction queries are deterministic
- Offline TTS support via `edge-tts`
- Frontend can run in the browser using the Flask UI or React + Vite

## Prerequisites
- Python 3.10+
- pip
- Node.js 18+ only if you want to run the React frontend in `frontend/`

> If `node --version` or `npm --version` fails, install Node.js from https://nodejs.org and restart your terminal.

## Quick Start: Backend only
This is the easiest way to run the app if you do not have Node.js installed.

1) Install Python dependencies:
```bash
pip install -r requirements.txt
```

2) Run the backend:
```bash
python app.py
```

3) Open the app in your browser:
- `http://127.0.0.1:5000`

This uses the Flask-served UI in `web/templates` and `web/static`.

## Full Setup: React frontend
If you want the React/Vite UI, you must install Node.js/npm first.

1) Install Node.js
- Download and install the LTS version from: https://nodejs.org
- Or use Windows package manager:
  ```powershell
  winget install OpenJS.NodeJS
  ```

2) Verify Node is installed:
```bash
node --version
npm --version
```

3) Install frontend dependencies:
```bash
cd frontend
npm install
```

4) Start backend in the project root:
```bash
python app.py
```

5) Start the React frontend:
```bash
cd frontend
npm run dev
```

6) Open the frontend in your browser:
- `http://127.0.0.1:3000`

The React app proxies API calls to the backend at `http://127.0.0.1:5000`.

## Environment modes
The app supports two optional refinement modes:

### Gemini mode (recommended)
```powershell
$env:GEMINI_ENABLED="true"
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:GEMINI_MODEL="gemini-1.5-flash"
```

### Indic-LLaMA mode (offline)
```powershell
$env:GEMINI_ENABLED="false"
$env:INDIC_LLM_ENABLED="true"
$env:INDIC_LLM_MODEL="ai4bharat/Indic-LLaMA-7B"
$env:INDIC_LLM_DEVICE="cpu"
```

> CPU inference for a 7B model may be slow. Use `cuda` only if you have a compatible NVIDIA GPU.

## Run backend with chosen mode
```bash
python app.py
```

## Verify backend status
Open:
- `http://127.0.0.1:5000/api/health`
- `http://127.0.0.1:5000/api/model-status`

## Folder structure
- `app.py`: Flask backend and API routes
- `data/`: demo JSON data for users, accounts, transactions, and general FAQ
- `embeddings/`: embedding creation and search logic
- `web/`: Flask-rendered UI templates and static files
- `frontend/`: React + Vite frontend UI

## Notes
- `python -m venv .venv` only manages Python dependencies. It does not install Node or npm.
- If `npm` is not recognized, install Node.js and restart your terminal.
- The backend can run independently of the React frontend.

## Useful commands
Backend only:
```bash
pip install -r requirements.txt
python app.py
```

Frontend setup (after Node install):
```bash
cd frontend
npm install
npm run dev
```

This creates/updates vector data under `embeddings/db/`.

### 6) Run backend (Flask)
```bash
python app.py
```

Backend runs at: `http://127.0.0.1:5000`

### 7) Run UI

Option A: Flask web UI
- Open: `http://127.0.0.1:5000`

Option B: React frontend
```bash
cd frontend
npm install
npm run dev
```
- Open: `http://127.0.0.1:3000`
- Vite proxy forwards `/api` calls to `http://127.0.0.1:5000`

## Demo Login

Use any mobile number from `data/users.json`.
Example:
- `9000007124`

## Notes
- Set a stronger secret key in production:
  - Environment variable: `BANK_ASSISTANT_SECRET`
- Keep `embeddings/db/` out of git if you want smaller repository size for deployment workflows.

## Troubleshooting

### Random/wrong answers
- ✅ FIXED: Banking facts now come ONLY from JSON, LLM cannot hallucinate
- Verify: Check `/api/model-status` shows `"configured_mode": "indic-llama"` (offline mode)

### Account details not showing
- ✅ FIXED: Intent detection updated for "मेरा अकाउंट नंबर क्या है" style queries
- Demo numbers: Any from `data/users.json` (e.g., `9000010001`)

### TTS too long (won't stop)
- ✅ FIXED: Click **STOP** button to interrupt immediately

### Works offline?
- ✅ YES: Fully offline with Indic-LLaMA on CPU/GPU
- Verify: No internet needed after first model download

### General troubleshooting
- Login fails: Mobile must exist in `data/users.json`
- Chat fails: Ensure embeddings created: `python embeddings/create_embeddings.py`
- TTS fails (offline): Rare; check gTTS alternatives
- React can't reach backend: Flask must run on `127.0.0.1:5000`

## Recent Fixes (for Hackathon)

1. **No more hallucination:** Banking facts from JSON only
2. **Better intent detection:** Account number queries now work in Hindi/Marathi
3. **Full offline:** Works with local Indic-LLaMA, zero internet dependency
4. **Stop button:** TTS can be interrupted immediately
5. **Refinement safe:** LLM only polishes language, never changes facts

## API Endpoints

- `GET /api/health` — Health check
- `POST /api/login` — Mobile login
- `POST /api/logout` — Logout
- `POST /api/chat` — Chat query (returns banking answer)
- `POST /api/tts` — Text-to-speech
- `POST /api/tts-stop` — Stop current TTS
- `GET /api/model-status` — Show active LLM backend (gemini/indic-llama/deterministic)

## Future Improvements
- Real authentication and OTP flow
- Role-based banking workflows
- Better observability and API logging
- Dockerized deployment
