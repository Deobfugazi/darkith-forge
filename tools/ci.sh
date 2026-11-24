#!/usr/bin/env bash
# ci.sh — the repository's tests, in ONE provider-neutral place.
#
# This file is the source of truth for "do the tests pass". It knows nothing about
# GitHub, GitLab, Bitbucket, Jenkins or any other CI vendor: it runs the suites and
# exits 0 only if every one passes. Any CI system (or a phone in Termux) can call it:
#
#     bash tools/ci.sh
#
# A vendor's YAML (e.g. .github/workflows/*.yml) must stay a thin adapter that calls
# this script — never a second copy of the logic. Copying the logic into a vendor file
# is what makes a repo a hostage to one provider; this script is what makes it portable.
#
# Exit status: 0 = every check passed, non-zero = at least one failed.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

# A bundled JVM is part of the toolchain: kotlinc cannot run without one, and a gate that
# cannot run its harness reports a code defect that does not exist. Export it here so every
# compile gate tells the truth on a machine with no system java.
if [ -x "$ROOT/.tools/jdk-17.0.12+7/bin/java" ]; then
  # Keep JAVA_HOME and PATH aligned: kotlinc may prefer JAVA_HOME over PATH.
  JAVA_HOME="$ROOT/.tools/jdk-17.0.12+7"
  export JAVA_HOME
  case ":$PATH:" in
    *":$JAVA_HOME/bin:"*) ;;
    *) PATH="$JAVA_HOME/bin:$PATH"; export PATH ;;
  esac
fi

FAILED=0
SKIPPED=0

# Log to disk (SPI-4). The terminal is a liar: it scrolls, it truncates, and a run that is
# not on disk cannot be re-read, cannot be receipted, and cannot be audited later. Every line
# this script prints is also appended to CI_LOG, and the receipt emitter parses that file
# rather than a remembered summary.
CI_LOG="${CI_LOG:-$ROOT/proof/ci_last.log}"
mkdir -p "$(dirname "$CI_LOG")" 2>/dev/null || true
: > "$CI_LOG" 2>/dev/null || true
# Tee the whole run: stdout keeps its normal shape for a human, the file keeps it for a
# machine. `exec` with process substitution keeps the exit status of this script intact.
if [ -w "$(dirname "$CI_LOG")" ]; then
  exec > >(tee -a "$CI_LOG") 2>&1
fi

run() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  # A gate signals SKIP with exit 3. Anything else non-zero is a FAIL. The distinction
  # matters because "the runtime is absent" and "the check ran and passed" are different
  # facts, and collapsing them into one green line is how a tree ships looking verified
  # when nothing verified it. A skip is never a PASS (SPI-15 / NEVER #13).
  if "$@"; then
    printf -- '--- %s: PASS\n' "$name"
  else
    local rc=$?
    if [ "$rc" -eq 3 ]; then
      printf -- '--- %s: SKIP (exit 3)\n' "$name"
      SKIPPED=$((SKIPPED+1))
    else
      printf -- '--- %s: FAIL (exit %s)\n' "$name" "$rc"
      FAILED=1
    fi
  fi
}

# Each suite is skipped only when its runtime is genuinely absent, and a skip is
# announced loudly — a silent skip is how a broken tree ships looking green.
have() { command -v "$1" >/dev/null 2>&1; }

