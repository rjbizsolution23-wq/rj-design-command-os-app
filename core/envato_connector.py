"""Envato Elements & Envato API Connected Asset Broker with Automatic RJ Sovereign Black & Gold Rebranding."""
import hashlib
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from core.contracts import DEFAULT_BRAND_KIT, export_css

DEFAULT_ENVATO_ZIPS_DIR = Path(
    os.environ.get(
        "RJ_ENVATO_ZIPS_DIR",
        "/Users/kalivibecoding/Downloads/Super-agents266/RJ-BUSINESS-SOLUTIONS-BRAND-SYSTEM/04-ENVATO-SOURCE-ASSETS/original-zips",
    )
)
GLOBAL_BRAND_LOGOS_DIR = Path("/Users/kalivibecoding/.gemini/config/brand/logos")
GLOBAL_BRAND_FONTS_DIR = Path("/Users/kalivibecoding/.gemini/config/brand/fonts")

CATEGORY_RULES = [
    ("fonts", ["font", "serif", "sans", "taillevere", "auretha", "siovanni", "galante", "grift", "xenon", "vank", "nority", "morgen", "pierre", "swarsh", "editorial"]),
    ("presentations", ["deck", "presentation", "pitch", "slide", "black-and-gold-2026"]),
    ("web-ui", ["website", "web", "figma", "ui", "landing", "dashboard"]),
    ("social-media", ["social", "linkedin", "youtube", "thumbnail", "instagram", "banner", "glamour"]),
    ("textures-3d", ["marble", "voronoi", "texture", "background", "3d", "abstract"]),
    ("stationery", ["stationery", "branding-identity", "card", "letterhead"]),
    ("video-motion", ["intro", "video", "motion", "reveal", "logo-intro"]),
]

ENVATO_ITEM_TYPE_MAP = {
    "fonts": "fonts",
    "presentations": "presentation-templates",
    "web-ui": "graphic-templates",
    "social-media": "graphic-templates",
    "textures-3d": "graphics",
    "stationery": "graphic-templates",
    "video-motion": "video-templates",
}


def _classify(filename: str) -> str:
    low = filename.lower()
    for cat, terms in CATEGORY_RULES:
        if any(t in low for t in terms):
            return cat
    return "graphics"


def _human_title(stem: str) -> str:
    cleaned = re.sub(r"-20\d\d-\d\d-\d\d-\d\d-\d\d-\d\d-utc$", "", stem)
    return " ".join(w.capitalize() for w in cleaned.replace("_", "-").split("-") if w)


def _slugify(stem: str) -> str:
    cleaned = re.sub(r"-20\d\d-\d\d-\d\d-\d\d-\d\d-\d\d-utc$", "", stem)
    return re.sub(r"[^a-z0-9-]+", "-", cleaned.lower()).strip("-")


