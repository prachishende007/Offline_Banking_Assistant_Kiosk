const API_BASE = "/api";

export async function loginByMobile(mobile) {
  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ mobile }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Login failed");
  return data;
}

export async function logoutUser() {
  const res = await fetch(`${API_BASE}/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Logout failed");
}

export async function processText(query, language = "auto") {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message: query, language }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Chat failed");

  return {
    response_text: data.answer,
    language: data.language,
    related_questions: data.related_questions || [],
  };
}

export async function getTtsAudio(text, language = "en", voiceMode = "stable") {
  const res = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ text, language, voice_mode: voiceMode }),
  });
  if (!res.ok) throw new Error("TTS failed");
  return res.blob();
}

export async function stopTts() {
  const res = await fetch(`${API_BASE}/tts-stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Stop TTS failed");
}