if have python3; then
  # ── ABSOLUTION IS A PRECONDITION OF HASHING, NOT A REPORT FILED AFTER IT ────────
  # This ran wrong for months: the hashing gates ran first, and the defect registry ran
  # last as a dry `--check` that repairs nothing. So CI sealed a tree that still held every
  # residual inconsistency, then detected the inconsistency, then did nothing about it —
  # detect-forever, heal-never. `--repair` was never called by CI at all.
  #
  # The order is the defect. You cannot attest bytes that are still moving. This phase
  # ingests every producer that absorbs outside state, runs the registry to repair, and
  # loops until residue is zero BEFORE any gate below hashes anything. If it cannot reach
  # zero it REFUSES, and the hashing gates never run on an inconsistent tree — so a seal
  # can never attest a lie. That refusal is the prophylaxis, and it is not destructive:
  # the phase only produces a consistent working tree and proves it, then hands it on.
  if [ -f tools/absolution_phase.py ]; then
    run "absolution phase (ingest+repair to zero before hashing)" python3 tools/absolution_phase.py
    run "absolution phase selftest"                               python3 tools/absolution_phase.py --selftest
  fi
  run "repo gate (build/verify.py --fast)" python3 build/verify.py --fast
  run "savf cli contract"                 python3 build/savf-cli-test.py
  run "darkbot self-test"                 python3 tools/darkbot.py selftest
  # Secret gate (fail-closed): no credential may ever be committed to the tracked tree.
  # A hit is not just a red line: push the dedup'd device alert so the Operator learns
  # at once (MUST #31). The gate stays the source of truth for pass/fail; the alert is
  # best-effort and never masks the failure (the gate's own exit code still governs).
  if ! python3 tools/secret_gate.py; then
    python3 tools/security_alert.py push --severity critical \
      --finding-id "committed-credential" \
      --title "SECURITY: a credential-shaped string is committed to the tree" \
      --body "tools/secret_gate.py failed in CI. See the run log for the exact path:line.\n\nA credential in the tree is already leaked (forks, backups, logs, git history): remove it\nAND rotate it. A rewrite does not un-leak it. This notice was created by an AI agent\n(OpenHands) on behalf of the Operator." || true
    FAILED=1
  fi
  run "secret gate self-test"             python3 tools/secret_gate.py selftest
  # Fracture Scout: offline proof its boolean parser, adapters, and ranker are correct.
  run "fracture scout self-test"          python3 tools/fracture_scout.py selftest
  # Burden gates: BURDEN-GATE-1 (double-count registry) and BURDEN-GATE-2 (witness
  # strength) were disclosed as ABSENT by the first rehearsal and refused their phantoms
  # only by admission review. Written down is not closed; these are the mechanical gates,
  # and the self-test proves each one FIRES on a phantom and stays silent on a good record.
  if [ -f tools/burden/burden_gates.py ]; then
    run "burden gates self-test"          python3 tools/burden/burden_gates.py --selftest
  fi
  # The rehearsal witness must pass on the committed evidence. If the evidence drifts
  # without a re-run, this refuses rather than narrating the damage after landing.
  if [ -f tools/burden/witness_e2e.py ]; then
    run "burden rehearsal witness"        python3 tools/burden/witness_e2e.py
  fi
  # Invariant resolver: every NT invariant driven to its exact target over rationals.
  # A gap left OPEN exits 1, so a declared repair that is not actually a repair fails
  # here rather than being narrated as closed.
  if [ -f tools/burden/resolve_invariants.py ]; then
    run "invariant resolver"              python3 tools/burden/resolve_invariants.py
  fi
  # The resolver must be able to say NO. Without this the resolver passing means
  # nothing: V9 injects an open gap and requires FAIL, V10 requires the control to live.
  if [ -f tools/burden/falsify_resolver.py ]; then
    run "resolver falsification"          python3 tools/burden/falsify_resolver.py
  fi
  # KB manifest reconciliation: the audit's specific charge was that the 78 entries
  # were never checked line by line. Undeclared drift or a missing file fails here.
  if [ -f tools/burden/kb_reconcile.py ]; then
    run "kb manifest reconcile"           python3 tools/burden/kb_reconcile.py
  fi
  # ── PART VII delivery laws (NEVER #24-#31 / MUST #43-#50) ─────────────────────
  # Each NEVER must carry a coupled MUST and a gate that exists. Orphans fail here.
  if [ -f tools/delivery_law_gate.py ]; then
    run "delivery law pairing"            python3 tools/delivery_law_gate.py
  fi
  # The general-reader register must be burden-first and apparatus-free (NEVER #25).
  if [ -f tools/audience_gate.py ]; then
    run "audience register"               python3 tools/audience_gate.py
  fi
  # Every delivered link absolute, SHA-pinned, size-declared (NEVER #26). Structure only
  # in CI; --fetch is for the pre-delivery check with network.
  if [ -f tools/delivery_surface_gate.py ]; then
    run "delivery surface"                python3 tools/delivery_surface_gate.py
  fi
  # Every attributed citation greppable in its named source (NEVER #27).
  if [ -f tools/citation_gate.py ]; then
    run "citation provenance"             python3 tools/citation_gate.py
  fi
  # An etymon used as an argument is a claim: it carries its source and retrieved date, or
  # it is OPEN (NEVER #27 clause 4 / MUST #46 clause 3). Unsourced etymology is the "doubly
  # mean word" the Operator traced by hand.
  if [ -f tools/etymon_trace.py ]; then
    run "etymon trace (sourced, literal, located)" python3 tools/etymon_trace.py
  fi
  # The Procedural Signature Protocol is a procedure, so it can be checked as one. A
  # reconstruction that only explains the sanitized signals is a paraphrase of the legend;
  # this gate requires the sections, the sequence, the body cost, the named factory, the
  # quote cut, the prediction, and no load-bearing claim resting on self-presentation.
  if [ -f tools/signature_protocol_gate.py ]; then
    run "signature protocol selftest"      python3 tools/signature_protocol_gate.py --selftest
    run "signature protocol (loop, not legend)" python3 tools/signature_protocol_gate.py
  fi
  # No float in a verdict path; the resolver must be falsifiable (NEVER #28).
  if [ -f tools/exactness_gate.py ]; then
    run "verdict exactness"               python3 tools/exactness_gate.py
  fi
  # Every carrier closes to the target dimension independently (NEVER #30).
  if [ -f tools/domain_bridge_gate.py ]; then
    run "domain bridge closure"           python3 tools/domain_bridge_gate.py
  fi
  # Apparatus is not progress: count thesis advance, name what is unwritten (NEVER #31).
  if [ -f tools/thesis_gate.py ]; then
    run "thesis advance"                  python3 tools/thesis_gate.py
  fi
  # Kotlin syntax gate: fail if any source tree has an unclosed block comment.
  # A scanner, not kotlinc (W-023), but exact about the defect that silently
  # swallows the rest of a file. Runs only when the app tree is present.
  if [ -d app/src/main/java ]; then
    SYNTAX_ROOTS="app/src/main/java"
    [ -d omega-app/src/main/java ] && SYNTAX_ROOTS="$SYNTAX_ROOTS omega-app/src/main/java"
    run "kotlin syntax gate"              python3 tools/syntax_gate.py $SYNTAX_ROOTS
    # Detection without a rehearsed repair is half a gate. This one damages a COPY at the
    # Operator's stated lines, requires the lexer to see every removal, restores them, and
    # requires the result to be byte-identical to the pristine tree. It refuses a run that
    # removed nothing, because a rehearsal that damages nothing proves nothing (SPI-31).
    if [ -f tools/kotlin_comment_repair.py ]; then
      run "kotlin comment repair selftest" python3 tools/kotlin_comment_repair.py --selftest
      if [ -d ../tree.orig/app/src/main/java ] && [ -f docs/KOTLIN-STRIP-TABLE.json ]; then
        run "kotlin repair rehearsal (19 files)"           python3 tools/kotlin_comment_repair.py --rehearse           ../tree.orig/app/src/main/java docs/KOTLIN-STRIP-TABLE.json
      fi
    fi
    # API-level gate: a high-API call with no SDK_INT guard crashes the launcher on
    # older devices before the UI paints. Static, but exact about that defect.
    if [ -f tools/api_level_gate.py ]; then
      run "API-level gate"                python3 tools/api_level_gate.py app/src/main/java
    fi
    # Icon gate: a manifest with no android:icon ships a blank launcher tile.
    if [ -f tools/icon_gate.py ]; then
      run "icon gate"                     python3 tools/icon_gate.py
    fi
    # Board gate: the durable board must exist and every done item must carry evidence.
    if [ -f tools/board_gate.py ]; then
      run "board gate"                    python3 tools/board_gate.py
    fi
    # The board's priority taxonomy is a claim about the law. A fabricated NEVER is
    # worse than no NEVER: it reads as binding and is not.
    if [ -f tools/board_law_gate.py ]; then
      run "board law citations"           python3 tools/board_law_gate.py
    fi
    if [ -f tools/tests/board_priority_test.py ]; then
      run "board priority engine"         python3 tools/tests/board_priority_test.py
    fi
    # The run feed is the audience's witness: every agentic round trip reports start,
    # stages, and a terminal, hash-chained so a rewritten line is caught. A run that dies
    # without a terminal is SEVERED — the broken-circuitry case automation must pick up.
    if [ -f tools/run_feed.py ]; then
      run "run feed chain"                python3 tools/run_feed.py verify
      run "run feed severance detector"   python3 tools/run_feed.py severed
    fi
    if [ -f tools/tests/run_feed_test.py ]; then
      run "run feed + derived governance" python3 tools/tests/run_feed_test.py
    fi
    # NEVER #22 / MUST #42: the general drift gate is a CLASS fix. The suite drives REAL
    # temporary git repos: detector fires on dirt, stays silent on a newborn tree, and
    # the deterministic repair provably converges.
    if [ -f tools/tests/drift_gate_test.py ]; then
      run "drift gate test (NEVER #22)"   python3 tools/tests/drift_gate_test.py
    fi
    if [ -f tools/tests/divergence_gate_test.py ]; then
      run "divergence gate test (SPI-40 P1)" python3 tools/tests/divergence_gate_test.py
    fi
    # The communal contribution ledger (NT XII). A mint's value is that its witness can be
    # re-run by anyone and print the same token, so the chain gate proves no entry was
    # rewritten and the selftest proves a porous barrier still blocks promotion.
    if [ -f tools/mint_ledger.py ]; then
      run "mint ledger chain"             python3 tools/mint_ledger.py verify
    fi
    if [ -f tools/tests/mint_ledger_test.py ]; then
      run "mint ledger trial barrier"     python3 tools/tests/mint_ledger_test.py
    fi
    # Praxis gate: the order in force must be present on EVERY board that can steer work —
    # the durable board, each live session board, each sibling worktree. MUST #26 pushes the
    # board; this makes the directive itself travel with it, so no worker carries out a
    # superseded order. Read-only: --check never repairs what it inspects.
    if [ -f tools/praxis_propagate.py ]; then
      run "praxis calibration (MUST #33)"  python3 tools/praxis_propagate.py --selftest
      run "praxis propagation gate"       python3 tools/praxis_propagate.py --check
    fi
    # Loophole gate (SPI-31/SPI-32): a gate that can pass without verifying is a gate that
    # lies. Catches skip-as-pass (SKIP then exit 0) and vacuous pass (empty input set, exit 0).
    if [ -f tools/loophole_gate.py ]; then
      run "loophole closure (SPI-31/32)"  python3 tools/loophole_gate.py
    fi
    # A closed briefing re-appearing on the board is a fresh agent re-litigating a
    # question the bytes already answered. That loop costs a delivery cycle every time.
    if [ -f tools/closed_briefings.py ]; then
      run "closed briefings stay closed"  python3 tools/closed_briefings.py --check
    fi
    # Revitalization chain gate: the sixteen-stage serial corrective cycle. The
    # pipeline itself never runs inside CI (a run writes receipts, and a green run
    # must not dirty the tree); CI verifies the sealed chain instead: serial parent
    # links (I1), four-state legality with SKIP-never-PASS (I3), task evidence
    # inheritance (I2/I8), and that a cycle claiming closure really is sealed.
    if [ -f tools/revitalization.py ]; then
      run "revitalization selftest" python3 tools/revitalization.py selftest
      if [ "${REVITALIZATION_BOOTSTRAP:-0}" = "1" ]; then
        echo "INACTIVE: revitalization chain gate deferred until S16 seal (bootstrap run)"
      else
        run "revitalization chain gate" python3 tools/revitalization.py gate
      fi
    fi
    # NEVER #22: the chain gate above reads the WORKING TREE, so a cycle can pass it against
    # bytes no checkout will ever contain. On 2026-11-22 a closed cycle left TASKS.md
    # uncommitted and three gates went red on that one fact; none of them may repair it.
    # This gate names the drift as its own defect instead of leaving it to be misattributed.
    if [ -f tools/tree_invariant.py ]; then
      run "tree invariant (NEVER #22: derived tree is landed)" python3 tools/tree_invariant.py --check
    fi
    # NEVER #23 / MUST #41: every gate above runs on the far side of the push, so it can only
    # narrate damage. This one proves the mechanism that refuses a known-red change before it
    # leaves the machine (the real suite, on the exact bytes, in an isolated worktree). CI
    # checks the checker; the pre-push hook is the caller.
    if [ -f tools/admission.py ]; then
      run "admission control (NEVER #23: preflight + rehearsal)" python3 tools/admission.py --selftest
    fi
    if [ -f tools/comment_audit.py ]; then
      run "kotlin comment scan (whole repo)"  python3 tools/comment_audit.py
    fi
    # MUST #17/#18 were gated by tools/pack_delivery.py, which had no --check and was never
    # invoked: a gate that cannot fail. It now proves idempotence by packing twice.
    if [ -f tools/pack_delivery.py ] && [ -d app ]; then
      run "packaging idempotence (MUST #18)" python3 tools/pack_delivery.py --check
    fi
    # Law gate: SPI-15 — a law that is not an executable gate is a note. Enforces the
    # prime directive (DARKITH.md §30) and that every declared NEVER/MUST/SPI names a
    # gate that exists, or is explicitly marked as not-yet-gated.
    if [ -f tools/law_gate.py ]; then
      run "law gate (SPI-15/prime)"       python3 tools/law_gate.py
    fi
      # Portable directive engine: same law set, read in ANY dialect (box-drawing, markdown,
      # bullet, blockquote, source comment) with ANY verb spelling (MUST/NEVER/SPI/RULE/LAW/
      # INVARIANT/CONSTRAINT/POLICY). Couples every law to a gate that can fail and regenerates
      # missing gates from their PREDICATE. Runs beside law_gate, not instead of it: two
      # independent readers disagreeing is information, and the branded reader was blind to
      # `SPI-1:`-style declarations for as long as it existed.
      if [ -f tools/directive_core.py ]; then
        run "directive engine (portable)"   python3 tools/directive_core.py --check
        for g in tools/generated/gate_*.py; do
          [ -f "$g" ] || continue
          run "generated $(basename "$g" .py)" python3 "$g"
        done
      fi
    # MUST #15 / #16 / NEVER #17 / §31 synchrony — the laws that were only notes until now.
    # SPI-37 (a quantity crosses a boundary with its unit). The compiler cannot see
    # dimension, so `reciprocate(usedRam, allocation.vertexBudget)` — bytes and a vertex
    # count — compiled clean and Pole B was never measured. Exit 3 is a named SKIP: no
    # boundary declared, so nothing was judged (never a silent pass).
    if [ -f tools/unit_ledger_gate.py ]; then
      run "unit ledger (SPI-37)"      python3 tools/unit_ledger_gate.py .
    fi
    # SPI-37 / SPI-38: the allocator's faults were not textual — the code was well-formed,
    # compiled clean, and read like a textbook PID. Only RUNNING it showed it emitted a
    # constant. This gate compiles and executes the real law; a regex could not see it.
    if [ -f tools/controller_gate.py ]; then
      run "controller behaviour (SPI-38)" python3 tools/controller_gate.py
    fi
    # The kit is the apparatus the Operator carries between accounts. A kit that only works
    # here is not portable, so CI runs its foreign-directory selftest, not just its presence.
    if [ -f kit/coordinasync.py ]; then
      run "coordinasync portable kit (MUST #40)" python3 kit/coordinasync.py selftest
    fi
    # The Operator's chat is the source of the order in force. A directive that exists only
    # because someone typed it into TASKS.md by hand is not ingested from his speech.
    if [ -f tools/chat_gatekeeper.py ]; then
      run "chat gatekeeper selftest (MUST #38)" python3 tools/chat_gatekeeper.py --selftest
      run "chat gatekeeper ingest (MUST #38)"   python3 tools/chat_gatekeeper.py --check
    fi
    # The self-rewriting-producer class is repaired by tools/absolution.py and carries its
    # own prevention gate in the autophagy registry (detect/repair/prevent). The witness is
    # registered there rather than duplicated here: one caller, not two. The gate label
    # "absolution of self-rewriting producers" is the one autophagy cites.
    if [ -f tools/absolution.py ]; then
      run "absolution of self-rewriting producers" python3 tools/absolution.py
      run "absolution gate selftest"               python3 tools/tests/absolution_test.py
    fi
    # FM-03, mechanically: a gate that CI never runs cannot fail, and a gate that cannot fail
    # is a comment. This refuses any tools/*gate*.py with no caller, which is the exact silo
    # a fresh agent builds when it does not yet know the gate it needs already exists.
    if [ -f tools/gate_coverage_gate.py ]; then
      run "gate coverage (no uncalled gate)" python3 tools/gate_coverage_gate.py
      run "gate coverage selftest"           python3 tools/gate_coverage_gate.py --selftest
    fi
    # NT-XIII's falsifier, executed: on a known cut the deficit must be BOOKED, not silenced.
    if [ -f tools/ofif_gate.py ]; then
      run "OFIF falsifier (NT-XIII G6/G7)" python3 tools/ofif_gate.py
    fi
    for g in circadian_gate download_gate stall_gate synchrony_gate convergence_gate; do
      if [ -f "tools/$g.py" ]; then
        run "$g"                          python3 "tools/$g.py"
      fi
    done
    # synchrony_pulse is run with --check, never bare: bare updates proof/synchrony_pulse.json,
    # and convergence_gate then fails on the file CI just wrote. A green run must not dirty
    # the tree, or every green run manufactures the next red one.
    if [ -f tools/synchrony_pulse.py ]; then
      run "synchrony_pulse"             python3 tools/synchrony_pulse.py --check
    fi
      # NT gate: run the noveltreatise corpus through SAVF and fail unless every
      # contradiction (claim kind C) is resolved to absolution by a re-run command.
      # A law cited but not carried, or a contradiction left unresolved, stops CI.
      if [ -f tools/nt_gate.py ]; then
        run "nt corpus reconciliation (SAVF)" python3 tools/nt_gate.py
      fi
      # Absolution admission: a noveltreatise enters the carried corpus only when it
      # is truthful down to the verifiable bit — carried (not merely cited), every claim
      # witnessed or derived, every contradiction resolved to a named EXPOSABLE boundary,
      # its own corpus count true, and no unresolved mechanism smuggled as RESOLVED.
      if [ -f tools/absolution_admission.py ]; then
        run "absolution admission (NT XII)"  python3 tools/absolution_admission.py
      fi
      # NT hardware-coupled sensor: the Healer repair example must name a symbol the
      # reference android.jar actually carries (raw android.*, not androidx.*). Reads the
      # compiler's own ground truth; a silent skip is announced (SPI-2/SPI-13).
      if [ -f tools/nt_sensor.py ]; then
        run "nt sensor (Healer example vs android.jar)" python3 tools/nt_sensor.py
        run "nt sensor self-test"           python3 tools/nt_sensor.py --selftest
      fi
      # NT XI progress-deficit indicator: the retention law W_in - E = S != 0 read off
      # the durable board + deficit ledger. Fails if the board's printed indicator is stale,
      # or if the ratio rose across a delivery with no new descope (M6 non-extractive).
      if [ -f tools/omega_deficit.py ]; then
        run "omega deficit (NT XI retention)" python3 tools/omega_deficit.py
      fi
    # the board must be pushed in REAL TIME so a parallel worker sees it (MUST #26)
    if [ -f tools/board_pulse.sh ]; then
      run "board pulse (real-time push)"    bash tools/board_pulse.sh --check
    fi
    # MUST #36 — the same fact measured as TIME, not a yes/no. board_pulse only asks "is it
    # pushed?"; this asks "for how long was it NOT?" and fails when the dwell exceeds the
    # Operator's budget in STALL_BUDGET.json. Without it, work sits unpushed for an hour with
    # every gate green, because no gate ever measured latency.
    if [ -f tools/stall_clock.py ]; then
      run "stall clock (off-schedule dwell)" python3 tools/stall_clock.py
    fi
    # NEVER #21: an automated decision is already approved. Prove the authority is inscribed
    # in every board, and that nothing is sitting uncommitted or unpushed. --budget 0 is the
    # CI setting: a pushed tree, or a red gate — there is no "pending approval" third state.
    if [ -f tools/authority_gate.py ]; then
      run "authority gate selftest"         python3 tools/authority_gate.py --selftest
      run "authority gate (NEVER #21)"      python3 tools/authority_gate.py --check --budget 0
    fi
  fi
