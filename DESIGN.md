# HireFlow interface direction

HireFlow uses an evidence-atelier direction: graphite for the cinematic stage, warm paper for documents and work surfaces, steel blue for data, and a restrained metal accent for decisions and focus. The folded document is the recurring motif across the hero, live evidence study, workspace cards, authentication, and signed-in previews. The liquid HF mark is an original SVG symbol with refractive glass on large displays; no outside logo artwork is embedded.

## Public experience

The homepage opens on a persistent, scroll-linked 3D document sculpture. Its brief, resume, and decision are three chapters that respond to scrolling, pointer position, drag, double-click reset, and keyboard-accessible chapter controls. Procedural paper grain, metallic lighting, and a custom GLSL shader give the scene its material quality. A light editorial method section changes the pace before an interactive evidence study: visitors switch recruiter/applicant examples, spotlight a requirement, resume line, or interpretation, and turn the physical rig with the pointer. Its result plaque uses `@liquidglassjs/react` for refraction. Full-width mode entrances use pointer-responsive depth and lead to the chosen mode after authentication. The closing act uses the large liquid mark.

## Signed-in experience

Authentication, mode selection, and both workspaces share the same materials and a consistent motion system. Recruiter and applicant introductions have a three-stage physical document preview. Job description and resume fields show a live signal as text is entered; upload areas respond to hover, focus, drag, and file selection. Mode switching, profile actions, tabs, ranking rows, score bars, suggestions, and export controls retain visible interaction states. Analysis and editing surfaces use lighter motion than the homepage so document evidence stays readable. A reduced-motion preference stops decorative movement and preserves all information and controls.

## Implementation notes

The existing React, Vite, FastAPI, and Python analysis stack remains intact. `web/src/Scene.tsx` owns the WebGL document scene and shader. `web/src/EvidenceLab.tsx`, `web/src/WorkspaceAtmosphere.tsx`, and `web/src/LiquidMark.tsx` own the physical surfaces. `web/src/cinematic-world.css` is the final visual layer. It is imported after `styles.css`, `motion-world.css`, and `liquid-world.css` so this redesign can change the frontend without disturbing analysis and account code. The glass library is limited to decorative surfaces; text and form controls remain native DOM. The original Streamlit and CLI interfaces remain available.

The [Awwwards 3D gallery](https://www.awwwards.com/websites/3d/) informed the immersive interaction direction. The [liquid-glass-js React package](https://github.com/Amir-Abushanab/liquid-glass-js) supplies the refractive component. The [liquid-logo project](https://github.com/collidingScopes/liquid-logo) informed the material exploration; HireFlow uses its own symbol and implementation. No referenced site's layout, assets, or code were copied. The earlier [Figma reference](https://www.figma.com/design/Y7CyEtbMPx023Uv2nAN1JC) records prior screens; the current React code is the runnable design.
