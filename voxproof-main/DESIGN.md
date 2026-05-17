# Design System: VoxProof

> Voice Agent Security Gateway — Stitch-ready design contract.

## 1. Visual Theme & Atmosphere

A **clinical security dashboard** that breathes — not the cramped cockpit of a SOC, but the deliberate calm of a modern compliance product. Dense enough that every pixel earns its keep, restrained enough that threats *visually* dominate when they appear.

- **Density:** 6/10 — "Daily app balanced" leaning slightly dense. Monospace numerals for findings/severities/timestamps.
- **Variance:** 6/10 — Asymmetric. Split-screen Login. 1fr / 1.3fr two-column dashboards. No centered hero.
- **Motion:** 4/10 — Restrained spring; ring gauges fill on data arrival, scenario cards stagger-mount, threat pulses on detection. No marketing-grade choreography.

The interface speaks the language of *forensic precision*: a defense product, not a demo. Threats are surfaced through color shift and weight — never through emoji or exclamation.

---

## 2. Color Palette & Roles

The palette is built on **Zinc** neutrals plus a single **Emerald** safety accent and one **Crimson** threat accent. No gradients on surfaces. No purple. No neon.

| Token | Hex | Role |
|-------|-----|------|
| **Canvas Mist** | `#FAFAFA` | App background (zinc-50) |
| **Pure Surface** | `#FFFFFF` | Cards, panels, modals |
| **Hairline Border** | `rgba(228,228,231,0.6)` | Card borders, dividers (zinc-200/60) |
| **Charcoal Ink** | `#18181B` | Primary text, dark hero panel background (zinc-900/950) |
| **Graphite** | `#3F3F46` | Body text on light (zinc-700) |
| **Muted Steel** | `#71717A` | Secondary text, metadata (zinc-500) |
| **Whisper Steel** | `#A1A1AA` | Tertiary text, disabled, placeholders (zinc-400) |
| **Verdant Pulse** | `#10B981` | Safety / PASS / brand accent (emerald-500) |
| **Verdant Deep** | `#047857` | Hover state for safety (emerald-700) |
| **Threat Crimson** | `#EF4444` | FAIL / blocked tool call (red-500) |
| **Caution Amber** | `#F59E0B` | NEEDS_REVIEW / warning (amber-500) |
| **Boundary Violet** | `#8B5CF6` | Audio-layer boundary tag (violet-500) |
| **Boundary Indigo** | `#6366F1` | Lobster boundary tag (indigo-500) |

**Banned:**
- Pure black (`#000000`) — use Charcoal Ink (`#18181B`) or Zinc-950 (`#09090B`)
- Purple/blue neon AI gradients on buttons or hero
- Saturated rainbow palettes — VoxProof has *one* safety accent and *one* threat accent. Everything else is neutral grayscale.
- Gradient text on large headers

The emerald accent sits at 84% saturation — at the edge of the "below 80%" rule. This is intentional: in a security product, the *safe* state must read instantly. It's used sparingly — on the brand mark, the PASS state, primary CTAs only.

---

## 3. Typographic Architecture

**Fonts:**
- **Display & Body:** `Geist` (weights 400/500/600/700/800) — track-tight, geometric, technical-but-warm. Already loaded.
- **Mono:** `Geist Mono` (weights 400/500/600) — for findings counts, severity scores, timestamps, code snippets, terminal-style tool call rendering.
- **Banned:** `Inter`, `Roboto`, `Times New Roman`, `Georgia`, system fonts, *any* serif.

**Scale (clamp-based for responsiveness):**

| Role | Spec | Weight |
|------|------|--------|
| Hero headline | `clamp(1.75rem, 4vw, 2rem)` — track-tight | 700 |
| Section title | `text-base` (1rem) | 700 |
| Card title | `text-sm` (0.875rem) | 600 |
| Body | `text-sm` (0.875rem) | 400, line-height 1.6 |
| Metadata | `text-xs` (0.75rem) | 500 |
| Eyebrow / label | `text-[10px]` uppercase, tracking-widest | 700 |
| Mono numeral | `tabular-nums font-mono` | 600 |

Hierarchy is delivered through **weight and color**, not size jumps. Body never reads "tiny" — minimum 12px (`text-xs`) and only for incidental metadata.

---

## 4. Hero Section (Login Page)

The Login page is the only "marketing" surface. Rules:

