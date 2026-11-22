#!/usr/bin/env python3
"""RJ Design Command OS v2.1 — Sovereign Luxury Investor Design System, AI Creative Director & Production-Hardened Server."""
import json
import mimetypes
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from core.contracts import (
    CONTRACT_VERSION,
    DEFAULT_BRAND_KIT,
    export_css,
    export_memo_html,
    export_tailwind,
    find_chrome_binary,
    render_pdf_bytes,
    validate_brand_contract,
)
from core.orchestrator import (
    DEPARTMENTS,
    INDUSTRY_REGISTRY,
    generate_react_scaffold,
    run_creative_director_pipeline,
)
from core.production import (
    build_react_zip_bundle,
    generate_3d_scene_package,
    generate_commercial_asset,
    inspect_local_repository,
)
from core.envato_connector import (
    ingest_envato_zip,
    install_asset_into_project,
    list_envato_vault,
    search_envato,
)
from core.qa_engine import run_automated_qa_audit
from core.security import (
    SlidingWindowRateLimiter,
    has_permission,
    hash_password,
    issue_session_token,
    verify_password,
    verify_session_token,
)

ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("RJ_DESIGN_DB", str(ROOT / "data" / "design.sqlite3")))
BACKUP_DIR = Path(os.environ.get("RJ_DESIGN_BACKUPS", str(ROOT / "data" / "backups")))
DEFAULT_ADMIN_PASSWORD = os.environ.get("RJ_ADMIN_PASSWORD", "Sovereign#2026!")
RATE_LIMITER = SlidingWindowRateLimiter(
    max_requests=int(os.environ.get("RJ_RATE_LIMIT_MAX", "180")),
    window_seconds=int(os.environ.get("RJ_RATE_LIMIT_WINDOW", "60")),
)

STYLES = [
    {"id": "sovereign", "name": "Sovereign Private Wealth", "category": "Flagship Investor", "font": "Cormorant Garamond + Plus Jakarta Sans", "colors": ["#0A0B0E", "#C5A059", "#FAF8F5"], "traits": ["investor", "wealth", "capital", "family office", "fund", "private equity", "sovereign", "billion", "accredited", "institutional"], "description": "RJ Business Solutions Global Brand Standard v2.1. Sovereign Obsidian vaults, burnished champagne gold hairlines, and fine alabaster editorial authority.", "is_default": True},
    {"id": "heritage", "name": "Heritage Family Office", "category": "Private Wealth", "font": "Cormorant Garamond + Manrope", "colors": ["#0E131B", "#D4B98C", "#F6F2EA"], "traits": ["heritage", "estate", "legal", "trust", "legacy", "multi-generational", "banking"], "description": "Old-world institutional gravitas with deep ink surfaces, restrained champagne metallic accents, and classical serif hierarchy.", "is_default": False},
    {"id": "geneva", "name": "Geneva Private Bank", "category": "Institutional", "font": "Playfair Display + Plus Jakarta Sans", "colors": ["#101815", "#B89B5E", "#F5F3EE"], "traits": ["bank", "treasury", "credit", "vault", "compliance", "audit", "swiss", "reserve"], "description": "Quiet Swiss private-banking restraint pairing racing-emerald shadows with brushed brass and crisp tabular capital reporting.", "is_default": False},
    {"id": "editorial", "name": "Architectural Editorial", "category": "Executive", "font": "Newsreader + Plus Jakarta Sans", "colors": ["#FAF7F2", "#14161B", "#9A7442"], "traits": ["memorandum", "report", "consulting", "strategy", "founder", "boardroom", "publication"], "description": "Commanding cotton-paper negative space, disciplined Swiss grid proportions, and gallery-grade investor storytelling.", "is_default": False},
    {"id": "manhattan", "name": "Manhattan Institutional", "category": "Capital Markets", "font": "Libre Baskerville + Manrope", "colors": ["#0C1018", "#9EA7B8", "#F4F5F7"], "traits": ["markets", "hedge fund", "securities", "reg d", "ma", "deal", "underwriting"], "description": "High-conviction Wall Street institutional precision with architectural platinum accents and ultra-legible financial schedules.", "is_default": False},
    {"id": "estate", "name": "Sovereign Real Estate", "category": "Real Assets", "font": "Cormorant Garamond + DM Sans", "colors": ["#1A1815", "#C7A97B", "#F2EDE4"], "traits": ["real estate", "property", "hospitality", "resort", "development", "luxury", "architecture"], "description": "Tactile limestone, warm travertine neutrals, and architectural photography framing for trophy assets and developments.", "is_default": False},
    {"id": "atelier", "name": "Haute Atelier", "category": "Luxury Brand", "font": "Italiana + Plus Jakarta Sans", "colors": ["#09090B", "#E2CFA8", "#F8F6F2"], "traits": ["couture", "fashion", "watch", "jewelry", "bespoke", "editorial", "cinema"], "description": "Runway-calibrated monochrome luxury with razor-sharp hairlines, dramatic proportion contrast, and tactile quietness.", "is_default": False},
    {"id": "aviation", "name": "Private Aviation & Marine", "category": "Ultra-HNW", "font": "Cinzel + Manrope", "colors": ["#0B131E", "#C9A86A", "#EDF0F4"], "traits": ["aviation", "yacht", "jet", "concierge", "charter", "members", "club"], "description": "Deep maritime obsidian, brushed champagne instrumentation, and bespoke private-club concierge clarity.", "is_default": False},
    {"id": "organic", "name": "Quiet Luxury Sanctuary", "category": "Hospitality", "font": "Fraunces + Manrope", "colors": ["#1E2520", "#C4AE8A", "#F4F0E8"], "traits": ["sanctuary", "wellness", "hotel", "dining", "retreat", "lifestyle", "organic"], "description": "Aman-inspired architectural serenity built on natural stone, muted cedar, and unhurried typographic cadence.", "is_default": False},
    {"id": "venture", "name": "Bespoke Venture Capital", "category": "Growth Capital", "font": "Instrument Serif + Plus Jakarta Sans", "colors": ["#0D1017", "#D4B475", "#F7F6F2"], "traits": ["venture", "ai", "technology", "portfolio", "series", "scale", "innovation"], "description": "Elevated institutional venture aesthetic that communicates billion-dollar thesis conviction without generic startup tropes.", "is_default": False},
    {"id": "precision", "name": "Executive Intelligence", "category": "LP Operations", "font": "Cormorant Garamond + Manrope", "colors": ["#0D1117", "#1B5E4B", "#F3F1EC"], "traits": ["dashboard", "portal", "analytics", "crm", "operations", "reporting", "enterprise"], "description": "High-density LP portfolio telemetry engineered with tabular figures, emerald yield markers, and zero visual clutter.", "is_default": False},
    {"id": "philanthropy", "name": "Foundation & Endowment", "category": "Endowment", "font": "Newsreader + Manrope", "colors": ["#17191C", "#B08D57", "#FAF8F4"], "traits": ["foundation", "endowment", "grant", "civic", "impact", "governance", "board"], "description": "Enduring civic and endowment typography designed for annual letters, governance charters, and multi-decade stewardship.", "is_default": False},
]

