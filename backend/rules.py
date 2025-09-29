import uuid, asyncio
from ai_helper import ask_ai
from translate import translate_text

SESSIONS = {}

def create_session():
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {
        "lang": "en",
        "conversation": []  
    }
    return sid

async def handle_message(session_id: str, user_input: str, lang: str = "en", action: str = None):
    if not session_id or session_id not in SESSIONS:
        session_id = create_session()
    session = SESSIONS[session_id]
    session["lang"] = lang

   
    input_text = user_input
    if lang != "en":
        input_text = translate_text(user_input, source=lang, target="en")

    
    ai_reply = await ask_ai(input_text, lang="en")

   
    if lang != "en":
        ai_reply = translate_text(ai_reply, source="en", target=lang)

    
    session["conversation"].append({"user": user_input, "bot": ai_reply})

    return {"session_id": session_id, "text": ai_reply, "awaiting": False}
