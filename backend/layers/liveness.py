"""
Layer 1: Smart Liveness Detection
- Micro-motion detection (primary photo spoof detector)
- Texture analysis (secondary)
- rPPG blood flow
- Screen glare + frame duplicate detection
- Cryptographic nonce (anti-replay)

CALIBRATION NOTES:
  motion threshold  : 0.4  (was 0.8 — too aggressive, flagged real users)
  texture threshold : 3.5  (was 5.0 — webcam compression reduces texture score)
  Both must fail simultaneously for HARD GATE (AND logic, not OR)
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
    PRIMARY photo spoof detector.
    Photos/screens = near-zero motion. Real faces = always some movement.

    CALIBRATED thresholds (tested on real webcam footage):
      is_static = mean_motion < 0.4 AND variance < 0.3
      (lowered from 0.8/0.5 to reduce false positives on real users)
    """
    if len(frames) < 10:
        return to_python({"motion_score": 0.0, "is_static": True,
                          "spoof_risk": 100, "detail": "Too few frames"})

    diffs = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    for frame in frames[1:]:
        curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        diffs.append(float(np.mean(np.abs(curr - prev))))
        prev = curr

    mean_motion    = float(np.mean(diffs))
    motion_variance = float(np.var(diffs))

    # CALIBRATED: real users moving slowly still show > 0.4 mean motion
    # Photos show < 0.2 even with camera shake
    is_static  = mean_motion < 0.4 and motion_variance < 0.3
    spoof_risk = max(0, min(100, int((1.0 - min(mean_motion / 2.0, 1.0)) * 100)))

    return to_python({
        "motion_score":    round(mean_motion, 3),
        "motion_variance": round(motion_variance, 4),
        "is_static":       is_static,
        "spoof_risk":      spoof_risk,
        "detail": f"Motion={mean_motion:.3f} — {'STATIC (photo/screen)' if is_static else 'movement detected'}",
    })


def detect_texture_liveness(frames: List[np.ndarray]) -> dict:
    """
    SECONDARY spoof detector.
    Printed photos have flat uniform texture. Real skin has micro-texture.

    CALIBRATED threshold: 3.5 (was 5.0)
    Webcam-compressed video of real skin typically scores 4–12.
    Printed photo held to webcam typically scores 1–3.
    """
    texture_scores = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi  = gray[h//4: 3*h//4, w//4: 3*w//4]
        kernel  = np.ones((8, 8), np.float32) / 64
        mean_sq = cv2.filter2D(roi.astype(np.float32)**2, -1, kernel)
        mean    = cv2.filter2D(roi.astype(np.float32),    -1, kernel)
        local_var = mean_sq - mean**2
        texture_scores.append(float(np.mean(np.sqrt(np.maximum(local_var, 0)))))

    avg_texture = float(np.mean(texture_scores)) if texture_scores else 0
    is_flat     = avg_texture < 3.5   # CALIBRATED (was 5.0)

    return to_python({
        "texture_score": round(avg_texture, 2),
        "is_flat":       is_flat,
        "detail": f"Texture={avg_texture:.1f} — {'FLAT (photo/screen)' if is_flat else 'natural skin'}",
    })


def detect_rppg_signal(frames: List[np.ndarray]) -> dict:
    if len(frames) < 20:
        return to_python({"score": 0, "is_real": False, "bpm": 0.0,
                          "snr": 0.0, "detail": "Too few frames for rPPG"})

    green_means = []
    for frame in frames:
        h, w = frame.shape[:2]
        roi  = frame[h//4: 3*h//4, w//4: 3*w//4]
        green_means.append(float(np.mean(roi[:, :, 1])))

    signal = np.array(green_means) - np.mean(green_means)
    fft    = np.abs(np.fft.rfft(signal))
    freqs  = np.fft.rfftfreq(len(signal), d=1.0/30)

    hr_band     = (freqs >= 0.75) & (freqs <= 3.0)
    hr_power    = np.sum(fft[hr_band]**2)
    noise_power = np.sum(fft[~hr_band]**2) + 1e-6
    snr         = float(hr_power / noise_power)

    bpm = 0.0
    if hr_band.any() and fft[hr_band].max() > 0:
        bpm = float(freqs[hr_band][np.argmax(fft[hr_band])] * 60)

    is_real = snr > 0.12 and 45 <= bpm <= 180   # slightly relaxed SNR threshold
    score   = min(100, int(snr * 120)) if is_real else max(0, int(snr * 40))

    return to_python({
        "score": score, "is_real": is_real, "bpm": round(bpm, 1), "snr": round(snr, 3),
        "detail": f"rPPG BPM={bpm:.0f} SNR={snr:.3f} — {'pulse detected' if is_real else 'no pulse'}",
    })


def detect_screen_glare(frames: List[np.ndarray]) -> dict:
    glare_scores = []
    for frame in frames[::5]:
        hsv        = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        glare_mask = (hsv[:, :, 2] > 220) & (hsv[:, :, 1] < 30)
        glare_scores.append(float(np.sum(glare_mask) / glare_mask.size))
    avg_glare = float(np.mean(glare_scores)) if glare_scores else 0
    is_screen = avg_glare > 0.05   # slightly raised from 0.04 to reduce false positives
    return to_python({
        "glare_ratio": round(avg_glare, 4), "is_screen": is_screen,
        "detail": f"Glare={avg_glare:.2%} — {'screen detected' if is_screen else 'normal'}",
    })


def detect_frame_duplicates(frames: List[np.ndarray]) -> dict:
    if len(frames) < 10:
        return to_python({"is_replay": False, "duplicate_ratio": 0.0,
                          "detail": "Insufficient frames"})

    def phash(frame):
        small = cv2.resize(frame, (16, 16))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return (gray > gray.mean()).flatten()

    hashes    = [phash(f) for f in frames[::3]]
    dups      = sum(float(np.mean(hashes[i] == hashes[i-1])) > 0.97
                    for i in range(1, len(hashes)))
    dup_ratio = float(dups) / max(len(hashes) - 1, 1)
    is_replay = dup_ratio > 0.5

    return to_python({
        "duplicate_ratio": round(dup_ratio, 3), "is_replay": is_replay,
        "detail": f"Duplicate ratio={dup_ratio:.1%} — {'REPLAY DETECTED' if is_replay else 'normal'}",
    })


def detect_low_light(frames: List[np.ndarray]) -> dict:
    vals = [float(np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))) for f in frames[::5]]
    avg  = float(np.mean(vals)) if vals else 0
    return to_python({
        "avg_brightness": round(avg, 1),
        "is_too_dark":    avg < 25,
        "is_too_bright":  avg > 235,
        "detail": f"Brightness={avg:.0f}/255 — {'TOO DARK' if avg < 25 else 'TOO BRIGHT' if avg > 235 else 'normal'}",
    })


