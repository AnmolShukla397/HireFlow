import { Canvas, useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type RefObject } from 'react'
import { CanvasTexture, Group, MathUtils, Mesh, ShaderMaterial, SRGBColorSpace } from 'three'
import { useInView, useReducedMotion } from 'motion/react'

type PageKind = 'brief' | 'resume' | 'decision'
type DragState = { x: number; y: number; lastX: number; lastY: number; distance: number; active: boolean }
const pageKinds: PageKind[] = ['brief', 'resume', 'decision']
const ink = '#1b2837'

const liquidVertex = `
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vPosition;
  varying float vWave;
  void main() {
    vec3 p = position;
    float a = sin(p.x * 2.5 + uTime * .65) * sin(p.y * 2.3 - uTime * .48);
    float b = sin(p.z * 3.1 + p.y * 1.4 + uTime * .4);
    float wave = a * .12 + b * .09;
    p += normal * wave;
    vWave = wave;
    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vPosition = mv.xyz;
    gl_Position = projectionMatrix * mv;
  }
`
const liquidFragment = `
  uniform float uTime;
  uniform float uPhase;
  varying vec3 vNormal;
  varying vec3 vPosition;
  varying float vWave;
  void main() {
    vec3 n = normalize(vNormal);
    vec3 viewDir = normalize(-vPosition);
    float fresnel = pow(1.0 - max(dot(n, viewDir), 0.0), 2.1);
    float ribbon = sin(n.y * 9.0 + n.x * 4.0 + uTime * .55 + vWave * 13.0) * .5 + .5;
    vec3 deep = vec3(.035, .07, .14);
    vec3 steel = vec3(.31, .44, .59);
    vec3 pearl = vec3(.91, .87, .79);
    vec3 copper = vec3(.69, .38, .27);
    vec3 bright = mix(steel, copper, smoothstep(.8, 2.0, uPhase));
    vec3 color = mix(deep, bright, ribbon * .57 + fresnel * .36);
    color = mix(color, pearl, pow(fresnel, 2.0) * .69 + smoothstep(.92, 1.0, ribbon) * .14);
    gl_FragColor = vec4(color, .82);
  }
`

function LiquidCore({ phase, reduced }: { phase: number; reduced: boolean }) {
  const mesh = useRef<Mesh>(null)
  const material = useRef<ShaderMaterial>(null)
  const uniforms = useMemo(() => ({uTime:{value:0},uPhase:{value:0}}), [])
  useFrame((state, delta) => {
    if (!material.current || !mesh.current) return
    if (!reduced) material.current.uniforms.uTime.value += delta
    material.current.uniforms.uPhase.value = reduced ? phase : MathUtils.damp(material.current.uniforms.uPhase.value, phase, 2.2, delta)
    mesh.current.rotation.y = MathUtils.damp(mesh.current.rotation.y, state.pointer.x * .22, 2, delta)
    mesh.current.rotation.x = MathUtils.damp(mesh.current.rotation.x, state.pointer.y * -.16, 2, delta)
  })
  return <mesh ref={mesh} position={[1.7, .05, -3.8]}><sphereGeometry args={[2.7, 64, 64]} /><shaderMaterial ref={material} uniforms={uniforms} vertexShader={liquidVertex} fragmentShader={liquidFragment} transparent depthWrite={false} /></mesh>
}

