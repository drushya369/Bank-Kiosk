from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import time
import uuid

app = FastAPI(title="VaaniBank Biometric Kiosk API")

# Enable CORS so the frontend on Render can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory account store (can be upgraded to PostgreSQL later)
ACCOUNTS_DB = [
    {"name": "Drushya S N", "account": "7739104826"},
    {"name": "Ramesh Kumar", "account": "4092817365"},
    {"name": "Lakshmi Devi", "account": "8821049512"},
]


class AccountCreate(BaseModel):
    name: str
    account: str


class SlipRequest(BaseModel):
    account: str
    tx_type: str
    amount: float


@app.get("/")
def health_check():
    return {"status": "online", "service": "VaaniBank Biometric Kiosk API"}


@app.get("/api/accounts")
def list_accounts():
    return {"accounts": ACCOUNTS_DB}


@app.post("/api/accounts")
def register_account(payload: AccountCreate):
    new_entry = {"name": payload.name.strip(), "account": payload.account.strip()}
    ACCOUNTS_DB.append(new_entry)
    return {"message": "Account registered", "account": new_entry}


@app.get("/api/lookup")
def lookup_account(name: str):
    query = name.strip().lower()
    for acc in ACCOUNTS_DB:
        if acc["name"].lower() == query or query in acc["name"].lower():
            return acc
    raise HTTPException(status_code=404, detail="Account not found")


@app.post("/api/generate-slip")
def generate_slip(data: SlipRequest):
    ref_id = f"UIDAI-{uuid.uuid4().hex[:8].upper()}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    raw_payload = f"{data.account}:{data.tx_type}:{data.amount}:{time.time()}"
    esign_hash = hashlib.sha256(raw_payload.encode()).hexdigest().upper()

    return {
        "reference_id": ref_id,
        "esign_hash": esign_hash,
        "timestamp": timestamp,
        "verified": True,
    }