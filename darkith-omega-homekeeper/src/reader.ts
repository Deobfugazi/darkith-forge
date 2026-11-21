import { Unit } from "./unit.js";

export function render(unit: Unit): string {
  const claims = JSON.stringify(unit.claims).replace(/</g, "\\u003c");
  const unitId = JSON.stringify(unit.id).replace(/</g, "\\u003c");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${unit.id} — Darkith Omega Homekeeper</title>
<style>
  :root { --bg: #fbfaf7; --ink: #1b1b1b; --muted: #6b6b6b; --rule: #d9d5cc; --accent: #7a3e1d; --panel: #f2efe8; --max: 46rem; --mono: ui-monospace, monospace; }
  [data-theme="dark"] { --bg: #141414; --ink: #e8e4dc; --muted: #9a958c; --rule: #2e2c28; --accent: #d99a6c; --panel: #1d1c1a; }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.65 Georgia, serif; transition: background .2s, color .2s; }
  #bar { position: sticky; top: 0; z-index: 10; display: flex; gap: .5rem; align-items: center; padding: .55rem 1rem; background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(6px); border-bottom: 1px solid var(--rule); font-family: system-ui, sans-serif; font-size: .82rem; }
  #bar a, #bar button { color: var(--muted); text-decoration: none; background: none; border: 1px solid transparent; border-radius: 6px; padding: .3rem .55rem; cursor: pointer; font: inherit; }
  #bar a:hover, #bar button:hover { color: var(--ink); border-color: var(--rule); }
  #bar .grow { flex: 1; }
  #bar .vol { border: 1px solid var(--rule); border-radius: 999px; padding: .28rem .7rem; }
  #bar .vol[aria-current="true"] { background: var(--ink); color: var(--bg); border-color: var(--ink); }
  main { max-width: var(--max); margin: 0 auto; padding: 3rem 1.4rem 8rem; }
  h1, h2 { font-family: system-ui, sans-serif; }
  .bookmarks { display: grid; gap: 1rem; margin: 2.2rem 0; }
  @media (min-width: 640px) { .bookmarks { grid-template-columns: repeat(4, 1fr); } }
  .bookmark { display: block; text-decoration: none; color: var(--ink); background: var(--panel); border: 1px solid var(--rule); border-radius: 10px; padding: 1.2rem; }
  .bookmark strong { display: block; font-family: system-ui, sans-serif; margin-bottom: .3rem; }
  pre { background: var(--panel); border: 1px solid var(--rule); border-radius: 8px; padding: 1rem; overflow-x: auto; font-family: var(--mono); font-size: .82rem; }
  details.provenance { margin: 1rem 0; padding: .6rem .8rem; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; font-family: var(--mono); font-size: .78rem; }
  details.provenance summary { cursor: pointer; color: var(--accent); font-family: system-ui, sans-serif; text-transform: uppercase; }
</style>
</head>
<body data-theme="light">
<header id="bar">
  <a href="#/home" style="font-weight:600;color:var(--ink)">${unit.id}</a>
  <span class="grow"></span>
  <a class="vol" data-vol="plain" href="#/plain/0">Plain</a>
  <a class="vol" data-vol="paper" href="#/paper/0">Paper</a>
  <a class="vol" data-vol="machine" href="#/machine/0">Machine</a>
  <a class="vol" data-vol="provenance" href="#/provenance/0">Provenance</a>
  <button id="theme">◐</button>
</header>
<main id="view"></main>
<script>
  const claims = ${claims};
  const unitId = ${unitId};
  function render() {
    const h = location.hash.replace(/^#\\/?/, "");
    const [vol, sid] = h.split("/");
    const view = document.getElementById("view");
    if (!vol || vol === "home") {
      view.innerHTML = \`<h1>\${unitId}</h1><p>An Admitted Unit in the Darkith Omega Homekeeper.</p>
        <div class="bookmarks">
          <a class="bookmark" href="#/plain/0"><strong>Plain</strong>No prior knowledge assumed.</a>
          <a class="bookmark" href="#/paper/0"><strong>Paper</strong>Full technical argument.</a>
          <a class="bookmark" href="#/machine/0"><strong>Machine</strong>Structured data.</a>
          <a class="bookmark" href="#/provenance/0"><strong>Provenance</strong>Layer 2 projected.</a>
        </div>\`;
      document.querySelectorAll("#bar .vol").forEach(a => a.removeAttribute("aria-current"));
      return;
    }
    document.querySelectorAll("#bar .vol").forEach(a => a.setAttribute("aria-current", String(a.dataset.vol === vol)));
    let content = \`<p>Content for \${vol} register, section \${sid || 0}.</p>\`;
    if (vol === "provenance") {
       const claim = claims.find(c => c.id.includes("-" + (sid || "0")));
       content = \`<pre>\${claim ? JSON.stringify(claim, null, 2) : "No claim record for this section."}</pre>\`;
    } else if (vol === "machine") {
       content = \`<pre>\${unitId}: \${vol} register mapped to structured output.</pre>\`;
    } else if (vol === "paper") {
       content = \`<h1>Section \${sid || 0}</h1><p>The technical argument for this section.</p>
       <details class="provenance"><summary>Provenance</summary><pre>Claims mapped to this section.</pre></details>\`;
    }
    view.innerHTML = \`<p style="font-family:system-ui; font-size:.75rem; letter-spacing:.14em; text-transform:uppercase; color:var(--muted)">\${vol} · \${sid || 0}</p><h1>Section \${sid || 0}</h1>\${content}\`;
  }
  document.getElementById("theme").onclick = () => {
    const next = document.body.dataset.theme === "dark" ? "light" : "dark";
    document.body.dataset.theme = next;
    try { localStorage.setItem("omega-theme", next); } catch (e) {}
  };
  try { document.body.dataset.theme = localStorage.getItem("omega-theme") || "light"; } catch (e) {}
  window.addEventListener("hashchange", render); render();
</script>
</body>
</html>`;
}