function paperTexture(kind: PageKind) {
  const canvas = document.createElement('canvas')
  canvas.width = 720
  canvas.height = 900
  const ctx = canvas.getContext('2d')!
  const accent = kind === 'brief' ? '#667e9c' : kind === 'resume' ? '#a37660' : '#9e7656'
  ctx.fillStyle = kind === 'brief' ? '#efece4' : kind === 'resume' ? '#f6f2eb' : '#ede6dc'
  ctx.fillRect(0, 0, 720, 900)
  let seed = 7
  for (let index = 0; index < 2600; index++) {
    seed = (seed * 16807) % 2147483647
    const x = seed % 720
    seed = (seed * 16807) % 2147483647
    const y = seed % 900
    ctx.fillStyle = index % 3 ? '#24354a0b' : '#ffffff4a'
    ctx.fillRect(x, y, 1.3, 1.3)
  }
  ctx.fillStyle = accent
  ctx.fillRect(48, 45, 52, 7)
  ctx.fillStyle = ink
  ctx.font = 'bold 19px Arial'
  ctx.fillText('H / F', 48, 91)
  ctx.textAlign = 'right'
  ctx.font = 'bold 14px Arial'
  ctx.fillText(kind === 'brief' ? '01 / THE BRIEF' : kind === 'resume' ? '02 / THE EVIDENCE' : '03 / THE DECISION', 666, 86)
  ctx.textAlign = 'left'
  ctx.fillStyle = '#738397'
  ctx.font = 'bold 14px Arial'
  ctx.fillText('DOCUMENT INTELLIGENCE', 48, 160)
  ctx.fillStyle = ink
  ctx.font = '54px Georgia'
  ctx.fillText(kind === 'brief' ? 'The role.' : kind === 'resume' ? 'The person.' : 'The fit.', 48, 226)
  ctx.strokeStyle = '#c9c1b3'
  ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(48, 250); ctx.lineTo(672, 250); ctx.stroke()
  ctx.font = 'bold 16px Arial'
  ctx.fillText(kind === 'brief' ? 'DATA ANALYST / PRODUCT' : kind === 'resume' ? 'ALEX MORGAN / RESUME' : 'EVIDENCE REVIEW / 01', 48, 306)
  const lines = kind === 'brief'
    ? ['Build reporting that turns complex data', 'into a useful signal for the team.', 'Python  /  SQL  /  dashboards', 'Clear communication is essential.']
    : kind === 'resume'
      ? ['Built a weekly sales dashboard', 'using Python and SQL.', 'Analyzed trends across teams', 'and presented actionable findings.']
      : ['MATCHED  /  Python, SQL, reporting', 'SUPPORTED  /  Dashboard project', 'REVIEW  /  Communication evidence', 'Decision belongs to the person.']
  ctx.font = '23px Arial'
  ctx.fillStyle = '#536071'
  lines.forEach((line, index) => ctx.fillText(line, 48, 371 + index * 43))
  ctx.fillStyle = '#d8d0c3'
  ctx.fillRect(48, 588, 624, 3)
  if (kind === 'decision') {
    ctx.fillStyle = '#dcd4c4'
    ctx.fillRect(48, 625, 624, 138)
    ctx.fillStyle = '#6b5660'
    ctx.font = 'bold 80px Georgia'
    ctx.fillText('83', 66, 720)
    ctx.font = 'bold 16px Arial'
    ctx.fillText('MATCH ESTIMATE', 236, 675)
    ctx.fillStyle = '#626b77'
    ctx.font = '17px Arial'
    ctx.fillText('Read the evidence behind the number.', 236, 709)
  } else {
    ctx.fillStyle = accent
    ctx.fillRect(48, 632, 92, 8)
    ctx.fillStyle = '#65768b'
    ctx.font = 'bold 16px Arial'
    ctx.fillText(kind === 'brief' ? 'REQUIREMENTS' : 'EXPERIENCE', 48, 692)
    ctx.fillStyle = '#d1c8ba'
    for (let index = 0; index < 3; index++) ctx.fillRect(48, 716 + index * 27, 570 - index * 67, 7)
  }
  ctx.strokeStyle = '#c8bfb2'
  ctx.strokeRect(48, 821, 624, 1)
  ctx.fillStyle = '#788494'
  ctx.font = 'bold 13px Arial'
  ctx.fillText('HIREFLOW / EVIDENCE FIRST', 48, 855)
  ctx.textAlign = 'right'
  ctx.fillText('HF — 0' + (pageKinds.indexOf(kind) + 1), 672, 855)
  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 4
  return texture
}