- **Layout:** Asymmetric split. Left: 460px dark Charcoal panel with brand + features + academic refs. Right: form on Canvas Mist.
- **No centered hero.** Forbidden.
- **No "Scroll to explore" or chevrons.** Form *is* the call-to-action.
- **No filler text.** Real value props: "Protect voice AI agents before they betray you" — concrete, not "Elevate your security posture."
- **No overlapping elements.** Decorative radial glows live as `pointer-events-none` background layers and never cross text zones.
- **CTA restraint:** One primary "Sign In →" button. Mode toggle (Sign In / Register) is *not* a second CTA — it's a tab.
- **Mobile collapse:** Dark hero hidden below `lg`, brand mark moves above form.

---

## 5. Component Stylings

### Buttons

- **Primary:** Charcoal Ink fill (`bg-zinc-900`), white text, `rounded-xl` (12px), `active:scale-[0.98]` tactile push. Disabled at 40% opacity.
- **Accent (Run Attack Suite):** Same Charcoal — emerald is reserved for *state*, not buttons.
- **Ghost:** Transparent, hover reveals `bg-zinc-100`.
- **Danger:** `bg-red-500 text-white` only for the Stop / abort affordances.
- **No outer glows.** No `box-shadow` color halos.
- **No icon-only buttons** without a tooltip.

### Cards

- `rounded-2.5xl` (20px) — generous, but not bubble.
- `border border-zinc-200/50` hairline + `shadow-diffuse` (very soft, 20px blur, 5% opacity).
- Lift to `shadow-diffuse-lg` on hover; **no Y-translation** on hover (was previously translating up — removed because it caused layout-shift on cursor entry of the scenario list).
- Cards are used **only when elevation communicates hierarchy** (detail panels, modals, toasts). The scenario list uses borderless rows with a `gate-color` 1.5px left strip — *not* cards.

### Tool Call Interception Card (Playground)

Signature component. Two zones:
- **Header band:** Solid threat color (`bg-red-600` for FAIL, `bg-amber-500` for NEEDS_REVIEW). White text + lock icon + gate badge.
- **Code zone:** `bg-zinc-950` terminal. Function name in amber-400, args in emerald-300, parens in zinc-600. Mono only.
- **Findings strip:** Dark-on-dark boundary tags with reduced contrast.

### Inputs

- Label above, error below. No floating labels.
- `rounded-xl` border, `border-zinc-200`. Focus: `border-emerald-400` + `ring-2 ring-emerald-100`.
- Password fields use `Lock` icon prefix at left-3.5.

### Loading States

- Three dots bouncing for in-message analyzing.
- Skeletal layout-matching shimmer for full-panel loads — **never** a centered circular spinner.

### Empty States

- Composed: muted icon at top, single-line bold copy, one-line description, action affordance.
- Never just "No data."

### Status / Threat Indicator

- Status bar: full-width pill, color shifts from `bg-emerald-50 border-emerald-200` (safe) to `bg-red-50 border-red-200` (threats detected). Shield icon recolors.
- Live dot: 1.5px emerald circle with `live-pulse` 1.8s ease-in-out — used only for actually-live channels (Gemini, audio stream).

### Trust Score Ring Gauge

- 96px SVG ring, 8px stroke, `round` linecap.
- Color tier: ≥80 emerald, 40–79 amber, <40 crimson.
- Track color is the lightest tint of the same hue.
- `stroke-dashoffset` transitions over 1.2s `cubic-bezier(0.4,0,0.2,1)` on data arrival.
- Tabular numeral center; "Trust" label uppercase eyebrow.

---

## 6. Layout Principles

- **Max-width container:** `max-w-[1440px]` centered with `px-6`.
- **Two-column dashboards:** `grid-cols-[1fr_1.3fr]` for "list + detail" pairs. Never 50/50 — slight asymmetry reads more intentional.
- **No 3-equal-card hero rows.** Anywhere. The Hackathon badges row uses 2 pills (Track 1, Track 2) — not 3.
- **No overlapping elements.** Decorative radial gradients live on `absolute inset-0 pointer-events-none` background layers; foreground content always has its own zone.
- **Spacing rhythm:** vertical gap-6 (24px) between major sections, gap-3 (12px) inside cards, gap-1.5 (6px) inside finding chips.
- **Sticky nav:** `sticky top-0 z-40 bg-white/90 backdrop-blur-xl border-b border-zinc-200/60`. Height 56px (`h-14`). Pipeline strip sits beneath as a 24px sub-bar.
- **CSS Grid over flexbox math.** No `calc()` percentage hacks.
- **Full-height pages:** `min-h-[100dvh]` — never `h-screen`.

