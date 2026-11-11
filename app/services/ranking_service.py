from app.embeddings.faiss_index import FAISSIndex

from app.ranking.ranker import CandidateRanker


class RankingService:

    def rank(
        self,
        resumes,
        job,
        top_k=5
    ):

        index = FAISSIndex()

        for resume in resumes:

            index.add_embedding(

                resume["file_name"],

                resume["embedding"]

            )

        semantic = index.search(

            job["embedding"],

            top_k

        )

        return CandidateRanker.rank(

            semantic,

            resumes,

            job

        )