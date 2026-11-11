"""End-to-end HTTP checks for accounts, mode separation, and document flows."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from web_api import app
except ImportError:
    TestClient = None


JOB = "We need a data analyst who uses Python and SQL to build reports, analyze trends, and communicate findings to the team."
RESUME = """Alex Morgan
alex@example.com | +1 202 555 0123
SUMMARY
Data analyst with Python and SQL experience.
EXPERIENCE
I used Python and SQL to make a weekly sales dashboard for my team.
EDUCATION
Bachelor of Science in Computer Science.
"""


@unittest.skipIf(TestClient is None, "Install requirements-web.txt and httpx to run HTTP tests")
class WebApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("HIREFLOW_DB_PATH")
        os.environ["HIREFLOW_DB_PATH"] = str(Path(self.temp.name) / "accounts.sqlite3")
        self.client = TestClient(app, headers={"X-HireFlow-Request": "1"})

    def tearDown(self):
        self.client.close()
        if self.previous is None:
            os.environ.pop("HIREFLOW_DB_PATH", None)
        else:
            os.environ["HIREFLOW_DB_PATH"] = self.previous
        self.temp.cleanup()

    def signup(self):
        response = self.client.post("/api/auth/signup", json={"email":"alex@example.com","display_name":"Alex Morgan","password":"correct horse battery staple","modes":["recruiter","applicant"]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertIn("samesite=strict", response.headers["set-cookie"].lower())

    def test_signup_mode_isolation_analysis_and_saved_data(self):
        self.signup()
        self.assertIsNone(self.client.get("/api/session").json()["mode"])
        blocked = self.client.post("/api/recruiter/rank", data={"job_text":JOB}, files=[("resumes",("candidate.txt",RESUME,"text/plain"))])
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(self.client.post("/api/mode",json={"mode":"applicant"}).status_code, 200)
        self.assertEqual(self.client.post("/api/recruiter/rank", data={"job_text":JOB}, files=[("resumes",("candidate.txt",RESUME,"text/plain"))]).status_code, 403)
        result = self.client.post("/api/applicant/tailor",data={"job_text":JOB,"resume_text":RESUME})
        self.assertEqual(result.status_code,200,result.text)
        report = result.json()
        self.assertIn("audit",report)
        self.assertIn("suggestions",report)
        self.assertGreater(report["overall"],0)
        saved = self.client.post("/api/applicant/versions",json={"name":"Analyst draft","resume_text":RESUME,"target_role":"Data Analyst"})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(len(self.client.get("/api/applicant/versions").json()),1)
        project = self.client.post("/api/applicant/projects",json={"company":"Example Co","role":"Analyst","status":"Preparing","resume_text":RESUME,"job_text":JOB})
        self.assertEqual(project.status_code,200,project.text)
        self.assertEqual(len(self.client.get("/api/applicant/projects").json()),1)
        self.assertEqual(self.client.post("/api/auth/logout").status_code,200)
        self.assertEqual(self.client.get("/api/session").status_code,401)
        login = self.client.post("/api/auth/login",json={"email":"alex@example.com","password":"correct horse battery staple"})
        self.assertEqual(login.status_code,200)
        self.assertIsNone(login.json()["mode"])

    def test_recruiter_ranking_and_request_guard(self):
        self.signup()
        self.assertEqual(self.client.post("/api/mode",json={"mode":"recruiter"}).status_code,200)
        ranked = self.client.post("/api/recruiter/rank",data={"job_text":JOB},files=[("resumes",("alex.txt",RESUME,"text/plain"))])
        self.assertEqual(ranked.status_code,200,ranked.text)
        self.assertEqual(len(ranked.json()["results"]),1)
        self.assertEqual(ranked.json()["results"][0]["candidate"],"Alex Morgan")
        self.assertEqual(self.client.post("/api/applicant/health",json={"text":RESUME}).status_code,403)
        untrusted = self.client.post("/api/mode",json={"mode":"applicant"},headers={"X-HireFlow-Request":""})
        self.assertEqual(untrusted.status_code,403)

    def test_profile_document_format_and_section_order(self):
        self.signup()
        renamed = self.client.patch("/api/profile", json={"display_name":"Alex Rivera"})
        self.assertEqual(renamed.status_code, 200, renamed.text)
        self.assertEqual(self.client.get("/api/session").json()["display_name"], "Alex Rivera")
        self.assertEqual(self.client.post("/api/mode", json={"mode":"applicant"}).status_code, 200)
        checked = self.client.post(
            "/api/applicant/health-file", data={"text": RESUME},
            files={"resume_file": ("alex.txt", RESUME, "text/plain")},
        )
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertIn("checks", checked.json())
        ordered = self.client.post("/api/applicant/reorder", json={"text": RESUME, "order":["Experience", "Summary", "Education"]})
        self.assertEqual(ordered.status_code, 200, ordered.text)
        self.assertLess(ordered.json()["text"].index("EXPERIENCE"), ordered.json()["text"].index("SUMMARY"))
        invalid = self.client.post("/api/applicant/reorder", json={"text": RESUME, "order":["Incorrect"]})
        self.assertEqual(invalid.status_code, 400)

    def test_eight_character_password_policy(self):
        details = {"email":"short@example.com", "display_name":"Short Password", "modes":["applicant"]}
        too_short = self.client.post("/api/auth/signup", json={**details,"password":"seven77"})
        self.assertEqual(too_short.status_code, 400)
        self.assertIn("8 to 256", too_short.json()["detail"])
        created = self.client.post("/api/auth/signup", json={**details,"password":"eight888"})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        signed_in = self.client.post("/api/auth/login", json={"email":details["email"],"password":"eight888"})
        self.assertEqual(signed_in.status_code, 200, signed_in.text)

    def test_scanned_pdf_ocr_and_upload_validation(self):
        import fitz
        from app.analysis import extract_document
        source = fitz.open()
        page = source.new_page(width=650, height=300)
        page.insert_text((30, 75), "Data Analyst built Python and SQL reporting dashboards", fontsize=19)
        page.insert_text((30, 112), "for weekly sales analysis and business teams.", fontsize=19)
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
        scanned = fitz.open()
        scanned.new_page(width=650, height=300).insert_image(fitz.Rect(0, 0, 650, 300), stream=image)
        text = extract_document("scan.pdf", scanned.tobytes())
        self.assertIn("Python", text)
        self.assertIn("SQL", text)
        source.close(); scanned.close()
        with self.assertRaisesRegex(ValueError, "valid PDF"):
            extract_document("fake.pdf", b"not a PDF with ten readable words in it")

    def test_private_records_export_preview_and_deletion(self):
        import fitz
        self.signup()
        self.assertEqual(self.client.post("/api/mode", json={"mode":"applicant"}).status_code, 200)
        saved = self.client.post("/api/applicant/versions", json={"name":"Analyst draft","resume_text":RESUME,"target_role":"Data Analyst"})
        self.assertEqual(saved.status_code, 200, saved.text)
        version_id = saved.json()["id"]
        project = self.client.post("/api/applicant/projects", json={"company":"Example Co","role":"Analyst","status":"Preparing","notes":"Follow up Tuesday","resume_text":RESUME,"job_text":JOB})
        self.assertEqual(project.status_code, 200, project.text)
        with sqlite3.connect(os.environ["HIREFLOW_DB_PATH"]) as database:
            raw_version = database.execute("SELECT name, resume_text FROM resume_versions WHERE id=?", (version_id,)).fetchone()
            raw_project = database.execute("SELECT company, notes FROM applicant_projects").fetchone()
        self.assertTrue(all(value.startswith("hfenc:v1:") for value in raw_version + raw_project))
        self.assertNotIn("Python", str(raw_version))
        exported = self.client.post("/api/account/export", json={})
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertIn("Python", exported.text)
        self.assertNotIn("password_hash", exported.text)
        self.assertEqual(len(exported.json()["resume_versions"]), 1)
        preview = self.client.post("/api/applicant/preview", json={"text":RESUME,"template":"Contemporary","options":{},"highlights":["I used Python and SQL to make a weekly sales dashboard for my team."]})
        self.assertEqual(preview.status_code, 200, preview.text[:100])
        with fitz.open(stream=preview.content, filetype="pdf") as document:
            self.assertIn("Alex Morgan", document[0].get_text())
            self.assertGreater(sum(1 for page in document for _ in (page.annots() or [])), 0)
        self.assertEqual(self.client.delete(f"/api/applicant/versions/{version_id}").status_code, 200)
        self.assertEqual(self.client.get("/api/applicant/versions").json(), [])
        wrong = self.client.post("/api/account/delete", json={"password":"wrong","confirmation":"DELETE"})
        self.assertEqual(wrong.status_code, 400)
        removed = self.client.post("/api/account/delete", json={"password":"correct horse battery staple","confirmation":"DELETE"})
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(self.client.get("/api/session").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"alex@example.com","password":"correct horse battery staple"}).status_code, 401)

    def test_aggregate_request_limit(self):
        response = self.client.post("/api/auth/signup", content=b"x", headers={"Content-Length": str(81 * 1024 * 1024)})
        self.assertEqual(response.status_code, 413)

    def test_configured_saved_record_retention(self):
        self.signup()
        self.assertEqual(self.client.post("/api/mode", json={"mode":"applicant"}).status_code, 200)
        self.assertEqual(self.client.post("/api/applicant/versions", json={"name":"Old draft","resume_text":RESUME}).status_code, 200)
        with sqlite3.connect(os.environ["HIREFLOW_DB_PATH"]) as database:
            database.execute("UPDATE resume_versions SET created_at='2020-01-01T00:00:00+00:00'")
        previous = os.environ.get("HIREFLOW_DATA_RETENTION_DAYS")
        os.environ["HIREFLOW_DATA_RETENTION_DAYS"] = "1"
        try:
            self.assertEqual(self.client.get("/api/applicant/versions").json(), [])
        finally:
            if previous is None:
                os.environ.pop("HIREFLOW_DATA_RETENTION_DAYS", None)
            else:
                os.environ["HIREFLOW_DATA_RETENTION_DAYS"] = previous


if __name__ == "__main__":
    unittest.main()