# Upgraded 10-Category 100-Point Evidence-Driven Quality Rubric
CATEGORIES = [
    ("UX and critical task completion", 20),
    ("Visual distinction and brand accuracy", 15),
    ("Accessibility", 15),
    ("Responsive experience", 10),
    ("Architecture and component quality", 10),
    ("Performance", 10),
    ("Motion and interaction", 5),
    ("Content accuracy and trust", 5),
    ("Security and privacy", 5),
    ("Test evidence", 5),
]

CRITICAL_CATEGORIES = (
    "UX and critical task completion",
    "Accessibility",
    "Performance",
    "Security and privacy",
)

COMPONENT_REGISTRY = [
    {"id": "sovereign-hero", "name": "Private Placement Hero Banner", "category": "Executive Headers", "wcag": "AAA (16.8:1)", "description": "Obsidian-to-graphite architectural header with fine champagne gold rule, institutional seal, and serif headline."},
    {"id": "lp-kpi-grid", "name": "LP Capital & Yield Metric Cards", "category": "Data Telemetry", "wcag": "AA (12.4:1)", "description": "Tabular-aligned AUM, Target IRR, Committed Capital, and Distribution cards with emerald yield delta indicators."},
    {"id": "capital-table", "name": "Institutional Capital Schedule", "category": "Financial Tables", "wcag": "AAA (15.1:1)", "description": "Right-aligned tabular financial ledger with parchment/obsidian header bands and gold-ruled total rows."},
    {"id": "sovereign-buttons", "name": "Executive Action Controls", "category": "Actions", "wcag": "AA (8.9:1)", "description": "Burnished Gold primary CTA, Obsidian authority CTA, and Hairline Gold Ghost button with subtle luxury easing."},
    {"id": "accreditation-seals", "name": "Accreditation & Tier Seals", "category": "Status & Badges", "wcag": "AA (7.2:1)", "description": "Wide-tracked uppercase institutional classification badges (Reg D 506(c), Qualified Purchaser, Verified LP)."},
    {"id": "protected-settlement", "name": "Protected Settlement Vault Card", "category": "Capital Operations", "wcag": "AA (11.8:1)", "description": "Authorized, principal-approved settlement issuance widget decoupled from universal brand templates."},
    {"id": "signature-block", "name": "Dual-Party Execution Block", "category": "Legal & Closing", "wcag": "AAA (14.2:1)", "description": "Formal boardroom signature lines for Managing Principal Rick Jefferson and Counterparty / Limited Partner."},
    {"id": "advisory-callout", "name": "Compliance & Fiduciary Notice", "category": "Governance", "wcag": "AA (10.5:1)", "description": "Left-gold-bordered institutional disclosure block for CROA, SEC Reg D, and non-advisory software notices."},
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, industry TEXT NOT NULL, audience TEXT NOT NULL, brief TEXT NOT NULL, mood TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS directions (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, style_id TEXT NOT NULL, score INTEGER NOT NULL, rationale TEXT NOT NULL, selected INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, label TEXT NOT NULL, value TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, name TEXT NOT NULL, metrics TEXT NOT NULL, score REAL NOT NULL, blockers TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS brand_settings (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS settlement_records (id TEXT PRIMARY KEY, project_id TEXT, recipient_name TEXT NOT NULL, recipient_verified INTEGER NOT NULL DEFAULT 0, method TEXT NOT NULL, institution TEXT NOT NULL, reference_code TEXT NOT NULL, approval_status TEXT NOT NULL DEFAULT 'pending', approved_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS orchestration_runs (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, asset_type TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT NOT NULL, mime_type TEXT NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL, commercial_rights TEXT NOT NULL, created_by TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS qa_runs (id TEXT PRIMARY KEY, score REAL NOT NULL, release_approved INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS audit_logs (id TEXT PRIMARY KEY, actor TEXT NOT NULL, role TEXT NOT NULL, action TEXT NOT NULL, resource TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL)")

    if not db.execute("SELECT id FROM brand_settings WHERE id='global'").fetchone():
        db.execute("INSERT INTO brand_settings VALUES (?,?,?)", ("global", json.dumps(DEFAULT_BRAND_KIT), now()))

    # Seed default local accounts (principal, director, viewer) if none exist
    if not db.execute("SELECT id FROM users LIMIT 1").fetchone():
        ts = now()
        db.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uuid.uuid4().hex, "principal", hash_password(DEFAULT_ADMIN_PASSWORD), "principal", ts))
        db.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uuid.uuid4().hex, "director", hash_password(DEFAULT_ADMIN_PASSWORD), "director", ts))
        db.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uuid.uuid4().hex, "viewer", hash_password(DEFAULT_ADMIN_PASSWORD), "viewer", ts))

    db.commit()
    return db


