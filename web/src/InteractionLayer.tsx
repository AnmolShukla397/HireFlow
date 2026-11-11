import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, useMotionValue, useReducedMotion, useSpring } from 'motion/react'

/** Pointer feedback is decorative: native focus, click and text cursors still work. */
export default function InteractionLayer() {
  const { pathname } = useLocation()
  const reduced = Boolean(useReducedMotion())
  const x = useMotionValue(-600)
  const y = useMotionValue(-600)
  const smoothX = useSpring(x, { stiffness: 310, damping: 32, mass: .38 })
  const smoothY = useSpring(y, { stiffness: 310, damping: 32, mass: .38 })
  const [finePointer, setFinePointer] = useState(false)
  const [visible, setVisible] = useState(false)
  const [label, setLabel] = useState('')
  const labelRef = useRef('')
  const publicPage = pathname === '/' || pathname === '/auth' || pathname === '/choose'

  useEffect(() => { setVisible(false); labelRef.current = ''; setLabel('') }, [pathname])

  useEffect(() => {
    const pointer = window.matchMedia('(hover: hover) and (pointer: fine)')
    const sync = () => setFinePointer(pointer.matches)
    sync()
    pointer.addEventListener('change', sync)
    return () => pointer.removeEventListener('change', sync)
  }, [])

  useEffect(() => {
    if (!finePointer || reduced) return
    function move(event: PointerEvent) {
      x.set(event.clientX)
      y.set(event.clientY)
      setVisible(true)
      const target = event.target instanceof Element ? event.target : null
      const interactive = target?.closest('[data-cursor], a, button, input, textarea, select')
      const custom = interactive?.getAttribute('data-cursor')
      const nextLabel = custom || (interactive?.matches('input, textarea, select') ? 'TYPE' : interactive?.matches('a') ? 'OPEN' : interactive?.matches('button') ? 'PRESS' : '')
      if (nextLabel !== labelRef.current) { labelRef.current = nextLabel; setLabel(nextLabel) }
    }
    function leave(event: PointerEvent) { if (!event.relatedTarget) setVisible(false) }
    function echo(event: PointerEvent) {
      if (event.button !== 0 || !(event.target instanceof Element)) return
      if (!event.target.closest('a, button, [data-click]')) return
      const pulse = document.createElement('span')
      pulse.className = 'pointer-echo'
      pulse.style.left = `${event.clientX}px`
      pulse.style.top = `${event.clientY}px`
      document.body.append(pulse)
      pulse.addEventListener('animationend', () => pulse.remove(), { once: true })
    }
    window.addEventListener('pointermove', move, { passive: true })
    window.addEventListener('pointerout', leave, { passive: true })
    window.addEventListener('pointerdown', echo, { passive: true, capture: true })
    return () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerout', leave)
      window.removeEventListener('pointerdown', echo, true)
    }
  }, [finePointer, reduced, x, y])

  if (!finePointer || reduced) return null
  return <>
    {publicPage && <motion.div className="pointer-light" style={{ x: smoothX, y: smoothY, opacity: visible ? 1 : 0 }} aria-hidden="true" />}
    <motion.div className={`pointer-orbit ${label ? 'is-active' : ''} ${publicPage ? 'on-public' : 'on-workspace'}`} style={{ x: smoothX, y: smoothY, opacity: visible ? 1 : 0 }} aria-hidden="true">
      <span className="pointer-ring" />
      <span className="pointer-dot" />
      {label && <span className="pointer-word">{label}</span>}
    </motion.div>
  </>
}
