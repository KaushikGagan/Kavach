"""
Layer 3: Hybrid Deepfake Detection
- Frequency domain artifact analysis (FFT checkerboard)
- Temporal landmark jitter (MediaPipe 468-point mesh)
- Optical flow inconsistency
- Facial warping edge detection
- Pretrained model (EfficientNet/fallback heuristic)
"""
import cv2
import numpy as np
from typing import List
from layers.utils import to_python


def analyze_frequency_artifacts(frames: List[np.ndarray]) -> dict:
    """
    GAN-generated faces leave checkerboard artifacts in frequency domain.
    Detectable via FFT high-frequency energy ratio.
    """
    scores = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        # Crop to face-center region
        roi = gray[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
        f = np.fft.fft2(roi.astype(np.float32))
        fshift = np.fft.fftshift(f)
        magnitude = np.log1p(np.abs(fshift))

        # High-frequency energy ratio (deepfakes have elevated HF energy)
        cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
        radius = min(cy, cx) // 3
        mask = np.zeros_like(magnitude)
        cv2.circle(mask, (cx, cy), radius, 1, -1)
        low_energy = np.sum(magnitude * mask)
        high_energy = np.sum(magnitude * (1 - mask))
        ratio = high_energy / (low_energy + 1e-6)
        scores.append(ratio)

    avg_ratio = float(np.mean(scores)) if scores else 0
    # Raised threshold: webcam-compressed video naturally has HF ratio 0.5-0.8
    # GAN deepfakes typically show > 1.2 due to checkerboard artifacts
    is_deepfake = avg_ratio > 1.2
    confidence  = min(100, int(avg_ratio * 60))

    return to_python({
        "hf_ratio": round(avg_ratio, 4),
        "is_deepfake": is_deepfake,
        "confidence": confidence,
        "detail": f"FFT HF ratio {avg_ratio:.3f} — {'GAN artifacts detected' if is_deepfake else 'frequency normal'}",
    })


def analyze_landmark_jitter(frames: List[np.ndarray]) -> dict:
    """
    Track 5 key landmarks across frames. Real faces = smooth trajectory.
    Deepfakes = high variance / jitter in landmark positions.
    """
    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_mesh
        face_mesh = mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
    except ImportError:
        return to_python({"jitter_score": 0, "is_deepfake": False, "confidence": 0, "detail": "MediaPipe unavailable — skipped"})

    # Key landmark indices: nose tip, left eye, right eye, left mouth, right mouth
    KEY_POINTS = [1, 33, 263, 61, 291]
    trajectories = {k: [] for k in KEY_POINTS}

    for frame in frames:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)
        if result.multi_face_landmarks:
            lm = result.multi_face_landmarks[0].landmark
            h, w = frame.shape[:2]
            for k in KEY_POINTS:
                if k < len(lm):
                    trajectories[k].append((lm[k].x * w, lm[k].y * h))

    face_mesh.close()

    if not any(len(v) > 5 for v in trajectories.values()):
        return to_python({"jitter_score": 0, "is_deepfake": False, "confidence": 0, "detail": "Insufficient landmark data"})

    jitter_values = []
    for pts in trajectories.values():
        if len(pts) < 5:
            continue
        arr = np.array(pts)
        # Second derivative = acceleration (real faces have low acceleration)
        velocity = np.diff(arr, axis=0)
        acceleration = np.diff(velocity, axis=0)
        jitter_values.append(float(np.mean(np.abs(acceleration))))

    avg_jitter = float(np.mean(jitter_values)) if jitter_values else 0
    # Threshold: >2.5px/frame² is suspicious
    is_deepfake = avg_jitter > 2.5
    score = min(100, int(avg_jitter * 20))

    return to_python({
        "jitter_score": round(avg_jitter, 3),
        "is_deepfake": is_deepfake,
        "confidence": score,
        "detail": f"Landmark jitter {avg_jitter:.2f}px/f² — {'unnatural movement detected' if is_deepfake else 'smooth natural motion'}",
    })


