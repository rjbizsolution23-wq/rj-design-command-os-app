"""Versioned Design Contracts, Schema Validation, Safe Investor Documents, and Headless Chrome PDF Pipeline."""
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "2.1.0"
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
CSS_LEN_RE = re.compile(r"^\d+(\.\d+)?(px|rem|em)$")

DEFAULT_BRAND_KIT = {
    "contract_version": CONTRACT_VERSION,
    "version": "2.1.0",
    "edition": "Sovereign Luxury Investor",
    "identity": {
        "firm_name": "RJ Business Solutions",
        "principal": "Rick Jefferson",
        "principal_title": "Founder & Managing Principal",
        "subline": "PRIVATE CAPITAL & INSTITUTIONAL ARCHITECTURE",
        "positioning": "Institutional capital architecture, sovereign private-wealth technology, high-conviction credit infrastructure, and bespoke executive digital platforms engineered for accredited investors, family offices, and enterprise principals.",
        "website": "https://rjbusinesssolutions.org",
        "executive_website": "https://rickjefferson.com",
        "client_portal": "https://rickjefferson.com/portal/",
        "booking_url": "https://rickjefferson.com/executive-session/",
        "email": "support@rjbusinesssolutions.org",
        "executive_email": "rick@rickjefferson.com",
        "telephone": "(817) 587-4783",
        "dfw_hq_address": "99 Regency Pkwy., Suite 305, Mansfield, TX 76063",
        "address": "1342 NM 333, Tijeras, New Mexico 87059",
        "logo_url": "/vault/logos/rj-luxury-black-gold-logo-primary.png",
        "legal_disclaimer": "RJ Business Solutions provides institutional software and automation technology. Not financial, investment, or legal advice.",
    },
    "palette": {
        "obsidian": "#0A0B0E",
        "vault": "#12141A",
        "graphite": "#1C2029",
        "gold": "#C5A059",
        "champagne": "#DFC48C",
        "bronze": "#8A6A2F",
        "ivory": "#FFFFFF",
        "alabaster": "#FAF8F5",
        "parchment": "#F3EFE6",
        "gold_border": "#E4D9C3",
        "stone_line": "#E6E2DA",
        "ink": "#111318",
        "muted_text": "#4A4E5A",
        "emerald": "#1B5E4B",
        "amber": "#9A6B26",
        "crimson": "#8C2D36",
    },
    "typography": {
        "display_font": "Taillevere",
        "secondary_serif": "Auretha",
        "editorial_serif": "Siovanni",
        "prestige_display": "Galante",
        "body_font": "Xenon Nue",
        "numeric_font": "Grift",
        "impact_display": "Vank",
        "overline_tracking": "0.22em",
        "heading_weight": "500",
        "body_size": "14px",
    },
    "geometry": {
        "doc_radius": "4px",
        "portal_radius": "10px",
        "button_radius": "4px",
        "hairline_width": "1px",
    },
    "governance": {
        "aesthetic_tier": "Billion-Dollar Institutional Private Wealth",
        "accessibility_target": "WCAG 2.2 AA",
        "release_gate_score": 90,
        "settlement_policy": "Strictly decoupled from universal brand templates; requires verified & principal-approved settlement record.",
        "banned_patterns": "Developer-SaaS Electric Blue (#2563eb), Space Grotesk, Neon Cyan, Sci-Fi Hacker Themes",
    },
}