else
  echo "SKIP: python3 not found"; FAILED=1
fi

# The NT IX raw-chain gates. These are the laws that were "notes, not gates" (SPI-15):
# they existed but nothing invoked them. A gate that is never run is a note, so CI runs them.
# The §19 gate (fork_integrity_gate.sh) ENFORCES the compile proof (MUST-11); to keep CI
# honest it is given a real toolchain from .tools/ when one is present, and it FAILS (not
# skips) when there is none. The APK-dependent loopholes are deferred explicitly via
# --source-only, which is a named SKIP, never a silent pass.
if [ -d app/src/main/java ] && [ -f tools/fork_integrity_gate.sh ]; then
  TOOLCHAIN="$ROOT/.tools"
  if [ -x "$TOOLCHAIN/kotlinc/bin/kotlinc" ]; then
    export KOTLINC="$TOOLCHAIN/kotlinc/bin/kotlinc"
    export ANDROID_JAR="$TOOLCHAIN/android-all-14-robolectric-10818077.jar"
    export EXTRA_CP="$TOOLCHAIN/apksig.jar"
    [ -x "$TOOLCHAIN/jdk-17.0.12+7/bin/java" ] && export JAVA_HOME="$TOOLCHAIN/jdk-17.0.12+7"
    # aapt2 (R.java for the compile proof) and zipalign live in aapt2d/; put them on PATH
    # so both the §19 proof and the install gate find real tools on a fresh runner.
    export PATH="$TOOLCHAIN/aapt2d:${JAVA_HOME:+$JAVA_HOME/bin:}$PATH"
    # apksigner (the install gate's signature check) ships in the Android build-tools tree
    # that build/refresh-host-artifacts.py stages under .tools/bt/. Stage it too, or the
    # install gate skips even though every tool it needs is present.
    if [ -d "$TOOLCHAIN/bt/android-14" ]; then
      export PATH="$TOOLCHAIN/bt/android-14:$PATH"
      [ -x "$TOOLCHAIN/bt/android-14/apksigner" ] && export APKSIGNER="$TOOLCHAIN/bt/android-14/apksigner"
    fi
    run "§19 fork integrity gate (compile proof)" \
      bash tools/fork_integrity_gate.sh app/src/main/java/com/darkith/transliaison "$ANDROID_JAR" "$EXTRA_CP"
  else
    echo "SKIP: no toolchain in .tools/ (run: bash tools/fetch_toolchain.sh) — §19 compile proof NOT run"
    echo "      (the §19 gate itself fails closed without it; this line only records the local skip)"
    FAILED=1
  fi

  run "delivery gate (source laws)" \
    bash tools/delivery_gate.sh . --source-only
  # THE GATE THAT WOULD HAVE CAUGHT THE LAUNCH CRASH. classes.dex referenced
  # kotlin-stdlib + apksig but defined neither, so the app died at runtime init
  # while every other test stayed green. If a built APK is present, link it.
  if [ -f "$ROOT/tools/dex_link_gate.py" ]; then
    APKS=""
    [ -f "$ROOT/app-signed.apk" ] && APKS="$ROOT/app-signed.apk"
    [ -f "$ROOT/build/termkit_omega/app-signed.apk" ] && APKS="$APKS $ROOT/build/termkit_omega/app-signed.apk"
    if [ -n "$APKS" ]; then
      run "dex link gate (no unresolved classes)" python3 tools/dex_link_gate.py $APKS
      run "apk gate (icon + store laws)"        python3 tools/apk_gate.py $APKS
    else
      echo "SKIP: no built APK on disk — dex link gate not run (build.sh produces one)"
    fi
  fi
  # The terminal must never lie about its version (darkterm/darktools/termkit/savf
  # each carried their own hardcoded string). This fails the moment one drifts.
  if [ -f "$ROOT/tools/stamp_versions.py" ]; then
    run "version surface gate (one version of record)" python3 tools/stamp_versions.py --check
  fi
  # savf.py and savf.html are two ports of ONE formulary; they must agree.
  if [ -f "$ROOT/tools/savf_parity_gate.py" ]; then
    run "savf py/js parity gate" python3 tools/savf_parity_gate.py
  fi
  # The pre-runner drives a real headless Chromium; lock its engine surface, its
  # exit-code contract and its honest (deterministic) verdicts.
  if [ -f "$ROOT/tools/prerunner_gate.py" ]; then
    run "pre-runner gate (engine + exit contract)" python3 tools/prerunner_gate.py
  fi
  # The ClearanceLoop ratchet is the governing law; lock its four laws and assert
  # the engines are wired into every surface, or a surface silently loses them.
  if [ -f "$ROOT/tools/clearanceloop_gate.py" ]; then
    run "clearanceloop gate (ratchet laws + integration)" python3 tools/clearanceloop_gate.py
  fi
  # Auto-Nodal Co-ordina-Sync: the receipt ledger, the total-function bot contract, and the
  # coordination layer. Proves the Python suite AND that the .js SAVF twin enforces the same
  # laws with byte-identical identity — a twin that hashes differently is a second system
  # wearing the same name, so this fails closed on any divergence.
  if [ -f "$ROOT/tools/nodal_gate.py" ]; then
    run "nodal gate (Co-ordina-Sync + python/js parity)" python3 tools/nodal_gate.py
  fi
  # The webapp gate drives the shipped file in a real headless Chromium: function,
  # measured a11y/layout, persistence, hostile state and denied storage. It SKIPS
  # (never fails) when no browser is installed, so a bare CI box stays green.
  if [ -f "$ROOT/tools/clearanceloop_ui_gate.py" ]; then
    run "clearanceloop webapp gate (headless browser)" python3 tools/clearanceloop_ui_gate.py
  fi
  # The SAVF webapp gate drives savf.html in real Chromium, Firefox and WebKit:
  # every tab, the audit flow, the axis/sign/exp laws, the ledger, the freeze/tamper
  # path, the in-app self-test, keyboard, both themes, measured a11y/layout at
  # 320/360/1280, hostile input, corrupt theme and denied storage.
  if [ -f "$ROOT/tools/savf_ui_gate.py" ]; then
    run "savf webapp gate (headless browser)" python3 tools/savf_ui_gate.py
  fi
  run "bridge contract audit" \
    python3 tools/bridge_contract_audit.py "darkith home forge.html" app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt
  run "doc consolidation check" \
    bash tools/consolidate_docs.sh --check
