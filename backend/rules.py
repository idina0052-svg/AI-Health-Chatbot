import json, os, uuid, asyncio
from rapidfuzz import process, fuzz
from translate import translate_text
from ai_helper import ask_ai  

KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")
KB_CACHE = {}

FALLBACK_MSGS = {
    "en": {
        "unknown": "I don’t have specific instructions in my offline knowledge base. Trying AI assistant...",
        "done": "Those are the steps. If the problem continues or is severe, please seek emergency care."
    },
    "ti": {
        "unknown": "ኣብ ካብ መስመር ወጻኢ ፍልጠት የብለይን። ኣሎ AI ሓጋዚ ንምርካብ...",
        "done": "እቶም ስጉምትታት እዮም። ጸገም እንተቐጺሉ ወይ ከቢድ እንተኾይኑ ህጹጽ ክንክን ድለዩ።"
    }
}

def load_kb(lang="en"):
    key = f"{lang}"
    if key in KB_CACHE:
        return KB_CACHE[key]
    path = os.path.join(KB_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(KB_DIR, "en.json")
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    KB_CACHE[key] = kb
    return kb

SESSIONS = {}
def create_session():
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {
        "intent": None,
        "steps": [],
        "current_step": -1,
        "awaiting_followup": False,
        "followup_meta": None,
        "lang": "en"
    }
    return sid

def is_positive(answer: str, lang="en"):
    a = answer.strip().replace("።","").replace(".","").lower()
    positives = {"en": ["yes","y","ya","yep","sure"],
                 "ti": ["እወ","yes"],
                 "am": ["አዎ","yes"]}
    neg = {"en": ["no","n","not","nope"],
           "ti": ["ኣይ","ኖኖ"],
           "am": ["አይ","ኖኖ"]}
    if a in positives.get(lang, []) or any(a.startswith(p) for p in positives.get(lang, [])):
        return True
    if a in neg.get(lang, []) or any(a.startswith(n) for n in neg.get(lang, [])):
        return False
    if "heavy" in a or "spurting" in a or "ከባድ" in a or "ዘይሳሕ" in a:
        return True
    return False

def match_intent(user_input: str, kb: dict):
    ui = user_input.lower()
    for intent, entry in kb.items():
        for kw in entry.get("keywords", [intent]):
            if kw.lower() in ui:
                return intent
    choices, kws_map = [], {}
    for intent, entry in kb.items():
        for kw in entry.get("keywords", [intent]):
            k = kw.lower()
            choices.append(k)
            kws_map[k] = intent
    match = process.extractOne(ui, choices, scorer=fuzz.WRatio)
    if match and match[1] >= 60:
        return kws_map[match[0]]
    return None

def start_intent(session, intent, kb):
    entry = kb.get(intent)
    lang = session["lang"]
    if not entry:
        return {"text": FALLBACK_MSGS[lang]["unknown"], "awaiting": False, "has_next": False}
    session["intent"] = intent
    session["steps"] = entry.get("steps", [])
    session["current_step"] = 0
    session["awaiting_followup"] = False
    session["followup_meta"] = None
    followups = entry.get("followups") or []
    if followups:
        session["awaiting_followup"] = True
        session["followup_meta"] = followups[0]
        step_text = session["steps"][0] if session["steps"] else ""
        return {"text": step_text, "followup_question": session["followup_meta"]["question"], "awaiting": True, "has_next": len(session["steps"]) > 1}
    else:
        step_text = session["steps"][0] if session["steps"] else ""
        return {"text": step_text, "awaiting": False, "has_next": len(session["steps"]) > 1}

def advance_step(session, kb):
    lang = session["lang"]
    if session["current_step"] + 1 < len(session["steps"]):
        session["current_step"] += 1
        return {"text": session["steps"][session["current_step"]], "awaiting": False, "done": False, "has_next": session["current_step"] + 1 < len(session["steps"])}
    else:
        escalation = kb.get(session["intent"], {}).get("escalation")
        final_msg = escalation if escalation else FALLBACK_MSGS[lang]["done"]
        return {"text": final_msg, "awaiting": False, "done": True, "has_next": False}

def handle_message(session_id: str, user_input: str, lang: str = "en", action: str = None):
    if not session_id or session_id not in SESSIONS:
        session_id = create_session()
    session = SESSIONS[session_id]
    session["lang"] = lang

    kb = load_kb(lang)

    if action == "next":
        resp = advance_step(session, kb)
    else:
        if session.get("awaiting_followup"):
            meta = session.get("followup_meta")
            if meta:
                positive = is_positive(user_input, lang)
                if positive and meta.get("yes_intent"):
                    resp = start_intent(session, meta["yes_intent"], kb)
                elif not positive and meta.get("no_intent"):
                    resp = start_intent(session, meta["no_intent"], kb)
                else:
                    session["awaiting_followup"] = False
                    session["followup_meta"] = None
                    resp = advance_step(session, kb)
            else:
                resp = advance_step(session, kb)
        else:
            intent = match_intent(user_input, kb)
            if intent:
                resp = start_intent(session, intent, kb)
            else:
                # ✅ Fallback to AI
                input_text = user_input
                if lang != "en":
                    input_text = translate_text(user_input, source=lang, target="en")

                ai_reply = asyncio.run(ask_ai(input_text, lang="en"))

                if lang != "en":
                    ai_reply = translate_text(ai_reply, source="en", target=lang)

                resp = {"text": ai_reply, "awaiting": False}

    return {"session_id": session_id, **resp}
