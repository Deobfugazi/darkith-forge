# NT IX Device-Coupled Candidate — Isolated Testnet

Branch: `testnet/nt-ix-device-coupled-candidate-2026-11-29`
Base: `main`
Purpose: Claude-agent review and isolated trial only. Do not merge or promote to main.

This branch is a handoff/control branch. It contains the candidate audit and corrected installer. It does NOT contain the full expanded candidate source snapshot or the candidate ZIP. The source archive is currently an external conversation attachment and is not downloadable by a remote clone from this branch. Do not treat this branch alone as the implementation source until the full source bundle is transferred and committed.

Candidate ZIP SHA-256 (external attachment):
`d40d4d542f3be63d78a141416d06699e18edc0acc2f172ea1776f062e063d2ea`

Audit SHA-256:
`76f8178698255f08b8f4033b1a1424cc18b4a2370955bd04194d5283a36f741a`

Installer SHA-256:
`e374a4001e3276b41b86643c2da473f77761100cc1ac3a216ee9651a314174bc`

Candidate state: source-level partial repairs; not full CI verified; not Android compiled; not installed; not TECNO runtime accepted. Keyboard gate remains expected-failing until native IME/lexical/prediction/clipboard-history functions are implemented.

Claude agent should clone this branch into its own ephemeral workspace, inspect the audit and installer, then obtain the exact candidate ZIP from the originating conversation attachment before attempting source integration. Preserve the branch as isolated; no main merge or release.
