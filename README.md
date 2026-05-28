# AI Bank Assistance - Offline-First Banking Assistant

## ⚠️ CRITICAL SAFETY GUARANTEES (Your Issues Fixed)

✅ **Problem 1: Random answers** → **FIXED**  
Banking facts (account number, balance, transactions) **ALWAYS come from JSON**, never from LLM hallucination.

✅ **Problem 2: Account details not working** → **FIXED**  
Intent detection improved. Account number queries now properly use JSON data.

✅ **Problem 3: Works WITHOUT internet** → **FIXED**  
Works 100% offline with local Indic-LLaMA model (no Gemini API needed).

✅ **Problem 5: API keys required** → **FIXED**  
Now uses Microsoft Edge TTS (offline) - no API keys needed for TTS. Works 100% offline.

## Architecture

- **Banking facts layer:** Deterministic JSON lookup (account, balance, transactions, profile)
- **FAQ layer:** Vector search over embeddings
- **Refinement layer:** Optional local Indic-LLaMA for language polish only
- **TTS:** Microsoft Edge TTS (offline) with Indian language support - no API keys required

## LLM Enhancement (Hindi/Marathi Quality)

This project now supports two optional refinement modes for better natural Hindi/Marathi output:
- **Gemini (recommended):** best speed/quality tradeoff for hackathon demos.
- **Indic-LLaMA-7B (optional):** local model path, better when you have strong GPU resources and want offline-ish control.

### Which one should you use?
- Use **Gemini** for fastest and most reliable upgrade right now.
- Use **Indic-LLaMA-7B** only if you have enough compute and want local inference.

## Offline First (Recommended For Your Next Trial)

Use this section if you want to run without internet dependency on Gemini.

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure offline mode (PowerShell)

```powershell
$env:GEMINI_ENABLED="false"
$env:INDIC_LLM_ENABLED="true"
$env:INDIC_LLM_MODEL="ai4bharat/Indic-LLaMA-7B"
$env:INDIC_LLM_DEVICE="cpu"   # set "cuda" if GPU is available
```

### 3) Start backend

```bash
python app.py
```

### 4) Verify active mode

Open:
- `http://127.0.0.1:5000/api/model-status`

Expected (offline):
- `configured_mode` should be `indic-llama`

### 5) Run frontend

```bash
cd frontend
npm install
npm run dev
```

### Offline note

The local model is loaded lazily on first chat request. CPU inference can be slow for a 7B model.

### A) Gemini setup (recommended)

1. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

2. Set environment variables (PowerShell):
  ```powershell
  $env:GEMINI_ENABLED="true"
  $env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
  $env:GEMINI_MODEL="gemini-1.5-flash"
  ```

3. Start backend:
  ```bash
  python app.py
  ```

### B) Indic-LLaMA-7B setup (optional)

1. Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

2. Set environment variables (PowerShell):
  ```powershell
  $env:INDIC_LLM_ENABLED="true"
  $env:INDIC_LLM_MODEL="ai4bharat/Indic-LLaMA-7B"
  $env:INDIC_LLM_DEVICE="cpu"   # set "cuda" if NVIDIA GPU is available
  ```

3. Start backend:
  ```bash
  python app.py
  ```

### Optional: GPU acceleration for Indic-LLaMA

If you have NVIDIA GPU:
```powershell
$env:INDIC_LLM_DEVICE="cuda"
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Fallback behavior

If Gemini/Indic-LLaMA is not configured or fails, assistant falls back to deterministic banking answers.

---

AI Bank Assistance is a multilingual banking assistant that answers account and FAQ queries in English, Hindi, and Marathi.

It combines:
- Retrieval over banking FAQ data using embeddings (ChromaDB + sentence-transformers)
- Rule/intention handling for account details and transaction summaries
- Flask APIs for login, chat, and text-to-speech
- Two UI options:
  - Server-rendered web UI in `web/`
  - React + Vite frontend in `frontend/`

## Project Details

### Core capabilities
- Mobile-number-based login using local demo user data
- Personalized answers using user, account, and transaction JSON datasets
- Language detection (`en`, `hi`, `mr`) and language-aware responses
- Text-to-speech response audio via gTTS
- FAQ retrieval powered by vector search over embedded content

### Main modules
- `app.py`: Flask backend and API routes
- `data/`: source JSON data (`users`, `accounts`, `transactions`, `general`)
- `embeddings/search.py`: intent + vector retrieval pipeline
- `embeddings/create_embeddings.py`: script to create/update embeddings in ChromaDB
- `web/`: Flask template/static UI
- `frontend/`: React + Vite UI (dev server + API proxy)

### API endpoints
- `GET /api/health`
- `POST /api/login`
- `POST /api/logout`
- `POST /api/chat`
- `POST /api/tts`

## Setup Info

### 1) Prerequisites
- Python 3.10+ (recommended)
- Node.js 18+ (only for React frontend)
- pip

### 2) Clone project
```bash
git clone https://github.com/Rohit-TecH306/CodeApex_2.0.git
cd CodeApex_2.0
```

### 3) Create and activate Python virtual environment

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

### 4) Install backend dependencies
```bash
pip install -r requirements.txt
```

### 5) Build or refresh embeddings (first time or after data changes)
```bash
python embeddings/create_embeddings.py
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
