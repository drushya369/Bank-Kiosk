import hashlib
import os
import secrets
from datetime import datetime
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel

app = FastAPI(title="VaaniBank Biometric Kiosk API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini client (automatically reads GEMINI_API_KEY from environment)
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

@app.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    context_hint: str = Form("general")
):
    """Receives recorded browser audio and transcribes it using Gemini."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    mime_type = audio.content_type or "audio/webm"
    registered_names = ", ".join(acc["name"] for acc in ACCOUNTS_DB)

    prompt = (
        f"Listen to this short banking kiosk audio clip from an Indian user. "
        f"Current kiosk step: {context_hint}. "
        f"Registered account names for reference: {registered_names}. "
        f"Return ONLY the exact spoken words (such as the person's name, 'Yes', 'No', "
        f"'Deposit', 'Withdrawal', or the numeric amount in digits). "
        f"Do not add punctuation, explanations, or extra text. If silent/unintelligible, return empty."
    )

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        transcript = (response.text or "").strip()
        return {"transcript": transcript}
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