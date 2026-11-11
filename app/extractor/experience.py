import re


class ExperienceExtractor:

    MONTH_PATTERN = (
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    )

    @staticmethod
    def extract(text):

        if not text:
            return []

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        # Remove repository links
        lines = [
            line
            for line in lines
            if not line.lower().startswith(
                ("repo:", "github:", "repository:")
            )
        ]

        experiences = []

        current = None

        i = 0

        while i < len(lines):

            # Detect new role

            if current is None:

                current = {
                    "role": lines[i],
                    "company": "",
                    "duration": "",
                    "description": []
                }

                i += 1

                continue

            # Company + Duration

            if current["company"] == "":

                company_line = lines[i]

                duration = re.search(
                    rf"{ExperienceExtractor.MONTH_PATTERN}.*\d{{4}}.*",
                    company_line,
                    re.IGNORECASE,
                )

                if duration:

                    current["duration"] = duration.group()

                    company = company_line.replace(
                        duration.group(),
                        ""
                    ).strip(" ,")

                    current["company"] = company

                else:

                    current["company"] = company_line

                i += 1

                continue

            # New experience starts

            if (
                i + 1 < len(lines)
                and re.search(
                    rf"{ExperienceExtractor.MONTH_PATTERN}.*\d{{4}}",
                    lines[i + 1],
                    re.IGNORECASE,
                )
            ):

                experiences.append(current)

                current = {
                    "role": lines[i],
                    "company": "",
                    "duration": "",
                    "description": []
                }

                i += 1

                continue

            current["description"].append(lines[i])

            i += 1

        if current:

            experiences.append(current)

        return experiences