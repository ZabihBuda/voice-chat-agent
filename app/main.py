"""Voice chat agent backend.

Serves the web page, hands the browser short-lived Azure Speech tokens (so the
Speech key never leaves the server), and answers questions with Azure OpenAI.
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.llm import answer_question

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

load_dotenv(ROOT / ".env")

app = FastAPI(title="Voice Chat Agent")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} is not set. Add it to your .env file.")
    return value


@app.get("/api/speech-token")
async def speech_token():
    """Exchange the Speech key for a token that is valid for 10 minutes."""
    key = _require_env("AZURE_SPEECH_KEY")
    region = _require_env("AZURE_SPEECH_REGION")
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers={"Ocp-Apim-Subscription-Key": key})
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Azure Speech token request failed ({resp.status_code}). Check your key and region.")
    return {
        "token": resp.text,
        "region": region,
        "voice": os.getenv("AZURE_SPEECH_VOICE", "en-US-JennyNeural"),
        "language": os.getenv("AZURE_SPEECH_LANGUAGE", "en-US"),
    }


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=20)


@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        answer = answer_question(req.question, [t.model_dump() for t in req.history])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"answer": answer}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
