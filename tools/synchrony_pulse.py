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
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build" / "gen"))
sys.path.insert(0, str(ROOT / "tools"))

from omega_time_runtime import (  # noqa: E402
    boot_stamp, classify, device_relation, iso, phase, since, stamp,
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


def observe(mark: bool = False) -> dict:
    prev = load()
    now_iso = iso()
    boot = prev.get("boot") or boot_stamp()
    last = now_iso if (mark or not prev.get("lastActivity")) else prev["lastActivity"]
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
