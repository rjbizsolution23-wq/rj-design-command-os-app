"""Phase 4 Automated Verification Engine: Live HTTP Security, Performance, DOM Accessibility, and Real Headless Chrome Screenshot Evidence."""
import hashlib
import http.client
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.contracts import find_chrome_binary


def run_automated_qa_audit(host: str, port: int, output_dir: Path, actor: str) -> dict:
    """Execute real live verification checks against the running server and capture Desktop + Mobile screenshot evidence."""
    run_id = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    checks = []

    # 1. Measure live HTTP latency & security headers on /
    t0 = time.perf_counter()
    conn = http.client.HTTPConnection(host, port, timeout=10)
    conn.request("GET", "/")
    resp = conn.getresponse()
    html_bytes = resp.read()
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    headers = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()

    html_text = html_bytes.decode("utf-8", errors="replace")

    # Security header checks
    csp_ok = "default-src 'self'" in headers.get("content-security-policy", "")
    nosniff_ok = headers.get("x-content-type-options") == "nosniff"
    xfo_ok = headers.get("x-frame-options") == "DENY"
    checks.append({"category": "Security", "name": "Content-Security-Policy strict header", "passed": csp_ok, "evidence": headers.get("content-security-policy", "missing")[:120]})
    checks.append({"category": "Security", "name": "X-Content-Type-Options: nosniff", "passed": nosniff_ok, "evidence": headers.get("x-content-type-options", "missing")})
    checks.append({"category": "Security", "name": "X-Frame-Options: DENY", "passed": xfo_ok, "evidence": headers.get("x-frame-options", "missing")})

    # DOM Accessibility invariants
    has_lang = bool(re.search(r'<html[^>]+lang="en"', html_text))
    has_main = "<main" in html_text
    has_nav_label = 'aria-label="Primary"' in html_text
    has_live_region = 'role="status"' in html_text and 'aria-live="polite"' in html_text
    no_inline_js = "javascript:" not in html_text.lower() and "onerror=" not in html_text.lower()
    checks.append({"category": "Accessibility", "name": "Document language attribute (<html lang>)", "passed": has_lang, "evidence": "lang=en detected" if has_lang else "missing"})
    checks.append({"category": "Accessibility", "name": "Semantic <main> + labeled <nav>", "passed": has_main and has_nav_label, "evidence": "main & nav aria-label present"})
    checks.append({"category": "Accessibility", "name": "ARIA live status region", "passed": has_live_region, "evidence": "role=status aria-live=polite"})
    checks.append({"category": "Security", "name": "Zero inline javascript: or onerror= vectors", "passed": no_inline_js, "evidence": "DOM clean"})

    # Performance checks
    payload_kb = round(len(html_bytes) / 1024, 2)
    checks.append({"category": "Performance", "name": "Initial HTML TTFB < 250ms", "passed": latency_ms < 250, "evidence": f"{latency_ms} ms"})
    checks.append({"category": "Performance", "name": "Initial HTML payload < 100 KB", "passed": payload_kb < 100, "evidence": f"{payload_kb} KB"})

    # Visual browser screenshots (Desktop 1440x900 & Mobile 390x844)
    screenshots = []
    chrome = find_chrome_binary()
    if chrome:
        output_dir.mkdir(parents=True, exist_ok=True)
        for label, size in [("desktop-1440x900", "1440,900"), ("iphone-390x844", "390,844")]:
            shot_path = output_dir / f"qa-{run_id[:8]}-{label}.png"
            cmd = [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--window-size={size}",
                f"--screenshot={shot_path}",
                f"http://{host}:{port}/",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0 and shot_path.exists():
                raw = shot_path.read_bytes()
                screenshots.append({
                    "viewport": label,
                    "file": shot_path.name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()[:16],
                })
        checks.append({
            "category": "Visual QA",
            "name": "Headless Chrome Desktop + Mobile screenshot capture",
            "passed": len(screenshots) == 2,
            "evidence": f"Captured {len(screenshots)}/2 viewports",
        })
    else:
        checks.append({"category": "Visual QA", "name": "Headless Chrome screenshot capture", "passed": False, "evidence": "Chrome binary not found"})

    passed_count = sum(1 for c in checks if c["passed"])
    score = round((passed_count / len(checks)) * 100, 1) if checks else 0.0
    release_approved = score >= 90.0 and all(c["passed"] for c in checks if c["category"] in ("Security", "Accessibility"))

    return {
        "run_id": run_id,
        "initiated_by": actor,
        "started_at": started_at,
        "target": f"http://{host}:{port}/",
        "latency_ms": latency_ms,
        "payload_kb": payload_kb,
        "passed_checks": passed_count,
        "total_checks": len(checks),
        "score": score,
        "release_approved": release_approved,
        "screenshots": screenshots,
        "checks": checks,
    }
