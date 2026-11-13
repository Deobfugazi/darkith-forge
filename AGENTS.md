# Repository notes

## What lives here

Three halves of the SAVF-1 (Signed Axis Verification Formulary) utility. All three
share the same audit semantics and are meant to agree verdict-for-verdict.

| File | Role | Notes |
| --- | --- | --- |
| `savf.py` | Python 3.9+ reference engine | stdlib only. `python3 savf.py selftest` runs the built-in suite. |
| `savf.html` | Browser audit engine | single file, fully offline. |
| `darkith code studio.html` | Single-file audit studio (v1.1 UI, SAVF core VERSION 3.0.0) | the main, most complete browser app. |

`darkith code studio.html` is one `<script>` block plus inline CSS. There is **no
build step and no network dependency** — everything must keep working from a plain
`file://` open.

## Hard rules for this codebase

1. **Zero network calls at runtime.** Never add a CDN `<script>`, `<link>`, font,
   or WASM fetch. The app must open from `file://` on any OS with no console
   errors. The code scanner is a built-in lexical pass, not Tree-sitter.
2. **OS agnostic.** Plain HTML/CSS/JS, no platform APIs, no Node-only syntax.
   Keep it to widely supported ES2020 (the one exception is `\u{...}` escapes in
   string literals, which are fine in all current browsers).
3. **Single source of truth for commands.** Every actionable button (belt, FAB,
   top bar, overflow menu) carries `data-cmd="<id>"`. Ids live in `CMD_REGISTRY`
   (metadata), `CMD_TIPS` (tooltips), and `DEFAULT_BELT` / `DEFAULT_FABS`
   (default layouts). The one global click delegate calls `dispatchCommand(id)`.
   To add a button: add the registry entry, add a `dispatchCommand` case, add a
   tip, and optionally add it to a default list. Nothing else.
4. **Persistence** goes through `cfgSet`/`cfgGet` (localStorage) for UI state and
   IndexedDB (`idbTx`/`idbKeys`, db `darkith_audit_studio` v2) for saved files.
   Theme (`auto`/`light`/`dark`), handedness, and button layouts must survive reload.

## Verdict semantics (shared contract)

- `PASS` — every claim verified.
- `LIED` — a HARD gate (phi2–5, phi7–12) failed. A false arithmetic claim is LIED.
- `BLOCKED` — a SOFT gate (phi0, phi1, phi6) failed, e.g. an unknown fact or a
  line that matches no grammar.
- `REVIEW` — nothing was evaluated (empty input).

## Editing workflow

- Edit the HTML directly; never fork a second copy of the file.
- After any JS change, extract and syntax-check:
  `python3 -c "import re;s=open('darkith code studio.html',encoding='utf-8').read();open('/tmp/m.js','w').write(re.findall(r'<script>(.*?)</script>',s,re.S)[-1])" && node --check /tmp/m.js`
- Verify in a real browser with Playwright (already installed) and **block all
  non-`file://` requests** so any reintroduced network dependency fails loudly.

## Known gotchas

- `savf.py` writes `__pycache__` when imported; delete it before committing.
- When scripting edits from Python, do not use raw strings for JS containing
  `\uXXXX` — `\U0001Fxxx` is not valid JS and lands in the file literally.
- The top bar intentionally scrolls horizontally under ~360px; secondary tools
  collapse into the `#btn-more` overflow menu below 720px.
- Safari/WebKit refuses to persist `Blob` objects in IndexedDB (the transaction
  aborts with a `null` error). Store `{__buf: ArrayBuffer, type: string}` and
  rebuild the Blob on read — see `extract`/`rehydrate` in the forge's Omega Memory.
- `Animation.finish()` dispatches its `finish` event asynchronously, so an
  out-animation from a superseded `nav()` can land later and strip `active` from
  a view the user has already returned to. `nav()` tags each transition with a
  generation counter and only the newest may settle the DOM.
- Catch handlers must tolerate `catch(e)` receiving `null` (WebKit does this for
  aborted IndexedDB transactions). Use `(e && e.message) || e`, never `e.message`.

## Integrated build (`darkith forge.html`)

`build/integrate.py` fuses `darkith home forge.html` (shell) with
`darkith code studio.html` (editor), which becomes the shell's Codebase Manager.
Run `python3 build/integrate.py` from the repo root to regenerate the output.

- The studio is carried verbatim inside `<script type="text/plain">` with
  `</script` escaped to `<\/script`, then injected as an `<iframe srcdoc>`. It
  shares the parent origin, so `localStorage` and IndexedDB are reachable from
  both halves. Do **not** add a `sandbox` attribute — it breaks `focus()`.
- The shell declares `const App`, a lexical global and **not** a `window`
  property. Reference it by name with a `window.App` fallback.
- `renderStudioPanel` builds the panel skeleton once and only re-renders the app
  list; re-rendering the whole panel detaches the iframe and wipes its document.
- Belt buttons carry both a direct click listener and the global `[data-cmd]`
  delegate; the direct listener calls `stopPropagation()` so a press runs once.

## Verifying

- Run the three-engine battery (Chromium/Firefox/WebKit) with non-`file://`
  requests blocked. All three must boot with zero page errors and zero network.
- Cross-engine is not optional: WebKit is what surfaces the Blob/IndexedDB and
  `null`-throw differences that Chromium and Firefox hide.