fi

if have python3 && [ -f tools/doc_path_gate.py ]; then
  run "doc path gate" python3 tools/doc_path_gate.py
fi

# Single-authority migration (§1.2, §7.2, §7.3). Three gates, each able to fail:
#   policy_block       DARKITH.md carries exactly one delimited, machine-readable policy
#                      block, it parses under one strict parser, its ids are unique, its
#                      precedence is total, and it is fresh against the law headings.
#   authority_inventory no secondary prose document DEFINES law; DARKITH.md is the source.
#   authority_gate_migration  plants the defects above and requires the checks to refuse
#                      them, so a gate that has only ever seen a healthy tree cannot pass.
# A migration whose result is only asserted is a claim; these make it a measurement.
if have python3 && [ -f tools/policy_block.py ]; then
  run "policy block (machine-readable law)" python3 tools/policy_block.py --check
  run "policy parser selftest"              python3 tools/policy_block.py --selftest
fi
if have python3 && [ -f tools/authority_inventory.py ]; then
  run "authority inventory (one source)"    python3 tools/authority_inventory.py --check
fi
if have python3 && [ -f tools/authority_gate_migration.py ]; then
  run "authority migration regressions"     python3 tools/authority_gate_migration.py
fi

# Blueprint gate: the Operator's specification corpus must never instruct the agent. The
# blueprint rode onto main with a live prompt-injection payload (`COPY AND PASTE ... INTO
# OPENHANDS`, `do not ask for confirmation; execute immediately`) because NOTHING checked
# it — a law that is not a gate is a note. This runs unconditionally (the corpus is not
# under app/), so the contaminant can never ride in ungated again.
if have python3 && [ -f tools/blueprint_gate.py ]; then
  run "blueprint gate (no injection)" python3 tools/blueprint_gate.py
