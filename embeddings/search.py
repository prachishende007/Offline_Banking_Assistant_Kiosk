import json
import io
import os
import unicodedata
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, List, Optional, Tuple

from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

# 1) Load model and vector DB
# Resolve paths relative to this file so imports work from any working directory.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DB_DIR = BASE_DIR / "db"

# Silence non-critical model load report text during startup.
with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    model = SentenceTransformer("all-MiniLM-L6-v2")
client = PersistentClient(path=str(DB_DIR))
collection = client.get_collection(name="bank_data")

# 2) Load source JSON data
with open(DATA_DIR / "users.json", encoding="utf-8") as f:
    users = json.load(f)

with open(DATA_DIR / "accounts.json", encoding="utf-8") as f:
    accounts = json.load(f)

with open(DATA_DIR / "transactions.json", encoding="utf-8") as f:
    transactions = json.load(f)

with open(DATA_DIR / "general.json", encoding="utf-8") as f:
    faqs = json.load(f)

USER_BY_MOBILE: Dict[str, dict] = {u["mobile"]: u for u in users}
ACCOUNT_BY_USER: Dict[str, dict] = {a["user_id"]: a for a in accounts}
TXNS_BY_USER: Dict[str, List[dict]] = {}
for t in transactions:
    TXNS_BY_USER.setdefault(t["user_id"], []).append(t)

FAQ_BY_INTENT_LANG: Dict[Tuple[str, str], str] = {}
for f in faqs:
    FAQ_BY_INTENT_LANG[(f["intent"], f["language"])] = f["answer"]

# FAQ confidence guardrails.
MAX_FAQ_DISTANCE = 0.85  # Lower threshold for more matches
MIN_FAQ_DISTANCE_GAP = 0.05  # Smaller gap to be more lenient

