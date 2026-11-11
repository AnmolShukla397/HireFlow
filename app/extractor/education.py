import re


class EducationExtractor:

    @staticmethod
    def extract(text: str):

        if not text:
            return {}

        education = {
            "college": "",
            "location": "",
            "degree": "",
            "specialization": "",
            "duration": "",
            "cgpa": ""
        }

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        # ---------- First line ----------
        if lines:

            first = lines[0]

            duration_match = re.search(
                r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\s*[-–]\s*(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}",
                first,
                re.IGNORECASE,
            )

            if duration_match:
                education["duration"] = duration_match.group()

                first = first.replace(duration_match.group(), "").strip()

            parts = [p.strip() for p in first.split(",")]

            if parts:
                education["college"] = parts[0]

            if len(parts) > 1:
                education["location"] = ", ".join(parts[1:])

        # ---------- Degree ----------
        degree_pattern = re.search(
            r"(Bachelor of Technology|Bachelor of Engineering|B\.?Tech|B\.?E\.?|Master of Technology|M\.?Tech|MBA|Bachelor of Science|Master of Science)(.*)",
            text,
            re.IGNORECASE,
        )

        if degree_pattern:

            education["degree"] = degree_pattern.group(1).strip()

            specialization = degree_pattern.group(2)

            specialization = re.sub(
                r"CGPA.*",
                "",
                specialization,
                flags=re.IGNORECASE,
            ).strip(" ,")

            education["specialization"] = specialization

        # ---------- CGPA ----------
        cgpa = re.search(
            r"(CGPA|GPA)\s*[:\-]?\s*([\d.]+)",
            text,
            re.IGNORECASE,
        )

        if cgpa:
            education["cgpa"] = cgpa.group(2)

        return education