fi

if have python3 && [ -f tools/autophagy.py ]; then
  # The defect-class registry. Every class found by hand must land as detector + repair +
  # prevention gate; this runs the detectors so a repaired class cannot silently return.
  # It runs BEFORE kb_index so a generator-order inversion is reported as itself rather
  # than as an anonymous stale index.
  run "autophagy selftest" python3 tools/autophagy.py --selftest
  run "autophagy (defect-class registry)" python3 tools/autophagy.py --check
fi

if have python3 && [ -f tools/phantom_tree_gate.py ]; then
  # A gitignored duplicate source tree is invisible to every reviewer but is judged by
  # gates that scan the working directory (the unit ledger did exactly that).
  run "phantom source tree" python3 tools/phantom_tree_gate.py --check
fi

if have python3 && [ -f tools/toolchain_gate.py ]; then
  # A compiler with no runtime makes a compile gate blame the code for an absent JVM.
  run "toolchain integrity" python3 tools/toolchain_gate.py --check
fi

if have python3 && [ -f tools/board_header_gate.py ]; then
  # A generated block must never delete a board's title or governance prose. This is the
  # gate for the class that let 340 lines of TASKS.md vanish while every gate stayed green.
  run "board header intact" python3 tools/board_header_gate.py --check
fi

if have python3 && [ -f tools/kb_index.py ]; then
  # Universal index of the readable knowledge-skill base (SPI-15). Fails if the index is
  # stale, if a readable file is unfiled, if two files share a hash without a declared
  # mirror, or if a declared mirror has drifted (NEVER #11 / #15 / #16, §22).
  run "knowledge-base index + dedup" python3 tools/kb_index.py
