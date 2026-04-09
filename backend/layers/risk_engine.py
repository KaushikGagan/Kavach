"""
Layer 5: Risk Scoring Engine

Decision logic:
  IF face_match HIGH AND liveness PASS AND spoof PASS → SAFE
  IF liveness FAIL OR spoof detected                  → FRAUD (spoof cap applied)
  ELSE                                                → SUSPICIOUS

Spoof cap: if spoof_risk >= 80, total weighted score capped at 40
"""
from layers.utils import to_python

WEIGHTS = {
    "face_match": 0.30,
    "liveness":   0.30,
    "deepfake":   0.25,
    "behavior":   0.15,
}


def compute_risk_score(
    face_match: dict,
    liveness:   dict,
    deepfake:   dict,
    behavior:   dict,
) -> dict:

    spoof_risk   = liveness.get("spoof_risk", 0)
    liveness_fail = liveness.get("status") == "FAIL"

    # ── HARD GATE 1: Replay attack (nonce) ────────────────────────────────
    if liveness_fail and "nonce" in liveness.get("detail", "").lower():
        return _build_verdict(
            verdict="FRAUD", risk_score=100, confidence=99,
            face_match=face_match, liveness=liveness,
            deepfake=deepfake, behavior=behavior,
            reason="HARD BLOCK: Session nonce invalid — replay attack prevented",
            action="Block and log incident",
        )

    # ── HARD GATE 2: Photo / screen spoof ─────────────────────────────────
    # If liveness fails with high spoof risk → FRAUD regardless of face match
    # This fixes Case 2: same photo attack must be FRAUD even if face matches
    if liveness_fail and spoof_risk >= 80:
        return _build_verdict(
            verdict="FRAUD", risk_score=95, confidence=95,
            face_match=face_match, liveness=liveness,
            deepfake=deepfake, behavior=behavior,
            reason=f"HARD BLOCK: {liveness.get('detail', 'Liveness failed')} — photo/replay spoof detected",
            action="Block — spoof attack detected",
        )

    # ── HARD GATE 3: 3+ deepfake signals ──────────────────────────────────
    if deepfake.get("flags_triggered", 0) >= 3:
        return _build_verdict(
            verdict="FRAUD", risk_score=95, confidence=92,
            face_match=face_match, liveness=liveness,
            deepfake=deepfake, behavior=behavior,
            reason="HARD BLOCK: 3+ deepfake signals triggered simultaneously",
            action="Block — deepfake media detected",
        )

    # ── Weighted score ─────────────────────────────────────────────────────
    weighted = (
        face_match.get("score", 0) * WEIGHTS["face_match"] +
        liveness.get("score", 0)   * WEIGHTS["liveness"]   +
        deepfake.get("score", 0)   * WEIGHTS["deepfake"]   +
        behavior.get("score", 0)   * WEIGHTS["behavior"]
    )
    weighted = round(weighted, 2)

    # ── SPOOF CAP: if spoof detected, cap score at 40 ─────────────────────
    # Fixes Case 2: even if face match is high, spoof overrides
    if spoof_risk >= 80 or liveness_fail:
        weighted = min(weighted, 40.0)

    # ── Confidence ────────────────────────────────────────────────────────
    statuses    = [face_match.get("status"), liveness.get("status"),
                   deepfake.get("status"),   behavior.get("status")]
    pass_count  = statuses.count("PASS")
    fail_count  = statuses.count("FAIL")

    if weighted >= 60:
        confidence = int(weighted * 0.85 + pass_count * 3)
    else:
        confidence = int((100 - weighted) * 0.85 + fail_count * 3)
    confidence = max(40, min(99, confidence))

    # ── Verdict ───────────────────────────────────────────────────────────
    # Case 1: Real user — face HIGH + liveness PASS → SAFE
    # Case 2: Photo spoof — already caught by hard gate above
    # Case 3: Ambiguous → SUSPICIOUS
    if weighted >= 75 and fail_count == 0 and not liveness_fail:
        verdict = "SAFE"
        action  = "Approve KYC — live user verified"
    elif weighted >= 55 and fail_count <= 1:
        verdict = "SUSPICIOUS"
        action  = "Escalate to manual review"
    else:
        verdict = "FRAUD"
        action  = "Block — do not approve"

    # Low confidence safety net
    if confidence < 55 and verdict == "SAFE":
        verdict = "SUSPICIOUS"
        action  = "Low confidence — escalate to manual review"

    reason = _build_reason(face_match, liveness, deepfake, behavior, spoof_risk)

    return _build_verdict(
        verdict=verdict, risk_score=round(100 - weighted, 2),
        confidence=confidence, face_match=face_match,
        liveness=liveness, deepfake=deepfake, behavior=behavior,
        reason=reason, action=action, weighted_score=weighted,
    )


