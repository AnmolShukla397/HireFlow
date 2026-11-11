class ProfileBuilder:

    @staticmethod
    def build(resume: dict) -> str:

        profile = []

        # Name
        if resume.get("name"):
            profile.append(f"Candidate: {resume['name']}")

        # Skills
        skills = resume.get("skills", [])

        if skills:
            profile.append(
                "Skills: " + ", ".join(skills)
            )

        # Education
        education = resume.get("education", {})

        if education:

            degree = education.get("degree", "")

            specialization = education.get(
                "specialization",
                ""
            )

            college = education.get(
                "college",
                ""
            )

            profile.append(
                f"Education: {degree} in {specialization} from {college}"
            )

        # Experience
        experiences = resume.get(
            "experience",
            []
        )

        for exp in experiences:

            profile.append(
                f"Worked as {exp['role']} at "
                f"{exp['company']} "
                f"({exp['duration']})"
            )

            for line in exp["description"]:

                profile.append(line)

        # Projects
        projects = resume.get(
            "projects",
            []
        )

        for project in projects:

            profile.append(
                f"Project: {project['name']}"
            )

            if project["technologies"]:

                profile.append(
                    "Technologies: "
                    + ", ".join(
                        project["technologies"]
                    )
                )

            profile.extend(
                project["description"]
            )

        # Certifications
        certs = resume.get(
            "certifications",
            []
        )

        if certs:

            profile.append(
                "Certifications: "
                + ", ".join(certs)
            )

        return "\n".join(profile)