import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, type HTMLMotionProps } from 'motion/react'
import { api, download, type Report, type User } from './api'
import LiquidMark from './LiquidMark'
import WorkspaceAtmosphere from './WorkspaceAtmosphere'

export function Brand({ light = false }: { light?: boolean }) {
  return <Link to="/" className={`brand ${light ? 'brand-light' : ''}`} aria-label="HireFlow home">Hire<span>Flow</span><LiquidMark className="brand-symbol" /></Link>
}

export function Button({ children, busy, className = '', ...props }: HTMLMotionProps<'button'> & { busy?: boolean }) {
  return <motion.button {...props} whileTap={{rotateX:4,y:2}} transition={{duration:.16}} className={`button ${className}`} disabled={busy || props.disabled} aria-busy={busy}><span className="button-content">{busy ? <><span className="spinner" aria-hidden="true" /> Working…</> : children as ReactNode}</span></motion.button>
}

export function Notice({ message, kind = 'info' }: { message: string; kind?: 'info' | 'error' | 'success' }) {
  return message ? <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{message}</div> : null
}

export function FileField({ label, onFile, multiple = false, files = [] }: { label: string; onFile: (files: File[]) => void; multiple?: boolean; files?: File[] }) {
  const [dragging, setDragging] = useState(false)
  return <label className={`file-field ${dragging?'dragging':''} ${files.length?'has-files':''}`} onDragOver={event=>{event.preventDefault();setDragging(true)}} onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node))setDragging(false)}} onDrop={event=>{event.preventDefault();setDragging(false);onFile(Array.from(event.dataTransfer.files).slice(0,multiple?40:1))}}><span className="field-label">{label}</span><input type="file" accept=".pdf,.docx,.txt,.md" multiple={multiple} onChange={event => {onFile(Array.from(event.target.files || []));event.currentTarget.value=''}} /><span className="file-drop"><motion.b aria-hidden="true" animate={{rotate:dragging?45:0,y:dragging?-4:0}} transition={{type:'spring',stiffness:360,damping:25}}>↗</motion.b><span>{files.length ? files.map(file => file.name).join(', ') : multiple ? 'Choose CVs or drop a batch' : 'Choose or drop a PDF, DOCX, TXT or MD file'}</span><small>{files.length ? `${files.length} ${files.length===1?'file':'files'} ready · select to replace` : multiple ? 'Up to 40 files · 10 MB each · 80 MB total' : '10 MB maximum · scanned PDFs supported'}</small></span></label>
}

export function InputSignal({ text, label, target = 80 }: { text: string; label: string; target?: number }) {
  const words = text.trim().split(/\s+/).filter(Boolean).length
  const progress = Math.min(1, words / target)
  return <div className="input-signal"><div><span><i aria-hidden="true" /> {label}</span><strong>{words} {words===1?'word':'words'}</strong></div><div className="input-signal-track" aria-hidden="true"><motion.i animate={{scaleX:progress}} transition={{type:'spring',stiffness:170,damping:25}} /></div><small>{words ? 'Your document is being prepared for analysis.' : 'Start typing or upload a document.'}</small></div>
}

export function Score({ label, value, detail }: { label: string; value: number; detail?: string }) {
  return <div className="score"><div className="score-top"><span>{label}</span><strong>{Math.round(value)}<small>/100</small></strong></div><div className="score-track"><motion.i initial={{scaleX:0}} animate={{scaleX:Math.max(0,Math.min(1,value/100))}} transition={{duration:.7,ease:[.22,1,.36,1]}} /></div>{detail && <small>{detail}</small>}</div>
}

export function Pills({ items, missing = false }: { items: string[]; missing?: boolean }) {
  return items.length ? <div className="pills">{items.map(item => <span className={missing ? 'pill pill-missing' : 'pill'} key={item}>{item}</span>)}</div> : <p className="muted small">None identified in the supplied text.</p>
}

