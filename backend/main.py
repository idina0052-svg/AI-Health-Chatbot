# backend/main.py (add/change chat handler)
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from rules import handle_message, create_session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str = ""
    lang: str = "en"
    session_id: str | None = None
    action: str | None = None  # "next" or None

@app.post("/chat")
def chat(req: ChatRequest):
    resp = handle_message(req.session_id, req.message, lang=req.lang, action=req.action)
    # ensure session_id returned
    if "session_id" not in resp:
        resp["session_id"] = req.session_id or create_session()
    return resp
