"""HTTP interface for HireFlow's existing Python account and document engines."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import accounts, analysis, applicant_tools, auth, resume_coach


ROOT = Path(__file__).resolve().parent
COOKIE = "hireflow_session"
IDLE = auth.IDLE_TIMEOUT_SECONDS
ABSOLUTE = auth.ABSOLUTE_TIMEOUT_SECONDS
MAX_REQUEST_BYTES = 80 * 1024 * 1024
app = FastAPI(title="HireFlow API", docs_url="/api/docs", openapi_url="/api/openapi.json")


class RequestTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """Reject oversized API bodies before or during multipart parsing."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            await self.application(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", ())}
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        rejection = Response("Request exceeds the 80 MB limit.", status_code=413)
        if declared > MAX_REQUEST_BYTES:
            await rejection(scope, receive, send)
            return
        total = 0
        started = False

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_REQUEST_BYTES:
                    raise RequestTooLarge
            return message

        async def tracked_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.application(scope, limited_receive, tracked_send)
        except RequestTooLarge:
            if not started:
                await rejection(scope, receive, send)


app.add_middleware(BodyLimitMiddleware)


def _session_table() -> None:
    accounts.init_db()
    with accounts._connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS web_sessions (
            token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, mode TEXT,
            created_at REAL NOT NULL, last_activity REAL NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS web_sessions_email ON web_sessions(email)")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public_user(user: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
    return {"email": user["username"], "display_name": user["display_name"], "modes": list(user["modes"]), "mode": mode}


def _issue_session(response: Response, user: dict[str, Any], request: Request) -> dict[str, Any]:
    _session_table()
    token = secrets.token_urlsafe(48)
    now = time.time()
    with accounts._connect() as db:
        db.execute("INSERT INTO web_sessions VALUES (?, ?, NULL, ?, ?)", (_token_hash(token), user["username"], now, now))
    response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=ABSOLUTE, path="/")
    return _public_user(user)


def _session(request: Request) -> tuple[dict[str, Any], str | None]:
    token = request.cookies.get(COOKIE, "")
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    _session_table()
    key = _token_hash(token)
    now = time.time()
    expired = False
    with accounts._connect() as db:
        row = db.execute("SELECT email, mode, created_at, last_activity FROM web_sessions WHERE token_hash=?", (key,)).fetchone()
        if row is None:
            raise HTTPException(401, "Sign in to continue.")
        if now - row["last_activity"] >= IDLE or now - row["created_at"] >= ABSOLUTE:
            db.execute("DELETE FROM web_sessions WHERE token_hash=?", (key,))
            expired = True
        else:
            db.execute("UPDATE web_sessions SET last_activity=? WHERE token_hash=?", (now, key))
    if expired:
        raise HTTPException(401, "Your session expired. Sign in again.")
    user = accounts.get_account(row["email"])
    if not user:
        raise HTTPException(401, "This account is no longer available.")
    mode = row["mode"] if row["mode"] in user["modes"] else None
    return user, mode


def current(request: Request) -> tuple[dict[str, Any], str | None]:
    return _session(request)


def recruiter(session: tuple[dict[str, Any], str | None] = Depends(current)) -> dict[str, Any]:
    user, mode = session
    if mode != "recruiter":
        raise HTTPException(403, "Choose recruiter mode to open this workspace.")
    return user


def applicant(session: tuple[dict[str, Any], str | None] = Depends(current)) -> dict[str, Any]:
    user, mode = session
    if mode != "applicant":
        raise HTTPException(403, "Choose applicant mode to open this workspace.")
    return user