---

## 7. Responsive Strategy

| Breakpoint | Behavior |
|-----------|----------|
| `< 768px` (mobile) | Dark Login hero hidden, brand collapses above form. Header hackathon badges hidden. Tab labels hidden (icons only). Two-column dashboards stack vertically. Trust gauge moves above stats list. |
| `768–1024px` (tablet) | Tabs show partial labels. Two-column splits remain at 1fr/1.3fr. |
| `≥ 1024px` (desktop) | Full layout with hero panel, badges, labels. |

- All multi-column layouts collapse to single column below 768px.
- No horizontal scroll anywhere.
- Touch targets minimum 44×44px (currently 36–40px for some compact icon buttons — these must grow on touch devices via `@media (pointer: coarse)`).
- Typography uses `clamp()` where it varies; body text never below 12px.

---

## 8. Motion & Interaction

- **Spring physics default:** for any future framer-motion additions, `stiffness: 100, damping: 20`.
- **CSS transitions:** 150ms `ease-out` for hover, 200ms for active scale, 1.2s `cubic-bezier(0.4,0,0.2,1)` for gauge fills.
- **Stagger reveals:** scenario list mounts with 60ms cascade via `animate-fadeIn` + per-item delay.
- **Perpetual loops:** `live-pulse` on the live dot (1.8s opacity loop). `threat-pulse` on the status bar when threats detected. `scan-line` on the LiveMonitor transcript when a session is active.
- **Hardware-accelerated only:** `transform` and `opacity`. Never `top`/`left`/`width`/`height` in transitions.
- **No custom mouse cursors.** No glitch effects. No parallax.

---

## 9. Iconography

- **Phosphor Icons** exclusively. `weight="fill"` for active states / strong assertions; `weight="duotone"` for empty-state decorative; `weight="regular"` for navigation.
- **No emojis.** Anywhere. Status, security, branding — all Phosphor.
- Icon-only buttons must have `title` attribute (tooltip).

---

## 10. Anti-Patterns (Hard Bans)

| Banned | Why |
|--------|-----|
| Emojis in UI copy | Reads consumer-app, not enterprise security |
| `Inter` font | Default-tier; we use `Geist` |
| Any generic serif (`Georgia`, `Times`, `Garamond`) | Banned in dashboards entirely |
| Pure `#000000` | Use `#18181B` (zinc-900) or `#09090B` (zinc-950) |
| Outer glow shadows on buttons / inputs | AI-product cliché |
| Purple/blue neon gradients | Hallmark of low-effort AI design |
| `Elevate`, `Seamless`, `Unleash`, `Next-gen` | Hollow AI copywriting |
| `Acme`, `John Doe`, `you@example.com` (defaults) | Use real-shaped placeholders: `you@company.com` |
| "Scroll to explore", bouncing chevrons | Filler UI |
| 3-equal-column feature row | Use asymmetric splits or 2-pill rows |
| Centered hero on Login | Use asymmetric split-screen |
| `h-screen` (use `min-h-[100dvh]`) | iOS Safari catastrophic jump |
| Animating `width` / `height` | Janky, non-GPU |
| Cards stacking with `translate-y` on hover | Causes layout-shift jitter on cursor entry |
| Centered circular spinner during data load | Use skeletal shimmer matching layout |
| Gradient on body text headings | Cheap-looking |
| 4+ accent colors competing | One safety, one threat. Everything else neutral. |

---

## Reference: Component → File Map

| Component | File |
|-----------|------|
| Login split-screen | `frontend/src/components/Login.tsx` |
| Header + pipeline strip + Attack Suite | `frontend/src/App.tsx` |
| TrustGauge SVG ring | `frontend/src/App.tsx` (inline component) |
| Playground + Tool Interception Card | `frontend/src/components/Playground.tsx` |
| LiveMonitor with scan-line | `frontend/src/components/LiveMonitor.tsx` |
| PolicyCompiler with academic refs | `frontend/src/components/PolicyCompiler.tsx` |
| CustomTest freeform input | `frontend/src/components/CustomTest.tsx` |
| Global tokens & animations | `frontend/src/index.css` |
| Color & font config | `frontend/tailwind.config.js` |
