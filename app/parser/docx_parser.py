from docx import Document


class DOCXParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text from a DOCX file.
        """
        document = Document(file_path)

        paragraphs = [
            para.text.strip()
            for para in document.paragraphs
            if para.text.strip()
        ]

        return "\n".join(paragraphs)