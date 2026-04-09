"""
KAVACH — Unified Server
FastAPI serves both the API and the React frontend from one process.
Visit: http://localhost:8000
"""
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from layers.liveness import generate_challenge, validate_nonce, extract_frames, analyze_liveness
from layers.face_match import match_faces
from layers.deepfake import analyze_deepfake
from layers.behavior import analyze_behavior
from layers.risk_engine import compute_risk_score

# Path to React production build
UI_BUILD = Path(__file__).parent.parent / "kavach-ui" / "build"

app = FastAPI(title="KAVACH KYC API", version="2.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session store: nonce -> start_time
_session_times: dict = {}


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "KAVACH KYC", "version": "2.0"}


@app.get("/challenge")
async def get_challenge():
    challenge_data = generate_challenge()
    _session_times[challenge_data["nonce"]] = time.time()
    return challenge_data


@app.post("/verify")
async def verify_kyc(
    request: Request,
    video: UploadFile = File(...),
    id_image: str = Form(...),
    nonce: str = Form(...),
    device_id: Optional[str] = Form(None),
):
    submission_time = time.time()
    session_start = _session_times.pop(nonce, submission_time - 10)

    nonce_valid, _ = validate_nonce(nonce)

    video_bytes = await video.read()
    frames = extract_frames(video_bytes, max_frames=60)

    if len(frames) < 10:
        return JSONResponse(status_code=400, content={
            "error": "Video too short — minimum 10 frames required",
            "verdict": "FRAUD",
        })

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    liveness_result = analyze_liveness(frames, nonce_valid)
    face_result     = match_faces(id_image, frames)
    deepfake_result = analyze_deepfake(frames)
    behavior_result = analyze_behavior(ip, ua, session_start, submission_time, device_id)

    verdict = compute_risk_score(face_result, liveness_result, deepfake_result, behavior_result)

    return {
        "status": "completed",
        "processing_time_ms": round((time.time() - submission_time) * 1000),
        **verdict,
    }


