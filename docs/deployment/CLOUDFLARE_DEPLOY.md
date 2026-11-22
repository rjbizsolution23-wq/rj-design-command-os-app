# Cloudflare Cloud Deployment Runbook (Phase 5 — iPhone & Global HTTPS Access)

Deploy **RJ Design Command OS v3.0** to Cloudflare Workers + D1 + R2 so it is securely accessible from your iPhone and desktop over HTTPS with zero secrets in version control.

## 1. Provision D1 & R2

```bash
cd infrastructure/cloudflare
wrangler d1 create rj-design-command-db
wrangler r2 bucket create rj-design-command-assets
```

Paste the returned `database_id` into `infrastructure/cloudflare/wrangler.toml`.

## 2. Apply Database Schema

```bash
wrangler d1 execute rj-design-command-db --remote --file=./migrations/0001_init.sql
```

## 3. Configure Encrypted Secrets (Never Commit `.env`)

```bash
wrangler secret put RJ_SESSION_SECRET
wrangler secret put RJ_ADMIN_PASSWORD
```

## 4. Deploy to Cloudflare Edge

```bash
wrangler deploy
```

## 5. Verify on iPhone

1. Open `https://rj-design-command-os.<your-subdomain>.workers.dev/api/health` in Safari on iPhone.
2. Confirm `{"ok": true, "runtime": "cloudflare-workers", "contract_version": "2.1.0"}`.
3. Optionally place behind **Cloudflare Access (Zero Trust MFA)** for hardware-key / biometric iPhone login.
