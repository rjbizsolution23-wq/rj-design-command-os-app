# DELIVERABLES 8 & 9 — Premium Website Template Recommendation & Implementation Blueprint

## 1. Platform & Stack Architecture (Cloudflare-First)
- **Existing Verified Infrastructure:** Cloudflare-first stack (Next.js App Router + Tailwind CSS v4 + Cloudflare Pages/Workers + D1 + R2). Do not downgrade to bloated WordPress themes.
- **Selected Visual Blueprint:** `Modern & Professional Finance Consulting Website (Credence)` by `Protagonis` (12-page Figma UI kit, extracted in `05-WEBSITE-TEMPLATES/envato-credence-finance-figma/`).
- **Typography Integration:** Run `bash ~/.gemini/config/brand/fonts/install-into-project.sh <site-dir>` to bundle `Taillevere`, `Auretha`, `Xenon Nue`, and `Grift` locally with `font-display: swap`.

## 2. Recommended Sitemap (`rjbusinesssolutions.org`)
1. **Home (`/`)** — Sovereign Obsidian hero with Rick Jefferson (`rick-hero.jpg`), institutional positioning, 3 core pillars (Credit Intelligence, AI Automation, White-Label Fintech), live platform proof, Executive CTA.
2. **About (`/about`)** — Founder profile (`rick-portrait.jpg`), mission, Tijeras NM headquarters, compliance commitment (CROA/FCRA).
3. **Services (`/services`)** + Dedicated Subpages:
   - `/services/credit-intelligence` (RJ Credit Intelligence Platform — Starter $47/mo, Pro $147–$197/mo)
   - `/services/crm-automation` (DFY CRM & Lead Follow-Up Systems)
   - `/services/white-label-fintech` (Enterprise White-Label Infrastructure)
   - `/services/ai-agents` (Production AI Agent Deployment)
4. **Investor & Partner Portal (`/investors`)** — Sovereign Obsidian vault interface, Reg D / partnership inquiry gate.
5. **Case Studies (`/case-studies`)** — *Hold pending verified client testimonials (`NEEDS VERIFICATION`).*
6. **Insights (`/insights`)** — Entity-SEO authority articles powered by `Alabaster Editorial` layout.
7. **Book Consultation (`/consultation`)** — Discovery call booking + qualification form (*wire booking URL once verified*).
8. **Legal (`/privacy`, `/terms`, `/refund-policy`, `/accessibility`)** — Mandatory CROA/FCRA & non-advice disclaimers.

## 3. Template Customization Plan (Credence Figma → Production Next.js)
1. Replace template colors with `02-COLORS-AND-TYPOGRAPHY/tokens.css` (`#0A0B0E`, `#12141A`, `#C5A059`, `#FAF8F5`).
2. Map all display headings to `'Taillevere'` / `'Auretha'`, UI/body to `'Xenon Nue'`, and KPIs/pricing tables to `'Grift'` with `font-variant-numeric: tabular-nums`.
3. Swap stock photography exclusively with the 6 verified Rick Jefferson photos (`10-PHOTOGRAPHY-AND-ILLUSTRATIONS/`) and subtle dark marble texture accents (`09-MARKETING-GRAPHICS/`).
4. Enforce WCAG 2.2 AA contrast (`#8A6A2F` bronze on light, `#DFC48C` champagne on dark) and Core Web Vitals targets (`LCP < 1.8s`, `CLS < 0.05`).