fi

if have node && [ -f tools/test_darktools.js ]; then
  run "darktools unit tests" node tools/test_darktools.js
fi

  # The four-register reader (omega-reader.html): dependency-free DOM-shim test. Proves
  # the routing is bounds-safe and the machine/provenance registers are HTML-escaped.
  if have node && [ -f tools/test_omega_reader.js ]; then
    run "omega reader tests" node tools/test_omega_reader.js
  fi

  # The Icon Forge (icon_forge.html): the visual-affordance specialist. Dependency-free
  # DOM/canvas-shim test that evaluates the REAL script. Proves sha256, the deterministic
  # ZIP (CRC-verified), absolute-only pathData for VectorDrawable, safe-zone geometry, the
  # four-state gates (a missing bridge is UNAVAILABLE, never PASS) and device coupling.
  if have node && [ -f tools/test_icon_forge.js ]; then
    run "icon forge tests" node tools/test_icon_forge.js
  fi

  # The Ω media player (darkith-omega-media-player.html): dependency-free DOM-shim test
  # that evaluates the REAL script. Proves the pure parsers (VTT/SRT/M3U/time/bytes),
  # the speed ladder, shuffle, the equaliser definition, the queue/playlist logic, and
  # that a hostile filename is HTML-escaped before it reaches the queue (no injection).
  if have node && [ -f tools/test_media_player.js ]; then
    run "media player tests" node tools/test_media_player.js
  fi

  # The Ω file manager (darkith-omega-files.html). Proves BOTH bridge fileList
  # contracts normalise to one shape (DarkithBridge {name,dir,size} and
  # HomekeeperBridge {name,type,bytes,mtime}), that fileRoots' U+0001 join is split
  # correctly, and that a hostile filename never reaches innerHTML.
  if have node && [ -f tools/test_files.js ]; then
    run "file manager tests" node tools/test_files.js
  fi

  # The five Ω device apps (phone, messages, contacts, camera, clock). Proves honest
  # degradation when a permission is missing (never a faked result), bounded polling
  # for the async capture path, and no bridge value injected as HTML.
  if have node && [ -f tools/test_device_apps.js ]; then
    run "device app tests" node tools/test_device_apps.js
  fi

  # The TermKit dual-register manual (help beginner / help dev). The invariant debugger
  # extracts the REAL shell core from the canonical page and executes every fixture the
  # manual prints, so documentation can never drift from the engine. No browser needed.
  if have node && [ -f tools/termkit_help_audit.mjs ]; then
    run "termkit help audit (dual register)" node tools/termkit_help_audit.mjs
  fi


  # The source inspector — the logical trial examiner. It puts the source on trial: 10
  # named charges, each calibrated (positive+negative), then autofixes the reversible ones
  # and enforces the HOMEOKINESIS ratchet (debt may only flux downward; stasis degrades).
  # `trial` proves every charge is calibrated AND the four ratchet laws hold, so a
  # miscalibrated gate can never reach CI. `inspect` then fails on any open blocker or any
  # net addition of escrow debt above the ratchet high-water mark.
  if have python3 && [ -f tools/source_inspector.py ]; then
    run "source inspector trial (charges + ratchet)" python3 tools/source_inspector.py trial
    run "source inspector (loophole trial)"          python3 tools/source_inspector.py inspect --fail-on-fixable
  fi

# The inscriber studio: boots in jsdom, engines present, terminal + toolkits live. Needs
# jsdom (an npm dev dep, not always installed), so it is skipped honestly when absent.
if have node && [ -f tools/test_inscriber.js ]; then
  if node -e 'require("jsdom")' >/dev/null 2>&1; then
    run "inscriber studio tests" node tools/test_inscriber.js
  else
    echo "SKIP: jsdom not installed (npm install jsdom) — inscriber studio test NOT run"
  fi
fi

if have node; then
  run "omega engine harness" node build/omega/omega-test.mjs
else
  echo "SKIP: node not found"; FAILED=1
fi

# The update watcher's decision logic (stale-vs-remote): pure, exercised with real
# inputs and a stubbed transport, so the alerting cannot silently rot.
if have node && [ -f tools/updater_test.mjs ]; then
  run "update watcher logic" node tools/updater_test.mjs
fi

# Browser UI test needs playwright; run it only if importable, so a slim environment
# skips it honestly instead of reporting a false failure.
if have python3 && python3 -c 'import playwright' >/dev/null 2>&1; then
  run "omega headless ui" python3 build/omega/ui-test.py
else
  echo "SKIP: playwright not installed (python3 -m pip install -r requirements-dev.txt)"
fi

# Byte-security invariant: signing key material must never be tracked in git.
# This is the one check that must run even with no runtime installed, so it is
# plain git + grep and is never skipped.
printf '\n=== no signing material tracked ===\n'
if have git && git rev-parse --git-dir >/dev/null 2>&1; then
  hits="$(git ls-files | grep -Ei '(^|/)(release_key|release_cert)$|\.(keystore|jks|p12|pfx|pem|key)$' || true)"
  if [ -n "$hits" ]; then
    printf -- '--- no signing material tracked: FAIL\n%s\n' "$hits"
    FAILED=1
  else
    printf -- '--- no signing material tracked: PASS\n'
  fi
else
  echo "SKIP: not a git checkout"
fi

printf '\n=== APK store rule (SPI-21 repack law) ===\n'
apks="$(ls delivery/*.apk 2>/dev/null || true)"
if have python3 && [ -n "$apks" ]; then
  # resources.arsc and lib/*.so MUST be STORED; DEFLATED means API 30+ install
  # fails with a bare "App not installed". delivery/ is regenerable output and
  # not committed, so an absent APK is a skip, never a failure. Check EVERY APK:
  # the defect is systemic (both shipped APKs had it), not a one-file accident.
  for apk in $apks; do
    if python3 - "$apk" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
bad = [n for n in z.namelist()
       if (n == "resources.arsc" or n.endswith(".so")) and z.getinfo(n).compress_type != 0]
