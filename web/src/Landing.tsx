import { lazy, Suspense, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useMotionValueEvent, useReducedMotion, useScroll } from 'motion/react'
import type { User } from './api'
import { Brand } from './components'
import ModePortal from './ModePortal'
import EvidenceLab from './EvidenceLab'
import LiquidMark from './LiquidMark'

const Scene = lazy(() => import('./Scene'))
const chapters = [
  { id: '01', label: 'THE INPUT', title: <>The next move<br />starts on <em>paper.</em></>, body: 'A role is more than a title. Put the job description beside the actual work and let the details set the standard.', micro: 'THE BRIEF / THE PERSON / THE PROOF' },
  { id: '02', label: 'THE READING', title: <>Look closer.<br /><em>See further.</em></>, body: 'HireFlow connects requirements to the lines that support them, revealing strengths, gaps, and the source behind every score.', micro: 'EVERY SIGNAL HAS A SOURCE' },
  { id: '03', label: 'THE DECISION', title: <>Keep the<br /><em>final say.</em></>, body: 'Build a more considered shortlist or a sharper resume. Inspect the evidence, approve the changes, and move forward with confidence.', micro: 'HUMAN JUDGMENT, BETTER INFORMED' },
]

export default function Landing({ user, onUser }: { user: User | null; onUser: (user: User) => void }) {
  const story = useRef<HTMLDivElement>(null)
  const [phase, setPhase] = useState(0)
  const reduced = Boolean(useReducedMotion())
  const { scrollYProgress } = useScroll({ target: story, offset: ['start start', 'end end'] })
  useMotionValueEvent(scrollYProgress, 'change', value => setPhase(Math.min(2, Math.floor(value * 3.02))))
  const destination = user ? (user.mode ? `/${user.mode}` : '/choose') : '/auth?create=1'
  function go(index: number) { document.getElementById(`act-${index}`)?.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth' }) }

  return <div className="kinetic-landing cinematic-landing">
    <motion.div className="kinetic-progress" style={{ scaleX: scrollYProgress }} />
    <header className="kinetic-nav cinematic-nav">
      <Brand light />
      <nav aria-label="Main navigation"><a href="#method">How it works</a><a href="#workspaces">Workspaces</a></nav>
      <div className="kinetic-nav-right">{user ? <Link to={destination}>Open workspace <span>↗</span></Link> : <><Link className="kinetic-signin" to="/auth">Sign in</Link><Link to="/auth?create=1">Get started <span>↗</span></Link></>}</div>
    </header>
    <main>
      <div id="story" className="kinetic-story cinematic-story" data-phase={phase} ref={story}>
        <div className="kinetic-stage cinematic-stage">
          <div className="cinematic-stage-top"><span>HIREFLOW / DOCUMENT INTELLIGENCE</span><span>DESIGNED FOR THE DECISION</span></div>
          <Suspense fallback={<div className="kinetic-scene-fallback" aria-hidden="true">HF</div>}><Scene phase={phase} onSelect={go} /></Suspense>
          <div className="cinematic-halo" aria-hidden="true" />
          <div className="cinematic-stage-side" aria-hidden="true">A BETTER WAY TO READ BETWEEN THE LINES <span>✳</span></div>
          <div className="kinetic-rail" aria-label="Story chapters">{chapters.map((chapter, i) => <button key={chapter.id} type="button" className={phase === i ? 'active' : ''} aria-label={`Go to ${chapter.label.toLowerCase()}`} aria-current={phase === i ? 'step' : undefined} onClick={() => go(i)}><span>{chapter.id}</span><i /></button>)}</div>
          <div className="cinematic-stage-bottom"><span><i /> MADE TO FIND THE SIGNAL</span><span>DRAG THE DOCUMENTS · SCROLL THE STORY ↓</span></div>
        </div>
        <div className="kinetic-acts cinematic-acts">
          {chapters.map((chapter, i) => <section id={`act-${i}`} className={`kinetic-act cinematic-act cinematic-act-${i}`} key={chapter.id}>
            <div className="kinetic-act-copy cinematic-act-copy">
              <motion.div className="cinematic-chapter" initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ amount: .5 }} transition={{ duration: .5 }}><span>{chapter.id} / 03</span><span>{chapter.label}</span></motion.div>
              {i === 0 ? <motion.h1 className="kinetic-act-title cinematic-act-title" initial={{ opacity: 0, y: 45 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ amount: .4 }} transition={{ duration: .85, ease: [.22, 1, .36, 1] }}>{chapter.title}</motion.h1> : <motion.h2 className="kinetic-act-title cinematic-act-title" initial={{ opacity: 0, y: 45 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ amount: .4 }} transition={{ duration: .85, ease: [.22, 1, .36, 1] }}>{chapter.title}</motion.h2>}
              <motion.p className="kinetic-act-body cinematic-act-body" initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ amount: .5 }} transition={{ duration: .6, delay: .1 }}>{chapter.body}</motion.p>
              {i === 0 ? <motion.div className="kinetic-hero-actions" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .5 }}><Link className="kinetic-primary-link" to={destination}><span>Start with your documents</span><b>↗</b></Link><a href="#method" className="kinetic-quiet-link">Discover the method <span>↓</span></a></motion.div> : <div className="cinematic-chapter-end"><span>HIREFLOW / {chapter.micro}</span><span>↗</span></div>}
            </div>
          </section>)}
        </div>
      </div>
      <section id="method" className="cinematic-manifesto" aria-labelledby="method-title">
        <div className="cinematic-manifesto-top"><span>THE METHOD</span><span>01 — 03 / FROM DOCUMENT TO DECISION</span></div>
        <div className="cinematic-manifesto-grid"><motion.h2 id="method-title" initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .5 }} transition={{ duration: .8 }}>A clearer view<br />of <em>what matters.</em></motion.h2><div className="cinematic-manifesto-list"><div><span>01</span><strong>Bring the role.</strong><p>Start with the job description in text or a document.</p></div><div><span>02</span><strong>Read the evidence.</strong><p>Compare candidate CVs or inspect your own resume against it.</p></div><div><span>03</span><strong>Make it yours.</strong><p>Review scores and suggestions, then decide what to do next.</p></div></div></div>
        <div className="cinematic-manifesto-foot"><span>THE SIGNAL IS IN THE DETAILS</span><span>↓ EXPLORE THE LIVE STUDY</span></div>
      </section>
      <EvidenceLab />
      <section id="workspaces" className="kinetic-workspaces cinematic-workspaces"><div className="kinetic-workspaces-head"><p>ONE ENGINE / TWO PERSPECTIVES</p><h2>Read the role.<br /><span>Own the outcome.</span></h2><div>The same careful reading powers two distinct workspaces. Choose the side of the table that is yours.</div></div><div className="kinetic-modes"><motion.div className="mode-entry" initial={{opacity:0,y:65,rotateX:5}} whileInView={{opacity:1,y:0,rotateX:0}} viewport={{once:true,amount:.16}} transition={{duration:.8,ease:[.22,1,.36,1]}}><ModePortal mode="recruiter" user={user} onUser={onUser} /></motion.div><motion.div className="mode-entry" initial={{opacity:0,y:65,rotateX:5}} whileInView={{opacity:1,y:0,rotateX:0}} viewport={{once:true,amount:.16}} transition={{duration:.8,ease:[.22,1,.36,1]}}><ModePortal mode="applicant" user={user} onUser={onUser} /></motion.div></div></section>
      <section className="kinetic-close cinematic-close"><div className="kinetic-close-symbol" aria-hidden="true"><LiquidMark large /></div><p>YOU HAVE THE LAST WORD</p><h2>Make your<br />next move <em>count.</em></h2><Link to={destination}>Enter HireFlow <span>↗</span></Link><span className="cinematic-close-index">H / F · 2026</span></section>
    </main>
    <footer className="kinetic-footer cinematic-footer"><Brand light /><p>Clarity for the next move.</p><span>© {new Date().getFullYear()} HireFlow</span></footer>
  </div>
}
