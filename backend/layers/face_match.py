"""
Layer 2: Face Matching
Works on Python 3.14 without TensorFlow/DeepFace.

Pipeline:
  1. Detect face region using Haar cascade (OpenCV built-in)
  2. Align + normalize lighting (CLAHE)
  3. Compare using SSIM + ORB feature matching
  4. Multi-frame voting (best 3 frames)
  5. DeepFace attempted first, falls back gracefully
"""
import cv2
import numpy as np
import base64
import tempfile
import os
from typing import Optional, List
from layers.utils import to_python


def _b64_to_bytes(b64: str) -> bytes:
    if "," in b64:
        b64 = b64.split(",")[1]
    return base64.b64decode(b64)


def _normalize(img: np.ndarray) -> np.ndarray:
    """CLAHE lighting normalization."""
    lab   = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _detect_face_roi(img: np.ndarray) -> Optional[np.ndarray]:
    """Crop to face region using Haar cascade. Returns None if no face found."""
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces    = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # largest face
    # Add 20% padding
    pad = int(0.2 * min(w, h))
    x1  = max(0, x - pad)
    y1  = max(0, y - pad)
    x2  = min(img.shape[1], x + w + pad)
    y2  = min(img.shape[0], y + h + pad)
    return img[y1:y2, x1:x2]


def _sharpness(frame: np.ndarray) -> float:
    return float(cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def _pick_best_frames(frames: List[np.ndarray], n: int = 3) -> List[np.ndarray]:
    scored = sorted(frames[::2], key=_sharpness, reverse=True)
    return scored[:n]


def _ssim_score(img1: np.ndarray, img2: np.ndarray, size: int = 128) -> float:
    """Structural Similarity Index between two face images."""
    g1 = cv2.resize(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), (size, size)).astype(np.float32)
    g2 = cv2.resize(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY), (size, size)).astype(np.float32)

    C1, C2 = 6.5025, 58.5225
    mu1, mu2 = cv2.GaussianBlur(g1, (11,11), 1.5), cv2.GaussianBlur(g2, (11,11), 1.5)
    mu1_sq, mu2_sq, mu1_mu2 = mu1**2, mu2**2, mu1*mu2

    s1  = cv2.GaussianBlur(g1*g1, (11,11), 1.5) - mu1_sq
    s2  = cv2.GaussianBlur(g2*g2, (11,11), 1.5) - mu2_sq
    s12 = cv2.GaussianBlur(g1*g2, (11,11), 1.5) - mu1_mu2

    num = (2*mu1_mu2 + C1) * (2*s12 + C2)
    den = (mu1_sq + mu2_sq + C1) * (s1 + s2 + C2)
    ssim_map = num / (den + 1e-8)
    return float(np.mean(ssim_map))


def _orb_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """ORB feature matching score 0-100."""
    g1 = cv2.resize(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), (200, 200))
    g2 = cv2.resize(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY), (200, 200))

    orb = cv2.ORB_create(nfeatures=800)
    kp1, des1 = orb.detectAndCompute(g1, None)
    kp2, des2 = orb.detectAndCompute(g2, None)

    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        return 0.0

    bf      = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda x: x.distance)
    good    = [m for m in matches if m.distance < 55]
    ratio   = len(good) / max(len(kp1), len(kp2), 1)
    return min(float(ratio) * 400, 100.0)  # scale to 0-100


def match_faces(id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    # Try DeepFace first (best accuracy if available)
    try:
        from deepface import DeepFace
        return _deepface_match(DeepFace, id_image_b64, live_frames)
    except Exception:
        pass

    # Fallback: SSIM + ORB (works on Python 3.14, no TF needed)
    return _opencv_match(id_image_b64, live_frames)


def _deepface_match(DeepFace, id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    id_bytes    = _b64_to_bytes(id_image_b64)
    id_arr      = np.frombuffer(id_bytes, np.uint8)
    id_img      = cv2.imdecode(id_arr, cv2.IMREAD_COLOR)
    if id_img is None:
        return _opencv_match(id_image_b64, live_frames)

    id_norm = _normalize(id_img)
    id_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(id_path.name, id_norm)
    id_path.close()

    best_frames  = _pick_best_frames(live_frames, 3)
    similarities = []

    for frame in best_frames:
        live_norm = _normalize(frame)
        lp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        cv2.imwrite(lp.name, live_norm)
        lp.close()
        try:
            r   = DeepFace.verify(img1_path=id_path.name, img2_path=lp.name,
                                  model_name="ArcFace", detector_backend="opencv",
                                  enforce_detection=False)
            similarities.append(float((1 - r["distance"]) * 100))
        except Exception:
            pass
        finally:
            try: os.unlink(lp.name)
            except Exception: pass

    try: os.unlink(id_path.name)
    except Exception: pass

    if not similarities:
        return _opencv_match(id_image_b64, live_frames)

    similarity = round(max(similarities), 2)
    status     = "PASS" if similarity >= 68 else ("WARN" if similarity >= 52 else "FAIL")
    return to_python({
        "score": max(0, min(100, int(similarity))), "similarity": similarity,
        "status": status, "method": "ArcFace",
        "detail": f"ArcFace {similarity:.1f}% — {'confirmed' if similarity >= 68 else 'mismatch'}",
        "threshold": 68,
    })


def _opencv_match(id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    """
    Pure OpenCV face matching — no TensorFlow, no external models.
    Uses: Haar face detection + CLAHE normalization + SSIM + ORB
    """
    id_bytes = _b64_to_bytes(id_image_b64)
    id_arr   = np.frombuffer(id_bytes, np.uint8)
    id_img   = cv2.imdecode(id_arr, cv2.IMREAD_COLOR)

    best_frames = _pick_best_frames(live_frames, 3)
    if id_img is None or not best_frames:
        return to_python({"score": 0, "status": "FAIL",
                          "detail": "Could not decode images", "method": "OpenCV"})

    id_norm = _normalize(id_img)
    id_face = _detect_face_roi(id_norm) or id_norm  # fallback to full image

    scores = []
    for frame in best_frames:
        live_norm = _normalize(frame)
        live_face = _detect_face_roi(live_norm) or live_norm

        ssim = _ssim_score(id_face, live_face)
        orb  = _orb_score(id_face, live_face)

        # SSIM range is -1 to 1, map to 0-100
        ssim_pct = max(0.0, float(ssim) * 100)

        # Weighted combination: SSIM is more reliable for face comparison
        combined = ssim_pct * 0.65 + orb * 0.35
        scores.append(combined)

    similarity = round(max(scores), 2) if scores else 0.0

    # Calibrated thresholds for SSIM+ORB (lower than ArcFace)
    status = "PASS" if similarity >= 55 else ("WARN" if similarity >= 38 else "FAIL")

    return to_python({
        "score":      max(0, min(100, int(similarity))),
        "similarity": similarity,
        "status":     status,
        "method":     "SSIM+ORB",
        "detail":     f"SSIM+ORB {similarity:.1f}% — {'confirmed' if similarity >= 55 else 'mismatch'}",
        "threshold":  55,
    })
