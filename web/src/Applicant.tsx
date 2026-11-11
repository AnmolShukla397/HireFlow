import { useEffect, useState, type FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { api, download, previewPdf, readDocument, type Check, type Project, type Report, type Suggestion, type User, type Version } from './api'
import { Button, FileField, InputSignal, Notice, ReportDetail, Score, Shell } from './components'

type Tab = 'Start' | 'Resume check' | 'Analyze & tailor' | 'Build' | 'Coach' | 'Cover letter' | 'Applications'
const tabs: Tab[] = ['Start','Resume check','Analyze & tailor','Build','Coach','Cover letter','Applications']
const fields = ['name','email','phone','location','link','summary','skills','experience','projects','education','certifications'] as const
const statuses = ['Interested','Preparing','Applied','Interviewing','Offer','Closed']

export default function Applicant({ user, onUser }: { user: User; onUser: (user: User | null) => void }) {
  const [tab, setTab] = useState<Tab>('Start')
  const [resume, setResume] = useState('')
  const [job, setJob] = useState('')
  const [resumeFile, setResumeFile] = useState<File[]>([])
  const [jobFile, setJobFile] = useState<File[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [health, setHealth] = useState<{score:number;areas:Record<string,number>;checks:Check[]} | null>(null)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [decisions, setDecisions] = useState<Record<string,string>>({})
  const [edits, setEdits] = useState<Record<string,string>>({})
  const [placements, setPlacements] = useState<Record<string,string>>({})
  const [evidence, setEvidence] = useState<Record<string,string>>({})
  const [attested, setAttested] = useState<Record<string,boolean>>({})
  const [finalText, setFinalText] = useState('')
  const [template, setTemplate] = useState('Contemporary')
  const [formatOptions, setFormatOptions] = useState<Record<string,number>>({body_size:10.5,heading_size:10.5,line_spacing:1.15,margin:.78})
  const [versionName, setVersionName] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [versions, setVersions] = useState<Version[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [builder, setBuilder] = useState<Record<string,string>>({})
  const [question, setQuestion] = useState('')
  const [answers, setAnswers] = useState<{question:string;answer:string;source:string}[]>([])
  const [letterInfo, setLetterInfo] = useState({company:'',role:''})
  const [letter, setLetter] = useState('')
  const [letterSource, setLetterSource] = useState('')
  const [project, setProject] = useState({id:'',company:'',role:'',status:'Interested',notes:''})
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function refreshSaved() {
    const [saved, applications] = await Promise.all([api<Version[]>('/applicant/versions'),api<Project[]>('/applicant/projects')])
    setVersions(saved); setProjects(applications)
  }
  useEffect(() => { refreshSaved().catch(failure=>setError((failure as Error).message)) }, [])

  async function action(name: string, work: () => Promise<void>) {
    setBusy(name); setError(''); setNotice('')
    try { await work() } catch (failure) { setError((failure as Error).message) } finally { setBusy('') }
  }

  async function upload(files: File[], kind: 'resume'|'job') {
    if (kind === 'resume') setResumeFile(files); else setJobFile(files)
    if (!files[0]) return
    await action('Reading file', async () => {
      const text = await readDocument(files[0])
      if (kind === 'resume') { setResume(text); setFinalText(text); setReport(null); setHealth(null) }
      else { setJob(text); setReport(null) }
      setNotice(`${files[0].name} is ready.`)
    })
  }
  function editResume(value: string) { setResume(value); setResumeFile([]); setReport(null); setHealth(null); setFinalText(value) }
  function editJob(value: string) { setJob(value); setJobFile([]); setReport(null) }

  async function checkResume() {
    await action('Checking resume', async () => {
      let result: typeof health
      if (resumeFile[0]) { const form = new FormData(); form.append('text',resume); form.append('resume_file',resumeFile[0]); result = await api<typeof health>('/applicant/health-file',form) }
      else result = await api<typeof health>('/applicant/health',{text:resume,filename:'Pasted text'})
      setHealth(result); setNotice('Resume check complete.')
    })
  }
  async function analyze() {
    await action('Analyzing resume', async () => {
      const form = new FormData(); form.append('job_text',job); form.append('resume_text',resume)
      if (jobFile[0]) form.append('job_file',jobFile[0]); if (resumeFile[0]) form.append('resume_file',resumeFile[0])
      const result = await api<Report>('/applicant/tailor',form)
      setReport(result); setSuggestions(result.suggestions); setDecisions({}); setEdits({}); setEvidence({}); setAttested({}); setFinalText(result.resume_text)
      setNotice('Your role-specific analysis is ready. Review each suggestion before adding it to the final draft.')
    })
  }
  async function draftLine(item: Suggestion) {
    await action('Drafting line', async () => {
      const draft = await api<{bullet:string;placement:string;note:string}>('/applicant/rewrite',{evidence:evidence[item.id] || '',job_text:job,required_skill:item.skill || null})
      setEdits(current=>({...current,[item.id]:draft.bullet})); setPlacements(current=>({...current,[item.id]:draft.placement})); setNotice(draft.note)
    })
  }
  async function buildFinal() {
    await action('Building final draft', async () => {
      const data = await api<{text:string}>('/applicant/apply',{original:report?.resume_text || resume,suggestions,decisions,edits,placements})
      setFinalText(data.text); setNotice('Approved edits are placed in their resume sections. Review the final text before export.')
    })
  }
  async function saveVersion() {
    await action('Saving version', async () => {
      await api('/applicant/versions',{name:versionName,resume_text:finalText || resume,target_role:targetRole,template})
      await refreshSaved(); setVersionName(''); setNotice('Resume version saved to your account.')
    })
  }
  async function removeVersion(id: string) {
    if (!window.confirm('Delete this saved resume version?')) return
    await action('Deleting version', async () => { await api(`/applicant/versions/${id}`, undefined, 'DELETE'); await refreshSaved(); setNotice('Saved version deleted.') })
  }
  async function exportResume(format: string) {
    await action('Exporting resume', async () => { await download('/applicant/export',{text:finalText || resume,format,template,options:formatOptions}); setNotice(`${format.toUpperCase()} downloaded.`) })
  }
  async function reorderFinal(order: string[]) {
    await action('Reordering sections', async () => { const data = await api<{text:string}>('/applicant/reorder',{text:finalText,order}); setFinalText(data.text); setNotice('Resume sections reordered. Review the preview before export.') })
  }
  async function makeBuilder(event: FormEvent) {
    event.preventDefault()
    await action('Building resume', async () => { const data = await api<{text:string}>('/applicant/build',builder); setResume(data.text); setFinalText(data.text); setResumeFile([]); setTab('Resume check'); setNotice('Your resume draft is ready for a document check.') })
  }
  async function askCoach(event: FormEvent) {
    event.preventDefault()
    await action('Asking coach', async () => { const answer = await api<{answer:string;source:string}>('/applicant/coach',{question,job_text:job,resume_text:resume}); setAnswers(current=>[...current,{question, ...answer}]); setQuestion('') })
  }
  async function makeLetter(event: FormEvent) {
    event.preventDefault()
    await action('Drafting letter', async () => { const data = await api<{text:string;source:string}>('/applicant/cover',{job_text:job,resume_text:resume,...letterInfo}); setLetter(data.text); setLetterSource(data.source); setNotice('Cover letter drafted from your supplied documents. Review every paragraph.') })
  }
  async function saveProject(event: FormEvent) {
    event.preventDefault()
    await action('Saving application', async () => { await api('/applicant/projects',{...project,id:project.id || null,job_text:job,resume_text:finalText || resume,cover_letter:letter}); await refreshSaved(); setProject({id:'',company:'',role:'',status:'Interested',notes:''}); setNotice('Application saved to your account.') })
  }
  async function removeProject(id: string) {
    if (!window.confirm('Remove this application from your account?')) return
    await action('Removing application', async () => { await api(`/applicant/projects/${id}`,undefined,'DELETE'); await refreshSaved(); setNotice('Application removed.') })
  }
  async function extraSuggestions() {
    await action('Finding more suggestions', async () => {
      const data = await api<{suggestions:Suggestion[]}>('/applicant/ai-suggestions',{job_text:job,resume_text:resume,excluded_lines:suggestions.filter(item=>item.kind==='replace').map(item=>item.line_index)})
      setSuggestions(current=>[...current,...data.suggestions]); setNotice(data.suggestions.length ? `${data.suggestions.length} extra edits are ready for review.` : 'No additional evidence-backed edits were found.')
    })
  }

  const acceptedLines = suggestions.filter(item=>decisions[item.id]==='accepted').map(item=>edits[item.id] ?? item.after ?? '').filter(Boolean)

  return <Shell user={user} onUser={onUser} title="Make your experience speak." subtitle="APPLICANT / RESUME STUDIO">
    <p className="workspace-lede">Build the document, compare it with the role, decide which edits are true, then export the version you want to send.</p>
    <div className="studio-tabs" role="tablist" aria-label="Applicant tools">{tabs.map(item=><button key={item} type="button" role="tab" aria-selected={tab===item} className={tab===item?'active':''} onClick={()=>{setTab(item);setError('');setNotice('')}}>{item}{tab===item&&<motion.i layoutId="studio-tab" />}</button>)}</div>
    <Notice message={error} kind="error" /><Notice message={notice} kind="success" />
    <AnimatePresence mode="wait"><motion.div key={tab} className="tab-content" initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-7}} transition={{duration:.2}}>
      {tab==='Start' && <><div className="section-head"><p className="eyebrow">01 / YOUR SOURCE MATERIAL</p><h2>Start with what you have.</h2><p>Import a resume, paste text, or open one of your saved versions. The original remains available as you review changes.</p></div><div className="two-panel"><section className="work-panel"><FileField label="Import your resume" files={resumeFile} onFile={files=>upload(files,'resume')} /><label className="field-label" htmlFor="resume-start">Or paste resume text</label><textarea id="resume-start" rows={13} value={resume} onChange={event=>editResume(event.target.value)} placeholder="Name, contact details, summary, experience, projects, education…" /><div className="panel-foot"><span>{resume.trim().split(/\s+/).filter(Boolean).length} words</span><Button onClick={()=>setTab('Resume check')} disabled={!resume.trim()}>Check this resume ↗</Button></div></section><section className="work-panel"><h3>Saved versions</h3><p className="muted small">Your drafts stay in your account across sign-ins.</p>{versions.length ? <div className="saved-list">{versions.map(version=><div className="version-row" key={version.id}><button onClick={()=>{setResume(version.resume_text);setFinalText(version.resume_text);setTemplate(version.template);setTargetRole(version.target_role);setResumeFile([]);setReport(null);setTab('Resume check');setNotice(`Opened ${version.name}.`)}}><span><strong>{version.name}</strong><small>{version.target_role || 'Untargeted'} · {version.template}</small></span><b>↗</b></button><button className="version-remove" onClick={()=>removeVersion(version.id)} aria-label={`Delete ${version.name} saved version`}>Remove</button></div>)}</div> : <div className="empty-inline">No saved versions yet. Your first draft can start on the left.</div>}</section></div></>}

      {tab==='Resume check' && <><div className="section-head"><p className="eyebrow">02 / DOCUMENT HEALTH</p><h2>See the whole resume clearly.</h2><p>Check structure, essentials, content and original-file format before tailoring it to a role.</p></div><div className="work-panel"><div className="panel-foot"><span>{resume ? `${resume.trim().split(/\s+/).length} words ready` : 'Add a resume in Start first'}</span><Button onClick={checkResume} busy={busy==='Checking resume'} disabled={!resume}>Analyze resume ↗</Button></div></div>{health && <div className="health-layout"><div className="work-panel"><Score label="Resume readiness estimate" value={health.score} /><div className="factor-list">{Object.entries(health.areas).map(([name,value])=><div key={name}><span>{name}</span><b>{value}</b></div>)}</div></div><div className="audit-list">{health.checks.map((check,index)=><div className="audit-item" key={index}><span className={`audit-dot ${check.status}`} /><div><small>{check.area} / {check.status}</small><strong>{check.title}</strong><p>{check.detail}</p><em>{check.action}</em></div></div>)}</div></div>}<GuidedRewrite job={job} resume={resume} onApply={value=>{setResume(value);setFinalText(value);setHealth(null);setNotice('The line is now inside your resume. Run the check again to see the updated result.')}} action={action} /></>}

      {tab==='Analyze & tailor' && <><div className="section-head"><p className="eyebrow">03 / ROLE-SPECIFIC REVIEW</p><h2>Put the role beside the resume.</h2><p>HireFlow scores the match and shows exactly what it found. Every proposed edit waits for your approval.</p></div><div className="two-panel"><section className="work-panel"><label className="field-label" htmlFor="target-job">Target job description</label><textarea id="target-job" value={job} onChange={event=>editJob(event.target.value)} rows={9} placeholder="Paste the role you are applying for…" /><InputSignal text={job} label="TARGET ROLE" /><FileField label="Or upload job description" files={jobFile} onFile={files=>upload(files,'job')} /></section><section className="work-panel"><label className="field-label" htmlFor="target-resume">Your resume</label><textarea id="target-resume" value={resume} onChange={event=>editResume(event.target.value)} rows={9} placeholder="Paste your resume or import it in Start…" /><InputSignal text={resume} label="YOUR EVIDENCE" target={120} /><FileField label="Or upload your resume" files={resumeFile} onFile={files=>upload(files,'resume')} /></section></div><div className="panel-foot analysis-submit"><span>Only supported facts should enter the final draft.</span><Button onClick={analyze} busy={busy==='Analyzing resume'} disabled={!resume || !job}>Analyze my resume ↗</Button></div>
        {report && <><ReportDetail result={report} applicant /><div className="section-head recommendations-head"><p className="eyebrow">DECISION DESK</p><h2>Review the proposed edits.</h2><p>Accept, reject, or rewrite. Missing skills require a real example from your own work.</p></div><div className="suggestion-list">{suggestions.length ? suggestions.map((item,index)=><section className="suggestion" data-decision={decisions[item.id] || undefined} key={item.id}><div className="suggestion-index">{String(index+1).padStart(2,'0')} / {item.category || (item.kind==='add'?'Evidence gap':'Clarity')}</div><p className="suggestion-reason">{item.reason}</p>{item.kind==='replace' ? <div className="before-after"><div><small>CURRENT LINE</small><p>{item.before}</p></div><div><small>PROPOSED WORDING</small><textarea aria-label={`Proposed wording for suggestion ${index+1}`} value={edits[item.id] ?? item.after ?? ''} onChange={event=>setEdits(current=>({...current,[item.id]:event.target.value}))} rows={3} /></div></div> : <div className="evidence-draft"><p className="muted">{item.skill ? `If you really used ${item.skill}, describe a specific task. HireFlow will write a professional line from your example.` : 'Describe real work that supports this role.'}</p><label className="field-label" htmlFor={`evidence-${item.id}`}>Your real example</label><textarea id={`evidence-${item.id}`} rows={3} value={evidence[item.id] || ''} onChange={event=>{setEvidence(current=>({...current,[item.id]:event.target.value}));setEdits(current=>({...current,[item.id]:''}));setAttested(current=>({...current,[item.id]:false}))}} placeholder="I used this skill to build, analyze or improve…" /><Button className="button-quiet" onClick={()=>draftLine(item)} busy={busy==='Drafting line'} disabled={!evidence[item.id]}>Rewrite my example ↗</Button>{edits[item.id] && <><label className="field-label" htmlFor={`draft-${item.id}`}>Professional line, editable</label><textarea id={`draft-${item.id}`} rows={3} value={edits[item.id]} onChange={event=>setEdits(current=>({...current,[item.id]:event.target.value}))} /><label className="check-line"><input type="checkbox" checked={Boolean(attested[item.id])} onChange={event=>setAttested(current=>({...current,[item.id]:event.target.checked}))} /> This describes work I actually did</label><label className="field-label">Place under <select value={placements[item.id] || 'Experience'} onChange={event=>setPlacements(current=>({...current,[item.id]:event.target.value}))}><option>Experience</option><option>Projects</option></select></label></>}</div>}<div className="suggestion-actions"><span className={`decision-label ${decisions[item.id] || ''}`}>{decisions[item.id] || 'Awaiting your decision'}</span><Button className="button-quiet" onClick={()=>setDecisions(current=>({...current,[item.id]:'rejected'}))}>Reject</Button><Button onClick={()=>setDecisions(current=>({...current,[item.id]:'accepted'}))} disabled={item.kind==='add' ? !edits[item.id] || !attested[item.id] || Boolean(item.skill && !edits[item.id].toLowerCase().includes(item.skill.toLowerCase())) : !(edits[item.id] ?? item.after)}>Accept change ↗</Button></div></section>) : <div className="empty-inline">No evidence-backed line changes were found. You can still edit the final resume directly.</div>}</div><div className="panel-foot"><span>{Object.values(decisions).filter(value=>value==='accepted').length} accepted · {Object.values(decisions).filter(value=>value==='rejected').length} rejected</span><div className="action-row"><Button className="button-quiet" onClick={extraSuggestions} busy={busy==='Finding more suggestions'}>Look for more edits</Button><Button onClick={buildFinal} busy={busy==='Building final draft'}>Build final draft ↗</Button></div></div><div className="section-head final-head"><p className="eyebrow">FINAL DOCUMENT</p><h2>The version you will send.</h2><p>Review and edit the assembled resume. Approved lines belong in their sections, not in an appendix.</p></div><FinalEditor text={finalText} onText={setFinalText} template={template} setTemplate={setTemplate} options={formatOptions} setOptions={setFormatOptions} onReorder={reorderFinal} versionName={versionName} setVersionName={setVersionName} targetRole={targetRole} setTargetRole={setTargetRole} onSave={saveVersion} onExport={exportResume} busy={busy} highlights={acceptedLines} /></>}
      </>}

      {tab==='Build' && <><div className="section-head"><p className="eyebrow">04 / BUILD FROM SCRATCH</p><h2>Give your experience a clear structure.</h2><p>Fill what is true. HireFlow assembles a single-column resume you can check, tailor and export.</p></div><form onSubmit={makeBuilder} className="builder-grid">{fields.map(field=><label key={field} className="work-panel"><span className="field-label">{field[0].toUpperCase()+field.slice(1)}</span>{['summary','skills','experience','projects','education','certifications'].includes(field) ? <textarea rows={field==='experience'?5:3} value={builder[field] || ''} onChange={event=>setBuilder(current=>({...current,[field]:event.target.value}))} placeholder={field==='experience'?'Role | Company | Dates, then action-led lines':`Your ${field}…`} /> : <input type={field==='email'?'email':'text'} value={builder[field] || ''} onChange={event=>setBuilder(current=>({...current,[field]:event.target.value}))} placeholder={field==='name'?'Your full name':field==='link'?'LinkedIn or portfolio':field} />}</label>)}<div className="builder-submit"><Button type="submit" busy={busy==='Building resume'}>Build my resume ↗</Button></div></form></>}

      {tab==='Coach' && <><div className="section-head"><p className="eyebrow">05 / RESUME COACH</p><h2>Ask about the evidence.</h2><p>Ask which section to improve, how to describe a task, or whether a missing skill really belongs.</p></div><div className="coach-layout"><div className="coach-thread" aria-live="polite">{answers.length ? answers.map((item,index)=><div key={index} className="coach-turn"><div className="coach-question">{item.question}</div><div className="coach-answer"><span>✳</span><p>{item.answer}<small>{item.source}</small></p></div></div>) : <div className="empty-inline">Your questions and document-based answers will appear here. Start with “What is my resume missing for this job?”</div>}</div><form onSubmit={askCoach} className="coach-form"><label className="field-label" htmlFor="coach-question">Your question</label><textarea id="coach-question" rows={3} value={question} onChange={event=>setQuestion(event.target.value)} placeholder="Which line should I strengthen for this role?" /><Button type="submit" busy={busy==='Asking coach'} disabled={!resume || question.length<6}>Ask HireFlow ↗</Button><small>Uses the resume and job description currently in the studio. External AI is optional and server-configured.</small></form></div></>}

      {tab==='Cover letter' && <><div className="section-head"><p className="eyebrow">06 / COVER LETTER</p><h2>Make the introduction count.</h2><p>Draft from your own resume and the target job. Review and personalize before sending.</p></div><form onSubmit={makeLetter} className="work-panel cover-form"><div className="two-fields"><label><span className="field-label">Company</span><input value={letterInfo.company} onChange={event=>setLetterInfo(current=>({...current,company:event.target.value}))} placeholder="Company name" /></label><label><span className="field-label">Role</span><input value={letterInfo.role} onChange={event=>setLetterInfo(current=>({...current,role:event.target.value}))} placeholder="Role title" /></label></div><div className="panel-foot"><span>Uses the current job description and resume.</span><Button type="submit" busy={busy==='Drafting letter'} disabled={!job || !resume}>Draft cover letter ↗</Button></div></form>{letter && <div className="work-panel letter-editor"><div className="panel-foot"><div><h3>Your draft</h3><small>{letterSource}</small></div><div className="action-row">{['pdf','docx','txt'].map(format=><Button key={format} className="button-quiet" onClick={()=>action('Exporting letter',()=>download('/applicant/letter-export',{text:letter,format}))}>↓ {format.toUpperCase()}</Button>)}</div></div><textarea aria-label="Edit cover letter" value={letter} onChange={event=>setLetter(event.target.value)} rows={17} /></div>}</>}

      {tab==='Applications' && <><div className="section-head"><p className="eyebrow">07 / APPLICATIONS</p><h2>Keep the next move visible.</h2><p>Save the role, the tailored resume and the letter together. Your records stay in your account.</p></div><div className="two-panel"><form onSubmit={saveProject} className="work-panel application-form"><h3>{project.id?'Update application':'Record an application'}</h3><label><span className="field-label">Company</span><input required value={project.company} onChange={event=>setProject(current=>({...current,company:event.target.value}))} /></label><label><span className="field-label">Role</span><input required value={project.role} onChange={event=>setProject(current=>({...current,role:event.target.value}))} /></label><label><span className="field-label">Status</span><select value={project.status} onChange={event=>setProject(current=>({...current,status:event.target.value}))}>{statuses.map(value=><option key={value}>{value}</option>)}</select></label><label><span className="field-label">Notes and next action</span><textarea rows={5} value={project.notes} onChange={event=>setProject(current=>({...current,notes:event.target.value}))} /></label><Button type="submit" busy={busy==='Saving application'}>Save application ↗</Button></form><div className="work-panel"><h3>Saved applications</h3>{projects.length ? <div className="saved-list">{projects.map(item=><div className="project-row" key={item.id}><div><strong>{item.company}</strong><small>{item.role} · {item.status}</small><p>{item.notes || 'No next action recorded.'}</p></div><div className="project-actions"><button onClick={()=>{setProject({id:item.id,company:item.company,role:item.role,status:item.status,notes:item.notes});setJob(item.job_text);setResume(item.resume_text);setFinalText(item.resume_text);setLetter(item.cover_letter);setNotice(`Opened ${item.company}.`)}}>Open</button><button onClick={()=>removeProject(item.id)} aria-label={`Remove ${item.company} application`}>Remove</button></div></div>)}</div> : <div className="empty-inline">Your first saved application will appear here.</div>}</div></div></>}
    </motion.div></AnimatePresence>
  </Shell>
}

function GuidedRewrite({job,resume,onApply,action}: {job:string;resume:string;onApply:(text:string)=>void;action:(name:string,work:()=>Promise<void>)=>Promise<void>}) {
  const [example,setExample] = useState('')
  const [draft,setDraft] = useState<{bullet:string;placement:string;note:string}|null>(null)
  const [confirmed,setConfirmed] = useState(false)
  async function rewrite() { await action('Rewriting example',async()=>{setDraft(await api('/applicant/rewrite',{evidence:example,job_text:job,required_skill:null}));setConfirmed(false)}) }
  async function accept() { if(!draft)return; await action('Adding line',async()=>{const data=await api<{text:string}>('/applicant/apply',{original:resume,suggestions:[{id:'guided',kind:'add',placement:draft.placement}],decisions:{guided:'accepted'},edits:{guided:draft.bullet},placements:{guided:draft.placement}});onApply(data.text);setDraft(null);setExample('');setConfirmed(false)}) }
  return <div className="work-panel guided-panel"><div className="section-head"><p className="eyebrow">TURN A NOTE INTO A LINE</p><h3>Write it casually. Review it professionally.</h3><p>Describe work you actually did. HireFlow rephrases it without adding invented metrics or skills.</p></div><label className="field-label" htmlFor="guided-evidence">Your example</label><textarea id="guided-evidence" rows={3} value={example} onChange={event=>{setExample(event.target.value);setDraft(null)}} placeholder="I used SQL to make a weekly sales report for my team…" /><Button className="button-quiet" onClick={rewrite} disabled={!example.trim()}>Draft professional line ↗</Button>{draft&&<div className="guided-result"><small>{draft.note}</small><textarea aria-label="Edit drafted resume line" rows={2} value={draft.bullet} onChange={event=>setDraft({...draft,bullet:event.target.value})} /><label className="check-line"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)} /> This describes work I actually did</label><div className="action-row"><Button className="button-quiet" onClick={()=>setDraft(null)}>Reject</Button><Button onClick={accept} disabled={!confirmed||!draft.bullet.trim()}>Add to {draft.placement} ↗</Button></div></div>}</div>
}

