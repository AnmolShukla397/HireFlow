import re

from app.extractor.skills import SkillExtractor


class JobExtractor:

    def __init__(self):

        self.skill_extractor = SkillExtractor()

    def extract(self, text):

        skills = self.skill_extractor.extract(text)

        experience = ""

        education = ""

        title = ""

        # -----------------------------
        # Job Title
        # -----------------------------

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        if lines:
            title = lines[0]

        # -----------------------------
        # Experience
        # -----------------------------

        exp = re.search(

            r"(\d+\+?\s*[-–]?\s*\d*\s*years?)",

            text,

            re.IGNORECASE

        )

        if exp:

            experience = exp.group()

        # -----------------------------
        # Education
        # -----------------------------

        degree = re.search(

            r"(Bachelor|Master|B\.Tech|M\.Tech|B\.E|M\.E).*",

            text,

            re.IGNORECASE

        )

        if degree:

            education = degree.group()

        return {

            "title": title,

            "skills": skills,

            "experience": experience,

            "education": education

        }