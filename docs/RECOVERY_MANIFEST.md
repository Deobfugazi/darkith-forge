# Recovery manifest — reconstructed from the conversation event store

Source: `/var/openhands/conversations/18393131094c4acfb45d943764549f23/events/`
Method: replay every `file_editor` `create` then apply each `str_replace` in timestamp order.

| recovered file | bytes | target path | fidelity |
|---|---|---|---|
| VERSION.md | 3347 | `/workspace/project/VERSION.md` | exact (single create) |
| DEFICIT_LEDGER.md | 5442 | `/workspace/project/DEFICIT_LEDGER.md` | exact (single create) |
| RECONCILIATION.md | 6394 | `/workspace/project/RECONCILIATION.md` | exact (create + 1 replace) |
| darkith-forge__tools__comment_balance.py | 3794 | `darkith-forge/tools/comment_balance.py` | exact (create + 1 replace) |
| delivery___verify.py | 1360 | `delivery/_verify.py` | exact (single create) |
| tree_omega__core__IRAuditor.kt | 2681 | `tree_omega/app/src/main/java/com/darkith/transliaison/core/IRAuditor.kt` | exact (single create) |

Not reconstructable from edits alone (staging copies; canonical twins survive):
- `tree_omega/MainActivity.kt`, `tree_omega/HomekeeperActivity.kt`, `tree_omega/core/SelfTest.kt`
  — these were flat staging paths edited by `str_replace` only, no `create` base.
  Their canonical versions live under `*/app/src/main/java/com/darkith/transliaison/`.
d02ae45f5474aa059a5564fef44784ad38e2f1c9108a049fb0b551161a3739fe  recovery/conversation-18393131094c4acfb45d943764549f23-trajectory.zip
