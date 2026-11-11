from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:

    _model = None

    @classmethod
    def get_model(cls):
        """
        Load the model only once.
        """
        if cls._model is None:
            cls._model = SentenceTransformer(
                "all-MiniLM-L6-v2"
            )
        return cls._model

    @classmethod
    def generate_embedding(cls, text: str):

        model = cls.get_model()

        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding