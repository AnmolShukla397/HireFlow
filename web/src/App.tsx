import { lazy, Suspense, useEffect, useLayoutEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import { api, type User } from './api'
import { Brand, Button, Notice } from './components'
import LiquidMark from './LiquidMark'
import InteractionLayer from './InteractionLayer'
import Landing from './Landing'
const Recruiter = lazy(() => import('./Recruiter'))
const Applicant = lazy(() => import('./Applicant'))

function Auth({onUser}:{onUser:(user:User)=>void}) {
  const navigate = useNavigate()
  const [create,setCreate] = useState(new URLSearchParams(window.location.search).has('create'))
  const [email,setEmail] = useState('')
  const [password,setPassword] = useState('')
  const [name,setName] = useState('')
  const [modes,setModes] = useState(['recruiter','applicant'])
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  function toggle(mode:string) { setModes(current=>current.includes(mode)?current.filter(item=>item!==mode):[...current,mode]) }
  async function submit(event:FormEvent) {
    event.preventDefault(); setError('')
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address.');return }
    if(!password || (create && password.length<8)) { setError(create?'Use a password of at least 8 characters.':'Enter your password.');return }
    if(create && (!name.trim() || !modes.length)) { setError('Add your name and choose at least one workspace.');return }
    setBusy(true)
    try { const user=await api<User>(create?'/auth/signup':'/auth/login',create?{email,password,display_name:name,modes}:{email,password}); onUser(user); navigate('/choose') }
    catch(failure) { setError((failure as Error).message) } finally { setBusy(false) }
  }
  return <div className="auth-page"><div className="auth-visual"><Brand light /><div className="auth-liquid-mark" aria-hidden="true"><LiquidMark large /></div><div className="auth-message"><p className="eyebrow">PRIVATE DOCUMENT INTELLIGENCE</p><h1>The work is<br />in the <em>details.</em></h1><p>Read the evidence behind every match. Improve your own resume with changes you can inspect and approve.</p></div><div className="auth-sample"><span>HIREFLOW / A CLOSER LOOK</span><div><b>Job brief</b><p>Build and deploy reliable services with Docker.</p></div><div><b>Resume evidence</b><p>Deployed microservices using Docker during an internship.</p></div><strong>↗ A claim tied to real work</strong></div></div><div className="auth-form-wrap"><Link to="/" className="back-link">← Back to home</Link><div className="auth-form-head"><p className="eyebrow">{create?'CREATE YOUR ACCOUNT':'WELCOME BACK'}</p><h2>{create?'Start with a clearer view.':'Good to see you again.'}</h2><p>{create?'Your documents and saved work belong to your account.':'Sign in to continue your work.'}</p></div><div className="auth-switch" role="tablist"><button role="tab" aria-selected={!create} className={!create?'active':''} onClick={()=>{setCreate(false);setError('')}}>Sign in</button><button role="tab" aria-selected={create} className={create?'active':''} onClick={()=>{setCreate(true);setError('')}}>Create account</button></div><form onSubmit={submit} className="auth-form">{create&&<label><span className="field-label">Full name</span><input autoComplete="name" value={name} onChange={event=>setName(event.target.value)} placeholder="Your full name" required /></label>}<label><span className="field-label">Email address</span><input type="email" autoComplete="email" value={email} onChange={event=>setEmail(event.target.value)} placeholder="name@example.com" required /></label><label><span className="field-label">Password</span><input type="password" autoComplete={create?'new-password':'current-password'} value={password} onChange={event=>setPassword(event.target.value)} placeholder={create?'At least 8 characters':'Your password'} required minLength={create?8:undefined} /></label>{create&&<fieldset><legend className="field-label">Workspace access</legend><label className="check-line"><input type="checkbox" checked={modes.includes('recruiter')} onChange={()=>toggle('recruiter')} /> Recruiter</label><label className="check-line"><input type="checkbox" checked={modes.includes('applicant')} onChange={()=>toggle('applicant')} /> Applicant</label></fieldset>}<Notice message={error} kind="error" /><Button type="submit" busy={busy}>{create?'Create account':'Sign in'} ↗</Button></form><p className="auth-note">Your account uses a salted password hash. Resume files are processed for your current session; saved versions and application records stay in your private account.</p></div></div>
}

function Choose({user,onUser}:{user:User;onUser:(user:User)=>void}) {
  const navigate=useNavigate()
  const [busy,setBusy]=useState('')
  const [error,setError]=useState('')
  async function select(mode:'recruiter'|'applicant') {setBusy(mode);setError('');try {const next=await api<User>('/mode',{mode});onUser(next);navigate(`/${mode}`)}catch(failure){setError((failure as Error).message)}finally{setBusy('')}}
  return <div className="choose-page"><header><Brand /><Link to="/">← Home</Link></header><main><p className="eyebrow">YOUR WORKSPACE / CHOOSE A VIEW</p><h1>{user.display_name.split(' ')[0]}, where are<br />we heading?</h1><p>Two focused workspaces. Bring a job brief to either one and decide what the evidence needs to do.</p><Notice message={error} kind="error" /><div className="choose-grid"><motion.article whileHover={{y:-5,rotateY:-2}} transition={{duration:.24}} className="choose-card"><span>01 / HIRING TEAM</span><h2>Find the<br />strongest fit.</h2><p>Rank a stack of CVs against a job description, then open the details behind each position.</p><div className="choose-path">Job brief <i>→</i> Candidate CVs <i>→</i> Shortlist</div><Button onClick={()=>select('recruiter')} disabled={!user.modes.includes('recruiter')} busy={busy==='recruiter'}>{user.modes.includes('recruiter')?'Enter recruiter mode ↗':'Access not enabled'}</Button></motion.article><motion.article whileHover={{y:-5,rotateY:2}} transition={{duration:.24}} className="choose-card"><span>02 / APPLICANT</span><h2>Make your<br />story sharper.</h2><p>Review your resume against the role, improve supported lines and export the version you approve.</p><div className="choose-path">Job brief <i>→</i> Your resume <i>→</i> Final draft</div><Button onClick={()=>select('applicant')} disabled={!user.modes.includes('applicant')} busy={busy==='applicant'}>{user.modes.includes('applicant')?'Enter applicant mode ↗':'Access not enabled'}</Button></motion.article></div></main></div>
}

export default function App() {
  const navigate=useNavigate()
  const {pathname}=useLocation()
  const [user,setUser]=useState<User|null>(null)
  const [ready,setReady]=useState(false)
  useLayoutEffect(()=>{document.documentElement.classList.add('route-reset');window.scrollTo(0,0);requestAnimationFrame(()=>document.documentElement.classList.remove('route-reset'))},[pathname])
  useEffect(()=>{api<User>('/session').then(setUser).catch(()=>setUser(null)).finally(()=>setReady(true))},[])
  useEffect(()=>{const expired=()=>{setUser(null);navigate('/auth')};window.addEventListener('hireflow:expired',expired);return()=>window.removeEventListener('hireflow:expired',expired)},[navigate])
  if(!ready)return <div className="boot"><Brand /><span className="spinner" /><p>Opening HireFlow…</p></div>
  const workspace=(mode:'recruiter'|'applicant')=>!user?<Navigate to="/auth" replace/>:user.mode!==mode?<Navigate to="/choose" replace/>:<Suspense fallback={<div className="boot"><span className="spinner" /><p>Opening workspace…</p></div>}>{mode==='recruiter'?<Recruiter user={user} onUser={setUser}/>:<Applicant user={user} onUser={setUser}/>}</Suspense>
  return <><InteractionLayer /><AnimatePresence mode="wait"><Routes><Route path="/" element={<Landing user={user} onUser={setUser}/>} /><Route path="/auth" element={user?<Navigate to="/choose" replace/>:<Auth onUser={setUser}/>} /><Route path="/choose" element={user?<Choose user={user} onUser={setUser}/>:<Navigate to="/auth" replace/>} /><Route path="/recruiter" element={workspace('recruiter')} /><Route path="/applicant" element={workspace('applicant')} /><Route path="*" element={<Navigate to="/" replace/>} /></Routes></AnimatePresence></>
}