@app.middleware("http")
async def same_origin_mutations(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        if request.headers.get("x-hireflow-request") != "1" or request.headers.get("sec-fetch-site") == "cross-site":
            return Response("Request origin rejected.", status_code=403)
    return await call_next(request)


@app.exception_handler(ValueError)
async def validation_error(_request: Request, exc: ValueError):
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": str(exc)}, status_code=400)


class Credentials(BaseModel):
    email: str
    password: str


class Signup(Credentials):
    display_name: str
    modes: list[str] = Field(default_factory=lambda: list(auth.SUPPORTED_MODES))


class Mode(BaseModel):
    mode: str


class Profile(BaseModel):
    display_name: str


class TextInput(BaseModel):
    text: str
    filename: str = "Pasted text"


class ReorderInput(BaseModel):
    text: str
    order: list[str]


class TailorDecision(BaseModel):
    original: str
    suggestions: list[dict[str, Any]]
    decisions: dict[str, str]
    edits: dict[str, str] = Field(default_factory=dict)
    placements: dict[str, str] = Field(default_factory=dict)


class RewriteInput(BaseModel):
    evidence: str
    job_text: str = ""
    required_skill: str | None = None


class CoachInput(BaseModel):
    question: str
    job_text: str
    resume_text: str


class LetterInput(BaseModel):
    job_text: str
    resume_text: str
    company: str = ""
    role: str = ""


class ExportInput(BaseModel):
    text: str
    format: str
    template: str = "Contemporary"
    options: dict[str, float] = Field(default_factory=dict)


class PreviewInput(BaseModel):
    text: str
    template: str = "Contemporary"
    options: dict[str, float] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)


class DeleteAccountInput(BaseModel):
    password: str
    confirmation: str


class VersionInput(BaseModel):
    name: str
    resume_text: str
    target_role: str = ""
    template: str = "Contemporary"
    source_id: str | None = None


class ProjectInput(BaseModel):
    id: str | None = None
    company: str
    role: str
    status: str = "Interested"
    job_text: str = ""
    resume_text: str = ""
    cover_letter: str = ""
    notes: str = ""


@app.post("/api/auth/signup")
def signup(payload: Signup, response: Response, request: Request):
    user = accounts.create_account(payload.email, payload.display_name, payload.password, payload.modes)
    return _issue_session(response, user, request)


@app.post("/api/auth/login")
def login(payload: Credentials, response: Response, request: Request):
    account = accounts.get_account(payload.email)
    user, wait = auth.authenticate("web", payload.email, payload.password, {payload.email.strip().lower(): account} if account else {})
    if not user:
        raise HTTPException(429 if wait else 401, f"Too many attempts. Try again in {wait} seconds." if wait else "Email or password was not recognized.")
    return _issue_session(response, user, request)


