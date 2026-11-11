import os

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from app.preprocessing.preprocessor import TextPreprocessor


class ResumeParser:
    @staticmethod
    def parse(file_path: str) -> dict:
        """
        Parse a resume (PDF or DOCX), extract text,
        preprocess it, and return structured metadata.
        """

        extension = os.path.splitext(file_path)[1].lower()

        if extension == ".pdf":
            raw_text = PDFParser.extract_text(file_path)

        elif extension == ".docx":
            raw_text = DOCXParser.extract_text(file_path)

        else:
            raise ValueError(f"Unsupported file type: {extension}")

        clean_text = TextPreprocessor.clean_text(raw_text)

        return {
            "file_name": os.path.basename(file_path),
            "file_type": extension.replace(".", ""),
            "text": raw_text,
            "clean_text": clean_text,
            "num_words": len(clean_text.split()),
            "num_characters": len(clean_text),
        }