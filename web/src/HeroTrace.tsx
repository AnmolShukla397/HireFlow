import { AnimatePresence, motion, useReducedMotion } from 'motion/react'

const steps = [
  { label: 'Brief', eyebrow: 'THE ROLE ASKS FOR', line: 'Python, SQL, and reporting that makes data useful.', note: 'Start with the exact requirements in the job description.' },
  { label: 'Evidence', eyebrow: 'THE RESUME SHOWS', line: 'Built a weekly sales dashboard using Python and SQL.', note: 'See the work behind a matching skill, line by line.' },
  { label: 'Decision', eyebrow: 'THE CONNECTION', line: 'A supported match, with the source kept in view.', note: 'Inspect the reasoning before ranking or approving a change.' },
]

export default function HeroTrace({ phase, onSelect }: { phase: number; onSelect: (index: number) => void }) {
  const reduced = Boolean(useReducedMotion())
  const current = steps[phase]
  return <div className="hero-trace" aria-label="Example evidence flow">
    <div className="trace-head"><span className="trace-signal" aria-hidden="true" /> <span>AN EXAMPLE, IN THREE MOVES</span><b>0{phase + 1} / 03</b></div>
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={phase} className="trace-reading" initial={reduced ? false : { opacity: .35, y: 9, filter: 'blur(7px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={reduced ? undefined : { opacity: 0, y: -7, filter: 'blur(5px)' }} transition={{ duration: .3, ease: [.22, 1, .36, 1] }}>
        <small>{current.eyebrow}</small><strong>“{current.line}”</strong><p>{current.note}</p>
      </motion.div>
    </AnimatePresence>
    <div className="trace-controls" role="tablist" aria-label="Example evidence stages">{steps.map((step, index) => <button key={step.label} type="button" role="tab" aria-selected={phase === index} className={phase === index ? 'active' : ''} onClick={() => onSelect(index)}><span>0{index + 1}</span>{step.label}</button>)}</div>
  </div>
}
