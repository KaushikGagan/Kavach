# 🛡️ KAVACH — AI-Powered Deepfake-Proof KYC System

> Multi-layer identity verification that defeats deepfakes, photo spoofs, video replays, and bot attacks.

![KAVACH](https://img.shields.io/badge/KAVACH-v2.0-8b5cf6?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-06b6d4?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18-00f5a0?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-f59e0b?style=for-the-badge&logo=fastapi)

---

## 🎯 What is KAVACH?

KAVACH is a production-grade KYC (Know Your Customer) verification system that uses **5 independent AI security layers** to detect and block identity fraud — including deepfakes, photo spoofs, video replays, and automated bots.

Unlike systems that rely on a single ML model, KAVACH combines multiple weak signals into an unbreakable chain. Fraud must defeat **all 5 layers simultaneously** — statistically near impossible.

---

## 🔐 5-Layer Security Architecture

| Layer | Technology | Weight |
|---|---|---|
| **Liveness Detection** | rPPG blood flow + random challenge-response + screen glare detection | 30% |
| **Face Matching** | ArcFace deep identity verification (DeepFace) | 30% |
| **Deepfake Detection** | FFT frequency artifacts + landmark jitter + optical flow + facial warping | 25% |
| **Behavioral Analysis** | Device fingerprint + IP anomaly + timing analysis | 15% |
| **Risk Scoring Engine** | Weighted fusion + hard gates + explainable AI verdict | — |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Start the Backend
```bash
cd backend
pip install fastapi uvicorn python-multipart opencv-python numpy deepface mediapipe Pillow scipy aiofiles
py -m uvicorn main:app --reload --port 8000
```

### 2. Build the Frontend
```bash
cd kavach-ui
npm install
npm run build
```

### 3. Open the App
Visit **http://localhost:8000** — the backend serves the React UI directly. One server, one URL.

---

## 🧪 Demo Scenarios

The app includes 4 built-in demo scenarios (no camera needed):

| Scenario | Attack Type | Expected Result |
|---|---|---|
| ✅ Real User | Legitimate KYC | **SAFE** |
| 📸 Photo Spoof | Static photo held to camera | **FRAUD** |
| 🔄 Video Replay | Previously recorded session | **FRAUD** |
| 🤖 Deepfake | AI-generated face swap | **FRAUD** |

---

## 🧠 Key Innovations

- **rPPG (Remote Photoplethysmography)** — Detects real heartbeat through webcam green-channel analysis. Screens and photos have zero blood flow signal.
- **Cryptographic Session Nonces** — Each session gets a unique single-use nonce. Replayed videos from old sessions are instantly blocked.
- **FFT Frequency Analysis** — GAN-generated deepfakes leave checkerboard artifacts in frequency domain, invisible to humans but trivially detectable mathematically.
- **Landmark Jitter Tracking** — Real faces have smooth landmark trajectories. Deepfakes show unnatural acceleration spikes.
- **Fail-Closed Design** — Low confidence = SUSPICIOUS, never auto-approve. System fails safe.

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
└── kavach-ui/
    └── src/
        ├── components/      # Glassmorphism UI components
        └── pages/           # KYC flow pages
```

---

## 🎨 UI Design

- **Glassmorphism + Liquid Glass** hybrid design system
- Animated KAVACH shield emblem
- Live face bounding box with neon corner brackets
- Real-time layer-by-layer analysis progress
- Explainable AI verdict dashboard with per-signal breakdown

---

## 📊 Risk Scoring Formula

```
weighted_score = (face_match × 0.30) + (liveness × 0.30) + (deepfake × 0.25) + (behavior × 0.15)

SAFE        → weighted ≥ 75 AND no FAIL layers
SUSPICIOUS  → weighted ≥ 55 AND ≤ 1 FAIL layer
FRAUD       → weighted < 55 OR hard gate triggered

Hard Gates (instant FRAUD regardless of score):
  - Session nonce invalid (replay attack)
  - 3+ deepfake signals triggered simultaneously
  - Blurry/adversarial input detected
```

---

## 🏆 Built For

Hackathon — AI-Powered Fintech Security Track

**Team:** KAVACH
