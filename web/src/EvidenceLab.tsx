import { useState, type PointerEvent } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { LiquidGlass } from '@liquidglassjs/react'

type View = 'recruiter' | 'applicant'
const examples = {
  recruiter: {
    brief: 'Build reporting with Python and SQL for a product team.',
    resume: 'Built a weekly sales dashboard using Python and SQL.',
    score: '87',
    label: 'MATCH ESTIMATE',
    note: 'The tools and the work appear in both documents. Open the report to inspect the source lines before deciding.',
    tags: ['Python', 'SQL', 'Dashboard evidence'],
  },
  applicant: {
    brief: 'Deploy reliable services and explain how you improved the process.',
    resume: 'I helped my team deploy our services during an internship.',
    score: '64',
    label: 'READINESS ESTIMATE',
    note: 'The experience may be relevant, but the line is vague. Add the real tool and outcome you can support.',
    tags: ['Experience found', 'Specific tool missing', 'Outcome missing'],
  },
}

export default function EvidenceLab() {
  const [view, setView] = useState<View>('recruiter')
  const [focus, setFocus] = useState(0)
  const reduced = Boolean(useReducedMotion())
  const data = examples[view]

  function move(event: PointerEvent<HTMLDivElement>) {
    if (reduced || event.pointerType === 'touch') return
    const rect = event.currentTarget.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width - .5
    const y = (event.clientY - rect.top) / rect.height - .5
    event.currentTarget.style.setProperty('--lab-x', `${(x * 6).toFixed(2)}deg`)
    event.currentTarget.style.setProperty('--lab-y', `${(-y * 5).toFixed(2)}deg`)
    event.currentTarget.style.setProperty('--lab-light-x', `${(x + .5) * 100}%`)
    event.currentTarget.style.setProperty('--lab-light-y', `${(y + .5) * 100}%`)
  }
  function reset(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.style.setProperty('--lab-x', '0deg')
    event.currentTarget.style.setProperty('--lab-y', '0deg')
  }

  return <section className="evidence-lab" aria-labelledby="evidence-title">
    <div className="evidence-lab-head"><span>THE LIVE CONNECTION / 01</span><span>AN INTERACTIVE EVIDENCE STUDY</span></div>
    <div className="evidence-lab-layout">
      <div className="evidence-lab-copy"><p className="evidence-label">FROM WORDS TO WARRANTED DECISIONS</p><h2 id="evidence-title">Find the signal.<br /><em>Follow the source.</em></h2><p>Move between both sides of the hiring table. Then trace what HireFlow found, what it did not find, and what should happen next.</p>
        <div className="evidence-switch" role="tablist" aria-label="Example perspective"><button type="button" role="tab" aria-selected={view === 'recruiter'} className={view === 'recruiter' ? 'active' : ''} onClick={() => { setView('recruiter'); setFocus(0) }}>Recruiter <span>↗</span></button><button type="button" role="tab" aria-selected={view === 'applicant'} className={view === 'applicant' ? 'active' : ''} onClick={() => { setView('applicant'); setFocus(0) }}>Applicant <span>↗</span></button></div>
        <div className="evidence-trace" aria-label="Evidence details">{['Job requirement','Resume line','Interpretation'].map((label, i) => <button type="button" key={label} className={focus === i ? 'active' : ''} aria-pressed={focus === i} onClick={() => setFocus(i)}><span>0{i + 1}</span><strong>{label}</strong><i>↗</i></button>)}</div>
      </div>
      <div className="evidence-stage" onPointerMove={move} onPointerLeave={reset} data-focus={focus}>
        <div className="evidence-stage-grid" aria-hidden="true" />
        <div className="evidence-rig">
          <AnimatePresence mode="wait"><motion.div key={view} className="evidence-documents" initial={{opacity:0,rotateY:-16,scale:.93}} animate={{opacity:1,rotateY:0,scale:1}} exit={{opacity:0,rotateY:12,scale:.95}} transition={{duration:.5,ease:[.22,1,.36,1]}}>
            <div className={`evidence-paper evidence-paper-brief ${focus===0?'lit':''}`}><small>01 / JOB DESCRIPTION</small><span className="paper-rule" /><p>{data.brief}</p><div className="paper-bars"><i /><i /><i /></div></div>
            <div className={`evidence-paper evidence-paper-resume ${focus===1?'lit':''}`}><small>02 / RESUME EVIDENCE</small><span className="paper-rule" /><p>{data.resume}</p><div className="paper-bars"><i /><i /><i /></div></div>
          </motion.div></AnimatePresence>
          <div className="evidence-connection" aria-hidden="true"><span /><span /><span /></div>
          <LiquidGlass className={`evidence-result-glass ${focus===2?'lit':''}`} radius={22} strength={15} chroma={.18} tint={10} blur={1}>
            <div className="ps-glass__refract"><div className="ps-glass__refract-inner evidence-refraction">HIREFLOW / SIGNAL / SOURCE / HIREFLOW</div></div>
            <div className="ps-glass__content"><span>{data.label}</span><strong>{data.score}<i>/100</i></strong><small>Open the details behind the number ↗</small></div>
          </LiquidGlass>
        </div>
        <div className="evidence-stage-foot"><span>H / F · EVIDENCE ENGINE</span><span>MOVE YOUR CURSOR TO TURN THE DESK</span></div>
      </div>
    </div>
    <motion.div className="evidence-outcome" layout><div className="evidence-outcome-tags">{data.tags.map((tag, i) => <motion.span key={tag} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:i*.05}}>{tag}</motion.span>)}</div><p key={`${view}-${focus}`}>{focus === 0 ? `The brief sets the standard. ${data.brief}` : focus === 1 ? `The supplied resume says: “${data.resume}”` : data.note}</p><span className="evidence-outcome-index">0{focus + 1} / 03</span></motion.div>
  </section>
}
