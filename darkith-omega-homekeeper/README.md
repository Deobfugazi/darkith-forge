# Darkith Omega Homekeeper

This is the executable specification and codebase for the **Darkith Omega Homekeeper**. It enforces the four-core invariant (A∧B∧C∧D) on reality-coupled units.

## Structure

- `src/invariant.ts`: Layer 0. The core A∧B∧C∧D definition.
- `src/record.ts`: Layer 2. Claim records, capability deltas, and the fleet separation-of-powers.
- `src/unit.ts`: Layer 1. The Unit interface (9 fields).
- `src/repository.ts`: Layer 3. The `admitted()` and `validate()` logic.
- `src/omega.ts`: The fixed-point calculation (`omega()`).
- `src/reader.ts`: The single-file HTML generator.
- `src/tests.ts`: The test runner (A1–A9, separation of powers, omega).

## How to Run the Tests

1. Ensure Node.js is installed.
2. Navigate to `darkith-omega-homekeeper/`.
3. Run:

```bash
npm install
npm test
```

This will compile the TypeScript (strict mode) and execute the test suite (13 passing, 0 failed).

## How to use render()

The `render(unit: Unit)` function in `src/reader.ts` takes an Admitted Unit and returns a complete, standalone HTML string.

```typescript
import { render } from "./reader.js";
import { Unit } from "./unit.js";

const myUnit: Unit = { /* ... */ };
const html = render(myUnit);
// Write the HTML string to a .html file and open it in a browser.
```