def log_audit(db: sqlite3.Connection, actor: str, role: str, action: str, resource: str, details: str = ""):
    db.execute(
        "INSERT INTO audit_logs VALUES (?,?,?,?,?,?,?)",
        (uuid.uuid4().hex, actor, role, action, resource, details[:500], now()),
    )


def get_brand_kit(db: sqlite3.Connection) -> dict:
    row = db.execute("SELECT payload, updated_at FROM brand_settings WHERE id='global'").fetchone()
    if not row:
        return dict(DEFAULT_BRAND_KIT)
    stored = json.loads(row["payload"])
    # Scrub any legacy hardcoded settlement keys if migrating from v2.0 SQLite DB
    ident = stored.get("identity", {})
    for forbidden in ("settlement_wire_routing", "settlement_wire_bank", "settlement_zelle"):
        ident.pop(forbidden, None)
    kit = deep_merge(DEFAULT_BRAND_KIT, stored)
    kit["contract_version"] = CONTRACT_VERSION
    kit["updated_at"] = row["updated_at"]
    return kit


def to_dict(row) -> dict:
    return dict(row)


def direction_candidates(project: dict) -> list:
    words = " ".join([project["name"], project["industry"], project["audience"], project["brief"], project["mood"]]).lower()
    scored = []
    for style in STYLES:
        hits = [word for word in style["traits"] if word in words]
        base = 66 if style["id"] == "sovereign" else 62
        score = min(98, base + len(hits) * 8 + (4 if style["id"] in ("heritage", "editorial") else 0))
        rationale = "Matched institutional signals: " + ", ".join(hits) if hits else "Curated luxury alternative for executive differentiation"
        scored.append((score, style, rationale))
    return sorted(scored, key=lambda item: (-item[0], item[1]["name"]))[:3]


