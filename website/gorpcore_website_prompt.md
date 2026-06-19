
---- PROMPT START ----

## Role & Goal

Build a polished, animated single-page **product website** that presents a finished, brand-facing deliverable: a **"Lightweight Gorpcore" Trend Intelligence & Design Direction** brief for Chinese sportswear brands (Anta / Li-Ning).

Treat the project as fully complete. This is the final product — present everything with the confidence of a delivered, validated piece of work. No "in progress", no methodology recap, no disclaimers, no roadmap. The audience is a brand design team; the site IS the deliverable.

**All visible copy must be in English.** It should read like a premium design-intelligence brief, not a generic template.

## Tech stack

- **React + Vite + TypeScript**, **Tailwind CSS**
- **Framer Motion** + **GSAP/ScrollTrigger** for scroll choreography and reveals
- **Recharts** (or D3) for the data moments
- Runnable with `npm install && npm run dev`. Fully responsive, mobile-first. Respect `prefers-reduced-motion`.

## Visual design direction

Aesthetic: "lightweight gorpcore" — technical outdoor wear meeting the city. Editorial, confident, design-forward.

- **Palette:** deep olive `#3F4A34`, sage `#7C8B6B`, warm khaki/sand neutrals, charcoal `#1C1E1A` text, off-white `#F4F2EC` background, one high-vis "reflective" accent `#E4571B` used sparingly.
- **Typography:** technical grotesk for headlines (Space Grotesk or similar), clean sans for body, **monospace** (JetBrains Mono) only for spec-sheet labels (HEX codes, material tags, %).
- **Motifs:** subtle topographic contour lines, thin technical "spec-sheet" rules with corner ticks, reflective hairlines, restrained grid.
- **Motion:** scroll reveals (fade + rise), animated counters, swatches and chips that stagger in, smooth section transitions. Tasteful, not noisy.
- Use clearly-labeled **image placeholder components** wherever real photos / mood-board images go.

## Page sections (a finished deliverable)

### 1. Hero
- Headline: **Lightweight Gorpcore** with a confident tagline: *A data-driven design direction for the urban-outdoor season.*
- One-line positioning: *From hardcore mountain gear to a lighter, city-ready style — distilled from real consumer signal into a concrete design playbook.*
- Drifting topographic background + parallax; headline animates in. No course/assignment framing at the top.

### 2. The Direction (the thesis)
One bold editorial statement: the market has moved from "engineered for extremes" to "engineered for the commute." Consumers want the look and the preparedness of gorpcore without the heat, weight and visual excess. The answer is a lightweight, city-ready line. 2–3 punchy sentences with a strong pull-quote treatment.

### 3. Trend Signals (the intelligence)
Present the curated intelligence behind the recommendations. Two tight, animated visuals:

**A) What consumers reject → what to design** — animated horizontal bars; each row pairs the demand signal with the design move it unlocks:
- Price sensitivity → value engineering, tiered materials
- Breathability → ventilation systems, breathable membranes
- Commute fit → daily-wear silhouettes, stowable features
- Durability → reinforced ripstop construction
- Weight → reduced-weight fabrics, minimal hardware
- Silhouette → refined urban cut
- Zipper reliability → sealed, dependable zipper systems

**B) Evidence at a glance** — a stat strip with animated counters: a large multimodal corpus of consumer signals, outfit images and competitor reviews, curated across four platforms and cross-verified between image and text to filter idealised social posts. (Phrase as delivered scale, not raw counts; e.g. "40K+ consumer signals · 1K+ curated outfit images · 4 platforms · image–text cross-verified.")

### 4. Visual Word Cloud / Trend Atlas (centerpiece)
A full-width, animated "Visual Word Cloud" — the data-driven mood board, presented as a finished trend atlas. Terms scale by weight and animate in; mix design language (Utility, Functional, Layering, Pocket, Zipper, Reflective, Loose Fit, Techwear, Modular) with tone words (Earthy Tones, Neutral Tones, Muted, Durable, Breathable). Leave a labeled placeholder so the rendered atlas / cropped-component cloud can drop in. Make this a visual highlight.

### 5. Design Recommendations (the core deliverable)
The actionable playbook, presented like a finished season design board. Four clean, animated panels:

- **Colour** — interactive swatch palette with monospace HEX labels: olive / army green, khaki, charcoal, off-white, navy, plus one reflective contrast accent. Swatches expand on hover.
- **Material** — chips with a weight read: matte nylon, ripstop, soft-shell as the lightweight, breathable core; heavy fleece / hard-shell intentionally minimised for the city line.
- **Silhouette** — loose but refined, oversize-with-structure, cropped and longline options; commute-ready proportions.
- **Functional details** — the gorpcore signatures kept in the lightweight edit: sealed/reflective zippers, stealth multi-pocket layouts, taped seams, detachable / quick-dry elements, underarm ventilation.

Each panel reads like a spec card a designer can act on next season.

### 6. Curated Evidence Gallery
A gallery of annotated outfit images proving the recommendations are grounded in structured, curated data. Each card = an image placeholder + a monospace attribute strip, e.g.:
`Fit: Loose · Zipper: Sealed · Reflective: true · Primary: black · Secondary: olive green · Material: matte nylon, ripstop · Scenario: Urban_Commute · Weight: lightweight`
6–9 cards, staggered reveal, labeled empty image slots.

### 7. Footer
Small and tasteful: *Gorpcore Trend Intelligence · Group 12 · INFO 202 Data Curation, Lanzhou University.* Team names (Zisheng Chen, Shang Ma, Linxiao Du, Chenye Zheng, Guanzheng Chen). One quiet credit line: *Built on an AI-assisted multimodal data-curation pipeline.* Repo link placeholder: `https://github.com/De-Carl/Gorpcore_Project`. Closing line: *"Not what is popular — what is defensible."*

## Quality bar

- Smooth 60fps animation, all motion gated by `prefers-reduced-motion`.
- Reads as a finished, confident brand deliverable on desktop and mobile.
- Labeled image placeholders everywhere real photos go.
- Clean, componentized, commented code; one command to run.

Build it.

---- PROMPT END ----
