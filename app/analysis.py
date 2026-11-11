"""Explainable job-to-resume analysis and editable, evidence-safe suggestions."""

from __future__ import annotations

import io
import math
import os
import re
import time
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from app.ranking.scorer import ResumeScorer


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_FILES = ("pdf", "docx", "txt", "md")
SCORING_VERSION = "2.0"
MAX_PDF_PAGES = 25
MAX_OCR_PAGES = 8
MAX_DOCX_UNCOMPRESSED = 40 * 1024 * 1024
STOP = set("a an and are as at be by can for from has in into is it of on or our the their this to with you your we will that who".split())
SECTION_NAMES = ("summary", "profile", "experience", "education", "projects", "skills", "certifications")
SECTION_ALIASES = {
    "professional summary": "Summary", "career summary": "Summary", "personal profile": "Profile",
    "work experience": "Experience", "professional experience": "Experience", "employment history": "Experience",
    "relevant experience": "Experience", "internships": "Experience",
    "project experience": "Projects", "personal projects": "Projects", "academic projects": "Projects",
    "technical skills": "Skills", "core skills": "Skills", "key skills": "Skills", "skills and tools": "Skills",
    "academic background": "Education", "educational background": "Education",
    "licenses and certifications": "Certifications", "certificates": "Certifications",
}
ACTION_WORDS = set("built created delivered designed developed improved implemented led managed analyzed automated collaborated launched optimized reduced increased researched supported tested wrote used applied deployed configured containerized engineered coordinated contributed".split())
SKILL_ALIASES = {
    "machine learning": ("ML",),
    "artificial intelligence": ("AI",),
    "aws": ("Amazon Web Services",),
    "gcp": ("Google Cloud Platform", "Google Cloud"),
    "postgresql": ("Postgres",),
    "power bi": ("PowerBI",),
    "javascript": ("JS",),
}


def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def skill_in_text(skill: str, text: str) -> bool:
    return _contains(text, skill)


def extract_document(filename: str, data: bytes) -> str:
    """Read document text, OCRing image-only PDF pages with bundled English data."""
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FILES:
        raise ValueError("Use a PDF, DOCX, TXT, or Markdown file.")
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Choose a non-empty file smaller than 10 MB.")
    if suffix == "pdf" and not data.lstrip().startswith(b"%PDF-"):
        raise ValueError("This file is not a valid PDF.")
    if suffix == "docx" and not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError("This file is not a valid DOCX document.")
    try:
        if suffix == "pdf":
            import fitz
            with fitz.open(stream=data, filetype="pdf") as document:
                if document.page_count > MAX_PDF_PAGES:
                    raise ValueError(f"PDFs may contain up to {MAX_PDF_PAGES} pages.")
                chunks = []
                ocr_pages = 0
                tessdata = ROOT / "data" / "tessdata"
                started = time.monotonic()
                for page in document:
                    if time.monotonic() - started > 45:
                        raise ValueError("Document reading took too long. Try a smaller PDF.")
                    content = page.get_text("text")
                    if len(content.split()) < 8 and page.get_images():
                        ocr_pages += 1
                        if ocr_pages > MAX_OCR_PAGES:
                            raise ValueError(f"A PDF may contain up to {MAX_OCR_PAGES} scanned pages for OCR.")
                        if not (tessdata / "eng.traineddata").is_file():
                            raise ValueError("English OCR data is missing. Restore data/tessdata/eng.traineddata.")
                        try:
                            textpage = page.get_textpage_ocr(language="eng", dpi=150, full=True, tessdata=str(tessdata))
                            content = page.get_text("text", textpage=textpage)
                        except Exception as exc:
                            raise ValueError("This scanned PDF could not be read with OCR. Try a clearer scan or a text PDF.") from exc
                    chunks.append(content)
                text = "\n".join(chunks)
        elif suffix == "docx":
            from docx import Document
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 500 or sum(item.file_size for item in entries) > MAX_DOCX_UNCOMPRESSED:
                    raise ValueError("This DOCX expands beyond the supported document size.")
            document = Document(io.BytesIO(data))
            chunks = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    chunks.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(chunks)
        else:
            text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The text file must use UTF-8 encoding.") from exc
    except ValueError:
        raise
    except ModuleNotFoundError as exc:
        raise ValueError("Document support is not installed. Run python -m pip install -r requirements-app.txt and try again.") from exc
    except Exception as exc:
        raise ValueError("This document could not be read. Check that the file is valid and try again.") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text.split()) < 8:
        raise ValueError("This file has too little readable text. Try a clearer scan or a different document.")
    return text


