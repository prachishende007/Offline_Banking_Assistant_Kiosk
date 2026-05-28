import os
from io import BytesIO
import base64
import asyncio
import edge_tts

from flask import Flask, jsonify, render_template, request, send_file, session
from flask_cors import CORS
from gtts import gTTS

from embeddings.search import USER_BY_MOBILE, answer_query, detect_language, get_refiner_status

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
CORS(app, supports_credentials=True)
app.config["SECRET_KEY"] = os.getenv("BANK_ASSISTANT_SECRET", "dev-secret-change-me")


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health() -> tuple:
    return jsonify({"status": "ok"}), 200


@app.get("/api/model-status")
def model_status() -> tuple:
    return jsonify(get_refiner_status()), 200


@app.post("/api/login")
def login() -> tuple:
    payload = request.get_json(silent=True) or {}
    mobile = str(payload.get("mobile", "")).strip()

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        return jsonify({"error": "Invalid mobile number"}), 401

    session["mobile"] = mobile
    return (
        jsonify(
            {
                "ok": True,
                "user": {
                    "name": user.get("name", "User"),
                    "district": user.get("district", ""),
                    "user_type": user.get("user_type", ""),
                    "mobile": mobile,
                },
            }
        ),
        200,
    )


@app.post("/api/logout")
def logout() -> tuple:
    session.clear()
    return jsonify({"ok": True}), 200


@app.post("/api/chat")
def chat() -> tuple:
    mobile = session.get("mobile")
    if not mobile:
        return jsonify({"error": "Not logged in"}), 401

    user = USER_BY_MOBILE.get(mobile)
    if not user:
        session.clear()
        return jsonify({"error": "Session expired"}), 401

    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    requested_lang = str(payload.get("language", "auto")).strip().lower()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    resolved_lang = detect_language(message) if requested_lang == "auto" else requested_lang
    if resolved_lang not in {"en", "hi", "mr"}:
        resolved_lang = "en"

    answer, related_questions = answer_query(user, message, lang_hint=resolved_lang)

    return jsonify({
        "answer": answer,
        "language": resolved_lang,
        "related_questions": related_questions
    }), 200


@app.post("/api/tts")
def tts() -> tuple:
    mobile = session.get("mobile")
    if not mobile or mobile not in USER_BY_MOBILE:
        return jsonify({"error": "Not logged in"}), 401

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    lang = str(payload.get("language", "en")).strip().lower()
    voice_mode = str(payload.get("voice_mode", "stable")).strip().lower()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    if lang not in {"en", "hi", "mr"}:
        lang = "en"

    # Map languages to edge-tts voice names
    voice_map = {
        "en": "en-IN-NeerjaNeural",  # Default English voice
        "hi": "hi-IN-SwaraNeural",   # Default Hindi voice
        "mr": "mr-IN-AarohiNeural"   # Default Marathi voice
    }
    
    # Cycle through different voices for variety in dynamic mode
    if voice_mode == "dynamic":
        turn = int(session.get("tts_turn", 0))
        session["tts_turn"] = turn + 1
        
        voices_by_lang = {
            "en": ["en-IN-NeerjaNeural", "en-IN-PrabhatNeural"],
            "hi": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"],
            "mr": ["mr-IN-AarohiNeural", "mr-IN-ManoharNeural"]
        }
        available_voices = voices_by_lang.get(lang, voices_by_lang["en"])
        voice_name = available_voices[turn % len(available_voices)]
    else:
        voice_name = voice_map.get(lang, voice_map["en"])

    try:
        # Use edge-tts for offline TTS
        async def generate_tts():
            communicate = edge_tts.Communicate(text, voice_name)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and "data" in chunk:
                    audio_data += chunk["data"]
            return audio_data

        audio_bytes = asyncio.run(generate_tts())
        audio = BytesIO(audio_bytes)
        audio.seek(0)
        
    except Exception as e:
        # Fallback to gTTS if edge-tts fails
        try:
            gtts_lang = "mr" if lang == "mr" else ("hi" if lang == "hi" else "en")
            tts_engine = gTTS(text=text, lang=gtts_lang, tld="co.in", slow=False)
            audio = BytesIO()
            tts_engine.write_to_fp(audio)
            audio.seek(0)
        except Exception:
            return jsonify({"error": f"TTS generation failed: {str(e)}"}), 500

    return send_file(audio, mimetype="audio/mpeg", as_attachment=False, download_name="reply.mp3"), 200


@app.post("/api/tts-stop")
def tts_stop() -> tuple:
    """Clear TTS state for immediate playback stop on frontend."""
    session["tts_stop_requested"] = True
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