def _build_reason(face_match, liveness, deepfake, behavior, spoof_risk) -> str:
    issues = []

    # Spoof signals (highest priority)
    if spoof_risk >= 80:
        issues.append(liveness.get("detail", "Spoof detected"))
    elif liveness.get("status") == "FAIL":
        sigs = liveness.get("signals", {})
        if sigs.get("motion", {}).get("is_static"):
            issues.append("Static image detected — no natural face movement")
        if sigs.get("texture", {}).get("is_flat"):
            issues.append("Flat texture detected — possible printed photo")
        if sigs.get("replay", {}).get("is_replay"):
            issues.append("Video replay attack — duplicate frames detected")
        if sigs.get("glare", {}).get("is_screen"):
            issues.append("Screen glare detected — possible digital replay")
        if not sigs.get("rppg", {}).get("is_real", True):
            issues.append("No blood flow signal (rPPG) — not a live person")

    # Face match
    if face_match.get("status") == "FAIL":
        issues.append(f"Face mismatch — similarity {face_match.get('similarity', 0):.0f}% (need 70%)")
    elif face_match.get("status") == "WARN":
        issues.append(f"Weak face match — similarity {face_match.get('similarity', 0):.0f}%")

    # Deepfake signals
    if deepfake.get("status") in ("FAIL", "WARN"):
        sigs = deepfake.get("signals", {})
        if sigs.get("frequency", {}).get("is_deepfake"):
            issues.append("GAN frequency artifacts detected")
        if sigs.get("landmark_jitter", {}).get("is_deepfake"):
            issues.append(f"Unnatural landmark jitter {sigs['landmark_jitter'].get('jitter_score', 0):.2f}px/f²")
        if sigs.get("optical_flow", {}).get("is_suspicious"):
            issues.append("Suspicious optical flow — static/mechanical motion")

    # Behavior
    if behavior.get("status") == "FAIL":
        for sig in behavior.get("signals", {}).values():
            if sig.get("status") == "FAIL":
                issues.append(sig.get("detail", "Behavioral anomaly"))

    if not issues:
        return "All checks passed — live user identity verified"

    return "Issues: " + "; ".join(issues)


def _build_verdict(verdict, risk_score, confidence, face_match, liveness,
                   deepfake, behavior, reason, action, weighted_score=None) -> dict:
    return to_python({
        "verdict":        verdict,
        "risk_score":     risk_score,
        "confidence":     confidence,
        "weighted_score": weighted_score or round(100 - risk_score, 2),
        "action":         action,
        "reason":         reason,
        "layers": {
            "face_match": {
                "score":  face_match.get("score", 0),
                "status": face_match.get("status", "UNKNOWN"),
                "detail": face_match.get("detail", ""),
                "weight": f"{int(WEIGHTS['face_match']*100)}%",
            },
            "liveness": {
                "score":      liveness.get("score", 0),
                "status":     liveness.get("status", "UNKNOWN"),
                "detail":     liveness.get("detail", ""),
                "weight":     f"{int(WEIGHTS['liveness']*100)}%",
                "spoof_risk": liveness.get("spoof_risk", 0),
                "signals":    liveness.get("signals", {}),
            },
            "deepfake": {
                "score":  deepfake.get("score", 0),
                "status": deepfake.get("status", "UNKNOWN"),
                "detail": deepfake.get("detail", ""),
                "weight": f"{int(WEIGHTS['deepfake']*100)}%",
                "signals": deepfake.get("signals", {}),
            },
            "behavior": {
                "score":  behavior.get("score", 0),
                "status": behavior.get("status", "UNKNOWN"),
                "detail": behavior.get("detail", ""),
                "weight": f"{int(WEIGHTS['behavior']*100)}%",
                "signals": behavior.get("signals", {}),
            },
        },
    })
