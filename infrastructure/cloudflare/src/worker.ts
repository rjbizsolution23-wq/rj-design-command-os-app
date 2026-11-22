/**
 * RJ Design Command OS v3.0 — Cloudflare Workers Edge API (D1 + R2 + Web Crypto Signed Sessions + RBAC)
 * Securely accessible from desktop and iPhone over HTTPS.
 */

export interface Env {
  DB: D1Database;
  ASSETS: R2Bucket;
  RJ_SESSION_SECRET: string;
  RJ_ADMIN_PASSWORD: string;
}

const CONTRACT_VERSION = "2.1.0";

const SECURITY_HEADERS: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Cache-Control": "no-store",
  "Content-Security-Policy": "default-src 'none'",
};

function jsonResponse(payload: unknown, status = 200, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...SECURITY_HEADERS, ...extra },
  });
}

async function signToken(payload: Record<string, unknown>, secret: string): Promise<string> {
  const enc = new TextEncoder();
  const body = btoa(JSON.stringify(payload));
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sigBuf = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  const sig = Array.from(new Uint8Array(sigBuf)).map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${body}.${sig}`;
}

async function verifyToken(token: string, secret: string): Promise<Record<string, unknown> | null> {
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const [body, sig] = parts;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const sigBytes = new Uint8Array((sig.match(/.{1,2}/g) || []).map((h) => parseInt(h, 16)));
  const ok = await crypto.subtle.verify("HMAC", key, sigBytes, enc.encode(body));
  if (!ok) return null;
  const parsed = JSON.parse(atob(body)) as Record<string, unknown>;
  if (Number(parsed.exp || 0) < Math.floor(Date.now() / 1000)) return null;
  return parsed;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "GET" && path === "/api/health") {
      return jsonResponse({
        ok: true,
        runtime: "cloudflare-workers",
        contract_version: CONTRACT_VERSION,
        brand_edition: "Sovereign Luxury Investor v3.0",
      });
    }

    if (request.method === "POST" && path === "/api/auth/login") {
      const body = (await request.json().catch(() => ({}))) as { username?: string; password?: string };
      if (!env.RJ_ADMIN_PASSWORD || !env.RJ_SESSION_SECRET) {
        return jsonResponse({ error: "Worker secrets not configured via wrangler secret put" }, 503);
      }
      if (body.username !== "principal" || body.password !== env.RJ_ADMIN_PASSWORD) {
        return jsonResponse({ error: "Invalid credentials" }, 401);
      }
      const token = await signToken(
        { sub: "principal", role: "principal", exp: Math.floor(Date.now() / 1000) + 28800 },
        env.RJ_SESSION_SECRET,
      );
      return jsonResponse(
        { authenticated: true, token, user: { username: "principal", role: "principal" } },
        200,
        { "Set-Cookie": `rj_session=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=28800` },
      );
    }

    if (request.method === "GET" && path === "/api/projects") {
      const { results } = await env.DB.prepare("SELECT * FROM projects ORDER BY updated_at DESC").all();
      return jsonResponse(results || []);
    }

    if (request.method === "POST" && path === "/api/projects") {
      const auth = request.headers.get("Authorization") || "";
      const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
      const session = await verifyToken(token, env.RJ_SESSION_SECRET || "");
      if (!session) return jsonResponse({ error: "Authentication required" }, 401);

      const data = (await request.json().catch(() => ({}))) as Record<string, string>;
      const fields = ["name", "industry", "audience", "brief", "mood"].map((k) => (data[k] || "").trim());
      if (fields.some((v) => !v)) return jsonResponse({ error: "All project fields are required" }, 400);

      const id = crypto.randomUUID().replace(/-/g, "");
      const ts = new Date().toISOString();
      await env.DB.prepare("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)")
        .bind(id, fields[0], fields[1], fields[2], fields[3], fields[4], ts, ts)
        .run();
      await env.DB.prepare("INSERT INTO audit_logs VALUES (?,?,?,?,?,?,?)")
        .bind(crypto.randomUUID().replace(/-/g, ""), String(session.sub), String(session.role), "project:create", id, fields[0], ts)
        .run();
      return jsonResponse({ id }, 201);
    }

    if (request.method === "GET" && path.startsWith("/api/assets/")) {
      const key = path.replace("/api/assets/", "");
      const obj = await env.ASSETS.get(key);
      if (!obj) return jsonResponse({ error: "Asset not found" }, 404);
      return new Response(obj.body, {
        headers: {
          "Content-Type": obj.httpMetadata?.contentType || "application/octet-stream",
          "X-Content-Type-Options": "nosniff",
        },
      });
    }

    return jsonResponse({ error: "Not found" }, 404);
  },
};
