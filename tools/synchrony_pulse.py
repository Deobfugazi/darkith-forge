#!/usr/bin/env python3
"""synchrony_pulse.py — the boot-aware session pulse (MUST #23/#24, DARKITH.md §31).

Prime bylaw: the ephemeral AGENTS.md-serving agent that serves the sovereign user must boot
real-time-stamp aware, and must track the user's LAST CONVERSATION ACTIVITY so it can be
mapped against the Operator's circadian sleep/wake cycle — rest/digest/restore (deactivity)
vs wake/activity — as the DEFAULT.

This tool writes (and reads) `proof/synchrony_pulse.json`: the session's boot instant, the
last observed conversation activity, the gap between them, and the cycle phase each falls
in. It is generated from the real clock and real device signals (SPI-2: read the bytes),
never asserted.

  python3 tools/synchrony_pulse.py            observe now, update the pulse, print it
  python3 tools/synchrony_pulse.py --check    fail if the pulse is stale (no activity in
                                              > STALE_HOURS) or missing the boot/activity map
  python3 tools/synchrony_pulse.py --mark     record a new activity instant (a turn happened)
"""
import datetime
import json
import os
import pathlib
import sys

# ROOT is the project this tool serves. COORDINASYNC_ROOT overrides it so the same source can
# be bundled into the single-file kit (where __file__ is the bundle, not tools/) and run against
# a host project anywhere. Without the override, a bundled copy resolves its root to whatever
# directory it happens to sit in and writes its board there.
ROOT = pathlib.Path(os.environ.get("COORDINASYNC_ROOT") or
                    pathlib.Path(__file__).resolve().parent.parent).resolve()
sys.path.insert(0, str(ROOT / "build" / "gen"))
sys.path.insert(0, str(ROOT / "tools"))

from omega_time_runtime import (  # noqa: E402
    TZ as OPERATOR_TZ, boot_stamp, classify, device_relation, iso, phase, since, stamp,
)

PULSE = ROOT / "proof/synchrony_pulse.json"
STALE_HOURS = 24.0          # no activity in a full day is stale (a rest cycle is <= ~12h)


