"""Regression coverage for job-specific applicant recommendations."""

import unittest

import fitz

from app import analysis, resume_coach


JOB = (
    "Senior data scientist with four years of experience. Build Python and SQL "
    "machine learning models using Pandas, Docker and AWS. Bachelor degree required."
)
RESUME = """Alex Rao
alex@example.com
SUMMARY
Data scientist with five years of experience and Bachelor degree.
SKILLS
Python, SQL, Pandas and ML.
EXPERIENCE
Responsible for building recommendation models and data pipelines for clients."""


class ApplicantRecommendationTests(unittest.TestCase):
    def test_suggestions_are_changes_grounded_in_job_and_resume(self):
        result = analysis.analyse(JOB, RESUME)
        self.assertEqual(result["required_years"], 4)
        self.assertEqual(result["resume_years"], 5)
        replacements = [item for item in result["suggestions"] if item["kind"] == "replace"]
        self.assertTrue(replacements)
        self.assertTrue(all(item["after"] != item["before"].strip() for item in replacements))
        categories = {item["category"] for item in replacements}
        self.assertIn("Targeted summary", categories)
        self.assertIn("Job keyword", categories)
        self.assertIn("Professional wording", categories)
        for item in replacements:
            changed = analysis.apply_decisions(RESUME, [item], {item["id"]: "accepted"}, {})
            self.assertGreater(analysis.estimate_ats(JOB, changed), result["ats"])
        self.assertEqual(
            analysis.apply_decisions(RESUME, replacements, {item["id"]: "rejected" for item in replacements}, {}),
            RESUME + "\n",
        )

    def test_missing_skill_evidence_is_rewritten_and_validated(self):
        result = analysis.analyse(JOB, RESUME)
        suggestion = next(item for item in result["suggestions"] if item.get("skill") == "Docker")
        proposed = analysis.draft_skill_bullet(
            "Docker", "I have used Docker for containerizing microservices in my internship"
        )
        self.assertEqual(proposed, "- Containerized microservices in my internship using Docker.")
        self.assertEqual(
            analysis.draft_skill_bullet("Docker", "In my internship, I used Docker to deploy microservices"),
            "- Deployed microservices using Docker during my internship.",
        )
        changed = analysis.apply_decisions(RESUME, [suggestion], {suggestion["id"]: "accepted"}, {suggestion["id"]: proposed})
        self.assertIn(proposed, changed)
        self.assertNotIn("ADDITIONAL RELEVANT EXPERIENCE", changed)
        self.assertGreater(changed.index(proposed), changed.index("\nEXPERIENCE"))
        self.assertGreater(analysis.estimate_ats(JOB, changed), result["ats"])
        with self.assertRaises(ValueError):
            analysis.draft_skill_bullet("Docker", "I built useful data pipelines for clients")
        with self.assertRaises(ValueError):
            analysis.draft_skill_bullet("Docker", "I know Docker")

    def test_casual_evidence_becomes_a_professional_line_in_the_right_section(self):
        resume = RESUME + "\nEDUCATION\nBachelor of Science"
        experience = resume_coach.rewrite_evidence("In my internship, I used Docker to deploy microservices", JOB, "Docker")
        project = resume_coach.rewrite_evidence("I used Python and SQL to build a sales dashboard in my project", JOB)
        self.assertEqual(experience["bullet"], "- Deployed microservices using Docker during my internship.")
        self.assertEqual(project["bullet"], "- Built a sales dashboard in my project using Python and SQL.")
        self.assertEqual(project["placement"], "Projects")
        suggestions = [{"id": "experience", "kind": "add"}, {"id": "project", "kind": "add"}]
        changed = analysis.apply_decisions(resume, suggestions, {"experience": "accepted", "project": "accepted"}, {"experience": experience["bullet"], "project": project["bullet"]}, {"experience": "Experience", "project": "Projects"})
        self.assertLess(changed.index(experience["bullet"]), changed.index("\nPROJECTS"))
        self.assertLess(changed.index(project["bullet"]), changed.index("\nEDUCATION"))
        with self.assertRaises(ValueError):
            resume_coach.rewrite_evidence("I did some stuff with Docker for work", JOB, "Docker")

    def test_report_distinguishes_content_from_uninspected_visual_layout(self):
        result = analysis.analyse(JOB, RESUME)
        checks = resume_coach.audit_resume(JOB, RESUME, result)
        by_title = {item["title"]: item for item in checks}
        self.assertEqual(by_title["Original layout not inspected"]["status"], "review")
        self.assertEqual(by_title["Phone number"]["status"], "review")
        self.assertEqual(by_title["Measurable impact"]["status"], "review")
        self.assertEqual(by_title["Job skills in the resume"]["status"], "review")
        self.assertEqual(analysis._contact("Data Analyst | Acme | 2021-2024")["phone"], "")

    def test_uploaded_pdf_flags_overlapping_columns_and_exports_remain_selectable(self):
        document = fitz.open()
        page = document.new_page()
        for y in (100, 150):
            page.insert_text((50, y), "Built Python pipelines for customer reporting teams", fontsize=10)
            page.insert_text((330, y), "Analyzed SQL data for weekly sales dashboards", fontsize=10)
        data = document.tobytes()
        document.close()
        text = analysis.extract_document("columns.pdf", data)
        result = analysis.analyse(JOB, text)
        checks = resume_coach.audit_resume(JOB, text, result, "columns.pdf", data)
        self.assertEqual(next(item for item in checks if item["title"] == "Column reading order")["status"], "review")
        with fitz.open(stream=analysis.export_pdf(RESUME, "Contemporary"), filetype="pdf") as exported:
            self.assertIn("Responsible for building recommendation models", exported[0].get_text())


if __name__ == "__main__":
    unittest.main()
