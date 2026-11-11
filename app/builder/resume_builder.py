from app.embeddings.profile_builder import ProfileBuilder


class ResumeBuilder:

    @staticmethod
    def extract_name(text: str) -> str:
        """
        Extract candidate name.
        Assumes the first non-empty line is the candidate's name.
        """

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        if lines:
            return lines[0]

        return ""

    @staticmethod
    def build(resume: dict, extracted: dict) -> dict:
        """
        Build the final structured resume JSON.
        """

        resume_json = {

            "name": ResumeBuilder.extract_name(
                resume["clean_text"]
            ),

            "file_name": resume["file_name"],

            "file_type": resume["file_type"],

            "email": extracted.get("email"),

            "phone": extracted.get("phone"),

            "linkedin": extracted.get("linkedin"),

            "github": extracted.get("github"),

            "skills": extracted.get("skills", []),

            "education": extracted.get("education", {}),

            "experience": extracted.get("experience", []),

            "projects": extracted.get("projects", []),

            "certifications": extracted.get("certifications", []),

            "metadata": {

                "num_words": resume["num_words"],

                "num_characters": resume["num_characters"]

            }

        }

        # Build semantic profile text for embeddings
        resume_json["profile_text"] = ProfileBuilder.build(
            resume_json
        )

        return resume_json