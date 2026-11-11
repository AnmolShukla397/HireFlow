"""Regression fixtures for scoring behavior; not a claim of hiring validity."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import analysis


FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ranking_benchmark.json").read_text())


class RankingBenchmarkTests(unittest.TestCase):
    def test_each_role_ranks_relevant_resume_first(self):
        with patch.dict(os.environ, {"HIREFLOW_SIMILARITY_BACKEND": "keyword"}):
            for role, job in FIXTURE["jobs"].items():
                with self.subTest(role=role):
                    reports = {name: analysis.analyse(job, resume) for name, resume in FIXTURE["resumes"].items()}
                    winner = max(reports, key=lambda name: reports[name]["overall"])
                    self.assertEqual(winner, FIXTURE["expected_top"][role])
                    self.assertTrue(all(report["scoring_version"] == analysis.SCORING_VERSION for report in reports.values()))
                    self.assertTrue(all(report["semantic_method"] == "keyword cosine" for report in reports.values()))

    def test_contact_identity_does_not_change_similarity(self):
        job = FIXTURE["jobs"]["data"]
        resume = FIXTURE["resumes"]["data"]
        other = resume.replace("Maya Chen", "Robin Taylor").replace("maya@example.com", "robin@example.org")
        with patch.dict(os.environ, {"HIREFLOW_SIMILARITY_BACKEND": "keyword"}):
            self.assertEqual(analysis.analyse(job, resume)["semantic"], analysis.analyse(job, other)["semantic"])

    def test_unavailable_explicit_backend_fails_clearly(self):
        with patch.dict(os.environ, {"HIREFLOW_SIMILARITY_BACKEND": "local"}), patch.object(analysis, "_local_model", return_value=None):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                analysis.analyse(FIXTURE["jobs"]["data"], FIXTURE["resumes"]["data"])


if __name__ == "__main__":
    unittest.main()