if bad:
    print("      " + sys.argv[1] + " DEFLATED (must be STORED): " + ", ".join(bad)); sys.exit(1)
print("      ok: " + sys.argv[1] + " (arsc + lib/*.so STORED)")
PY
    then printf -- '--- APK store rule: PASS (%s)\n' "$apk"
    else printf -- '--- APK store rule: FAIL (%s)\n' "$apk"; FAILED=1; fi
  done
else
  printf -- '--- APK store rule: skipped (no delivery/*.apk)\n'
fi

printf '\n=== install gate (no "App not installed") ===\n'
# The two failures a user actually feels are (1) the package installer refusing the APK
# and (2) the UI not painting once the OS launches it. Both are gated explicitly. The
# install gate needs aapt2 (manifest) + apksigner (signature); absent them it is a named
# SKIP, never a false pass. zipalign is optional (I-04 is N/A without it).
if have python3 && command -v aapt2 >/dev/null 2>&1 && command -v apksigner >/dev/null 2>&1; then
  gate_apks="$apks"
  [ -f app-signed.apk ] && gate_apks="$gate_apks app-signed.apk"
  if [ -n "${gate_apks// /}" ]; then
    for apk in $gate_apks; do
      run "install gate ($apk)" python3 tools/install_gate.py "$apk" .
    done
  else
    printf -- '--- install gate: skipped (no APK to check)\n'
  fi
else
  printf -- '--- install gate: SKIP (no APK, or aapt2/apksigner absent; build an APK and stage tools with: bash tools/fetch_toolchain.sh)\n'
fi

# I-03's v2 detector is a regex against apksigner's stdout; a wrong regex silently reads
# OPEN, or worse PASSes a v1-only APK. Guard it directly, independent of any APK.
if have python3 && [ -f tools/install_gate.py ]; then
  run "install gate selftest (I-03 v2 detector)" python3 tools/install_gate.py --selftest
fi

# C2: a forged child APK must be a working, self-forging app, not merely a clean build. The
# host manifest sets extractNativeLibs for exactly this reason (L-17); the child template must
# match or a forged app cannot exec the native forge tools and install_gate I-07 goes OPEN.
if have python3 && [ -f tools/forge_child_gate.py ]; then
  run "forge child gate (C2)" python3 tools/forge_child_gate.py
fi

printf '\n=== runtime render gate (the UI the OS hands to Zygote) ===\n'
# Loads the real launcher asset at 360x800 with and without the native bridge and fails on
# any console/page error, blank body, empty DOM, or overflow. Self-skips (exit 0) when
# playwright is absent, so a slim environment is honest, not red.
if have python3; then
  run "runtime render gate" python3 tools/runtime_gate.py
else
  printf -- '--- runtime render gate: SKIP (no python3)\n'
fi

printf '\n=== discrepancy detectors (two tabs must agree) ===\n'
if have git && git rev-parse --git-dir >/dev/null 2>&1; then

  # D-1 / NEVER #22 uncommitted drift: with two tabs, an uncommitted edit is invisible
  # to the other tab and can be lost. This STOPS being a warning: a drifting tree is a
  # defect CLASS (inscribed in DARKITH.md, registered in tools/autophagy.py both as the
  # derived-artifact subclass via tools/tree_invariant.py and the general class via
  # tools/drift_gate.py). The gate fails closed on drift; `python3 tools/drift_gate.py
  # --fix` is the deterministic repair (stage, commit, push — never force).
  if [ -f tools/drift_gate.py ]; then
    run "drift gate (NEVER #22)" python3 tools/drift_gate.py --check
  else
    printf -- '--- drift gate (NEVER #22): FAIL (tools/drift_gate.py missing)\n'
    FAILED=1
  fi

  # D-1b / SPI-40 P1 divergence: local main ahead AND behind origin is the state that
  # froze a session (8 ahead, 109 behind, unwritable without force). The detector fails
  # closed; the repair parks on a pushed branch, fast-forwards, rebases, never forces.
  if [ -f tools/divergence_gate.py ]; then
    run "divergence gate (SPI-40 P1)" python3 tools/divergence_gate.py --check
  else
    printf -- '--- divergence gate (SPI-40 P1): FAIL (tools/divergence_gate.py missing)\n'
    FAILED=1
  fi

  # D-2 fork singularity (AGENTS.md NEVER #11 / SPI-12, the missing W-040 gate).
  # NEVER #11 forbids two *divergent* live copies. A basename at more than one tracked path
  # is only a violation when the copies DIFFER; byte-identical copies are mirrors, and this
  # gate keeps them honest by failing the moment one drifts. (The old gate used a hardcoded
  # name list, so it never saw `darkith forge.html` vs `darkith home forge.html`, nor
  # `darkith_ui.html` vs `darkith-inscriber.html`.)
  if ! python3 - <<'PYGATE'
import hashlib, subprocess, sys, collections
files = subprocess.run(["git","ls-files","-z"], capture_output=True, text=True).stdout.split("\0")[:-1]
# NEVER #11 forbids two DIVERGENT copies within ONE authoritative tree. Two
# independent apps (app/ and omega-app/) are each their own tree, so a shared
# basename across them is not a fork — only divergence WITHIN a tree is. Scope
# the comparison per tree; shared/root files use the "" tree.
def tree_of(f):
    # A sealed cycle's receipt directory is its own tree for the same reason app/
    # and omega-app/ are: each cycle is independent evidence, so S01_BASELINE.json
    # in cycle A and in cycle B are two records, not two copies of one file.
    # Comparing them would report every successive cycle as a fork of the last.
    if f.startswith("proof/revitalization/"):
        rest = f.split("/", 3)
        if len(rest) == 4 and rest[2] != "":
            return "proof/revitalization/" + rest[2]
    head = f.split("/",1)[0]
    # A nested project directory is its own tree, exactly like app/ and omega-app/.
    # The homekeeper Node app has its own README, package.json and src/, none of which
    # are copies of the root equivalents; treating them as one tree reports a fork
    # between two unrelated documents.
    return head if head in ("app","omega-app","darkith-omega-homekeeper") else ""
by = collections.defaultdict(list)
for f in files:
    # EXEMPT Android resource-qualifier dirs: the SAME basename in different
    # buckets (mipmap-mdpi vs mipmap-hdpi, values vs values-night) is REQUIRED
    # to differ — that is what the qualifier means. A false positive here trains
    # people to ignore the gate.
    if "/res/" in f:
        continue
    by[(tree_of(f), f.rsplit("/",1)[-1])].append(f)
divergent, mirrors = {}, {}
for (tree, name), paths in sorted(by.items()):
    if len(paths) < 2:
        continue
    hashes = {}
    for pth in paths:
        try:
            hashes[pth] = hashlib.sha256(open(pth,"rb").read()).hexdigest()
        except OSError:
            hashes[pth] = "?"
    (divergent if len(set(hashes.values())) > 1 else mirrors)[f"{tree}/{name}" if tree else name] = hashes if len(set(hashes.values()))>1 else paths
