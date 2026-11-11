from app.parser.job_parser import JobParser

from app.job.extractor import JobExtractor

from app.job.builder import JobBuilder

from app.embeddings.job_embedder import JobEmbedder


class JobService:

    def __init__(self):

        self.extractor = JobExtractor()

    def process_job(self, job_path):

        text = JobParser.parse(job_path)

        job = self.extractor.extract(text)

        profile = JobBuilder.build(job)

        embedding = JobEmbedder.embed(profile)

        job["profile"] = profile

        job["embedding"] = embedding

        return job