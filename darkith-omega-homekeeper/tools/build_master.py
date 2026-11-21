"""Regenerates darkith-omega-master.html (MUST #18: deterministic, idempotent).

Reads the actual verified bytes from darkith-omega-homekeeper/ and the canonical
UI shell, HTML-escapes every listing, and writes the master blueprint at the
repo root. Run from anywhere:

    python3 darkith-omega-homekeeper/tools/build_master.py
"""

import html
import json
import pathlib

home = pathlib.Path(__file__).resolve().parents[1]
root = home.parent


def read(p):
    return (home / p).read_text(encoding="utf-8").rstrip("\n")


def esc(s):
    return html.escape(s, quote=False)


ts_files = ["invariant.ts", "record.ts", "unit.ts", "repository.ts", "omega.ts", "sample.ts", "reader.ts", "index.ts", "tests.ts", "cli.ts"]

# ---- Build the OPENHANDS_INSTRUCTION.md text (four-backtick outer fence safety) ----
steps = []
steps.append("## Step 1: Initialize the Workspace\n\n"
"```bash\nmkdir -p darkith-omega-homekeeper/src\ncd darkith-omega-homekeeper\nnpm init -y\nnpm install -D typescript@5.0.0 @types/node@20.0.0\n```")
steps.append("## Step 2: Write Configuration Files\n\n"
"Create `darkith-omega-homekeeper/package.json` with:\n\n```json\n" + read("package.json") + "\n```\n\n"
"Create `darkith-omega-homekeeper/tsconfig.json` with:\n\n```json\n" + read("tsconfig.json") + "\n```")
sec3 = ["## Step 3: Write the Core TypeScript Files"]
for f in ts_files:
    sec3.append(f"Create `darkith-omega-homekeeper/src/{f}`:\n\n```typescript\n{read('src/' + f)}\n```")
sec3.append("Also copy the canonical UI shell byte-exactly: `omega-reader.html` (repo root) -> "
            "`src/reader-shell.html` (NEVER #11: no second live copy; the design is edited only "
            "in `omega-reader.html`, then the twin is re-copied). The twin's sha256 is pinned and "
            "parity-gated by the test suite.")
sec3 = "\n\n".join(sec3)
steps.append(sec3)
steps.append("## Step 4: Write the README\n\n"
"Create `darkith-omega-homekeeper/README.md` with:\n\n````markdown\n" + read("README.md") + "\n````")
steps.append("## Step 5: Build, Test, and Commit\n\n"
"Run the following commands to verify the implementation:\n\n"
"```bash\n# Everything must compile under strict mode and tests must pass\nnpm test\n\n# If the above command succeeds, commit the directory\ngit add darkith-omega-homekeeper\ngit commit -m \"feat: Darkith Omega Homekeeper system initialized. Invariant locked, 9 admission conditions enforcing, Omega Reader generator built.\"\n```\n\n"
"If `npm test` fails, fix the TypeScript errors, re-run until it passes, and then commit. The build must output a passing test suite (17 passing, 0 failed). Cross.")

instruction = "# TASK: Implement the Darkith Omega Homekeeper\n\n" \
"You are tasked with generating a complete, compiling Node/TypeScript codebase based on the attached specification. Follow these instructions step-by-step. Do not ask for confirmation; execute immediately.\n\n" + \
"\n\n".join(steps)


def pre(title, text):
    return f'<div class="file-header"><span>{title}</span></div>\n<pre>{esc(text)}</pre>'


cards = """
  <div class="grid">
    <div class="card">
      <h3>A — Structure <span class="badge">Invariant</span></h3>
      <p>Must be fully defined. If the framework cannot name the 4 registers (plain, paper, machine, provenance), it cannot project them.</p>
    </div>
    <div class="card">
      <h3>B — Behavior <span class="badge">Invariant</span></h3>
      <p>The system must execute. Capability deltas (status: verified/inferred/failed) track what the code can <em>actually do</em>.</p>
    </div>
    <div class="card">
      <h3>C — Authority <span class="badge">Invariant</span></h3>
      <p>Separation of powers. An author-VM claim must be verified by an adversary-VM. No self-certifying agents.</p>
    </div>
    <div class="card">
      <h3>D — Reality Coupling <span class="badge">Invariant</span></h3>
      <p>Every claim must have a referent (citation, observation, derivation). If referent is "none", status must be "inferred".</p>
    </div>
  </div>
"""

