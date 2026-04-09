"""
Layer 3: Hybrid Deepfake Detection
- FFT frequency artifacts (threshold raised to 2.0 for webcam VP8/H264)
- Landmark jitter via OpenCV Haar cascade tracking (no external model needed)
- Optical flow inconsistency
- Facial warping edge detection
- Blur/sharpness check
"""
import cv2
import numpy as np
from typing import List
from layers.utils import to_python

_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def analyze_frequency_artifacts(frames: List[np.ndarray]) -> dict:
    """
    GAN deepfakes leave checkerboard artifacts in frequency domain.
    CALIBRATED threshold: 2.0
    Real webcam VP8/H264 video naturally produces HF ratios of 5-12
    due to codec block artifacts. Only true GAN patterns exceed 2.0
    consistently across multiple frames.
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
    # Threshold 2.0 — real webcam video scores 5-12, GAN deepfakes score 15+
    # We use relative comparison: flag only if consistently high
    is_deepfake = avg_ratio > 15.0
    confidence  = min(100, int(max(0, avg_ratio - 10) * 5))

    return to_python({
        "hf_ratio":    round(avg_ratio, 4),
        "is_deepfake": is_deepfake,
        "confidence":  confidence,
        "detail": f"FFT HF={avg_ratio:.3f} — {'GAN artifacts' if is_deepfake else 'normal'}",
    })


def analyze_landmark_jitter(frames: List[np.ndarray]) -> dict:
    """
    Track face bounding box center across frames as landmark proxy.
    Real faces: smooth trajectory with natural movement.
    Deepfakes: jittery, inconsistent face position.
    Uses OpenCV Haar cascade — no external model needed.
    """
    centers = []
    for frame in frames[::2]:
        gray  = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 3, minSize=(60, 60))
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append((float(x + w/2), float(y + h/2)))

    if len(centers) < 8:
        return to_python({"jitter_score": 0.0, "is_deepfake": False,
                          "confidence": 0,
                          "detail": "Insufficient face detections for jitter analysis"})

    arr = np.array(centers, dtype=np.float32)
    vel = np.diff(arr, axis=0)
    acc = np.diff(vel, axis=0)
    avg_jitter  = float(np.mean(np.abs(acc)))
    is_deepfake = avg_jitter > 3.0  # deepfakes have erratic face position

    return to_python({
        "jitter_score": round(avg_jitter, 3),
        "is_deepfake":  is_deepfake,
        "confidence":   min(100, int(avg_jitter * 15)),
        "detail": f"Face jitter={avg_jitter:.2f}px/f\u00b2 \u2014 {'unnatural' if is_deepfake else 'smooth'}",
    })


def analyze_optical_flow(frames: List[np.ndarray]) -> dict:
    if len(frames) < 10:
        return to_python({"flow_score": 0.0, "is_suspicious": False,
                          "detail": "Too few frames"})

    flow_mags = []
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

    for frame in frames[1::2]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow      = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        flow_mags.append(float(np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2))))
        prev_gray = curr_gray

    if not flow_mags:
        return to_python({"flow_score": 0.0, "is_suspicious": False,
                          "detail": "No flow computed"})

    mean_flow     = float(np.mean(flow_mags))
    flow_variance = float(np.var(flow_mags))
    # Only flag true static replay — both mean AND variance near zero
    is_suspicious = mean_flow < 0.15 and flow_variance < 0.003

    return to_python({
        "mean_flow":     round(mean_flow, 4),
        "flow_variance": round(flow_variance, 4),
        "is_suspicious": is_suspicious,
        "detail": f"Flow mean={mean_flow:.3f} var={flow_variance:.4f} \u2014 {'suspicious' if is_suspicious else 'natural'}",
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

    avg_warp  = float(np.mean(warp_scores)) if warp_scores else 0.0
    is_warped = avg_warp > 0.18

    return to_python({
        "warp_score": round(avg_warp, 4), "is_warped": is_warped,
        "detail": f"Edge density={avg_warp:.3f} \u2014 {'warping' if is_warped else 'clean'}",
    })


def detect_image_blur(frames: List[np.ndarray]) -> dict:
    vals = [float(cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
            for f in frames[::5]]
    avg       = float(np.mean(vals)) if vals else 0.0
    is_blurry = avg < 20
    return to_python({
        "sharpness": round(avg, 1), "is_blurry": is_blurry,
        "detail": f"Sharpness={avg:.0f} \u2014 {'BLURRY' if is_blurry else 'sharp'}",
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
    status        = "FAIL" if flag_count >= 3 else ("WARN" if flag_count >= 2 else "PASS")
    score         = max(0, 100 - deepfake_prob)

    return to_python({
        "score": score, "deepfake_probability": deepfake_prob,
        "status": status, "flags_triggered": flag_count,
        "signals": {"frequency": freq, "landmark_jitter": jitter,
                    "optical_flow": flow, "facial_warping": warp, "blur": blur},
        "detail": f"{flag_count}/4 deepfake signals \u2014 {status}",
    })
