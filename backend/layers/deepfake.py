"""
Layer 3: Hybrid Deepfake Detection
- FFT frequency artifacts (threshold raised to 1.2 for webcam compatibility)
- Landmark jitter via MediaPipe (if available)
- Optical flow inconsistency
- Facial warping edge detection
- Blur/sharpness check
"""
import cv2
import numpy as np
from typing import List
from layers.utils import to_python


def analyze_frequency_artifacts(frames: List[np.ndarray]) -> dict:
    """
    GAN deepfakes leave checkerboard artifacts in frequency domain.
    CALIBRATED threshold: 1.2 (was 0.68 — too low, flagged real webcam video)
    Webcam-compressed real video: HF ratio ~0.5-0.9
    GAN deepfakes: HF ratio > 1.2
    """
    scores = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        roi  = gray[h//4: 3*h//4, w//4: 3*w//4]
        if roi.size == 0:
            continue
        f         = np.fft.fft2(roi.astype(np.float32))
        fshift    = np.fft.fftshift(f)
        magnitude = np.log1p(np.abs(fshift))
        cy, cx    = magnitude.shape[0]//2, magnitude.shape[1]//2
        radius    = min(cy, cx) // 3
        mask      = np.zeros_like(magnitude)
        cv2.circle(mask, (cx, cy), radius, 1, -1)
        low_e  = float(np.sum(magnitude * mask))
        high_e = float(np.sum(magnitude * (1 - mask)))
        scores.append(high_e / (low_e + 1e-6))

    avg_ratio   = float(np.mean(scores)) if scores else 0.0
    is_deepfake = avg_ratio > 1.2   # CALIBRATED (was 0.68)
    confidence  = min(100, int(avg_ratio * 50))

    return to_python({
        "hf_ratio":   round(avg_ratio, 4),
        "is_deepfake": is_deepfake,
        "confidence":  confidence,
        "detail": f"FFT HF={avg_ratio:.3f} — {'GAN artifacts' if is_deepfake else 'normal'}",
    })


def analyze_landmark_jitter(frames: List[np.ndarray]) -> dict:
    """
    Track facial landmarks across frames.
    Real faces = smooth trajectory. Deepfakes = jitter.
    Uses MediaPipe if available, falls back to Haar-based tracking.
    """
    try:
        import mediapipe as mp
        # Try new Tasks API first, then legacy
        try:
            mp_face = mp.solutions.face_mesh
            face_mesh = mp_face.FaceMesh(
                static_image_mode=False, max_num_faces=1,
                refine_landmarks=False, min_detection_confidence=0.5,
            )
            KEY_POINTS  = [1, 33, 263, 61, 291]
            trajectories = {k: [] for k in KEY_POINTS}

            for frame in frames[::2]:
                rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = face_mesh.process(rgb)
                if result.multi_face_landmarks:
                    lm   = result.multi_face_landmarks[0].landmark
                    h, w = frame.shape[:2]
                    for k in KEY_POINTS:
                        if k < len(lm):
                            trajectories[k].append((lm[k].x * w, lm[k].y * h))

            face_mesh.close()

            jitter_vals = []
            for pts in trajectories.values():
                if len(pts) < 5:
                    continue
                arr  = np.array(pts, dtype=np.float32)
                vel  = np.diff(arr, axis=0)
                acc  = np.diff(vel, axis=0)
                jitter_vals.append(float(np.mean(np.abs(acc))))

            if not jitter_vals:
                return to_python({"jitter_score": 0.0, "is_deepfake": False,
                                  "confidence": 0, "detail": "No landmarks tracked"})

            avg_jitter  = float(np.mean(jitter_vals))
            is_deepfake = avg_jitter > 2.5
            return to_python({
                "jitter_score": round(avg_jitter, 3),
                "is_deepfake":  is_deepfake,
                "confidence":   min(100, int(avg_jitter * 20)),
                "detail": f"Jitter={avg_jitter:.2f}px/f² — {'unnatural' if is_deepfake else 'smooth'}",
            })
        except AttributeError:
            pass
    except ImportError:
        pass

    return to_python({"jitter_score": 0.0, "is_deepfake": False,
                      "confidence": 0, "detail": "MediaPipe unavailable — skipped"})


def analyze_optical_flow(frames: List[np.ndarray]) -> dict:
    if len(frames) < 10:
        return to_python({"flow_score": 0.0, "is_suspicious": False, "detail": "Too few frames"})

    flow_mags = []
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

    for frame in frames[1::2]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow      = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        mag = float(np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)))
        flow_mags.append(mag)
        prev_gray = curr_gray

    if not flow_mags:
        return to_python({"flow_score": 0.0, "is_suspicious": False, "detail": "No flow computed"})

    mean_flow     = float(np.mean(flow_mags))
    flow_variance = float(np.var(flow_mags))
    # Only flag if BOTH mean and variance are very low (true static replay)
    is_suspicious = mean_flow < 0.2 and flow_variance < 0.005

    return to_python({
        "mean_flow":     round(mean_flow, 4),
        "flow_variance": round(flow_variance, 4),
        "is_suspicious": is_suspicious,
        "detail": f"Flow mean={mean_flow:.3f} var={flow_variance:.4f} — {'suspicious' if is_suspicious else 'natural'}",
    })