export function ReportDetail({ result, applicant = false }: { result: Report; applicant?: boolean }) {
  return <div className="report-detail">
    <p className="score-method">Scoring v{result.scoring_version || '2.0'} · {result.semantic_method} · Evidence-based estimate</p>
    <div className="score-grid"><Score label="Job match estimate" value={result.overall} detail={result.semantic_method} /><Score label="ATS readiness estimate" value={result.ats} detail="HireFlow estimate, not an employer score" /><Score label="Skill overlap" value={result.skill} /></div>
    <p className="report-summary">{result.summary}</p>
    <div className="split-report"><section><h3>Evidence in both documents</h3><Pills items={result.matched_skills} /></section><section><h3>Requested, not found</h3><Pills items={result.missing_skills} missing /></section></div>
    {applicant && result.audit && <section className="report-section"><div className="section-head"><p className="eyebrow">DOCUMENT CHECK</p><h3>What the resume needs</h3></div><div className="audit-list">{result.audit.map((check, i) => <div className="audit-item" key={`${check.title}-${i}`}><span className={`audit-dot ${check.status}`} /><div><small>{check.area} / {check.status}</small><strong>{check.title}</strong><p>{check.detail}</p><em>{check.action}</em></div></div>)}</div></section>}
    {applicant && result.keyword_map && <section className="report-section"><div className="section-head"><p className="eyebrow">ROLE LANGUAGE</p><h3>Keyword context</h3></div><div className="keyword-list">{result.keyword_map.map(item => <div key={item.skill}><strong>{item.skill}</strong><span>{item.status}</span><p>{item.detail}</p></div>)}</div></section>}
    <div className="split-report report-section"><section><h3>How the scores were built</h3><div className="factor-list">{Object.entries(result.ats_factors).map(([name, value]) => <div key={name}><span>{name}</span><b>{Math.round(value)}</b></div>)}</div></section><section><h3>Parsed resume</h3><p className="small muted">{result.word_count} words · {result.headings.join(', ') || 'No standard headings found'}</p><p className="small muted">{result.contact.email || 'Email not found'} · {result.contact.phone || 'Phone not found'}</p><details><summary>Show parsed sections</summary>{Object.entries(result.sections).map(([name, lines]) => <div key={name} className="parsed-section"><b>{name}</b><pre>{lines.join('\n')}</pre></div>)}</details></section></div>
  </div>
}

