#!/usr/bin/env bash
set -euo pipefail

# RJ Business Solutions — Sovereign Luxury Font Vault Project Installer
# Usage: bash install-into-project.sh <target-project-dir> [public-subpath]

TARGET_DIR="${1:-.}"
PUBLIC_SUBPATH="${2:-public/fonts/rj-luxury}"
VAULT_DIR="/Users/kalivibecoding/Downloads/Super-agents266/envato-fonts/vault"

mkdir -p "$TARGET_DIR/$PUBLIC_SUBPATH"
cp -R "$VAULT_DIR/fonts/"* "$TARGET_DIR/$PUBLIC_SUBPATH/"

# Rewrite CSS relative ./fonts/ URLs to web root /fonts/rj-luxury/
WEB_PREFIX="/${PUBLIC_SUBPATH#public/}"
sed "s|\./fonts/|${WEB_PREFIX}/|g" "$VAULT_DIR/rj-luxury-fonts.css" > "$TARGET_DIR/$PUBLIC_SUBPATH/rj-luxury-fonts.css"

echo "✅ Installed RJ Sovereign Luxury Font Vault (12 families) into $TARGET_DIR/$PUBLIC_SUBPATH"
echo "   Import CSS via: <link rel=\"stylesheet\" href=\"${WEB_PREFIX}/rj-luxury-fonts.css\" />"
echo "   Or in Next.js/Vite CSS: @import '${WEB_PREFIX}/rj-luxury-fonts.css';"
