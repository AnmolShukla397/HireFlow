import json
import os
import numpy as np

from app.parser.parser import ResumeParser
from app.extractor.extractor import ResumeExtractor
from app.builder.resume_builder import ResumeBuilder
from app.embeddings.embedding_generator import EmbeddingGenerator


class ResumeService:

    def __init__(self):

        self.extractor = ResumeExtractor()

    def process_resume(self, resume_path):

        resume = ResumeParser.parse(resume_path)

        extracted = self.extractor.extract(resume)

        structured_resume = ResumeBuilder.build(
            resume,
            extracted
        )

        embedding = EmbeddingGenerator.generate_embedding(
            structured_resume["profile_text"]
        )

        structured_resume["embedding"] = embedding
        structured_resume["file_name"] = os.path.basename(resume_path)
        return structured_resume