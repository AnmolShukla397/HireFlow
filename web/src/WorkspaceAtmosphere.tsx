import { useState, type PointerEvent } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import LiquidMark from './LiquidMark'

const stages = ['Brief', 'Evidence', 'Decision'] as const

export default function WorkspaceAtmosphere({ mode }: { mode: 'recruiter' | 'applicant' }) {
  const [stage, setStage] = useState(0)
  const reduced = Boolean(useReducedMotion())
  const recruiter = mode === 'recruiter'
  const lines = recruiter
    ? ['Read the role in full.', 'Inspect each candidate line.', 'Build a sourced shortlist.']
    : ['Bring the target role.', 'Find what your resume supports.', 'Approve your own final draft.']
  function turn(event: PointerEvent<HTMLDivElement>) {
    if (reduced || event.pointerType === 'touch') return
    const r = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--turn-x', `${(((event.clientX-r.left)/r.width-.5)*9).toFixed(2)}deg`)
    event.currentTarget.style.setProperty('--turn-y', `${((.5-(event.clientY-r.top)/r.height)*7).toFixed(2)}deg`)
  }
  function reset(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.style.setProperty('--turn-x', '0deg')
    event.currentTarget.style.setProperty('--turn-y', '0deg')
  }
  return <div className="workspace-atmosphere" onPointerMove={turn} onPointerLeave={reset}>
    <div className="workspace-atmosphere-orb" aria-hidden="true"><LiquidMark /></div>
    <div className="workspace-atmosphere-ring" aria-hidden="true" />
    <div className="workspace-atmosphere-sheet" aria-hidden="true"><div className="workspace-sheet-head"><span>H / F</span><span>{recruiter ? 'CANDIDATE INTELLIGENCE' : 'RESUME STUDIO'}</span></div><AnimatePresence mode="wait"><motion.div key={`${mode}-${stage}`} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-12}} transition={{duration:.28}}><small>0{stage+1} / {stages[stage].toUpperCase()}</small><p>{lines[stage]}</p></motion.div></AnimatePresence><div className="workspace-sheet-lines"><i /><i /><i /></div></div>
    <div className="workspace-atmosphere-controls" role="group" aria-label={`${recruiter ? 'Recruiter' : 'Applicant'} process preview`}>{stages.map((name,index)=><button type="button" key={name} aria-label={`Preview ${name.toLowerCase()} stage`} aria-pressed={stage===index} className={stage===index?'active':''} onClick={()=>setStage(index)}>0{index+1}</button>)}</div>
  </div>
}