def list_envato_vault(zips_dir: Path | None = None) -> list[dict]:
    """Scan and index all licensed Envato Elements zip archives in the local vault."""
    root = zips_dir or DEFAULT_ENVATO_ZIPS_DIR
    if not root.exists():
        return []
    items = []
    for zpath in sorted(root.glob("*.zip")):
        slug = _slugify(zpath.stem)
        cat = _classify(zpath.name)
        formats = set()
        file_count = 0
        try:
            with zipfile.ZipFile(zpath, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir() or "__MACOSX" in info.filename:
                        continue
                    file_count += 1
                    ext = Path(info.filename).suffix.lower()
                    if ext:
                        formats.add(ext)
        except zipfile.BadZipFile:
            continue
        size_mb = round(zpath.stat().st_size / (1024 * 1024), 2)
        items.append({
            "id": slug,
            "title": _human_title(zpath.stem),
            "category": cat,
            "filename": zpath.name,
            "zip_path": str(zpath),
            "size_mb": size_mb,
            "file_count": file_count,
            "formats": sorted(formats)[:12],
            "source": "Envato Elements (Licensed Local Vault)",
        })
    return items


def build_envato_elements_search_url(query: str, category: str | None = None) -> str:
    item_type = ENVATO_ITEM_TYPE_MAP.get(category or "", "")
    params = {"term": query, "sort": "popular"}
    if item_type:
        params["itemType"] = item_type
    return f"https://app.envato.com/search?{urllib.parse.urlencode(params)}"


def query_envato_market_api(query: str, limit: int = 8) -> dict:
    """Query official Envato Market Discovery API when ENVATO_API_TOKEN is configured."""
    token = os.environ.get("ENVATO_API_TOKEN", "").strip()
    if not token:
        return {"connected": False, "items": [], "note": "Set ENVATO_API_TOKEN for live Envato Market API search, or use Envato Elements authenticated browser session."}
    url = f"https://api.envato.com/v1/discovery/search/search/item?term={urllib.parse.quote(query)}&page_size={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "RJ-Design-Command-OS/3.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        matches = []
        for m in data.get("matches", [])[:limit]:
            matches.append({
                "id": str(m.get("id", "")),
                "title": m.get("name", ""),
                "category": m.get("classification", ""),
                "url": m.get("url", ""),
                "price_cents": m.get("price_cents"),
                "rating": m.get("rating", {}).get("rating"),
                "source": "Envato Market Live API",
            })
        return {"connected": True, "items": matches}
    except Exception as exc:
        return {"connected": True, "items": [], "error": str(exc)}


def search_envato(query: str = "", category: str | None = None, include_live_api: bool = False, zips_dir: Path | None = None) -> dict:
    vault = list_envato_vault(zips_dir)
    q_words = [w for w in re.split(r"\s+", query.strip().lower()) if w]
    results = []
    for item in vault:
        if category and category != "all" and item["category"] != category:
            continue
        haystack = " ".join([item["title"], item["category"], " ".join(item["formats"]), item["id"]]).lower()
        if not q_words:
            score = 100
        else:
            hits = sum(1 for w in q_words if w in haystack)
            if hits == 0:
                continue
            score = round((hits / len(q_words)) * 100)
        results.append({**item, "relevance": score})
    results.sort(key=lambda x: (-x["relevance"], x["title"]))
    live = query_envato_market_api(query) if (include_live_api and query.strip()) else {"connected": bool(os.environ.get("ENVATO_API_TOKEN")), "items": []}
    return {
        "query": query,
        "category": category or "all",
        "vault_count": len(vault),
        "matches": results,
        "envato_elements_live_url": build_envato_elements_search_url(query or "luxury black gold", category),
        "live_market_api": live,
    }


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest_dir.resolve()
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir() or "__MACOSX" in member.filename:
                continue
            target = (dest_dir / member.filename).resolve()
            try:
                target.relative_to(dest_resolved)
            except ValueError:
                raise ValueError(f"Blocked unsafe zip entry (Zip Slip): {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(str(target.relative_to(dest_resolved)))
    return extracted


def install_asset_into_project(
    asset_id: str,
    target_dir_str: str,
    apply_rj_branding: bool = True,
    brand_kit: dict | None = None,
    zips_dir: Path | None = None,
) -> dict:
    """Extract a licensed Envato asset into any target project AND auto-inject RJ Sovereign Black & Gold branding."""
    vault = list_envato_vault(zips_dir)
    match = next((item for item in vault if item["id"] == asset_id or item["filename"] == asset_id), None)
    if not match:
        raise ValueError(f"Envato vault asset not found: {asset_id}")

    target_dir = Path(target_dir_str).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    asset_dest = target_dir / "envato-assets" / match["id"]
    extracted_files = _safe_extract_zip(Path(match["zip_path"]), asset_dest)

    branding_files = []
    if apply_rj_branding:
        kit = brand_kit or DEFAULT_BRAND_KIT
        brand_dir = target_dir / "rj-brand"
        brand_dir.mkdir(parents=True, exist_ok=True)

        # 1. Sovereign CSS tokens
        tokens_path = brand_dir / "rj-sovereign-tokens.css"
        tokens_path.write_text(export_css(kit), encoding="utf-8")
        branding_files.append("rj-brand/rj-sovereign-tokens.css")

        # 2. Brand manifest JSON (zero hardcoded banking details)
        manifest_path = brand_dir / "rj-brand-manifest.json"
        manifest_path.write_text(json.dumps(kit, indent=2), encoding="utf-8")
        branding_files.append("rj-brand/rj-brand-manifest.json")

        # 3. Copy Black & Gold Luxury Tech Division logos
        logos_dest = brand_dir / "logos"
        logos_dest.mkdir(parents=True, exist_ok=True)
        if GLOBAL_BRAND_LOGOS_DIR.exists():
            for logo in GLOBAL_BRAND_LOGOS_DIR.iterdir():
                if logo.is_file():
                    shutil.copy2(logo, logos_dest / logo.name)
                    branding_files.append(f"rj-brand/logos/{logo.name}")

        # 4. Copy Luxury Font CSS reference
        if (GLOBAL_BRAND_FONTS_DIR / "rj-luxury-fonts.css").exists():
            shutil.copy2(GLOBAL_BRAND_FONTS_DIR / "rj-luxury-fonts.css", brand_dir / "rj-luxury-fonts.css")
            branding_files.append("rj-brand/rj-luxury-fonts.css")

    return {
        "asset_id": match["id"],
        "title": match["title"],
        "category": match["category"],
        "target_dir": str(target_dir),
        "extracted_to": str(asset_dest),
        "extracted_count": len(extracted_files),
        "sample_files": extracted_files[:15],
        "rj_branding_applied": apply_rj_branding,
        "branding_files": branding_files,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def ingest_envato_zip(source_zip_str: str, zips_dir: Path | None = None) -> dict:
    """Ingest any newly downloaded Envato Elements .zip archive into the global agent vault."""
    src = Path(source_zip_str).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != ".zip":
        raise ValueError(f"Expected a valid .zip file: {source_zip_str}")
    if not zipfile.is_zipfile(src):
        raise ValueError(f"File is not a valid zip archive: {source_zip_str}")

    dest_root = zips_dir or DEFAULT_ENVATO_ZIPS_DIR
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / src.name
    if src != dest.resolve():
        shutil.copy2(src, dest)

    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    item = next(i for i in list_envato_vault(dest_root) if i["filename"] == dest.name)
    item["sha256"] = digest
    return item
