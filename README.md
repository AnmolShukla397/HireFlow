# HireFlow

HireFlow is a document intelligence workspace for both sides of a hiring decision. Recruiters compare a job description with a batch of candidate CVs and inspect each ranking. Applicants check and tailor their own resume against a supplied job description, review each proposed edit, and export the version they approve. HireFlow does not publish or search for jobs.

## Run the new web application

Use Python 3.12 and Node.js 22 or newer. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-web.txt
cd web
npm ci
npm run build
cd ..
python -m uvicorn web_api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The built React site and FastAPI backend are served from the same origin, so sign-in and document actions work without extra configuration. The project archive includes `web/dist`; on a fresh checkout, build it using the commands above. `requirements-web.txt` uses the document engine without Streamlit or PyArrow, avoiding the earlier PyArrow/NumPy table error.

The `web/.npmrc` file places npm's download cache in `web/.npm-cache`, avoiding a root-owned global `~/.npm` cache. The local cache and `node_modules` are excluded from the project archive and Git. Run `npm ci` from inside `web`; then `npm run build` will find the installed TypeScript compiler.

For frontend development, leave the API on port 8000 and run `cd web && npm run dev` in a second terminal. Open the Vite address it prints; `/api` requests proxy to port 8000. Rebuild with `npm run build` before serving the production site from FastAPI.

The original Streamlit entry point remains available for reference: install `requirements-app.txt` and run `streamlit run streamlit_app.py`. The older CLI workflow remains in `main.py` and `requirements.txt`. The React app is the primary interface.

## Accounts and sessions

The home page opens before sign-in. Create an account using a valid email, a password of 8–256 characters, and one or both workspace permissions; both are selected by default. After each sign-in, choose recruiter or applicant mode. The top-right profile menu shows your name, email, permissions, profile editing, workspace switch, and sign out. A mode selection is stored in that browser session, and the API rejects requests to the other mode. Each account's saved applicant drafts and application records remain after sign-out and app restarts.

Accounts, salted PBKDF2-SHA256 password hashes, saved applicant records, and hashed web session tokens live in `data/hireflow.sqlite3`. The same account database is used by both frontends. Saved resume and application content is encrypted before SQLite writes it; existing saved rows are migrated when the app first starts with this version. Local development generates `data/hireflow.key` with restricted permissions. In production, set `HIREFLOW_DATA_KEY` to a Fernet key stored separately from the database (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). Keep that key for backups and restoration: losing it makes saved content unreadable. Older database backups made before migration still contain plaintext. Set `HIREFLOW_DB_PATH` to select another database. Database files and environment secrets are excluded from Git. Session cookies are HttpOnly and SameSite Strict, are Secure over HTTPS, and expire after 30 minutes idle or eight hours total. Failed logins are rate limited per email. Deploy behind HTTPS.

The profile menu can download all saved account data as JSON, delete an individual saved resume, or delete the account and its saved records after password confirmation. Set `HIREFLOW_DATA_RETENTION_DAYS` to a positive integer to purge saved resume versions and applications older than that many days; the default `0` retains them until the user deletes them. Recruiter uploads and unsaved applicant uploads are processed in memory. API requests have an 80 MB total body limit, and each document has a 10 MB limit. Protect database backups and the exported JSON file because they contain personal data.

## Workspaces

**Recruiter.** Paste or upload one job description, upload up to 40 PDF, DOCX, TXT, or Markdown CVs (10 MB each, 80 MB total request), and select **Rank candidates**. Filter and sort the shortlist, inspect matched and missing skills, parsed sections, line evidence and score factors, and export the visible ranking as CSV. Uploaded candidate documents are processed for the current session and are not saved to the account database.