@app.get("/api/session")
def session(state: tuple[dict[str, Any], str | None] = Depends(current)):
    return _public_user(*state)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        _session_table()
        with accounts._connect() as db:
            db.execute("DELETE FROM web_sessions WHERE token_hash=?", (_token_hash(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.post("/api/mode")
def choose_mode(payload: Mode, request: Request, state: tuple[dict[str, Any], str | None] = Depends(current)):
    user, _ = state
    if payload.mode not in user["modes"]:
        raise HTTPException(403, "This workspace is not enabled for your account.")
    with accounts._connect() as db:
        db.execute("UPDATE web_sessions SET mode=? WHERE token_hash=?", (payload.mode, _token_hash(request.cookies[COOKIE])))
    return _public_user(user, payload.mode)


@app.patch("/api/profile")
def update_profile(payload: Profile, state: tuple[dict[str, Any], str | None] = Depends(current)):
    user, mode = state
    return _public_user(accounts.update_display_name(user["username"], payload.display_name), mode)


def _read_file(upload: UploadFile | None) -> str | None:
    if upload is None:
        return None
    filename = (upload.filename or "document").replace("\\", "/").split("/")[-1]
    if len(filename) > 180:
        raise ValueError("File names may contain up to 180 characters.")
    data = upload.file.read(10 * 1024 * 1024 + 1)
    return analysis.extract_document(filename, data)


@app.post("/api/documents/extract")
def extract(file: UploadFile = File(...), _state: tuple[dict[str, Any], str | None] = Depends(current)):
    return {"text": _read_file(file), "filename": file.filename}


@app.post("/api/recruiter/rank")
def rank_candidates(job_text: str = Form(""), job_file: UploadFile | None = File(None), resumes: list[UploadFile] = File(...), _user: dict = Depends(recruiter)):
    job = _read_file(job_file) or job_text.strip()
    if len(job.split()) < 8:
        raise ValueError("Add a job description of at least eight words.")
    if not resumes or len(resumes) > 40:
        raise ValueError("Upload between one and forty candidate resumes.")
    results, failures = [], []
    for upload in resumes:
        try:
            text = _read_file(upload)
            results.append(analysis.analyse(job, text or "", upload.filename or "Resume"))
        except ValueError as exc:
            failures.append({"filename": upload.filename, "reason": str(exc)})
    results.sort(key=lambda item: (item["overall"], item["ats"]), reverse=True)
    return {"results": results, "failures": failures}


@app.post("/api/applicant/health")
def health(payload: TextInput, _user: dict = Depends(applicant)):
    return applicant_tools.resume_health(payload.text, payload.filename)


@app.post("/api/applicant/health-file")
def health_file(text: str = Form(""), resume_file: UploadFile = File(...), _user: dict = Depends(applicant)):
    data = resume_file.file.read(10 * 1024 * 1024 + 1)
    parsed = analysis.extract_document(resume_file.filename or "resume", data)
    return applicant_tools.resume_health(text or parsed, resume_file.filename or "resume", data)


@app.post("/api/applicant/tailor")
def tailor(job_text: str = Form(""), resume_text: str = Form(""), job_file: UploadFile | None = File(None), resume_file: UploadFile | None = File(None), _user: dict = Depends(applicant)):
    job = _read_file(job_file) or job_text.strip()
    resume = _read_file(resume_file) or resume_text.strip()
    result = analysis.analyse(job, resume, resume_file.filename if resume_file else "Pasted text")
    data = None
    if resume_file:
        resume_file.file.seek(0)
        data = resume_file.file.read(10 * 1024 * 1024 + 1)
    result["audit"] = resume_coach.audit_resume(job, resume, result, resume_file.filename if resume_file else "Pasted text", data)
    result["keyword_map"] = applicant_tools.keyword_map(job, resume)
    return result


@app.post("/api/applicant/rewrite")
def rewrite(payload: RewriteInput, _user: dict = Depends(applicant)):
    return resume_coach.rewrite_evidence(payload.evidence, payload.job_text, payload.required_skill)


@app.post("/api/applicant/apply")
def apply(payload: TailorDecision, _user: dict = Depends(applicant)):
    return {"text": analysis.apply_decisions(payload.original, payload.suggestions, payload.decisions, payload.edits, payload.placements)}


@app.post("/api/applicant/reorder")
def reorder(payload: ReorderInput, _user: dict = Depends(applicant)):
    allowed = {"Summary", "Profile", "Skills", "Experience", "Projects", "Education", "Certifications"}
    if any(section not in allowed for section in payload.order):
        raise ValueError("Choose standard resume sections to reorder.")
    return {"text": applicant_tools.reorder_sections(payload.text, payload.order)}


@app.post("/api/applicant/ai-suggestions")
def extra_suggestions(payload: dict[str, Any], _user: dict = Depends(applicant)):
    return {"suggestions": applicant_tools.ai_tailoring_suggestions(str(payload.get("job_text", "")), str(payload.get("resume_text", "")), set(payload.get("excluded_lines", [])))}


@app.post("/api/applicant/build")
def build(payload: dict[str, str], _user: dict = Depends(applicant)):
    return {"text": applicant_tools.build_resume(payload)}


@app.post("/api/applicant/coach")
def coach(payload: CoachInput, _user: dict = Depends(applicant)):
    result = analysis.analyse(payload.job_text, payload.resume_text) if len(payload.job_text.split()) >= 8 else applicant_tools.resume_health(payload.resume_text)
    answer, source = applicant_tools.coach_reply(payload.question, payload.job_text, payload.resume_text, result)
    return {"answer": answer, "source": source}


@app.post("/api/applicant/cover")
def cover(payload: LetterInput, _user: dict = Depends(applicant)):
    text, source = applicant_tools.cover_letter(payload.job_text, payload.resume_text, payload.company, payload.role)
    return {"text": text, "source": source}


@app.post("/api/applicant/export")
def export(payload: ExportInput, _user: dict = Depends(applicant)):
    if len(payload.text.split()) < 8:
        raise ValueError("Add more resume content before exporting.")
    if payload.format == "pdf":
        data, media, filename = analysis.export_pdf(payload.text, payload.template, payload.options), "application/pdf", "hireflow-resume.pdf"
    elif payload.format == "docx":
        data, media, filename = analysis.export_docx(payload.text, payload.template, payload.options), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "hireflow-resume.docx"
    elif payload.format == "txt":
        data, media, filename = payload.text.encode("utf-8"), "text/plain", "hireflow-resume.txt"
    else:
        raise ValueError("Choose PDF, DOCX or TXT.")
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/applicant/preview")
def preview(payload: PreviewInput, _user: dict = Depends(applicant)):
    if len(payload.text.split()) < 8:
        raise ValueError("Add more resume content to preview the PDF.")
    import fitz
    document = fitz.open(stream=analysis.export_pdf(payload.text, payload.template, payload.options), filetype="pdf")
    try:
        for proposed in payload.highlights[:25]:
            phrase = proposed.strip().lstrip("-• ").rstrip(" .")[:180]
            if len(phrase) < 8:
                continue
            for page in document:
                for area in page.search_for(phrase)[:3]:
                    annotation = page.add_highlight_annot(area)
                    if annotation:
                        annotation.set_colors(stroke=(0.92, 0.61, 0.39))
                        annotation.update()
        data = document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="hireflow-preview.pdf"', "Cache-Control": "no-store"})


@app.post("/api/applicant/letter-export")
def letter_export(payload: ExportInput, _user: dict = Depends(applicant)):
    if payload.format == "pdf":
        data, media, filename = applicant_tools.export_letter_pdf(payload.text), "application/pdf", "hireflow-cover-letter.pdf"
    elif payload.format == "docx":
        data, media, filename = applicant_tools.export_letter_docx(payload.text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "hireflow-cover-letter.docx"
    elif payload.format == "txt":
        data, media, filename = payload.text.encode("utf-8"), "text/plain", "hireflow-cover-letter.txt"
    else:
        raise ValueError("Choose PDF, DOCX or TXT.")
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/applicant/versions")
def versions(user: dict = Depends(applicant)):
    return accounts.list_resume_versions(user["username"])


@app.delete("/api/applicant/versions/{version_id}")
def delete_version(version_id: str, user: dict = Depends(applicant)):
    if not accounts.delete_resume_version(user["username"], version_id):
        raise HTTPException(404, "Resume version not found.")
    return {"ok": True}


@app.post("/api/account/export")
def account_export(state: tuple[dict[str, Any], str | None] = Depends(current)):
    data = json.dumps(accounts.export_account_data(state[0]["username"]), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(data, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="hireflow-account-data.json"', "Cache-Control": "no-store"})


@app.post("/api/account/delete")
def account_delete(payload: DeleteAccountInput, response: Response, state: tuple[dict[str, Any], str | None] = Depends(current)):
    if payload.confirmation != "DELETE":
        raise ValueError("Type DELETE to confirm account removal.")
    accounts.delete_account(state[0]["username"], payload.password)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.post("/api/applicant/versions")
def save_version(payload: VersionInput, user: dict = Depends(applicant)):
    return {"id": accounts.save_resume_version(user["username"], payload.name, payload.resume_text, payload.target_role, payload.template, payload.source_id)}


@app.get("/api/applicant/projects")
def projects(user: dict = Depends(applicant)):
    return accounts.list_projects(user["username"])


@app.post("/api/applicant/projects")
def save_project(payload: ProjectInput, user: dict = Depends(applicant)):
    identity = accounts.save_project(user["username"], payload.company, payload.role, payload.status, payload.job_text, payload.resume_text, payload.cover_letter, payload.notes, payload.id)
    return {"id": identity}


@app.delete("/api/applicant/projects/{project_id}")
def delete_project(project_id: str, user: dict = Depends(applicant)):
    if not accounts.delete_project(user["username"], project_id):
        raise HTTPException(404, "Application not found.")
    return {"ok": True}


DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API route not found.")
        asset = (DIST / path).resolve()
        if path and asset.is_file() and DIST.resolve() in asset.parents:
            return FileResponse(asset)
        return FileResponse(DIST / "index.html")
