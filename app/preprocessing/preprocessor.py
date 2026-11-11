import re
import unicodedata


class TextPreprocessor:

    @staticmethod
    def clean_text(text: str) -> str:

        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)

        text = text.replace("\t", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize common bullets
        bullets = ["•", "▪", "◦", "●", "■", "►"]
        for bullet in bullets:
            text = text.replace(bullet, "- ")

        # Remove non-printable characters
        text = "".join(
            ch for ch in text
            if ch.isprintable() or ch == "\n"
        )

        # Collapse spaces
        text = re.sub(r"[ ]{2,}", " ", text)

        # Collapse blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()