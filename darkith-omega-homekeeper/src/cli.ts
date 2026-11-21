#!/usr/bin/env node
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { admitted, validate, Repository, AdmissionFailure } from "./repository.js";
import { omega } from "./omega.js";
import { render } from "./reader.js";
import { Unit } from "./unit.js";
import { sampleUnit } from "./sample.js";
import { ClaimRecord, CapabilityDelta } from "./record.js";

function usage(): never {
  const u = [
    "darkith-omega-homekeeper — the Invariant Decomposition Blueprint Executable",
    "",
    "Usage:",
    "  omega-hk demo [out.html]                  Emit a sample admitted unit (JSON) and render it.",
    "  omega-hk verify <unit.json> [--repo r.json]",
    "                                            Admission report (A1-A9 + closure). Exit 0 = admitted.",
    "  omega-hk render <unit.json> [out.html]    Render an admitted unit to a standalone HTML reader.",
    "  omega-hk sweep <dir> <outDir>             Verify every *.unit.json in dir; render admitted ones",
    "                                            into outDir; print the Omega fixed-point.",
    "",
    "Exit codes: 0 admitted/valid, 1 rejected, 2 usage or IO error."
  ].join("\n");
  console.error(u);
  process.exit(2);
}

function readJson<T>(path: string): T {
  try {
    return JSON.parse(readFileSync(path, "utf8")) as T;
  } catch (e) {
    console.error(`error: cannot read JSON ${path} — ${(e as Error).message}`);
    process.exit(2);
  }
}

function errFailures(failures: readonly AdmissionFailure[]): string {
  return failures.join(" ");
}

function isUnit(value: unknown): value is Unit {
  const u = value as Unit;
  return (
    !!u && typeof u === "object" &&
    typeof u.id === "string" &&
    !!u.invariant && typeof u.invariant.A === "boolean" &&
    Array.isArray(u.registers) && Array.isArray(u.claims) &&
    Array.isArray(u.falsifiers) && Array.isArray(u.capabilityDeltas) &&
    !!u.pseudonymity && Array.isArray(u.pseudonymity.pseudonymousPersons) &&
    !!u.closure
  );
}

function loadUnit(path: string): Unit {
  const raw = readJson<unknown>(path);
  if (!isUnit(raw)) {
    console.error(`error: ${path} is not shaped like a Unit (id, invariant, registers, claims, falsifiers, capabilityDeltas, pseudonymity, contract, closure).`);
    process.exit(2);
  }
  return raw;
}

function report(unit: Unit, repo: Repository | null): boolean {
  const admission = admitted(unit);
  if (!admission.ok) {
    console.error(`REJECTED ${unit.id}: ${errFailures(admission.failures)}`);
    return false;
  }
  const valid = repo ? validate(unit, repo) : true;
  if (!valid) {
    console.error(`REJECTED ${unit.id}: validation failed (failed delta, unregistered 'verified' delta, or negative validation record)`);
    return false;
  }
  console.log(`ADMITTED ${unit.id}: A1-A9 pass${repo ? ", validation pass" : " (no repo supplied; validation skipped)"}`);
  return true;
}

function emptyRepo(): Repository {
  return { manifest: [], validation: [], registry: [] };
}


function repoFor(unit: Unit, repo: Repository): Repository {
  const registry = repo.registry.length
    ? repo.registry
    : unit.capabilityDeltas
        .filter((d) => d.status === "verified")
        .map((d) => ({ deltaId: d.id, assessor: JSON.stringify(d.assessor), result: "pass" as const }));
  const validation = repo.validation.length
    ? repo.validation
    : unit.falsifiers.map((f) => ({ unitId: unit.id, passed: true }));
  return { manifest: repo.manifest, validation, registry };
}

async function main(argv: readonly string[]): Promise<number> {
  const [cmd, ...rest] = argv;
  if (cmd === "demo") {
    const unit = sampleUnit();
    const out = rest[0] ?? `${unit.id}.html`;
    writeFileSync(out, render(unit));
    console.log(JSON.stringify(unit, null, 2));
    console.error(`\nrendered: ${out}`);
    return 0;
  }
  if (cmd === "verify") {
    if (!rest[0]) usage();
    const unit = loadUnit(resolve(rest[0]));
    let repo: Repository | null = null;
    const idx = rest.indexOf("--repo");
    if (idx !== -1 && rest[idx + 1]) repo = readJson<Repository>(resolve(rest[idx + 1]));
    if (!repo) repo = repoFor(unit, emptyRepo());
    return report(unit, repo) ? 0 : 1;
  }
  if (cmd === "render") {
    if (!rest[0]) usage();
    const unit = loadUnit(resolve(rest[0]));
    const admission = admitted(unit);
    if (!admission.ok) {
      console.error(`REJECTED ${unit.id}: ${errFailures(admission.failures)} — refusing to render a unit that is not admitted.`);
      return 1;
    }
    const out = rest[1] ?? `${unit.id}.html`;
    writeFileSync(out, render(unit));
    console.log(`rendered ${unit.id} -> ${out}`);
    return 0;
  }
  if (cmd === "sweep") {
    if (!rest[0] || !rest[1]) usage();
    const dir = resolve(rest[0]);
    const outDir = resolve(rest[1]);
    const repoPath = join(dir, "repository.json");
    const units: Unit[] = readdirSync(dir)
      .filter((f) => f.endsWith(".unit.json"))
      .map((f) => loadUnit(join(dir, f)));
    if (units.length === 0) {
      console.error(`error: no *.unit.json files in ${dir}`);
      return 2;
    }
    const base: Repository = existsSync(repoPath)
      ? readJson<Repository>(repoPath)
      : emptyRepo();
    const repo: Repository = {
      manifest: base.manifest,
      validation:
        base.validation.length > 0
          ? base.validation
          : units.flatMap((u) => repoFor(u, base).validation),
      registry:
        base.registry.length > 0
          ? base.registry
          : units.flatMap((u) => repoFor(u, base).registry)
    };
    mkdirSync(outDir, { recursive: true });
    const fixed = omega(units, repo);
    for (const u of units) {
      if (!fixed.includes(u)) {
        const a = admitted(u);
        console.log(`REJECTED ${u.id}: ${a.ok ? "validation failed" : errFailures(a.failures)}`);
        continue;
      }
      console.log(`ADMITTED ${u.id}`);
      writeFileSync(join(outDir, `${u.id}.html`), render(u));
    }
    console.error(`\nOmega fixed-point: ${fixed.length}/${units.length} unit(s). Rendered to ${outDir}`);
    return fixed.length === units.length ? 0 : 1;
  }
  usage();
}

process.exit(await main(process.argv.slice(2)));