def analyze_liveness(frames: List[np.ndarray], nonce_valid: bool) -> dict:
    # ── Hard gate: invalid nonce ───────────────────────────────────────────
    if not nonce_valid:
        return to_python({"score": 0, "status": "FAIL", "spoof_risk": 100,
                          "detail": "Session nonce invalid — replay attack blocked",
                          "signals": {}})

    # ── Hard gate: unusable lighting ──────────────────────────────────────
    lighting = detect_low_light(frames)
    if lighting["is_too_dark"] or lighting["is_too_bright"]:
        return to_python({"score": 5, "status": "FAIL", "spoof_risk": 70,
                          "detail": f"Lighting check failed: {lighting['detail']}",
                          "signals": {"lighting": lighting}})

    # ── Run all signals ────────────────────────────────────────────────────
    motion  = detect_micro_motion(frames)
    texture = detect_texture_liveness(frames)
    rppg    = detect_rppg_signal(frames)
    glare   = detect_screen_glare(frames)
    replay  = detect_frame_duplicates(frames)

    # ── Hard gate: replay attack ───────────────────────────────────────────
    if replay["is_replay"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 98,
            "detail": "VIDEO REPLAY DETECTED — duplicate frames",
            "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                        "glare": glare, "replay": replay, "lighting": lighting},
        })

    # ── Hard gate: photo spoof (BOTH motion AND texture must fail) ─────────
    # Using AND logic — prevents false positives on real users with slow movement
    if motion["is_static"] and texture["is_flat"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 92,
            "detail": "PHOTO SPOOF DETECTED — static image with flat texture",
            "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                        "glare": glare, "replay": replay, "lighting": lighting},
        })

    # ── Weighted scoring ───────────────────────────────────────────────────
    score = 0
    if not motion["is_static"]:         score += 35  # strongest signal
    if not texture["is_flat"]:          score += 20  # secondary
    if rppg.get("is_real", False):      score += 25  # rPPG
    if not glare.get("is_screen"):      score += 10
    if not replay["is_replay"]:         score += 10

    spoof_risk = max(0, 100 - score)
    status     = "PASS" if score >= 65 else ("WARN" if score >= 40 else "FAIL")

    return to_python({
        "score": score, "status": status, "spoof_risk": spoof_risk,
        "signals": {"motion": motion, "texture": texture, "rppg": rppg,
                    "glare": glare, "replay": replay, "lighting": lighting},
        "detail": f"Liveness {score}/100 — {status} (spoof risk: {spoof_risk}%)",
    })
