import os

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser


class JobParser:

    @staticmethod
    def parse(file_path: str):

        extension = os.path.splitext(file_path)[1].lower()

        if extension == ".pdf":
            return PDFParser.extract_text(file_path)

        elif extension == ".docx":
            return DOCXParser.extract_text(file_path)

        elif extension == ".txt":

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as f:

                return f.read()

        else:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )