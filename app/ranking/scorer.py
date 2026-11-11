import re


class ResumeScorer:

    @staticmethod
    def semantic_score(score):
        """
        Convert cosine similarity (0-1) to percentage.
        """
        return round(score * 100, 2)

    @staticmethod
    def skill_score(resume_skills, job_skills):
        """
        Percentage of required job skills present in the resume.
        """

        if not job_skills:
            return 100.0

        resume = {
            skill.lower().strip()
            for skill in resume_skills
        }

        job = {
            skill.lower().strip()
            for skill in job_skills
        }

        matched = resume.intersection(job)

        return round(
            (len(matched) / len(job)) * 100,
            2
        )

    @staticmethod
    def experience_score(
        resume_experience,
        required_experience
    ):
        """
        Scores experience based on the number of experience entries.
        Later we can replace this with actual duration calculation.
        """

        if not required_experience:
            return 100.0

        # Extract all numbers from strings like:
        # "0-2 years"
        # "3+ years"
        # "5 years"

        numbers = re.findall(
            r"\d+",
            required_experience
        )

        if not numbers:
            return 100.0

        # Use the largest number
        required = max(
            int(n)
            for n in numbers
        )

        # Prevent divide by zero
        if required == 0:
            return 100.0

        # Number of experience entries
        actual = len(resume_experience)

        score = min(
            (actual / required) * 100,
            100
        )

        return round(score, 2)

    @staticmethod
    def education_score(
        resume_education,
        job_education
    ):

        if not job_education:
            return 100.0

        degree = resume_education.get(
            "degree",
            ""
        ).lower()

        job = job_education.lower()

        if (
            "bachelor" in job
            and (
                "bachelor" in degree
                or "b.tech" in degree
                or "b.e" in degree
            )
        ):
            return 100.0

        if (
            "master" in job
            and (
                "master" in degree
                or "m.tech" in degree
                or "m.e" in degree
            )
        ):
            return 100.0

        return 50.0

    @staticmethod
    def final_score(
        semantic,
        skill,
        experience,
        education
    ):
        """
        Weighted hybrid score.
        """

        score = (
            semantic * 0.50 +
            skill * 0.30 +
            experience * 0.10 +
            education * 0.10
        )

        return round(score, 2)