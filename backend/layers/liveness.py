"""
Layer 1: Smart Liveness Detection
- rPPG blood flow (anti-photo/screen)
- Micro-motion detection (static image = FAIL)
- Texture variance (flat printed photo = FAIL)
- Screen glare detection
- Frame duplicate detection (replay)
- Random challenge-response with nonce
"""
import cv2
import numpy as np
import hashlib
import time
import random
from typing import List, Tuple
from layers.utils import to_python

CHALLENGES = [
    "blink_twice", "turn_left", "turn_right", "open_mouth",
    "look_up", "show_three_fingers", "touch_nose", "smile",
]

_nonce_store: dict = {}


def generate_challenge() -> dict:
    nonce = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    challenge = random.choice(CHALLENGES)
    _nonce_store[nonce] = {"challenge": challenge, "expires_at": time.time() + 30}
    return {"nonce": nonce, "challenge": challenge, "expires_in": 30}


def validate_nonce(nonce: str) -> Tuple[bool, str]:
    if nonce not in _nonce_store:
        return False, "Invalid session nonce"
    entry = _nonce_store[nonce]
    if time.time() > entry["expires_at"]:
        del _nonce_store[nonce]
        return False, "Session expired (>30s) — replay attack blocked"
    del _nonce_store[nonce]
    return True, entry["challenge"]


def extract_frames(video_bytes: bytes, max_frames: int = 60) -> List[np.ndarray]:
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name
    cap = cv2.VideoCapture(tmp_path)
    frames = []
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    os.unlink(tmp_path)
    return frames


def detect_micro_motion(frames: List[np.ndarray]) -> dict:
    """
    CRITICAL: Photos and static screens have near-zero inter-frame motion.
    Real faces always have micro-movements (breathing, muscle tremors).
    This is the PRIMARY photo spoof detector.
    """
    if len(frames) < 10:
        return to_python({"motion_score": 0, "is_static": True, "spoof_risk": 100, "detail": "Too few frames"})

    diffs = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    for frame in frames[1:]:
        curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        diff = np.mean(np.abs(curr - prev))
        diffs.append(diff)
        prev = curr

    mean_motion = float(np.mean(diffs))
    motion_variance = float(np.var(diffs))

    # Photo/static image: mean_motion < 0.8, variance near 0
    # Real face: mean_motion > 1.5 due to natural micro-movements
    is_static = mean_motion < 0.8 and motion_variance < 0.5

    spoof_risk = max(0, min(100, int((1.0 - min(mean_motion / 3.0, 1.0)) * 100)))

    return to_python({
        "motion_score": round(mean_motion, 3),
        "motion_variance": round(motion_variance, 4),
        "is_static": is_static,
        "spoof_risk": spoof_risk,
        "detail": f"Motion={mean_motion:.3f} var={motion_variance:.4f} — {'STATIC IMAGE DETECTED' if is_static else 'natural movement'}",
    })


