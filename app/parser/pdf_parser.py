import fitz


class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text from a PDF file.
        """
        text = ""

        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text("text") + "\n"

        return text.strip()