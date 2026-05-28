# AI Bank Assistance

## Project Overview
AI Bank Assistance is an offline-first multilingual banking assistant built for English, Hindi, and Marathi users. It combines deterministic banking data with FAQ retrieval, optional language refinement, and voice synthesis to deliver a conversational banking experience.

The project includes:
- A Flask backend serving banking APIs, chat, and TTS
- Demo account, transaction, and FAQ datasets in `data/`
- Vector search and embedding support in `embeddings/`
- A Flask web UI under `web/`
- An optional React + Vite frontend in `frontend/`

## Key Features
- Multilingual chat support: English, Hindi, Marathi
- Deterministic account and transaction responses from JSON data
- FAQ retrieval using vector embeddings
- Configurable LLM refinement for reply polishing
- Voice output using `edge-tts` with fallback to `gTTS`
- Both Flask-rendered UI and React frontend options

## Architecture
- `app.py`: main Flask app, REST APIs, login/session handling, chat, and TTS endpoints
- `data/`: demo JSON files for users, accounts, transactions, and general FAQs
- `embeddings/`: search and embedding management for FAQ retrieval
- `web/`: templates and static assets for the Flask UI
- `frontend/`: React/Vite application for a richer client interface

## Prerequisites
- Python 3.10+
- `pip`
- Node.js 18+ if using the React frontend

## Backend Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the backend:
   ```bash
   python app.py
   ```
3. Open the Flask UI:
   - `http://127.0.0.1:5000`

## React Frontend Setup (Optional)
1. Install Node.js and npm.
2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Run the backend from the project root:
   ```bash
   python app.py
   ```
4. Start the React frontend:
   ```bash
   cd frontend
   npm run dev
   ```
5. Open the React app:
   - `http://127.0.0.1:3000`

The React frontend proxies API calls to the backend at `http://127.0.0.1:5000`.

## Optional Refinement Modes
The assistant can use an optional language model refiner for answer polishing.

### Gemini mode
```powershell
$env:GEMINI_ENABLED="true"
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:GEMINI_MODEL="gemini-1.5-flash"
```

### Indic-LLaMA offline mode
```powershell
$env:GEMINI_ENABLED="false"
$env:INDIC_LLM_ENABLED="true"
$env:INDIC_LLM_MODEL="ai4bharat/Indic-LLaMA-7B"
$env:INDIC_LLM_DEVICE="cpu"
```

## API Endpoints
- `GET /api/health` — service health check
- `GET /api/model-status` — refiner/model configuration status
- `POST /api/login` — authenticate with mobile number
- `POST /api/logout` — clear session
- `POST /api/chat` — submit banking questions
- `POST /api/tts` — generate voice replies
- `POST /api/tts-stop` — request TTS stop

## Demo Credentials
Use any number from `data/users.json` to log in.
Example mobile number:
- `9000007124`

## Notes
- The backend runs independently of the React frontend.
- `embeddings/` contains vector search and retrieval logic used by FAQ chat.
- `web/` contains the default Flask UI served by `app.py`.
- For production, set a stronger secret key via `BANK_ASSISTANT_SECRET`.

## Folder Summary
- `app.py` — Flask application and endpoints
- `data/` — sample bank data for users, accounts, transactions, and FAQs
- `embeddings/` — embedding creation, search, and query handling
- `web/` — Flask templates and static frontend assets
- `frontend/` — React + Vite frontend app

## Running the Project
Backend only:
```bash
pip install -r requirements.txt
python app.py
```

React frontend (optional):
```bash
cd frontend
npm install
npm run dev
```

Open the frontend UI:
- Flask UI: `http://127.0.0.1:5000`
- React UI: `http://127.0.0.1:3000`


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