def _luminance(hex_color: str) -> float:
    clean = hex_color.lstrip("#")
    r, g, b = (int(clean[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def validate_brand_contract(kit: dict) -> dict:
    errors = []
    warnings = []

    palette = kit.get("palette", {})
    for key, val in palette.items():
        if not isinstance(val, str) or not HEX_RE.match(val):
            errors.append(f"palette.{key}: expected 6-digit HEX color, got {val!r}")

    typography = kit.get("typography", {})
    for key in ("display_font", "body_font", "numeric_font"):
        if not str(typography.get(key, "")).strip():
            errors.append(f"typography.{key}: font family is required")

    geometry = kit.get("geometry", {})
    for key in ("doc_radius", "portal_radius", "button_radius", "hairline_width"):
        val = str(geometry.get(key, ""))
        if not CSS_LEN_RE.match(val):
            errors.append(f"geometry.{key}: invalid CSS length {val!r}")

    identity = kit.get("identity", {})
    for forbidden in ("settlement_wire_routing", "settlement_zelle", "routing_number", "account_number"):
        if forbidden in identity:
            errors.append(f"identity.{forbidden}: banking/settlement data is prohibited inside universal brand templates")

    # Contrast verification if palette is valid
    contrast_checks = []
    if not any(e.startswith("palette.") for e in errors):
        pairs = [
            ("Ivory on Obsidian", "#F5F2EB", palette["obsidian"], 4.5),
            ("Champagne on Obsidian", palette["champagne"], palette["obsidian"], 4.5),
            ("Obsidian on Gold CTA", palette["obsidian"], palette["gold"], 4.5),
            ("Ink on Alabaster Paper", palette["ink"], palette["alabaster"], 4.5),
            ("Bronze on Ivory", palette["bronze"], palette["ivory"], 4.5),
        ]
        for label, fg, bg, minimum in pairs:
            ratio = contrast_ratio(fg, bg)
            passed = ratio >= minimum
            contrast_checks.append({"pair": label, "ratio": ratio, "passed": passed, "minimum": minimum})
            if not passed:
                warnings.append(f"Contrast below {minimum}:1 for {label} ({ratio}:1)")

    return {
        "valid": len(errors) == 0,
        "contract_version": CONTRACT_VERSION,
        "errors": errors,
        "warnings": warnings,
        "contrast_checks": contrast_checks,
    }


def export_css(kit: dict) -> str:
    p = kit["palette"]
    t = kit["typography"]
    g = kit["geometry"]
    ident = kit["identity"]
    return f"""/* ═══════════════════════════════════════════════════════════════════
   {ident['firm_name']} · {kit['edition']} Design Tokens · Contract v{CONTRACT_VERSION}
   Generated by RJ Design Command OS
   ═══════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Manrope:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {{
  --rj-obsidian:    {p['obsidian']};
  --rj-vault:       {p['vault']};
  --rj-graphite:    {p['graphite']};
  --rj-gold:        {p['gold']};
  --rj-champagne:   {p['champagne']};
  --rj-bronze:      {p['bronze']};
  --rj-ivory:       {p['ivory']};
  --rj-alabaster:   {p['alabaster']};
  --rj-parchment:   {p['parchment']};
  --rj-gold-border: {p['gold_border']};
  --rj-stone-line:  {p['stone_line']};
  --rj-ink:         {p['ink']};
  --rj-muted-text:  {p['muted_text']};
  --rj-emerald:     {p['emerald']};
  --rj-amber:       {p['amber']};
  --rj-crimson:     {p['crimson']};

  --font-display: "{t['display_font']}", "Playfair Display", Georgia, serif;
  --font-body:    "{t['body_font']}", "Manrope", system-ui, sans-serif;
  --font-num:     "{t['numeric_font']}", "Plus Jakarta Sans", system-ui, sans-serif;
  --tracking-seal: {t['overline_tracking']};

  --radius-doc:    {g['doc_radius']};
  --radius-portal: {g['portal_radius']};
  --radius-btn:    {g['button_radius']};
  --hairline:      {g['hairline_width']};

  --grad-dark: linear-gradient(135deg, {p['obsidian']} 0%, {p['vault']} 55%, {p['graphite']} 100%);
  --grad-gold: linear-gradient(135deg, {p['bronze']} 0%, {p['champagne']} 50%, {p['gold']} 100%);
  --logo-url:  url("{ident['logo_url']}");
}}
"""


def export_tailwind(kit: dict) -> str:
    p = kit["palette"]
    t = kit["typography"]
    g = kit["geometry"]
    return f"""/* Tailwind CSS v4 — {kit['identity']['firm_name']} Sovereign Luxury Investor Theme (Contract v{CONTRACT_VERSION}) */
@import "tailwindcss";

@theme {{
  --color-rj-obsidian: {p['obsidian']};
  --color-rj-vault: {p['vault']};
  --color-rj-graphite: {p['graphite']};
  --color-rj-gold: {p['gold']};
  --color-rj-champagne: {p['champagne']};
  --color-rj-bronze: {p['bronze']};
  --color-rj-ivory: {p['ivory']};
  --color-rj-alabaster: {p['alabaster']};
  --color-rj-parchment: {p['parchment']};
  --color-rj-gold-border: {p['gold_border']};
  --color-rj-stone-line: {p['stone_line']};
  --color-rj-ink: {p['ink']};
  --color-rj-muted: {p['muted_text']};
  --color-rj-emerald: {p['emerald']};
  --color-rj-amber: {p['amber']};
  --color-rj-crimson: {p['crimson']};

  --font-display: "{t['display_font']}", Georgia, serif;
  --font-sans: "{t['body_font']}", system-ui, sans-serif;
  --font-num: "{t['numeric_font']}", system-ui, sans-serif;

  --radius-doc: {g['doc_radius']};
  --radius-portal: {g['portal_radius']};
  --radius-btn: {g['button_radius']};
}}
"""


def export_memo_html(kit: dict, settlement_record: dict | None = None) -> str:
    """Render Confidential Executive Memorandum. Never embeds hardcoded banking details."""
    p = kit["palette"]
    t = kit["typography"]
    ident = kit["identity"]
    esc = html.escape
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if settlement_record and settlement_record.get("approval_status") == "approved" and settlement_record.get("recipient_verified"):
        settlement_html = f"""
    <span class="section-seal">03 · AUTHORIZED SETTLEMENT RECORD ({esc(settlement_record['id'][:8].upper())})</span>
    <div class="settlement">
      <div class="card">
        <h4>Verified {esc(settlement_record['method'].upper())} Instruction</h4>
        <p><strong>Counterparty:</strong> {esc(settlement_record['recipient_name'])}<br>
        <strong>Institution / Channel:</strong> {esc(settlement_record['institution'])}<br>
        <strong>Authorized Reference:</strong> {esc(settlement_record['reference_code'])}</p>
      </div>
      <div class="card">
        <h4>Governance &amp; Approval Audit</h4>
        <p><strong>Status:</strong> APPROVED &amp; RECIPIENT VERIFIED<br>
        <strong>Approved By:</strong> {esc(settlement_record['approved_by'])}<br>
        <strong>Audit Timestamp:</strong> {esc(settlement_record['updated_at'])}</p>
      </div>
    </div>"""
    else:
        settlement_html = """
    <span class="section-seal">03 · SETTLEMENT SECURITY PROTOCOL</span>
    <div class="card">
      <h4>Protected Settlement Issuance</h4>
      <p>Banking and settlement instructions are strictly separated from universal brand templates. Verified wire or settlement details are issued exclusively through an authorized, principal-approved transaction record after counterparty KYC/AML verification.</p>
    </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(ident['firm_name'])} — Confidential Executive Memorandum</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Manrope:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  @page {{ size: Letter; margin: 0.45in; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 36px 24px; background: {p['alabaster']}; color: {p['ink']}; font-family: '{esc(t['body_font'])}', system-ui, sans-serif; font-size: 13.5px; line-height: 1.65; }}
  .sheet {{ max-width: 920px; margin: 0 auto; background: {p['ivory']}; border: 1px solid {p['gold_border']}; box-shadow: 0 24px 60px rgba(10,11,14,0.08); }}
  .hero {{ background: linear-gradient(135deg, {p['obsidian']} 0%, {p['vault']} 55%, {p['graphite']} 100%); color: #F5F2EB; padding: 40px 44px; border-bottom: 2px solid {p['gold']}; display: flex; justify-content: space-between; align-items: center; gap: 24px; }}
  .brand-lockup {{ display: flex; align-items: center; gap: 18px; }}
  .brand-lockup img {{ width: 52px; height: 52px; object-fit: cover; border-radius: 4px; border: 1px solid rgba(197,160,89,0.55); }}
  .firm {{ font-family: '{esc(t['display_font'])}', Georgia, serif; font-size: 29px; font-weight: 600; letter-spacing: 0.04em; margin: 0; }}
  .subline {{ font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; color: {p['champagne']}; margin-top: 6px; font-weight: 600; }}
  .seal {{ border: 1px solid rgba(197,160,89,0.45); background: rgba(197,160,89,0.1); color: {p['champagne']}; padding: 8px 14px; font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase; font-weight: 600; }}
  .meta-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid {p['stone_line']}; background: {p['parchment']}; }}
  .meta-cell {{ padding: 15px 20px; border-right: 1px solid {p['stone_line']}; }}
  .meta-cell:last-child {{ border-right: 0; }}
  .meta-cell small {{ display: block; font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: {p['bronze']}; font-weight: 700; }}
  .meta-cell strong {{ display: block; margin-top: 4px; font-size: 13px; color: {p['ink']}; }}
  .content {{ padding: 40px 44px; }}
  .section-seal {{ display: inline-block; background: {p['parchment']}; color: {p['bronze']}; border: 1px solid {p['gold_border']}; padding: 5px 12px; font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase; font-weight: 700; margin-bottom: 14px; }}
  h2 {{ font-family: '{esc(t['display_font'])}', Georgia, serif; font-size: 32px; font-weight: 500; margin: 0 0 14px; color: {p['ink']}; }}
  p {{ color: {p['muted_text']}; margin: 0 0 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0 30px; font-family: '{esc(t['numeric_font'])}', sans-serif; font-variant-numeric: tabular-nums; page-break-inside: avoid; }}
  th {{ text-align: left; background: {p['parchment']}; color: {p['bronze']}; font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; padding: 13px 16px; border-top: 1px solid {p['gold_border']}; border-bottom: 1px solid {p['gold_border']}; }}
  td {{ padding: 13px 16px; border-bottom: 1px solid {p['stone_line']}; font-size: 13px; }}
  td.num, th.num {{ text-align: right; }}
  tr.total td {{ font-weight: 700; color: {p['ink']}; border-top: 2px solid {p['gold']}; background: {p['alabaster']}; }}
  .settlement {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 20px 0 28px; page-break-inside: avoid; }}
  .card {{ border: 1px solid {p['gold_border']}; background: {p['alabaster']}; padding: 18px 20px; page-break-inside: avoid; }}
  .card h4 {{ font-family: '{esc(t['display_font'])}', Georgia, serif; font-size: 20px; margin: 0 0 8px; }}
  .signatures {{ display: grid; grid-template-columns: 1fr 1fr; gap: 36px; margin-top: 34px; padding-top: 24px; border-top: 1px solid {p['stone_line']}; page-break-inside: avoid; }}
  .sig-line {{ border-bottom: 1px solid {p['ink']}; height: 40px; margin-bottom: 10px; }}
  .footer {{ background: {p['obsidian']}; color: #B3AFA6; padding: 20px 44px; font-size: 11px; display: flex; justify-content: space-between; gap: 20px; }}
  @media print {{ body {{ padding: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }} .sheet {{ box-shadow: none; border: 0; }} }}
</style>
</head>
<body>
<article class="sheet">
  <header class="hero">
    <div class="brand-lockup">
      <img src="{esc(ident['logo_url'])}" alt="{esc(ident['firm_name'])}">
      <div>
        <h1 class="firm">{esc(ident['firm_name'])}</h1>
        <div class="subline">{esc(ident['subline'])}</div>
      </div>
    </div>
    <div class="seal">CONFIDENTIAL · LP BRIEF</div>
  </header>
  <div class="meta-bar">
    <div class="meta-cell"><small>PREPARED FOR</small><strong>Accredited Institutional Partner</strong></div>
    <div class="meta-cell"><small>MANAGING PRINCIPAL</small><strong>{esc(ident['principal'])}</strong></div>
    <div class="meta-cell"><small>DATE OF ISSUE</small><strong>{today}</strong></div>
    <div class="meta-cell"><small>CONTRACT VERSION</small><strong>v{CONTRACT_VERSION} · Verified</strong></div>
  </div>
  <div class="content">
    <span class="section-seal">01 · EXECUTIVE MANDATE</span>
    <h2>Institutional Capital &amp; Sovereign Architecture</h2>
    <p>{esc(ident['positioning'])}</p>

    <span class="section-seal">02 · INDICATIVE ARCHITECTURE SCHEDULE</span>
    <table>
      <thead><tr><th>Mandate Component</th><th>Classification</th><th class="num">Indicative Allocation</th></tr></thead>
      <tbody>
        <tr><td>Sovereign Brand &amp; Investor Portal Infrastructure</td><td>Core Platform</td><td class="num">$150,000</td></tr>
        <tr><td>Private Credit &amp; Institutional Underwriting Engine</td><td>Proprietary IP</td><td class="num">$250,000</td></tr>
        <tr><td>Dedicated Family Office Concierge &amp; Governance Suite</td><td>Compliance</td><td class="num">$100,000</td></tr>
        <tr class="total"><td colspan="2">Total Indicative Institutional Mandate</td><td class="num">$500,000</td></tr>
      </tbody>
    </table>

    {settlement_html}

    <div class="signatures">
      <div><div class="sig-line"></div><strong>{esc(ident['principal'])}</strong><br><small>{esc(ident['principal_title'])}, {esc(ident['firm_name'])}</small></div>
      <div><div class="sig-line"></div><strong>Authorized Institutional Signatory</strong><br><small>Counterparty / Limited Partner Representative</small></div>
    </div>
  </div>
  <footer class="footer">
    <div>{esc(ident['firm_name'])} · {esc(ident['address'])} · {esc(ident['website'])}</div>
    <div>{esc(ident['legal_disclaimer'])}</div>
  </footer>
</article>
</body>
</html>"""


def find_chrome_binary() -> str | None:
    candidates = [
        os.environ.get("RJ_CHROME_BIN", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def render_pdf_bytes(html_content: str) -> bytes:
    """Render HTML into a real binary PDF via local Headless Chrome."""
    chrome = find_chrome_binary()
    if not chrome:
        raise RuntimeError("Headless Chrome binary not found for PDF rendering")
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "memo.html"
        pdf_path = Path(tmp) / "memo.pdf"
        html_path.write_text(html_content, encoding="utf-8")
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(f"PDF render failed: {result.stderr[:300]}")
        data = pdf_path.read_bytes()
        if not data.startswith(b"%PDF-"):
            raise RuntimeError("Rendered output is not a valid PDF binary")
        return data
