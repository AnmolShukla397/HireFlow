import { useEffect, useRef, useState, type MouseEvent, type PointerEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type User } from './api'

type Mode = 'recruiter' | 'applicant'

export default function ModePortal({ mode, user, onUser }: { mode: Mode; user: User | null; onUser: (user: User) => void }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const frame = useRef<number | null>(null)
  const pending = useRef<{ element: HTMLAnchorElement; x: number; y: number } | null>(null)
  const allowed = !user || user.modes.includes(mode)
  useEffect(() => () => { if (frame.current !== null) cancelAnimationFrame(frame.current) }, [])

  function tilt(event: PointerEvent<HTMLAnchorElement>) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    pending.current = { element: event.currentTarget, x: event.clientX, y: event.clientY }
    if (frame.current !== null) return
    frame.current = requestAnimationFrame(() => {
      frame.current = null
      if (!pending.current) return
      const { element, x: pointerX, y: pointerY } = pending.current
      // Measure the stationary wrapper so the pointer cannot chase a tilted target.
      const rect = (element.parentElement ?? element).getBoundingClientRect()
      const x = (pointerX - rect.left) / rect.width - .5
      const y = (pointerY - rect.top) / rect.height - .5
      element.style.setProperty('--tilt-x', `${(-y * 7).toFixed(2)}deg`)
      element.style.setProperty('--tilt-y', `${(x * 8).toFixed(2)}deg`)
      element.style.setProperty('--shine-x', `${(x + .5) * 100}%`)
      element.style.setProperty('--shine-y', `${(y + .5) * 100}%`)
    })
  }
  function untilt(event: PointerEvent<HTMLAnchorElement>) {
    pending.current = null
    if (frame.current !== null) { cancelAnimationFrame(frame.current); frame.current = null }
    event.currentTarget.style.setProperty('--tilt-x', '0deg')
    event.currentTarget.style.setProperty('--tilt-y', '0deg')
  }
  async function open(event: MouseEvent<HTMLAnchorElement>) {
    if (!user) return
    event.preventDefault()
    if (busy) return
    if (!allowed) { setError('This workspace is not enabled for your account.'); return }
    if (user.mode === mode) { navigate(`/${mode}`); return }
    setBusy(true); setError('')
    try {
      const updated = await api<User>('/mode', { mode })
      onUser(updated)
      window.requestAnimationFrame(() => navigate(`/${mode}`))
    } catch (failure) {
      setError((failure as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const recruiter = mode === 'recruiter'
  return <Link
    to={user ? `/${mode}` : '/auth?create=1'}
    className={`mode-tile mode-tile-${mode} ${!allowed ? 'mode-tile-locked' : ''}`}
    data-cursor={allowed ? 'ENTER' : 'LOCKED'}
    aria-busy={busy}
    aria-label={`${recruiter ? 'Recruiter' : 'Applicant'} mode: ${recruiter ? 'rank candidate CVs' : 'improve your resume'}`}
    onClick={open}
    onPointerMove={tilt}
    onPointerLeave={untilt}
  >
    <span className="mode-index">{recruiter ? '01 / FOR THE HIRING TEAM' : '02 / FOR THE APPLICANT'}<i>↗</i></span>
    <h3>{recruiter ? <>See who fits.<br />See why.</> : <>Make every<br />line count.</>}</h3>
    <p>{recruiter ? 'Compare a job brief with multiple CVs. Inspect the skills and evidence behind every rank.' : 'Test your resume against the role. Review supported improvements and export your strongest draft.'}</p>
    <div className={`mode-art mode-art-${mode}`} aria-hidden="true">
      {recruiter ? <>
        <div className="art-brief"><span>JOB BRIEF / DATA ANALYST</span><b>Python · SQL · insight</b><i /></div>
        <div className="art-candidate art-candidate-3"><small>03 / CANDIDATE</small><strong>76</strong></div>
        <div className="art-candidate art-candidate-2"><small>02 / CANDIDATE</small><strong>82</strong></div>
        <div className="art-candidate art-candidate-1"><small>01 / CANDIDATE</small><strong>91</strong><em>↗ EVIDENCE FOUND</em></div>
      </> : <>
        <div className="art-resume art-resume-before"><small>ORIGINAL / YOUR FACTS</small><span>I made reports using SQL for the team.</span><i /></div>
        <div className="art-resume art-resume-after"><small>REFINED / YOUR VOICE</small><strong>Built SQL reports that helped the team review performance.</strong><em>✓ APPROVED BY YOU</em></div>
      </>}
    </div>
    <div className="mode-diagram"><b>{recruiter ? 'Job brief' : 'Resume'}</b><i>→</i><b>{recruiter ? 'Candidate stack' : 'Role check'}</b><i>→</i><b>{recruiter ? 'Shortlist' : 'Final draft'}</b></div>
    <strong className="mode-tile-action">{busy ? 'Opening workspace…' : !allowed ? 'Access not enabled' : `Enter ${mode} mode`} <span>↗</span></strong>
    {error && <span className="mode-error" role="alert">{error}</span>}
  </Link>
}
