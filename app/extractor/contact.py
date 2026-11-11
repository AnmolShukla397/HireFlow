import re


class ContactExtractor:

    @staticmethod
    def extract_email(text: str):
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(pattern, text)

        return match.group() if match else None

    @staticmethod
    def extract_phone(text: str):
        pattern = r"(?:\+91[- ]?)?[6-9]\d{9}"
        match = re.search(pattern, text)

        return match.group() if match else None

    @staticmethod
    def extract_linkedin(text: str):
        pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s]+"
        match = re.search(pattern, text)

        return match.group() if match else None

    @staticmethod
    def extract_github(text: str):
        pattern = r"(?:https?://)?(?:www\.)?github\.com/[^\s]+"
        match = re.search(pattern, text)

        return match.group() if match else None