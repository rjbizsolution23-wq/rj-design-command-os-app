import http.client
import io
import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class SovereignEnterpriseAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        server.DATABASE = Path(cls.temp.name) / "test.sqlite3"
        server.BACKUP_DIR = Path(cls.temp.name) / "backups"
        server.connect().close()
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), server.API)
        cls.port = cls.http.server_port
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.temp.cleanup()

    def request_raw(self, method, path, body=None, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        payload = json.dumps(body).encode() if body is not None else None
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection.request(method, path, body=payload, headers=headers)
        result = connection.getresponse()
        status = result.status
        data = result.read()
        connection.close()
        return status, data

    def request(self, method, path, body=None, token=None):
        status, raw = self.request_raw(method, path, body, token=token)
        return status, json.loads(raw.decode("utf-8"))

    def login(self, username, password=None):
        status, data = self.request(
            "POST",
            "/api/auth/login",
            {"username": username, "password": password or server.DEFAULT_ADMIN_PASSWORD},
        )
        self.assertEqual(status, 200)
        return data["token"]

    def test_01_health_catalogs_and_contract_validation(self):
        status, health = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["styles_count"], 12)
        self.assertEqual(health["departments_count"], 8)
        self.assertEqual(health["industries_count"], 8)

        status, contract = self.request("GET", "/api/contracts/validate")
        self.assertEqual(status, 200)
        self.assertTrue(contract["valid"])
        self.assertEqual(contract["contract_version"], "2.1.0")

        # Verify universal memo template contains ZERO hardcoded bank routing numbers
        status, memo_bytes = self.request_raw("GET", "/api/brand/export/memo")
        self.assertEqual(status, 200)
        memo_html = memo_bytes.decode("utf-8")
        self.assertNotIn("121000248", memo_html)
        self.assertNotIn("rjbizsolution23@gmail.com", memo_html)
        self.assertIn("Protected Settlement Issuance", memo_html)

    def test_02_authentication_and_rbac_negative_paths(self):
        # Unauthenticated writes must be rejected (401)
        self.assertEqual(self.request("PUT", "/api/brand", {"identity": {"subline": "HACK"}})[0], 401)
        self.assertEqual(self.request("POST", "/api/projects", {"name": "X", "industry": "Y", "audience": "Z", "brief": "B", "mood": "M"})[0], 401)
        self.assertEqual(self.request("POST", "/api/auth/login", {"username": "principal", "password": "wrong"})[0], 401)

        # Viewer role cannot mutate brand or create projects (403)
        viewer_token = self.login("viewer")
        self.assertEqual(self.request("PUT", "/api/brand", {"identity": {"subline": "NOPE"}}, token=viewer_token)[0], 403)
        self.assertEqual(self.request("POST", "/api/projects", {"name": "X", "industry": "Y", "audience": "Z", "brief": "B", "mood": "M"}, token=viewer_token)[0], 403)

        # Director role cannot mutate global brand or run admin backup (403)
        director_token = self.login("director")
        self.assertEqual(self.request("PUT", "/api/brand", {"identity": {"subline": "NOPE"}}, token=director_token)[0], 403)
        self.assertEqual(self.request("POST", "/api/admin/backup", {}, token=director_token)[0], 403)

    def test_03_brand_contract_rejects_invalid_tokens_and_banking_injection(self):
        principal = self.login("principal")
        # Invalid HEX must be rejected
        status, err = self.request("PUT", "/api/brand", {"palette": {"gold": "not-a-hex"}}, token=principal)
        self.assertEqual(status, 400)
        self.assertIn("validation", err)

        # Banking data injection into universal brand template must be rejected
        status, err = self.request("PUT", "/api/brand", {"identity": {"settlement_wire_routing": "121000248"}}, token=principal)
        self.assertEqual(status, 400)
        self.assertFalse(err["validation"]["valid"])

    def test_04_protected_settlement_workflow_and_real_pdf_export(self):
        director = self.login("director")
        principal = self.login("principal")

        # Director creates pending settlement record
        status, created = self.request(
            "POST",
            "/api/settlements",
            {
                "recipient_name": "Meridian Family Office LP",
                "method": "wire",
                "institution": "Private Institutional Escrow Trust",
                "reference_code": "RJ-LP-2026-9901",
            },
            token=director,
        )
        self.assertEqual(status, 201)
        sid = created["id"]

        # Unverified settlement cannot be approved (400)
        self.assertEqual(self.request("POST", f"/api/settlements/{sid}/approve", {}, token=principal)[0], 400)
        # Unapproved settlement cannot be attached to memo (403)
        self.assertEqual(self.request("GET", f"/api/brand/export/memo?settlement_id={sid}", token=principal)[0], 403)

        # Director verifies recipient, cannot approve (403)
        self.assertEqual(self.request("POST", f"/api/settlements/{sid}/verify", {}, token=director)[0], 200)
        self.assertEqual(self.request("POST", f"/api/settlements/{sid}/approve", {}, token=director)[0], 403)

        # Principal approves
        status, approved = self.request("POST", f"/api/settlements/{sid}/approve", {}, token=principal)
        self.assertEqual(status, 200)
        self.assertEqual(approved["approval_status"], "approved")

        # Authorized Memo HTML now includes the approved settlement reference
        status, memo_bytes = self.request_raw("GET", f"/api/brand/export/memo?settlement_id={sid}", token=principal)
        self.assertEqual(status, 200)
        self.assertIn("RJ-LP-2026-9901", memo_bytes.decode("utf-8"))

        # Real Binary PDF Export via Headless Chrome
        if server.find_chrome_binary():
            status, pdf_bytes = self.request_raw("GET", f"/api/brand/export/pdf?settlement_id={sid}", token=principal)
            self.assertEqual(status, 200)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
            self.assertGreater(len(pdf_bytes), 5000)

    def test_05_ai_creative_director_sector_inheritance_and_react_scaffold(self):
        director = self.login("director")
        principal = self.login("principal")

        # Non-RJ client project in luxury hospitality should inherit hospitality palette, NOT RJ's palette
        status, created = self.request(
            "POST",
            "/api/projects",
            {
                "name": "Kyoto Cedar Sanctuary",
                "industry": "luxury hospitality and resort",
                "audience": "ultra-high-net-worth travelers",
                "brief": "Serene boutique sanctuary hotel and seasonal dining reservation platform",
                "mood": "Architectural quiet luxury",
            },
            token=director,
        )
        self.assertEqual(status, 201)
        pid = created["id"]

        status, run = self.request("POST", f"/api/projects/{pid}/orchestrate", {}, token=director)
        self.assertEqual(status, 201)
        self.assertEqual(run["departments_executed"], 8)
        self.assertEqual(run["total_specialists"], 56)
        self.assertEqual(run["industry_intelligence"]["id"], "hospitality-sanctuary")
        self.assertIn("Client-Specific", run["palette_inheritance"])

        status, scaffold = self.request("GET", f"/api/projects/{pid}/scaffold", token=director)
        self.assertEqual(status, 200)
        self.assertIn("package.json", scaffold["files"])
        self.assertIn("src/App.tsx", scaffold["files"])
        self.assertIn("src/theme.css", scaffold["files"])

        # 10-category evaluation with critical Security blocker
        bad_scores = {name: 5 for name, _ in server.CATEGORIES}
        bad_scores["Security and privacy"] = 2
        status, eval_res = self.request(
            "POST",
            f"/api/projects/{pid}/evaluate",
            {"name": "Security Gate Check", "metrics": bad_scores},
            token=director,
        )
        self.assertEqual(status, 201)
        self.assertIn("Security and privacy", eval_res["blockers"])
        self.assertEqual(eval_res["status"], "Needs refinement")

        # Principal can delete project
        self.assertEqual(self.request("DELETE", f"/api/projects/{pid}", token=director)[0], 403)
        self.assertEqual(self.request("DELETE", f"/api/projects/{pid}", token=principal)[0], 200)

    def test_06_online_sqlite_backup_and_audit_log(self):
        principal = self.login("principal")
        status, backup = self.request("POST", "/api/admin/backup", {}, token=principal)
        self.assertEqual(status, 201)
        backup_file = server.BACKUP_DIR / backup["backup"]
        self.assertTrue(backup_file.exists())
        # Verify backup SQLite integrity
        with sqlite3.connect(backup_file, factory=server.ClosingConnection) as conn:
            check = conn.execute("PRAGMA integrity_check").fetchone()[0]
            self.assertEqual(check, "ok")

        status, logs = self.request("GET", "/api/audit", token=principal)
        self.assertEqual(status, 200)
        self.assertGreater(len(logs), 3)

    def test_07_production_assets_3d_zip_and_repo_adapter(self):
        director = self.login("director")

        # Commercial SVG crest + 3-slide investor deck
        for asset_type, expected_marker in [
            ("monogram-crest", "<svg"),
            ("investor-banner", "1200 628"),
            ("investor-deck", "Slide 01 / 03"),
        ]:
            status, meta = self.request(
                "POST",
                "/api/production/assets",
                {"asset_type": asset_type, "title": "Sovereign Capital", "subtitle": "Institutional Architecture"},
                token=director,
            )
            self.assertEqual(status, 201)
            self.assertEqual(len(meta["sha256"]), 64)
            status, raw = self.request_raw("GET", meta["download_url"])
            self.assertEqual(status, 200)
            self.assertIn(expected_marker, raw.decode("utf-8"))

        # Universal Repository Adapter (read-only inspection)
        status, repo_report = self.request(
            "POST",
            "/api/production/inspect-repo",
            {"path": str(Path(__file__).resolve().parents[1])},
            token=director,
        )
        self.assertEqual(status, 200)
        self.assertEqual(repo_report["framework_detected"], "Python Application")

        # Create project -> generate 3D R3F scene -> download real .zip React+3D bundle
        status, created = self.request(
            "POST",
            "/api/projects",
            {
                "name": "Meridian Private Vault",
                "industry": "private wealth",
                "audience": "family offices",
                "brief": "Luxury LP portal with 3D sculpture emblem",
                "mood": "Sovereign and institutional",
            },
            token=director,
        )
        self.assertEqual(status, 201)
        pid = created["id"]

        status, scene = self.request("GET", f"/api/projects/{pid}/3d-scene", token=director)
        self.assertEqual(status, 200)
        self.assertTrue(scene["budget_report"]["mobile_fallback_verified"])
        self.assertIn("src/SovereignSculptureScene.tsx", scene["files"])

        status, zip_bytes = self.request_raw("GET", f"/api/projects/{pid}/bundle.zip", token=director)
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = set(zf.namelist())
            self.assertIn("package.json", names)
            self.assertIn("src/App.tsx", names)
            self.assertIn("src/SovereignSculptureScene.tsx", names)

    def test_08_automated_qa_engine_live_audit(self):
        principal = self.login("principal")
        status, report = self.request("POST", "/api/qa/run", {}, token=principal)
        self.assertEqual(status, 201)
        self.assertGreaterEqual(report["score"], 90.0)
        self.assertTrue(report["release_approved"])
        self.assertEqual(len(report["screenshots"]), 2 if server.find_chrome_binary() else 0)

    def test_09_envato_vault_fonts_assets_and_contact_directory(self):
        status, vault = self.request("GET", "/api/vault")
        self.assertEqual(status, 200)
        self.assertEqual(len(vault["envato_kits"]), 5)
        self.assertGreaterEqual(len(vault["logos"]), 4)
        self.assertGreaterEqual(len(vault["photos"]), 6)
        self.assertGreaterEqual(len(vault["templates"]), 3)
        self.assertEqual(vault["contact_directory"]["telephone"], "(817) 587-4783")
        # P0 security check: settlement info scrubbed from public vault contact directory
        self.assertNotIn("settlement", vault["contact_directory"])

        # Verify licensed Envato font CSS & logo serve cleanly
        status, css_bytes = self.request_raw("GET", "/fonts/rj-luxury/rj-luxury-fonts.css")
        self.assertEqual(status, 200)
        self.assertIn("Taillevere", css_bytes.decode("utf-8"))

        status, logo_bytes = self.request_raw("GET", "/vault/logos/rj-luxury-black-gold-logo-primary.png")
        self.assertEqual(status, 200)
        self.assertGreater(len(logo_bytes), 50000)

        # Path traversal attempt must be blocked (403)
        status, _ = self.request_raw("GET", "/vault/..%2Fserver.py")
        self.assertEqual(status, 403)

    def test_10_envato_connector_search_install_and_rebrand(self):
        director = self.login("director")
        status, st = self.request("GET", "/api/envato/status")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(st["vault_archives_count"], 22)

        status, search_res = self.request("GET", "/api/envato/search?q=taillevere&category=fonts")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(search_res["matches"]), 1)
        asset_id = search_res["matches"][0]["id"]

        target_dir = Path(self.temp.name) / "envato-installed-proj"
        status, inst = self.request(
            "POST",
            "/api/envato/install",
            {"asset_id": asset_id, "target_dir": str(target_dir), "apply_rj_branding": True},
            token=director,
        )
        self.assertEqual(status, 200)
        self.assertGreater(inst["extracted_count"], 0)
        self.assertTrue(inst["rj_branding_applied"])
        self.assertTrue((target_dir / "rj-brand" / "rj-sovereign-tokens.css").exists())
        self.assertTrue((target_dir / "rj-brand" / "logos" / "rj-luxury-black-gold-logo-primary.png").exists())


if __name__ == "__main__":
    unittest.main()