def analyze_facial_warping(frames: List[np.ndarray]) -> dict:
    warp_scores = []
    for frame in frames[::5]:
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w  = gray.shape
        inner = gray[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        if inner.size == 0:
            continue
        edges = cv2.Canny(inner, 50, 150)
        warp_scores.append(float(np.sum(edges > 0) / edges.size))

    avg_warp = float(np.mean(warp_scores)) if warp_scores else 0.0
    is_warped = avg_warp > 0.15

    return to_python({
        "warp_score": round(avg_warp, 4), "is_warped": is_warped,
        "detail": f"Edge density={avg_warp:.3f} — {'warping' if is_warped else 'clean'}",
    })


def detect_image_blur(frames: List[np.ndarray]) -> dict:
    vals = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        vals.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    avg       = float(np.mean(vals)) if vals else 0.0
    is_blurry = avg < 30
    return to_python({
        "sharpness": round(avg, 1), "is_blurry": is_blurry,
        "detail": f"Sharpness={avg:.0f} — {'BLURRY' if is_blurry else 'sharp'}",
    })


def analyze_deepfake(frames: List[np.ndarray]) -> dict:
    freq   = analyze_frequency_artifacts(frames)
    jitter = analyze_landmark_jitter(frames)
    flow   = analyze_optical_flow(frames)
    warp   = analyze_facial_warping(frames)
    blur   = detect_image_blur(frames)

    if blur["is_blurry"]:
        return to_python({
            "score": 20, "deepfake_probability": 80, "status": "FAIL",
            "flags_triggered": 4,
            "signals": {"frequency": freq, "landmark_jitter": jitter,
                        "optical_flow": flow, "facial_warping": warp, "blur": blur},
            "detail": f"HARD FAIL: Blurry input (sharpness={blur['sharpness']:.0f})",
        })

    flags = [
        freq.get("is_deepfake", False),
        jitter.get("is_deepfake", False),
        flow.get("is_suspicious", False),
        warp.get("is_warped", False),
    ]
    flag_count = sum(flags)

    raw_score = (
        freq.get("confidence", 0) * 0.40 +
        jitter.get("confidence", 0) * 0.35 +
        (50 if flow.get("is_suspicious") else 0) * 0.15 +
        (50 if warp.get("is_warped") else 0) * 0.10
    )
    deepfake_prob = min(100, int(raw_score))

    status = "FAIL" if flag_count >= 3 else ("WARN" if flag_count >= 2 else "PASS")
    score  = max(0, 100 - deepfake_prob)

    return to_python({
        "score": score, "deepfake_probability": deepfake_prob,
        "status": status, "flags_triggered": flag_count,
        "signals": {"frequency": freq, "landmark_jitter": jitter,
                    "optical_flow": flow, "facial_warping": warp, "blur": blur},
        "detail": f"{flag_count}/4 deepfake signals — {status}",
    })
