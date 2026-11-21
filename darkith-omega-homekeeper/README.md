# Darkith Omega Homekeeper

This is the executable specification and codebase for the **Darkith Omega Homekeeper**. It enforces the four-core invariant (A∧B∧C∧D) on reality-coupled units.

## Structure

- `src/invariant.ts`: Layer 0. The core A∧B∧C∧D definition.
- `src/record.ts`: Layer 2. Claim records, capability deltas, and the fleet separation-of-powers.
- `src/unit.ts`: Layer 1. The Unit interface (9 fields).
- `src/repository.ts`: Layer 3. The `admitted()` and `validate()` logic.
- `src/omega.ts`: The fixed-point calculation (`omega()`).
- `src/reader.ts`: The single-file HTML generator. It projects a Unit into `src/reader-shell.html` — a byte-exact twin of the repo's canonical `omega-reader.html` (parity gate: drift FAILS the suite).
- `src/reader-shell.html`: The canonical reader shell (NEVER edit here to change design — edit `omega-reader.html` at the repo root and re-copy).
- `src/cli.ts`: The `omega-hk` command-line interface (`demo`, `verify`, `render`, `sweep`).
- `src/sample.ts`: The sample admitted Unit used by `demo` and the reader gates.
- `src/tests.ts`: The test runner (A1–A9, separation of powers, omega).
- `tools/build_master.py`: Regenerates `../darkith-omega-master.html` from the verified bytes on disk (idempotent: two runs are byte-identical, MUST #18).

## How to Run the Tests

1. Ensure Node.js is installed.
2. Navigate to `darkith-omega-homekeeper/`.
3. Run:

```bash
npm install
npm test
```

This will compile the TypeScript (strict mode) and execute the test suite (17 passing, 0 failed).

## Command Line

After `npm run build` (or as a global install via `npm link`):

```bash
omega-hk verify my-unit.unit.json                 # admission report; exit 0 = admitted
omega-hk verify my-unit.unit.json --repo repository.json
omega-hk render my-unit.unit.json my-unit.html    # standalone HTML reader (refuses non-admitted units)
omega-hk sweep units/ out/                        # verify every *.unit.json, render the Omega fixed-point
omega-hk demo sample.html                         # generate a sample admitted unit + its reader page
```

`verify` and `sweep` derive the default `repository.json` (registry + validation records) from the candidate units themselves when none is supplied.

## How to use render()

The `render(unit: Unit)` function in `src/reader.ts` takes an Admitted Unit and returns a complete, standalone HTML string.

```typescript
import { render } from "./reader.js";
import { Unit } from "./unit.js";

const myUnit: Unit = { /* ... */ };
const html = render(myUnit);
// Write the HTML string to a .html file and open it in a browser.
```