**Applicant.** The seven studio tabs cover importing a resume or opening a saved version; checking document structure and original PDF/DOCX layout; analyzing a resume against a job description; building a resume from supplied facts; asking a document-based coach; drafting an editable cover letter; and recording applications. Analysis provides match and ATS-readiness estimates, gaps, keyword context, and line suggestions. Applicants may reject, accept, or edit each suggestion. New missing-skill lines require a real example and explicit confirmation. Approved lines are placed within Experience or Projects. The final draft supports text editing, section ordering, Contemporary or Classic templates, type size, line spacing, margins, named version saving, and PDF, DOCX, or TXT export. The final editor renders a live preview using the same PDF generator as export; accepted edits are marked in the preview for review, while downloads have clean pages. Cover letters also export to those formats.

English image-only PDF pages are OCRed locally using the bundled `data/tessdata/eng.traineddata`; PDFs are limited to 25 pages and at most eight scanned pages. Faint, rotated, handwritten, or non-English scans may still need a clearer copy. Scores are explainable estimates, not scores from an employer's ATS. The ranking gives 50% weight to text similarity, 30% to recognized skill overlap, 10% to experience evidence, and 10% to education evidence. ATS readiness separately weights skill overlap, contact information, section headings, readable text, keyword context, and action-led lines. The fixed default similarity method is keyword cosine (`HIREFLOW_SIMILARITY_BACKEND=keyword`), reported with scoring version 2.0. The optional cached `all-MiniLM-L6-v2` model runs only when explicitly selected with `HIREFLOW_SIMILARITY_BACKEND=local`; if unavailable, analysis returns a clear error instead of silently changing methods. Extend `data/skills.txt` for additional domain terms. The synthetic benchmark fixture in `tests/fixtures/ranking_benchmark.json` checks ranking consistency; real-world calibration requires labeled resumes and human review. Local resume rewrites are evidence-based but cannot infer achievements or guarantee any hiring outcome. Review final wording and exported layout before use.

Optional generative coaching, cover-letter drafting, and extra tailoring suggestions use a server-side `HIREFLOW_OPENAI_API_KEY`; `HIREFLOW_AI_MODEL` selects the model (default `gpt-5-mini`). Requested document content is sent to the configured API with `store: false`. Without a key, the local document workflows still run. Never put an API key in the browser or repository.

## Interface and architecture

The React and Vite frontend uses Motion for route entrances, control feedback, and scroll-driven changes. React Three Fiber and Three.js render a persistent job brief → resume → decision sculpture with custom paper textures and a liquid shader. Scrolling advances the 3D document; pointer movement and dragging turn it, while keyboard and touch users can use the chapter controls. A new editorial method section leads into the interactive evidence lab, where visitors switch perspectives, spotlight the source of a result, and turn the document rig. Both signed-in workspaces use the same graphite, paper, steel-blue, and warm-metal design system with a physical document preview, live text-entry feedback, responsive upload controls, and a top-right profile menu. The current visual layer is `web/src/cinematic-world.css`, loaded after the earlier styles to preserve the working interface structure. The 3D canvas limits pixel density on small screens, pauses continuous rendering when offscreen or when the browser tab is hidden, and uses on-demand frames for reduced motion. Large liquid marks and the evidence plaque use `@liquidglassjs/react` and `@liquidglassjs/core`. Fonts and textures are served locally; the older Streamlit interface remains available.

`web_api.py` is the FastAPI boundary. It reuses `app/accounts.py`, `app/auth.py`, `app/analysis.py`, `app/applicant_tools.py`, and `app/resume_coach.py` instead of duplicating the analysis logic. `web/src` holds the new views and 3D scene. The original Streamlit application, static assets, console pipeline and analysis modules remain in place.

## Checks

```bash
cd web && npm run build && cd ..
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
cd web && npm run test:e2e
```

The web API tests cover persistent sign-in, selected-mode permissions, applicant analysis and saved records, OCR, PDF annotations, encrypted content, account export/deletion, retention, recruiter ranking, scoring fixtures, and request guards. The browser test uses Playwright with installed Google Chrome and starts an isolated local API database. Set `HIREFLOW_PYTHON` to the Python interpreter with `requirements-dev.txt` installed if `python` on your path points elsewhere. The repository's earlier applicant recommendation tests are included in the full suite.
