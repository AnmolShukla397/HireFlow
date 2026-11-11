import re


class SectionExtractor:

    HEADERS = [
        "education",
        "experience",
        "work experience",
        "internship",
        "internships",
        "projects",
        "technical skills",
        "skills",
        "certifications",
        "achievements",
        "publications",
        "languages",
        "interests"
    ]

    @staticmethod
    def extract(text: str, section_name: str):

        headers = [
            h for h in SectionExtractor.HEADERS
            if h.lower() != section_name.lower()
        ]

        pattern = rf"{section_name}(.*?)(?=\n(?:{'|'.join(headers)})|\Z)"

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            return match.group(1).strip()

        return ""