@app.post("/demo/{scenario}")
async def demo_scenario(scenario: str):
    scenarios = {
        "real_user": {
            "face_match": {"score": 91, "status": "PASS", "similarity": 91.2, "detail": "ArcFace similarity 91.2% — identity confirmed"},
            "liveness":   {"score": 95, "status": "PASS", "spoof_risk": 5, "detail": "Liveness 95/100 — PASS", "signals": {
                "motion":  {"motion_score": 2.8,  "is_static": False, "spoof_risk": 5,  "detail": "Motion=2.800 — natural movement"},
                "texture": {"texture_score": 12.4, "is_flat": False,  "detail": "Texture 12.4 — natural skin texture"},
                "rppg":    {"score": 88, "is_real": True, "bpm": 72.0, "snr": 0.73, "detail": "rPPG BPM=72 — pulse detected"},
                "glare":   {"glare_ratio": 0.008, "is_screen": False, "detail": "Glare 0.80% — normal"},
                "replay":  {"duplicate_ratio": 0.04, "is_replay": False, "detail": "Duplicate ratio 4% — normal"},
            }},
            "deepfake":   {"score": 94, "status": "PASS", "flags_triggered": 0, "deepfake_probability": 6, "detail": "0/4 deepfake signals triggered — PASS", "signals": {
                "frequency":       {"hf_ratio": 0.41, "is_deepfake": False, "confidence": 41, "detail": "FFT HF ratio 0.410 — frequency normal"},
                "landmark_jitter": {"jitter_score": 0.82, "is_deepfake": False, "confidence": 16, "detail": "Landmark jitter 0.82px/f² — smooth natural motion"},
                "optical_flow":    {"mean_flow": 1.23, "flow_variance": 0.18, "is_suspicious": False, "detail": "Optical flow mean=1.230 — natural motion"},
                "facial_warping":  {"warp_score": 0.06, "is_warped": False, "detail": "Edge density 0.060 — clean boundaries"},
            }},
            "behavior":   {"score": 92, "status": "PASS", "detail": "Behavioral score 92/100 — PASS", "signals": {
                "speed":      {"status": "PASS", "detail": "Completed in 12.3s — normal human timing"},
                "user_agent": {"status": "PASS", "detail": "User-agent appears to be a real browser"},
                "ip":         {"status": "PASS", "detail": "IP appears public"},
                "time":       {"status": "PASS", "detail": "Submission at hour 14 — normal"},
            }},
        },
        "photo_spoof": {
            "face_match": {"score": 78, "status": "PASS", "similarity": 78.4, "detail": "ArcFace similarity 78.4% — identity confirmed"},
            "liveness":   {"score": 0, "status": "FAIL", "spoof_risk": 95, "detail": "PHOTO SPOOF DETECTED — static image with flat texture", "signals": {
                "motion":  {"motion_score": 0.11, "is_static": True,  "spoof_risk": 95, "detail": "Motion=0.110 — STATIC IMAGE DETECTED"},
                "texture": {"texture_score": 3.1,  "is_flat": True,   "detail": "Texture 3.1 — FLAT TEXTURE (photo/screen)"},
                "rppg":    {"score": 5,  "is_real": False, "bpm": 0.0, "snr": 0.02, "detail": "rPPG BPM=0 — no pulse"},
                "glare":   {"glare_ratio": 0.071, "is_screen": True,  "detail": "Glare 7.10% — screen detected"},
                "replay":  {"duplicate_ratio": 0.12, "is_replay": False, "detail": "Duplicate ratio 12% — normal"},
            }},
            "deepfake":   {"score": 70, "status": "PASS", "flags_triggered": 1, "deepfake_probability": 30, "detail": "1/4 deepfake signals triggered — PASS", "signals": {
                "frequency":       {"hf_ratio": 0.45, "is_deepfake": False, "confidence": 45, "detail": "FFT HF ratio 0.450 — frequency normal"},
                "landmark_jitter": {"jitter_score": 0.12, "is_deepfake": False, "confidence": 2,  "detail": "Landmark jitter 0.12px/f² — smooth"},
                "optical_flow":    {"mean_flow": 0.08, "flow_variance": 0.002, "is_suspicious": True,  "detail": "Optical flow mean=0.080 — suspicious (static)"},
                "facial_warping":  {"warp_score": 0.07, "is_warped": False, "detail": "Edge density 0.070 — clean boundaries"},
            }},
            "behavior":   {"score": 85, "status": "PASS", "detail": "Behavioral score 85/100 — PASS", "signals": {
                "speed":      {"status": "PASS", "detail": "Completed in 9.1s — normal human timing"},
                "user_agent": {"status": "PASS", "detail": "User-agent appears to be a real browser"},
                "ip":         {"status": "PASS", "detail": "IP appears public"},
                "time":       {"status": "PASS", "detail": "Submission at hour 11 — normal"},
            }},
        },
        "video_replay": {
            "face_match": {"score": 82, "status": "PASS", "similarity": 82.1, "detail": "ArcFace similarity 82.1% — identity confirmed"},
            "liveness":   {"score": 0, "status": "FAIL", "spoof_risk": 98, "detail": "Session nonce invalid — replay attack blocked", "signals": {}},
            "deepfake":   {"score": 65, "status": "WARN", "flags_triggered": 2, "deepfake_probability": 35, "detail": "2/4 deepfake signals triggered — WARN", "signals": {
                "frequency":       {"hf_ratio": 0.52, "is_deepfake": False, "confidence": 52, "detail": "FFT HF ratio 0.520 — frequency normal"},
                "landmark_jitter": {"jitter_score": 0.31, "is_deepfake": False, "confidence": 6,  "detail": "Landmark jitter 0.31px/f² — smooth"},
                "optical_flow":    {"mean_flow": 0.11, "flow_variance": 0.003, "is_suspicious": True,  "detail": "Optical flow mean=0.110 — suspicious"},
                "facial_warping":  {"warp_score": 0.09, "is_warped": False, "detail": "Edge density 0.090 — clean boundaries"},
            }},
            "behavior":   {"score": 75, "status": "PASS", "detail": "Behavioral score 75/100 — PASS", "signals": {
                "speed":      {"status": "PASS", "detail": "Completed in 7.8s — normal human timing"},
                "user_agent": {"status": "PASS", "detail": "User-agent appears to be a real browser"},
                "ip":         {"status": "WARN", "detail": "IP flags: private/VPN-range IP — possible VPN/proxy"},
                "time":       {"status": "PASS", "detail": "Submission at hour 16 — normal"},
            }},
        },
        "deepfake": {
            "face_match": {"score": 74, "status": "PASS", "similarity": 74.3, "detail": "ArcFace similarity 74.3% — identity confirmed"},
            "liveness":   {"score": 40, "status": "WARN", "spoof_risk": 45, "detail": "Liveness 40/100 — WARN", "signals": {
                "motion":  {"motion_score": 1.2,  "is_static": False, "spoof_risk": 40, "detail": "Motion=1.200 — low movement"},
                "texture": {"texture_score": 7.1,  "is_flat": False,  "detail": "Texture 7.1 — borderline"},
                "rppg":    {"score": 30, "is_real": False, "bpm": 38.0, "snr": 0.09, "detail": "rPPG BPM=38 — no pulse"},
                "glare":   {"glare_ratio": 0.021, "is_screen": False, "detail": "Glare 2.10% — normal"},
                "replay":  {"duplicate_ratio": 0.12, "is_replay": False, "detail": "Duplicate ratio 12% — normal"},
            }},
            "deepfake":   {"score": 18, "status": "FAIL", "flags_triggered": 3, "deepfake_probability": 82, "detail": "3/4 deepfake signals triggered — FAIL", "signals": {
                "frequency":       {"hf_ratio": 0.81, "is_deepfake": True,  "confidence": 81, "detail": "FFT HF ratio 0.810 — GAN artifacts detected"},
                "landmark_jitter": {"jitter_score": 3.74, "is_deepfake": True,  "confidence": 74, "detail": "Landmark jitter 3.74px/f² — unnatural movement"},
                "optical_flow":    {"mean_flow": 0.19, "flow_variance": 0.005, "is_suspicious": True,  "detail": "Optical flow mean=0.190 — suspicious"},
                "facial_warping":  {"warp_score": 0.08, "is_warped": False, "detail": "Edge density 0.080 — clean boundaries"},
            }},
            "behavior":   {"score": 60, "status": "WARN", "detail": "Behavioral score 60/100 — WARN", "signals": {
                "speed":      {"status": "WARN", "detail": "Completed in 6.2s — slightly fast"},
                "user_agent": {"status": "PASS", "detail": "User-agent appears to be a real browser"},
                "ip":         {"status": "WARN", "detail": "IP flags: private/VPN-range IP — possible VPN/proxy"},
                "time":       {"status": "PASS", "detail": "Submission at hour 03 — unusual hours"},
            }},
        },
    }

    if scenario not in scenarios:
        return JSONResponse(status_code=404, content={"error": f"Unknown scenario: {scenario}"})

    s = scenarios[scenario]
    result = compute_risk_score(s["face_match"], s["liveness"], s["deepfake"], s["behavior"])
    return {"status": "demo", "scenario": scenario, "processing_time_ms": 420, **result}


# ── Serve React frontend (must be LAST) ──────────────────────────────────────

if UI_BUILD.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=str(UI_BUILD / "static")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # API routes are already handled above — this catches everything else
        index = UI_BUILD / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/")
    async def no_ui():
        return {"message": "UI build not found. Run: cd kavach-ui && npm run build"}