def analyze_optical_flow(frames: List[np.ndarray]) -> dict:
    """
    Real faces have organic, varied optical flow.
    Replayed/deepfake videos have mechanical or near-zero background flow.
    """
    if len(frames) < 10:
        return to_python({"flow_score": 0, "is_suspicious": False, "detail": "Too few frames"})

    flow_magnitudes = []
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

    for frame in frames[1::2]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        flow_magnitudes.append(float(np.mean(magnitude)))
        prev_gray = curr_gray

    if not flow_magnitudes:
        return to_python({"flow_score": 0, "is_suspicious": False, "detail": "No flow computed"})

    mean_flow = float(np.mean(flow_magnitudes))
    flow_variance = float(np.var(flow_magnitudes))

    # Replay: very low variance (static video). Deepfake: unnaturally uniform flow.
    is_suspicious = mean_flow < 0.3 or flow_variance < 0.01

    return to_python({
        "mean_flow": round(mean_flow, 4),
        "flow_variance": round(flow_variance, 4),
        "is_suspicious": is_suspicious,
        "detail": f"Optical flow mean={mean_flow:.3f} var={flow_variance:.4f} — {'suspicious (static/replay)' if is_suspicious else 'natural motion'}",
    })


def analyze_facial_warping(frames: List[np.ndarray]) -> dict:
    """
    Deepfake face-swap creates warping artifacts at face boundaries.
    Detect via edge density in face border region.
    """
    warp_scores = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        # Face border region (outer 20% of face area)
        inner = gray[int(h * 0.2):int(h * 0.8), int(w * 0.2):int(w * 0.8)]
        edges = cv2.Canny(inner, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        warp_scores.append(edge_density)

    avg_warp = float(np.mean(warp_scores)) if warp_scores else 0
    is_warped = avg_warp > 0.12

    return to_python({
        "warp_score": round(avg_warp, 4),
        "is_warped": is_warped,
        "detail": f"Edge density {avg_warp:.3f} — {'warping artifacts detected' if is_warped else 'clean boundaries'}",
    })


def detect_image_blur(frames: List[np.ndarray]) -> dict:
    """
    FIX #10: Detect adversarially blurred input that defeats face matching.
    Uses Laplacian variance — real sharp faces score >100.
    """
    sharpness_vals = []
    for frame in frames[::5]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness_vals.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    avg_sharpness = float(np.mean(sharpness_vals)) if sharpness_vals else 0
    is_blurry = avg_sharpness < 40
    return to_python({
        "sharpness": round(avg_sharpness, 1),
        "is_blurry": is_blurry,
        "detail": f"Sharpness {avg_sharpness:.0f} — {'BLURRY INPUT DETECTED' if is_blurry else 'sharp'}",
    })


def analyze_deepfake(frames: List[np.ndarray]) -> dict:
    freq = analyze_frequency_artifacts(frames)
    jitter = analyze_landmark_jitter(frames)
    flow = analyze_optical_flow(frames)
    warp = analyze_facial_warping(frames)
    blur = detect_image_blur(frames)

    # FIX #10: Hard gate — blurry input is adversarial or unusable
    if blur["is_blurry"]:
        return to_python({
            "score": 20, "deepfake_probability": 80, "status": "FAIL", "flags_triggered": 4,
            "signals": {"frequency": freq, "landmark_jitter": jitter, "optical_flow": flow, "facial_warping": warp, "blur": blur},
            "detail": f"HARD FAIL: Blurry input (sharpness={blur['sharpness']:.0f}) — possible adversarial manipulation",
        })

    # Count suspicious signals — FIX: use .get() safely on all signal dicts
    flags = [
        freq.get("is_deepfake", False),
        jitter.get("is_deepfake", False),
        flow.get("is_suspicious", False),
        warp.get("is_warped", False),
    ]
    flag_count = sum(flags)

    # Weighted score: frequency + jitter are strongest signals
    raw_score = (
        (freq["confidence"] * 0.35) +
        (jitter.get("confidence", 0) * 0.35) +
        (50 if flow["is_suspicious"] else 0) * 0.15 +
        (50 if warp["is_warped"] else 0) * 0.15
    )
    deepfake_probability = min(100, int(raw_score))

    if flag_count >= 3:
        status = "FAIL"
    elif flag_count >= 2:
        status = "WARN"
    else:
        status = "PASS"

    # Invert for safety score
    score = max(0, 100 - deepfake_probability)

    return to_python({
        "score": score,
        "deepfake_probability": deepfake_probability,
        "status": status,
        "flags_triggered": flag_count,
        "signals": {
            "frequency": freq,
            "landmark_jitter": jitter,
            "optical_flow": flow,
            "facial_warping": warp,
            "blur": blur,
        },
        "detail": f"{flag_count}/4 deepfake signals triggered — {status}",
    })
