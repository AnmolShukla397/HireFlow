import os

from app.services.resume_service import ResumeService
from app.services.job_service import JobService
from app.services.ranking_service import RankingService


# ==========================================
# CONFIGURATION
# ==========================================

RESUME_FOLDER = "data/resumes"
JOB_FILE = "data/jobs/data_scientist_sample_jd.pdf"


# ==========================================
# INITIALIZE SERVICES
# ==========================================

resume_service = ResumeService()
job_service = JobService()
ranking_service = RankingService()

resumes = []

print("\nProcessing Resumes...\n")


# ==========================================
# PROCESS RESUMES
# ==========================================

for filename in os.listdir(RESUME_FOLDER):

    if filename.startswith("."):
        continue

    resume_path = os.path.join(
        RESUME_FOLDER,
        filename
    )

    try:

        resume = resume_service.process_resume(
            resume_path
        )

        resumes.append(resume)

        print(f"✓ {filename}")

    except Exception as e:

        print(f"❌ Error processing {filename}")

        print(e)


print("\n")
print("=" * 80)
print(f"Processed {len(resumes)} resumes")
print("=" * 80)


# ==========================================
# PROCESS JOB DESCRIPTION
# ==========================================

print("\nReading Job Description...\n")

job = job_service.process_job(JOB_FILE)

print("=" * 80)
print("JOB PROFILE")
print("=" * 80)

print(job["profile"])


# ==========================================
# RANK CANDIDATES
# ==========================================

results = ranking_service.rank(

    resumes,

    job,

    top_k=5

)


# ==========================================
# DISPLAY RESULTS
# ==========================================

print("\n")
print("=" * 100)
print("FINAL RANKING")
print("=" * 100)

for i, r in enumerate(results, start=1):

    print(f"\n{i}. {r['candidate']}")

    print(f"Resume          : {r['resume']}")

    print(f"Semantic Score  : {r['semantic']:.2f}")

    print(f"Skill Score     : {r['skill']:.2f}")

    print(f"Experience      : {r['experience']:.2f}")

    print(f"Education       : {r['education']:.2f}")

    print(f"Final Score     : {r['final_score']:.2f}")

    print("\nMatched Skills")

    print("-" * 30)

    if r["matched_skills"]:

        for skill in r["matched_skills"]:

            print(f"✓ {skill}")

    else:

        print("None")

    print("\nMissing Skills")

    print("-" * 30)

    if r["missing_skills"]:

        for skill in r["missing_skills"]:

            print(f"✗ {skill}")

    else:

        print("None")

    print("\n" + "=" * 100)