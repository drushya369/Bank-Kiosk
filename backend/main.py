import hashlib
import secrets
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="VaaniBank Biometric Kiosk API", version="1.0.0")

# Allow frontend Static Site on Render to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AccountCreate(BaseModel):
    name: str
    account: str


class SlipRequest(BaseModel):
    name: str
    account: str
    tx_type: str
    amount: float
    biometric_pulses: int = 1


# In-memory demo account directory
ACCOUNTS_DB: List[dict] = [
    {"name": "Drushya S N", "account": "7739104826"},
    {"name": "Ramesh Kumar", "account": "4092817365"},
    {"name": "Lakshmi Devi", "account": "8821049512"},
]


@app.get("/")
def health_check():
    return {"status": "online", "service": "VaaniBank Biometric Kiosk API"}


@app.get("/api/lookup")
def lookup_account(name: str):
    query = name.strip().lower()
    if not query:
        raise HTTPException(status_code=400, detail="Name query cannot be empty")

    for acc in ACCOUNTS_DB:
        acc_name = acc["name"].lower()
        if acc_name == query or query in acc_name or acc_name in query:
            return acc

    raise HTTPException(status_code=404, detail="Account not found")


@app.post("/api/accounts")
def register_account(payload: AccountCreate):
    new_acc = {"name": payload.name.strip(), "account": payload.account.strip()}
    ACCOUNTS_DB.append(new_acc)
    return {"message": "Account registered", "account": new_acc}


@app.post("/api/generate-slip")
def generate_slip(payload: SlipRequest):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    tx_type = payload.tx_type.upper()
    if tx_type not in {"DEPOSIT", "WITHDRAWAL"}:
        raise HTTPException(status_code=400, detail="Invalid transaction type")

    now_str = datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p")
    ref_id = f"BIO-{secrets.token_hex(4).upper()}"
    raw_token = f"{payload.account}:{tx_type}:{payload.amount}:{payload.biometric_pulses}:{ref_id}"
    esign_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest().upper()

    return {
        "reference_id": ref_id,
        "timestamp": now_str,
        "name": payload.name,
        "account": payload.account,
        "tx_type": tx_type,
        "amount": payload.amount,
        "esign_hash": esign_hash,
    }