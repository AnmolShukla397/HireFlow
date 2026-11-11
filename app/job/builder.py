class JobBuilder:

    @staticmethod
    def build(job):

        profile = []

        profile.append(

            f"Job Title: {job['title']}"

        )

        if job["skills"]:

            profile.append(

                "Required Skills: "

                + ", ".join(job["skills"])

            )

        if job["education"]:

            profile.append(

                "Education: "

                + job["education"]

            )

        if job["experience"]:

            profile.append(

                "Experience: "

                + job["experience"]

            )

        return "\n".join(profile)