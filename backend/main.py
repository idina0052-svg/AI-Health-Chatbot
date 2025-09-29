from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from rules import handle_message, create_session
from typing import Optional

app = FastAPI()

# Logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"➡️ Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"⬅️ Response status: {response.status_code}")
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ChatRequest(BaseModel):
    message: str = ""
    lang: str = "en"
    session_id: Optional[str] = None
    action: Optional[str] = None

# Chat handler
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        resp =await handle_message(req.session_id, req.message, lang=req.lang, action=req.action) or {}
        if "session_id" not in resp:
            resp["session_id"] = req.session_id or create_session()
        return resp
    except Exception as e:
        # Log the error for debugging
        print("❌ Error in /chat:", e)
        return {"text": "⚠️ Server error occurred.", "session_id": req.session_id}
