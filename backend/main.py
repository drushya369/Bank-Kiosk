import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel

app = FastAPI(title="VaaniBank Biometric Kiosk API", version="2.2.0")

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

def _clean_mime_type(raw_mime: str | None) -> str:
    if not raw_mime:
        return "audio/webm"
    base = raw_mime.split(";")[0].strip().lower()
    return base or "audio/webm"

@app.post("/api/turn")
async def voice_turn(
    audio: UploadFile = File(...),
    step_state: str = Form("ASK_NAME"),
    context_info: str = Form("")
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        return {"transcript": "", "intent": "UNKNOWN", "name": None, "amount": None}

    mime_type = _clean_mime_type(audio.content_type)
    registered_names = ", ".join(acc["name"] for acc in ACCOUNTS_DB)

    prompt = (
        f"You are the voice intent parser for VaaniBank, an Indian banking kiosk.\n"
        f"Current step: {step_state}. Context: {context_info}.\n"
        f"Registered names: [{registered_names}].\n"
        f"Listen to the audio clip (Indian English, Kannada, Hindi, or mixed).\n"
        f"Map confirmations ('yes', 'yeah', 'yep', 'ok', 'okay', 'haan', 'ha', 'confirm') -> 'YES'.\n"
        f"Map rejections ('no', 'nope', 'wrong', 'cancel', 'nahi', 'retry') -> 'NO'.\n"
        f"Map deposit -> 'DEPOSIT', withdrawal/withdraw -> 'WITHDRAWAL'.\n"
        f"If amount is spoken, set 'amount' to the number (e.g., 5000) and intent 'AMOUNT'.\n"
        f"If a name is spoken, set 'name' to the closest registered name or spoken name and intent 'NAME'.\n"
        f"Reply ONLY with valid JSON: "
        f'{{"transcript": "...", "intent": "YES|NO|DEPOSIT|WITHDRAWAL|NAME|AMOUNT|UNKNOWN", "name": null, "amount": null}}'
    )

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        raw_text = (response.text or "").strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "", 1).strip()
        parsed = json.loads(raw_text)
        return {
            "transcript": str(parsed.get("transcript") or "").strip(),
            "intent": str(parsed.get("intent") or "UNKNOWN").upper(),
            "name": parsed.get("name"),
            "amount": parsed.get("amount"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini turn error: {str(e)}")

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