def detect_texture_liveness(frames: List[np.ndarray]) -> dict:
    """
    Printed photos and screens have uniform, flat texture.
    Real skin has complex micro-texture (pores, fine lines).
    Uses LBP-inspired local variance analysis.
    """
    texture_scores = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi = gray[h//4: 3*h//4, w//4: 3*w//4]

        # Local standard deviation map — real skin has high local variance
        kernel = np.ones((8, 8), np.float32) / 64
        mean_sq = cv2.filter2D(roi.astype(np.float32)**2, -1, kernel)
        mean = cv2.filter2D(roi.astype(np.float32), -1, kernel)
        local_var = mean_sq - mean**2
        texture_scores.append(float(np.mean(np.sqrt(np.maximum(local_var, 0)))))

    avg_texture = float(np.mean(texture_scores)) if texture_scores else 0
    # Real skin: texture > 8. Printed photo: texture < 5. Screen: texture < 4.
    is_flat = avg_texture < 5.0

    return to_python({
        "texture_score": round(avg_texture, 2),
        "is_flat": is_flat,
        "detail": f"Texture score {avg_texture:.1f} — {'FLAT TEXTURE (photo/screen)' if is_flat else 'natural skin texture'}",
    })


def detect_rppg_signal(frames: List[np.ndarray]) -> dict:
    if len(frames) < 20:
        return to_python({"score": 0, "is_real": False, "bpm": 0.0, "snr": 0.0, "detail": "Too few frames for rPPG"})

    green_means = []
    for frame in frames:
        h, w = frame.shape[:2]
        roi = frame[h//4: 3*h//4, w//4: 3*w//4]
        green_means.append(float(np.mean(roi[:, :, 1])))

    signal = np.array(green_means) - np.mean(green_means)
    fft = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0/30)

    hr_band = (freqs >= 0.75) & (freqs <= 3.0)
    hr_power = np.sum(fft[hr_band]**2)
    noise_power = np.sum(fft[~hr_band]**2) + 1e-6
    snr = hr_power / noise_power

    bpm = 0.0
    if hr_band.any() and fft[hr_band].max() > 0:
        bpm = float(freqs[hr_band][np.argmax(fft[hr_band])] * 60)

    is_real = snr > 0.15 and 45 <= bpm <= 180
    score = min(100, int(snr * 120)) if is_real else max(0, int(snr * 40))

    return to_python({
        "score": score, "is_real": is_real, "bpm": round(bpm, 1), "snr": round(snr, 3),
        "detail": f"rPPG BPM={bpm:.0f}, SNR={snr:.3f} — {'pulse detected' if is_real else 'no pulse — possible photo/screen'}",
    })


def detect_screen_glare(frames: List[np.ndarray]) -> dict:
    glare_scores = []
    for frame in frames[::5]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        glare_mask = (hsv[:, :, 2] > 220) & (hsv[:, :, 1] < 30)
        glare_scores.append(np.sum(glare_mask) / glare_mask.size)
    avg_glare = float(np.mean(glare_scores)) if glare_scores else 0
    is_screen = avg_glare > 0.04
    return to_python({
        "glare_ratio": round(avg_glare, 4), "is_screen": is_screen,
        "detail": f"Glare {avg_glare:.2%} — {'screen detected' if is_screen else 'normal'}",
    })


def detect_frame_duplicates(frames: List[np.ndarray]) -> dict:
    if len(frames) < 10:
        return to_python({"is_replay": False, "duplicate_ratio": 0.0, "detail": "Insufficient frames"})

    def phash(frame):
        small = cv2.resize(frame, (16, 16))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return (gray > gray.mean()).flatten()

    hashes = [phash(f) for f in frames[::3]]
    dups = sum(np.mean(hashes[i] == hashes[i-1]) > 0.97 for i in range(1, len(hashes)))
    dup_ratio = dups / max(len(hashes) - 1, 1)
    is_replay = dup_ratio > 0.5
    return to_python({
        "duplicate_ratio": round(dup_ratio, 3), "is_replay": is_replay,
        "detail": f"Duplicate ratio {dup_ratio:.1%} — {'REPLAY DETECTED' if is_replay else 'normal'}",
    })


def detect_low_light(frames: List[np.ndarray]) -> dict:
    vals = [float(np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))) for f in frames[::5]]
    avg = float(np.mean(vals)) if vals else 0
    return to_python({
        "avg_brightness": round(avg, 1),
        "is_too_dark": avg < 30,
        "is_too_bright": avg > 230,
        "detail": f"Brightness {avg:.0f}/255 — {'TOO DARK' if avg < 30 else 'TOO BRIGHT' if avg > 230 else 'normal'}",
    })


def analyze_liveness(frames: List[np.ndarray], nonce_valid: bool) -> dict:
    if not nonce_valid:
        return to_python({"score": 0, "status": "FAIL", "spoof_risk": 100,
                "detail": "Session nonce invalid — replay attack blocked", "signals": {}})

    lighting = detect_low_light(frames)
    if lighting["is_too_dark"] or lighting["is_too_bright"]:
        return to_python({"score": 5, "status": "FAIL", "spoof_risk": 80,
                "detail": f"Lighting check failed: {lighting['detail']}",
                "signals": {"lighting": lighting}})

    # Run all signals
    motion  = detect_micro_motion(frames)
    texture = detect_texture_liveness(frames)
    rppg    = detect_rppg_signal(frames)
    glare   = detect_screen_glare(frames)
    replay  = detect_frame_duplicates(frames)

    # ── HARD GATE: Photo spoof detection ──────────────────────────────────
    # If BOTH motion is static AND texture is flat → definite photo attack
    if motion["is_static"] and texture["is_flat"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 95,
            "detail": "PHOTO SPOOF DETECTED — static image with flat texture",
            "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                        "glare": glare, "replay": replay, "lighting": lighting},
        })

    if replay["is_replay"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 98,
            "detail": "VIDEO REPLAY DETECTED — duplicate frames",
            "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                        "glare": glare, "replay": replay, "lighting": lighting},
        })

    # ── Weighted scoring ───────────────────────────────────────────────────
    score = 0
    if not motion["is_static"]:       score += 30   # motion is strongest signal
    if not texture["is_flat"]:        score += 20   # texture second
    if rppg.get("is_real", False):    score += 30   # rPPG third
    if not glare.get("is_screen"):    score += 10
    if not replay["is_replay"]:       score += 10

    # Spoof risk = inverse of liveness confidence
    spoof_risk = max(0, 100 - score)
    status = "PASS" if score >= 70 else ("WARN" if score >= 45 else "FAIL")

    return to_python({
        "score": score, "status": status, "spoof_risk": spoof_risk,
        "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                    "glare": glare, "replay": replay, "lighting": lighting},
        "detail": f"Liveness {score}/100 — {status} (spoof risk: {spoof_risk}%)",
    })
