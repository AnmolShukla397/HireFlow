import { useMemo, useState, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { api, type Report, type User } from './api'
import { Button, FileField, InputSignal, Notice, ReportDetail, Shell, csvDownload } from './components'

export default function Recruiter({ user, onUser }: { user: User; onUser: (user: User | null) => void }) {
  const [job, setJob] = useState('')
  const [jobFile, setJobFile] = useState<File[]>([])
  const [resumes, setResumes] = useState<File[]>([])
  const [results, setResults] = useState<Report[]>([])
  const [failures, setFailures] = useState<{filename:string;reason:string}[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [sort, setSort] = useState<'overall'|'ats'|'skill'>('overall')
  const [minimum, setMinimum] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const visible = useMemo(() => [...results].filter(row => row.overall >= minimum).sort((a,b) => b[sort]-a[sort] || b.overall-a.overall), [results,sort,minimum])
  const current = visible.find(row => row.filename === selected) || visible[0]

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setResults([]); setFailures([])
    try {
      const form = new FormData(); form.append('job_text', job)
      if (jobFile[0]) form.append('job_file',jobFile[0])
      resumes.forEach(file => form.append('resumes',file))
      const data = await api<{results:Report[];failures:{filename:string;reason:string}[]}>('/recruiter/rank', form)
      setResults(data.results); setFailures(data.failures); setSelected(data.results[0]?.filename || null)
    } catch (failure) { setError((failure as Error).message) } finally { setBusy(false) }
  }

  return <Shell user={user} onUser={onUser} title="Find the strongest fit." subtitle="RECRUITER / CANDIDATE INTELLIGENCE">
    <p className="workspace-lede">One job description. A batch of CVs. A ranked shortlist with the evidence behind each position.</p>
    <form onSubmit={submit} className="work-form recruiter-form"><section><div className="form-index">01 / THE JOB BRIEF</div><h2>What the role asks for</h2><label className="field-label" htmlFor="job-recruiter">Job description</label><textarea id="job-recruiter" value={job} onChange={event=>setJob(event.target.value)} placeholder="Paste the complete job description here…" rows={8} /><InputSignal text={job} label="LIVE BRIEF" /><FileField label="Or upload the job brief" files={jobFile} onFile={setJobFile} /></section><section><div className="form-index">02 / THE CANDIDATE STACK</div><h2>Who might be a match</h2><p className="muted">Upload PDF, DOCX, TXT or Markdown resumes. Each file receives its own score, parsed snapshot and skill evidence.</p><FileField label="Candidate CVs" files={resumes} onFile={setResumes} multiple /><div className="upload-count"><strong>{resumes.length.toString().padStart(2,'0')}</strong><span>resumes ready to review</span></div></section><div className="form-footer"><span>Documents are processed for this session and are not saved to your account.</span><Button type="submit" busy={busy} disabled={!resumes.length || (!job.trim() && !jobFile.length)}>Rank candidates <span aria-hidden="true">↗</span></Button></div></form>
    <Notice message={error} kind="error" />
    {failures.map(item => <Notice key={item.filename} message={`${item.filename}: ${item.reason}`} kind="error" />)}
    {results.length > 0 && <motion.section className="results-section" initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{duration:.42}}><div className="results-head"><div><p className="eyebrow">RANKING COMPLETE</p><h2>Shortlist, with receipts.</h2><p>{visible.length} of {results.length} candidates in view</p></div><Button className="button-quiet" onClick={() => csvDownload('hireflow-ranking.csv', visible.map((row,index)=>({Rank:index+1,Candidate:row.candidate,File:row.filename,Match:row.overall,ATS:row.ats,Skills:row.skill,Matched:row.matched_skills.join('; '),Missing:row.missing_skills.join('; ')})))}>Export CSV ↓</Button></div>
      <div className="filter-bar"><label>Sort by <select value={sort} onChange={event=>setSort(event.target.value as typeof sort)}><option value="overall">Job match</option><option value="ats">ATS readiness</option><option value="skill">Skill overlap</option></select></label><label>Minimum match <input type="range" min="0" max="100" value={minimum} onChange={event=>setMinimum(Number(event.target.value))} /> <b>{minimum}</b></label></div>
      {visible.length ? <div className="ranking-layout"><div className="ranking-list" role="list" aria-label="Ranked candidates">{visible.map((row,index) => <motion.button layout type="button" role="listitem" key={row.filename} className={`candidate-row ${current?.filename===row.filename?'selected':''}`} onClick={()=>setSelected(row.filename)} whileTap={{scale:.99}}><span className="candidate-rank">{String(index+1).padStart(2,'0')}</span><span className="candidate-name"><strong>{row.candidate}</strong><small>{row.filename}</small><span>{row.matched_skills.slice(0,3).join(' · ') || 'No skill overlap found'}</span></span><span className="candidate-score"><strong>{Math.round(row.overall)}</strong><small>MATCH</small></span></motion.button>)}</div><AnimatePresence mode="wait">{current && <motion.div key={current.filename} initial={{opacity:0,x:14}} animate={{opacity:1,x:0}} exit={{opacity:0,x:-8}} transition={{duration:.22}} className="candidate-detail"><p className="eyebrow">CANDIDATE / {current.filename}</p><h3>{current.candidate}</h3><ReportDetail result={current} /></motion.div>}</AnimatePresence></div> : <div className="empty-state">No candidate meets this threshold. Lower the minimum match to see the shortlist.</div>}
    </motion.section>}
    {!results.length && !error && !busy && <div className="empty-state empty-waiting"><span>✳</span><h2>The shortlist starts with evidence.</h2><p>Add a job description and candidate CVs to see detailed ranking here.</p></div>}
  </Shell>
}
