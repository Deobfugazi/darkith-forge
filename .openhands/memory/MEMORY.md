# SAVF / DARKITH Forge — session checkpoint

Written to make the next session resumable without re-deriving state.
This directory is agent scaffolding and is excluded from the delivery zip.

## State

`Σ = 0`. The engine is real and verified; nothing is outstanding.

- `python3 build/verify.py` → **VERIFY: PASS** (sync · parity · battery).
- `python3 build/sync-delivery.py --check` → **delivery: in sync**.
- Delivery zips are current: `delivery/dl/darkith-forge-delivery.zip`
  (whole project) and `darkith-webapp.zip` (apps only). Both hashes on
  `delivery/dl/index.html` match the served bytes.
- Hub `delivery/index.html` leads with the download card.
- UI: WCAG AA in both themes, 44px tap targets, no overflow 320–1280px.

## last_completed_step

Packaged the project for download: added `build/make-delivery-zip.py`,
generated both archives, added `delivery/dl/index.html`, linked them from the
hub, verified the served sha256 matches the printed one, and re-ran
`build/verify.py` (PASS) and `site_test.py` (ALL PASS).

## exact_next_step

None required. If the apps change: `python3 build/sync-delivery.py` then
`python3 build/make-delivery-zip.py`, then `python3 build/verify.py`.

## savf_residuals

Σ = 0.

## Rebuild order (if starting cold)

1. `python3 build/build-forge.py` — regenerate the three HTML artifacts.
2. `python3 build/sync-delivery.py` — copy to `delivery/`, refresh hashes.
3. `python3 build/make-delivery-zip.py` — repackage the downloads.
4. `python3 build/verify.py` — the proof.

## Final archives (this session)

- delivery/dl/darkith-forge-delivery.zip — 29,616,935 B
  sha256 e9dbeec2f95979a3ef583e2d0874b4916d3492d8e18c02c26cd4e1bdaf1747bb
- delivery/dl/darkith-webapp.zip — 494,521 B
  sha256 fd3fb3916df63d4404486a5ed404ab6b6b049897a4eea82f07b4446fb9795862

Both match the hashes printed on delivery/dl/index.html and on the served page.
