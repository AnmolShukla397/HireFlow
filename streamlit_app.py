"""HireFlow: private document analysis for recruiters and applicants."""
from __future__ import annotations

import csv
import html
import io
import logging
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app import accounts, analysis, auth, resume_coach, applicant_tools

LOGGER = logging.getLogger(__name__)

st.set_page_config(page_title="HireFlow · Resume intelligence", page_icon="H", layout="wide", initial_sidebar_state="collapsed")


def safe(value: object) -> str:
    return html.escape(str(value))


def styles() -> None:
    st.markdown("<style>" + (Path(__file__).parent / "static" / "hireflow.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
    motion_script = (Path(__file__).parent / "static" / "hireflow_motion.js").read_text(encoding="utf-8")
    components.html("<script>" + motion_script + "</script>", height=0)


def header(title: str, description: str, mode: str) -> None:
    label = "Recruiter workspace" if mode == "recruiter" else "Applicant workspace"
    sequence = ("Job brief", "Candidate resumes", "Ranked evidence") if mode == "recruiter" else ("Job brief", "Your resume", "Tailored draft")
    st.markdown(
        f'<section class="workspace-hero"><div class="workspace-copy"><p class="workspace-label">{label}</p><h1>{safe(title)}</h1><p>{safe(description)}</p></div>'
        + '<div class="workspace-diagram" aria-hidden="true">'
        + ''.join(f'<span>{safe(step)}</span>' for step in sequence)
        + '</div></section>', unsafe_allow_html=True,
    )


def set_mode(mode: str, user: dict) -> None:
    if mode not in user.get("modes", ()):
        st.error("This account cannot open that workspace.")
        return
    st.session_state["active_mode"] = mode
    st.rerun()


def landing() -> None:
    styles()
    st.markdown('<div class="landing-scroll-progress" aria-hidden="true"></div>', unsafe_allow_html=True)
    nav = st.columns([7, 1.2, 1.4], vertical_alignment="center")
    with nav[0]:
        st.markdown('<div class="landing-brand">Hire<span>Flow</span><i aria-hidden="true"></i></div>', unsafe_allow_html=True)
    if nav[1].button("Sign in", key="landing-signin", use_container_width=True):
        st.session_state.update({"public_view": "auth", "auth-action": "Sign in"})
        st.rerun()
    if nav[2].button("Create account", key="landing-create", use_container_width=True):
        st.session_state.update({"public_view": "auth", "auth-action": "Create account"})
        st.rerun()
    notice = st.session_state.pop("auth_notice", None)
    if notice:
        st.info(notice)
    hero = st.columns([.91, 1.09], gap="large", vertical_alignment="center")
    with hero[0]:
        st.markdown('<section class="landing-copy"><p class="landing-kicker">A clearer case for the work you have done</p><h1><span>Make</span><span>every</span><br><span>line</span><em>count.</em></h1><p>HireFlow reads the job brief beside your resume, finds the evidence that matters, and lets you approve every change before it becomes your story.</p></section>', unsafe_allow_html=True)
        if st.button("Start with your resume  ↗", key="landing-primary", use_container_width=False):
            st.session_state.update({"public_view": "auth", "auth-action": "Create account"})
            st.rerun()
        st.markdown('<p class="landing-subline">Build a resume · Check your fit · Keep the final say</p>', unsafe_allow_html=True)
    with hero[1]:
        st.markdown('''<div class="landing-stage"><div class="scene-aura" aria-hidden="true"></div><div class="scene-grid" aria-hidden="true"></div><div class="hf-3d-scene" role="group" tabindex="0" aria-label="Interactive three-dimensional example showing how a job brief, resume, and evidence review connect. Move the pointer or use arrow keys to rotate; press Home to reset."><div class="hf-scene-core"><div class="scene-orbit" aria-hidden="true"></div><div class="scene-card scene-brief"><div class="scene-card-heading"><span>01 / JOB BRIEF</span><i>↗</i></div><strong>Data Analyst</strong><p>Build reporting that helps teams make better decisions.</p><div class="scene-tags"><span>Python</span><span>SQL</span><span>Reporting</span></div></div><div class="scene-card scene-resume"><div class="scene-card-heading"><span>02 / RESUME</span><i>↗</i></div><strong>Alex Morgan</strong><small>DATA ANALYST · EXPERIENCE</small><div class="scene-divider"></div><p>I used Python and SQL to make a weekly sales dashboard for my team.</p><div class="scene-resume-foot">Original evidence <b>●</b> Verified</div></div><div class="scene-card scene-insight"><div class="scene-card-heading"><span>03 / HIREFLOW REVIEW</span><i>✦</i></div><small>ROLE-ALIGNED REWRITE</small><p>Built a weekly sales dashboard using <mark>Python</mark> and <mark>SQL</mark> for team reporting.</p><div class="scene-insight-foot"><span>Evidence preserved</span><b>Review edit ↗</b></div></div><div class="scene-connector scene-connector-one" aria-hidden="true"></div><div class="scene-connector scene-connector-two" aria-hidden="true"></div></div></div><div class="scene-guidance"><span><i aria-hidden="true">✣</i> Move to explore · Drag to rotate · Arrow keys also work</span><button type="button" class="scene-reset" aria-label="Reset three-dimensional view">Reset view ↺</button></div></div>''', unsafe_allow_html=True)
    st.markdown('<div class="landing-section-head hf-reveal"><span>SEE THE DIFFERENCE</span><h2>One line. More signal.</h2><p>Try the comparison. Every suggested edit in the app stays under your control.</p></div>', unsafe_allow_html=True)
    show_revised = st.toggle("Show the tailored version", key="landing-comparison")
    if show_revised:
        st.markdown('<div class="landing-comparison is-revised" data-ui><div><small>AFTER · ACTION + EVIDENCE</small><p>Built a weekly sales dashboard using <mark>Python</mark> and <mark>SQL</mark> for team reporting.</p></div><span>Proposed wording · awaiting your approval</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="landing-comparison" data-ui><div><small>BEFORE · YOUR ORIGINAL WORDS</small><p>I used Python and SQL to make a weekly sales dashboard for my team.</p></div><span>Source evidence · no facts added</span></div>', unsafe_allow_html=True)
    st.markdown('''<section class="motion-story" aria-label="How HireFlow works"><div class="motion-story-intro hf-reveal"><span>THE WORKFLOW / 01—03</span><h2>From document to decision.</h2><p>Scroll through a real example. The software surfaces evidence; you decide what belongs in the final document.</p></div><div class="motion-story-grid"><div class="motion-story-steps"><article class="motion-chapter" data-step="1"><span>01 / IMPORT</span><h3>Start with what you wrote.</h3><p>Bring a resume and a job brief. HireFlow reads the text while keeping the original wording available for comparison.</p></article><article class="motion-chapter" data-step="2"><span>02 / INSPECT</span><h3>See the evidence, not a mystery score.</h3><p>Find relevant terms, section gaps, formatting risks and the experience that already supports the role.</p></article><article class="motion-chapter" data-step="3"><span>03 / APPROVE</span><h3>Make the final call.</h3><p>Review a specific rewrite, accept or reject it, then export a resume that still sounds like you.</p></article></div><div class="motion-story-display"><div class="story-stage" data-step="1" aria-label="Illustrated HireFlow document workflow"><div class="story-stage-top"><span class="story-stage-mark">H<span>F</span></span><span>DOCUMENT / IN PROGRESS</span><span class="story-live">● LIVE PREVIEW</span></div><div class="story-visual" data-step="1"><small>ORIGINAL RESUME LINE</small><p>I used Python and SQL to make a weekly sales dashboard for my team.</p><div class="story-meta"><span>Alex Morgan · Experience</span><b>Source</b></div></div><div class="story-visual" data-step="2" aria-hidden="true"><small>WHAT HIREFLOW FOUND</small><p>Python <em>✓ supported</em><br>SQL <em>✓ supported</em><br>Result <em class="story-review">Needs context</em></p><div class="story-meta"><span>2 role terms found in real work</span><b>Review</b></div></div><div class="story-visual" data-step="3" aria-hidden="true"><small>PROPOSED · AWAITING APPROVAL</small><p>Built a weekly sales dashboard using <mark>Python</mark> and <mark>SQL</mark> for team reporting.</p><div class="story-meta"><span>Facts preserved from the source</span><b>Accept ↗</b></div></div><div class="story-stage-bottom"><span>YOUR EVIDENCE / YOUR DECISION</span><div class="story-step-track" aria-hidden="true"><i></i></div><span class="story-step-number">01 / 03</span></div></div></div></div></section>''', unsafe_allow_html=True)
    st.markdown('<div class="landing-section-head landing-modes-head hf-reveal"><span>TWO FOCUSED WORKSPACES</span><h2>Different tasks. One standard of evidence.</h2><p>Explore the kind of decision each workspace helps you make.</p></div>', unsafe_allow_html=True)
    preview = st.radio("Preview a workspace", ("Applicant", "Recruiter"), horizontal=True, label_visibility="collapsed", key="landing-workspace-preview")
    if preview == "Applicant":
        st.markdown('''<section class="landing-workspace-preview applicant-preview" aria-label="Applicant workspace preview"><div><span class="preview-index">01 / APPLICANT</span><h3>Improve the resume you will actually send.</h3><p>Compare your experience with a target role, inspect specific findings, and approve each change before it enters the final document.</p><div class="preview-steps"><span>Import</span><b>→</b><span>Analyze</span><b>→</b><span>Approve</span><b>→</b><span>Export</span></div></div><div class="preview-artifact"><small>RESUME / RECOMMENDATION</small><div class="preview-artifact-line"><i>01</i><span>Built a weekly sales dashboard using Python and SQL.</span></div><div class="preview-artifact-note"><span>✓</span> Supported by your original experience</div><div class="preview-artifact-actions"><span>Accept change</span><span>Reject</span></div></div></section>''', unsafe_allow_html=True)
    else:
        st.markdown('''<section class="landing-workspace-preview recruiter-preview" aria-label="Recruiter workspace preview"><div><span class="preview-index">02 / RECRUITER</span><h3>Read the shortlist behind the ranking.</h3><p>Compare a job description with a batch of CVs. Open any candidate to see the skills, gaps and resume evidence behind their position.</p><div class="preview-steps"><span>Job brief</span><b>→</b><span>Candidate CVs</span><b>→</b><span>Ranked evidence</span></div></div><div class="preview-artifact"><small>SHORTLIST / SAMPLE</small><div class="preview-candidate"><b>01</b><span>Alex Morgan<small>Python · SQL · reporting</small></span><strong>86</strong></div><div class="preview-candidate"><b>02</b><span>Sam Rivera<small>SQL · stakeholder work</small></span><strong>74</strong></div><div class="preview-artifact-note"><span>↗</span> Open a candidate for the full score breakdown</div></div></section>''', unsafe_allow_html=True)
    st.markdown('<div class="landing-close hf-reveal"><div><h2>Your next draft starts here.</h2><p>One workspace for the resume, the job brief and the decisions in between.</p></div></div>', unsafe_allow_html=True)
    if st.button("Create your account  ↗", key="landing-bottom", use_container_width=False):
        st.session_state.update({"public_view": "auth", "auth-action": "Create account"})
        st.rerun()
    st.markdown('<p class="landing-footer">HireFlow <span>·</span> Resume intelligence with your judgment in the loop.</p>', unsafe_allow_html=True)


def login() -> None:
    styles()
    if st.button("← Back to home", key="auth-back"):
        st.session_state["public_view"] = "home"
        st.rerun()
    left, right = st.columns([1.32, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown('''<section class="login-visual"><div class="login-top"><div class="brand">Hire<span>Flow</span></div><small>Private document intelligence</small></div><div class="login-title"><h1><span>Read</span> between the resumes.</h1><p>See the evidence behind every match. Turn your own experience into a resume that speaks to the role.</p></div><div class="login-proof motion-object" aria-label="Example of how HireFlow compares a job brief with resume evidence"><div class="proof-heading">Inside a HireFlow review <span>Sample evidence</span></div><div class="proof-grid"><div><small>From the job brief</small><strong>Build and deploy reliable services with Docker.</strong></div><div><small>Found in the resume</small><strong>Deployed microservices using Docker during an internship.</strong></div></div><div class="proof-outcome"><i></i> A claim tied to real experience</div></div></section>''', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel-title">Your next move starts here.</div>', unsafe_allow_html=True)
        notice = st.session_state.pop("auth_notice", None)
        if notice:
            st.warning(notice)
        tab = st.radio("Account action", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed", key="auth-action")
        if tab == "Sign in":
            with st.form("sign_in"):
                email = st.text_input("Work email", placeholder="name@example.com", autocomplete="email")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if not accounts.valid_email(email):
                    st.error("Enter a valid email address.")
                elif not password:
                    st.error("Enter your password.")
                else:
                    with st.spinner("Checking your account…"):
                        account = accounts.get_account(email)
                        user, wait = auth.authenticate("web", email, password, {email.strip().lower(): account} if account else {})
                    if user:
                        auth.start_session(st.session_state, user)
                        st.rerun()
                    elif wait:
                        st.error(f"Too many failed attempts. Try again in {wait} seconds.")
                    else:
                        st.error("Email or password is incorrect. Check both and try again.")
        else:
            with st.form("create_account"):
                name = st.text_input("Full name", max_chars=100, autocomplete="name")
                email = st.text_input("Work email", placeholder="name@example.com", autocomplete="email")
                password = st.text_input("Password", type="password", help="Use at least 8 characters.", autocomplete="new-password")
                confirm = st.text_input("Confirm password", type="password", autocomplete="new-password")
                st.caption("Workspace access")
                recruiter = st.checkbox("Recruiter analysis", value=True)
                applicant = st.checkbox("Applicant resume review", value=True)
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if password != confirm:
                    st.error("Passwords do not match. Re-enter them and try again.")
                else:
                    try:
                        with st.spinner("Creating your secure account…"):
                            user = accounts.create_account(email, name, password, [mode for mode, enabled in (("recruiter", recruiter), ("applicant", applicant)) if enabled])
                        auth.start_session(st.session_state, user)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    except OSError:
                        st.error("Account storage is unavailable. Try again or contact the workspace administrator.")
        st.markdown('<p class="login-note"><strong>Private by design.</strong> Analysis files remain in this session. Applications you choose to save are stored in your local account database.</p>', unsafe_allow_html=True)


def choose_mode(user: dict) -> None:
    styles()
    account_bar(user)
    name = str(user.get("display_name") or user["username"]).split()[0]
    st.markdown(f'<section class="mode-hero"><h1>{safe(name)}, where are we heading?</h1><p>Two focused workspaces. Bring a job brief to either one, then choose whether you are evaluating candidates or improving your own resume.</p></section>', unsafe_allow_html=True)
    cols = st.columns(2, gap="large")
    for col, mode, title, copy, path, number, mark in (
        (cols[0], "recruiter", "Find the strongest fit", "Compare a job description with a batch of CVs. Read the shortlist, score breakdown and evidence behind every rank.", ("Job brief", "Candidate CVs", "Shortlist"), "For hiring teams", "↗"),
        (cols[1], "applicant", "Make your story sharper", "Check your resume against the role, strengthen real experience, and export a version you have reviewed.", ("Job brief", "Your resume", "Final draft"), "For applicants", "↗"),
    ):
        with col:
            journey = '<span class="mode-arrow" aria-hidden="true">→</span>'.join(f'<span>{safe(step)}</span>' for step in path)
            st.markdown(f'<section class="mode-copy {mode}"><span class="mode-number">{safe(number)}</span><h3>{safe(title)}</h3><p>{safe(copy)}</p><div class="mode-path">{journey}</div><span class="mode-object motion-object" aria-hidden="true">{mark}</span></section>', unsafe_allow_html=True)
            if mode in user.get("modes", ()):
                if st.button(f"Open {mode} workspace", key=f"mode-{mode}", use_container_width=True):
                    set_mode(mode, user)
            else:
                st.button("Access not enabled", key=f"disabled-{mode}", disabled=True, use_container_width=True)


def account_bar(user: dict, mode: str | None = None) -> None:
    name = str(user.get("display_name") or user["username"])
    initials = "".join(part[0].upper() for part in name.split()[:2]) or "HF"
    left, right = st.columns([5, 2])
    with left:
        context = {"recruiter": "Candidate intelligence", "applicant": "Resume studio"}.get(mode, "Choose a workspace")
        st.markdown(f'<div class="account-brand">Hire<span>Flow</span></div><p class="account-context">{safe(context)}</p>', unsafe_allow_html=True)
    with right:
        with st.popover(f"{initials}  {name}", use_container_width=True):
            st.markdown(f'<div class="profile-name">{safe(name)}</div><div class="profile-email">{safe(user["username"])}</div>', unsafe_allow_html=True)
            st.markdown('<div class="access-label">Workspace access</div>', unsafe_allow_html=True)
            labels = [label for key, label in (("recruiter", "Recruiter"), ("applicant", "Applicant")) if key in user.get("modes", ())]
            skill_pills(labels)
            st.caption("Analysis clears on sign out · saved applications stay in your account")
            if mode is not None and st.button("Switch workspace", key="profile-switch", use_container_width=True):
                st.session_state["active_mode"] = None
                st.rerun()
            if st.button("Sign out", key="profile-signout", use_container_width=True):
                auth.clear_session(st.session_state, "You have signed out.")
                st.rerun()
    st.divider()


def score_bar(result: dict) -> None:
    st.markdown('<div class="score-line">' + ''.join(f'<div><small>{safe(label)}</small><strong>{safe(round(result[key]))}</strong><span> / 100</span></div>' for label, key in (("Match", "overall"), ("ATS readiness", "ats"), ("Skills", "skill"))) + '</div>', unsafe_allow_html=True)


def skill_pills(skills: list, missing: bool = False) -> None:
    if skills:
        st.markdown(''.join(f'<span class="pill{" missing" if missing else ""}">{safe(skill)}</span>' for skill in skills), unsafe_allow_html=True)
    else:
        st.caption("None identified in the current text.")


def render_table(rows: list[dict], columns: list[str], label: str) -> None:
    """Render an accessible report table without Streamlit's PyArrow bridge."""
    if not rows:
        st.info("There are no rows to show for this selection.")
        return
    head = "".join(f"<th scope='col'>{safe(column)}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(
            f"<td{' class=num' if isinstance(row.get(column), (int, float)) else ''}>{safe(row.get(column, ''))}</td>"
            for column in columns
        ) + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="table-wrap" role="region" aria-label="{safe(label)}" tabindex="0"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def evidence(result: dict) -> None:
    score_bar(result)
    st.write(result["summary"])
    if not result["job_skills"]:
        st.warning("No job skills matched the current vocabulary. Skill fit uses a neutral estimate; add relevant terms to data/skills.txt for a more useful comparison.")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Skills found in both documents**")
        skill_pills(result["matched_skills"])
    with cols[1]:
        st.markdown("**Requested skills not found in resume**")
        skill_pills(result["missing_skills"], True)
    st.markdown("### Scoring evidence")
    render_table([
        {"Dimension": "Meaning / wording", "Score": result["semantic"], "Evidence": result["semantic_method"], "Weight": "50%"},
        {"Dimension": "Recognized skills", "Score": result["skill"], "Evidence": f'{len(result["matched_skills"])} of {len(result["job_skills"])} detected job skills', "Weight": "30%"},
        {"Dimension": "Experience", "Score": result["experience"], "Evidence": f'{result["resume_years"]:g} years stated; {result["required_years"]:g} requested', "Weight": "10%"},
        {"Dimension": "Education", "Score": result["education"], "Evidence": "Degree level found in text" if result["resume_degree"] else "No degree level detected", "Weight": "10%"},
    ], ["Dimension", "Score", "Evidence", "Weight"], "Scoring evidence")
    st.caption("Match = weighted estimate. ATS readiness combines job skill overlap, evidence context, action-led experience, contact details, sections and selectable text. It is not a score from an employer's ATS.")
    st.markdown("**ATS readiness factors**")
    render_table([{"Factor": label, "Score": value, "Weight": f'{result["ats_weights"][label] * 100:.0f}%'} for label, value in result["ats_factors"].items()], ["Factor", "Score", "Weight"], "ATS readiness factors")
    st.markdown("### Parsed resume snapshot")
    contact = result["contact"]
    st.write(f'**Contact:** {contact["email"] or "Email not found"} · {contact["phone"] or "Phone not found"} · {contact["linkedin"] or "LinkedIn not found"}')
    st.write(f'**Sections detected:** {", ".join(result["headings"]) or "None"} · **Words:** {result["word_count"]}')
    if result["skill_evidence"]:
        st.markdown("**Skill evidence in resume text**")
        render_table([{"Skill": skill, "Resume evidence": " / ".join(lines) or "Listed without context"} for skill, lines in result["skill_evidence"].items()], ["Skill", "Resume evidence"], "Skill evidence")
    with st.expander("Parsed sections"):
        for title, lines in result["sections"].items():
            st.markdown(f"**{title}**")
            st.text("\n".join(lines) if lines else "No content found beneath this heading.")
    with st.expander("All resume lines"):
        st.text(result["resume_text"])


def recruiter() -> None:
    header("Find the strongest fit.", "Add one job description and a batch of resumes. HireFlow compares each document, ranks the matches and shows exactly what it found.", "recruiter")
    with st.form("recruiter_input"):
        brief_col, candidate_col = st.columns([1.2, 1], gap="large")
        with brief_col:
            st.markdown('<div class="form-step">The job brief <span>What the role needs</span></div>', unsafe_allow_html=True)
            job_text = st.text_area("Job description text", height=160, placeholder="Paste the full job description, or upload it below.")
            job_file = st.file_uploader("Upload job description", type=list(analysis.SUPPORTED_FILES), key="recruiter-job")
        with candidate_col:
            st.markdown('<div class="form-step">The candidate stack <span>PDF, DOCX, TXT or MD</span></div>', unsafe_allow_html=True)
            resumes = st.file_uploader("Upload candidate resumes", type=list(analysis.SUPPORTED_FILES), accept_multiple_files=True, key="recruiter-resumes", help="Select multiple PDF, DOCX, TXT or MD files, each under 10 MB.")
            st.markdown('<p class="section-note">Each CV gets its own score and evidence summary. Add the full batch before ranking.</p>', unsafe_allow_html=True)
        submitted = st.form_submit_button("Rank candidates", use_container_width=True)
    if submitted:
        st.session_state.pop("ranked_results", None)
        st.session_state.pop("ranked_failures", None)
        try:
            job = analysis.extract_document(job_file.name, job_file.getvalue()) if job_file else job_text.strip()
            if len(job.split()) < 8:
                raise ValueError("Add a job description of at least eight words.")
            if not resumes:
                raise ValueError("Upload at least one candidate resume.")
            results, failures = [], []
            with st.spinner(f"Reading and comparing {len(resumes)} resumes…"):
                for upload in resumes:
                    try:
                        text = analysis.extract_document(upload.name, upload.getvalue())
                        results.append(analysis.analyse(job, text, upload.name))
                    except Exception as exc:
                        failures.append(f"{upload.name}: {exc}")
            results.sort(key=lambda item: (item["overall"], item["ats"]), reverse=True)
            st.session_state["ranked_results"] = results
            st.session_state["ranked_failures"] = failures
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            LOGGER.exception("Recruiter analysis failed")
            st.error("Ranking could not finish. Check the uploaded documents and app dependencies, then try again.")
    results = st.session_state.get("ranked_results", [])
    failures = st.session_state.get("ranked_failures", [])
    for failure in failures:
        st.warning(failure)
    if failures and not results:
        st.error("No resumes could be analyzed. Check that each file contains selectable text and try again.")
    if results:
        st.markdown("## Ranked shortlist")
        sort_col, filter_col = st.columns([1, 1])
        with sort_col:
            sort_by = st.selectbox("Sort candidates by", ("Match", "ATS readiness", "Skills"), key="rank-sort")
        with filter_col:
            minimum = st.slider("Minimum match score", 0, 100, 0, key="rank-minimum")
        sort_key = {"Match": "overall", "ATS readiness": "ats", "Skills": "skill"}[sort_by]
        visible = sorted((item for item in results if item["overall"] >= minimum), key=lambda item: (item[sort_key], item["overall"]), reverse=True)
        st.caption(f"Showing {len(visible)} of {len(results)} analyzed resumes")
        if visible:
            rows = [{"Rank": i, "Candidate": result["candidate"], "File": result["filename"], "Match": result["overall"], "ATS readiness": result["ats"], "Skills": result["skill"], "Experience": result["experience"], "Education": result["education"], "Matched skills": ", ".join(result["matched_skills"]), "Missing skills": ", ".join(result["missing_skills"])} for i, result in enumerate(visible, 1)]
            render_table(rows, list(rows[0]), "Ranked candidates")
            csv_file = io.StringIO()
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            st.download_button("Download visible results CSV", csv_file.getvalue().encode("utf-8"), "hireflow-ranking.csv", "text/csv")
            selection = st.selectbox("Inspect a candidate", range(len(visible)), format_func=lambda i: f'{i + 1}. {visible[i]["candidate"]} · {visible[i]["overall"]:.0f} match', key="rank-selected")
            st.markdown(f'### {safe(visible[selection]["candidate"])}')
            evidence(visible[selection])
        else:
            st.info("No candidate meets this threshold. Lower the minimum match score to see the full shortlist.")
    elif not failures:
        st.info("Your shortlist will appear here after you add a job description and candidate resumes.")


def studio_header() -> None:
    st.markdown('''<section class="studio-hero"><div><p class="workspace-label">Applicant workspace</p><h1>Make your experience speak.</h1><p>Build, analyze and tailor your resume to the role. Turn real work into sharper lines, then keep every application moving.</p><div class="studio-path"><b>Build</b><span>→</span><span>Analyze</span><span>→</span><span>Tailor</span><span>→</span><span>Apply</span></div></div><div class="studio-sheet" aria-hidden="true"><small>Original note</small><p class="sheet-before">I used Docker to deploy microservices during my internship.</p><div class="sheet-transition">Resume line ↓</div><strong>Deployed microservices using Docker during an internship.</strong><div class="sheet-highlight">Role requirement: Docker · deployment</div></div></section>''', unsafe_allow_html=True)


def applicant_report(result: dict) -> None:
    checks = result["audit"]
    fixes = sum(item["status"] == "fix" for item in checks)
    reviews = sum(item["status"] == "review" for item in checks)
    st.markdown(
        '<div class="report-strip">'
        + ''.join(f'<div class="report-measure"><span>{safe(label)}</span><strong>{score:.0f} / 100</strong><div class="report-track"><i style="--value:{score:.0f}%"></i></div></div>' for label, score in (("Job match estimate", result["overall"]), ("ATS readiness estimate", result["ats"])))
        + f'<div class="report-count"><b>{fixes}</b> to fix<br><b>{reviews}</b> to review</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("## Your resume check")
    st.markdown('<p class="studio-note">Each finding names what HireFlow could read and the next change to consider. Format checks use the uploaded file; pasted text can only be checked for content and structure.</p>', unsafe_allow_html=True)
    filters = st.columns(2)
    area = filters[0].selectbox("Area", ("All areas", "Format", "Essentials", "Structure", "Content", "Job fit"), key="report-area")
    status = filters[1].selectbox("Priority", ("All findings", "Fix", "Review", "Good"), key="report-priority")
    shown = [item for item in checks if (area == "All areas" or item["area"] == area) and (status == "All findings" or item["status"] == status.lower())]
    if shown:
        labels = {"fix": "Fix", "review": "Review", "good": "Looks good"}
        cards = ''.join(
            f'<div class="audit-row"><div class="audit-meta"><span class="audit-area">{safe(item["area"])}</span><span class="audit-status {safe(item["status"])}">{labels[item["status"]]}</span></div><div class="audit-body"><strong>{safe(item["title"])}</strong><p>{safe(item["detail"])}</p><em>{safe(item["action"])}</em></div></div>'
            for item in shown
        )
        st.markdown(f'<div class="audit-list" role="list" aria-label="Resume checks">{cards}</div>', unsafe_allow_html=True)
    else:
        st.info("No findings in this filter. Choose another area or priority.")
    st.markdown("### Job terms")
    columns = st.columns(2)
    with columns[0]:
        st.markdown("**Already supported by your resume**")
        skill_pills(result["matched_skills"])
    with columns[1]:
        st.markdown("**Not found in the parsed resume**")
        skill_pills(result["missing_skills"], True)
    mapped = applicant_tools.keyword_map(st.session_state["applicant_job"], result["resume_text"])
    if mapped:
        st.markdown("### Keyword map")
        st.markdown('<p class="studio-note">A direct modification changes wording already supported by your resume. A contextual match needs a concrete example; an evidence gap may simply be inapplicable.</p>', unsafe_allow_html=True)
        st.markdown('<div class="keyword-map">' + ''.join(f'<div><strong>{safe(item["skill"])}</strong><span class="keyword-status">{safe(item["status"])}</span><p>{safe(item["detail"])}</p></div>' for item in mapped) + '</div>', unsafe_allow_html=True)
    with st.expander("See scoring and parsing details"):
        render_table([{"Factor": label, "Score": value, "Weight": f'{result["ats_weights"][label] * 100:.0f}%'} for label, value in result["ats_factors"].items()], ["Factor", "Score", "Weight"], "ATS readiness factors")
        st.caption("This is a transparent estimate of readable content and job fit. Employers use different systems and criteria.")
        st.markdown("**Parsed sections**")
        for title, lines in result["sections"].items():
            st.markdown(f"**{title}:** {safe(' · '.join(lines[:2]) or 'Empty section')}")
    st.button("Review suggested changes", on_click=lambda: st.session_state.update({"studio-view": "Improve"}))


def applicant_improve(result: dict) -> None:
    job = st.session_state["applicant_job"]
    decisions = st.session_state.setdefault("edit_decisions", {})
    edits = st.session_state.setdefault("edit_text", {})
    placements = st.session_state.setdefault("edit_placements", {})
    custom = st.session_state.setdefault("custom_suggestions", [])
    suggestions = result["suggestions"] + custom
    approved_text = analysis.apply_decisions(result["resume_text"], suggestions, decisions, edits, placements)

    def decision_for(item: dict) -> str | None:
        explicit = decisions.get(item["id"])
        if explicit:
            return explicit
        if item["kind"] == "add" and item.get("skill") and analysis.skill_in_text(item["skill"], approved_text):
            return "covered"
        return None
    st.markdown("## Rewrite something you actually did")
    st.markdown('<p class="studio-note">Write it as you would tell a friend. HireFlow turns a concrete task into a resume line and keeps only the facts you supplied.</p>', unsafe_allow_html=True)
    with st.form("free_rewrite"):
        casual = st.text_area("Describe a real task in your own words", height=100, placeholder="I used Python and SQL to build a sales dashboard for my team.", key="free-evidence")
        options = ["Match terms automatically"] + result["job_skills"]
        chosen_skill = st.selectbox("Job skill to highlight", options, key="free-skill")
        drafted = st.form_submit_button("Draft a professional line")
    if drafted:
        try:
            draft = resume_coach.rewrite_evidence(casual, job, None if chosen_skill == options[0] else chosen_skill)
            st.session_state["custom_draft"] = {**draft, "source": casual, "skill": None if chosen_skill == options[0] else chosen_skill}
            st.session_state["custom-line"] = draft["bullet"]
            st.session_state["custom-place"] = draft["placement"]
            st.session_state["custom-confirm"] = False
        except ValueError as exc:
            st.session_state.pop("custom_draft", None)
            st.warning(str(exc))
    draft = st.session_state.get("custom_draft")
    if draft:
        compare = st.columns(2, gap="large")
        with compare[0]:
            st.markdown('<div class="draft-label">Your words</div>', unsafe_allow_html=True)
            st.code(draft["source"], language=None)
        with compare[1]:
            st.markdown('<div class="draft-label">Resume wording</div>', unsafe_allow_html=True)
            proposed = st.text_area("Edit the drafted line", key="custom-line", height=100)
        place = st.selectbox("Place this line in", ("Experience", "Projects"), key="custom-place")
        st.caption(draft["note"])
        if draft["job_terms"]:
            st.caption("Job terms supported by this example: " + ", ".join(draft["job_terms"]))
        confirmed = st.checkbox("I confirm this line describes work I actually did", key="custom-confirm")
        valid = bool(proposed.strip()) and confirmed and (not draft["skill"] or analysis.skill_in_text(draft["skill"], proposed))
        if draft["skill"] and proposed.strip() and not analysis.skill_in_text(draft["skill"], proposed):
            st.warning(f'Keep {draft["skill"]} in the line to address this job requirement.')
        controls = st.columns(2)
        if controls[0].button("Add line to my resume", disabled=not valid, use_container_width=True):
            if any(edits.get(item["id"], "").strip() == proposed.strip() for item in custom):
                st.warning("This line is already in your approved changes.")
            else:
                identity = "custom-" + str(st.session_state.get("custom_counter", 0) + 1)
                st.session_state["custom_counter"] = st.session_state.get("custom_counter", 0) + 1
                custom.append({"id": identity, "kind": "add", "category": "Your draft", "placement": place, "skill": draft["skill"], "source": draft["source"], "reason": "A line drafted from your confirmed example."})
                decisions[identity] = "accepted"
                edits[identity] = proposed
                placements[identity] = place
                st.session_state.pop("custom_draft", None)
                st.rerun()
        if controls[1].button("Discard draft", use_container_width=True):
            st.session_state.pop("custom_draft", None)
            st.rerun()
    st.markdown('<div class="studio-divider"></div>', unsafe_allow_html=True)
    st.markdown("## Recommendations for this job")
    st.markdown('<p class="studio-note">Existing lines are reworded only when the change is supported by your resume. For a missing skill, supply a real example and choose where it belongs.</p>', unsafe_allow_html=True)
    if applicant_tools.ai_enabled():
        st.caption("AI is enabled. Select the button to send this job description and resume to the configured OpenAI API for extra line suggestions. You approve every edit.")
        if st.button("Generate additional AI suggestions", use_container_width=False):
            excluded = {item["line_index"] for item in suggestions if item["kind"] == "replace"}
            with st.spinner("Looking for additional job-specific edits…"):
                extra = applicant_tools.ai_tailoring_suggestions(job, result["resume_text"], excluded)
            if extra:
                custom.extend(extra)
                st.success(f"Added {len(extra)} suggestions for review below.")
                st.rerun()
            else:
                st.info("No additional supported line edits were found. You can still revise the final resume directly.")
    suggestions = result["suggestions"] + custom
    total = len(suggestions)
    reviewed = sum(decision_for(item) is not None for item in suggestions)
    st.progress(round(reviewed / total * 100) if total else 100)
    st.caption(f"{reviewed} of {total} decisions made")
    status = st.selectbox("Show recommendations", ("Needs review", "Accepted", "Covered", "Rejected", "All"), key="review-filter")
    status_value = {"Needs review": None, "Accepted": "accepted", "Covered": "covered", "Rejected": "rejected"}.get(status)
    visible = [item for item in suggestions if status == "All" or decision_for(item) == status_value]
    if not visible:
        st.info("No recommendations in this view. Choose another status or draft a line above.")
    for suggestion in visible:
        identity = suggestion["id"]
        decision = decision_for(suggestion)
        is_add = suggestion["kind"] == "add"
        title = f'{suggestion.get("category", "Evidence gap")} · {suggestion.get("skill") or placements.get(identity, "resume line")}' if is_add else f'{suggestion["category"]} · line {suggestion["line_index"] + 1}'
        with st.expander(f'{title} · {decision or "Review needed"}'):
            st.caption(suggestion["reason"])
            valid = False
            proposed = edits.get(identity, "")
            if is_add and not decision and suggestion.get("skill"):
                with st.form(f"draft-form-{identity}"):
                    evidence_text = st.text_area(f'What did you do with {suggestion["skill"]}?', key=f"evidence-{identity}", height=95, placeholder=f'I used {suggestion["skill"]} to complete a specific task or project.')
                    make_draft = st.form_submit_button("Rewrite my example")
                if make_draft:
                    try:
                        new_draft = resume_coach.rewrite_evidence(evidence_text, job, suggestion["skill"])
                        st.session_state[f"draft-{identity}"] = {**new_draft, "source": evidence_text}
                        st.session_state[f"edit-{identity}"] = new_draft["bullet"]
                        st.session_state[f"place-{identity}"] = new_draft["placement"]
                        st.session_state[f"attest-{identity}"] = False
                    except ValueError as exc:
                        st.warning(str(exc))
                current_draft = st.session_state.get(f"draft-{identity}")
                if current_draft:
                    st.markdown("**Professional resume line**")
                    proposed = st.text_area("Edit this line", key=f"edit-{identity}", height=90)
                    place = st.selectbox("Place under", ("Experience", "Projects"), key=f"place-{identity}")
                    placements[identity] = place
                    st.caption(current_draft["note"])
                    confirmed = st.checkbox("I confirm this describes work I actually did", key=f"attest-{identity}")
                    valid = bool(proposed.strip()) and analysis.skill_in_text(suggestion["skill"], proposed) and confirmed and current_draft["source"] == evidence_text
                    if current_draft["source"] != evidence_text:
                        st.warning("Your example changed. Select Rewrite my example again before accepting.")
                    elif proposed.strip() and not analysis.skill_in_text(suggestion["skill"], proposed):
                        st.warning(f'Keep {suggestion["skill"]} in the line to address this job requirement.')
                else:
                    st.info("Describe a specific task, then select Rewrite my example to see a proposed line.")
            elif is_add and not decision:
                st.caption("Your original example: " + suggestion.get("source", ""))
                edit_key = f"edit-{identity}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = proposed
                proposed = st.text_area("Edit this line", key=edit_key, height=90)
                place_key = f"place-{identity}"
                if place_key not in st.session_state:
                    st.session_state[place_key] = placements.get(identity, suggestion.get("placement", "Experience"))
                placements[identity] = st.selectbox("Place under", ("Experience", "Projects"), key=place_key)
                confirmed = st.checkbox("I confirm this describes work I actually did", key=f"attest-{identity}")
                valid = bool(proposed.strip()) and confirmed and (not suggestion.get("skill") or analysis.skill_in_text(suggestion["skill"], proposed))
            elif decision == "covered":
                st.success("This job skill is already supported by an accepted line in your draft. Review that line under Accepted if you want to change it.")
            elif is_add:
                st.code(proposed, language=None)
                st.caption("Placed under " + placements.get(identity, suggestion.get("placement", "Experience")) + ".")
            else:
                st.markdown("**Current line**")
                st.code(suggestion["before"], language=None)
                if not decision:
                    edit_key = f"edit-{identity}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = edits.get(identity, suggestion["after"])
                    proposed = st.text_area("Proposed wording", key=edit_key, height=90)
                    valid = bool(proposed.strip()) and proposed.strip() != suggestion["before"].strip()
                else:
                    st.markdown("**Approved wording**" if decision == "accepted" else "**Rejected wording**")
                    st.code(proposed or suggestion["after"], language=None)
            if not decision:
                edits[identity] = proposed
                if valid:
                    baseline_decisions = {key: value for key, value in decisions.items() if key != identity}
                    before = analysis.apply_decisions(result["resume_text"], suggestions, baseline_decisions, edits, placements)
                    after = analysis.apply_decisions(result["resume_text"], suggestions, {**baseline_decisions, identity: "accepted"}, edits, placements)
                    before_score, after_score = analysis.estimate_ats(job, before), analysis.estimate_ats(job, after)
                    delta = round(after_score - before_score, 1)
                    st.caption(f'Estimated ATS readiness with this edit: {before_score:.1f} → {after_score:.1f} ({delta:+.1f}). Scores are estimates.')
                controls = st.columns(2)
                if controls[0].button("Accept change", key=f"accept-{identity}", disabled=not valid, use_container_width=True):
                    decisions[identity] = "accepted"
                    st.rerun()
                if controls[1].button("Reject change", key=f"reject-{identity}", use_container_width=True):
                    decisions[identity] = "rejected"
                    st.rerun()
            elif decision != "covered" and st.button("Undo decision", key=f"undo-{identity}"):
                decisions.pop(identity, None)
                st.rerun()
    with st.expander("See every parsed line"):
        render_table(result["line_reviews"], ["line", "text", "assessment", "reason"], "Line review")


def applicant_final(result: dict) -> None:
    suggestions = result["suggestions"] + st.session_state.get("custom_suggestions", [])
    approved = analysis.apply_decisions(result["resume_text"], suggestions, st.session_state.get("edit_decisions", {}), st.session_state.get("edit_text", {}), st.session_state.get("edit_placements", {}))
    if "pending_final_text" in st.session_state:
        st.session_state["final-editor"] = st.session_state.pop("pending_final_text")
        st.session_state["final_source"] = approved
    if st.session_state.get("final_source") != approved:
        if st.session_state.get("final_source") and st.session_state.get("final-editor") != st.session_state["final_source"]:
            st.session_state["pending_approved"] = approved
        else:
            st.session_state["final-editor"] = approved
            st.session_state["final_source"] = approved
            st.session_state.pop("pending_approved", None)
    st.markdown("## Your tailored resume")
    st.markdown('<p class="studio-note">Accepted bullets sit inside Experience or Projects. Make any final wording changes here, then choose a clean, single-column export.</p>', unsafe_allow_html=True)
    if st.session_state.get("pending_approved"):
        st.warning("You have manual final edits and new approved changes. The editor still has your manual version. Select Use latest approved changes to replace it with the newly approved version.")

    def use_approved() -> None:
        st.session_state["final-editor"] = approved
        st.session_state["final_source"] = approved
        st.session_state.pop("pending_approved", None)

    if st.session_state.get("pending_approved"):
        st.button("Use latest approved changes", on_click=use_approved)
    final_text = st.text_area("Edit the final resume", key="final-editor", height=420)
    st.button("Reset to approved changes", on_click=use_approved)
    if len(final_text.split()) < 8:
        st.error("Add at least eight words to the final resume before exporting.")
        return
    current = analysis.estimate_ats(st.session_state["applicant_job"], final_text)
    st.caption(f'Estimated ATS readiness for this draft: {current:.1f}/100 · {sum(value == "accepted" for value in st.session_state.get("edit_decisions", {}).values())} accepted changes')
    template = st.radio("Export layout", ("Contemporary", "Classic"), horizontal=True, key="resume-template", help="Both layouts use one text column and selectable content.")
    with st.expander("Format and section order"):
        st.caption("Adjust the exported document. These settings affect the DOCX and PDF, while your editable text stays intact.")
        sizes = st.columns(2)
        body_size = sizes[0].slider("Body text size (pt)", 9.0, 12.0, 10.5, 0.5, key="format-body-size")
        heading_size = sizes[1].slider("Heading size (pt)", 10.0, 15.0, 10.5, 0.5, key="format-heading-size")
        spacing = st.slider("Line spacing", 1.0, 1.5, 1.15, 0.05, key="format-line-spacing")
        margin = st.slider("Page margin (in)", 0.55, 1.1, 0.78, 0.01, key="format-margin")
        found_sections = [name for name in analysis._sections(final_text) if name != "Header"]
        current_order = st.session_state.get("resume-section-order", [])
        if set(current_order) != set(found_sections) or len(current_order) != len(found_sections):
            current_order = found_sections[:]
            st.session_state["resume-section-order"] = current_order
        if len(current_order) > 1:
            st.caption("Section order: " + " → ".join(current_order))
            selected_section = st.selectbox("Move a section", current_order, key="format-selected-section")
            shift = st.columns(2)
            for col, label, step in ((shift[0], "Move up", -1), (shift[1], "Move down", 1)):
                position = current_order.index(selected_section)
                if col.button(label, key=f"format-move-{step}", disabled=not 0 <= position + step < len(current_order), use_container_width=True):
                    changed_order = current_order[:]
                    changed_order[position], changed_order[position + step] = changed_order[position + step], changed_order[position]
                    st.session_state["resume-section-order"] = changed_order
                    st.session_state["pending_final_text"] = applicant_tools.reorder_sections(final_text, changed_order)
                    st.rerun()
    format_options = {"body_size": body_size, "heading_size": heading_size, "line_spacing": spacing, "margin": margin}
    preview_sections = analysis._sections(final_text)
    preview_name = next((line for line in final_text.splitlines() if line.strip()), "Your name")
    preview_summary = " ".join(preview_sections.get("Summary", preview_sections.get("Profile", [])))[:165] or "Your strongest, supported experience appears here."
    st.markdown(
        f'<div class="template-preview {safe(template.lower())}" aria-label="Preview of the selected {safe(template)} resume layout">'
        f'<span class="template-eyebrow">{safe(template)} · single column</span><h3>{safe(preview_name)}</h3>'
        f'<div class="template-rule"></div><strong>PROFESSIONAL SUMMARY</strong><p>{safe(preview_summary)}</p>'
        '<strong>EXPERIENCE</strong><div class="template-lines"><i></i><i></i><i></i></div></div>', unsafe_allow_html=True,
    )
    downloads = st.columns(3)
    try:
        downloads[0].download_button("Download DOCX", analysis.export_docx(final_text, template, format_options), "hireflow-tailored-resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
    except Exception:
        LOGGER.exception("DOCX export failed")
        downloads[0].error("DOCX export is unavailable. Install requirements-app.txt and retry.")
    try:
        downloads[1].download_button("Download PDF", analysis.export_pdf(final_text, template, format_options), "hireflow-tailored-resume.pdf", "application/pdf", use_container_width=True)
    except Exception:
        LOGGER.exception("PDF export failed")
        downloads[1].error("PDF export is unavailable. Install requirements-app.txt and retry.")
    downloads[2].download_button("Download TXT", final_text.encode("utf-8"), "hireflow-tailored-resume.txt", "text/plain", use_container_width=True)
    with st.expander("Save as a new resume version"):
        with st.form("save_final_version"):
            version_name = st.text_input("Version name", value=(st.session_state.get("resume-name") or "My resume") + " · Tailored")
            target_role = st.text_input("Target role", value=st.session_state.get("target-role", ""))
            save_version = st.form_submit_button("Save this version", use_container_width=True)
        if save_version:
            try:
                identity = accounts.save_resume_version(st.session_state["auth_user"]["username"], version_name, final_text, target_role, template, st.session_state.get("resume-version-id"))
                st.session_state["resume-version-id"] = identity
                st.session_state["resume-name"] = version_name.strip()
                st.success("Saved. Find this version under Start → Use a saved version.")
            except ValueError as exc:
                st.error(str(exc))
    st.caption("Review the downloaded file before applying. HireFlow cannot guarantee how a particular employer scores or reviews a resume.")


def applicant_start(user: dict) -> None:
    st.markdown("## Start a resume")
    st.markdown('<p class="studio-note">Bring an existing document, create one from scratch, or return to a version you saved. Each version is private to your account.</p>', unsafe_allow_html=True)
    versions = accounts.list_resume_versions(user["username"])
    source = st.radio("Starting point", ("Import a resume", "Build from scratch", "Use a saved version"), horizontal=True, key="resume-source")
    if source == "Import a resume":
        with st.form("resume_import"):
            cols = st.columns(2)
            name = cols[0].text_input("Resume name", placeholder="My base resume")
            target = cols[1].text_input("Target role", placeholder="Data analyst")
            template = st.radio("Choose a template", ("Contemporary", "Classic"), horizontal=True)
            pasted = st.text_area("Paste your resume", height=170, placeholder="Your name, contact details, summary, skills and experience")
            uploaded = st.file_uploader("Or upload a PDF, DOCX, TXT or Markdown resume", type=list(analysis.SUPPORTED_FILES))
            submit = st.form_submit_button("Continue to resume analysis", use_container_width=True)
        if submit:
            try:
                resume = analysis.extract_document(uploaded.name, uploaded.getvalue()) if uploaded else pasted.strip()
                identity = accounts.save_resume_version(user["username"], name, resume, target, template)
                st.session_state.update({"resume-version-id": identity, "resume-name": name.strip(), "target-role": target.strip(), "resume-template": template, "applicant-resume-text": resume, "resume-analysis-text": resume, "resume-analysis-editor": resume, "resume-source-text": resume, "resume-source-filename": uploaded.name if uploaded else "Pasted text", "resume-source-data": uploaded.getvalue() if uploaded else None, "next-applicant-tool": "Resume analysis"})
                st.session_state.pop("resume-health-score", None)
                st.session_state.pop("resume-guided-draft", None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    elif source == "Build from scratch":
        applicant_build()
    elif versions:
        options = {version["id"]: version for version in versions}
        chosen = st.selectbox("Saved resumes", list(options), format_func=lambda identity: f'{options[identity]["name"]} · {options[identity]["target_role"] or "General"} · {options[identity]["template"]}')
        version = options[chosen]
        st.caption(f'{len(version["resume_text"].split())} words · saved {version["created_at"][:10]}')
        with st.expander("Preview saved content"):
            st.code(version["resume_text"][:5000], language=None)
        actions = st.columns(2)
        if actions[0].button("Open this resume", use_container_width=True):
            st.session_state.update({"resume-version-id": chosen, "resume-name": version["name"], "target-role": version["target_role"], "resume-template": version["template"], "applicant-resume-text": version["resume_text"], "resume-analysis-text": version["resume_text"], "resume-analysis-editor": version["resume_text"], "resume-source-text": version["resume_text"], "resume-source-filename": "Saved text", "resume-source-data": None, "next-applicant-tool": "Resume analysis"})
            st.session_state.pop("resume-health-score", None)
            st.session_state.pop("resume-guided-draft", None)
            st.rerun()
        if actions[1].button("Duplicate this resume", use_container_width=True):
            try:
                copy_name = version["name"] + " · Copy"
                identity = accounts.save_resume_version(user["username"], copy_name, version["resume_text"], version["target_role"], version["template"], chosen)
                st.session_state.update({"resume-version-id": identity, "resume-name": copy_name, "target-role": version["target_role"], "resume-template": version["template"], "applicant-resume-text": version["resume_text"], "resume-analysis-text": version["resume_text"], "resume-analysis-editor": version["resume_text"], "resume-source-text": version["resume_text"], "resume-source-filename": "Saved text", "resume-source-data": None, "next-applicant-tool": "Resume analysis"})
                st.session_state.pop("resume-health-score", None)
                st.session_state.pop("resume-guided-draft", None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("No saved resumes yet. Import one or build a new resume to get started.")


def applicant_resume_analysis() -> None:
    if "resume-analysis-pending" in st.session_state:
        updated = st.session_state.pop("resume-analysis-pending")
        st.session_state["resume-analysis-editor"] = updated
        st.session_state["resume-analysis-text"] = updated
    if "resume-analysis-editor" not in st.session_state:
        st.session_state["resume-analysis-editor"] = st.session_state.get("resume-analysis-text") or st.session_state.get("applicant-resume-text", "")
    st.markdown("## Resume analysis")
    st.markdown('<p class="studio-note">Start with the resume itself. Check completeness, structure, evidence and original-file layout, then rescore before tailoring it to a job.</p>', unsafe_allow_html=True)
    text = st.text_area("Edit your resume", height=310, key="resume-analysis-editor")
    st.session_state["resume-analysis-text"] = text
    if len(text.split()) < 8:
        st.info("Import or build a resume first, then come back here for a section-by-section check.")
        return
    original_file = text.strip() == st.session_state.get("resume-source-text", "").strip()
    try:
        report = applicant_tools.resume_health(text, st.session_state.get("resume-source-filename", "Pasted text") if original_file else "Edited text", st.session_state.get("resume-source-data") if original_file else None)
    except ValueError as exc:
        st.error(str(exc))
        return
    previous = st.session_state.get("resume-health-score")
    st.markdown(f'<div class="health-score"><span>RESUME READINESS</span><strong>{report["score"]}<small> / 100</small></strong><p>HireFlow estimate · based on the checks below</p></div>', unsafe_allow_html=True)
    metrics = st.columns(4)
    for col, (area, score) in zip(metrics, report["areas"].items()):
        col.metric(area, f"{score}/100")
    if st.button("Rescore this resume", key="resume-rescore"):
        st.session_state["resume-health-score"] = report["score"]
        if previous is None:
            st.success(f"Baseline recorded at {report['score']}/100.")
        else:
            st.success(f"Rescored: {previous} → {report['score']} ({report['score'] - previous:+d}).")
    st.markdown("### Section-by-section feedback")
    for item in report["checks"]:
        with st.expander(f'{item["area"]} · {item["title"]} · {item["status"].title()}'):
            st.write(item["detail"])
            st.caption(item["action"])
    st.markdown("### Guided line improvement")
    st.markdown('<p class="studio-note">Choose an existing line or add a real example. Explain the task in your own words; HireFlow drafts a professional line for your approval.</p>', unsafe_allow_html=True)
    candidates = [(index, line.strip()) for index, line in enumerate(text.splitlines()) if len(line.split()) >= 6 and not analysis.section_heading(line) and not analysis._contact(line)["email"]]
    with st.form("resume-guided-fix"):
        action = st.radio("Change type", ("Improve an existing line", "Add a real example"), horizontal=True)
        selected = st.selectbox("Line to improve", candidates, format_func=lambda item: f'Line {item[0] + 1}: {item[1][:90]}', disabled=action != "Improve an existing line" or not candidates) if candidates else None
        evidence = st.text_area("What did you actually do?", height=90, placeholder="I used Python and SQL to build a weekly dashboard for the sales team.")
        make = st.form_submit_button("Draft a change", use_container_width=True)
    if make:
        try:
            draft = resume_coach.rewrite_evidence(evidence, st.session_state.get("target-role", ""))
            st.session_state["resume-guided-draft"] = {**draft, "before": selected[1] if selected and action == "Improve an existing line" else "", "line_index": selected[0] if selected and action == "Improve an existing line" else -1}
            st.session_state["resume-guided-editor"] = draft["bullet"]
        except ValueError as exc:
            st.error(str(exc))
    draft = st.session_state.get("resume-guided-draft")
    if draft:
        if draft["before"]:
            st.caption("Current line")
            st.code(draft["before"], language=None)
        proposed = st.text_area("Proposed line", key="resume-guided-editor", height=85)
        st.caption("Place under " + draft["placement"] + ". " + draft["note"])
        confirmed = st.checkbox("I confirm this change describes work I actually did", key="resume-guided-confirm")
        actions = st.columns(2)
        if actions[0].button("Accept this change", disabled=not confirmed or not proposed.strip(), use_container_width=True):
            if draft["line_index"] >= 0:
                suggestion = {"id": "guided", "kind": "replace", "line_index": draft["line_index"], "after": proposed}
            else:
                suggestion = {"id": "guided", "kind": "add", "placement": draft["placement"]}
            revised = analysis.apply_decisions(text, [suggestion], {"guided": "accepted"}, {"guided": proposed}, {"guided": draft["placement"]})
            st.session_state["resume-analysis-pending"] = revised
            st.session_state.pop("resume-guided-draft", None)
            st.session_state.pop("resume-guided-confirm", None)
            st.rerun()
        if actions[1].button("Reject this change", use_container_width=True):
            st.session_state.pop("resume-guided-draft", None)
            st.session_state.pop("resume-guided-confirm", None)
            st.rerun()
    if st.button("Tailor this resume to a job  ↗", key="from-health-to-tailor", use_container_width=True):
        st.session_state["applicant-resume-text"] = text
        st.session_state["applicant-upload-version"] = st.session_state.get("applicant-upload-version", 0) + 1
        st.session_state["next-applicant-tool"] = "Analyze & tailor"
        st.rerun()


def applicant_analyze() -> None:
    upload_version = st.session_state.get("applicant-upload-version", 0)
    with st.form("applicant_input"):
        inputs = st.columns(2, gap="large")
        with inputs[0]:
            job_text = st.text_area("Job description", height=165, placeholder="Paste the job description here.", key="applicant-job-text")
            job_file = st.file_uploader("Or upload the job description", type=list(analysis.SUPPORTED_FILES), key=f"applicant-job-upload-{upload_version}")
        with inputs[1]:
            resume_text = st.text_area("Your current resume", height=165, placeholder="Paste your resume here.", key="applicant-resume-text")
            resume_file = st.file_uploader("Or upload your resume", type=list(analysis.SUPPORTED_FILES), key=f"applicant-resume-upload-{upload_version}")
        submitted = st.form_submit_button("Analyze my resume", use_container_width=True)
    if submitted:
        st.session_state.pop("applicant_result", None)
        for key in list(st.session_state):
            if key.startswith(("edit-", "attest-", "evidence-", "draft-", "place-", "custom-", "final-", "free-")):
                del st.session_state[key]
        for key in ("custom_draft", "custom_counter", "final_source", "pending_approved", "cover-letter-editor", "cover-source"):
            st.session_state.pop(key, None)
        st.session_state.pop("coach-history", None)
        st.session_state["review-filter"] = "Needs review"
        st.session_state["studio-view"] = "Report"
        st.session_state["report-area"] = "All areas"
        st.session_state["report-priority"] = "All findings"
        try:
            job = analysis.extract_document(job_file.name, job_file.getvalue()) if job_file else job_text.strip()
            resume = analysis.extract_document(resume_file.name, resume_file.getvalue()) if resume_file else resume_text.strip()
            with st.spinner("Checking the content, structure and job match…"):
                result = analysis.analyse(job, resume, resume_file.name if resume_file else "Your resume")
                result["audit"] = resume_coach.audit_resume(job, resume, result, resume_file.name if resume_file else "Pasted text", resume_file.getvalue() if resume_file else None)
            st.session_state["applicant_result"] = result
            st.session_state["applicant_job"] = job
            st.session_state["edit_decisions"] = {}
            st.session_state["edit_text"] = {}
            st.session_state["edit_placements"] = {}
            st.session_state["custom_suggestions"] = []
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            LOGGER.exception("Applicant analysis failed")
            st.error("Resume analysis could not finish. Check both documents and app dependencies, then try again.")
    result = st.session_state.get("applicant_result")
    if not result:
        st.info("Add the job description and your resume to see a detailed check and build a tailored version.")
        return
    view = st.radio("Resume studio view", ("Report", "Improve", "Final resume"), horizontal=True, key="studio-view")
    if view == "Report":
        applicant_report(result)
    elif view == "Improve":
        applicant_improve(result)
    else:
        applicant_final(result)


def applicant_build() -> None:
    st.markdown("## Build your resume")
    st.markdown('<p class="studio-note">Start from a clean, readable structure. Write only work you can explain; HireFlow will arrange the sections for a single-column export.</p>', unsafe_allow_html=True)
    with st.form("resume_builder"):
        version = st.columns(2, gap="large")
        resume_name = version[0].text_input("Resume name", key="builder-resume-name", placeholder="My base resume")
        target_role = version[1].text_input("Target role", key="builder-target-role", placeholder="Data analyst")
        identity = st.columns(2, gap="large")
        name = identity[0].text_input("Full name", key="builder-name")
        email = identity[1].text_input("Contact email", key="builder-email")
        contact = st.columns(3)
        phone = contact[0].text_input("Phone", key="builder-phone")
        location = contact[1].text_input("Location", key="builder-location")
        link = contact[2].text_input("Portfolio or LinkedIn", key="builder-link")
        summary = st.text_area("Professional summary", height=100, key="builder-summary", help="A short, factual introduction. Tailor it after you add the job description.")
        skills = st.text_area("Skills", height=75, key="builder-skills", placeholder="Python, SQL, stakeholder reporting")
        experience = st.text_area("Experience", height=160, key="builder-experience", placeholder="Role · Company · Dates\n- Describe what you did and the result.")
        projects = st.text_area("Projects", height=120, key="builder-projects", placeholder="Project name · Dates\n- Describe the work and tools.")
        education = st.text_area("Education", height=80, key="builder-education")
        certifications = st.text_area("Certifications", height=65, key="builder-certifications")
        built = st.form_submit_button("Build resume", use_container_width=True)
    if built:
        try:
            fields = locals()
            text = applicant_tools.build_resume({key: fields[key] for key in applicant_tools.BUILDER_FIELDS})
            identity = accounts.save_resume_version(st.session_state["auth_user"]["username"], resume_name, text, target_role)
            st.session_state["built-resume"] = text
            st.session_state["built-resume-editor"] = text
            st.session_state["resume-version-id"] = identity
            st.session_state["resume-name"] = resume_name.strip()
            st.session_state["target-role"] = target_role.strip()
            st.success("Your resume draft is ready. Review it below, then move it to analysis when you are ready.")
        except ValueError as exc:
            st.error(str(exc))
    draft = st.session_state.get("built-resume")
    if draft:
        st.markdown("### Resume draft")
        edited = st.text_area("Edit your structured resume", value=draft, height=360, key="built-resume-editor")
        controls = st.columns(2)
        if controls[0].button("Use in analysis", use_container_width=True):
            st.session_state["applicant-resume-text"] = edited
            st.session_state["resume-analysis-text"] = edited
            st.session_state["resume-analysis-editor"] = edited
            st.session_state["resume-source-text"] = edited
            st.session_state["resume-source-data"] = None
            st.session_state["resume-source-filename"] = "Built text"
            st.session_state["applicant-upload-version"] = st.session_state.get("applicant-upload-version", 0) + 1
            st.session_state["next-applicant-tool"] = "Resume analysis"
            st.rerun()
        controls[1].download_button("Download TXT", edited.encode("utf-8"), "hireflow-resume-draft.txt", "text/plain", use_container_width=True)


def applicant_coach() -> None:
    st.markdown("## Resume coach")
    st.markdown('<p class="studio-note">Ask about a section, a job requirement, or a specific line. Guidance uses the documents in this workspace. Concrete rewrites stay in Improve for your approval.</p>', unsafe_allow_html=True)
    result = st.session_state.get("applicant_result")
    if not result:
        st.info("Analyze a job description and resume first so the coach can use your actual evidence.")
        return
    if applicant_tools.ai_enabled():
        st.caption("AI is enabled by the server administrator. The job description, resume and your question are sent to the configured OpenAI API for each answer. Review all claims.")
    prompts = st.columns(3)
    question = None
    for col, label, prompt in zip(prompts, ("Improve my summary", "Find missing skills", "Check my format"), ("How should I improve my summary?", "Which skills or keywords are missing for this job?", "What should I change about the format or template?")):
        if col.button(label, use_container_width=True):
            question = prompt
    history = st.session_state.setdefault("coach-history", [])
    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["text"])
            if item.get("source"):
                st.caption(item["source"])
    typed = st.chat_input("Ask about this resume and job description")
    if typed:
        question = typed
    if question:
        history.append({"role": "user", "text": question})
        try:
            with st.spinner("Reviewing your documents…"):
                answer, source = applicant_tools.coach_reply(question, st.session_state["applicant_job"], result["resume_text"], result)
            history.append({"role": "assistant", "text": answer, "source": source})
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))


def applicant_cover() -> None:
    st.markdown("## Cover letter studio")
    st.markdown('<p class="studio-note">Draft a letter from the job description and the experience already in your resume. Edit it before downloading or saving it with an application.</p>', unsafe_allow_html=True)
    job = st.session_state.get("applicant_job") or st.session_state.get("applicant-job-text", "")
    result = st.session_state.get("applicant_result")
    resume = st.session_state.get("final-editor") or (result["resume_text"] if result else st.session_state.get("applicant-resume-text", ""))
    if applicant_tools.ai_enabled():
        st.caption("AI is enabled by the server administrator. The job description and resume are sent to the configured OpenAI API when you draft a letter. Review all claims.")
    with st.form("cover_letter_form"):
        cols = st.columns(2)
        company = cols[0].text_input("Company", key="cover-company")
        role = cols[1].text_input("Role", key="cover-role")
        st.caption("Uses the job description and resume currently in Analyze & tailor.")
        make = st.form_submit_button("Draft cover letter", use_container_width=True)
    if make:
        try:
            with st.spinner("Drafting from your supplied evidence…"):
                letter, source = applicant_tools.cover_letter(job, resume, company, role)
            st.session_state["cover-letter-editor"] = letter
            st.session_state["cover-source"] = source
            st.success("Draft created. Read each claim and personalize the letter before sending.")
        except ValueError as exc:
            st.error(str(exc))
    if st.session_state.get("cover-letter-editor"):
        letter = st.text_area("Edit your cover letter", key="cover-letter-editor", height=390)
        st.caption(st.session_state.get("cover-source", ""))
        columns = st.columns(3)
        columns[0].download_button("Download TXT", letter.encode("utf-8"), "hireflow-cover-letter.txt", "text/plain", use_container_width=True)
        try:
            columns[1].download_button("Download DOCX", applicant_tools.export_letter_docx(letter), "hireflow-cover-letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            columns[2].download_button("Download PDF", applicant_tools.export_letter_pdf(letter), "hireflow-cover-letter.pdf", "application/pdf", use_container_width=True)
        except Exception:
            LOGGER.exception("Cover letter export failed")
            st.error("Document export is unavailable. Install requirements-app.txt and retry.")


def applicant_applications(user: dict) -> None:
    st.markdown("## Application tracker")
    st.markdown('<p class="studio-note">Keep the roles you are actively applying for, the documents you tailored, and your next step in one private workspace.</p>', unsafe_allow_html=True)
    projects = accounts.list_projects(user["username"])
    counts = {status: sum(project["status"] == status for project in projects) for status in accounts.PROJECT_STATUSES}
    st.markdown('<div class="tracker-strip">' + ''.join(f'<div><strong>{counts[status]}</strong><span>{safe(status)}</span></div>' for status in ("Preparing", "Applied", "Interviewing", "Offer")) + '</div>', unsafe_allow_html=True)
    index = {project["id"]: project for project in projects}
    if "tracker-next-select" in st.session_state:
        st.session_state["tracker-select"] = st.session_state.pop("tracker-next-select")
    selection = st.selectbox("Application", [None] + list(index), format_func=lambda item: "New application" if item is None else f'{index[item]["company"]} · {index[item]["role"]} · {index[item]["status"]}', key="tracker-select")
    current = index.get(selection) if selection else None
    job_default = st.session_state.get("applicant_job") or st.session_state.get("applicant-job-text", "")
    result = st.session_state.get("applicant_result")
    resume_default = st.session_state.get("final-editor") or (result["resume_text"] if result else st.session_state.get("applicant-resume-text", ""))
    if selection is None and (job_default or resume_default):
        if st.button("Fill from current studio", use_container_width=False):
            st.session_state["tracker-job-new"] = job_default
            st.session_state["tracker-resume-new"] = resume_default
            st.session_state["tracker-letter-new"] = st.session_state.get("cover-letter-editor", "")
    form_key = selection or "new"
    defaults = {
        "company": current["company"] if current else st.session_state.get("cover-company", ""),
        "role": current["role"] if current else st.session_state.get("cover-role", ""),
        "status": current["status"] if current else "Preparing",
        "notes": current["notes"] if current else "",
        "job": current["job_text"] if current else job_default,
        "resume": current["resume_text"] if current else resume_default,
        "letter": current["cover_letter"] if current else st.session_state.get("cover-letter-editor", ""),
    }
    for field, value in defaults.items():
        st.session_state.setdefault(f"tracker-{field}-{form_key}", value)
    with st.form("tracker-form"):
        cols = st.columns(2)
        company = cols[0].text_input("Company", key=f"tracker-company-{form_key}")
        role = cols[1].text_input("Role", key=f"tracker-role-{form_key}")
        status = st.selectbox("Status", accounts.PROJECT_STATUSES, key=f"tracker-status-{form_key}")
        notes = st.text_area("Notes and next step", height=90, key=f"tracker-notes-{form_key}")
        with st.expander("Documents saved with this application"):
            saved_job = st.text_area("Job description", height=120, key=f"tracker-job-{form_key}")
            saved_resume = st.text_area("Tailored resume", height=150, key=f"tracker-resume-{form_key}")
            saved_letter = st.text_area("Cover letter", height=120, key=f"tracker-letter-{form_key}")
        saved = st.form_submit_button("Save application", use_container_width=True)
    if saved:
        try:
            identity = accounts.save_project(user["username"], company, role, status, saved_job, saved_resume, saved_letter, notes, selection)
            st.session_state["tracker-next-select"] = identity
            st.success("Application saved to your private workspace.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if current:
        controls = st.columns(2)
        if controls[0].button("Open documents in studio", use_container_width=True):
            st.session_state["applicant-job-text"] = current["job_text"]
            st.session_state["applicant-resume-text"] = current["resume_text"]
            st.session_state["applicant-upload-version"] = st.session_state.get("applicant-upload-version", 0) + 1
            st.session_state["next-applicant-tool"] = "Analyze & tailor"
            st.session_state.pop("applicant_result", None)
            st.rerun()
        with controls[1].popover("Delete application", use_container_width=True):
            st.warning("This permanently removes the saved application and its documents.")
            if st.button("Confirm delete", key="tracker-delete-confirm", use_container_width=True):
                accounts.delete_project(user["username"], current["id"])
                st.session_state["tracker-next-select"] = None
                st.rerun()


def applicant() -> None:
    studio_header()
    if "next-applicant-tool" in st.session_state:
        st.session_state["applicant-tool"] = st.session_state.pop("next-applicant-tool")
    tool = st.radio("Applicant tools", ("Start", "Resume analysis", "Analyze & tailor", "Build", "Coach", "Cover letter", "Applications"), horizontal=True, key="applicant-tool")
    st.markdown('<div class="studio-divider"></div>', unsafe_allow_html=True)
    if tool == "Start":
        applicant_start(st.session_state["auth_user"])
    elif tool == "Resume analysis":
        applicant_resume_analysis()
    elif tool == "Analyze & tailor":
        applicant_analyze()
    elif tool == "Build":
        applicant_build()
    elif tool == "Coach":
        applicant_coach()
    elif tool == "Cover letter":
        applicant_cover()
    else:
        applicant_applications(st.session_state["auth_user"])


def main() -> None:
    authenticated, _ = auth.session_status(st.session_state)
    if not authenticated:
        if st.session_state.get("public_view") == "auth":
            login()
        else:
            landing()
        return
    user = st.session_state["auth_user"]
    mode = st.session_state.get("active_mode")
    if mode not in user.get("modes", ()):
        st.session_state["active_mode"] = None
        choose_mode(user); return
    styles()
    account_bar(user, mode)
    if mode == "recruiter":
        recruiter()
    elif mode == "applicant":
        applicant()


if __name__ == "__main__":
    main()
