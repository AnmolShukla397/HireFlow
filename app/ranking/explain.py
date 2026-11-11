class RankingExplainer:

    @staticmethod
    def explain(resume_skills, job_skills):

        resume = {
            skill.lower(): skill
            for skill in resume_skills
        }

        matched = []
        missing = []

        for skill in job_skills:

            if skill.lower() in resume:

                matched.append(skill)

            else:

                missing.append(skill)

        return {

            "matched": matched,

            "missing": missing

        }