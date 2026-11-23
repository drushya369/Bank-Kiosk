# Bank Kiosk
A kiosk to print the transaction (withdrawal or Deposit) slip through voice instructions
<p>
**Project Summary: Voice-Assisted Biometric Banking Kiosk**

**Problem Statement**
Non-literate and visually impaired individuals face significant barriers when filling out physical deposit and withdrawal slips at banks, often forcing them to rely on third parties and exposing them to potential fraud or privacy risks.

**Solution Overview**
This project is a voice-assisted, dual-mode banking kiosk prototype built with Python and FastAPI that enables users to independently generate printed deposit and withdrawal slips using voice commands and continuous biometric authentication.

**Core Logical Workflow**

1. **Session Initiation & Continuous Biometric Lock:** The user initiates the session by placing their thumb on the biometric scanner. The system acts as a continuous "dead-man's switch"—if the user lifts their finger at any point before the slip is printed, the session immediately terminates and resets to prevent third-party tampering or session hijacking.
2. **Voice-Guided Interaction:** Once authenticated, the kiosk welcomes the user and provides clear, step-by-step audio instructions.
3. **Identity & Account Resolution:** The user speaks their name, which the backend cross-references against the bank's database to fetch and auto-fill their corresponding account number onto the digital slip.
4. **Transaction Capture & Cryptographic e-Sign:** The system prompts the user to state the transaction type (deposit or withdrawal) and the amount. Because non-literate users may not have a handwritten signature and Aadhaar does not store visual signature images, the thumbprint authentication itself generates a legally valid cryptographic Aadhaar e-Sign verification stamp (with a unique Transaction Reference ID and timestamp) instead of requiring a handwritten signature.
5. **Automated Slip Generation:** The kiosk immediately prints a physical, ready-to-submit transaction slip containing the verified account number, transaction details, cryptographic e-Sign verification stamp, and timestamp, completing the self-service workflow.

**Architecture & Scalability (Dual-Mode Design)**

* **Mock Mode (Prototype):** Uses a simulated biometric HTTP server and mock database payloads to validate the end-to-end voice logic, interrupt handling, and slip generation without hardware dependencies.
* **Live Mode (Production-Ready):** Designed with a modular configuration toggle to seamlessly connect with UIDAI-certified L1 fingerprint scanners and live core banking APIs.
</p>