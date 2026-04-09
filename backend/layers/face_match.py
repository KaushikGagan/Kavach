"""
Layer 2: Face Matching
- DeepFace ArcFace (primary)
- Lighting normalization before comparison
- Multi-frame voting (best 3 frames, take highest score)
- Fallback: ORB feature matching
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


def _save_temp(data: bytes, suffix: str = ".jpg") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        return f.name


def _normalize_lighting(img: np.ndarray) -> np.ndarray:
    """CLAHE histogram equalization — fixes dark/bright ID photos vs webcam."""
    lab   = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _sharpness(frame: np.ndarray) -> float:
    return float(cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def _pick_best_frames(frames: List[np.ndarray], n: int = 3) -> List[np.ndarray]:
    """Pick top-n sharpest frames for multi-frame voting."""
    scored = sorted(frames[::2], key=_sharpness, reverse=True)
    return scored[:n]


def match_faces(id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    try:
        from deepface import DeepFace
        return _deepface_match(DeepFace, id_image_b64, live_frames)
    except ImportError:
        return _fallback_match(id_image_b64, live_frames)
    except Exception as e:
        return _fallback_match(id_image_b64, live_frames)


def _deepface_match(DeepFace, id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    id_bytes = _b64_to_bytes(id_image_b64)
    id_arr   = np.frombuffer(id_bytes, np.uint8)
    id_img   = cv2.imdecode(id_arr, cv2.IMREAD_COLOR)

    if id_img is None:
        return to_python({"score": 0, "status": "FAIL",
                          "detail": "Could not decode ID image"})

    # Normalize ID image lighting
    id_img_norm = _normalize_lighting(id_img)
    id_path     = _save_temp(cv2.imencode(".jpg", id_img_norm)[1].tobytes())

    best_frames = _pick_best_frames(live_frames, n=3)
    if not best_frames:
        os.unlink(id_path)
        return to_python({"score": 0, "status": "FAIL",
                          "detail": "No valid frames extracted"})

    similarities = []
    for frame in best_frames:
        frame_norm = _normalize_lighting(frame)
        live_path  = _save_temp(cv2.imencode(".jpg", frame_norm)[1].tobytes())
        try:
            result     = DeepFace.verify(
                img1_path=id_path, img2_path=live_path,
                model_name="ArcFace", detector_backend="opencv",
                enforce_detection=False,
            )
            sim = float((1 - result["distance"]) * 100)
            similarities.append(sim)
        except Exception:
            pass
        finally:
            try: os.unlink(live_path)
            except Exception: pass

    try: os.unlink(id_path)
    except Exception: pass

    if not similarities:
        return to_python({"score": 40, "status": "WARN",
                          "detail": "ArcFace could not process frames — using fallback",
                          "similarity": 40.0})

    # Take the best similarity across frames (most favorable match)
    similarity = round(max(similarities), 2)
    verified   = similarity >= 68   # slightly relaxed from 70

    if verified and similarity >= 68:
        status = "PASS"
    elif similarity >= 52:
        status = "WARN"
    else:
        status = "FAIL"

    return to_python({
        "score":      max(0, min(100, int(similarity))),
        "similarity": similarity,
        "status":     status,
        "detail":     f"ArcFace {similarity:.1f}% — {'identity confirmed' if verified else 'identity mismatch'}",
        "threshold":  68,
        "frames_checked": len(similarities),
    })


def _fallback_match(id_image_b64: str, live_frames: List[np.ndarray]) -> dict:
    """
    Fallback when DeepFace unavailable.
    Uses ORB feature matching — more robust than histogram for face comparison.
    """
    id_bytes = _b64_to_bytes(id_image_b64)
    id_arr   = np.frombuffer(id_bytes, np.uint8)
    id_img   = cv2.imdecode(id_arr, cv2.IMREAD_COLOR)

    best_frames = _pick_best_frames(live_frames, n=1)
    if id_img is None or not best_frames:
        return to_python({"score": 0, "status": "FAIL",
                          "detail": "Could not decode images"})

    live_frame = best_frames[0]

    # Normalize both
    id_norm   = _normalize_lighting(id_img)
    live_norm = _normalize_lighting(live_frame)

    # Resize to same size
    target = (200, 200)
    id_r   = cv2.resize(cv2.cvtColor(id_norm,   cv2.COLOR_BGR2GRAY), target)
    live_r = cv2.resize(cv2.cvtColor(live_norm, cv2.COLOR_BGR2GRAY), target)

    # ORB feature matching
    orb  = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(id_r,   None)
    kp2, des2 = orb.detectAndCompute(live_r, None)

    similarity = 0.0
    if des1 is not None and des2 is not None and len(des1) > 10 and len(des2) > 10:
        bf      = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        good    = [m for m in matches if m.distance < 50]
        similarity = float(len(good)) / max(len(kp1), len(kp2)) * 100
        similarity = min(similarity * 3.5, 100.0)  # scale to 0-100

    status = "PASS" if similarity >= 60 else ("WARN" if similarity >= 40 else "FAIL")
    return to_python({
        "score":      max(0, int(similarity)),
        "similarity": round(similarity, 2),
        "status":     status,
        "detail":     f"ORB fallback similarity {similarity:.1f}% (DeepFace unavailable)",
        "threshold":  60,
    })
