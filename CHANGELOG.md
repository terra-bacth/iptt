# IPTT Changelog

## v0.1.0
- Initial IPTT release
- Programme Management
- Project Management
- Scope Management
- Day-0 Planning
- Execution Tracking
- Reporting Dashboard

## v0.1.3
- Shared navigation partial now used by every page, ending the invisible-links bug
  caused by page-local CSS overriding the theme (white links on a white bar)
- Pages that had no navigation at all (audit logs, circle executive dashboard, scope pages) now have it
- The IPTT logo/brand links back to /home on every page
- Motion: navigation and section entrances, hover lift on cards, button press feedback,
  progress gauges growing, mobile menu slide, scroll reveal, all disabled by
  prefers-reduced-motion
- Footer credit is now "Hosted with ❤️ by CloudTeam", fades in and its heart beats on
  hover or keyboard focus
- Fixed the circle executive dashboard summary card (missing surface + text pushed
  outside the box by white-space handling)
- KPI tiles use two columns on phones; logo weight reduced
- scripts/check_ui.py extended to 365 checks, including navigation and motion guards

## v0.1.2
- Responsive layout extended to every page, verified from 320px phones to 1440px monitors
- Unified navigation across all screens with a keyboard-operable mobile menu
- Accessibility: WCAG AA colour palette, visible focus, skip links and labelled controls
  (axe-core reports 0 violations across 17 routes at mobile and desktop widths)
- `GET /projects` without a programme id now redirects instead of returning HTTP 422
- Shared footer on every page with the "made with ❤️ CloudTeam" credit
- Reduced static asset weight (login logo 1.3 MB -> 83 KB)
- Added `scripts/check_ui.py` UI/responsive/accessibility check

## v0.1.1
- Fixed execution plan download
- Added in-memory Excel generation