import hashlib
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="xyzBank — Voice-Assisted Biometric Banking Kiosk API",
    description="REST API for account lookup and SHA-256 cryptographic Aadhaar e-Sign slip generation.",
    version="1.0.0",
)

# Enable CORS so a Render Static Site frontend can communicate seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server cryptographic salt (override via env var in production)
ESIGN_SECRET_SALT = os.getenv("ESIGN_SECRET_SALT", "xyzBank-Aadhaar-L1-Biometric-eSign-Salt-2026")
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class AccountRecord(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    account_number: Optional[str] = Field(default=None, max_length=32)
    aadhaar_last4: str = Field(default="0000", pattern=r"^\d{4}$")
    branch: str = Field(default="Kiosk Registered", max_length=80)


class AccountLookupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class AccountLookupResponse(BaseModel):
    found: bool
    account: Optional[AccountRecord] = None
    match_score: float = 0.0


class ESignRequest(BaseModel):
    account_holder: str = Field(..., min_length=2, max_length=120)
    account_number: str = Field(..., min_length=4, max_length=32)
    tx_type: str = Field(..., pattern=r"^(DEPOSIT|WITHDRAWAL)$")
    amount: int = Field(..., gt=0, le=10_000_000)
    biometric_token: str = Field(..., min_length=4, max_length=256)
    mode: str = Field(default="PROTOTYPE", pattern=r"^(PROTOTYPE|USER)$")


class ESignResponse(BaseModel):
    reference_id: str
    timestamp: str
    account_holder: str
    account_number: str
    tx_type: str
    amount: int
    mode: str
    sha256_hash: str
    esign_verified: bool = True


# ---------------------------------------------------------------------------
# Pre-loaded Prototype Account Store
# ---------------------------------------------------------------------------
ACCOUNTS_DB: List[AccountRecord] = [
    AccountRecord(
        name="Drushya S N",
        account_number="XYZB00104821",
        aadhaar_last4="7842",
        branch="Bengaluru Main",
    ),
    AccountRecord(
        name="Ramesh Kumar",
        account_number="XYZB00109354",
        aadhaar_last4="5190",
        branch="Mysuru Rural",
    ),
    AccountRecord(
        name="Lakshmi Devi",
        account_number="XYZB00112763",
        aadhaar_last4="3068",
        branch="Mandya Branch",
    ),
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "xyzBank Biometric Kiosk API",
        "status": "running",
        "endpoints": ["/health", "/api/accounts", "/api/accounts/lookup", "/api/esign"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")}


@app.get("/api/accounts", response_model=List[AccountRecord])
def list_accounts():
    return ACCOUNTS_DB


@app.post("/api/accounts", response_model=AccountRecord, status_code=201)
def register_account(payload: AccountRecord):
    acc_num = payload.account_number
    if not acc_num:
        acc_num = f"XYZB{uuid.uuid4().hex[:8].upper()}"

    # Prevent duplicate account numbers
    for existing in ACCOUNTS_DB:
        if existing.account_number == acc_num:
            raise HTTPException(status_code=409, detail="Account number already exists.")

    record = AccountRecord(
        name=payload.name.strip(),
        account_number=acc_num,
        aadhaar_last4=payload.aadhaar_last4,
        branch=payload.branch,
    )
    ACCOUNTS_DB.append(record)
    return record


@app.post("/api/accounts/lookup", response_model=AccountLookupResponse)
def lookup_account(payload: AccountLookupRequest):
    query = _normalize(payload.name)
    if not query:
        return AccountLookupResponse(found=False, account=None, match_score=0.0)

    q_tokens = set(query.split())
    best_account: Optional[AccountRecord] = None
    best_score = 0.0

    for acc in ACCOUNTS_DB:
        target = _normalize(acc.name)
        if target == query:
            return AccountLookupResponse(found=True, account=acc, match_score=1.0)
        if query in target or target in query:
            return AccountLookupResponse(found=True, account=acc, match_score=0.9)

        t_tokens = set(target.split())
        if not t_tokens:
            continue

        overlap = sum(
            1
            for qt in q_tokens
            if any(tt == qt or tt.startswith(qt) or qt.startswith(tt) for tt in t_tokens)
        )
        score = overlap / max(len(q_tokens), len(t_tokens))
        if score > best_score and score >= 0.4:
            best_score = score
            best_account = acc

    if best_account:
        return AccountLookupResponse(found=True, account=best_account, match_score=round(best_score, 2))

    return AccountLookupResponse(found=False, account=None, match_score=0.0)


@app.post("/api/esign", response_model=ESignResponse)
def generate_aadhaar_esign(payload: ESignRequest):
    now_ist = datetime.now(IST)
    reference_id = f"XYZ-{now_ist.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    timestamp_str = now_ist.strftime("%d %b %Y, %I:%M:%S %p IST")

    # Canonical cryptographic payload for SHA-256 Aadhaar e-Sign verification
    canonical_string = (
        f"{reference_id}|{payload.account_number}|{payload.account_holder}|"
        f"{payload.tx_type}|{payload.amount}|{payload.biometric_token}|"
        f"{payload.mode}|{timestamp_str}|{ESIGN_SECRET_SALT}"
    )
    sha256_hash = hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()

    return ESignResponse(
        reference_id=reference_id,
        timestamp=timestamp_str,
        account_holder=payload.account_holder,
        account_number=payload.account_number,
        tx_type=payload.tx_type,
        amount=payload.amount,
        mode=payload.mode,
        sha256_hash=sha256_hash,
        esign_verified=True,
    )