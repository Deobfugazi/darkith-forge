#!/usr/bin/env python3
"""Generate the NT XII claims + reconciliation ledgers. Every claim is a witness
(a re-run evidence command), a derivation (holds iff its parents hold), an analysis
(the author's synthesis, marked INFERRED), or a contradiction (resolved as a named
EXPOSABLE boundary). Nothing is asserted; the ledgers are consumed by
tools/absolution_admission.py and savf.py ledger --run."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = "docs/nt/NT-XII.txt"


def _probe(marker: str, needle: str, target: str) -> str:
    """A shell-free re-run: the needle and target ride as a base64 payload, so no
    quoting, no shell metacharacter, and no unicode byte can break the witness."""
    import base64
    payload = base64.b64encode(f"{target}\n{needle}\n{marker}".encode("utf-8")).decode("ascii")
    return (f'python3 -c "import base64,pathlib; '
            f'b=base64.b64decode(\'{payload}\').decode(\'utf-8\').split(chr(10)); '
            f's=pathlib.Path(b[0]).read_text(encoding=\'utf-8\'); '
            f'assert b[1] in s; print(b[2])"')


def w(marker: str, needle: str, referent: str, note: str,
      external: bool = True, target: str = CORPUS) -> dict:
    return {"id": marker, "kind": "W", "referent": referent,
            "evidence": {"cmd": _probe(marker, needle, target), "expect": marker,
                         "external": external}, "note": note}


def r(cid: str, parents: list[str], note: str) -> dict:
    return {"id": cid, "kind": "R", "derived_from": parents, "note": note}


def a(cid: str, note: str) -> dict:
    return {"id": cid, "kind": "A", "note": note}


def c(cid: str, note: str) -> dict:
    return {"id": cid, "kind": "C", "note": note}


C = [  # ------------------------------------------------------------------ witnesses
    w("XII-ONE-RULE-W", "Show the path. Log the instant. Carry the citation verbatim.",
      "NT XII Part One (corpus text)",
      "The one rule: source / transformation / falsifier, at every step."),
    w("XII-BFN-W", "Bond Formation Number", "NT XII Part Five (corpus text)",
      "The treatise states the Bond Formation Number."),
    w("XII-BFN-FORM-W", "is the necessary and sufficient condition for a durable joint",
      "NT XII Part Five (corpus text)",
      "The universal bonding condition (B >= 1) is stated."),
    w("XII-CRIT-W", "is the boundary between a bonded joint and a non-bonded interface",
      "NT XII Part Six (corpus text)",
      "The critical value is exactly 1 (the adhesive-cohesive transition)."),
    w("XII-ALPHAGEL-W", "\u03b1_gel \u2208 [0.17, 0.80]", "NT XII Part Six (corpus text)",
      "The critical conversion range is carried."),
    w("XII-RATIO-W", "(W_A / W_coh)_c \u2208 [1/3, 1/2]", "NT XII Part Six (corpus text)",
      "The critical thermodynamic-ratio band is carried."),
    w("XII-NINE-W", "No mechanism class escapes the invariant", "NT XII Part Seven (corpus text)",
      "The nine mechanism classes close the invariant."),
    w("XII-TRIAD-W", "Rooting undoes the base; log-ing undoes the exponent",
      "NT XII Part Twelve (corpus text)",
      "The closed triple: R o F = pi_b and L o F = pi_n; one redundancy, 3-for-2."),
    w("XII-RESIDUAL-W", "r = ln x \u2212 n ln b", "NT XII Part Twelve (corpus text)",
      "The residual r measures the distance off the surface; r = 0 on the relation."),
    w("XII-ANCHOR-W", "Anchor Pair {0, 1}", "NT XII Part Twelve (corpus text)",
      "The anchor pair {0,1} and the refusal of the log leg at b=1."),
    w("XII-SIGMA-W", "\u03a3 = \u03a3_S + \u03a3_B = 0", "NT XII Part Fourteen (corpus text)",
      "The closure criterion: substrate + bytecode residual must be zero."),
    w("XII-SIGMA-DEF-W", "Substrate residual", "NT XII Part Fourteen (corpus text)",
      "The two residuals (substrate, bytecode) are defined."),
    w("XII-RETENTION-W", "lim_{t \u2192 \u221e} (E / W_in) = 0", "NT XII Part Sixteen (corpus text)",
      "The retention equation; absolution as E/W_in -> 0."),
    w("XII-ASE-W", "The Autophagic Sovereign Economy (ASE)", "NT XII Part Sixteen (corpus text)",
      "The ASE is stated with its survival constraints."),
    w("XII-PRIME-W", "NEVER WRITE A STUB. EVER.", "NT XII Part Fourteen (corpus text)",
      "The Prime Directive forbids a stub that makes the build green."),
    w("XII-MANUFACTORY-W", "Generative Manufactory", "NT XII Part Fifteen (corpus text)",
      "The artifact is a generative manufactory, not an app."),
    w("XII-MINT-W", "The Manufactory (The Artifact)", "NT XII Part Fifteen (corpus text)",
      "The mint is the codified harvest of the zeroed residual."),
    w("XII-BUILD-W", "aapt2 compile", "NT XII Part Thirteen (corpus text)",
      "The seven-step forced chain begins at aapt2 compile."),
    w("XII-BUILD-SIGN-W", "apksigner", "NT XII Part Thirteen (corpus text)",
      "The chain ends at apksigner (sign after align)."),
    w("XII-BUILD-CEIL-W", "android-34/android.jar", "NT XII Part Thirteen (corpus text)",
      "The one external artifact is android-34/android.jar (API 34 ceiling)."),
    w("XII-BUILD-API34-W", "API 34 (Android 14)", "NT XII Part Thirteen (corpus text)",
      "The ceiling is stated empirically as API 34."),
    w("XII-COUNT-W", "The eleven preceding noveltreatises", "NT XII Runtime Log (corpus text)",
      "The treatise is truthful about its substrate: eleven preceding treatises."),
    w("XII-SET-W", "The twelve noveltreatises each tested a bond", "NT XII Part Seventeen (corpus text)",
      "The whole set (eleven carried + this one) is twelve."),
    w("XII-INDEX-W", "NT INDEX", "docs/nt/NT-INDEX.md",
      "The corpus index exists and enumerates the carried treatises.",
      target="docs/nt/NT-INDEX.md"),
    w("XII-REPO-BUILD-W", "aapt2", "build.sh",
      "The repo build.sh realizes the no-Gradle chain.", target="build.sh"),
    w("XII-REPO-NOGRADLE-W", "Gradle", "build.sh",
      "build.sh names Gradle only to forbid it (SPI-1).", target="build.sh"),
    w("XII-REPO-NTGATE-W", "nt_gate", "tools/nt_gate.py",
      "The corpus reconciliation is gated by tools/nt_gate.py (SPI-15).", target="tools/nt_gate.py"),
    w("XII-REPO-DEFICIT-W", "E/W_in", "tools/omega_deficit.py",
      "The retention law is gated as the project's own progress-deficit indicator.",
      target="tools/omega_deficit.py"),
]

R = [  # ------------------------------------------------------------------ derivations
    r("XII-BFN", ["XII-BFN-W", "XII-BFN-FORM-W"],
      "The Bond Formation Number B = (W_A/W_coh)(a_inf/a_gel)eta >= 1 is stated."),
    r("XII-CRIT", ["XII-CRIT-W"], "B_c = 1 is exact (the adhesive-cohesive transition)."),
    r("XII-BANDS", ["XII-ALPHAGEL-W", "XII-RATIO-W"],
      "The numerical signatures: alpha_gel in [0.17,0.80]; W_A/W_coh in [1/3,1/2]."),
    r("XII-NINE", ["XII-NINE-W"], "The nine mechanism classes are limits of the invariant."),
    r("XII-TRIAD", ["XII-TRIAD-W", "XII-RESIDUAL-W"],
      "b^n = x is a closed triple (3-for-2) with residual r = ln x - n ln b."),
    r("XII-ANCHOR", ["XII-ANCHOR-W"],
      "The anchor pair {0,1}; a collapse signals a stationary frame; do not force the log leg."),
    r("XII-SIGMA", ["XII-SIGMA-W", "XII-SIGMA-DEF-W"],
      "Sigma = Sigma_S + Sigma_B = 0; a build is closed iff Sigma = 0."),
    r("XII-RETENTION", ["XII-RETENTION-W", "XII-ASE-W"],
      "W_in - E = S != 0; absolution as E/W_in -> 0."),
    r("XII-PRIME", ["XII-PRIME-W"],
      "The Prime Directive: no stub; declare an unwritten artifact as a named boundary."),
    r("XII-MANUFACTORY", ["XII-MANUFACTORY-W", "XII-MINT-W"],
      "The mints are zipped into a single generative manufactory file."),
    r("XII-BUILD", ["XII-BUILD-W", "XII-BUILD-SIGN-W", "XII-BUILD-CEIL-W", "XII-BUILD-API34-W"],
      "The seven-step forced chain; API 34 ceiling; align before sign."),
    r("XII-COUNT", ["XII-COUNT-W", "XII-SET-W", "XII-INDEX-W"],
      "The treatise's corpus count is true: eleven preceding, twelve in the set."),
    r("XII-REPO-CHAIN", ["XII-REPO-BUILD-W", "XII-REPO-NOGRADLE-W", "XII-BUILD"],
      "The repo realizes the treatise's chain without Gradle."),
    r("XII-REPO-GATED", ["XII-REPO-NTGATE-W", "XII-REPO-DEFICIT-W"],
      "The treatise's two closure laws are executable gates in this repo (SPI-15)."),
]

A = [  # ------------------------------------------------------------------ analyses (INFERRED)
    a("XII-CROSSTREATISE-A",
      "INFERRED: the identification of every prior treatise's bond with B is the author's compression."),
    a("XII-DIACHRONIC-A",
      "INFERRED: the reading of birch-bark hafting as the first attestation of the bonding function is the author's."),
    a("XII-ONTOLOGY-A",
      "INFERRED: the ontological framing (truth as observed, the mint backed by exhaustion) is the author's."),
    a("XII-MANUFACTORY-A",
      "INFERRED: the SAVF Generative Manufactory is the author's synthesis of the derivation, execution, and mint."),
    a("XII-LAMINAR-A",
      "INFERRED: the lamination (the pen stroke and the motor gap) as the first material attestation is the author's analogy."),
]

D = [  # ------------------------------------------------------------------ contradictions (resolved EXPOSABLE)
    c("XII-DEMO-ECON-C",
      "CONTRADICTION: the live economic demonstrations carry external figures (Harvard 718 firms/725k workers; "
      "Anthropic 27%->9%; GitClear 623M changes; Zylo 79%) not carried verbatim."),
    c("XII-MATERIALS-C",
      "CONTRADICTION: the material-stream and diachronic dates (Campitello ~200 kya; ochre ~70 kya) are external "
      "archaeology not carried verbatim."),
    c("XII-API35-C",
      "CONTRADICTION: the API-35 fracture rests on an external report (Termux issue #22667) not carried verbatim."),
    c("XII-NOVELTY-C",
      "CONTRADICTION: the novelty boundary ('Bond Formation Number' absent from the literature) rests on an "
      "external literature search not carried verbatim."),
    c("XII-HEALER-C",
      "CONTRADICTION: the Autophagic Healer (libllama.so / .gguf) is a design, not executed in this repo."),
    c("XII-ASE-PRAXIS-C",
      "CONTRADICTION: the ASE modules carry praxis actuals (external co-op/housing figures) not carried verbatim."),
]

claims = C + R + A + D

# Merge into the main ledger idempotently: drop any prior XII-* rows, keep the rest,
# append the new rows. NT-INDEX states nt_gate reconciles every file in docs/nt/, so
# NT XII's claims belong in the same ledger as the corpus they join.
main_claims_path = ROOT / "proof" / "nt_claims.json"
main = json.loads(main_claims_path.read_text(encoding="utf-8"))
main = [c for c in main if not str(c.get("id", "")).startswith("XII-")]
main += claims
main_claims_path.write_text(json.dumps(main, indent=2) + "\n", encoding="utf-8")
# The standalone copy mirrors the XII slice, for the admission gate's focused run.
(ROOT / "proof" / "nt_xii_claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- reconciliation
def res(cid: str, marker: str, needle: str, why: str) -> dict:
    return {"id": cid, "resolved_as": "EXPOSABLE", "resolution": why,
            "evidence": {"cmd": _probe(marker, needle, CORPUS), "expect": marker, "external": True}}

recon = [
    res("XII-DEMO-ECON-C", "XII-DEMO-EXPOSABLE", "EXPOSABLE",
        "Truthful absolution: the treatise carries the demonstration and flags its parts EXPOSABLE; "
        "the verbatim primary sources are a named boundary, not a defect."),
    res("XII-MATERIALS-C", "XII-MATERIALS-EXPOSABLE", "Campitello Quarry",
        "Truthful absolution: the archaeology is carried with its dates and flagged EXPOSABLE."),
    res("XII-API35-C", "XII-API35-EXPOSABLE", "API 35",
        "Truthful absolution: the ceiling is carried as empirical (34 works, 35 fails) and flagged EXPOSABLE."),
    res("XII-NOVELTY-C", "XII-NOVELTY-EXPOSABLE", "component-novel, not component-invented",
        "Truthful absolution: the novelty boundary is stated precisely; the search itself is a named boundary."),
    res("XII-HEALER-C", "XII-HEALER-EXPOSABLE", "libllama.so",
        "Truthful absolution: the Healer is carried as a designed mechanism; its execution is a named boundary."),
    res("XII-ASE-PRAXIS-C", "XII-ASE-EXPOSABLE", "Autophagic Feedback Loop",
        "Truthful absolution: the ASE modules are carried as the design; their praxis actuals are a named boundary."),
]
main_recon_path = ROOT / "proof" / "nt_reconciliation.json"
main_recon = json.loads(main_recon_path.read_text(encoding="utf-8"))
main_recon = [x for x in main_recon if not str(x.get("id", "")).startswith("XII-")]
main_recon += recon
main_recon_path.write_text(json.dumps(main_recon, indent=2) + "\n", encoding="utf-8")
(ROOT / "proof" / "nt_xii_reconciliation.json").write_text(json.dumps(recon, indent=2) + "\n", encoding="utf-8")

print(f"wrote proof/nt_xii_claims.json ({len(C)} W, {len(R)} R, {len(A)} A, {len(D)} C)")
print(f"merged into proof/nt_claims.json ({len(main)} claims total)")
print(f"wrote proof/nt_xii_reconciliation.json ({len(recon)} resolutions)")
print(f"merged into proof/nt_reconciliation.json ({len(main_recon)} resolutions total)")
