"""
Layer 2: Face Matching
- Compare ID document photo vs live capture
- Uses DeepFace with ArcFace backend (state-of-the-art accuracy)
- Hard threshold + confidence scoring
"""
import cv2
import numpy as np
import base64
import tempfile
import os
from typing import Optional


def _save_temp_image(image_data: bytes, suffix: str = ".jpg") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(image_data)
        return f.name


def _b64_to_bytes(b64_string: str) -> bytes:
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    return base64.b64decode(b64_string)


def extract_best_frame(frames: list) -> Optional[np.ndarray]:
    """Pick sharpest frame using Laplacian variance."""
    best_frame, best_score = None, 0
    for frame in frames[::3]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if score > best_score:
            best_score = score
            best_frame = frame
    return best_frame


def match_faces(id_image_b64: str, live_frames: list) -> dict:
    try:
        from deepface import DeepFace
    except ImportError:
        return _fallback_face_match(id_image_b64, live_frames)

    id_bytes = _b64_to_bytes(id_image_b64)
    id_path = _save_temp_image(id_bytes)

    best_frame = extract_best_frame(live_frames)
    if best_frame is None:
        return {"score": 0, "status": "FAIL", "detail": "No valid frame extracted from video"}

    live_path = _save_temp_image(cv2.imencode(".jpg", best_frame)[1].tobytes())

    try:
        result = DeepFace.verify(
            img1_path=id_path,
            img2_path=live_path,
            model_name="ArcFace",
            detector_backend="opencv",
            enforce_detection=False,
        )
        similarity = round((1 - result["distance"]) * 100, 2)
        verified = result["verified"]
        status = "PASS" if verified and similarity >= 70 else ("WARN" if similarity >= 55 else "FAIL")

        return {
            "score": max(0, min(100, int(similarity))),
            "similarity": similarity,
            "status": status,
            "detail": f"ArcFace similarity {similarity:.1f}% — {'identity confirmed' if verified else 'identity mismatch'}",
            "threshold": 70,
        }
    except Exception as e:
        return {"score": 40, "status": "WARN", "detail": f"Face match error: {str(e)[:80]}"}
    finally:
        for p in [id_path, live_path]:
            try:
                os.unlink(p)
            except Exception:
                pass


def _fallback_face_match(id_image_b64: str, live_frames: list) -> dict:
    """
    Fallback: OpenCV histogram comparison when DeepFace unavailable.
    Less accurate but always works.
    """
    id_bytes = _b64_to_bytes(id_image_b64)
    id_arr = np.frombuffer(id_bytes, np.uint8)
    id_img = cv2.imdecode(id_arr, cv2.IMREAD_COLOR)

    best_frame = extract_best_frame(live_frames)
    if id_img is None or best_frame is None:
        return {"score": 0, "status": "FAIL", "detail": "Could not decode images"}

    def face_histogram(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        return cv2.normalize(hist, hist).flatten()

    h1 = face_histogram(id_img)
    h2 = face_histogram(best_frame)
    similarity = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL) * 100

    status = "PASS" if similarity >= 65 else ("WARN" if similarity >= 45 else "FAIL")
    return {
        "score": max(0, int(similarity)),
        "similarity": round(similarity, 2),
        "status": status,
        "detail": f"Fallback histogram similarity {similarity:.1f}% (DeepFace unavailable)",
        "threshold": 65,
    }
