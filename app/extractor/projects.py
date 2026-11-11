import re


class ProjectExtractor:

    @staticmethod
    def extract(text):

        if not text:
            return []

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        projects = []

        current = None

        for line in lines:

            if " - " in line:

                if current:
                    projects.append(current)

                parts = line.split(" - ", 1)

                tech = [
                    t.strip()
                    for t in parts[1].split(",")
                ]

                current = {
                    "name": parts[0].strip(),
                    "technologies": tech,
                    "description": []
                }

            else:
                

                if current:
                    current["description"].append(line)

        if current:
            projects.append(current)

        return projects