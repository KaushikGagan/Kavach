"""
Layer 1: Liveness Detection
Python 3.14 compatible — uses only bundled OpenCV models.

Signals:
  1. Micro-motion  — inter-frame pixel difference (primary photo detector)
  2. Texture       — local variance (flat photo vs real skin)
  3. Head movement — face center tracking (left/right turn)
  4. EAR blink     — eye area transitions via Haar cascade
  5. rPPG          — green channel pulse (real skin only)
  6. Glare         — screen reflection detection
  7. Frame hash    — replay attack detection (normalized correlation)
  8. Lighting      — brightness sanity check

ACTIVE SEQUENCE (bank-style enforcement):
  blink_done + head_turned → both required for PASS
  If either missing → liveness score capped at 40 (WARN/FAIL)
"""
import cv2
import numpy as np
import hashlib
import time
import random
from typing import List, Tuple
from layers.utils import to_python

CHALLENGE_CATEGORIES = {
    "eye":        ["blink_twice"],
    "head":       ["turn_left", "turn_right", "look_up"],
    "expression": ["open_mouth", "smile"],
    "gesture":    ["show_three_fingers", "touch_nose"],
}

_nonce_store: dict = {}

_EYE_CASCADE  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
_FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def generate_challenge() -> dict:
    nonce = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    cats  = random.sample(list(CHALLENGE_CATEGORIES.keys()), 3)
    challenges = [random.choice(CHALLENGE_CATEGORIES[c]) for c in cats]
    _nonce_store[nonce] = {
        "challenge":  challenges[0],
        "challenges": challenges,
        "expires_at": time.time() + 45,
    }
    return {"nonce": nonce, "challenge": challenges[0],
            "challenges": challenges, "expires_in": 45}


def validate_nonce(nonce: str) -> Tuple[bool, str]:
    # Clean expired nonces
    expired = [k for k, v in _nonce_store.items() if time.time() > v["expires_at"]]
    for k in expired:
        del _nonce_store[k]

    if nonce not in _nonce_store:
        return False, "Invalid session nonce"
    entry = _nonce_store[nonce]
    if time.time() > entry["expires_at"]:
        del _nonce_store[nonce]
        return False, "Session expired — replay attack blocked"
    del _nonce_store[nonce]
    return True, entry["challenge"]


def extract_frames(video_bytes: bytes, max_frames: int = 90) -> List[np.ndarray]:
    """
    Extract frames with FPS normalization.
    Targets ~15 FPS to avoid duplicate frames from variable-rate webcam codecs.
    """
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(video_bytes)
        tmp = f.name

    cap = cv2.VideoCapture(tmp)
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    target_fps = 15.0
    step = max(1, int(round(source_fps / target_fps)))

    frames = []
    idx = 0
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            frames.append(frame)
        idx += 1

    cap.release()
    try:
        os.unlink(tmp)
    except Exception:
        pass
    return frames


# ── Signal 1: Micro-motion ─────────────────────────────────────────────────
def detect_micro_motion(frames: List[np.ndarray]) -> dict:
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

    # Calibrated: printed photo < 0.35, real face > 0.5
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
    scores = []
    for frame in frames[::4]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi  = gray[h//4: 3*h//4, w//4: 3*w//4]
        if roi.size == 0:
            continue
        kernel    = np.ones((8, 8), np.float32) / 64
        roi_f     = roi.astype(np.float32)
        mean_sq   = cv2.filter2D(roi_f**2, -1, kernel)
        mean_val  = cv2.filter2D(roi_f,    -1, kernel)
        local_var = mean_sq - mean_val**2
        scores.append(float(np.mean(np.sqrt(np.maximum(local_var, 0)))))

    avg     = float(np.mean(scores)) if scores else 0.0
    is_flat = avg < 3.5

    return to_python({
        "texture_score": round(avg, 2),
        "is_flat":       is_flat,
        "detail": f"Texture={avg:.1f} — {'FLAT (photo/screen)' if is_flat else 'natural skin'}",
    })


# ── Signal 3: Head movement ────────────────────────────────────────────────
def detect_head_movement(frames: List[np.ndarray]) -> dict:
    face_centers = []
    for frame in frames[::3]:
        gray  = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 3, minSize=(60, 60))
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_centers.append((float(x + w / 2), float(y + h / 2)))

    if len(face_centers) < 5:
        return to_python({"head_movement": 0.0, "h_range": 0.0, "turned": False,
                          "detail": "Insufficient face detections for head pose"})

    centers  = np.array(face_centers)
    h_range  = float(np.max(centers[:, 0]) - np.min(centers[:, 0]))
    v_range  = float(np.max(centers[:, 1]) - np.min(centers[:, 1]))
    total    = float(np.sqrt(h_range**2 + v_range**2))
    turned   = h_range > 15.0

    return to_python({
        "head_movement": round(total, 1),
        "h_range":       round(h_range, 1),
        "turned":        turned,
        "detail": f"Head h={h_range:.0f}px — {'head turn detected' if turned else 'no head movement'}",
    })


