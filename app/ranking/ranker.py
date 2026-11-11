from .scorer import ResumeScorer
from .explain import RankingExplainer


class CandidateRanker:

    @staticmethod
    def rank(
        semantic_results,
        resumes,
        job
    ):

        ranked = []

        # Create lookup dictionary
        resume_map = {
            resume["file_name"]: resume
            for resume in resumes
        }

        for result in semantic_results:

            resume = resume_map[result["resume"]]

            # -----------------------------
            # Individual Scores
            # -----------------------------

            semantic = ResumeScorer.semantic_score(
                result["score"]
            )

            skill = ResumeScorer.skill_score(
                resume["skills"],
                job["skills"]
            )

            experience = ResumeScorer.experience_score(
                resume["experience"],
                job["experience"]
            )

            education = ResumeScorer.education_score(
                resume["education"],
                job["education"]
            )

            final = ResumeScorer.final_score(
                semantic,
                skill,
                experience,
                education
            )

            # -----------------------------
            # Explainability
            # -----------------------------

            explanation = RankingExplainer.explain(
                resume["skills"],
                job["skills"]
            )

            ranked.append({

                "candidate": resume["name"],

                "resume": resume["file_name"],

                "semantic": semantic,

                "skill": skill,

                "experience": experience,

                "education": education,

                "matched_skills": explanation["matched"],

                "missing_skills": explanation["missing"],

                "final_score": final

            })

        ranked.sort(
            key=lambda x: x["final_score"],
            reverse=True
        )

        return ranked