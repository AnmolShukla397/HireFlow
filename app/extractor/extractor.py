from .contact import ContactExtractor
from .skills import SkillExtractor
from .section import SectionExtractor

from .education import EducationExtractor
from .experience import ExperienceExtractor
from .projects import ProjectExtractor
from .certifications import CertificationExtractor


class ResumeExtractor:

    def __init__(self):

        self.skill_extractor = SkillExtractor()

    def extract(self, resume):

        text = resume["clean_text"]

        education_section = SectionExtractor.extract(
            text,
            "education"
        )

        experience_section = SectionExtractor.extract(
            text,
            "experience"
        )

        project_section = SectionExtractor.extract(
            text,
            "projects"
        )

        certification_section = SectionExtractor.extract(
            text,
            "certifications"
        )

        return {

            "file_name": resume["file_name"],

            "email": ContactExtractor.extract_email(text),

            "phone": ContactExtractor.extract_phone(text),

            "linkedin": ContactExtractor.extract_linkedin(text),

            "github": ContactExtractor.extract_github(text),

            "skills": self.skill_extractor.extract(text),

            "education": EducationExtractor.extract(
                education_section
            ),

            "experience": ExperienceExtractor.extract(
                experience_section
            ),

            "projects": ProjectExtractor.extract(
                project_section
            ),

            "certifications": CertificationExtractor.extract(
                certification_section
            )
        }