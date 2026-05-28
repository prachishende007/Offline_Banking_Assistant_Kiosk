# Offline Demo Setup (No Internet Required)

This guide gets your project running 100% offline with Indic-LLaMA-7B for Hindi/Marathi responses and Microsoft Edge TTS for voice output.

## Features Working Offline

✅ **Banking queries** (JSON-based, no LLM needed)  
✅ **FAQ answers** (vector search on local embeddings)  
✅ **Hindi/Marathi responses** (local Indic-LLaMA model)  
✅ **Text-to-speech** (Microsoft Edge TTS, no API keys)  
✅ **Voice recognition** (local speech-to-text)  

## One-Command Setup

Open **2 PowerShell terminals** in project root:

### Terminal 1: Backend

```powershell
# Activate environment
& ".\.venv\Scripts\Activate.ps1"

# Configure offline (no internet needed)
$env:GEMINI_ENABLED="false"
$env:INDIC_LLM_ENABLED="true"
$env:INDIC_LLM_MODEL="ai4bharat/Indic-LLaMA-7B"
$env:INDIC_LLM_DEVICE="cpu"

# (Optional: Use GPU for faster inference)
# $env:INDIC_LLM_DEVICE="cuda"

# Create embeddings (one-time)
python embeddings/create_embeddings.py

# Start backend
python app.py
```

Backend runs at: `http://127.0.0.1:5000`

### Terminal 2: Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://127.0.0.1:3000`

## Verify Offline Mode

After backend starts, open:
```
http://127.0.0.1:5000/api/model-status
```

Should show:
```json
{
  "configured_mode": "indic-llama",
  "last_used_mode": "deterministic",
  "gemini_enabled": "false",
  "indic_enabled": "true"
}
```

## Demo Login

Use any mobile from `data/users.json`:
- `9000010001` (Archana Wagh, Senior, Amravati)
- `9000007124` (Sneha Godbole, Student, Nagpur)
- Or any other mobile in the file

## Demo Queries (Hindi/Marathi)

**Account Balance:**
- "मेरे खाते में कितना पैसा है?"
- "माझ्या खातात किती रुपये आहेत?"

**Account Number:**
- "मेरा अकाउंट नंबर क्या है?"
- "माझा खाते क्रमांक बताओ"

**Transactions:**
- "मेरे आखिरी लेनदेन दिखाओ"
- "माझे पिछले व्यवहार दाखवा"

**Profile:**
- "मेरा नाम और जिला बताओ"
- "माझे नाव आणि जिल्हा सांगा"

## Features in This Setup

✅ Completely offline (no internet after model downloads)  
✅ Hindi/Marathi responses polished by local Indic-LLaMA  
✅ Banking facts always from JSON (no hallucination)  
✅ Stop button stops long TTS responses immediately  
✅ Works on CPU (slow) or GPU (fast)  

## Performance Notes

**CPU Mode:**
- First chat takes 30-60 seconds (model loads)
- Subsequent chats take 10-30 seconds
- Good for demos, not real-time

**GPU Mode (CUDA):**
- First chat takes 15-30 seconds
- Subsequent chats take 2-5 seconds
- Recommended for smooth demo

## Troubleshooting

**Model download stalls?**
- First run: Indic-LLaMA (~7GB) downloads to ~/.cache/huggingface
- Ensure 15GB free disk space

**Can't find mobile?**
- Check `data/users.json` for valid numbers

**TTS says "online" error?**
- gTTS may need retry; click Stop and try again

**Backend won't start?**
- Verify embeddings created: `python embeddings/create_embeddings.py`
- Check all env vars set

## Next Steps (After Demo)

After successful offline demo, you can:
1. **Add Gemini** for faster/better responses (online)
2. **Reduce model size** to Indic-LLaMA-3B
3. **Deploy on server** with persistent model cache