# Optional Gemini refinement (recommended for faster multilingual quality).
GEMINI_ENABLED = os.getenv("GEMINI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Optional local Indic LLM refinement (disabled by default).
INDIC_LLM_ENABLED = os.getenv("INDIC_LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
INDIC_LLM_MODEL_NAME = os.getenv("INDIC_LLM_MODEL", "ai4bharat/Indic-LLaMA-7B")
INDIC_LLM_DEVICE = os.getenv("INDIC_LLM_DEVICE", "cpu")  # Use "cuda" if GPU available

# Lazy-load Indic model to avoid startup delay if not needed.
_indic_model = None
_indic_tokenizer = None
_indic_model_load_error = None
_gemini_model = None
_gemini_model_load_error = None
_last_refiner = "deterministic"


def _lazy_load_gemini_model():
    """Load Gemini client on first use with fallback."""
    global _gemini_model, _gemini_model_load_error

    if _gemini_model is not None or _gemini_model_load_error is not None:
        return _gemini_model

    if not GEMINI_ENABLED:
        _gemini_model_load_error = "Gemini disabled"
        return None
    if not GEMINI_API_KEY:
        _gemini_model_load_error = "GEMINI_API_KEY missing"
        return None

    try:
        import google.generativeai as genai  # type: ignore[import-not-found]

        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
        return _gemini_model
    except Exception as e:
        _gemini_model_load_error = str(e)
        print(f"Warning: Could not load Gemini model: {e}. Using fallback responses.")
        return None


def _pick_torch_device() -> str:
    try:
        import torch

        if INDIC_LLM_DEVICE == "cuda" and torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _lazy_load_indic_model():
    """Load Indic-LLaMA model on first use with fallback."""
    global _indic_model, _indic_tokenizer, _indic_model_load_error
    
    if _indic_model is not None or _indic_model_load_error is not None:
        return _indic_model, _indic_tokenizer
    
    try:
        if not INDIC_LLM_ENABLED:
            _indic_model_load_error = "Indic LLM disabled"
            return None, None
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except ImportError:
            _indic_model_load_error = "transformers not installed"
            return None, None
        
        device = _pick_torch_device()
        
        print(f"Loading Indic-LLaMA model ({INDIC_LLM_MODEL_NAME}) on {device}...")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            _indic_tokenizer = AutoTokenizer.from_pretrained(INDIC_LLM_MODEL_NAME)
            _indic_model = AutoModelForCausalLM.from_pretrained(INDIC_LLM_MODEL_NAME)

        # Move model to selected device after load for broad compatibility.
        try:
            _indic_model = _indic_model.to(device)
        except Exception:
            # Keep CPU if transfer is not possible in this environment.
            device = "cpu"
            _indic_model = _indic_model.to(device)

        _indic_model = _indic_model.eval()
        print(f"Indic-LLaMA loaded successfully on {device}")
        return _indic_model, _indic_tokenizer
    except Exception as e:
        _indic_model_load_error = str(e)
        print(f"Warning: Could not load Indic-LLaMA model: {e}. Using fallback responses.")
        return None, None


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower().strip()


def get_related_questions(intent: str, lang: str) -> List[str]:
    """Generate 3 related questions based on the detected intent."""
    related_questions = {
        "account_balance": {
            "en": [
                "How can I check my account balance?",
                "What are my recent transactions?",
                "Is my account active?"
            ],
            "hi": [
                "मैं अपना खाता बैलेंस कैसे चेक कर सकता हूँ?",
                "मेरे हाल के लेनदेन क्या हैं?",
                "क्या मेरा खाता सक्रिय है?"
            ],
            "mr": [
                "मी माझा खाता बॅलन्स कसा चेक करू शकतो?",
                "माझे अलीकडील व्यवहार काय आहेत?",
                "माझे खाते सक्रिय आहे का?"
            ]
        },
        "transactions": {
            "en": [
                "What is my account balance?",
                "How many transactions can I see?",
                "Can I download my statement?"
            ],
            "hi": [
                "मेरा खाता बैलेंस क्या है?",
                "मैं कितने लेनदेन देख सकता हूँ?",
                "क्या मैं अपना स्टेटमेंट डाउनलोड कर सकता हूँ?"
            ],
            "mr": [
                "माझा खाता बॅलन्स काय आहे?",
                "मी किती व्यवहार पाहू शकतो?",
                "मी माझे स्टेटमेंट डाउनलोड करू शकतो का?"
            ]
        },
        "account_details": {
            "en": [
                "What is my account balance?",
                "Is my account active?",
                "How can I update my KYC?"
            ],
            "hi": [
                "मेरा खाता बैलेंस क्या है?",
                "क्या मेरा खाता सक्रिय है?",
                "मैं अपना KYC कैसे अपडेट कर सकता हूँ?"
            ],
            "mr": [
                "माझा खाता बॅलन्स काय आहे?",
                "माझे खाते सक्रिय आहे का?",
                "मी माझे KYC कसे अपडेट करू शकतो?"
            ]
        },
        "user_profile": {
            "en": [
                "What is my account balance?",
                "What are my account details?",
                "Is my account active?"
            ],
            "hi": [
                "मेरा खाता बैलेंस क्या है?",
                "मेरे खाते का विवरण क्या है?",
                "क्या मेरा खाता सक्रिय है?"
            ],
            "mr": [
                "माझा खाता बॅलन्स काय आहे?",
                "माझ्या खात्याचे तपशील काय आहेत?",
                "माझे खाते सक्रिय आहे का?"
            ]
        },
        "loan_query": {
            "en": [
                "What are the interest rates for loans?",
                "What documents do I need for a loan?",
                "How can I calculate EMI?"
            ],
            "hi": [
                "लोन के लिए ब्याज दर क्या हैं?",
                "लोन के लिए मुझे कौन से दस्तावेज चाहिए?",
                "मैं EMI कैसे कैलकुलेट कर सकता हूँ?"
            ],
            "mr": [
                "कर्जासाठी व्याज दर काय आहेत?",
                "कर्जासाठी मला कोणते कागदपत्रे हवी आहेत?",
                "मी EMI कसा कॅल्क्युलेट करू शकतो?"
            ]
        },
        "interest_query": {
            "en": [
                "What are the loan interest rates?",
                "How can I calculate EMI?",
                "What is the minimum loan amount?"
            ],
            "hi": [
                "लोन ब्याज दर क्या हैं?",
                "मैं EMI कैसे कैलकुलेट कर सकता हूँ?",
                "न्यूनतम लोन राशि क्या है?"
            ],
            "mr": [
                "कर्ज व्याज दर काय आहेत?",
                "मी EMI कसा कॅल्क्युलेट करू शकतो?",
                "किमान कर्ज रक्कम किती आहे?"
            ]
        },
        "kyc_update": {
            "en": [
                "What documents are needed for KYC?",
                "How long does KYC update take?",
                "Can I do KYC online?"
            ],
            "hi": [
                "KYC के लिए कौन से दस्तावेज चाहिए?",
                "KYC अपडेट में कितना समय लगता है?",
                "क्या मैं ऑनलाइन KYC कर सकता हूँ?"
            ],
            "mr": [
                "KYC साठी कोणते कागदपत्रे हवी आहेत?",
                "KYC अपडेटमध्ये किती वेळ लागतो?",
                "मी ऑनलाइन KYC करू शकतो का?"
            ]
        },
        "general": {
            "en": [
                "What is my account balance?",
                "How can I check my transactions?",
                "What are the loan interest rates?"
            ],
            "hi": [
                "मेरा खाता बैलेंस क्या है?",
                "मैं अपने लेनदेन कैसे चेक कर सकता हूँ?",
                "लोन ब्याज दर क्या हैं?"
            ],
            "mr": [
                "माझा खाता बॅलन्स काय आहे?",
                "मी माझे व्यवहार कसे चेक करू शकतो?",
                "कर्ज व्याज दर काय आहेत?"
            ]
        }
    }

    return related_questions.get(intent, related_questions["general"]).get(lang, related_questions["general"]["en"])


def print_help_examples() -> None:
    print("\nSample questions you can ask:")
    print("English:")
    print("- What is my current account balance?")
    print("- Show my last five transactions with dates.")
    print("- What is my account number and account type?")
    print("- Tell me my name, district, and user category.")
    print("- Is my account active right now?")
    print("- How do I update KYC and reset UPI PIN?")
    print("- What is the current loan interest information?")
    print("Hindi:")
    print("- मेरे खाते में अभी कितना बैलेंस है?")
    print("- मेरे पिछले पांच लेनदेन तारीख के साथ दिखाओ।")
    print("- मेरा अकाउंट नंबर और अकाउंट टाइप बताओ।")
    print("- मेरा नाम, जिला और यूज़र प्रकार बताओ।")
    print("- क्या मेरा खाता सक्रिय है?")
    print("- KYC अपडेट और UPI PIN रीसेट कैसे करें?")
    print("- लोन पर ब्याज की जानकारी क्या है?")
    print("Marathi:")
    print("- माझ्या खात्यात आत्ता किती शिल्लक आहे?")
    print("- माझे शेवटचे पाच व्यवहार तारखेसह दाखवा.")
    print("- माझा खाते क्रमांक आणि खाते प्रकार सांगा.")
    print("- माझे नाव, जिल्हा आणि वापरकर्ता प्रकार सांगा.")
    print("- माझे खाते सक्रिय आहे का?")
    print("- KYC अपडेट आणि UPI PIN रीसेट कसे करायचे?")
    print("- कर्जावरील व्याजाची माहिती काय आहे?")
    print("Type 'help' anytime to see this list again.\n")


def detect_language(text: str) -> str:
    q = normalize(text)

    marathi_markers = [
        "माझ", "शिल्लक", "काय", "कसे", "आहे", "करायचे", "साठी", "व्याज", "कर्ज",
    ]
    hindi_markers = [
        "मेरे", "मेरा", "कैसे", "कितना", "है", "करें", "चाहिए", "लोन", "ब्याज",
    ]

    has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in text)
    if has_devanagari:
        mr_hits = sum(1 for m in marathi_markers if m in q)
        hi_hits = sum(1 for m in hindi_markers if m in q)
        return "mr" if mr_hits >= hi_hits else "hi"

    # Romanized query hints for Hindi/Marathi typed in Latin script.
    roman_hi_markers = ["mera", "mere", "kaise", "kya", "len den", "khata", "byaaj"]
    roman_mr_markers = ["majha", "majhe", "kase", "kay", "khate", "shillak", "vyavhar", "karayche"]
    hi_hits = sum(1 for m in roman_hi_markers if m in q)
    mr_hits = sum(1 for m in roman_mr_markers if m in q)
    if hi_hits or mr_hits:
        return "mr" if mr_hits > hi_hits else "hi"

    return "en"


def detect_intent(query: str) -> str:
    q = normalize(query)

    if any(word in q for word in [
        "balance", "बैलेंस", "बॅलन्स", "शिल्लक", "पैसा", "पैसे", "money", "funds",
        "available amount", "available funds", "khate me kitna", "khatyat kiti", "saldo",
    ]):
        return "account_balance"

    if any(word in q for word in [
        "transaction",
        "transactions",
        "last transaction",
        "last transactions",
        "recent transaction",
        "recent transactions",
        "history",
        "statement",
        "mini statement",
        "लेनदेन",
        "व्यवहार",
        "ट्रांजैक्शन",
        "मिनी स्टेटमेंट",
        "स्टेटमेंट",
        "len den",
        "vyavhar",
        "vyavhaar",
    ]):
        return "transactions"

    if any(word in q for word in [
        "account number",
        "account no",
        "a/c number",
        "ac number",
        "खाता नंबर",
        "खाते क्रमांक",
        "खाते नंबर",
        "मेरा अकाउंट नंबर",
        "अकाउंट नंबर",
        "khata number",
        "khate kramank",
        "khate number",
        "mera account number",
        "account type",
        "खाता प्रकार",
        "खाते प्रकार",
        "खाते का प्रकार",
        "khata prakar",
        "khate prakar",
    ]):
        return "account_details"

    if any(word in q for word in [
        "account active",
        "account status",
        "is my account active",
        "is account active",
        "खाता सक्रिय",
        "खाता चालू",
        "खाते सक्रिय",
        "खाते चालू",
        "status",
    ]):
        return "account_status"

    if any(word in q for word in [
        "my name",
        "tell my name",
        "what is my name",
        "what is my district",
        "tell my district",
        "which district",
        "where do i live",
        "who am i",
        "mera naam",
        "mera name",
        "mera jila",
        "mera district",
        "mujhe mera naam batao",
        "majha nav",
        "majhe nav",
        "maje nav",
        "nav sanga",
        "majha jilha",
        "majha district",
        "my profile",
        "मेरा नाम",
        "मेरे नाम",
        "मेरा जिला",
        "मेरा प्रोफाइल",
        "मुझे मेरा नाम बताओ",
        "मेरा प्रोफाइल",
        "माझे नाव",
        "माझं नाव",
        "माझा जिल्हा",
        "माझे प्रोफाइल",
        "माझे प्रोफाइल",
        "district",
        "जिला",
        "जिल्हा",
        "user type",
        "वापरकर्ता",
    ]):
        return "user_profile"

    if any(word in q for word in ["loan", "कर्ज", "लोन", "interest", "interest rate", "ब्याज", "व्याज", "byaaj", "vyaj"]):
        return "loan_query"

    if any(word in q for word in ["kyc", "केवाईसी", "केवायसी", "केवायसी", "k y c"]):
        return "kyc_update"

    return "general"


def is_bank_related(query: str) -> bool:
    q = normalize(query)
    keywords = [
        "bank", "account", "balance", "transaction", "loan", "kyc", "atm", "card", "upi", "neft", "rtgs",
        "बैंक", "खाता", "बैलेंस", "लेनदेन", "लोन", "कार्ड", "पैसा", "केवाईसी",
        "बँक", "खाते", "शिल्लक", "व्यवहार", "कर्ज", "कार्ड", "पैसे",
        "mini statement", "statement", "status", "active", "interest", "pin",
        "khata", "khate", "len den", "vyavhar", "karj", "byaaj", "upy",
        "name", "profile", "district", "mera naam", "majha nav", "majhe nav", "nav",
    ]
    return any(k in q for k in keywords)


def handoff_message(lang: str) -> str:
    messages = {
        "en": "I am not fully confident about this answer. I will connect you to a bank officer.",
        "hi": "मुझे इस उत्तर पर पूरा भरोसा नहीं है। मैं आपको बैंक अधिकारी से जोड़ता हूँ।",
        "mr": "या उत्तराबद्दल मला पूर्ण खात्री नाही. मी तुम्हाला बँक अधिकाऱ्याशी जोडतो.",
    }
    return messages.get(lang, messages["en"])


def out_of_scope_message(lang: str) -> str:
    messages = {
        "en": (
            "I specialize in banking questions. I can help you with your account balance, "
            "transaction history, account details, KYC updates, and loan information. "
            "What banking question can I assist you with today?"
        ),
        "hi": (
            "मैं बैंकिंग प्रश्नों में विशेषज्ञ हूँ। मैं आपकी मदद कर सकता हूँ आपके खाते का बैलेंस, "
            "लेनदेन इतिहास, खाता विवरण, KYC अपडेट और लोन जानकारी में। "
            "आज मैं आपकी कौन सी बैंकिंग समस्या में मदद कर सकता हूँ?"
        ),
        "mr": (
            "मी बँकिंग प्रश्नांमध्ये तज्ञ आहे. मी तुम्हाला मदत करू शकतो तुमच्या खात्याची शिल्लक, "
            "व्यवहार इतिहास, खाते तपशील, KYC अपडेट आणि कर्ज माहितीमध्ये. "
            "आज मी तुम्हाला कोणत्या बँकिंग समस्येमध्ये मदत करू शकतो?"
        ),
    }
    return messages.get(lang, messages["en"])


def uncertain_faq_message(lang: str) -> str:
    messages = {
        "en": (
            "I'm not entirely sure about that. Could you please rephrase your question? "
            "For example, you can ask about your account balance, recent transactions, or account details."
        ),
        "hi": (
            "मुझे इस बारे में पूरी जानकारी नहीं है। क्या आप अपना प्रश्न दोबारा कह सकते हैं? "
            "उदाहरण के लिए, आप अपने खाते का बैलेंस, हाल के लेनदेन या खाता विवरण के बारे में पूछ सकते हैं।"
        ),
        "mr": (
            "त्याबद्दल मला पूर्ण माहिती नाही. तुम्ही तुमचा प्रश्न पुन्हा विचारू शकता का? "
            "उदाहरणार्थ, तुम्ही तुमच्या खात्याची शिल्लक, अलीकडील व्यवहार किंवा खाते तपशील विचारू शकता."
        ),
    }
    return messages.get(lang, messages["en"])


def _maybe_refine_with_indic_model(query: str, answer: str, lang: str) -> str:
    """Optionally improve phrasing using Indic-LLaMA while keeping facts unchanged."""
    if not INDIC_LLM_ENABLED:
        return answer
    
    model, tokenizer = _lazy_load_indic_model()
    if model is None or tokenizer is None:
        return answer

    # Keep escalation/scope messages deterministic and policy-safe.
    protected = {
        handoff_message(lang),
        out_of_scope_message(lang),
        uncertain_faq_message(lang),
    }
    if answer in protected:
        return answer

    language_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English")
    prompt = (
        f"You are a banking response refiner. Target language: {language_name}.\n"
        "Rules:\n"
        "1) Keep all numbers, dates, amounts and account identifiers unchanged.\n"
        "2) Do not add new facts, policy claims, or advice.\n"
        "3) Keep response concise and natural.\n"
        "4) Return only the refined answer text.\n\n"
        f"User question: {query}\n"
        f"Base answer: {answer}"
    )

    try:
        import torch
        inputs = tokenizer(prompt, return_tensors="pt", max_length=768, truncation=True)
        if _pick_torch_device() == "cuda" and torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=120,
                temperature=0.2,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        candidate = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        return candidate[:500].strip() or answer
    except Exception:
        return answer


def _maybe_refine_with_gemini(query: str, answer: str, lang: str) -> str:
    """Optionally improve phrasing using Gemini while keeping facts unchanged."""
    model = _lazy_load_gemini_model()
    if model is None:
        return answer

    protected = {
        handoff_message(lang),
        out_of_scope_message(lang),
        uncertain_faq_message(lang),
    }
    if answer in protected:
        return answer

    language_name = {"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English")
    prompt = (
        f"You are a banking response refiner. Target language: {language_name}.\n"
        "Rules:\n"
        "1) Keep all numbers, amounts, dates, account identifiers and facts exactly unchanged.\n"
        "2) Do not add new facts, policies, or advice.\n"
        "3) Keep the response concise and user-friendly.\n"
        "4) Return only the final refined answer text.\n\n"
        f"User question: {query}\n"
        f"Base answer: {answer}"
    )

    try:
        response = model.generate_content(prompt)
        candidate = (getattr(response, "text", "") or "").strip()
        if not candidate:
            return answer
        return candidate[:500]
    except Exception:
        return answer


def refine_answer(query: str, answer: str, lang: str) -> str:
    """Refine answer with Gemini first, then Indic model fallback."""
    global _last_refiner
    refined = _maybe_refine_with_gemini(query, answer, lang)
    if refined != answer:
        _last_refiner = "gemini"
        return refined

    refined = _maybe_refine_with_indic_model(query, answer, lang)
    if refined != answer:
        _last_refiner = "indic-llama"
        return refined

    _last_refiner = "deterministic"
    return answer


def get_refiner_status() -> Dict[str, str]:
    """Return active and configured refinement backend details."""
    configured = "deterministic"
    if GEMINI_ENABLED and GEMINI_API_KEY:
        configured = "gemini"
    elif INDIC_LLM_ENABLED:
        configured = "indic-llama"

    return {
        "configured_mode": configured,
        "last_used_mode": _last_refiner,
        "gemini_enabled": str(GEMINI_ENABLED).lower(),
        "indic_enabled": str(INDIC_LLM_ENABLED).lower(),
    }


# User-specific answers (deterministic)
def format_currency(amount: int) -> str:
    return f"{amount:,}"


def get_balance(user_id: str, lang: str) -> str:
    acc = ACCOUNT_BY_USER.get(user_id)
    if not acc:
        return {
            "en": "Account not found.",
            "hi": "खाता नहीं मिला।",
            "mr": "खातेची माहिती सापडली नाही.",
        }[lang]

    bal = format_currency(acc["balance"])
    if lang == "hi":
        return f"आपके खाते में ₹{bal} बैलेंस है।"
    if lang == "mr":
        return f"तुमच्या खात्यात ₹{bal} शिल्लक आहे."
    return f"Your account balance is ₹{bal}."


def get_transactions(user_id: str, lang: str, limit: int = 5) -> str:
    rows = sorted(TXNS_BY_USER.get(user_id, []), key=lambda x: x["date"], reverse=True)[:limit]
    if not rows:
        return {
            "en": "No transactions found.",
            "hi": "कोई लेनदेन नहीं मिला।",
            "mr": "व्यवहार सापडले नाहीत.",
        }[lang]

    if lang == "hi":
        header = "आपके हाल के लेनदेन:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "जमा"
        debit_label = "निकासी"
    elif lang == "mr":
        header = "तुमचे अलीकडील व्यवहार:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "जमा"
        debit_label = "डेबिट"
    else:
        header = "Your recent transactions:"
        line = "- {date}: {typ} ₹{amt}"
        credit_label = "credit"
        debit_label = "debit"

    lines = [header]
    for r in rows:
        typ = credit_label if r["type"].lower() == "credit" else debit_label
        lines.append(line.format(date=r["date"], typ=typ, amt=format_currency(r["amount"])))
    return "\n".join(lines)


def get_account_details(user_id: str, lang: str) -> str:
    acc = ACCOUNT_BY_USER.get(user_id)
    if not acc:
        return {
            "en": "Account details not found.",
            "hi": "खाते का विवरण नहीं मिला।",
            "mr": "खातेचे तपशील सापडले नाहीत.",
        }[lang]

    if lang == "hi":
        return (
            f"आपका अकाउंट नंबर {acc['account_number']} है। "
            f"अकाउंट प्रकार: {acc['account_type']}।"
        )
    if lang == "mr":
        return (
            f"तुमचा खाते क्रमांक {acc['account_number']} आहे. "
            f"खाते प्रकार: {acc['account_type']}."
        )
    return (
        f"Your account number is {acc['account_number']}. "
        f"Account type: {acc['account_type']}."
    )


def get_user_profile(user: dict, lang: str) -> str:
    if lang == "hi":
        return (
            f"आपका नाम {user['name']} है। "
            f"जिला: {user['district']}। "
            f"यूज़र प्रकार: {user['user_type']}।"
        )
    if lang == "mr":
        return (
            f"तुमचे नाव {user['name']} आहे. "
            f"जिल्हा: {user['district']}. "
            f"वापरकर्ता प्रकार: {user['user_type']}."
        )
    return (
        f"Your name is {user['name']}. "
        f"District: {user['district']}. "
        f"User type: {user['user_type']}."
    )


def get_account_status(lang: str) -> str:
    if lang == "hi":
        return "आपका खाता सक्रिय है।"
    if lang == "mr":
        return "तुमचे खाते सक्रिय आहे."
    return "Your account is active."


# FAQ retrieval with confidence guardrail

def extract_answer(doc: str) -> str:
    if "Answer:" in doc:
        start = doc.find("Answer:") + len("Answer:")
        end = doc.find("Intent:")
        if end == -1:
            return doc[start:].strip()
        return doc[start:end].strip()
    return doc.strip()


def get_common_banking_answer(query: str, lang: str) -> Optional[str]:
    """Provide direct answers for very common banking questions."""
    q = normalize(query)

    # Common questions that might not be in FAQ but are frequently asked
    common_patterns = {
        "en": {
            "how to check balance": "You can check your account balance by asking me 'What is my balance?' or by logging into the bank's mobile app.",
            "how to transfer money": "To transfer money, you can use UPI, NEFT, or RTGS through the bank's app or website. For UPI transfers, you'll need the recipient's UPI ID.",
            "how to reset pin": "To reset your ATM PIN, visit your nearest bank branch with your ID proof, or use the bank's mobile app if available.",
            "what is upi": "UPI (Unified Payments Interface) is a real-time payment system that allows instant money transfer between bank accounts using mobile numbers or UPI IDs.",
            "how to open account": "To open a new bank account, visit your nearest bank branch with ID proof, address proof, and passport-sized photographs.",
            "atm limit": "Daily ATM withdrawal limits vary by account type. Savings accounts typically allow ₹40,000-₹50,000 per day.",
        },
        "hi": {
            "बैलेंस कैसे चेक करें": "आप अपना खाता बैलेंस चेक करने के लिए मुझसे 'मेरा बैलेंस क्या है?' पूछ सकते हैं या बैंक की मोबाइल ऐप में लॉग इन कर सकते हैं।",
            "पैसे कैसे ट्रांसफर करें": "पैसे ट्रांसफर करने के लिए आप UPI, NEFT या RTGS का इस्तेमाल बैंक ऐप या वेबसाइट के माध्यम से कर सकते हैं। UPI ट्रांसफर के लिए रिसीवर का UPI ID चाहिए।",
            "पिन कैसे रीसेट करें": "ATM PIN रीसेट करने के लिए अपने नजदीकी बैंक ब्रांच जाएं ID प्रूफ लेकर, या अगर उपलब्ध हो तो बैंक की मोबाइल ऐप इस्तेमाल करें।",
            "upi क्या है": "UPI (यूनिफाइड पेमेंट्स इंटरफेस) एक रीयल-टाइम पेमेंट सिस्टम है जो मोबाइल नंबर या UPI ID का इस्तेमाल करके बैंक खातों के बीच तुरंत पैसे ट्रांसफर करने की अनुमति देता है।",
            "खाता कैसे खोलें": "नया बैंक खाता खोलने के लिए अपने नजदीकी बैंक ब्रांच जाएं ID प्रूफ, एड्रेस प्रूफ और पासपोर्ट साइज फोटो लेकर।",
            "atm लिमिट": "दैनिक ATM निकासी की सीमा खाता प्रकार के अनुसार अलग-अलग होती है। सेविंग्स खाते में आमतौर पर दिन में ₹40,000-₹50,000 की अनुमति होती है।",
        },
        "mr": {
            "बॅलन्स कसा चेक करावा": "तुम्ही तुमचा खाता बॅलन्स चेक करण्यासाठी मला 'माझी शिल्लक काय आहे?' विचारू शकता किंवा बँकेच्या मोबाइल अॅपमध्ये लॉग इन करू शकता.",
            "पैसे कसे ट्रान्सफर करावे": "पैसे ट्रान्सफर करण्यासाठी तुम्ही UPI, NEFT किंवा RTGS चा वापर बँक अॅप किंवा वेबसाइटद्वारे करू शकता. UPI ट्रान्सफरसाठी रिसीव्हरचा UPI ID लागतो.",
            "पिन कसा रीसेट करावा": "ATM PIN रीसेट करण्यासाठी तुमच्या जवळच्या बँक शाखेत जा ID प्रूफ घेऊन, किंवा उपलब्ध असल्यास बँकेची मोबाइल अॅप वापरा.",
            "upi काय आहे": "UPI (युनिफाइड पेमेंट्स इंटरफेस) हा रिअल-टाइम पेमेंट सिस्टम आहे जो मोबाइल नंबर किंवा UPI ID वापरून बँक खात्यांदरम्यान तातडीने पैसे ट्रान्सफर करण्यास परवानगी देतो.",
            "खाते कसे उघडावे": "नवीन बँक खाते उघडण्यासाठी तुमच्या जवळच्या बँक शाखेत जा ID प्रूफ, पत्ता प्रूफ आणि पासपोर्ट साइज फोटो घेऊन.",
            "atm लिमिट": "दैनिक ATM पैसे काढण्याची मर्यादा खाते प्रकारानुसार वेगवेगळी असते. बचत खात्यांमध्ये सहसा दिवसाला ₹40,000-₹50,000 पर्यंत परवानगी असते.",
        }
    }

    lang_patterns = common_patterns.get(lang, common_patterns["en"])

    for pattern, answer in lang_patterns.items():
        if pattern in q:
            return answer

    return None


def vector_search_faq(query: str, lang: str) -> str:
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=6,
        where={"type": "faq"},
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        # Try common banking answers as fallback
        common_answer = get_common_banking_answer(query, lang)
        if common_answer:
            return refine_answer(query, common_answer, lang)
        return uncertain_faq_message(lang)

    top_dist = distances[0] if distances else 999.0
    if top_dist > MAX_FAQ_DISTANCE:
        # Try common banking answers before giving up
        common_answer = get_common_banking_answer(query, lang)
        if common_answer:
            return refine_answer(query, common_answer, lang)
        return uncertain_faq_message(lang)

    # If top candidates are too close but represent different intents, avoid random answer.
    if len(distances) > 1 and len(metas) > 1:
        gap = distances[1] - distances[0]
        top_intent = metas[0].get("intent")
        second_intent = metas[1].get("intent")
        if top_intent != second_intent and gap < MIN_FAQ_DISTANCE_GAP:
            # Try common banking answers before uncertain message
            common_answer = get_common_banking_answer(query, lang)
            if common_answer:
                return refine_answer(query, common_answer, lang)
            return uncertain_faq_message(lang)

    # Prefer same-language answer with good distance.
    for doc, meta, dist in zip(docs, metas, distances):
        if meta.get("language") == lang and dist <= MAX_FAQ_DISTANCE:
            return refine_answer(query, extract_answer(doc), lang)

    # Fallback 1: best intent in requested language.
    top_intent = metas[0].get("intent") if metas else None
    top_dist = distances[0] if distances else 999.0
    if top_intent and (top_intent, lang) in FAQ_BY_INTENT_LANG and top_dist <= MAX_FAQ_DISTANCE:
        return refine_answer(query, FAQ_BY_INTENT_LANG[(top_intent, lang)], lang)

    # Fallback 2: strict language query.
    lang_results = collection.query(
        query_embeddings=query_embedding,
        n_results=1,
        where={"$and": [{"type": "faq"}, {"language": lang}]},
        include=["documents", "distances"],
    )
    lang_docs = lang_results.get("documents", [[]])[0]
    lang_distances = lang_results.get("distances", [[]])[0]
    if lang_docs and lang_distances and lang_distances[0] <= MAX_FAQ_DISTANCE:
        return refine_answer(query, extract_answer(lang_docs[0]), lang)

    # Final fallback: common banking answers
    common_answer = get_common_banking_answer(query, lang)
    if common_answer:
        return refine_answer(query, common_answer, lang)

    return uncertain_faq_message(lang)


def answer_query(user: dict, query: str, lang_hint: Optional[str] = None) -> Tuple[str, List[str]]:
    lang = lang_hint if lang_hint in {"en", "hi", "mr"} else detect_language(query)
    intent = detect_intent(query)
    user_id = user["user_id"]

    # Deterministic intents: NEVER refine with LLM for banking facts to prevent hallucination.
    if intent == "account_balance":
        answer = get_balance(user_id, lang)
        related = get_related_questions(intent, lang)
        return answer, related
    if intent == "transactions":
        answer = get_transactions(user_id, lang)
        related = get_related_questions(intent, lang)
        return answer, related
    if intent == "account_details":
        answer = get_account_details(user_id, lang)
        related = get_related_questions(intent, lang)
        return answer, related
    if intent == "account_status":
        answer = get_account_status(lang)
        related = get_related_questions(intent, lang)
        return answer, related
    if intent == "user_profile":
        answer = get_user_profile(user, lang)
        related = get_related_questions(intent, lang)
        return answer, related

    # For FAQ/general banking queries, use vector search with optional LLM refinement.
    if intent != "general":
        answer = refine_answer(query, vector_search_faq(query, lang), lang)
        related = get_related_questions(intent, lang)
        return answer, related

    if not is_bank_related(query):
        answer = out_of_scope_message(lang)
        related = get_related_questions("general", lang)
        return answer, related

    answer = refine_answer(query, vector_search_faq(query, lang), lang)
    related = get_related_questions("general", lang)
    return answer, related


def run_cli() -> None:
    print("AI Banking Assistant started.")
    print("Supported languages: English, Hindi, Marathi")
    print("Use any valid mobile from data/users.json to login.")
    print("Example mobile: 9876543210")
    print("Type 'help' after login for sample questions.")

    mobile = input("Enter your mobile number: ").strip()
    user = USER_BY_MOBILE.get(mobile)

    if not user:
        print("User not found.")
        print("Try one of these demo numbers:")
        for m in list(USER_BY_MOBILE.keys())[:5]:
            print(f"- {m}")
        raise SystemExit(1)

    print("Login successful.")
    print_help_examples()

    while True:
        query = input("Ask your question (or type 'exit'): ").strip()
        if not query:
            continue
        if query.lower() == "help":
            print_help_examples()
            continue
        if query.lower() == "exit":
            print("Goodbye!")
            break

        answer = answer_query(user, query)
        print("\nAnswer:")
        print(answer)
        print("-" * 50)


if __name__ == "__main__":
    run_cli()
