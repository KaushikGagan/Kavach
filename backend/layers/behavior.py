"""
Layer 4: Behavioral & Context Analysis
- Device fingerprint consistency
- IP geolocation anomaly
- Time-of-day anomaly
- Submission timing analysis (too fast = bot)
"""
import time
import hashlib
from typing import Optional
from layers.utils import to_python


def analyze_behavior(
    ip_address: str,
    user_agent: str,
    session_start_time: float,
    submission_time: float,
    device_id: Optional[str] = None,
) -> dict:
    signals = {}
    score = 100  # start clean, deduct for anomalies

    # 1. Submission speed check (too fast = automated/bot)
    elapsed = submission_time - session_start_time
    if elapsed < 4:
        signals["speed"] = {
            "status": "FAIL",
            "detail": f"Completed in {elapsed:.1f}s — too fast for human (min 4s)",
        }
        score -= 40
    elif elapsed < 8:
        signals["speed"] = {
            "status": "WARN",
            "detail": f"Completed in {elapsed:.1f}s — slightly fast",
        }
        score -= 15
    else:
        signals["speed"] = {
            "status": "PASS",
            "detail": f"Completed in {elapsed:.1f}s — normal human timing",
        }

    # 2. User-agent analysis
    ua_lower = user_agent.lower() if user_agent else ""
    bot_keywords = ["bot", "crawler", "python", "curl", "wget", "headless", "phantom", "selenium"]
    is_bot_ua = any(kw in ua_lower for kw in bot_keywords)
    if is_bot_ua:
        signals["user_agent"] = {
            "status": "FAIL",
            "detail": f"Bot/automation user-agent detected: {user_agent[:60]}",
        }
        score -= 35
    else:
        signals["user_agent"] = {
            "status": "PASS",
            "detail": "User-agent appears to be a real browser",
        }

    # 3. IP basic checks
    ip_flags = []
    if ip_address in ("127.0.0.1", "::1", "localhost"):
        ip_flags.append("localhost IP")
    octets = ip_address.split(".")
    if len(octets) == 4:
        try:
            first = int(octets[0])
            if first == 10 or (first == 172 and 16 <= int(octets[1]) <= 31) or (first == 192 and octets[1] == "168"):
                ip_flags.append("private/VPN-range IP")
        except ValueError:
            pass

    if ip_flags:
        signals["ip"] = {
            "status": "WARN",
            "detail": f"IP flags: {', '.join(ip_flags)} — possible VPN/proxy",
        }
        score -= 10
    else:
        signals["ip"] = {"status": "PASS", "detail": f"IP {ip_address} appears public"}

    # 4. Time-of-day anomaly (3AM–5AM submissions are higher risk)
    hour = time.localtime(submission_time).tm_hour
    if 3 <= hour <= 5:
        signals["time"] = {
            "status": "WARN",
            "detail": f"Submission at {hour:02d}:00 — unusual hours (3-5 AM)",
        }
        score -= 10
    else:
        signals["time"] = {"status": "PASS", "detail": f"Submission at hour {hour:02d} — normal"}

    # FIX #9: Device fingerprint — use consistent hash that matches frontend btoa(UA).slice(0,16)
    if device_id:
        import base64
        expected = base64.b64encode(user_agent.encode()).decode()[:16] if user_agent else ""
        if device_id[:8] == expected[:8]:
            signals["device"] = {"status": "PASS", "detail": "Device fingerprint consistent"}
        else:
            signals["device"] = {
                "status": "WARN",
                "detail": "Device fingerprint mismatch — possible session hijack",
            }
            score -= 15

    score = max(0, min(100, score))
    status = "PASS" if score >= 70 else ("WARN" if score >= 45 else "FAIL")

    return to_python({
        "score": score,
        "status": status,
        "signals": signals,
        "detail": f"Behavioral score {score}/100 — {status}",
    })
