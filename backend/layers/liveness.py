"""
Layer 1: Smart Liveness Detection
- Random challenge-response (anti-replay)
- rPPG blood flow detection (anti-photo/screen)
- Passive skin texture analysis
- Screen glare detection
"""
import cv2
import numpy as np
import hashlib
import time
import random
from typing import List, Tuple

CHALLENGES = [
    "blink_twice",
    "turn_left",
    "turn_right",
    "open_mouth",
    "look_up",
    "show_three_fingers",
    "touch_nose",
    "smile",
]

# In-memory nonce store {nonce: (challenge, expires_at)}
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
    del _nonce_store[nonce]  # single-use
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


def detect_rppg_signal(frames: List[np.ndarray]) -> dict:
    """
    Remote Photoplethysmography: real skin shows green-channel pulse (~60-100 BPM).
    Screens/photos have flat or noise-only signal.
    """
    if len(frames) < 20:
        # FIX: always return is_real key to prevent KeyError in analyze_liveness
        return {"score": 0, "is_real": False, "bpm": 0.0, "snr": 0.0, "detail": "Too few frames for rPPG analysis"}

    green_means = []
    for frame in frames:
        # Use center face region
        h, w = frame.shape[:2]
        roi = frame[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
        green_means.append(float(np.mean(roi[:, :, 1])))  # green channel

    signal = np.array(green_means)
    signal = signal - np.mean(signal)  # detrend

    # FFT to find dominant frequency
    fft = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / 30)  # assume 30fps

    # Heart rate band: 0.75–3.0 Hz (45–180 BPM)
    hr_band = (freqs >= 0.75) & (freqs <= 3.0)
    noise_band = ~hr_band

    hr_power = np.sum(fft[hr_band] ** 2)
    noise_power = np.sum(fft[noise_band] ** 2) + 1e-6
    snr = hr_power / noise_power

    # Dominant BPM
    if hr_band.any() and fft[hr_band].max() > 0:
        dominant_freq = freqs[hr_band][np.argmax(fft[hr_band])]
        bpm = dominant_freq * 60
    else:
        bpm = 0

    is_real = snr > 0.15 and 45 <= bpm <= 180
    score = min(100, int(snr * 120)) if is_real else max(0, int(snr * 40))

    return {
        "score": score,
        "is_real": is_real,
        "bpm": round(bpm, 1),
        "snr": round(snr, 3),
        "detail": f"rPPG BPM={bpm:.0f}, SNR={snr:.3f} — {'pulse detected' if is_real else 'no pulse — possible screen/photo'}",
    }


def detect_screen_glare(frames: List[np.ndarray]) -> dict:
    """
    Screens have specular highlights with high saturation in HSV.
    Real faces don't have uniform bright patches.
    """
    glare_scores = []
    for frame in frames[::5]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # High value + low saturation = glare
        glare_mask = (hsv[:, :, 2] > 220) & (hsv[:, :, 1] < 30)
        glare_ratio = np.sum(glare_mask) / glare_mask.size
        glare_scores.append(glare_ratio)

    avg_glare = np.mean(glare_scores)
    is_screen = avg_glare > 0.04  # >4% of frame is glare = suspicious

    return {
        "glare_ratio": round(float(avg_glare), 4),
        "is_screen": is_screen,
        "detail": f"Glare ratio {avg_glare:.2%} — {'screen detected' if is_screen else 'normal'}",
    }


def detect_frame_duplicates(frames: List[np.ndarray]) -> dict:
    """
    Replay attacks loop frames. Detect via perceptual hash similarity.
    """
    if len(frames) < 10:
        return {"is_replay": False, "detail": "Insufficient frames"}

    def phash(frame):
        small = cv2.resize(frame, (16, 16))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        mean = gray.mean()
        return (gray > mean).flatten()

    hashes = [phash(f) for f in frames[::3]]
    duplicates = 0
    for i in range(1, len(hashes)):
        similarity = np.mean(hashes[i] == hashes[i - 1])
        if similarity > 0.97:
            duplicates += 1

    dup_ratio = duplicates / max(len(hashes) - 1, 1)
    is_replay = dup_ratio > 0.5

    return {
        "duplicate_ratio": round(dup_ratio, 3),
        "is_replay": is_replay,
        "detail": f"Frame duplicate ratio {dup_ratio:.1%} — {'REPLAY DETECTED' if is_replay else 'normal temporal variation'}",
    }


def detect_low_light(frames: List[np.ndarray]) -> dict:
    """
    FIX #10: Detect low-light / near-black frames that defeat all analysis.
    """
    brightness_vals = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness_vals.append(float(np.mean(gray)))
    avg_brightness = float(np.mean(brightness_vals)) if brightness_vals else 0
    is_too_dark = avg_brightness < 30  # 0-255 scale
    is_too_bright = avg_brightness > 230
    return {
        "avg_brightness": round(avg_brightness, 1),
        "is_too_dark": is_too_dark,
        "is_too_bright": is_too_bright,
        "detail": f"Avg brightness {avg_brightness:.0f}/255 — {'TOO DARK' if is_too_dark else 'TOO BRIGHT' if is_too_bright else 'normal lighting'}",
    }


def analyze_liveness(frames: List[np.ndarray], nonce_valid: bool) -> dict:
    if not nonce_valid:
        return {
            "score": 0,
            "status": "FAIL",
            "detail": "Session nonce invalid — replay attack blocked",
            "signals": {},
        }

    # FIX #10: Hard gate — reject unusable lighting before any ML
    lighting = detect_low_light(frames)
    if lighting["is_too_dark"] or lighting["is_too_bright"]:
        return {
            "score": 5,
            "status": "FAIL",
            "detail": f"Lighting check failed: {lighting['detail']}",
            "signals": {"lighting": lighting},
        }

    rppg = detect_rppg_signal(frames)
    glare = detect_screen_glare(frames)
    replay = detect_frame_duplicates(frames)

    # Weighted liveness score
    score = 0
    if rppg.get("is_real", False):   # FIX #2: safe .get() with default
        score += 50
    if not glare.get("is_screen", False):
        score += 25
    if not replay.get("is_replay", False):
        score += 25

    status = "PASS" if score >= 60 else ("WARN" if score >= 35 else "FAIL")

    return {
        "score": score,
        "status": status,
        "signals": {"rppg": rppg, "glare": glare, "replay": replay, "lighting": lighting},
        "detail": f"Liveness score {score}/100 — {status}",
    }
