import { GlassShape } from '@liquidglassjs/react'

function SymbolArt({ id }: { id: string }) {
  return <svg className="liquid-mark-art" viewBox="0 0 220 220" role="img" aria-label="HireFlow liquid mark">
    <defs>
      <linearGradient id={`${id}-metal`} x1="0" x2="1" y1="0" y2="1">
        <stop offset="0" stopColor="#fff8ea" /><stop offset=".22" stopColor="#d7bf9d" /><stop offset=".49" stopColor="#627b96" /><stop offset=".72" stopColor="#b17d68" /><stop offset="1" stopColor="#f3e5d2" />
      </linearGradient>
      <radialGradient id={`${id}-light`} cx=".3" cy=".25" r=".85">
        <stop offset="0" stopColor="#ffffff" stopOpacity=".7" /><stop offset="1" stopColor="#ffffff" stopOpacity="0" />
      </radialGradient>
    </defs>
    <path d="M110 15C59 15 18 55 18 108c0 51 39 96 91 97 53 1 93-42 93-94 0-28-11-48-27-62-14-12-33-17-50-13-18 5-31 21-31 40 0 24 20 40 42 40 14 0 27-5 40-14-3 32-29 55-64 55-30 0-53-22-53-52 0-33 24-55 51-55 10 0 18 2 26 6 8-14 20-25 34-32C151 17 132 15 110 15Z" fill={`url(#${id}-metal)`} />
    <path d="M110 15C59 15 18 55 18 108c0 51 39 96 91 97 53 1 93-42 93-94 0-28-11-48-27-62-14-12-33-17-50-13-18 5-31 21-31 40 0 24 20 40 42 40 14 0 27-5 40-14-3 32-29 55-64 55-30 0-53-22-53-52 0-33 24-55 51-55 10 0 18 2 26 6 8-14 20-25 34-32C151 17 132 15 110 15Z" fill={`url(#${id}-light)`} />
    <path d="M67 70v82m0-42h67m0-40v82" fill="none" stroke="#fff8ec" strokeWidth="7" strokeLinecap="round" opacity=".78" />
  </svg>
}

export default function LiquidMark({ large = false, className = '' }: { large?: boolean; className?: string }) {
  const id = large ? 'hf-large' : 'hf-small'
  return large ? <GlassShape className={`liquid-mark liquid-mark-large ${className}`} strength={15} chroma={.25} blur={.6} shade={.23} glint="#f0d6b6"><SymbolArt id={id} /></GlassShape> : <span className={`liquid-mark ${className}`}><SymbolArt id={id} /></span>
}