class API(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _client_ip(self) -> str:
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def _check_rate_limit(self) -> bool:
        allowed, retry_after = RATE_LIMITER.allow(self._client_ip())
        if not allowed:
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Retry-After", str(retry_after))
            body = json.dumps({"error": "Rate limit exceeded", "retry_after": retry_after}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return False
        return True

    def current_session(self) -> dict | None:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            session = verify_session_token(auth[7:].strip())
            if session:
                return session
        cookie_hdr = self.headers.get("Cookie", "")
        if cookie_hdr:
            jar = SimpleCookie()
            jar.load(cookie_hdr)
            if "rj_session" in jar:
                return verify_session_token(jar["rj_session"].value)
        return None

    def require_permission(self, permission: str) -> dict | None:
        session = self.current_session()
        if not session:
            self.respond(401, {"error": "Authentication required. Sign in as Principal or Director."})
            return None
        if not has_permission(session.get("role", ""), permission):
            self.respond(403, {"error": f"Insufficient role ({session.get('role')}) for permission '{permission}'"})
            return None
        return session

    def respond(self, status: int, payload, extra_headers: dict | None = None):
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def respond_bytes(self, status: int, data: bytes, content_type: str, filename: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size < 1 or size > 128_000:
            raise ValueError("Request must be between 1 and 128000 bytes")
        obj = json.loads(self.rfile.read(size))
        if not isinstance(obj, dict):
            raise ValueError("Expected JSON object")
        return obj

    def parsed(self):
        u = urlparse(self.path)
        parts = [x for x in u.path.split("/") if x]
        qs = parse_qs(u.query)
        return parts, qs

    def static(self, filename: str, content_type: str):
        path = ROOT / "web" / filename
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; img-src 'self' data: https://storage.googleapis.com; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def serve_safe_file(self, base_dir: Path, rel_parts: list[str], allow_html: bool = False):
        rel = Path(*[unquote(p) for p in rel_parts])
        target = (base_dir / rel).resolve()
        try:
            target.relative_to(base_dir.resolve())
        except ValueError:
            return self.respond(403, {"error": "Path traversal blocked"})
        if not target.is_file():
            return self.respond(404, {"error": "File not found"})
        ctype, _ = mimetypes.guess_type(str(target))
        if target.suffix.lower() == ".woff2":
            ctype = "font/woff2"
        elif target.suffix.lower() == ".woff":
            ctype = "font/woff"
        elif target.suffix.lower() == ".otf":
            ctype = "font/otf"
        elif target.suffix.lower() == ".ttf":
            ctype = "font/ttf"
        elif target.suffix.lower() == ".svg":
            ctype = "image/svg+xml"
        elif not ctype:
            ctype = "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if allow_html and target.suffix.lower() == ".html":
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://storage.googleapis.com data:")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._check_rate_limit():
            return
        parts, qs = self.parsed()
        if not parts or parts == ["index.html"]:
            return self.static("index.html", "text/html; charset=utf-8")
        if parts == ["app.css"]:
            return self.static("app.css", "text/css; charset=utf-8")
        if parts == ["app.js"]:
            return self.static("app.js", "text/javascript; charset=utf-8")
        if len(parts) >= 3 and parts[:2] == ["fonts", "rj-luxury"]:
            return self.serve_safe_file(ROOT / "web" / "fonts" / "rj-luxury", parts[2:])
        if len(parts) >= 2 and parts[0] == "vault":
            return self.serve_safe_file(ROOT / "brand-vault", parts[1:], allow_html=True)

        if parts == ["api", "health"]:
            return self.respond(200, {
                "ok": True,
                "database": True,
                "brand_edition": "Sovereign Luxury Investor v2.1",
                "contract_version": CONTRACT_VERSION,
                "styles_count": len(STYLES),
                "departments_count": len(DEPARTMENTS),
                "industries_count": len(INDUSTRY_REGISTRY),
                "pdf_renderer_ready": bool(find_chrome_binary()),
            })
        if parts == ["api", "auth", "me"]:
            session = self.current_session()
            if not session:
                return self.respond(200, {"authenticated": False, "user": None})
            return self.respond(200, {"authenticated": True, "user": {"username": session["sub"], "role": session["role"]}})
        if parts == ["api", "styles"]:
            return self.respond(200, STYLES)
        if parts == ["api", "components"]:
            return self.respond(200, COMPONENT_REGISTRY)
        if parts == ["api", "industries"]:
            return self.respond(200, INDUSTRY_REGISTRY)
        if parts == ["api", "agents"]:
            return self.respond(200, DEPARTMENTS)
        if parts == ["api", "vault"]:
            vault_dir = ROOT / "brand-vault"
            reg_dir = vault_dir / "registries"
            contact = json.loads((reg_dir / "contact-directory.json").read_text()) if (reg_dir / "contact-directory.json").exists() else {}
            contact.pop("settlement", None)  # P0 guarantee: never expose bank details in public vault directory
            registry = json.loads((reg_dir / "master-asset-registry.json").read_text()) if (reg_dir / "master-asset-registry.json").exists() else {}
            fonts_manifest = json.loads((reg_dir / "font-manifest.json").read_text()) if (reg_dir / "font-manifest.json").exists() else {}
            logos = sorted(p.name for p in (vault_dir / "logos").iterdir() if p.is_file()) if (vault_dir / "logos").exists() else []
            photos = sorted(p.name for p in (vault_dir / "photos").iterdir() if p.is_file()) if (vault_dir / "photos").exists() else []
            templates = sorted(p.name for p in (vault_dir / "templates").iterdir() if p.is_file()) if (vault_dir / "templates").exists() else []
            textures = sorted(p.name for p in (vault_dir / "textures").iterdir() if p.is_file()) if (vault_dir / "textures").exists() else []
            return self.respond(200, {
                "contact_directory": contact,
                "envato_kits": registry.get("downloaded_envato_kits", []),
                "font_families": list(fonts_manifest.get("families", {}).keys()) if isinstance(fonts_manifest.get("families"), dict) else fonts_manifest.get("families", []),
                "logos": [f"/vault/logos/{name}" for name in logos],
                "photos": [f"/vault/photos/{name}" for name in photos],
                "templates": [{"name": name, "url": f"/vault/templates/{name}"} for name in templates],
                "textures": [f"/vault/textures/{name}" for name in textures],
            })
        if parts == ["api", "brand"]:
            with connect() as db:
                return self.respond(200, get_brand_kit(db))
        if parts == ["api", "contracts", "validate"]:
            with connect() as db:
                kit = get_brand_kit(db)
            return self.respond(200, validate_brand_contract(kit))
        if parts == ["api", "audit"]:
            session = self.require_permission("audit:read")
            if not session:
                return
            with connect() as db:
                rows = [to_dict(r) for r in db.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 60")]
            return self.respond(200, rows)
        if parts == ["api", "settlements"]:
            session = self.require_permission("audit:read")
            if not session:
                return
            with connect() as db:
                rows = [to_dict(r) for r in db.execute("SELECT * FROM settlement_records ORDER BY updated_at DESC")]
            return self.respond(200, rows)
        if parts == ["api", "production", "assets"]:
            with connect() as db:
                rows = [to_dict(r) for r in db.execute("SELECT id, asset_type, title, subtitle, mime_type, filename, sha256, commercial_rights, created_by, created_at FROM assets ORDER BY created_at DESC LIMIT 30")]
            return self.respond(200, rows)
        if len(parts) == 4 and parts[:3] == ["api", "production", "assets"]:
            with connect() as db:
                row = db.execute("SELECT * FROM assets WHERE id=?", (parts[3],)).fetchone()
                if not row:
                    return self.respond(404, {"error": "Asset not found"})
                return self.respond_bytes(200, row["content"].encode("utf-8"), f"{row['mime_type']}; charset=utf-8", row["filename"])
        if parts == ["api", "qa", "runs"]:
            with connect() as db:
                rows = [json.loads(r["payload"]) for r in db.execute("SELECT payload FROM qa_runs ORDER BY created_at DESC LIMIT 10")]
            return self.respond(200, rows)
        if parts == ["api", "envato", "status"]:
            items = list_envato_vault()
            total_mb = round(sum(i["size_mb"] for i in items), 2)
            return self.respond(200, {
                "connected": True,
                "vault_archives_count": len(items),
                "total_size_mb": total_mb,
                "envato_market_api_token_configured": bool(os.environ.get("ENVATO_API_TOKEN")),
                "envato_elements_browser_bridge": "ready",
                "cli": "/Users/kalivibecoding/.gemini/bin/rj-envato",
            })
        if parts == ["api", "envato", "search"]:
            q = (qs.get("q") or [""])[0]
            cat = (qs.get("category") or ["all"])[0]
            live = (qs.get("live") or ["0"])[0] in ("1", "true")
            return self.respond(200, search_envato(q, cat, include_live_api=live))

        if len(parts) == 4 and parts[:3] == ["api", "brand", "export"]:
            fmt = parts[3]
            settlement_id = (qs.get("settlement_id") or [None])[0]
            with connect() as db:
                kit = get_brand_kit(db)
                settlement = None
                if settlement_id:
                    session = self.require_permission("audit:read")
                    if not session:
                        return
                    row = db.execute("SELECT * FROM settlement_records WHERE id=?", (settlement_id,)).fetchone()
                    if not row:
                        return self.respond(404, {"error": "Settlement record not found"})
                    settlement = to_dict(row)
                    if not settlement["recipient_verified"] or settlement["approval_status"] != "approved":
                        return self.respond(403, {"error": "Settlement record must be recipient-verified and principal-approved before inclusion"})

            if fmt == "css":
                return self.respond_bytes(200, export_css(kit).encode("utf-8"), "text/css; charset=utf-8", "rj-sovereign-tokens.css")
            if fmt == "json":
                return self.respond_bytes(200, json.dumps(kit, indent=2).encode("utf-8"), "application/json; charset=utf-8", "rj-sovereign-tokens.json")
            if fmt == "tailwind":
                return self.respond_bytes(200, export_tailwind(kit).encode("utf-8"), "text/css; charset=utf-8", "rj-sovereign-tailwind.css")
            if fmt == "memo":
                return self.respond_bytes(200, export_memo_html(kit, settlement).encode("utf-8"), "text/html; charset=utf-8", "rj-executive-memorandum.html")
            if fmt == "pdf":
                session = self.require_permission("export:pdf")
                if not session:
                    return
                try:
                    pdf_bytes = render_pdf_bytes(export_memo_html(kit, settlement))
                    with connect() as db:
                        log_audit(db, session["sub"], session["role"], "export:pdf", settlement_id or "brand-memo", f"Rendered {len(pdf_bytes)} bytes PDF")
                    return self.respond_bytes(200, pdf_bytes, "application/pdf", "rj-executive-memorandum.pdf")
                except RuntimeError as err:
                    return self.respond(501, {"error": str(err)})
            return self.respond(404, {"error": "Unsupported export format"})

        if parts == ["api", "projects"]:
            with connect() as db:
                return self.respond(200, [to_dict(row) for row in db.execute("SELECT * FROM projects ORDER BY updated_at DESC")])
        if len(parts) == 3 and parts[:2] == ["api", "projects"]:
            with connect() as db:
                project = db.execute("SELECT * FROM projects WHERE id=?", (parts[2],)).fetchone()
                if not project:
                    return self.respond(404, {"error": "Project not found"})
                directions = [to_dict(x) for x in db.execute("SELECT * FROM directions WHERE project_id=? ORDER BY score DESC", (parts[2],))]
                memories = [to_dict(x) for x in db.execute("SELECT * FROM memories WHERE project_id=? ORDER BY created_at DESC", (parts[2],))]
                evaluations = [to_dict(x) for x in db.execute("SELECT * FROM evaluations WHERE project_id=? ORDER BY created_at DESC", (parts[2],))]
                runs = [json.loads(x["payload"]) for x in db.execute("SELECT payload FROM orchestration_runs WHERE project_id=? ORDER BY created_at DESC LIMIT 5", (parts[2],))]
                return self.respond(200, {"project": to_dict(project), "directions": directions, "memories": memories, "evaluations": evaluations, "orchestration_runs": runs})
        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "scaffold":
            session = self.require_permission("orchestrator:run")
            if not session:
                return
            with connect() as db:
                project = db.execute("SELECT * FROM projects WHERE id=?", (parts[2],)).fetchone()
                if not project:
                    return self.respond(404, {"error": "Project not found"})
                kit = get_brand_kit(db)
                scaffold = generate_react_scaffold(to_dict(project), kit)
                log_audit(db, session["sub"], session["role"], "scaffold:generate", parts[2], f"Generated React/TS/Tailwind v4 scaffold for {project['name']}")
                return self.respond(200, scaffold)
        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "bundle.zip":
            session = self.require_permission("orchestrator:run")
            if not session:
                return
            with connect() as db:
                project = db.execute("SELECT * FROM projects WHERE id=?", (parts[2],)).fetchone()
                if not project:
                    return self.respond(404, {"error": "Project not found"})
                kit = get_brand_kit(db)
                zip_bytes = build_react_zip_bundle(to_dict(project), kit)
                log_audit(db, session["sub"], session["role"], "bundle:zip", parts[2], f"Packaged {len(zip_bytes)} byte React/TS/3D zip bundle")
                return self.respond_bytes(200, zip_bytes, "application/zip", f"{project['name'].lower().replace(' ', '-')}-bundle.zip")
        if len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "3d-scene":
            session = self.require_permission("orchestrator:run")
            if not session:
                return
            with connect() as db:
                project = db.execute("SELECT * FROM projects WHERE id=?", (parts[2],)).fetchone()
                if not project:
                    return self.respond(404, {"error": "Project not found"})
                kit = get_brand_kit(db)
                scene = generate_3d_scene_package(to_dict(project), kit["palette"])
                log_audit(db, session["sub"], session["role"], "3d:generate", parts[2], f"Generated R3F 3D scene + 2D fallback for {project['name']}")
                return self.respond(200, scene)

        self.respond(404, {"error": "Not found"})

    def do_PUT(self):
        if not self._check_rate_limit():
            return
        try:
            parts, _ = self.parsed()
            data = self.body()
            if parts == ["api", "brand"]:
                session = self.require_permission("brand:write")
                if not session:
                    return
                with connect() as db:
                    current = get_brand_kit(db)
                    updated = deep_merge(current, data)
                    updated.pop("updated_at", None)
                    validation = validate_brand_contract(updated)
                    if not validation["valid"]:
                        return self.respond(400, {"error": "Design contract validation failed", "validation": validation})
                    ts = now()
                    db.execute("UPDATE brand_settings SET payload=?, updated_at=? WHERE id='global'", (json.dumps(updated), ts))
                    log_audit(db, session["sub"], session["role"], "brand:update", "global", f"Contract v{CONTRACT_VERSION} updated")
                    updated["updated_at"] = ts
                    updated["validation"] = validation
                return self.respond(200, updated)
            self.respond(404, {"error": "Not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.respond(400, {"error": str(error)})
        except sqlite3.Error:
            self.respond(500, {"error": "Database operation failed"})

    def do_DELETE(self):
        if not self._check_rate_limit():
            return
        try:
            parts, _ = self.parsed()
            if len(parts) == 3 and parts[:2] == ["api", "projects"]:
                session = self.require_permission("project:delete")
                if not session:
                    return
                with connect() as db:
                    cur = db.execute("DELETE FROM projects WHERE id=?", (parts[2],))
                    if cur.rowcount == 0:
                        return self.respond(404, {"error": "Project not found"})
                    log_audit(db, session["sub"], session["role"], "project:delete", parts[2], "Mandate deleted")
                return self.respond(200, {"deleted": parts[2]})
            self.respond(404, {"error": "Not found"})
        except sqlite3.Error:
            self.respond(500, {"error": "Database operation failed"})

    def do_POST(self):
        if not self._check_rate_limit():
            return
        try:
            parts, _ = self.parsed()
            data = self.body()

            if parts == ["api", "auth", "login"]:
                username = str(data.get("username", "")).strip()
                password = str(data.get("password", ""))
                with connect() as db:
                    user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
                    if not user or not verify_password(password, user["password_hash"]):
                        log_audit(db, username or "anonymous", "none", "auth:failed", "session", "Invalid credentials")
                        return self.respond(401, {"error": "Invalid username or password"})
                    token = issue_session_token(user["id"], user["username"], user["role"])
                    log_audit(db, user["username"], user["role"], "auth:login", "session", "Signed session issued")
                cookie = f"rj_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800"
                return self.respond(200, {"authenticated": True, "token": token, "user": {"username": user["username"], "role": user["role"]}}, {"Set-Cookie": cookie})

            if parts == ["api", "auth", "logout"]:
                cookie = "rj_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                return self.respond(200, {"authenticated": False}, {"Set-Cookie": cookie})

            if parts == ["api", "brand", "reset"]:
                session = self.require_permission("brand:write")
                if not session:
                    return
                ts = now()
                with connect() as db:
                    db.execute("UPDATE brand_settings SET payload=?, updated_at=? WHERE id='global'", (json.dumps(DEFAULT_BRAND_KIT), ts))
                    log_audit(db, session["sub"], session["role"], "brand:reset", "global", "Reset to Sovereign v2.1 defaults")
                    kit = get_brand_kit(db)
                return self.respond(200, kit)

            if parts == ["api", "admin", "backup"]:
                session = self.require_permission("admin:backup")
                if not session:
                    return
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                backup_name = f"design-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.sqlite3"
                backup_path = BACKUP_DIR / backup_name
                with connect() as src:
                    dst = sqlite3.connect(backup_path, factory=ClosingConnection)
                    with dst:
                        src.backup(dst)
                    log_audit(src, session["sub"], session["role"], "admin:backup", backup_name, f"SQLite online backup ({backup_path.stat().st_size} bytes)")
                return self.respond(201, {"backup": backup_name, "bytes": backup_path.stat().st_size})

            # Phase 3: Commercial Asset Studio & Universal Repo Adapter
            if parts == ["api", "production", "assets"]:
                session = self.require_permission("orchestrator:run")
                if not session:
                    return
                asset_type = str(data.get("asset_type", "")).strip()
                title = str(data.get("title", "RJ Sovereign Mandate")).strip()[:100]
                subtitle = str(data.get("subtitle", "Institutional Capital Architecture")).strip()[:200]
                with connect() as db:
                    kit = get_brand_kit(db)
                    asset = generate_commercial_asset(asset_type, title, subtitle, kit["palette"], session["sub"])
                    db.execute(
                        "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (asset["id"], asset["asset_type"], asset["title"], asset["subtitle"], asset["mime_type"], asset["filename"], asset["sha256"], asset["commercial_rights"], asset["created_by"], asset["content"], asset["created_at"]),
                    )
                    log_audit(db, session["sub"], session["role"], "asset:create", asset["id"], f"Generated {asset_type} ({asset['filename']})")
                resp_asset = {k: v for k, v in asset.items() if k != "content"}
                resp_asset["download_url"] = f"/api/production/assets/{asset['id']}"
                return self.respond(201, resp_asset)

            if parts == ["api", "production", "inspect-repo"]:
                session = self.require_permission("orchestrator:run")
                if not session:
                    return
                repo_path = str(data.get("path", "")).strip()
                if not repo_path:
                    return self.respond(400, {"error": "Repository path is required"})
                report = inspect_local_repository(repo_path)
                with connect() as db:
                    log_audit(db, session["sub"], session["role"], "repo:inspect", repo_path, f"Detected {report['framework_detected']}")
                return self.respond(200, report)

            # Envato Connector: Install + Auto-Rebrand & Ingest New Downloads
            if parts == ["api", "envato", "install"]:
                session = self.require_permission("orchestrator:run")
                if not session:
                    return
                asset_id = str(data.get("asset_id", "")).strip()
                target_dir = str(data.get("target_dir", "")).strip()
                apply_brand = bool(data.get("apply_rj_branding", True))
                if not asset_id or not target_dir:
                    return self.respond(400, {"error": "asset_id and target_dir are required"})
                with connect() as db:
                    kit = get_brand_kit(db)
                    result = install_asset_into_project(asset_id, target_dir, apply_rj_branding=apply_brand, brand_kit=kit)
                    log_audit(db, session["sub"], session["role"], "envato:install", asset_id, f"Installed into {target_dir} (branded={apply_brand})")
                return self.respond(200, result)

            if parts == ["api", "envato", "ingest"]:
                session = self.require_permission("orchestrator:run")
                if not session:
                    return
                zip_path = str(data.get("zip_path", "")).strip()
                if not zip_path:
                    return self.respond(400, {"error": "zip_path is required"})
                item = ingest_envato_zip(zip_path)
                with connect() as db:
                    log_audit(db, session["sub"], session["role"], "envato:ingest", item["id"], f"Ingested {item['filename']}")
                return self.respond(201, item)

            # Phase 4: Automated Live Browser/Security/Accessibility/Performance QA Runner
            if parts == ["api", "qa", "run"]:
                session = self.require_permission("orchestrator:run")
                if not session:
                    return
                host, port = self.server.server_address[0], self.server.server_address[1]
                qa_report = run_automated_qa_audit(host, port, ROOT / "verification", session["sub"])
                with connect() as db:
                    db.execute(
                        "INSERT INTO qa_runs VALUES (?,?,?,?,?)",
                        (qa_report["run_id"], qa_report["score"], 1 if qa_report["release_approved"] else 0, json.dumps(qa_report), qa_report["started_at"]),
                    )
                    log_audit(db, session["sub"], session["role"], "qa:run", qa_report["run_id"], f"Automated QA scored {qa_report['score']}/100 ({qa_report['passed_checks']}/{qa_report['total_checks']} passed)")
                return self.respond(201, qa_report)

            # Protected Settlement Records Workflow
            if parts == ["api", "settlements"]:
                session = self.require_permission("settlement:write")
                if not session:
                    return
                recipient = str(data.get("recipient_name", "")).strip()[:160]
                method = str(data.get("method", "")).strip().lower()
                institution = str(data.get("institution", "")).strip()[:160]
                ref_code = str(data.get("reference_code", "")).strip()[:120]
                project_id = str(data.get("project_id", "")).strip() or None
                if not recipient or method not in ("wire", "zelle", "escrow") or not institution or not ref_code:
                    return self.respond(400, {"error": "recipient_name, method (wire|zelle|escrow), institution, and reference_code are required"})
                sid = uuid.uuid4().hex
                ts = now()
                with connect() as db:
                    db.execute(
                        "INSERT INTO settlement_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, project_id, recipient, 0, method, institution, ref_code, "pending", None, ts, ts),
                    )
                    log_audit(db, session["sub"], session["role"], "settlement:create", sid, f"Created pending {method} record for {recipient}")
                return self.respond(201, {"id": sid, "approval_status": "pending", "recipient_verified": False})

            if len(parts) == 4 and parts[:2] == ["api", "settlements"]:
                sid, action = parts[2], parts[3]
                if action == "verify":
                    session = self.require_permission("settlement:write")
                    if not session:
                        return
                    with connect() as db:
                        cur = db.execute("UPDATE settlement_records SET recipient_verified=1, updated_at=? WHERE id=?", (now(), sid))
                        if cur.rowcount == 0:
                            return self.respond(404, {"error": "Settlement record not found"})
                        log_audit(db, session["sub"], session["role"], "settlement:verify", sid, "Recipient KYC/callback verified")
                    return self.respond(200, {"id": sid, "recipient_verified": True})
                if action == "approve":
                    session = self.require_permission("settlement:approve")
                    if not session:
                        return
                    with connect() as db:
                        row = db.execute("SELECT * FROM settlement_records WHERE id=?", (sid,)).fetchone()
                        if not row:
                            return self.respond(404, {"error": "Settlement record not found"})
                        if not row["recipient_verified"]:
                            return self.respond(400, {"error": "Recipient must be verified before principal approval"})
                        ts = now()
                        db.execute("UPDATE settlement_records SET approval_status='approved', approved_by=?, updated_at=? WHERE id=?", (session["sub"], ts, sid))
                        log_audit(db, session["sub"], session["role"], "settlement:approve", sid, "Principal approved settlement record")
                    return self.respond(200, {"id": sid, "approval_status": "approved", "approved_by": session["sub"]})
                if action == "revoke":
                    session = self.require_permission("settlement:approve")
                    if not session:
                        return
                    with connect() as db:
                        cur = db.execute("UPDATE settlement_records SET approval_status='revoked', updated_at=? WHERE id=?", (now(), sid))
                        if cur.rowcount == 0:
                            return self.respond(404, {"error": "Settlement record not found"})
                        log_audit(db, session["sub"], session["role"], "settlement:revoke", sid, "Principal revoked settlement record")
                    return self.respond(200, {"id": sid, "approval_status": "revoked"})

            # Projects / Mandates & Orchestration
            if parts == ["api", "projects"]:
                session = self.require_permission("project:write")
                if not session:
                    return
                fields = {key: str(data.get(key, "")).strip()[:3000] for key in ("name", "industry", "audience", "brief", "mood")}
                if not all(fields.values()):
                    return self.respond(400, {"error": "All project fields are required"})
                identifier = uuid.uuid4().hex
                timestamp = now()
                with connect() as db:
                    db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)", (identifier, *fields.values(), timestamp, timestamp))
                    log_audit(db, session["sub"], session["role"], "project:create", identifier, f"Created mandate '{fields['name']}'")
                return self.respond(201, {"id": identifier})

            if len(parts) >= 4 and parts[:2] == ["api", "projects"]:
                session = self.require_permission("project:write")
                if not session:
                    return
                project_id, action = parts[2], parts[3]
                with connect() as db:
                    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
                    if not project:
                        return self.respond(404, {"error": "Project not found"})
                    if action == "directions":
                        db.execute("DELETE FROM directions WHERE project_id=?", (project_id,))
                        results = []
                        for score, style, rationale in direction_candidates(to_dict(project)):
                            identifier = uuid.uuid4().hex
                            db.execute("INSERT INTO directions VALUES (?,?,?,?,?,?,?)", (identifier, project_id, style["id"], score, rationale, 0, now()))
                            results.append({"id": identifier, "style_id": style["id"], "score": score, "rationale": rationale})
                        log_audit(db, session["sub"], session["role"], "project:directions", project_id, "Generated 3 ranked directions")
                        return self.respond(201, results)
                    if action == "select" and len(parts) == 5:
                        direction = db.execute("SELECT id FROM directions WHERE project_id=? AND id=?", (project_id, parts[4])).fetchone()
                        if not direction:
                            return self.respond(404, {"error": "Direction not found"})
                        db.execute("UPDATE directions SET selected=0 WHERE project_id=?", (project_id,))
                        db.execute("UPDATE directions SET selected=1 WHERE id=?", (parts[4],))
                        log_audit(db, session["sub"], session["role"], "project:select_direction", project_id, f"Selected {parts[4]}")
                        return self.respond(200, {"selected": parts[4]})
                    if action == "memory":
                        label, value = str(data.get("label", "")).strip()[:120], str(data.get("value", "")).strip()[:2000]
                        if not label or not value:
                            return self.respond(400, {"error": "Label and value are required"})
                        identifier = uuid.uuid4().hex
                        db.execute("INSERT INTO memories VALUES (?,?,?,?,?)", (identifier, project_id, label, value, now()))
                        log_audit(db, session["sub"], session["role"], "project:memory", project_id, f"Saved memory '{label}'")
                        return self.respond(201, {"id": identifier})
                    if action == "orchestrate":
                        kit = get_brand_kit(db)
                        run_result = run_creative_director_pipeline(to_dict(project), kit, session["sub"])
                        db.execute("INSERT INTO orchestration_runs VALUES (?,?,?,?)", (run_result["run_id"], project_id, json.dumps(run_result), now()))
                        log_audit(db, session["sub"], session["role"], "orchestrator:run", project_id, f"Executed 8 departments ({run_result['total_specialists']} specialists)")
                        return self.respond(201, run_result)
                    if action == "evaluate":
                        name = str(data.get("name", "")).strip()[:120]
                        metrics = data.get("metrics", {})
                        if not name or not isinstance(metrics, dict) or set(metrics) != {x[0] for x in CATEGORIES}:
                            return self.respond(400, {"error": "Evaluation name and all 10 quality categories are required"})
                        if any(type(value) not in (float, int) or not 0 <= value <= 5 for value in metrics.values()):
                            return self.respond(400, {"error": "Each category must be from zero to five"})
                        score = round(sum(metrics[key] / 5 * weight for key, weight in CATEGORIES), 1)
                        blockers = [key for key in CRITICAL_CATEGORIES if metrics[key] < 3]
                        identifier = uuid.uuid4().hex
                        db.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?,?)", (identifier, project_id, name, json.dumps(metrics), score, json.dumps(blockers), now()))
                        log_audit(db, session["sub"], session["role"], "project:evaluate", project_id, f"Scored {score}/100 (blockers: {len(blockers)})")
                        return self.respond(201, {"id": identifier, "score": score, "blockers": blockers, "status": "Approved" if score >= 90 and not blockers else "Needs refinement"})

            self.respond(404, {"error": "Not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.respond(400, {"error": str(error)})
        except sqlite3.Error:
            self.respond(500, {"error": "Database operation failed"})


if __name__ == "__main__":
    connect().close()
    host = os.environ.get("RJ_DESIGN_HOST", "127.0.0.1")
    port = int(os.environ.get("RJ_DESIGN_PORT", "8787"))
    print(f"RJ Design Command OS v2.1 (Sovereign Enterprise Edition) ready at http://{host}:{port}")
    ThreadingHTTPServer((host, port), API).serve_forever()