def _skills(text: str) -> List[str]:
    vocabulary = (ROOT / "data" / "skills.txt").read_text(encoding="utf-8").splitlines()
    found = []
    for item in vocabulary:
        skill = item.strip()
        if skill and re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", text, re.I):
            found.append(skill)
    return sorted(set(found), key=str.casefold)


def _tokens(text: str) -> Counter:
    words = re.findall(r"[a-z][a-z0-9+#.-]{1,}", text.lower())
    return Counter(word for word in words if word not in STOP)


def _scoring_text(resume_text: str) -> str:
    """Exclude contact identifiers from job similarity while retaining job evidence."""
    lines = resume_text.splitlines()
    if len(lines) > 1 and len(lines[0].split()) <= 5 and ("@" in lines[1] or _contact(lines[1])["phone"]):
        lines = lines[1:]
    text = "\n".join(lines)
    for identifier in _contact(text).values():
        if identifier:
            text = text.replace(identifier, " ")
    return text


def _semantic_score(job_text: str, resume_text: str) -> tuple[float, str]:
    """Use an explicit, stable backend; never change methods silently."""
    backend = os.environ.get("HIREFLOW_SIMILARITY_BACKEND", "keyword").strip().lower()
    scoring_text = _scoring_text(resume_text)
    if backend == "local":
        model = _local_model()
        if model is None:
            raise ValueError("The local similarity model is unavailable. Install and cache all-MiniLM-L6-v2, or use HIREFLOW_SIMILARITY_BACKEND=keyword.")
        vectors = model.encode([job_text, scoring_text], normalize_embeddings=True)
        return max(0.0, min(100.0, float(vectors[0] @ vectors[1]) * 100)), "local MiniLM model"
    if backend != "keyword":
        raise ValueError("HIREFLOW_SIMILARITY_BACKEND must be keyword or local.")
    job, resume = _tokens(job_text), _tokens(scoring_text)
    numerator = sum(count * resume.get(word, 0) for word, count in job.items())
    denominator = math.sqrt(sum(count * count for count in job.values())) * math.sqrt(sum(count * count for count in resume.values()))
    return (round(100 * numerator / denominator, 1) if denominator else 0.0), "keyword cosine"


@lru_cache(maxsize=1)
def _local_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception:
        return None


def _degree_level(text: str) -> int:
    if re.search(r"\b(master|m\.tech|m\.e\b|mba|msc|m\.sc)\b", text, re.I):
        return 2
    if re.search(r"\b(bachelor|b\.tech|b\.e\b|bsc|b\.sc)\b", text, re.I):
        return 1
    return 0