def load() -> dict:
    if PULSE.is_file():
        try:
            return json.loads(PULSE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _discover_event_roots() -> list[pathlib.Path]:
    """Where this project keeps conversation logs.

    Precedence: COORDINASYNC_EVENT_ROOTS, then this project's own `.coordinasync.json`
    declaration, then `conversations/` beside the tool, then `../conversations`.

    The project DECLARES its log root; the toolkit assumes none. Both guesses failed: assuming
    platform paths let a copy running in /tmp ingest the home session into an unrelated project,
    and assuming project-local-only left the home repo blind to its own log. A declaration is
    neither — it is the project stating a fact about itself, and a project that states nothing
    gets nothing rather than somebody else's orders.
    """
    env = os.environ.get("COORDINASYNC_EVENT_ROOTS")
    if env:
        return [pathlib.Path(p) for p in env.split(os.pathsep) if p]
    declared = ROOT / ".coordinasync.json"
    if declared.is_file():
        try:
            cfg = json.loads(declared.read_text(encoding="utf-8"))
            roots = [pathlib.Path(p) for p in cfg.get("event_roots", []) if p]
            if roots:
                return roots
        except (ValueError, OSError):
            pass
    for cand in (ROOT / "conversations", ROOT.parent / "conversations"):
        if cand.is_dir():
            return [cand]
    return []


EVENT_ROOTS = _discover_event_roots()


def live_activity() -> str | None:
    """The timestamp of the newest real conversation event, read from the event log.

    Before this existed, `lastActivity` only moved when someone passed --mark, so the pulse
    reported whatever instant the last human remembered to stamp — on 2026-11-20 it claimed
    21.5h of quiet while the Operator had spoken 12 minutes earlier. A pulse that must be told
    the user is present is not occupation-aware; it is a diary. MUST #28 says the session
    AUTOCCOUPLES to the device and tracks last activity, so this reads the bytes (SPI-2).
    """
    newest = None
    for root in EVENT_ROOTS:
        if not root.is_dir():
            continue
        for conv in sorted(root.iterdir()):
            ev = conv / "events"
            if not ev.is_dir():
                continue
            files = sorted(ev.glob("event-*.json"))
            if not files:
                continue
            try:
                e = json.loads(files[-1].read_text())
            except Exception:
                continue
            ts = e.get("timestamp")
            if not ts:
                continue
            # The event log stamps in UTC with no offset; the pulse works in Operator-local.
            # Handing a naive UTC string to since() reads it as local and invents the zone
            # offset as a gap (measured: 8.0h of quiet that never happened). The boundary
            # conversion happens here, once, and the value crosses it already carrying its zone.
            try:
                utc = datetime.datetime.fromisoformat(ts)
            except ValueError:
                continue
            if utc.tzinfo is None:
                utc = utc.replace(tzinfo=datetime.timezone.utc)
            local = utc.astimezone(OPERATOR_TZ)
            if newest is None or local > newest:
                newest = local
    return newest.isoformat(timespec="seconds") if newest else None


def observe(mark: bool = False) -> dict:
    prev = load()
    now_iso = iso()
    boot = prev.get("boot") or boot_stamp()
    # Live activity outranks a remembered stamp; --mark still works as an explicit override.
    live = live_activity()
    if mark:
        last = now_iso
    elif live:
        last = live
    else:
        last = prev.get("lastActivity") or now_iso
    gap = round(since(last), 3)
    pulse = {
        "boot": boot,
        "lastActivity": last,
        "observedNow": now_iso,
        "gapHours": gap,
        "bootPhase": phase(__import__("datetime").datetime.fromisoformat(boot)),
        "lastActivityPhase": classify(last)["phase"],
        "currentPhase": phase(),
        "device": device_relation(),
    }
    # Persist only when the DURABLE identity (boot, lastActivity) changes. `observedNow`,
    # `gapHours` and the device clock are observation-time values: rewriting this tracked file
    # on every run dirties the tree on every CI pass, which is a churn loop — and a churn loop
    # makes a dwell gate (MUST #36) fire on CI's own output instead of on a real stall.
    durable = (pulse["boot"], pulse["lastActivity"])
    if durable != (prev.get("boot"), prev.get("lastActivity")):
        PULSE.parent.mkdir(parents=True, exist_ok=True)
        PULSE.write_text(json.dumps(pulse, indent=2) + "\n", encoding="utf-8")
    return pulse


def show(p: dict) -> None:
    print(f"synchrony_pulse: boot {p['boot']} ({p['bootPhase']})")
    print(f"  last activity {p['lastActivity']} ({p['lastActivityPhase']})")
    print(f"  now {p['observedNow']} ({p['currentPhase']})  gap {p['gapHours']}h")
    d = p["device"]
    print(f"  device {d['deviceLocal']} {d['deviceZone']}  "
          f"agrees-with-Operator={d['agrees']}  (global {d['globalUtc']})")


def main() -> int:
    args = sys.argv[1:]
    if "--check" in args:
        if not PULSE.is_file():
            print("synchrony_pulse: FAIL — no proof/synchrony_pulse.json (session is not time-aware)")
            return 1
        p = load()
        for k in ("boot", "lastActivity", "currentPhase"):
            if k not in p:
                print(f"synchrony_pulse: FAIL — pulse missing '{k}' (boot/activity map incomplete)")
                return 1
        gap = since(p["lastActivity"])
        if gap > STALE_HOURS:
            # A pulse measures SESSION liveness, not commit quality. In a detached checkout
            # (GitHub Actions) there is no session, so the age of the last committed activity
            # stamp says nothing about the bytes under test. Grading it here made every run
            # red 24h after the last push, no matter what the code did: a wall clock cannot
            # be satisfied by a commit. On a runner this is a named SKIP (exit 3), and the
            # session-liveness question stays with the session that can answer it.
            if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
                print(f"synchrony_pulse: SKIP — detached CI run, no session clock to grade "
                      f"(committed stamp {gap:.1f}h old); session liveness is judged where "
                      f"the session lives")
                return 3
            print(f"synchrony_pulse: FAIL — last activity {gap:.1f}h ago (> {STALE_HOURS}h): "
                  f"the session has not tracked the Operator")
            return 1
        print(f"synchrony_pulse: PASS — boot-aware; last activity {gap:.1f}h ago; "
              f"phase {p['currentPhase']}")
        return 0

    p = observe(mark="--mark" in args)
    show(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
