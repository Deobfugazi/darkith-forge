import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ClaimRecord } from "./record.js";
import { Unit } from "./unit.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const SHELL_PATH = join(HERE, "..", "src", "reader-shell.html");

function escapeHtml(s: string): string {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function jsLiteral(s: string): string {
  return `\
    ${String(s)
      .replace(/\\/g, "\\\\")
      .replace(/`/g, "\\`")
      .replace(/\$\{/g, "\\${")
      .replace(/</g, "\\u003c")}`;
}

function splice(src: string, start: string, end: string, replacement: string): string {
  const a = src.indexOf(start);
  const b = src.indexOf(end, a);
  if (a === -1 || b === -1) {
    throw new Error("canonical reader shell marker missing — reader-shell.html must be a byte-exact twin of omega-reader.html");
  }
  return src.slice(0, a) + replacement + src.slice(b);
}

function replaceOnce(src: string, needle: string, replacement: string): string {
  const i = src.indexOf(needle);
  if (i === -1) {
    throw new Error(`canonical reader shell anchor missing: ${needle}`);
  }
  return src.slice(0, i) + replacement + src.slice(i + needle.length);
}

function claimProvenance(c: ClaimRecord): string {
  return JSON.stringify(
    {
      id: c.id,
      text: c.text,
      asserted_by: c.assertedBy,
      asserted_role: c.assertedRole.kind,
      verified_by: c.verifiedBy.map((v) => ("id" in v ? `${v.kind}:${v.id}` : v.kind)),
      real_world_referent: c.referent,
      status: c.status,
      falsifier: c.falsifier,
      anchors: c.anchors
    },
    null,
    2
  );
}

function sections(u: Unit): { id: number; title: string }[] {
  const s = [{ id: 0, title: "Front matter" }, ...u.claims.map((c, i) => ({ id: i + 1, title: c.id }))];
  if (u.falsifiers.length > 0) s.push({ id: s.length, title: "Closure" });
  return s;
}

function projection(u: Unit) {
  const secs = sections(u);
  const plain = new Map<number, string>();
  const paper = new Map<number, string>();
  const machine = new Map<number, string>();
  const provenance = new Map<number, string>();

  plain.set(0, `<p class="lede">${escapeHtml(u.contract)}</p><p>An admitted unit in the Darkith Omega Homekeeper, projected into the four registers.</p>`);
  paper.set(0, `<p class="kicker">Abstract</p><p>${escapeHtml(u.contract)}</p>`);
  machine.set(0, `unit:
  id: ${u.id}
  invariant: [A, B, C, D]
  registers: [plain, paper, machine, provenance]
  claims: ${u.claims.length}
  falsifiers: ${u.falsifiers.length}
  capability_deltas: ${u.capabilityDeltas.length}
  pseudonymous_persons: ${u.pseudonymity.pseudonymousPersons.length}`);
  provenance.set(0, `# PROVENANCE — Layer 2 projected into the reader
# Each claim: id, asserted_by, verified_by, referent, status, falsifier
# The repository (not the unit) holds the pseudonym resolution.
claims: ${u.claims.length}`);

  u.claims.forEach((c, i) => {
    plain.set(i + 1, `<h2>${escapeHtml(c.id)}</h2><p>${escapeHtml(c.anchors.plain)}</p>`);
    paper.set(i + 1, `<h2>${escapeHtml(c.id)}</h2><p>${escapeHtml(c.anchors.paper)}</p>`);
    machine.set(i + 1, claimProvenance(c));
    provenance.set(i + 1, claimProvenance(c));
  });

  const last = secs.length - 1;
  if (u.falsifiers.length > 0) {
    const falsifierList = u.falsifiers.map((f) => String(f)).join(", ");
    const deltas = u.capabilityDeltas.map((d) => ({ id: d.id, tier: d.tier, status: d.status, falsifier: d.falsifier }));
    plain.set(last, `<h2>Where this unit could be wrong</h2><p>Falsifiers: ${escapeHtml(falsifierList)}.</p>`);
    paper.set(last, `<h2>Closure</h2><p>Falsifiers: ${escapeHtml(falsifierList)}. Capability deltas: ${escapeHtml(String(u.capabilityDeltas.length))}.</p>`);
    machine.set(last, JSON.stringify({ closure: u.closure, falsifiers: u.falsifiers, capability_deltas: deltas }, null, 2));
    provenance.set(last, claimProvenance(u.claims[u.claims.length - 1] ?? ({ id: "none" } as ClaimRecord)));
  }

  const block = (m: Map<number, string>): string =>
    Array.from(m.entries())
      .map(([k, v]) => `    ${k}: \`${jsLiteral(v)}\`,`)
      .join("\n");

  const seclist = secs.map((s) => `  { id: ${s.id},  title: ${JSON.stringify(s.title)} },`).join("\n");
  const content = `const SECTIONS = [\n${seclist}\n];\n\nconst CONTENT = {\n  plain: {\n${block(plain)}\n  },\n  paper: {\n${block(paper)}\n  },\n  machine: {\n${block(machine)}\n  },\n  provenance: {\n${block(provenance)}\n  },\n};\n\n`;

  return content;
}

export function render(unit: Unit): string {
  const shell = readFileSync(SHELL_PATH, "utf8");
  const id = escapeHtml(unit.id);
  let out = splice(shell, "const SECTIONS = [", "/* ============================================================\n   2. CONTENT", `${projection(unit)}\n`);
  out = replaceOnce(out, "<title>Repository — A Unit in Four Registers</title>", `<title>${id} — A Unit in Four Registers</title>`);
  out = replaceOnce(out, 'color:var(--ink)">Repository</a>', `color:var(--ink)">${id}</a>`);
  out = replaceOnce(out, "<h1>Repository</h1>", `<h1>${id}</h1>`);
  return out;
}