function Document({ kind, active, pageRef, onSelect, drag, reduced }: { kind: PageKind; active: boolean; pageRef: RefObject<Group | null>; onSelect: () => void; drag: RefObject<DragState>; reduced: boolean }) {
  const texture = useMemo(() => paperTexture(kind), [kind])
  const scan = useRef<Group>(null)
  useEffect(() => () => texture.dispose(), [texture])
  useFrame(({ clock }) => {
    if (scan.current) scan.current.position.y = active ? reduced ? 0 : 1.9 - (clock.elapsedTime * .65 % 3.8) : 3
  })
  return <group ref={pageRef} onClick={event => { event.stopPropagation(); if (drag.current.distance < 8) onSelect() }}>
    <mesh position={[.08, -.08, -.08]} castShadow><boxGeometry args={[3.78, 4.78, .16]} /><meshStandardMaterial color="#61738b" roughness={.85} /></mesh>
    <mesh castShadow receiveShadow><boxGeometry args={[3.76, 4.76, .1]} /><meshStandardMaterial color="#f5f0e8" roughness={.86} /></mesh>
    <mesh position={[0, 0, .059]}><planeGeometry args={[3.74, 4.74]} /><meshStandardMaterial map={texture} roughness={.88} metalness={.01} /></mesh>
    <group ref={scan} position={[0, 3, .071]}><mesh><planeGeometry args={[3.65, .034]} /><meshBasicMaterial color="#e9c398" transparent opacity={active ? .65 : 0} depthWrite={false} /></mesh></group>
  </group>
}

function Composition({ phase, onSelect, reduced, drag }: { phase: number; onSelect: (index: number) => void; reduced: boolean; drag: RefObject<DragState> }) {
  const rig = useRef<Group>(null)
  const orbit = useRef<Group>(null)
  const pages = [useRef<Group>(null), useRef<Group>(null), useRef<Group>(null)]
  useFrame((state, delta) => {
    if (orbit.current && !reduced) orbit.current.rotation.z += delta * .045
    if (!rig.current) return
    const pointerX = reduced ? 0 : state.pointer.x
    const pointerY = reduced ? 0 : state.pointer.y
    rig.current.rotation.x = MathUtils.damp(rig.current.rotation.x, -.13 - pointerY * .1 + drag.current.y, 3.4, delta)
    rig.current.rotation.y = MathUtils.damp(rig.current.rotation.y, -.18 + pointerX * .25 + drag.current.x, 3.4, delta)
    rig.current.position.y = MathUtils.damp(rig.current.position.y, reduced ? 0 : Math.sin(state.clock.elapsedTime * .52) * .09, 2, delta)
    rig.current.position.x = MathUtils.damp(rig.current.position.x, 1.7, 3, delta)
    pages.forEach((ref, index) => {
      const page = ref.current
      if (!page) return
      const offset = index - phase
      const selected = offset === 0
      const speed = reduced ? 1000 : 3.8
      page.position.x = MathUtils.damp(page.position.x, selected ? 0 : offset * 1.38, speed, delta)
      page.position.y = MathUtils.damp(page.position.y, selected ? .16 : -.22 + index * .1, speed, delta)
      page.position.z = MathUtils.damp(page.position.z, selected ? .9 : -.75 - Math.abs(offset) * .3, speed, delta)
      page.rotation.z = MathUtils.damp(page.rotation.z, selected ? -.035 : offset * .145, speed, delta)
      page.rotation.y = MathUtils.damp(page.rotation.y, selected ? -.025 : -offset * .13, speed, delta)
      const scale = MathUtils.damp(page.scale.x, selected ? .86 : .78, speed, delta)
      page.scale.setScalar(scale)
    })
  })
  return <>
    <ambientLight intensity={1.35} />
    <directionalLight position={[1.5, 5, 6]} intensity={3.3} castShadow shadow-mapSize={[1024, 1024]} />
    <pointLight position={[-4, -1, 3]} intensity={4} color="#a9bdd8" />
    <pointLight position={[4, 2, -1]} intensity={3.2} color="#d3a88d" />
    <LiquidCore phase={phase} reduced={reduced} />
    <group ref={orbit} position={[1.7, 0, -2.8]} rotation={[.15, .15, -.3]}>
      <mesh><torusGeometry args={[3.2, .018, 8, 112]} /><meshBasicMaterial color="#c5b6a5" transparent opacity={.4} depthWrite={false} /></mesh>
      <mesh rotation={[.28, .22, .6]}><torusGeometry args={[2.65, .012, 8, 112]} /><meshBasicMaterial color="#8fa5c3" transparent opacity={.34} depthWrite={false} /></mesh>
      <mesh position={[3.08, .42, .2]}><sphereGeometry args={[.24, 24, 24]} /><meshPhysicalMaterial color="#d4c0a7" metalness={.2} roughness={.13} clearcoat={1} transparent opacity={.68} /></mesh>
      <mesh position={[-2.58, -.45, .1]}><sphereGeometry args={[.11, 16, 16]} /><meshBasicMaterial color="#d9ae89" /></mesh>
    </group>
    <group ref={rig} rotation={[-.13, -.18, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -3.2, -1]} receiveShadow><planeGeometry args={[14, 13]} /><shadowMaterial opacity={.3} /></mesh>
      {pageKinds.map((kind, index) => <Document key={kind} kind={kind} pageRef={pages[index]} active={phase === index} onSelect={() => onSelect(index)} drag={drag} reduced={reduced} />)}
    </group>
  </>
}

