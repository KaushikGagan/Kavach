# 🛡️ KAVACH — AI-Powered Deepfake-Proof KYC System

> Multi-layer identity verification that defeats deepfakes, photo spoofs, video replays, and bot attacks.

![KAVACH](https://img.shields.io/badge/KAVACH-v2.0-8b5cf6?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-06b6d4?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18-00f5a0?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-f59e0b?style=for-the-badge&logo=fastapi)

---

## 🚀 Quick Start (After Cloning)

### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)

### Option A — One Click (Windows)
Just double-click **`setup_and_run.bat`** — it installs everything, builds the UI, and starts the server automatically.

### Option B — Manual Steps

**Step 1: Install Python dependencies**
```bash
cd backend
pip install fastapi uvicorn python-multipart opencv-python numpy Pillow scipy aiofiles
```

**Step 2: Build the React frontend**
```bash
cd kavach-ui
npm install
npm run build
```

**Step 3: Start the server**
```bash
cd backend
py -m uvicorn main:app --reload --port 8000
```

**Step 4: Open the app**

Visit **http://localhost:8000** in your browser.

> ⚠️ You must run `npm run build` after cloning — the build folder is not included in the repo.

---

## 🧪 Demo Scenarios (No Camera Needed)

Click any scenario on the right panel to instantly see results:

| Scenario | Attack Type | Result |
|---|---|---|
| ✅ Real User | Legitimate KYC | **SAFE** |
| 📸 Photo Spoof | Static photo attack | **FRAUD** |
| 🔄 Video Replay | Replay attack | **FRAUD** |
| 🤖 Deepfake | AI-generated face | **FRAUD** |

---

## 🔐 5-Layer Security Architecture

| Layer | Technology | Weight |
|---|---|---|
| **Liveness Detection** | rPPG blood flow + challenge-response + glare | 30% |
| **Face Matching** | ArcFace deep identity verification | 30% |
| **Deepfake Detection** | FFT + landmark jitter + optical flow | 25% |
| **Behavioral Analysis** | Device + IP + timing anomaly | 15% |
| **Risk Scoring Engine** | Weighted fusion + hard gates + explainable AI | — |

---

## 📁 Project Structure

```
KAVACH/
├── backend/
│   ├── layers/
│   │   ├── liveness.py      # Layer 1: rPPG + challenge + glare
│   │   ├── face_match.py    # Layer 2: ArcFace identity matching
│   │   ├── deepfake.py      # Layer 3: Hybrid deepfake detection
│   │   ├── behavior.py      # Layer 4: Behavioral context
│   │   └── risk_engine.py   # Layer 5: Weighted risk scoring
│   └── main.py              # FastAPI unified server
├── kavach-ui/
│   └── src/
│       ├── components/      # Glassmorphism UI components
│       └── pages/           # KYC flow pages
└── setup_and_run.bat        # One-click Windows setup
```

---

## 📊 Risk Scoring Formula

```
weighted = (face_match × 0.30) + (liveness × 0.30) + (deepfake × 0.25) + (behavior × 0.15)

SAFE        → weighted ≥ 75 AND no FAIL layers
SUSPICIOUS  → weighted ≥ 55 AND ≤ 1 FAIL layer
FRAUD       → weighted < 55 OR hard gate triggered

Hard Gates (instant FRAUD):
  - Session nonce invalid (replay attack)
  - 3+ deepfake signals triggered simultaneously
  - Blurry/adversarial input detected
```

---

## 🏆 Built For

Hackathon — AI-Powered Fintech Security Track · **Team KAVACH**
