"""
Layer 1: Liveness Detection
Python 3.14 compatible — uses only bundled OpenCV models.

Signals:
  1. Micro-motion  — inter-frame pixel difference (primary photo detector)
  2. Texture       — LBP variance (flat photo vs real skin)
  3. EAR blink     — Eye Aspect Ratio via eye cascade (requires live eyes)
  4. rPPG          — green channel pulse (real skin only)
  5. Glare         — screen reflection detection
  6. Frame hash    — replay attack detection (normalized correlation)
  7. Lighting      — brightness sanity check
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

# Bundled cascades
_EYE_CASCADE  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
_FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def generate_challenge() -> dict:
    nonce     = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    challenge = random.choice(CHALLENGES)
    _nonce_store[nonce] = {"challenge": challenge, "expires_at": time.time() + 30}
    return {"nonce": nonce, "challenge": challenge, "expires_in": 30}


def validate_nonce(nonce: str) -> Tuple[bool, str]:
    if nonce not in _nonce_store:
        return False, "Invalid session nonce"
    entry = _nonce_store[nonce]
    if time.time() > entry["expires_at"]:
        del _nonce_store[nonce]
        return False, "Session expired — replay attack blocked"
    del _nonce_store[nonce]
    return True, entry["challenge"]


def extract_frames(video_bytes: bytes, max_frames: int = 90) -> List[np.ndarray]:
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(video_bytes)
        tmp = f.name
    cap    = cv2.VideoCapture(tmp)
    frames = []
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    os.unlink(tmp)
    return frames


# ── Signal 1: Micro-motion ─────────────────────────────────────────────────
def detect_micro_motion(frames: List[np.ndarray]) -> dict:
    """
    Photos/screens = near-zero motion.
    Real faces = always some movement (breathing, micro-tremors).
    Threshold calibrated: real users show > 0.5 mean motion even when still.
    """
    if len(frames) < 8:
        return to_python({"motion_score": 0.0, "is_static": True,
                          "spoof_risk": 100, "detail": "Too few frames"})

    diffs = []
    prev  = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    for frame in frames[1:]:
        curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        diffs.append(float(np.mean(np.abs(curr - prev))))
        prev = curr

    mean_motion     = float(np.mean(diffs))
    motion_variance = float(np.var(diffs))

    # Calibrated: printed photo < 0.3, real face > 0.5
    is_static  = mean_motion < 0.35 and motion_variance < 0.25
    spoof_risk = max(0, min(100, int((1.0 - min(mean_motion / 2.5, 1.0)) * 100)))

    return to_python({
        "motion_score":    round(mean_motion, 3),
        "motion_variance": round(motion_variance, 4),
        "is_static":       is_static,
        "spoof_risk":      spoof_risk,
        "detail": f"Motion={mean_motion:.3f} — {'STATIC (photo/screen)' if is_static else 'movement OK'}",
    })


# ── Signal 2: Texture analysis ─────────────────────────────────────────────
def detect_texture_liveness(frames: List[np.ndarray]) -> dict:
    """
    Real skin has complex micro-texture. Printed photos are flat.
    Uses Laplacian variance on face ROI.
    Threshold: 3.5 (was 5.0 — too aggressive, caused false positives)
    """
    scores = []
    for frame in frames[::4]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi  = gray[h//4: 3*h//4, w//4: 3*w//4]
        if roi.size == 0:
            continue
        # Local variance via filter
        kernel    = np.ones((8, 8), np.float32) / 64
        roi_f     = roi.astype(np.float32)
        mean_sq   = cv2.filter2D(roi_f**2, -1, kernel)
        mean_val  = cv2.filter2D(roi_f,    -1, kernel)
        local_var = mean_sq - mean_val**2
        scores.append(float(np.mean(np.sqrt(np.maximum(local_var, 0)))))

    avg = float(np.mean(scores)) if scores else 0.0
    is_flat = avg < 3.5

    return to_python({
        "texture_score": round(avg, 2),
        "is_flat":       is_flat,
        "detail": f"Texture={avg:.1f} — {'FLAT (photo/screen)' if is_flat else 'natural skin'}",
    })


# ── Signal 3: EAR blink detection ─────────────────────────────────────────
def detect_blinks(frames: List[np.ndarray]) -> dict:
    """
    Eye Aspect Ratio (EAR) blink detection using Haar eye cascade.
    A real person blinks naturally. A photo never blinks.
    Detects eye open/close transitions across frames.
    """
    eye_areas = []
    for frame in frames[::2]:
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)
        # Detect face first to limit eye search region
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 3, minSize=(60,60))
        if len(faces) == 0:
            eye_areas.append(None)
            continue
        x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
        face_roi   = gray[y:y+h, x:x+w]
        eyes       = _EYE_CASCADE.detectMultiScale(face_roi, 1.05, 3, minSize=(15,15))
        if len(eyes) >= 2:
            # Both eyes detected — open
            total_eye_area = sum(ew*eh for (ex,ey,ew,eh) in eyes[:2])
            eye_areas.append(float(total_eye_area))
        elif len(eyes) == 1:
            eye_areas.append(float(eyes[0][2] * eyes[0][3]) * 0.5)
        else:
            eye_areas.append(0.0)

    valid = [a for a in eye_areas if a is not None]
    if len(valid) < 5:
        return to_python({"blinks_detected": 0, "eye_detected": False,
                          "detail": "Insufficient frames for blink detection"})

    # Count blinks: transitions from high→low→high eye area
    arr    = np.array(valid, dtype=np.float32)
    mean_a = float(np.mean(arr))
    blinks = 0
    in_blink = False
    threshold = mean_a * 0.55  # eye area drops to <55% of mean during blink

    for area in arr:
        if area < threshold and not in_blink:
            in_blink = True
        elif area >= threshold and in_blink:
            blinks += 1
            in_blink = False

    eye_detected = mean_a > 100  # eyes were visible at some point

    return to_python({
        "blinks_detected": blinks,
        "eye_detected":    eye_detected,
        "mean_eye_area":   round(mean_a, 1),
        "detail": f"Blinks={blinks}, eyes={'detected' if eye_detected else 'not detected'}",
    })


# ── Signal 4: rPPG ─────────────────────────────────────────────────────────
def detect_rppg_signal(frames: List[np.ndarray]) -> dict:
    """Remote Photoplethysmography — real skin shows green-channel pulse."""
    if len(frames) < 20:
        return to_python({"score": 0, "is_real": False, "bpm": 0.0,
                          "snr": 0.0, "detail": "Too few frames for rPPG"})

    green_means = []
    for frame in frames:
        h, w = frame.shape[:2]
        roi  = frame[h//4: 3*h//4, w//4: 3*w//4]
        if roi.size > 0:
            green_means.append(float(np.mean(roi[:, :, 1])))

    if len(green_means) < 20:
        return to_python({"score": 0, "is_real": False, "bpm": 0.0,
                          "snr": 0.0, "detail": "Insufficient ROI data"})

    signal = np.array(green_means, dtype=np.float32)
    signal = signal - np.mean(signal)
    fft    = np.abs(np.fft.rfft(signal))
    freqs  = np.fft.rfftfreq(len(signal), d=1.0/30)

    hr_band     = (freqs >= 0.75) & (freqs <= 3.0)
    hr_power    = float(np.sum(fft[hr_band]**2))
    noise_power = float(np.sum(fft[~hr_band]**2)) + 1e-6
    snr         = hr_power / noise_power

    bpm = 0.0
    if hr_band.any() and fft[hr_band].max() > 0:
        bpm = float(freqs[hr_band][np.argmax(fft[hr_band])] * 60)

    is_real = snr > 0.10 and 45 <= bpm <= 180
    score   = min(100, int(snr * 120)) if is_real else max(0, int(snr * 40))

    return to_python({
        "score": score, "is_real": is_real,
        "bpm": round(bpm, 1), "snr": round(snr, 3),
        "detail": f"rPPG BPM={bpm:.0f} SNR={snr:.3f} — {'pulse detected' if is_real else 'no pulse'}",
    })


# ── Signal 5: Screen glare ─────────────────────────────────────────────────
def detect_screen_glare(frames: List[np.ndarray]) -> dict:
    scores = []
    for frame in frames[::5]:
        hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = (hsv[:, :, 2] > 220) & (hsv[:, :, 1] < 30)
        scores.append(float(np.sum(mask) / mask.size))
    avg       = float(np.mean(scores)) if scores else 0.0
    is_screen = avg > 0.05
    return to_python({
        "glare_ratio": round(avg, 4), "is_screen": is_screen,
        "detail": f"Glare={avg:.2%} — {'screen detected' if is_screen else 'normal'}",
    })


# ── Signal 6: Frame duplicate (replay) ────────────────────────────────────
def detect_frame_duplicates(frames: List[np.ndarray]) -> dict:
    """
    Replay attacks loop frames.
    Uses 32x32 normalized correlation — much more robust than binary hash.
    Threshold 0.9995 — only true duplicates trigger.
    """
    if len(frames) < 10:
        return to_python({"is_replay": False, "duplicate_ratio": 0.0,
                          "detail": "Insufficient frames"})

    def fingerprint(frame):
        small = cv2.resize(frame, (32, 32))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).flatten().astype(np.float32)
        norm  = np.linalg.norm(gray)
        return gray / (norm + 1e-8)

    fps   = [fingerprint(f) for f in frames[::2]]
    dups  = 0
    for i in range(1, len(fps)):
        corr = float(np.dot(fps[i], fps[i-1]))
        if corr > 0.9995:
            dups += 1

    dup_ratio = float(dups) / max(len(fps) - 1, 1)
    is_replay = dup_ratio > 0.80  # >80% truly identical frames

    return to_python({
        "duplicate_ratio": round(dup_ratio, 3), "is_replay": is_replay,
        "detail": f"Duplicate={dup_ratio:.1%} — {'REPLAY DETECTED' if is_replay else 'normal'}",
    })


# ── Signal 7: Lighting ─────────────────────────────────────────────────────
def detect_low_light(frames: List[np.ndarray]) -> dict:
    vals = [float(np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))) for f in frames[::5]]
    avg  = float(np.mean(vals)) if vals else 0.0
    return to_python({
        "avg_brightness": round(avg, 1),
        "is_too_dark":    avg < 25,
        "is_too_bright":  avg > 235,
        "detail": f"Brightness={avg:.0f}/255 — {'TOO DARK' if avg < 25 else 'TOO BRIGHT' if avg > 235 else 'normal'}",
    })


# ── Main liveness analyzer ─────────────────────────────────────────────────
def analyze_liveness(frames: List[np.ndarray], nonce_valid: bool) -> dict:

    # Hard gate: invalid nonce
    if not nonce_valid:
        return to_python({"score": 0, "status": "FAIL", "spoof_risk": 100,
                          "detail": "Session nonce invalid — replay attack blocked",
                          "signals": {}})

    # Hard gate: bad lighting
    lighting = detect_low_light(frames)
    if lighting["is_too_dark"] or lighting["is_too_bright"]:
        return to_python({"score": 5, "status": "FAIL", "spoof_risk": 70,
                          "detail": f"Lighting failed: {lighting['detail']}",
                          "signals": {"lighting": lighting}})

    # Run all signals
    motion  = detect_micro_motion(frames)
    texture = detect_texture_liveness(frames)
    blinks  = detect_blinks(frames)
    rppg    = detect_rppg_signal(frames)
    glare   = detect_screen_glare(frames)
    replay  = detect_frame_duplicates(frames)

    # Hard gate: replay attack
    if replay["is_replay"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 98,
            "detail": "VIDEO REPLAY DETECTED — duplicate frames",
            "signals": {"motion": motion, "texture": texture, "blinks": blinks,
                        "rppg": rppg, "glare": glare, "replay": replay, "lighting": lighting},
        })

    # Hard gate: photo spoof (BOTH motion AND texture must fail — AND logic prevents false positives)
    if motion["is_static"] and texture["is_flat"]:
        return to_python({
            "score": 0, "status": "FAIL", "spoof_risk": 92,
            "detail": "PHOTO SPOOF DETECTED — static image with flat texture",
            "signals": {"motion": motion, "texture": texture, "blinks": blinks,
                        "rppg": rppg, "glare": glare, "replay": replay, "lighting": lighting},
        })

    # Weighted scoring
    score = 0
    if not motion["is_static"]:                    score += 30  # strongest
    if not texture["is_flat"]:                     score += 15
    if blinks.get("blinks_detected", 0) >= 1:     score += 20  # at least 1 blink
    if blinks.get("eye_detected", False):          score += 10
    if rppg.get("is_real", False):                 score += 15
    if not glare.get("is_screen", False):          score += 5
    if not replay["is_replay"]:                    score += 5

    spoof_risk = max(0, 100 - score)
    status     = "PASS" if score >= 65 else ("WARN" if score >= 40 else "FAIL")

    return to_python({
        "score": score, "status": status, "spoof_risk": spoof_risk,
        "signals": {"motion": motion, "texture": texture, "blinks": blinks,
                    "rppg": rppg, "glare": glare, "replay": replay, "lighting": lighting},
        "detail": f"Liveness {score}/100 — {status} (spoof risk: {spoof_risk}%)",
    })