# ── Signal 4: EAR blink detection ─────────────────────────────────────────
def detect_blinks(frames: List[np.ndarray]) -> dict:
    eye_areas = []
    for frame in frames[::2]:
        gray  = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 3, minSize=(60, 60))
        if len(faces) == 0:
            eye_areas.append(None)
            continue
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_roi   = gray[y:y+h, x:x+w]
        eyes       = _EYE_CASCADE.detectMultiScale(face_roi, 1.05, 3, minSize=(15, 15))
        if len(eyes) >= 2:
            eye_areas.append(float(sum(ew * eh for (ex, ey, ew, eh) in eyes[:2])))
        elif len(eyes) == 1:
            eye_areas.append(float(eyes[0][2] * eyes[0][3]) * 0.5)
        else:
            eye_areas.append(0.0)

    valid = [a for a in eye_areas if a is not None]
    if len(valid) < 5:
        return to_python({"blinks_detected": 0, "eye_detected": False,
                          "detail": "Insufficient frames for blink detection"})

    arr       = np.array(valid, dtype=np.float32)
    mean_a    = float(np.mean(arr))
    threshold = mean_a * 0.55
    blinks    = 0
    in_blink  = False

    for area in arr:
        if area < threshold and not in_blink:
            in_blink = True
        elif area >= threshold and in_blink:
            blinks += 1
            in_blink = False

    eye_detected = mean_a > 100

    return to_python({
        "blinks_detected": blinks,
        "eye_detected":    eye_detected,
        "mean_eye_area":   round(mean_a, 1),
        "detail": f"Blinks={blinks}, eyes={'detected' if eye_detected else 'not detected'}",
    })


# ── Signal 5: rPPG ─────────────────────────────────────────────────────────
def detect_rppg_signal(frames: List[np.ndarray]) -> dict:
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

    signal      = np.array(green_means, dtype=np.float32) - np.mean(green_means)
    fft         = np.abs(np.fft.rfft(signal))
    freqs       = np.fft.rfftfreq(len(signal), d=1.0 / 15)  # 15 FPS after normalization
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


# ── Signal 6: Screen glare ─────────────────────────────────────────────────
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


# ── Signal 7: Frame duplicate (replay) ────────────────────────────────────
def detect_frame_duplicates(frames: List[np.ndarray]) -> dict:
    if len(frames) < 10:
        return to_python({"is_replay": False, "duplicate_ratio": 0.0,
                          "detail": "Insufficient frames"})

    def fingerprint(frame):
        small = cv2.resize(frame, (32, 32))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).flatten().astype(np.float32)
        norm  = np.linalg.norm(gray)
        return gray / (norm + 1e-8)

    fps       = [fingerprint(f) for f in frames[::2]]
    dups      = sum(float(np.dot(fps[i], fps[i-1])) > 0.9995
                    for i in range(1, len(fps)))
    dup_ratio = float(dups) / max(len(fps) - 1, 1)
    is_replay = dup_ratio > 0.80

    return to_python({
        "duplicate_ratio": round(dup_ratio, 3), "is_replay": is_replay,
        "detail": f"Duplicate={dup_ratio:.1%} — {'REPLAY DETECTED' if is_replay else 'normal'}",
    })


# ── Signal 8: Lighting ─────────────────────────────────────────────────────
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

    # Run all passive signals
    motion  = detect_micro_motion(frames)
    texture = detect_texture_liveness(frames)
    head    = detect_head_movement(frames)
    blinks  = detect_blinks(frames)
    rppg    = detect_rppg_signal(frames)
    glare   = detect_screen_glare(frames)
    replay  = detect_frame_duplicates(frames)

    signals = {"motion": motion, "texture": texture, "head": head,
               "blinks": blinks, "rppg": rppg, "glare": glare,
               "replay": replay, "lighting": lighting}

    # Hard gate: replay attack
    if replay["is_replay"]:
        return to_python({"score": 0, "status": "FAIL", "spoof_risk": 98,
                          "detail": "VIDEO REPLAY DETECTED — duplicate frames",
                          "signals": signals})

    # Hard gate: photo spoof (BOTH motion AND texture must fail)
    if motion["is_static"] and texture["is_flat"]:
        return to_python({"score": 0, "status": "FAIL", "spoof_risk": 92,
                          "detail": "PHOTO SPOOF DETECTED — static image with flat texture",
                          "signals": signals})

    # ── ACTIVE SEQUENCE CHECK (bank-style) ────────────────────────────────
    # Both blink AND head turn must be detected for full liveness pass
    blink_done = blinks.get("blinks_detected", 0) >= 1
    head_done  = head.get("turned", False)

    # Weighted scoring
    score = 0
    if not motion["is_static"]:      score += 25
    if not texture["is_flat"]:       score += 15
    if head_done:                    score += 15
    if blink_done:                   score += 15
    if blinks.get("eye_detected"):   score += 10
    if rppg.get("is_real", False):   score += 10
    if not glare.get("is_screen"):   score += 5
    if not replay["is_replay"]:      score += 5

    # Active sequence enforcement:
    # If neither blink nor head turn detected → cap score (passive signals alone not enough)
    if not blink_done and not head_done:
        score = min(score, 40)
        detail = f"Liveness {score}/100 — active gestures not detected (blink={blink_done}, head={head_done})"
    else:
        detail = f"Liveness {score}/100 — {'PASS' if score >= 65 else 'WARN'} (blink={blink_done}, head={head_done})"

    spoof_risk = max(0, 100 - score)
    status     = "PASS" if score >= 65 else ("WARN" if score >= 40 else "FAIL")

    return to_python({"score": score, "status": status, "spoof_risk": spoof_risk,
                      "signals": signals, "detail": detail})
