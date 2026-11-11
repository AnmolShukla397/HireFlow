from .embedding_generator import EmbeddingGenerator


class JobEmbedder:

    @staticmethod
    def embed(job_description: str):

        return EmbeddingGenerator.generate_embedding(
            job_description
        )