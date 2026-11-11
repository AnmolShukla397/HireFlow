import numpy as np


class Similarity:

    @staticmethod
    def cosine_similarity(a, b):

        a = np.asarray(a)

        b = np.asarray(b)

        return float(np.dot(a, b))