type FinalEditorProps = {text:string;onText:(value:string)=>void;template:string;setTemplate:(value:string)=>void;options:Record<string,number>;setOptions:(value:Record<string,number>)=>void;onReorder:(order:string[])=>void;versionName:string;setVersionName:(value:string)=>void;targetRole:string;setTargetRole:(value:string)=>void;onSave:()=>void;onExport:(format:string)=>void;busy:string;highlights:string[]}

function FinalEditor({text,onText,template,setTemplate,options,setOptions,onReorder,versionName,setVersionName,targetRole,setTargetRole,onSave,onExport,busy,highlights}:FinalEditorProps) {
  const [pdfUrl,setPdfUrl] = useState('')
  const [previewLoading,setPreviewLoading] = useState(false)
  const [previewError,setPreviewError] = useState('')
  const highlightsKey = highlights.join('\u0000')
  useEffect(() => {
    if (text.trim().split(/\s+/).length < 8) { setPdfUrl(''); setPreviewLoading(false); return }
    const controller = new AbortController()
    let objectUrl = ''
    setPreviewLoading(true); setPreviewError(''); setPdfUrl('')
    const timer = window.setTimeout(async () => {
      try {
        const blob = await previewPdf({text,template,options,highlights},controller.signal)
        if (controller.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setPdfUrl(objectUrl)
      } catch (failure) {
        if (!controller.signal.aborted) {setPreviewError((failure as Error).message);setPdfUrl('')}
      } finally {if (!controller.signal.aborted) setPreviewLoading(false)}
    }, 500)
    return () => {controller.abort();window.clearTimeout(timer);if (objectUrl) URL.revokeObjectURL(objectUrl)}
  }, [text,template,options,highlightsKey])
  const sections = ['Summary','Profile','Skills','Experience','Projects','Education','Certifications']
  const available = sections.filter(section => new RegExp(`^${section}$`, 'im').test(text))
  const [order,setOrder] = useState<string[]>(sections)
  const controls = [
    {key:'body_size',label:'Body size',min:9,max:12,step:.5,unit:'pt'},
    {key:'heading_size',label:'Heading size',min:10,max:15,step:.5,unit:'pt'},
    {key:'line_spacing',label:'Line spacing',min:1,max:1.5,step:.05,unit:'×'},
    {key:'margin',label:'Page margins',min:.55,max:1.1,step:.05,unit:'in'},
  ]
  function move(section:string,direction:number) {
    const current = order.filter(item=>available.includes(item))
    const index = current.indexOf(section)
    const next = index+direction
    if (index<0 || next<0 || next>=current.length) return
    ;[current[index],current[next]]=[current[next],current[index]]
    setOrder([...current,...sections.filter(item=>!current.includes(item))])
    onReorder(current)
  }
  return <div className="two-panel final-layout"><div className="work-panel">
    <div className="two-fields"><label><span className="field-label">Template</span><select value={template} onChange={event=>setTemplate(event.target.value)}><option>Contemporary</option><option>Classic</option></select></label><label><span className="field-label">Target role</span><input value={targetRole} onChange={event=>setTargetRole(event.target.value)} placeholder="Optional" /></label></div>
    <div className="format-grid">{controls.map(control=><label key={control.key}><span className="field-label">{control.label} <b>{options[control.key]} {control.unit}</b></span><input type="range" min={control.min} max={control.max} step={control.step} value={options[control.key]} onChange={event=>setOptions({...options,[control.key]:Number(event.target.value)})} /></label>)}</div>
    {available.length>1 && <div className="section-order"><span className="field-label">Section order</span><p className="muted small">Move sections to put your strongest evidence first.</p>{order.filter(section=>available.includes(section)).map((section,index,array)=><div key={section}><span>{section}</span><button type="button" aria-label={`Move ${section} up`} disabled={index===0 || Boolean(busy)} onClick={()=>move(section,-1)}>↑</button><button type="button" aria-label={`Move ${section} down`} disabled={index===array.length-1 || Boolean(busy)} onClick={()=>move(section,1)}>↓</button></div>)}</div>}
    <label className="field-label" htmlFor="final-resume">Final resume text</label><textarea id="final-resume" value={text} onChange={event=>onText(event.target.value)} rows={20} />
    <div className="two-fields"><label><span className="field-label">Version name</span><input value={versionName} onChange={event=>setVersionName(event.target.value)} placeholder="e.g. Data analyst · November" /></label><Button onClick={onSave} busy={busy==='Saving version'} disabled={!text||!versionName}>Save version ↗</Button></div>
    <div className="action-row export-row">{['pdf','docx','txt'].map(format=><Button key={format} className="button-quiet" onClick={()=>onExport(format)} busy={busy==='Exporting resume'} disabled={!text}>↓ {format.toUpperCase()}</Button>)}</div>
  </div><div className="resume-preview pdf-preview" aria-label="Exported PDF preview"><div className="preview-top"><span>HIREFLOW / PDF LAYOUT</span>{pdfUrl && <a href={pdfUrl} target="_blank" rel="noreferrer">Open full size ↗</a>}</div>{previewLoading && <div className="preview-status" role="status">Rendering your PDF…</div>}{previewError && <div className="preview-status error" role="alert">{previewError}</div>}{pdfUrl ? <iframe className="pdf-preview-frame" title="Actual exported PDF preview" src={`${pdfUrl}#toolbar=0&navpanes=0`} /> : !previewLoading && !previewError ? <div className="preview-status">Add a final resume to see the PDF you will download.</div> : null}{highlights.length > 0 && <details className="preview-edits"><summary>{highlights.length} accepted edit{highlights.length===1?'':'s'} marked for review</summary><p>Copper highlights show approved wording in this preview. The downloaded PDF uses the same layout without review marks.</p></details>}</div></div>
}
