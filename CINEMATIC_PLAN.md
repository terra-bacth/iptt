# Cinematic UI/UX Redesign — Plan (No Fundamentals Changed)

## Current Audit
- **theme.css v9** tries to unify, but every template (`dashboard.html`, `project_executive_dashboard.html`, `programme_executive_dashboard.html`, `circle_dashboard.html`, `projects.html`, `home.html`) still ships inline `<style>` blocks with different card shadows, table headers, button colors, border radii.
- No design tokens for motion, elevation, or depth. Everything is flat white on #f2f5f9.
- Reports: heavy tables, sticky columns with z-index hacks, progress bars with text inside, collapsible sections are abrupt (display:none), no visual hierarchy between KPI / matrix / risk.
- Nav is sticky but opaque white, no depth separation from content.

**Goal:** Keep all routes, DB, JS hooks, status colours (`status-green/red/yellow`), and Jinja variables intact. Only presentation layer.

## Cinematic Direction
Think: **Linear + Stripe Dashboard + Apple TV** — not flashy gaming UI.

- **Depth:** App background becomes layered: deep ink (#070B14) radial glows + subtle noise, cards float with soft border + inner highlight.
- **Glass Navigation:** Floating, blurred, with 1px hairline border, brand mark glows on hover.
- **Typography:** Tight display headings (-0.03em), uppercase eyebrows (12px / 0.12em), Inter/Sora for UI, tabular numbers for KPIs.
- **Motion:** 
  - Page enter: `iptt-rise` 0.6s cubic
  - Cards lift -4px on hover + shadow bloom
  - Progress bars grow from 0 (scaleX)
  - Collapsibles use height + opacity, not display toggle
  - Scroll reveal with IntersectionObserver (already there, refined)
- **Color:** 
  - Background: #070B14 -> #0F172A gradient
  - Surface: rgba(255,255,255,0.96) with backdrop blur for light mode, and rgba(15,23,42,0.8) for dark cinematic
  - Primary: #4F7CFF to #7C3AED gradient (electric)
  - Success: #0EB368, Warning: #FF8A2B, Danger: #FF3B5C
- **Reports Fine-Tuned:**
  - Executive Brief: becomes a hero with left accent + large serif quote style, not just blue box
  - KPI grid: 6 cards -> 3+3 with icon + trend, large 32px numbers, progress ring instead of flat bar where health
  - Matrix: sticky header, zebra, hover highlight, completion row as gradient footer, circles clickable with pill style
  - Risk tables: left border accent (red/orange), chip badges, delay as pill not just colored text
  - Collapsible: chevron rotates, header becomes sticky on scroll inside report, content has 16px padding with inner shadow
  - PDF export: same DOM, print CSS keeps cinematic but removes glass

## What Changes (File List)
1. **static/theme.css** → Rewrite to v10 cinematic:
   - New tokens: --bg, --surface, --surface-2, --border, --shadow-cinematic, --glow
   - App shell: layered background with ::before radial gradients + noise SVG
   - Nav: glass, floating
   - Cards: new .iptt-card variant with inner highlight
   - Tables: .iptt-table with better head
   - Reports: .report-hero, .kpi-card-cinematic, .matrix-table

2. **templates/partials/nav.html** → Add wrapper .iptt-nav-glass, add subtle search/command hint (no function change)

3. **templates/base.html** → Add font preconnect (Inter), keep structure

4. **Per-template inline <style> removal:** Move all inline styles into theme.css classes, keep Jinja loops intact. Templates will keep same HTML but class names updated.

5. **static/ui.js** → Enhance: smooth collapsible (height animation), progress bar observer, add .iptt-cinematic class toggle for dark/light (stored in localStorage)

6. **Reports layout:**
   - project_executive_dashboard.html: hero + KPI + matrix + risk + leadership + delayed + aging → unified .report-section with header + chevron
   - programme_executive_dashboard.html: same, side nav becomes floating glass toc
   - circle_dashboard.html / dashboard.html: same KPI style

## What DOESN'T Change
- No route, no DB model, no API, no business logic
- No new dependencies
- All existing CSS hooks like .status-green, .kpi-card, .report-card kept as aliases to new styles (backward compatible)
- All JS function names kept (toggleSection etc)

## Demo
See `/demo/index.html` — interactive preview with:
- Home mock
- Governance mock
- Executive Dashboard mock (with new report layout)
- Toggle light/dark cinematic

If approved, I apply in 3 phases:
Phase 1: theme.css v10 + nav + base + ui.js
Phase 2: home + programmes + projects + execution
Phase 3: reports (project/programme/circle/forecast) fine-tuned

## Rollback
Old theme.css is v9 — we keep it as theme.legacy.css if needed.
