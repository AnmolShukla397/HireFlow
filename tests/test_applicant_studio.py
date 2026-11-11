"""Applicant studio workflows and account-owned application storage."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import fitz

from app import accounts, analysis, applicant_tools, resume_coach


JOB = "Data analyst role at Northstar. Build Python and SQL dashboards for stakeholders and explain business results."
RESUME = """Alex Rao
alex@example.com
SUMMARY
Data analyst with reporting experience.
SKILLS
Python, SQL
EXPERIENCE
- Built a Python and SQL dashboard for weekly sales reporting.
"""


class ApplicantStudioTests(unittest.TestCase):
    def test_resume_only_review_guided_edit_and_formatting(self):
        report = applicant_tools.resume_health(RESUME)
        self.assertGreater(report["score"], 0)
        self.assertIn("Content", report["areas"])
        revised, bullet = applicant_tools.apply_guided_example(RESUME, "I used Python and SQL to build a weekly sales dashboard for my team")
        self.assertIn(bullet, revised)
        self.assertGreater(revised.index(bullet), revised.index("\nEXPERIENCE"))
        reordered = applicant_tools.reorder_sections(revised, ["Experience", "Summary", "Skills"])
        self.assertLess(reordered.index("EXPERIENCE"), reordered.index("SUMMARY"))
        mapped = applicant_tools.keyword_map(JOB, RESUME)
        self.assertTrue(any(item["status"] == "Supported" for item in mapped))
        options = {"body_size": 12, "heading_size": 14, "line_spacing": 1.3, "margin": 1.0}
        self.assertTrue(analysis.export_docx(reordered, options=options).startswith(b"PK"))
        with fitz.open(stream=analysis.export_pdf(reordered, options=options), filetype="pdf") as document:
            self.assertIn("Alex Rao", document[0].get_text())

    def test_builder_analysis_coach_and_letter_exports(self):
        built = applicant_tools.build_resume({
            "name": "Alex Rao", "email": "alex@example.com", "skills": "Python, SQL",
            "experience": "- Built a Python and SQL dashboard for weekly sales reporting.",
        })
        self.assertIn("\nEXPERIENCE\n", built)
        self.assertIn("alex@example.com", built)
        result = analysis.analyse(JOB, RESUME)
        result["audit"] = resume_coach.audit_resume(JOB, RESUME, result)
        with patch.dict(os.environ, {"HIREFLOW_OPENAI_API_KEY": ""}):
            reply, source = applicant_tools.coach_reply("Which job skills am I missing?", JOB, RESUME, result)
            letter, letter_source = applicant_tools.cover_letter(JOB, RESUME, "Northstar", "Data analyst")
        self.assertIn("recognized job skills", reply.lower())
        self.assertIn("Document-based", source)
        self.assertIn("Northstar", letter)
        self.assertIn("Python and SQL dashboard", letter)
        self.assertIn("Grounded", letter_source)
        self.assertTrue(applicant_tools.export_letter_docx(letter).startswith(b"PK"))
        with fitz.open(stream=applicant_tools.export_letter_pdf(letter), filetype="pdf") as document:
            self.assertIn("Northstar", document[0].get_text())

    def test_projects_are_private_and_survive_new_connections(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HIREFLOW_DB_PATH": os.path.join(directory, "accounts.sqlite3")}):
            accounts.create_account("alex@example.com", "Alex Rao", "longsecurepassword1")
            accounts.create_account("sam@example.com", "Sam Lee", "longsecurepassword2", ["applicant"])
            accounts.create_account("hr@example.com", "HR Lee", "longsecurepassword3", ["recruiter"])
            identity = accounts.save_project("alex@example.com", "Northstar", "Data analyst", "Preparing", JOB, RESUME)
            self.assertEqual(len(accounts.list_projects("alex@example.com")), 1)
            self.assertEqual(accounts.list_projects("sam@example.com"), [])
            with self.assertRaises(ValueError):
                accounts.save_project("sam@example.com", "Northstar", "Data analyst", "Applied", project_id=identity)
            with self.assertRaises(ValueError):
                accounts.list_projects("hr@example.com")
            self.assertFalse(accounts.delete_project("sam@example.com", identity))
            self.assertTrue(accounts.delete_project("alex@example.com", identity))
            self.assertEqual(accounts.list_projects("alex@example.com"), [])

    def test_named_resume_versions_are_owned_and_can_be_duplicated(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"HIREFLOW_DB_PATH": os.path.join(directory, "accounts.sqlite3")}):
            accounts.create_account("alex@example.com", "Alex Rao", "longsecurepassword1")
            accounts.create_account("sam@example.com", "Sam Lee", "longsecurepassword2", ["applicant"])
            base = accounts.save_resume_version("alex@example.com", "Base", RESUME, "Data analyst")
            copy = accounts.save_resume_version("alex@example.com", "Northstar", RESUME, "Data analyst", source_id=base)
            versions = accounts.list_resume_versions("alex@example.com")
            self.assertEqual({item["id"] for item in versions}, {base, copy})
            self.assertEqual(next(item for item in versions if item["id"] == copy)["source_id"], base)
            self.assertEqual(accounts.list_resume_versions("sam@example.com"), [])
            with self.assertRaises(ValueError):
                accounts.save_resume_version("sam@example.com", "Copy", RESUME, source_id=base)

    def test_ai_tailoring_rejects_new_metrics_and_skills(self):
        candidates = '[{"line_index": 7, "after": "- Built a Python and SQL dashboard for weekly sales reporting, increasing revenue 30%.", "reason": "Impact"}, {"line_index": 7, "after": "- Developed a Python and SQL dashboard for weekly sales reporting.", "reason": "Clearer action"}]'
        with patch.dict(os.environ, {"HIREFLOW_OPENAI_API_KEY": "test"}), patch.object(applicant_tools, "_ai_text", return_value=candidates):
            suggestions = applicant_tools.ai_tailoring_suggestions(JOB, RESUME, set())
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["after"], "- Developed a Python and SQL dashboard for weekly sales reporting.")


if __name__ == "__main__":
    unittest.main()