def _years(text: str) -> float:
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", text, re.I)
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    written = [words[value.lower()] for value in re.findall(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*\+?\s*years?\b", text, re.I)]
    return max([float(value) for value in numbers] + written, default=0.0)


def _contact(text: str) -> Dict[str, str]:
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = next((match.group(0) for match in re.finditer(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)", text) if 10 <= len(re.sub(r"\D", "", match.group(0))) <= 15), "")
    linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+", text, re.I)
    return {
        "email": email.group(0) if email else "",
        "phone": phone,
        "linkedin": linkedin.group(0) if linkedin else "",
    }


def _sections(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current = "Header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = section_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return sections


def section_heading(line: str) -> str | None:
    """Recognize conventional resume headings while preserving their text."""
    normalized = re.sub(r"^\s*#{1,6}\s*", "", line).strip().rstrip(":").strip().casefold()
    if normalized in SECTION_NAMES:
        return normalized.title()
    return SECTION_ALIASES.get(normalized)


def _skill_evidence(text: str, skills: Sequence[str]) -> Dict[str, List[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        skill: [line[:220] for line in lines if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", line, re.I)][:2]
        for skill in skills
    }


def _line_suggestions(job_text: str, resume_text: str, job_skills: Sequence[str], matched: Sequence[str], missing: Sequence[str]) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Propose only factual, material edits that reflect the supplied job."""
    suggestions: List[Dict[str, Any]] = []
    reviews: List[Dict[str, str]] = []
    current_section = "header"
    job_terms = set(_tokens(job_text)) - {"experience", "years", "year", "degree", "required", "candidate", "role"}
    for index, original in enumerate(resume_text.splitlines()):
        line = original.strip()
        if not line:
            continue
        heading = section_heading(line)
        if heading:
            current_section = heading.lower()
            reviews.append({"line": str(index + 1), "text": line[:220], "assessment": "Keep heading", "reason": "Standard section heading."})
            continue
        if _contact(line)["email"] or _contact(line)["phone"] or len(line.split()) < 5:
            reviews.append({"line": str(index + 1), "text": line[:220], "assessment": "Keep", "reason": "No evidence-backed wording change identified."})
            continue
        proposed = line
        reasons: List[str] = []
        category = "Clarity"
        for skill in job_skills:
            for alias in SKILL_ALIASES.get(skill.casefold(), ()):
                if _contains(proposed, alias) and not _contains(proposed, skill):
                    proposed = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", "{} ({})".format(skill, alias), proposed, count=1, flags=re.I)
                    reasons.append("The job description names {}. Your resume uses {}; spelling out the exact term helps keyword matching.".format(skill, alias))
                    category = "Job keyword"
                    break
        if current_section in ("summary", "profile") and not re.search(r"\b(core|key|relevant) skills\b", proposed, re.I):
            focused = [skill for skill in matched if not _contains(proposed, skill)][:4]
            if focused:
                proposed = proposed.rstrip(" .;") + ". Core skills include " + ", ".join(focused) + "."
                reasons.append("These exact job skills are already listed in your resume; placing them in the summary makes the match easier to find.")
                category = "Targeted summary"
        line_terms = set(_tokens(line))
        if current_section in ("experience", "projects", "header"):
            prefix_match = re.match(r"^([-•]\s*)", proposed)
            prefix = prefix_match.group(1) if prefix_match else ""
            body = proposed[len(prefix):]
            for pattern, replacement in (
                (r"^i (?:have |had )?made\b", "Created"),
                (r"^i (?:have |had )?built\b", "Built"),
                (r"^i (?:have |had )?used\b", "Used"),
                (r"^i (?:have |had )?worked on\b", "Contributed to"),
                (r"^i (?:was |have been )?responsible for building\b", "Built"),
                (r"^i (?:was |have been )?responsible for\b", "Contributed to"),
                (r"^i (?:have |had )?helped with\b", "Supported"),
                (r"^responsible for building\b", "Built"),
                (r"^responsible for\b", "Contributed to"),
                (r"^worked on\b", "Contributed to"),
                (r"^helped with\b", "Supported"),
                (r"^involved in\b", "Contributed to"),
            ):
                if re.search(pattern, body, re.I):
                    proposed = prefix + re.sub(pattern, replacement, body, count=1, flags=re.I)
                    reasons.append("This line supports the job description. Lead with the work you completed so it is easier to scan." if line_terms.intersection(job_terms) else "Lead with your actual contribution instead of casual or indirect wording.")
                    category = "Professional wording"
                    break
        if proposed != line and len(suggestions) < 14:
            suggestions.append({"id": "replace-" + str(index), "kind": "replace", "category": category, "line_index": index, "before": original, "after": proposed, "reason": " ".join(reasons)})
        reviews.append({"line": str(index + 1), "text": line[:220], "assessment": "Suggested change" if proposed != line else "Keep", "reason": " ".join(reasons) if reasons else "No evidence-backed wording change identified."})
    for skill in missing[:5]:
        suggestions.append({
            "id": "add-" + re.sub(r"\W+", "-", skill.lower()), "kind": "add", "category": "Evidence gap", "line_index": -1,
            "before": "", "after": "", "reason": "The job description asks for {} but it was not found in your resume. Add a specific example only if you have actually used it.".format(skill),
            "skill": skill,
        })
    return suggestions, reviews


def draft_skill_bullet(skill: str, evidence: str) -> str:
    """Turn a truthful first-person example into a concise resume bullet."""
    line = re.sub(r"\s+", " ", evidence).strip().lstrip("-• ").strip()
    if len(line.split()) < 6:
        raise ValueError("Describe a specific task or project in at least six words.")
    if re.match(r"^(?:I (?:just )?know|I am familiar with|familiar with)\b", line, re.I):
        raise ValueError("Describe how you used the skill in a real task or project.")
    if not _contains(line, skill):
        alias = next((item for item in SKILL_ALIASES.get(skill.casefold(), ()) if _contains(line, item)), None)
        if alias is None:
            raise ValueError("Include {} and describe how you used it.".format(skill))
        line = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", "{} ({})".format(skill, alias), line, count=1, flags=re.I)
    context = re.match(r"^(?:In|During) my (internship|project|role|job),?\s+(.+)$", line, re.I)
    if context:
        line = context.group(2)
        suffix = " during my " + context.group(1).lower()
    else:
        suffix = ""
    verbose = re.match(r"^I (?:have |had )?experience (?:using|with) " + re.escape(skill) + r" (?:from|in) (?:my|a) (internship|project|role|job) where I (.+)$", line, re.I)
    if verbose:
        line = "I " + verbose.group(2)
        suffix = suffix or " during my " + verbose.group(1).lower()
    project = re.match(r"^I (?:have )?worked on a (project|internship|role|job) where I (.+)$", line, re.I)
    if project:
        line = "I " + project.group(2)
        suffix = suffix or " during my " + project.group(1).lower()
    action_verbs = {
        "build": "Built", "building": "Built", "deploy": "Deployed", "deploying": "Deployed",
        "containerize": "Containerized", "containerizing": "Containerized", "test": "Tested", "testing": "Tested",
        "analyze": "Analyzed", "analyzing": "Analyzed", "design": "Designed", "designing": "Designed",
        "automate": "Automated", "automating": "Automated", "develop": "Developed", "developing": "Developed",
        "create": "Created", "creating": "Created", "implement": "Implemented", "implementing": "Implemented",
        "manage": "Managed", "managing": "Managed", "configure": "Configured", "configuring": "Configured",
        "improve": "Improved", "improving": "Improved", "optimize": "Optimized", "optimizing": "Optimized",
    }
    used = re.match(r"^I (?:have |had )?used\s+" + re.escape(skill) + r"(?:\s+\([^)]{1,32}\))?\s+(?:to|for)\s+(\w+)\s+(.+)$", line, re.I)
    if used and used.group(1).lower() in action_verbs:
        line = "{} {} using {}".format(action_verbs[used.group(1).lower()], used.group(2).rstrip(" ."), skill)
    else:
        line = re.sub(r"^I (?:have |had )?used\b", "Used", line, flags=re.I)
        line = re.sub(r"^I (?:have |had )?worked on\b", "Contributed to", line, flags=re.I)
        line = re.sub(r"^I (?:was )?responsible for building\b", "Built", line, flags=re.I)
        line = re.sub(r"^I (?:was )?responsible for\b", "Contributed to", line, flags=re.I)
        line = re.sub(r"^I (built|developed|designed|deployed|created|analyzed|managed|led|implemented|tested|automated|configured|improved|optimized|containerized)\b", lambda match: match.group(1).capitalize(), line, flags=re.I)
        line = re.sub(r"^I have experience (?:using|with)\b", "Used", line, flags=re.I)
        line = re.sub(r"^My experience includes\b", "Worked with", line, flags=re.I)
    line = re.sub(r"\bfor (building|deploying|containerizing|testing|analyzing|designing|automating)\b", lambda match: "to " + {"building": "build", "deploying": "deploy", "containerizing": "containerize", "testing": "test", "analyzing": "analyze", "designing": "design", "automating": "automate"}[match.group(1).lower()], line, flags=re.I)
    line = line.rstrip(" .") + suffix
    line = line[0].upper() + line[1:]
    return "- " + line.rstrip(" .") + "."


ATS_WEIGHTS = {
    "Skill overlap": 0.35,
    "Contact fields": 0.15,
    "Section headings": 0.15,
    "Selectable text": 0.10,
    "Job skill context": 0.15,
    "Action-led evidence": 0.10,
}


def _ats_readiness(resume_text: str, job_skills: Sequence[str], resume_skills: Sequence[str], contact: Mapping[str, str], sections: Mapping[str, Sequence[str]]) -> tuple[float, Dict[str, float]]:
    matched = [skill for skill in job_skills if skill.casefold() in {item.casefold() for item in resume_skills}]
    skill_score = ResumeScorer.skill_score(resume_skills, job_skills) if job_skills else 50.0
    context_lines = [line for section in ("Summary", "Profile", "Experience", "Projects") for line in sections.get(section, ())]
    contextual = sum(any(_contains(line, skill) for line in context_lines) for skill in matched)
    context_score = round(100 * contextual / len(job_skills), 1) if job_skills else 50.0
    evidence_lines = [line.strip().lstrip("-• ") for section in ("Experience", "Projects") for line in sections.get(section, ()) if len(line.split()) >= 5]
    action_score = round(100 * sum(line.split()[0].lower().strip(".,:;") in ACTION_WORDS for line in evidence_lines) / len(evidence_lines), 1) if evidence_lines else 50.0
    factors = {
        "Skill overlap": skill_score,
        "Contact fields": round(100 * sum(bool(value) for value in contact.values()) / 3, 1),
        "Section headings": min(100.0, len([name for name in sections if name != "Header"]) * 25.0),
        "Selectable text": round(min(100.0, len(resume_text.split()) / 2.5), 1),
        "Job skill context": context_score,
        "Action-led evidence": action_score,
    }
    return round(sum(factors[name] * weight for name, weight in ATS_WEIGHTS.items()), 1), factors


def estimate_ats(job_text: str, resume_text: str) -> float:
    """Fast ATS-readiness estimate for a proposed applicant edit."""
    job_skills, resume_skills = _skills(job_text), _skills(resume_text)
    score, _ = _ats_readiness(resume_text, job_skills, resume_skills, _contact(resume_text), _sections(resume_text))
    return score


def analyse(job_text: str, resume_text: str, filename: str = "Resume") -> Dict[str, Any]:
    job_text, resume_text = job_text.strip(), resume_text.strip()
    if len(job_text.split()) < 8 or len(resume_text.split()) < 8:
        raise ValueError("Provide a job description and resume with at least eight words each.")
    job_skills, resume_skills = _skills(job_text), _skills(resume_text)
    matched = [skill for skill in job_skills if skill.casefold() in {item.casefold() for item in resume_skills}]
    missing = [skill for skill in job_skills if skill.casefold() not in {item.casefold() for item in resume_skills}]
    semantic, method = _semantic_score(job_text, resume_text)
    skill_score = ResumeScorer.skill_score(resume_skills, job_skills) if job_skills else 50.0
    required_years, resume_years = _years(job_text), _years(resume_text)
    experience = 100.0 if not required_years else min(100.0, round(resume_years / required_years * 100, 1)) if resume_years else 50.0 if re.search(r"\bexperience\b", resume_text, re.I) else 20.0
    required_degree, resume_degree = _degree_level(job_text), _degree_level(resume_text)
    education = 100.0 if not required_degree or resume_degree >= required_degree else 30.0
    overall = ResumeScorer.final_score(semantic, skill_score, experience, education)
    contact = _contact(resume_text)
    sections = _sections(resume_text)
    headings = [name.lower() for name in sections if name != "Header"]
    ats, ats_factors = _ats_readiness(resume_text, job_skills, resume_skills, contact, sections)
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    name = lines[0][:100] if lines else filename
    if "@" in name or len(name.split()) > 6:
        name = Path(filename).stem
    summary = "{} shows {} recognized skill{}{}".format(
        name, len(resume_skills), "" if len(resume_skills) == 1 else "s",
        " and explicit experience of up to {} years".format(resume_years) if resume_years else "",
    ) + ". " + ("Strongest overlap: {}.".format(", ".join(matched[:5])) if matched else "No listed job skills were found verbatim in the resume.")
    suggestions, reviews = _line_suggestions(job_text, resume_text, job_skills, matched, missing)
    return {
        "candidate": name, "filename": filename, "summary": summary, "contact": contact,
        "resume_skills": resume_skills, "job_skills": job_skills, "matched_skills": matched, "missing_skills": missing,
        "semantic": round(semantic, 1), "semantic_method": method, "skill": skill_score,
        "scoring_version": SCORING_VERSION,
        "experience": experience, "education": education, "overall": overall, "ats": ats,
        "required_years": required_years, "resume_years": resume_years, "required_degree": required_degree,
        "resume_degree": resume_degree, "headings": headings, "word_count": len(resume_text.split()),
        "sections": sections, "skill_evidence": _skill_evidence(resume_text, matched),
        "ats_factors": ats_factors, "ats_weights": ATS_WEIGHTS,
        "suggestions": suggestions, "line_reviews": reviews, "resume_text": resume_text,
    }


def _insert_into_section(lines: List[str], section: str, text: str) -> None:
    headings = [(index, section_heading(line)) for index, line in enumerate(lines)]
    matches = [index for index, heading in headings if heading == section]
    if matches:
        start = matches[0] + 1
        end = next((index for index, heading in headings if index >= start and heading), len(lines))
        content = [(index, len(set(_tokens(text)).intersection(_tokens(lines[index])))) for index in range(start, end) if lines[index].strip()]
        best = max(content, key=lambda item: item[1], default=None)
        position = best[0] + 1 if best and best[1] >= 2 else end
        while position > start and not lines[position - 1].strip():
            position -= 1
        lines.insert(position, text)
        return
    if section == "Experience":
        before = {"Projects", "Education", "Certifications"}
    else:
        before = {"Education", "Certifications"}
    position = next((index for index, heading in headings if heading in before), len(lines))
    while position > 0 and not lines[position - 1].strip():
        position -= 1
    prefix = [""] if position and lines[position - 1].strip() else []
    lines[position:position] = prefix + [section.upper(), text, ""]


def apply_decisions(original: str, suggestions: Sequence[Mapping[str, Any]], decisions: Mapping[str, str], additions: Mapping[str, str], placements: Mapping[str, str] | None = None) -> str:
    lines = original.splitlines()
    insertions = []
    placements = placements or {}
    for suggestion in suggestions:
        if decisions.get(str(suggestion["id"])) != "accepted":
            continue
        if suggestion["kind"] == "replace":
            index = int(suggestion["line_index"])
            if 0 <= index < len(lines):
                lines[index] = additions.get(str(suggestion["id"]), "").strip() or str(suggestion["after"])
        else:
            text = additions.get(str(suggestion["id"]), "").strip()
            if text:
                section = placements.get(str(suggestion["id"]), str(suggestion.get("placement", "Experience")))
                insertions.append((section if section in ("Experience", "Projects") else "Experience", text))
    for section, text in insertions:
        _insert_into_section(lines, section, text)
    return "\n".join(lines).strip() + "\n"


def _format_options(options: Mapping[str, float] | None) -> Dict[str, float]:
    defaults = {"body_size": 10.5, "heading_size": 10.5, "line_spacing": 1.15, "margin": 0.78}
    bounds = {"body_size": (9, 12), "heading_size": (10, 15), "line_spacing": (1.0, 1.5), "margin": (0.55, 1.1)}
    for key, value in (options or {}).items():
        if key in defaults:
            number = float(value)
            low, high = bounds[key]
            defaults[key] = max(low, min(high, number))
    return defaults


def export_docx(text: str, template: str = "Contemporary", options: Mapping[str, float] | None = None) -> bytes:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    settings = _format_options(options)
    document = Document()
    section = document.sections[0]
    section.top_margin = section.bottom_margin = Inches(settings["margin"])
    section.left_margin = section.right_margin = Inches(settings["margin"])
    normal = document.styles["Normal"]
    normal.font.name = "Aptos" if template == "Contemporary" else "Calibri"
    normal.font.size = Pt(settings["body_size"])
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = settings["line_spacing"]
    ink = RGBColor(24, 44, 48) if template == "Contemporary" else RGBColor(28, 28, 28)
    accent = RGBColor(49, 88, 75) if template == "Contemporary" else ink
    normal.font.color.rgb = ink
    heading_style = document.styles["Heading 1"]
    heading_style.font.name = normal.font.name
    heading_style.font.size = Pt(settings["heading_size"])
    heading_style.font.bold = True
    heading_style.font.color.rgb = accent
    heading_style.paragraph_format.space_before = Pt(12)
    heading_style.paragraph_format.space_after = Pt(5)
    for index, line in enumerate(text.splitlines()):
        value = line.strip()
        if not value:
            continue
        elif index == 0:
            name = document.add_paragraph()
            name.paragraph_format.space_after = Pt(5)
            run = name.add_run(value)
            run.font.name = normal.font.name
            run.font.size = Pt(18 if template == "Contemporary" else 17)
            run.font.bold = True
            run.font.color.rgb = ink
        elif section_heading(value) and len(value) < 60:
            document.add_paragraph(section_heading(value).upper(), style="Heading 1")
        elif value.startswith(("-", "•")):
            document.add_paragraph(value.lstrip("-• "), style="List Bullet")
        else:
            document.add_paragraph(value)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def export_pdf(text: str, template: str = "Contemporary", options: Mapping[str, float] | None = None) -> bytes:
    import fitz
    import textwrap
    settings = _format_options(options)
    document = fitz.open()
    page = document.new_page()
    body_font = ROOT / "static" / "fonts" / "DM-Sans-Variable.ttf"
    title_font = ROOT / "static" / "fonts" / "Manrope-Variable.ttf"
    palette = (0.094, 0.173, 0.188) if template == "Contemporary" else (0.11, 0.11, 0.11)
    accent = (0.192, 0.345, 0.294) if template == "Contemporary" else palette

    def install_fonts(current_page: Any) -> None:
        current_page.insert_font(fontname="HireFlowBody", fontfile=str(body_font))
        current_page.insert_font(fontname="HireFlowTitle", fontfile=str(title_font))

    install_fonts(page)
    left = settings["margin"] * 72
    right = page.rect.width - left
    y = left
    for index, line in enumerate(text.splitlines()):
        value = line.strip()
        if not value:
            y += 5
            continue
        is_name = index == 0
        is_heading = bool(section_heading(value)) and not is_name
        size = 17 if is_name else settings["heading_size"] if is_heading else settings["body_size"]
        font = "HireFlowTitle" if is_name or is_heading else "HireFlowBody"
        color = accent if is_heading else palette
        x = left + (8 if value.startswith(("-", "•")) and not is_name else 0)
        value = ("• " + value.lstrip("-• ")) if value.startswith(("-", "•")) else value
        available = max(200, right - x)
        char_width = size * (0.56 if is_name else 0.51)
        wrapped = textwrap.wrap(value, width=max(20, int(available / char_width)), break_long_words=False, break_on_hyphens=False) or [""]
        if is_heading:
            y += 8
        for part in wrapped:
            if y > page.rect.height - left:
                page = document.new_page()
                install_fonts(page)
                y = left
            page.insert_text((x, y), part, fontsize=size, fontname=font, color=color)
            y += (size + 5) if is_name else size * settings["line_spacing"] + 3
        if is_heading:
            page.draw_line((left, y - 7), (right, y - 7), color=accent, width=.5)
            y += 4
    output = document.tobytes()
    document.close()
    return output