export default function Scene({ phase, onSelect }: { phase: number; onSelect: (index: number) => void }) {
  const reduced = Boolean(useReducedMotion())
  const wrapper = useRef<HTMLDivElement>(null)
  const drag = useRef<DragState>({ x: 0, y: 0, lastX: 0, lastY: 0, distance: 0, active: false })
  const inView = useInView(wrapper, { margin: '180px' })
  const [pageVisible, setPageVisible] = useState(!document.hidden)
  const [pixelRatio, setPixelRatio] = useState(window.innerWidth < 700 ? 1 : Math.min(window.devicePixelRatio, 1.5))
  useEffect(() => {
    const visibility = () => setPageVisible(!document.hidden)
    const resolution = () => setPixelRatio(window.innerWidth < 700 ? 1 : Math.min(window.devicePixelRatio, 1.5))
    document.addEventListener('visibilitychange', visibility)
    window.addEventListener('resize', resolution, { passive: true })
    return () => { document.removeEventListener('visibilitychange', visibility); window.removeEventListener('resize', resolution) }
  }, [])
  function startDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (reduced || event.button !== 0 || event.pointerType === 'touch') return
    drag.current.active = true
    drag.current.distance = 0
    drag.current.lastX = event.clientX
    drag.current.lastY = event.clientY
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  function moveDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag.current.active) return
    const dx = event.clientX - drag.current.lastX
    const dy = event.clientY - drag.current.lastY
    drag.current.x = MathUtils.clamp(drag.current.x + dx / 650, -.42, .42)
    drag.current.y = MathUtils.clamp(drag.current.y + dy / 650, -.24, .24)
    drag.current.distance += Math.abs(dx) + Math.abs(dy)
    drag.current.lastX = event.clientX
    drag.current.lastY = event.clientY
  }
  function stopDrag(event: ReactPointerEvent<HTMLDivElement>) {
    drag.current.active = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  return <div ref={wrapper} className="scene-wrap" data-cursor="TURN" aria-hidden="true" onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={stopDrag} onPointerCancel={stopDrag} onDoubleClick={() => { drag.current.x = 0; drag.current.y = 0 }}>
    <Canvas camera={{ position: [0, 0, 10], fov: 40 }} dpr={pixelRatio} shadows frameloop={inView && pageVisible && !reduced ? 'always' : 'demand'} gl={{ antialias: true, alpha: true }} fallback={<div className="scene-fallback">Job brief · Resume · Decision</div>}>
      <Composition phase={phase} onSelect={onSelect} reduced={reduced} drag={drag} />
    </Canvas>
  </div>
}
