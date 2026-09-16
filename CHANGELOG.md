# IPTT Changelog

## v0.1.0
- Initial IPTT release
- Programme Management
- Project Management
- Scope Management
- Day-0 Planning
- Execution Tracking
- Reporting Dashboard

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