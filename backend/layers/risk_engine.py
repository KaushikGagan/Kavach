"""
Layer 5: Risk Scoring Engine
- Weighted combination of all layer signals
- Hard gates (instant FAIL conditions)
- Explainable verdict with reason codes
- Fallback to human review on low confidence
"""
from layers.utils import to_python

WEIGHTS = {
    "face_match": 0.30,
    "liveness": 0.30,
    "deepfake": 0.25,
    "behavior": 0.15,
}

HARD_FAIL_CONDITIONS = [
    ("liveness", "replay", "Replay attack detected — session nonce invalid"),
    ("liveness", "nonce_invalid", "Cryptographic session binding failed"),
]


def compute_risk_score(
    face_match: dict,
    liveness: dict,
    deepfake: dict,
    behavior: dict,
) -> dict:

    # ── HARD GATE: Photo spoof — face match alone cannot pass ─────────────
    # This fixes the critical vulnerability where same photo = 100% trust
    if liveness.get("status") == "FAIL":
        spoof_risk = liveness.get("spoof_risk", 50)
        if spoof_risk >= 80:
            return _build_verdict(
                verdict="FRAUD", risk_score=95, confidence=95,
                face_match=face_match, liveness=liveness,
                deepfake=deepfake, behavior=behavior,
                reason=f"HARD BLOCK: {liveness.get('detail', 'Liveness failed')} — face match alone is insufficient",
                action="Block — photo/replay spoof detected",
            )

    # ── HARD GATE: Nonce invalid ───────────────────────────────────────────
    if liveness.get("status") == "FAIL" and "nonce" in liveness.get("detail", "").lower():
        return _build_verdict(
            verdict="FRAUD",
            risk_score=100,
            confidence=99,
            face_match=face_match,
            liveness=liveness,
            deepfake=deepfake,
            behavior=behavior,
            reason="HARD BLOCK: Cryptographic session nonce failed — replay attack prevented",
            action="Block and log incident",
        )

    if deepfake.get("flags_triggered", 0) >= 3:
        return _build_verdict(
            verdict="FRAUD",
            risk_score=95,
            confidence=92,
            face_match=face_match,
            liveness=liveness,
            deepfake=deepfake,
            behavior=behavior,
            reason="HARD BLOCK: 3+ deepfake signals triggered simultaneously",
            action="Block — deepfake media detected",
        )

    # ── Weighted score ─────────────────────────────────────────────────────
    weighted = (
        face_match.get("score", 0) * WEIGHTS["face_match"] +
        liveness.get("score", 0) * WEIGHTS["liveness"] +
        deepfake.get("score", 0) * WEIGHTS["deepfake"] +
        behavior.get("score", 0) * WEIGHTS["behavior"]
    )
    weighted = round(weighted, 2)

    # ── FIX #6: Confidence formula — deterministic, bounded, no overflow ──
    statuses = [
        face_match.get("status"),
        liveness.get("status"),
        deepfake.get("status"),
        behavior.get("status"),
    ]
    pass_count = statuses.count("PASS")
    fail_count = statuses.count("FAIL")
    warn_count = statuses.count("WARN")

    # Confidence = how strongly all layers agree on the outcome
    if weighted >= 60:
        # Leaning SAFE: confidence = weighted score scaled, boosted by unanimous pass
        confidence = int(weighted * 0.85 + pass_count * 3)
    else:
        # Leaning FRAUD: confidence = inverse weighted, boosted by unanimous fail
        confidence = int((100 - weighted) * 0.85 + fail_count * 3)
    confidence = max(40, min(99, confidence))

    # ── Verdict logic ──────────────────────────────────────────────────────
    if weighted >= 75 and fail_count == 0:
        verdict = "SAFE"
        action = "Approve KYC"
    elif weighted >= 55 and fail_count <= 1:
        verdict = "SUSPICIOUS"
        action = "Escalate to manual review"
    else:
        verdict = "FRAUD"
        action = "Block — do not approve"

    # FIX #7: Low confidence escalation applies to ALL verdicts, not just SAFE
    if confidence < 55:
        if verdict == "SAFE":
            verdict = "SUSPICIOUS"
            action = "Low confidence — escalate to manual review"
        elif verdict == "FRAUD" and fail_count < 2:
            # Lone FAIL with low confidence — don’t auto-block, escalate
            verdict = "SUSPICIOUS"
            action = "Low confidence FRAUD signal — escalate to manual review"

    reason = _build_reason(face_match, liveness, deepfake, behavior, verdict)

    return _build_verdict(
        verdict=verdict,
        risk_score=round(100 - weighted, 2),
        confidence=confidence,
        face_match=face_match,
        liveness=liveness,
        deepfake=deepfake,
        behavior=behavior,
        reason=reason,
        action=action,
        weighted_score=weighted,
    )


