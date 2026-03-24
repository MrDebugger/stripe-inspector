# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-03-24

### Added
- Cross-platform PDF reports using xhtml2pdf (works on Windows/Mac/Linux, no system deps)
- Dedicated PDF template with clean white pentest-report style
- Friendly error messages for PDF failures

### Changed
- Replaced weasyprint with xhtml2pdf for PDF generation
- PDF tables limited to 7 columns, values truncated at 24 chars
- Section titles tighter to their content
- Cache-busted static assets with version query string (built once at startup)
- Web UI JS falls back to POST /api/inspect when SSE streaming unavailable

### Fixed
- CSS variables resolved for PDF renderer
- GitHub corner SVG broken path data
- Column overlap in PDF tables

## [0.6.0] - 2026-03-24

### Added
- **Scan history** — saved to localStorage, floating clock button with badge, slide-out panel to reload past scans (max 20)
- **API-only mode** — `stripe-inspector serve --api-only` starts just the API without web UI
- **GitHub corner ribbon** — diagonal octocat in top-right, waves on hover
- **Floating social icons** — GitHub (with bounce + notification dot + "Star us" bubble) and PyPI in bottom-left
- **Favicon** — inline SVG "SI" monogram
- **Docker support** — `docker compose up` for one-command deployment

### Changed
- GitHub/PyPI links moved from nav bar to floating icons
- Mobile responsive: nav padding for corner ribbon, actions bar wraps, KV rows stack, history panel 85vw
- Timestamps formatted at core level with both raw and `_formatted` fields

### Fixed
- GitHub bubble fade-out (CSS animation override)
- Nav items hidden under corner ribbon on mobile

## [0.5.1] - 2026-03-24

### Changed
- Renamed "Report" to "Inspection" throughout the UI and templates for consistent branding
- Share flow uses custom modal with warning instead of browser confirm dialog
- Actions bar (Copy JSON, Download, Share) now renders at top and bottom of results
- Shared inspection page has sticky toolbar with "New Inspection" and "GitHub" buttons
- API routes renamed: `/api/report/share` → `/api/inspection/share`, `/report/<id>` → `/inspection/<id>`

### Fixed
- Scan duration not showing in web UI (SSE stream was missing `duration_seconds`)
- HTML report not rendering disputes, refunds, balance_transactions, coupons (missing list keys in template)
- HTML report showing permission_scan as raw key-value (added dedicated renderer)
- Share modal resets properly when closed and reopened

## [0.5.0] - 2026-03-24

### Added
- **CSV export** — `--csv <dir>` exports per-module CSV files
- **Silent mode** — `--silent` suppresses table output (for scripted use with --report/--csv)
- **Diff command** — `stripe-inspector diff key1 key2` compares permissions and endpoint access between two keys
- **Scan duration timer** — shows how long the scan took in CLI and web UI
- **Copy JSON** button in web UI with clipboard fallback for HTTP
- **Share Report** — opens HTML report in new browser tab
- **Dark/Light theme toggle** — persists to localStorage
- **Top navigation bar** — Privacy, Docs, GitHub, PyPI links
- **Ethics banner** — yellow warning about authorized use only
- **Privacy modal** — no data collection, self-hosted, key masking, no warranty
- **Docs modal** — installation, CLI usage, modules, key types, output formats
- **SSE streaming** — web UI shows real-time progress as each module completes (POST-based, key never in URL)
- **Permission scan renderer** — web UI now properly displays OK/NO/error per endpoint

### Fixed
- Module chips in web UI replaced with data-attribute spans (no more native checkbox rendering)
- Permission scan showing 0/0/0 in web UI (missing dedicated renderer)
- Key no longer sent as GET parameter to SSE endpoint (moved to POST body)

## [0.4.0] - 2026-03-24

### Added
- **Deep pagination** — `--deep` flag fetches all pages instead of first 100 items (up to 5000 per module)
- Deep mode toggle in web UI and API (`deep: true` in request body)
- `stripe_get_all()` base function for paginated Stripe API calls with cursor-based pagination
- Deep mode support in batch command

## [0.3.0] - 2026-03-24

### Added
- **Multi-key batch mode** — `stripe-inspector batch keys.txt` scans multiple keys from a file with optional per-key HTML reports
- **PII exposure summary** — auto-detects and counts emails, names, phones, card numbers, countries across all modules
- **Rate limit tracking** — shows API request count and remaining rate limit in output
- **`--version` / `-V` flag** — displays current version
- **Timestamp formatting** — Unix timestamps in tables now show human-readable dates

## [0.2.0] - 2026-03-24

### Added
- 5 new modules: disputes, refunds, balance_transactions, coupons, permission_scan
- Permission scanner probes 35+ Stripe API endpoints to build a full access matrix
- PDF report generation via `--pdf` flag (requires `pip install stripe-inspector[pdf]`)
- Module selector in web UI with toggle chips, All/None buttons
- Terminal logo and animated demo SVG for README
- CHANGELOG, CONTRIBUTING docs
- Professional README with badges, module table, usage examples

### Changed
- CLI spinner replaced with threaded implementation for Windows compatibility
- Version bumped to 0.2.0

## [0.1.0] - 2026-03-23

### Added
- Initial release
- Core inspection engine with 12 modules: account, balance, customers, charges, payment_intents, products, payouts, subscriptions, invoices, webhooks, events, connected accounts
- CLI interface with `inspect`, `serve`, and `list-modules` commands
- Table, JSON, and HTML report output formats
- FastAPI web UI with dark theme
- Auto-detection of key types (secret/restricted, test/live)
- Per-module permission tracking
- Optional bearer token auth for web UI
- Module filtering with `--modules` flag
- Key masking in reports and output
