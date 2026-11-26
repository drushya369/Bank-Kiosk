import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel

app = FastAPI(title="VaaniBank Biometric Kiosk API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class AccountCreate(BaseModel):
    name: str
    account: str

class SlipRequest(BaseModel):
    name: str
    account: str
    tx_type: str
    amount: float
    biometric_pulses: int = 1

ACCOUNTS_DB: List[dict] = [
    {"name": "Drushya S N", "account": "7739104826"},
    {"name": "Ramesh Kumar", "account": "4092817365"},
    {"name": "Lakshmi Devi", "account": "8821049512"},
]

@app.get("/")
def health_check():
    return {"status": "online", "service": "VaaniBank Biometric Kiosk API"}

async def _run_gemini_audio(audio_bytes: bytes, mime_type: str, prompt: str, json_mode: bool = False) -> str:
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type or "audio/webm"),
        ],
        config=config,
    )
    return (response.text or "").strip()

@app.post("/api/turn")
async def voice_turn(
    audio: UploadFile = File(...),
    step_state: str = Form("ASK_NAME"),
    context_info: str = Form("")
):
    """Understands user speech with Gemini and returns both transcript and clean intent."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        return {"transcript": "", "intent": "UNKNOWN", "name": None, "amount": None}

    registered_names = ", ".join(acc["name"] for acc in ACCOUNTS_DB)
    prompt = (
        f"You are the voice parser for VaaniBank, an Indian banking kiosk.\n"
        f"Current step: {step_state}. Extra context: {context_info}.\n"
        f"Registered account holders: [{registered_names}].\n"
        f"Listen to the user's audio (Indian English, Kannada, Hindi, or mixed speech). "
        f"Map simple confirmations like 'yes', 'yeah', 'yep', 'haan', 'ok', 'confirm' to intent 'YES', "
        f"and 'no', 'nope', 'wrong', 'cancel', 'nahi' to intent 'NO'. "
        f"For transaction type, map deposit words to 'DEPOSIT' and withdrawal words to 'WITHDRAWAL'. "
        f"For amounts, extract the numeric rupees value as a positive number (e.g., 5000). "
        f"For names, match closely to one of the registered names if possible or return the spoken name.\n"
        f"Return STRICT JSON with keys: "
        f'{{"transcript": string, "intent": "YES"|"NO"|"DEPOSIT"|"WITHDRAWAL"|"NAME"|"AMOUNT"|"REPEAT"|"UNKNOWN", "name": string|null, "amount": number|null}}'
    )

    try:
        raw = await _run_gemini_audio(audio_bytes, audio.content_type or "audio/webm", prompt, json_mode=True)
        parsed = json.loads(raw)
        return {
            "transcript": str(parsed.get("transcript") or "").strip(),
            "intent": str(parsed.get("intent") or "UNKNOWN").upper(),
            "name": parsed.get("name"),
            "amount": parsed.get("amount"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini turn error: {str(e)}")

@app.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    context_hint: str = Form("general")
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    registered_names = ", ".join(acc["name"] for acc in ACCOUNTS_DB)
    prompt = (
        f"Transcribe this short banking kiosk audio from an Indian user. "
        f"Step: {context_hint}. Known names: {registered_names}. "
        f"Return ONLY the exact words or digits spoken, with no extra text."
    )
    try:
        text = await _run_gemini_audio(audio_bytes, audio.content_type or "audio/webm", prompt, json_mode=False)
        return {"transcript": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini transcription error: {str(e)}")

@app.get("/api/lookup")
def lookup_account(name: str):
    query = name.strip().lower()
    for acc in ACCOUNTS_DB:
        if query in acc["name"].lower() or acc["name"].lower() in query:
            return acc
    raise HTTPException(status_code=404, detail="Account not found")

@app.post("/api/accounts")
def register_account(payload: AccountCreate):
    new_acc = {"name": payload.name.strip(), "account": payload.account.strip()}
    ACCOUNTS_DB.append(new_acc)
    return {"message": "Account registered", "account": new_acc}

@app.post("/api/generate-slip")
def generate_slip(payload: SlipRequest):
    now_str = datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p")
    ref_id = f"BIO-{secrets.token_hex(4).upper()}"
    raw_token = f"{payload.account}:{payload.tx_type.upper()}:{payload.amount}:{payload.biometric_pulses}:{ref_id}"
    esign_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest().upper()

    return {
        "reference_id": ref_id,
        "timestamp": now_str,
        "name": payload.name,
        "account": payload.account,
        "tx_type": payload.tx_type.upper(),
        "amount": payload.amount,
        "esign_hash": esign_hash,
    }