export function Shell({ user, onUser, children, title, subtitle }: { user: User; onUser: (user: User | null) => void; children: ReactNode; title: string; subtitle: string }) {
  const navigate = useNavigate()
  const [menu, setMenu] = useState(false)
  const [editing, setEditing] = useState(false)
  const [displayName, setDisplayName] = useState(user.display_name)
  const [profileError, setProfileError] = useState('')
  const [saving, setSaving] = useState(false)
  const [switching, setSwitching] = useState('')
  const [switchError, setSwitchError] = useState('')
  const [removing, setRemoving] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [accountBusy, setAccountBusy] = useState(false)
  const [accountNotice, setAccountNotice] = useState('')
  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setProfileError(''); setSaving(true)
    try { onUser(await api<User>('/profile',{display_name:displayName},'PATCH')); setEditing(false) }
    catch (error) { setProfileError((error as Error).message) }
    finally { setSaving(false) }
  }
  async function logout() {
    setProfileError('')
    try { await api('/auth/logout', {}); onUser(null); navigate('/auth') }
    catch (error) { setProfileError((error as Error).message) }
  }
  async function exportAccount() {
    setProfileError(''); setAccountNotice(''); setAccountBusy(true)
    try { await download('/account/export', {}); setAccountNotice('Your account data was downloaded.') }
    catch (error) { setProfileError((error as Error).message) }
    finally { setAccountBusy(false) }
  }
  async function deleteAccount(event: FormEvent) {
    event.preventDefault(); setProfileError(''); setAccountBusy(true)
    try {
      await api('/account/delete', {password:deletePassword,confirmation:deleteConfirmation})
      onUser(null); window.location.replace('/')
    } catch (error) { setProfileError((error as Error).message) }
    finally { setAccountBusy(false) }
  }
  async function switchMode(mode: 'recruiter' | 'applicant') {
    if (user.mode === mode || switching) return
    setSwitching(mode); setSwitchError('')
    try { onUser(await api<User>('/mode', { mode })); window.requestAnimationFrame(() => navigate(`/${mode}`)) }
    catch (error) { setSwitchError((error as Error).message) }
    finally { setSwitching('') }
  }
  return <div className="app-shell"><aside className="app-rail"><Brand /><div className="rail-label">DOCUMENT INTELLIGENCE</div><nav aria-label="Workspace navigation">{user.modes.includes('recruiter') && <button type="button" className={user.mode === 'recruiter' ? 'rail-link active' : 'rail-link'} aria-current={user.mode === 'recruiter' ? 'page' : undefined} aria-busy={switching === 'recruiter'} disabled={Boolean(switching)} onClick={() => switchMode('recruiter')}>↗ <span>Recruiter</span></button>}{user.modes.includes('applicant') && <button type="button" className={user.mode === 'applicant' ? 'rail-link active' : 'rail-link'} aria-current={user.mode === 'applicant' ? 'page' : undefined} aria-busy={switching === 'applicant'} disabled={Boolean(switching)} onClick={() => switchMode('applicant')}>✳ <span>Applicant</span></button>}</nav><div className="rail-foot"><div className="rail-line" /><span>Evidence first.<br />Decision yours.</span></div></aside>
    <div className="app-body"><header className="app-top"><div className="app-breadcrumb"><span>WORKSPACE</span><b>/</b><strong>{user.mode === 'recruiter' ? 'Candidate intelligence' : 'Resume studio'}</strong></div><div className="profile-wrap"><button className="profile-trigger" aria-expanded={menu} aria-haspopup="true" onClick={() => setMenu(!menu)}><span className="avatar">{user.display_name.split(' ').map(part=>part[0]).slice(0,2).join('').toUpperCase()}</span><span>{user.display_name}</span><b>⌄</b></button>{menu && <div className="profile-menu"><div className="profile-meta"><strong>{user.display_name}</strong><small>{user.email}</small><small>Access: {user.modes.join(' + ')}</small></div>{editing ? <form className="profile-edit" onSubmit={saveProfile}><label className="field-label" htmlFor="profile-name">Display name</label><input id="profile-name" autoFocus required minLength={2} maxLength={80} value={displayName} onChange={event=>setDisplayName(event.target.value)} /><Notice message={profileError} kind="error" /><div className="action-row"><Button type="submit" busy={saving}>Save</Button><button type="button" onClick={()=>{setEditing(false);setProfileError('');setDisplayName(user.display_name)}}>Cancel</button></div></form> : <button onClick={()=>setEditing(true)}>Edit profile →</button>}<button onClick={() => { setMenu(false); navigate('/choose') }}>Switch workspace →</button><button onClick={exportAccount} disabled={accountBusy}>Download my data ↓</button>{removing ? <form className="profile-delete" onSubmit={deleteAccount}><p>Delete this account, its saved resumes and application records permanently.</p><label className="field-label" htmlFor="delete-password">Current password</label><input id="delete-password" type="password" autoComplete="current-password" value={deletePassword} onChange={event=>setDeletePassword(event.target.value)} required /><label className="field-label" htmlFor="delete-confirmation">Type DELETE to confirm</label><input id="delete-confirmation" value={deleteConfirmation} onChange={event=>setDeleteConfirmation(event.target.value)} required /><div className="action-row"><Button type="submit" busy={accountBusy} disabled={!deletePassword || deleteConfirmation !== 'DELETE'}>Delete account</Button><button type="button" onClick={()=>{setRemoving(false);setDeletePassword('');setDeleteConfirmation('');setProfileError('')}}>Cancel</button></div></form> : <button className="profile-danger" onClick={()=>{setRemoving(true);setEditing(false);setProfileError('')}}>Delete account →</button>}<Notice message={profileError} kind="error" /><Notice message={accountNotice} kind="success" /><button onClick={logout}>Sign out ↗</button></div>}</div></header><main className="app-main"><Notice message={switchError} kind="error" /><motion.div key={title} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.35,ease:[.22,1,.36,1]}} className="workspace-intro"><div className="workspace-intro-copy"><p className="eyebrow">{subtitle}</p><h1>{title}</h1><p className="workspace-intro-note">{user.mode === 'recruiter' ? 'A clearer shortlist begins with the evidence.' : 'Your next draft, grounded in your real work.'}</p></div><WorkspaceAtmosphere mode={user.mode === 'recruiter' ? 'recruiter' : 'applicant'} /></motion.div>{children}</main></div>
  </div>
}

export function csvDownload(name: string, rows: Record<string,unknown>[]) {
  if (!rows.length) return
  const columns = Object.keys(rows[0])
  const cell = (value: unknown) => { const safe = String(value ?? '').replace(/^[\s]*[=+\-@]/, "'$&"); return `"${safe.replaceAll('"','""')}"` }
  const csv = [columns.map(cell).join(','), ...rows.map(row => columns.map(column => cell(row[column])).join(','))].join('\r\n')
  const link = document.createElement('a'); const url = URL.createObjectURL(new Blob([csv], {type:'text/csv;charset=utf-8'}))
  link.href = url; link.download = name; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
