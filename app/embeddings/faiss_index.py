import faiss
import numpy as np


class FAISSIndex:

    def __init__(self, dimension=384):

        self.dimension = dimension

        # Cosine similarity (vectors are normalized)
        self.index = faiss.IndexFlatIP(dimension)

        self.resume_ids = []

    def add_embedding(self, resume_id, embedding):

        embedding = np.asarray(
            embedding,
            dtype="float32"
        ).reshape(1, -1)

        self.index.add(embedding)

        self.resume_ids.append(resume_id)

    def search(self, query_embedding, top_k=5):

        query_embedding = np.asarray(
            query_embedding,
            dtype="float32"
        ).reshape(1, -1)

        scores, indices = self.index.search(
            query_embedding,
            top_k
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx == -1:
                continue

            results.append({

                "resume": self.resume_ids[idx],

                "score": float(score)

            })

        return results