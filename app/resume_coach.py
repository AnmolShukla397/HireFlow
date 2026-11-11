"""Applicant-only resume diagnostics and factual sentence rewriting."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from app import analysis


PAST_VERBS = {
    "analyze": "Analyzed", "analyzed": "Analyzed", "analysed": "Analyzed", "analyzing": "Analyzed",
    "automate": "Automated", "automated": "Automated", "automating": "Automated",
    "build": "Built", "built": "Built", "building": "Built", "make": "Created", "made": "Created", "making": "Created",
    "clean": "Cleaned", "cleaned": "Cleaned", "cleaning": "Cleaned",
    "create": "Created", "created": "Created", "creating": "Created",
    "design": "Designed", "designed": "Designed", "designing": "Designed",
    "develop": "Developed", "developed": "Developed", "developing": "Developed",
    "deploy": "Deployed", "deployed": "Deployed", "deploying": "Deployed",
    "improve": "Improved", "improved": "Improved", "improving": "Improved",
    "implement": "Implemented", "implemented": "Implemented", "implementing": "Implemented",
    "manage": "Managed", "managed": "Managed", "managing": "Managed",
    "optimize": "Optimized", "optimized": "Optimized", "optimizing": "Optimized",
    "test": "Tested", "tested": "Tested", "testing": "Tested",
    "train": "Trained", "trained": "Trained", "training": "Trained",
    "write": "Wrote", "wrote": "Wrote", "writing": "Wrote",
    "containerize": "Containerized", "containerized": "Containerized", "containerizing": "Containerized",
}
VAGUE = re.compile(r"\b(?:stuff|things|some work|many tasks|a lot of things|etc\.?|something|anything)\b", re.I)
PERSONAL = re.compile(r"\b(?:date of birth|dob|marital status|religion|gender|father'?s name|mother'?s name)\b", re.I)
METRIC = re.compile(r"(?:\b\d+(?:[.,]\d+)?\s*(?:%|percent|users?|customers?|records?|hours?|days?|weeks?|months?|years?|transactions?|requests?|projects?|teams?|people)\b|\$\s*\d+)", re.I)
DATE = re.compile(r"\b(?:20\d{2}|19\d{2}|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b", re.I)


def _check(area: str, status: str, title: str, detail: str, action: str) -> dict[str, str]:
    return {"area": area, "status": status, "title": title, "detail": detail, "action": action}


def _layout_checks(filename: str, data: bytes | None) -> list[dict[str, str]]:
    if not data:
        return [_check("Format", "review", "Original layout not inspected", "Pasted text shows content and section structure, but not fonts, columns, graphics or tables.", "Upload the original PDF or DOCX for a layout check.")]
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        import fitz
        with fitz.open(stream=data, filetype="pdf") as document:
            pages = len(document)
            image_blocks = 0
            body_sizes: list[float] = []
            two_columns = False
            for page in document:
                blocks = page.get_text("dict")["blocks"]
                image_blocks += sum(block.get("type") == 1 for block in blocks)
                text_lines = []
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", ()):
                        text = " ".join(span["text"] for span in line.get("spans", ()))
                        if len(text.split()) >= 5:
                            text_lines.append(line["bbox"])
                        body_sizes.extend(span["size"] for span in line.get("spans", ()) if span.get("text", "").strip())
                left = [box for box in text_lines if box[2] < page.rect.width * .58]
                right = [box for box in text_lines if box[0] > page.rect.width * .42]
                two_columns |= len(left) >= 2 and len(right) >= 2 and any(min(a[3], b[3]) - max(a[1], b[1]) > 8 for a in left for b in right)
        checks = []
        checks.append(_check("Format", "review" if two_columns else "good", "Column reading order" if two_columns else "Single-column reading pattern", "Side-by-side text blocks were detected; some systems may read them out of order." if two_columns else "No overlapping text columns were detected in the extracted PDF.", "Export a single-column version and check its extracted text." if two_columns else "Keep headings and text selectable."))
        if body_sizes and sorted(body_sizes)[len(body_sizes) // 2] < 9:
            checks.append(_check("Format", "fix", "Text may be too small", "The PDF's median text size is below 9 pt.", "Use about 10–11 pt for body text and export again."))
        if image_blocks:
            checks.append(_check("Format", "review", "Graphics in the PDF", f"Detected {image_blocks} image block{'s' if image_blocks != 1 else ''} across {pages} page{'s' if pages != 1 else ''}.", "Keep essential contact, experience and skills in selectable text."))
        if pages > 2:
            checks.append(_check("Format", "review", "Resume length", f"The PDF has {pages} pages.", "Check whether each page adds relevant evidence for this role."))
        return checks
    if suffix == ".docx":
        from docx import Document
        document = Document(io.BytesIO(data))
        table_count = len(document.tables)
        header_text = " ".join(paragraph.text for section in document.sections for paragraph in section.header.paragraphs)
        checks = [_check("Format", "review" if table_count else "good", "Table-based layout" if table_count else "Readable document structure", f"Found {table_count} table{'s' if table_count != 1 else ''} in the Word document." if table_count else "No tables were found in the Word document body.", "Move essential information into ordinary paragraphs if extraction is out of order." if table_count else "Use standard headings and a single text column.")]
        if analysis._contact(header_text)["email"] or analysis._contact(header_text)["phone"]:
            checks.append(_check("Format", "fix", "Contact details in the header", "Word header content may be missed by some resume parsers.", "Repeat your email and phone in the document body."))
        return checks
    return [_check("Format", "review", "Plain text layout", "Text and Markdown files have no fixed visual template to inspect.", "Use the clean DOCX or PDF export to create a readable final layout.")]


def audit_resume(job_text: str, resume_text: str, result: dict[str, Any], filename: str = "Pasted text", data: bytes | None = None) -> list[dict[str, str]]:
    """Return specific, explainable checks without claiming an employer ATS verdict."""
    checks = _layout_checks(filename, data)
    sections = result["sections"]
    contact = result["contact"]
    words = result["word_count"]
    checks.append(_check("Essentials", "good" if contact["email"] else "fix", "Email address", "A readable email address was found." if contact["email"] else "No email address was found in the parsed resume.", "Keep the email as selectable text near your name." if contact["email"] else "Add a professional email address near your name."))
    checks.append(_check("Essentials", "good" if contact["phone"] else "review", "Phone number", "A phone number was found." if contact["phone"] else "No phone number was found in the parsed resume.", "Confirm it is current and easy to read." if contact["phone"] else "Add a phone number if you want recruiters to call you."))
    needed = [name for name in ("Summary", "Skills", "Experience", "Education") if name not in sections]
    if "Experience" in needed and "Projects" in sections:
        needed.remove("Experience")
    checks.append(_check("Structure", "fix" if needed else "good", "Core sections", "Missing or unrecognized: " + ", ".join(needed) + "." if needed else "Summary, skills, experience or projects, and education were recognized.", "Add conventional section headings so your content is easy to parse." if needed else "Keep these headings clear and consistent."))
    checks.append(_check("Structure", "review" if words < 180 or words > 1100 else "good", "Content density", f"The parsed resume contains {words} words.", "Add concise evidence of relevant work; avoid filler." if words < 180 else "Trim repeated or unrelated content for this role." if words > 1100 else "Keep the most relevant details easy to scan."))
    if PERSONAL.search(resume_text):
        checks.append(_check("Essentials", "review", "Personal details", "A personal detail such as date of birth, marital status or religion was detected.", "Consider removing details unrelated to the role."))
    experience_lines = [line for section in ("Experience", "Projects") for line in sections.get(section, ()) if len(line.split()) >= 5 and not ("|" in line and DATE.search(line))]
    if experience_lines:
        action_count = sum(line.lstrip("-• ").split()[0].lower().strip(".,:;") in analysis.ACTION_WORDS for line in experience_lines)
        checks.append(_check("Content", "review" if action_count < len(experience_lines) else "good", "Action-led experience", f"{action_count} of {len(experience_lines)} substantive experience or project lines start with a clear action.", "Lead vague lines with what you actually built, analyzed, improved or delivered." if action_count < len(experience_lines) else "Keep each statement specific to your contribution."))
        quantified = sum(bool(METRIC.search(line)) for line in experience_lines)
        checks.append(_check("Content", "review" if not quantified else "good", "Measurable impact", f"{quantified} of {len(experience_lines)} experience or project lines contain a measurable result or scale.", "Add a number only when you can verify it; describe scope or outcome otherwise." if not quantified else "Check that every number is accurate and useful."))
        long_bullets = sum(len(line.split()) > 34 for line in experience_lines)
        if long_bullets:
            checks.append(_check("Content", "review", "Long experience lines", f"{long_bullets} line{'s' if long_bullets != 1 else ''} exceed 34 words.", "Split dense lines into focused action and outcome statements."))
    else:
        checks.append(_check("Content", "fix", "Work or project evidence", "No substantive experience or project lines were found under a recognized heading.", "Describe concrete tasks in Experience or Projects."))
    if VAGUE.search(resume_text):
        checks.append(_check("Content", "review", "Vague wording", "The resume contains words such as “stuff” or “things” that hide the actual work.", "Replace each vague phrase with a specific task, tool or result."))
    if result["job_skills"]:
        checks.append(_check("Job fit", "review" if result["missing_skills"] else "good", "Job skills in the resume", f'{len(result["matched_skills"])} of {len(result["job_skills"])} recognized job skills appear in the resume. Missing: {", ".join(result["missing_skills"][:6]) or "none"}.', "For a missing skill you truly used, add a concrete example in the appropriate section; otherwise leave it out." if result["missing_skills"] else "Keep matching skills tied to real work, not only a list."))
        summary = " ".join(list(sections.get("Summary", ())) + list(sections.get("Profile", ())))
        supported = [skill for skill in result["matched_skills"] if analysis.skill_in_text(skill, summary)]
        if result["matched_skills"] and not supported:
            checks.append(_check("Job fit", "review", "Tailored summary", "Your summary does not mention any of the matching job skills already in your resume.", "Bring the strongest supported skills into a short summary."))
    else:
        checks.append(_check("Job fit", "review", "No recognized job skills", "The current skill vocabulary did not recognize a specific skill in this job description.", "Review the job description manually and make sure your final resume states relevant, truthful experience clearly."))
    if DATE.search(resume_text) and not re.search(r"\b(?:19|20)\d{2}\s*[-–—]\s*(?:\b(?:19|20)\d{2}\b|present|current)\b", resume_text, re.I):
        checks.append(_check("Structure", "review", "Date clarity", "Dates were found, but a clear year range was not recognized.", "Check that each role or project has a consistent start and end date."))
    return checks


def rewrite_evidence(evidence: str, job_text: str, required_skill: str | None = None) -> dict[str, Any]:
    """Rewrite a real task into a bullet without adding facts or metrics."""
    raw = re.sub(r"\s+", " ", evidence).strip().lstrip("-• ").rstrip(" .")
    if len(raw.split()) < 7 or VAGUE.search(raw):
        raise ValueError("Describe a specific task, tool and outcome or scope in at least seven words. Replace vague terms such as “stuff” or “things”.")
    if re.match(r"^(?:I (?:just )?know|I am familiar with|familiar with)\b", raw, re.I):
        raise ValueError("Describe work you actually completed, not familiarity with a skill.")
    job_skills = analysis._skills(job_text)
    if required_skill:
        aliases = analysis.SKILL_ALIASES.get(required_skill.casefold(), ())
        if not analysis.skill_in_text(required_skill, raw):
            alias = next((item for item in aliases if analysis.skill_in_text(item, raw)), None)
            if alias is None:
                raise ValueError(f"Include {required_skill} and explain how you used it.")
            raw = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", required_skill, raw, count=1, flags=re.I)
    terms = [skill for skill in job_skills if analysis.skill_in_text(skill, raw)]
    if required_skill and required_skill not in terms:
        terms.insert(0, required_skill)
    context = ""
    prefix = re.match(r"^(?:In|During) (my|a|the) (internship|project|role|job|course),?\s+(.+)$", raw, re.I)
    if prefix:
        raw = prefix.group(3)
        context = f" during {prefix.group(1).lower()} {prefix.group(2).lower()}"
    role = re.match(r"^I (?:have |had )?(?:worked on|did) (?:a|the|my) (project|internship) (?:where|and) I (.+)$", raw, re.I)
    if role:
        raw = "I " + role.group(2)
        context = context or f" in my {role.group(1).lower()}"
    phrase = re.match(r"^I (?:have |had )?used (.+?) (?:to|for) (\w+) (.+)$", raw, re.I)
    if phrase and phrase.group(2).lower() in PAST_VERBS:
        tools = phrase.group(1).strip()
        object_text = phrase.group(3).strip()
        if phrase.group(2).lower().endswith("ing") and object_text.startswith("of "):
            object_text = object_text[3:]
        drafted = f"{PAST_VERBS[phrase.group(2).lower()]} {object_text} using {tools}"
    else:
        drafted = raw
        for pattern, replacement in (
            (r"^I (?:have |had )?been (?:working on|doing)\b", "Contributed to"),
            (r"^I (?:have |had )?worked on\b", "Contributed to"),
            (r"^I (?:was |have been )?responsible for building\b", "Built"),
            (r"^I (?:was |have been )?responsible for\b", "Contributed to"),
            (r"^I (?:have |had )?helped (?:with|in)\b", "Supported"),
            (r"^I (?:have |had )?used\b", "Used"),
            (r"^I (?:have |had )?experience (?:with|using)\b", "Used"),
            (r"^My experience includes\b", "Worked with"),
        ):
            if re.match(pattern, drafted, re.I):
                drafted = re.sub(pattern, replacement, drafted, count=1, flags=re.I)
                break
        first_person = re.match(r"^I (\w+)\b(.*)$", drafted, re.I)
        if first_person and first_person.group(1).lower() in PAST_VERBS:
            drafted = PAST_VERBS[first_person.group(1).lower()] + first_person.group(2)
    drafted = re.sub(r"\b(?:basically|really|kind of|sort of|actually|just)\b\s*", "", drafted, flags=re.I)
    drafted = re.sub(r"^Supported (?:creating|making)\b", "Supported the creation of", drafted, flags=re.I)
    drafted = re.sub(r"\s+", " ", drafted).strip(" ,.;")
    if drafted.lower().startswith(("i ", "we ", "my ")):
        raise ValueError("Describe what you did with an action verb, such as built, analyzed or improved, so HireFlow can draft a professional line.")
    if not drafted:
        raise ValueError("Add a concrete action and result before drafting a line.")
    drafted = drafted[0].upper() + drafted[1:]
    if context and context.casefold() not in drafted.casefold():
        drafted += context
    bullet = "- " + drafted.rstrip(" .") + "."
    if required_skill and not analysis.skill_in_text(required_skill, bullet):
        bullet = bullet[:-1] + f" using {required_skill}."
    placement = "Projects" if re.search(r"\b(project|course|capstone|hackathon|portfolio)\b", evidence, re.I) else "Experience"
    return {"bullet": bullet, "placement": placement, "job_terms": terms, "note": "Uses only the task and tools you supplied. Add a verified outcome or number if you have one."}