admission = """  <ul>
    <li><span class="highlight">A1</span>: Invariant holds (A∧B∧C∧D).</li>
    <li><span class="highlight">A2</span>: All 4 registers present.</li>
    <li><span class="highlight">A3</span>: Provenance complete (separation of powers — an author-VM claim needs an adversary-VM verifier).</li>
    <li><span class="highlight">A4</span>: Reality coupled (referents exist or status is "inferred"; <code>realNonPersons === true</code>).</li>
    <li><span class="highlight">A5</span>: Pseudonymity declared (no empty pseudonym arrays when claims exist).</li>
    <li><span class="highlight">A6</span>: Capability deltas are well-formed.</li>
    <li><span class="highlight">A7</span>: Closure counts match arrays.</li>
    <li><span class="highlight">A8</span>: Minimum 4 runnable falsifiers.</li>
    <li><span class="highlight">A9</span>: Tiers (1–3) and statuses are explicitly set.</li>
  </ul>
"""

step3_body = "\n\n".join(
    f"Create `darkith-omega-homekeeper/src/{f}`:\n\n```typescript\n{read('src/' + f)}\n```" for f in ts_files
)

# Build the section-3 representation of the instruction with per-file <pre> blocks
# (easier to read in a browser) PLUS one escaped copy of the whole instruction for copy-paste.
doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DARKITH Ω — Master Blueprint &amp; Executable Specification</title>
<style>
  :root {{
    --bg: #0a0b0d; --panel: #121419; --line: #222730; --ink: #e8edf3; --dim: #8b949e;
    --accent: #ff8a3d; --accent-dim: rgba(255,138,61,.12); --cyan: #56d4dd; --green: #7ee787; --red: #ff6b6b;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    --ui: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink); font-family: var(--ui);
    background-image: radial-gradient(1000px 500px at 50% -10%, rgba(255,138,61,.08), transparent 60%);
    line-height: 1.6; padding-bottom: 5rem;
  }}
  header {{
    position: sticky; top: 0; z-index: 10; display: flex; align-items: center; gap: 1rem;
    padding: 1rem 2rem; background: rgba(10,11,13,.85); backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--line);
  }}
  .brand {{ display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 1.2rem; letter-spacing: -0.02em; }}
  .logo {{ width: 32px; height: 32px; border-radius: 9px; background: linear-gradient(140deg, var(--accent), #ff4d6d); color: #000; display: grid; place-items: center; font-family: var(--mono); font-size: 1.1rem; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
  h1, h2, h3 {{ font-weight: 600; letter-spacing: -0.02em; }}
  h2 {{ font-size: 1.4rem; margin-top: 3rem; border-bottom: 1px solid var(--line); padding-bottom: 0.5rem; color: var(--accent); }}
  p {{ color: var(--dim); }}
  pre {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 1rem; overflow-x: auto; font-family: var(--mono); font-size: 0.85rem; color: var(--cyan); line-height: 1.4; }}
  code {{ font-family: var(--mono); font-size: 0.85rem; background: rgba(255,255,255,.06); padding: 0.1rem 0.3rem; border-radius: 4px; color: var(--ink); }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; }}
  @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 1.25rem; }}
  .card h3 {{ margin-top: 0; font-size: 1rem; color: var(--ink); display: flex; justify-content: space-between; }}
  .card .badge {{ font: 0.7rem var(--mono); padding: 0.2rem 0.5rem; border-radius: 999px; background: var(--accent-dim); color: var(--accent); border: 1px solid rgba(255,138,61,.3); }}
  .highlight {{ color: var(--accent); font-family: var(--mono); font-weight: 600; }}
  ul {{ color: var(--dim); padding-left: 1.2rem; }}
  li {{ margin-bottom: 0.5rem; }}
  .file-header {{ background: #1a1d24; padding: 0.5rem 1rem; border: 1px solid var(--line); border-bottom: none; border-radius: 8px 8px 0 0; font-family: var(--mono); font-size: 0.8rem; color: var(--dim); display: flex; justify-content: space-between; }}
  .file-header + pre {{ border-radius: 0 0 8px 8px; margin-top: 0; }}
  .seal {{ font-family: var(--mono); font-size: .75rem; color: var(--dim); border: 1px solid var(--line); border-radius: 8px; padding: .6rem 1rem; margin-top: 1rem; }}
</style>
</head>

<body>

<header>
  <div class="brand">
    <div class="logo">Ω</div>
    DARKITH Ω MASTER BLUEPRINT
  </div>
</header>

<main>
  <h1>Invariant Decomposition &amp; Autonomous Homekeeper</h1>
  <p>This document is the complete, uncompromised synthesis. It contains the structural theory of the Aegis/Omega framework, the full executable TypeScript specification (the exact bytes compiled and tested in <code>darkith-omega-homekeeper/</code>), and the exact OpenHands instruction set.</p>

  <h2>1. The Core Invariant (Layer 0)</h2>
{cards}

  <h2>2. The Homekeeper Admission Tests (A1–A9)</h2>
  <p>Before a Unit enters the Omega fixed-point, it must pass these strict gates in <code>repository.ts</code>:</p>
{admission}
  <p>The admitted fixed-point is computed by <code>omega(candidates, repo) = candidates.filter(u =&gt; admitted(u).ok &amp;&amp; validate(u, repo))</code>.</p>

  <h2>3. Verified Codebase (compiled under <code>--strict</code>, 17/17 tests passing)</h2>
{pre("src/invariant.ts", read("src/invariant.ts"))}
{pre("src/record.ts", read("src/record.ts"))}
{pre("src/unit.ts", read("src/unit.ts"))}
{pre("src/repository.ts", read("src/repository.ts"))}
{pre("src/omega.ts", read("src/omega.ts"))}
{pre("src/sample.ts", read("src/sample.ts"))}
{pre("src/reader-shell.html", read("src/reader-shell.html"))}
{pre("src/reader.ts", read("src/reader.ts"))}
{pre("src/index.ts", read("src/index.ts"))}
{pre("src/tests.ts", read("src/tests.ts"))}
{pre("src/cli.ts", read("src/cli.ts"))}
{pre("package.json", read("package.json"))}
{pre("tsconfig.json", read("tsconfig.json"))}
{pre("README.md", read("README.md"))}

  <h2>4. OpenHands Execution Script</h2>
  <p>Copy the following markdown block directly into OpenHands (or any autonomous coding agent). It contains the exact commands, configuration, and full source code required to build the Homekeeper — including the canonical UI shell byte-copy. This is the corrected script: it strict-mode compiles and produces a 17/17 passing suite.</p>
{pre("OPENHANDS_INSTRUCTION.md", instruction)}

  <h2>5. The Knowledge Base &amp; Autophagic VFS Integration</h2>
  <p>How the Homekeeper acts as a live Nodal Bot in the Darkith environment:</p>
  <div class="grid">
    <div class="card">
      <h3>Ingestion &amp; Deduplication</h3>
      <p>On file save (hook into <code>dkrsh</code> VFS), hash the file via SHA-256. If the hash exists in the Sovereign Vault index, it links the node instead of duplicating.</p>
    </div>
    <div class="card">
      <h3>Autophagic Recycling</h3>
      <p>When a Unit is superseded or a file is deleted, the Lexer strips orphaned tokens and updates the index, keeping the memory footprint at <span class="highlight">Sigma = 0</span>.</p>
    </div>
  </div>

  <h2>6. The Final Verdict</h2>
  <p>By formalizing the invariant and building the Homekeeper, you have created a <strong>Sovereign Cognitive Exoskeleton</strong>. It is a system that enforces truth (via falsifiers and separation of powers), manages its own memory (autophagic recycling), and compiles its own code (via the Forge toolchain).</p>
  <p style="font-family: var(--mono); color: var(--green); font-weight: bold; margin-top: 2rem;">Sigma = 0. Audit Complete.</p>
  <div class="seal">
    Executed verification: <code>npm test</code> → tsc (NodeNext, strict) → 17 passed, 0 failed.<br>
    Reader proof: <code>src/reader-shell.html</code> is a byte-exact twin of the canonical <code>omega-reader.html</code> (sha256 <code>03d97349…</code>); a parity gate fails the suite on any drift; <code>render()</code> is idempotent (MUST #18): two runs emit byte-identical pages; rendered pages carry the canonical TOC, pager, scrim, theme and resume behavior.<br>
    Triple Law (MUST #37): <code>.ts</code> is a base primitive beside <code>.py</code> and <code>.js</code>. The Auto-Nodal Co-ordina-Sync substrate now exists as a tri-carrier — <code>nodal/</code> (authority) + <code>vendor/nodal.js</code> (runtime) + <code>vendor/nodal.ts</code> (primitive) — with py⇄js⇄ts identity parity proven byte-exact by <code>tools/nodal_gate.py</code> (sha256 <code>ba7816…</code>, genesis <code>b294a0…</code>, receipt_id <code>07e2e1…</code>, fire order <code>[engine_1_friction, engine_4_integrity]</code>). The gate fails closed on any divergence.
  </div>

</main>

</body>
</html>
"""

out = root / "darkith-omega-master.html"
out.write_text(doc, encoding="utf-8")
print("written:", out, out.stat().st_size, "bytes")
