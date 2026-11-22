# DELIVERABLE 5 — Master Color & Typography System

## 1. Authoritative Color Palette (Approved Sovereign Luxury Investor v2.0)
| Token | Name | Hex / Value | Role & Usage Rule |
| :--- | :--- | :--- | :--- |
| `--rj-obsidian` | Sovereign Obsidian | `#0A0B0E` | Primary dark hero headers, private-client portals, pitch deck canvas |
| `--rj-vault` | Charcoal Vault | `#12141A` | Elevated dark cards, LP dashboards, dark modals |
| `--rj-graphite` | Midnight Graphite | `#1C2029` | Dark structural borders, secondary panels |
| `--rj-gold` | Burnished Champagne Gold | `#C5A059` | Strategic prestige accent, 1px hairline rules, primary luxury CTAs |
| `--rj-champagne` | Brushed Pale Gold | `#DFC48C` | Luminous dark-surface highlights, hover states, deck headings |
| `--rj-bronze` | Deep Antique Bronze | `#8A6A2F` | High-contrast WCAG AA gold for text & badges on light paper |
| `--rj-alabaster` | Warm Alabaster | `#FAF8F5` | Signature light-mode canvas & print background |
| `--rj-ivory` | Pure Ivory | `#FFFFFF` | Document cards, offering memoranda, stationery |
| `--rj-parchment` | Parchment Mist | `#F3EFE6` | Table headers, section seals, subtle pill fills |
| `--rj-ink` | Ink Primary | `#111318` | Primary body copy on light surfaces (17.8:1 contrast) |
| `--rj-emerald` | Institutional Emerald | `#1B5E4B` | Positive financial/credit indicators, verified badges |
| `--rj-crimson` | Burgundy Alert | `#8C2D36` | Risk alerts, destructive actions |

**Gold Restraint Rule:** Gold accents must never exceed ~10% of any viewport or page area. Use for 1px borders, overline seals, key numerical callouts, and primary CTA borders/fills.

## 2. Complete 12-Family Licensed Envato Typography System (Installed Globally)
All 12 families are installed system-wide on macOS (`~/Library/Fonts/RJ-Envato-Luxury/`) and bundled in `02-COLORS-AND-TYPOGRAPHY/rj-luxury-fonts.css`.

| Role | Primary Envato Family | Secondary / Fallback | Weights Used |
| :--- | :--- | :--- | :--- |
| **Hero / Sovereign Display** | `'Taillevere'` (Didone) or `'Galante'` (9 weights) | `'Cormorant Garamond'`, Georgia, serif | 400, 600, 700 |
| **Editorial Headings (H1–H3)** | `'Auretha'` (7 weights + Variable) or `'Siovanni'` (14 styles) | `'Cormorant Garamond'`, Georgia, serif | 400, 500, 600 |
| **Campaign / Statement Accent** | `'Swarsh Daisy'`, `'Morgen'`, `'Pierre Robe'` | `'Editorial Luxury'`, Georgia, serif | 400, Italic |
| **Corporate Body & UI (H4–H6, P, Nav)** | `'Xenon Nue'` (18 styles) | `'Plus Jakarta Sans'`, system-ui, sans-serif | 400, 500, 600 |
| **Financial Tables & SaaS Metrics** | `'Grift'` (18 static + Variable, `tabular-nums`) | `'Manrope'`, system-ui, sans-serif | 500, 600, 700 |
| **Impact / Thumbnails / KPI Callouts** | `'Vank'` (Bold Condensed) or `'Nority'` (Inktrap Bold) | system-ui, sans-serif | 700 |

## 3. Type Scale Specification
| Element | Font Family | Desktop Size | Mobile Size | Line Height | Letter Spacing |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Hero Display** | `'Taillevere'` / `'Galante'` | 64–84px | 40–48px | 1.04 | `-0.02em` |
| **H1 (Page Title)** | `'Auretha'` / `'Taillevere'` | 48px | 34px | 1.10 | `-0.015em` |
| **H2 (Section Title)** | `'Auretha'` / `'Siovanni'` | 34px | 26px | 1.18 | `-0.01em` |
| **H3 (Card Title)** | `'Siovanni'` / `'Xenon Nue'` | 22px | 20px | 1.25 | `0` |
| **H4–H6 / Overline Seal** | `'Xenon Nue'` (Uppercase 600) | 11–14px | 11–13px | 1.40 | `0.18em–0.22em` |
| **Body Paragraph** | `'Xenon Nue'` (400) | 16px | 15px | 1.65 | `0` |
| **Buttons / Navigation** | `'Xenon Nue'` (600) | 13–14px | 13px | 1.0 | `0.10em` |
| **Captions / Legal Text** | `'Grift'` (400) | 11–12px | 11px | 1.50 | `0.02em` |
| **Presentation Slides (1920×1080)** | Title: `'Taillevere'` 54–72pt · Body: `'Xenon Nue'` 20–24pt | — | — | 1.15 / 1.45 | `-0.01em` / `0` |

**Licensing Note:** All 12 fonts are commercially licensed under the user's active Envato Elements subscription for registered RJ Business Solutions projects (websites, PDFs, presentations, social graphics). Do not redistribute raw `.otf`/`.ttf`/`.woff2` files as standalone downloadable templates to third parties.
