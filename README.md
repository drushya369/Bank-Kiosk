# VaaniBank — Voice-Assisted Biometric Banking Kiosk

VaaniBank is a voice-assisted, biometric banking kiosk prototype designed to help non-literate, semi-literate, elderly, and visually impaired customers generate cash deposit and withdrawal slips without manual form filling or handwritten/cursive signatures.

## Key Features

- **Strict Half-Duplex Voice Engine:** Physically stops microphone recording while the kiosk speaks and waits through an echo buffer before opening the mic so the built-in laptop microphone does not capture the kiosk's own voice.
- **Gemini AI Audio Transcription (`/api/transcribe`):** Uses `MediaRecorder` (`echoCancellation: true`, `noiseSuppression: true`) to capture short audio clips and sends them to a FastAPI backend powered by Gemini (`gemini-3.5-flash-lite`) with step context and registered account hints for Indian accents and spoken numbers.
- **Step-by-Step Readback Verification:** Confirms each input (`Yes` / `No`) across four stages: **Thumb Lock** -> **Account Name** -> **Transaction Type (Deposit/Withdrawal)** -> **Amount & Final Confirmation**, with manual fallback inputs and buttons at every step.
- **Continuous Biometric Lock & Cryptographic e-Sign:** Tracks continuous thumb contact via a heartbeat timer (with a simulated lock toggle in Prototype Mode and UIDAI L1 RD Service polling on `https://127.0.0.1:11100` in User Mode), performs a mid-session biometric check, and generates a printable slip containing a Reference ID, timestamp, and **SHA-256** verification hash.

## Repository Structure

```text
Bank-Kiosk/
├── frontend/
│   └── index.html          # Standalone Tailwind CSS + Vanilla JS kiosk UI
├── backend/
│   ├── main.py             # FastAPI endpoints (/api/transcribe, /api/lookup, /api/accounts, /api/generate-slip)
│   └── requirements.txt    # Python dependencies
└── README.md