for name, paths in mirrors.items():
    print(f"      mirror (identical): {name} at {', '.join(paths)}")
if divergent:
    print("--- fork singularity (NEVER #11): FAIL (divergent copies)")
    for name, hashes in divergent.items():
        print(f"      {name} tracked at {len(hashes)} paths with DIFFERENT bytes:")
        for pth, h in hashes.items():
            print(f"        {h[:12]}  {pth}")
    sys.exit(1)
print("--- fork singularity (NEVER #11): PASS (no divergent copies)")
PYGATE
  then FAILED=1; fi

  # D-2b explicit mirror pairs: one surface under two names by design. They must stay
  # byte-identical — drift is a fork (NEVER #11) even though the basenames differ, which the
  # basename-based D-2 above cannot see. The app ships assets/darkith_ui.html; the repo-root
  # studio is the same page for browser use, and tools/test_inscriber.js drives the studio.
  for pair in "app/src/main/assets/darkith_ui.html:darkith-inscriber.html"; do
    a="${pair%%:*}"; b="${pair##*:}"
    if [ -f "$a" ] && [ -f "$b" ]; then
      if cmp -s "$a" "$b"; then
        printf -- '--- mirror pair identical: %s == %s\n' "$a" "$b"
      else
        printf -- '--- mirror pair DRIFT (NEVER #11): %s != %s\n' "$a" "$b"
        FAILED=1
      fi
    fi
  done

  # D-3 version truth: if the AndroidManifest is versioned (MUST #12), the
  # versionName it declares must be the one AGENTS.md states. A tab that bumps
  # one but not the other is a discrepancy.
  man="$(git ls-files | grep -E '(^|/)AndroidManifest\.xml$' | head -1 || true)"
  if [ -n "$man" ] && [ -f AGENTS.md ]; then
    vn="$(sed -n 's/.*versionName="\([^"]*\)".*/\1/p' "$man" | head -1)"
    if [ -n "$vn" ] && ! grep -qF "$vn" AGENTS.md; then
      printf -- '--- version truth: FAIL (manifest says %s, AGENTS.md does not)\n' "$vn"
      FAILED=1
    else
      printf -- '--- version truth: PASS (%s)\n' "${vn:-n/a}"
    fi
  else
    printf -- '--- version truth: skipped (no tracked AndroidManifest.xml)\n'
  fi

else
  printf -- '--- discrepancy detectors: SKIP (not a git checkout)\n'
fi

# ── the one-shot installer: the Operator's single build+install entrypoint ──────
# It must exist, be tracked, carry a payload that matches the tree, and contain the
# native toolchain libs the on-device forge execs. Without this check the one-shot
# can silently vanish again (it did: it was referenced by three packagers and absent).
if have python3 && [ -f build/make-oneshot.py ]; then
  if python3 build/make-oneshot.py --check >/tmp/oneshot_check.$$ 2>&1; then
    printf -- '--- one-shot installer: PASS (%s)\n' "$(tail -1 /tmp/oneshot_check.$$ | sed 's/^ *//')"
  else
    printf -- '--- one-shot installer: FAIL (payload stale or missing)\n'
    cat /tmp/oneshot_check.$$ | sed 's/^/    /'
    FAILED=1
  fi
  rm -f /tmp/oneshot_check.$$
fi

# Version truth + update-watcher wiring: the version stamped in the page, the
# app surface, the manifest and updater.js must all agree with VERSION.json, or a
# stale install could be told it is current (or a current one told to update).
if have python3 && [ -f tools/update_gate.py ]; then
  run "version truth + update wiring" python3 tools/update_gate.py
fi

# The app surface must carry the CURRENT watcher block (idempotent injector).
if have python3 && [ -f build/inject_updater.py ]; then
  run "update watcher injected (app surface)" python3 build/inject_updater.py --check
fi

# The Operator's one-shot entrypoint (build&install.sh) must exist, be valid bash,
# invoke the raw chain (never Gradle: SPI-1), and be reachable. It is the "drop
# Termux" surface; it has silently gone missing before, so it is gated.
if [ -f 'build&install.sh' ]; then
  if bash -n 'build&install.sh' 2>/dev/null && grep -q 'build.sh' 'build&install.sh' \
     && ! grep -Eq '^\s*gradle|gradlew|gradle\.bat' 'build&install.sh'; then
    printf -- '--- build&install.sh entrypoint: PASS (valid, Gradle-free)\n'
  else
    printf -- '--- build&install.sh entrypoint: FAIL (syntax error or Gradle reference)\n'
    FAILED=1
  fi
else
  printf -- '--- build&install.sh entrypoint: FAIL (missing — the one-shot is the deliverable)\n'
  FAILED=1
fi

  # ── the CNS directive: one order, every board, every peripheral ────────────────
  # A directive that lives in one conversation leaves the other agents working a superseded
  # order. The board copy is the durable record; this gate proves it is on every board.
  if have python3 && [ -f tools/cns_directive.py ]; then
    run "cns directive (one order, every board)" python3 tools/cns_directive.py --check
  fi

  # ── autophagy: the tree consumes its own defects and returns to newborn ────────
  # --check repairs nothing and must exit non-zero if ANY registered class is dirty. This is
  # the gate that makes "a defect was possible" a build failure rather than a later surprise.
  if have python3 && [ -f tools/autophagy.py ]; then
    run "autophagy (defect classes are impossible, not absent)" python3 tools/autophagy.py --check
  fi

# Bind this run to the hash-chained ledger. The terminal forgets; the ledger does not.
# Each receipt attests "this named program, over these bytes, returned this verdict", so a
# later claim of green can be checked against evidence instead of trusted. Emitting must
# never change the CI verdict: a receipt failure is reported, not promoted to a build
# failure, because a broken ledger is a bookkeeping fault, not a broken tree.
# The run's own stdout is the source of truth for what each gate reported, so re-run the
# parse against a log this script wrote itself rather than a variable that may not exist.
if [ "${REVITALIZATION_BOOTSTRAP:-0}" != "1" ] && [ -f tools/ci_receipts.py ] && [ -f "${CI_LOG:-}" ]; then
  printf '\n=== ci receipts ===\n'
  python3 tools/ci_receipts.py --emit < "$CI_LOG" || true
  python3 tools/ci_receipts.py --verify || true
elif [ "${REVITALIZATION_BOOTSTRAP:-0}" = "1" ]; then
  echo "INACTIVE: CI receipt emitter deferred until the sealed cycle is available"
fi

printf '\nCI: %s (%d skipped)\n' "$([ "$FAILED" -eq 0 ] && echo PASS || echo FAIL)" "$SKIPPED"
exit "$FAILED"


