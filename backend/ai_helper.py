# backend/ai_helper.py
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load API key
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def ask_ai(prompt: str, lang: str = "en") -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # fast + cheap model
            messages=[
                {"role": "system", "content": "You are a helpful health assistant. Be empathetic but concise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("AI error:", e)
        return "⚠️ Sorry, AI service is not available right now."
