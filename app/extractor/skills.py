import re


class SkillExtractor:

    def __init__(self, skill_file="data/skills.txt"):

        with open(skill_file, "r", encoding="utf-8") as f:
            self.skills = [
                skill.strip()
                for skill in f.readlines()
                if skill.strip()
            ]

    def extract(self, text):

        text_lower = text.lower()

        found_skills = []

        for skill in self.skills:

            pattern = r"\b" + re.escape(skill.lower()) + r"\b"

            if re.search(pattern, text_lower):
                found_skills.append(skill)

        return sorted(list(set(found_skills)))