def _build_reason(face_match, liveness, deepfake, behavior, verdict) -> str:
    issues = []

    if face_match.get("status") == "FAIL":
        issues.append(f"Face match failed ({face_match.get('similarity', 0):.0f}% similarity, need 70%)")
    elif face_match.get("status") == "WARN":
        issues.append(f"Face match weak ({face_match.get('similarity', 0):.0f}% similarity)")

    if liveness.get("status") == "FAIL":
        rppg = liveness.get("signals", {}).get("rppg", {})
        glare = liveness.get("signals", {}).get("glare", {})
        replay = liveness.get("signals", {}).get("replay", {})
        if replay.get("is_replay"):
            issues.append("Video replay attack detected (duplicate frames)")
        if not rppg.get("is_real", True):
            issues.append("No blood flow signal (rPPG) — possible photo or screen spoof")
        if glare.get("is_screen"):
            issues.append("Screen glare detected — possible digital replay")

    if deepfake.get("status") in ("FAIL", "WARN"):
        sigs = deepfake.get("signals", {})
        if sigs.get("frequency", {}).get("is_deepfake"):
            issues.append("GAN frequency artifacts in face region")
        if sigs.get("landmark_jitter", {}).get("is_deepfake"):
            issues.append(f"Unnatural landmark jitter ({sigs['landmark_jitter'].get('jitter_score', 0):.2f}px/f²)")
        if sigs.get("optical_flow", {}).get("is_suspicious"):
            issues.append("Suspicious optical flow (static/mechanical motion)")

    if behavior.get("status") == "FAIL":
        for sig in behavior.get("signals", {}).values():
            if sig.get("status") == "FAIL":
                issues.append(sig.get("detail", "Behavioral anomaly"))

    if not issues:
        return "All checks passed — identity verified"

    return "Issues detected: " + "; ".join(issues)


def _build_verdict(verdict, risk_score, confidence, face_match, liveness,
                   deepfake, behavior, reason, action, weighted_score=None) -> dict:
    return to_python({
        "verdict": verdict,
        "risk_score": risk_score,
        "confidence": confidence,
        "weighted_score": weighted_score or round(100 - risk_score, 2),
        "action": action,
        "reason": reason,
        "layers": {
            "face_match": {
                "score": face_match.get("score", 0),
                "status": face_match.get("status", "UNKNOWN"),
                "detail": face_match.get("detail", ""),
                "weight": f"{int(WEIGHTS['face_match']*100)}%",
            },
            "liveness": {
                "score": liveness.get("score", 0),
                "status": liveness.get("status", "UNKNOWN"),
                "detail": liveness.get("detail", ""),
                "weight": f"{int(WEIGHTS['liveness']*100)}%",
                "signals": liveness.get("signals", {}),
                "spoof_risk": liveness.get("spoof_risk", 0),
            },
            "deepfake": {
                "score": deepfake.get("score", 0),
                "status": deepfake.get("status", "UNKNOWN"),
                "detail": deepfake.get("detail", ""),
                "weight": f"{int(WEIGHTS['deepfake']*100)}%",
                "signals": deepfake.get("signals", {}),
            },
            "behavior": {
                "score": behavior.get("score", 0),
                "status": behavior.get("status", "UNKNOWN"),
                "detail": behavior.get("detail", ""),
                "weight": f"{int(WEIGHTS['behavior']*100)}%",
                "signals": behavior.get("signals", {}),
            },
        },
    })
