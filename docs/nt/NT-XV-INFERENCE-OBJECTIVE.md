# NT XV — OMEGA EDITION

## THE CONSTRAINT-SATISFYING INFERENCE OBJECTIVE FOR THE MINIMUM VIABLE SUBSTRATE

**Edition:** OMEGA 1.0 (consolidated from the OMEGA Objective and the Minimum Viable Inference Substrate drafts)
**Date:** 26 November 2026
**Status:** OBJECTIVE DECLARED; IMPLEMENTATION NOT YET VERIFIED
**Scope:** Darkith Omega's local inference substrate and its direct coupling to the existing engine
**Relationship:** NT XV governs the objective and admission policy for Omega inference. It does not claim that the implementation has already satisfied the objective.

---

## §0 — THE OBJECTIVE

Omega exists to execute the smallest useful, constraint-satisfying inference architecture that couples directly to Darkith's engine and produces practical utility within a measured resource budget.

The objective is not maximum model coverage. The objective is **maximum useful inference per unit of memory, compute, storage, latency, integration complexity, and maintenance burden.**

**USEFUL INFERENCE
+ EXACT ENGINE COUPLING
+ VERIFIED NUMERICAL BEHAVIOR
+ BOUNDED RESOURCE COST
− UNJUSTIFIED COMPLEXITY
= OMEGA ADMISSION**

A capability is admitted only when it contributes to this objective and its cost is measured or explicitly bounded.

Omega is **not** tasked with:

- 0.1 Universal GGUF compatibility.
- 0.2 Supporting every architecture, tensor layout, tokenizer, quantization type, or model family.
- 0.3 Reproducing the breadth of llama.cpp or any other general-purpose runtime.
- 0.4 Accumulating fallback paths for models Omega has no operational reason to run.
- 0.5 Treating successful file loading or token emission as proof of useful inference.
- 0.6 Expanding the architecture matrix merely because a new model can be made to run.
- 0.7 Maximizing model size, architecture count, tensor-format count, or compatibility claims.
- 0.8 Spending scarce RAM, compute, storage, or engineering time on compatibility with no measured utility return.

---

## §1 — THE CONTAINER IS NOT THE OBJECTIVE

GGUF is a model-storage and interchange container. Its metadata describes an architecture and its tensors; its extensible structure can carry information for multiple model families and tensor types. That extensibility is a property of the format, not an obligation imposed on Omega [S1].

The distinction is binding:

- GGUF FILE ACCEPTANCE ≠ MODEL EXECUTION SUPPORT
- MODEL EXECUTION SUPPORT ≠ USEFUL INFERENCE
- USEFUL INFERENCE ≠ RESOURCE-QUALIFIED OMEGA ADMISSION

Omega may use GGUF as the selected model delivery format while deliberately admitting only one exact execution profile. GGUF is an artifact container and admission surface, not Omega's product objective.

An input file that is valid GGUF but outside the admitted profile must be rejected **before** costly tensor allocation or inference begins. Rejection is correct behavior when the file violates the declared contract.

---

## §2 — CORE INVARIANT

The engine defines a narrow, explicit execution contract. The model must fit the engine's contract; the engine must not continually expand to accommodate models outside it.

A model is eligible only when its architecture, tensor names and shapes, tensor ordering, numerical representation, tokenizer, positional encoding, context behavior, and required metadata satisfy that contract. Unsupported or ambiguous artifacts must fail admission clearly and early. They must not trigger silent architecture guessing, automatic broadening, hidden conversion, or fallback behavior that changes the declared execution path.

**Rejecting an out-of-contract model is correct behavior.**

---

## §3 — THE MINIMUM VIABLE EXECUTION PROFILE

Omega shall define and lock one target inference profile before expanding implementation.

The profile is not merely an architecture label such as "llama." It is the complete, versioned combination of:

1. Model identity and immutable artifact digest.
2. Architecture identifier and required architectural metadata.
3. Required tensor names, dimensions, ordering, and stored layout (full tensor schema).
4. Exact attention and positional-encoding convention, including the exact RoPE convention, rotary dimension, frequency base, and any required weight-layout transformation.
5. Exact tokenizer model, vocabulary, special-token IDs, and decoding rules.
6. One admitted weight representation / quantization format and its verified decoder.
7. Context ceiling and KV-cache representation, allocation policy, and budget.
8. Required operators, their order, and their implementation path.
9. Engine bridge contract, state ownership, and token-stream behavior.
10. Runtime memory, latency, and utility acceptance limits.

A change to any of these coordinates creates a **new profile revision** and requires revalidation. The engine must not silently broaden its profile because a new file happens to parse. The architecture contract is the boundary of the core — not a list of aspirations.

---

## §4 — ADMISSION CONTRACT: FAIL CLOSED, NOT BROADLY

The admission path is:

```
MODEL FILE
→ HEADER / METADATA VALIDATION
→ PROFILE IDENTITY CHECK
→ TENSOR CONTRACT CHECK (schema, shapes, layouts)
→ TOKENIZER CONTRACT CHECK
→ RoPE / POSITIONAL-ENCODING CONTRACT CHECK
→ RESOURCE PREFLIGHT
→ LOAD / MAP
→ INFERENCE
→ OUTPUT THROUGH THE EXISTING OMEGA ENGINE
→ OUTPUT AND RESOURCE MEASUREMENT
```

Each stage must be inspectable and must produce an explicit result and a defined failure reason.

The admission gate shall:

- Verify the exact architecture and metadata required by the locked profile.
- Verify required tensors, dimensions, tensor types, and layouts.
- Verify the positional-encoding implementation matches the profile; do not infer a layout from a broad family list without a profile-level declaration and test.
- Verify tokenizer and special-token behavior.
- Verify quantization block constraints and decoder support.
- Estimate or measure model-weight, KV-cache, workspace, and runtime allocation costs before committing them.
- Reject missing, contradictory, unsupported, or out-of-budget inputs without silently substituting defaults.
- Avoid allocating the full model before profile and budget checks pass.
- Emit a stable, inspectable admission record.

Admission must reject (deterministically, with a clear reason):

- a different or unknown architecture;
- missing or contradictory required metadata;
- unsupported tensor names, shapes, or layouts;
- unsupported quantization;
- incompatible tokenizer or special-token mapping;
- invalid RoPE parameters;
- context or cache requirements exceeding the declared budget.

Unsupported model families, tensor types, and quantization schemes are **not compatibility defects** when they are outside the declared objective. No silent fallback may turn a rejected model into a different, undocumented execution configuration.

---

## §5 — THE ENGINE IS THE DONOR; THE MODEL MUST COUPLE TO IT

Omega's existing engine is the donor substrate. The admitted model profile is the payload.

The coupling must be direct, inspectable, and bounded. The model must satisfy the engine's execution contract; the engine must not accumulate an indefinite adaptation layer to satisfy unrelated model families.

The coupling contract includes:

- One explicit inference entry point.
- One defined tokenizer-to-token-ID boundary.
- One defined token-ID-to-decoded-output boundary.
- Explicit state and KV-cache ownership.
- Explicit cancellation, completion, and error states.
- No false "started" or "success" response without observable execution or output.
- No duplicated inference engine, hidden runtime, or redundant model slot unless it demonstrably improves the objective.
- No compatibility shim without a recorded need, measured cost, and test.

The smallest implementation is not the one with the fewest lines. It is the one with the **fewest necessary moving parts that still satisfies the verified execution contract.**

---

## §6 — RoPE AND TENSOR-LAYOUT DISCIPLINE

RoPE implementation is architecture-specific evidence, not a reason to create a universal positional-encoding compatibility layer.

The current investigation distinguishes two dimension-pairing conventions:

- **NEOX-style pairing:** dimensions separated by half the rotary dimension.
- **NORM-style pairing:** adjacent dimension pairs.

These conventions are **not interchangeable.** The correct choice must be established for the declared target architecture and its exact weight layout.

Omega shall:

- implement the convention required by its selected target;
- validate rotary dimension and head-dimension constraints;
- document any conversion or permutation applied to query/key weights;
- test the implementation against an independent reference using the same weights, metadata, and tensor layout;
- remove unrelated architecture mappings from the core.

An architecture dictionary containing families Omega does not intend to run is **compatibility drift.**

---

## §7 — RESOURCE ROI IS AN ADMISSION CONDITION

A model is not admitted merely because it fits in memory. Every supported component must earn its footprint.

Omega shall measure, on the actual target device and execution path:

- Model artifact size.
- Resident / mapped weight memory and peak process memory during load and inference.
- KV-cache cost at the admitted context limit.
- Temporary workspace and allocation peaks.
- First-token latency.
- Prefill throughput and decode throughput.
- Sustained behavior under thermal and battery constraints when relevant.
- Task utility on a declared local-use test set.
- Failure rate, output integrity, and recoverability.
- Implementation and maintenance complexity.

The resource budget must include the Android system, Darkith's baseline, the engine, the model, the KV cache, and working allocations. **A model-size estimate alone is not a memory budget.**

The selection rule is NOT "load the largest model that fits." The selection rule is:

**ADMIT THE PROFILE THAT MEETS THE REQUIRED TASK UTILITY
WITH THE LOWEST JUSTIFIED TOTAL RESOURCE AND COMPLEXITY COST.**

A smaller model that reliably completes the required tasks may outrank a larger model that consumes more memory, slows the engine, causes thermal throttling, or adds no measurable practical benefit.

No numeric threshold is invented by this treatise. The target device's actual limits and the task-level acceptance thresholds must be recorded before final admission.

### Quantization and architecture must earn their place

Quantization is a resource trade, not a badge. Omega shall begin with the minimum representation required to validate the execution path, then evaluate the chosen quantized representation against: weight-memory reduction; decoder and operator complexity; numerical deviation from the reference; task-level quality degradation; decode speed and peak memory; implementation and maintenance burden.

Only one production quantization path is admitted initially. Additional formats require a demonstrated, material improvement in the objective and a separate conformance test.

The same rule applies to architectural features. Grouped-query attention, alternative RoPE layouts, MoE routing, normalization variants, speculative decoding, GPU/NPU paths, and other mechanisms are not included merely because they exist in other model families. They are included only if the selected profile requires them and the target implementation proves them.

---

## §8 — VALIDATION STANDARD AND TEST EVIDENCE

Numerical validation and practical utility validation are separate gates.

### 8.1 — Numerical gate

For a controlled test artifact, compare Omega's intermediate values or final logits against an independent reference implementation using identical weights, quantization semantics, metadata, and token inputs. Record: reference implementation and version; exact test artifact and checksum; input token sequence; tested tensors or logits; absolute and relative error metrics; tolerance and pass/fail rule; architecture and RoPE configuration.

Tiny synthetic models are appropriate for isolating arithmetic, tensor-layout, quantization, and execution errors. They are test instruments, not proof of production utility.

### 8.2 — Real-artifact gate

A real model that conforms to the selected contract must run through the intended Omega/Darkith path. Record the artifact identity, checksum, tokenizer, resource measurements, and output behavior.

### 8.3 — Utility gate

The model must demonstrate a defined task or workflow that justifies its resource footprint. A successful forward pass, fluent-looking text, or a low numerical error alone does not establish this gate. **"It generates text" is not sufficient.**

### 8.4 — What the current test evidence establishes

The reported controlled fixtures used synthetic, small GGUF models with two transformer layers, embedding width 64, four attention heads, two KV heads, and feed-forward width 96. The reported F32 and Q8 runs passed their capability checks and matched the supplied reference logits with maximum absolute differences of approximately 2.36×10⁻⁷ and 2.70×10⁻⁷ respectively. The test output also reported successful capability checks, the selected RoPE mode, and a tokenizer decoding check.

This supports a narrow conclusion: **the tested implementation and reference agree closely on the generated fixtures and tested path.**

It does **not** establish:

- Real-model compatibility.
- Useful language behavior.
- Correctness for an unselected architecture.
- Correctness for every RoPE convention.
- Correctness for every tokenizer or quantization format.
- Acceptable memory, latency, or thermal behavior on the target phone.
- Production readiness.

The synthetic fixtures remain diagnostic instruments. They are not the product and do not define the production model. The broad architecture-to-RoPE dictionary shown during development is not an Omega objective and must not become the runtime support policy. The final profile shall name one required convention and test it against an independent implementation or trusted reference.

---

## §9 — THE COMPATIBILITY DRIFT PROHIBITION

The following are prohibited unless an objective-linked evidence record justifies them:

- Expanding the architecture list "for future compatibility."
- Adding quantization decoders without a selected model requiring them.
- Automatically selecting among a ladder of model tiers as a substitute for choosing and validating the target.
- Maintaining multiple resident model variants without a demonstrated user need.
- Adding generic fallback behavior that obscures a profile mismatch.
- Treating successful parsing, token emission, or fluent-looking text as proof of correct inference.
- Replacing direct engine coupling with a separate, bloated runtime whose footprint exceeds its utility.
- Claiming support from metadata recognition alone.
- Silently changing model semantics to make an artifact appear compatible.

A candidate-model bench may compare alternatives during selection. It is not a runtime compatibility matrix. The production admission set remains the single locked profile until a revision is justified.

---

## §10 — IMPLEMENTATION RULES

10.1 Keep the execution path small, direct, and inspectable.
10.2 Prefer explicit constraints over adaptive compatibility.
10.3 Avoid duplicate parsing, decoding, allocation, or transformation paths.
10.4 Do not introduce a generic abstraction unless at least two required use cases justify it and the abstraction reduces total complexity.
10.5 Do not add architecture support without an approved target requirement and complete validation.
10.6 Do not add quantization formats without numerical and resource comparisons.
10.7 Do not silently change model semantics to make an artifact appear compatible.
10.8 Keep tests, fixtures, and reference tooling separate from production inference code where separation reduces runtime footprint.
10.9 Make resource budgets and rejection behavior observable.
10.10 Preserve the exact relationship between model artifact, engine version, configuration, and test evidence.

---

## §11 — VERIFICATION AND FALSIFICATION

Omega's objective is considered satisfied only when **all** of the following are demonstrated:

- **A. Profile closure.** The exact model artifact, architecture, tensors, layout, tokenizer, quantization, context, and engine contract are versioned and reproducible.
- **B. Numerical conformance.** The target model's intermediate or output logits agree with an independent reference within a declared tolerance appropriate to the representation and execution path.
- **C. Functional utility.** The model completes the required local tasks under a predeclared test set.
- **D. Resource closure.** Peak memory, context/KV cost, latency, throughput, and relevant thermal behavior remain within the measured target budget.
- **E. Engine coupling.** The existing Omega surface receives actual token output, errors, cancellation, and completion from the inference path. No stub or false success state remains.
- **F. Rejection correctness.** A deliberately incompatible model or malformed tensor fixture is rejected before expensive allocation, with a clear reason.
- **G. Re-entry.** The complete build, profile admission, test run, and evidence record can be repeated from the repository without hidden state.

**Falsifiers:**

- The selected real model cannot execute correctly through the locked profile.
- The reference comparison exceeds the declared tolerance.
- Required tasks fail at the predeclared utility threshold.
- The model exceeds the actual memory or execution budget.
- The engine bridge reports success without real output or fails to propagate terminal state.
- An unsupported file is silently accepted or triggers uncontrolled allocation.
- A required operator or format cannot be implemented without expanding the profile beyond the declared constraints.

Any falsifier reopens the profile. It does not authorize unbounded compatibility expansion.

---

## §12 — ACCEPTANCE CHECKLIST

NT XV implementation acceptance requires all of the following to be evidenced:

```
[ ] One target architecture and variant are explicitly selected.
[ ] The architecture contract is versioned and machine-checkable where practical.
[ ] Tensor schema, shapes, layouts, and required transformations are fixed.
[ ] RoPE convention and rotary parameters are verified against the target.
[ ] One tokenizer contract is fixed and tested.
[ ] Only required tensor and quantization paths are included.
[ ] Unsupported artifacts are rejected deterministically.
[ ] Synthetic numerical tests pass against an independent reference.
[ ] A real, conforming target model runs through the intended Omega/Darkith path.
[ ] Peak memory and KV-cache use remain within the declared budget.
[ ] Latency and compute measurements are recorded.
[ ] A defined task demonstrates useful inference.
[ ] Utility justifies model, runtime, and maintenance costs.
[ ] No unrequired compatibility layer remains in the core.
[ ] Rejection correctness is demonstrated with a deliberately incompatible fixture.
[ ] The full build/admission/test/evidence loop re-runs from the repository without hidden state (A–G all demonstrated).
```

---

## §13 — OBJECTIVE LEDGER AND CHANGE CONTROL

Every proposed addition to Omega must answer, in an auditable record:

1. Which required task does it enable or improve?
2. Which constraint does it satisfy?
3. What memory, compute, latency, code, dependency, and maintenance cost does it add?
4. What measured baseline is it compared against?
5. What result would justify keeping it?
6. What result would cause it to be removed?
7. Does it change the locked profile or its revision?

Additional change-control questions before implementation:

- What concrete Darkith/Omega task requires this capability?
- What is the smallest implementation that satisfies that task?
- What existing path, if any, can be removed because of it?

If the addition has no measurable or logically necessary contribution to the objective, it is not admitted. The default decision is to **reject unneeded complexity**, not to carry it until it becomes a problem.

---

## §14 — THE OMEGA OBJECTIVE, INVARIANT FORM

Let **P** be the locked inference profile, **E** the existing Omega engine, **U** the required task utility, and **R** the measured resource envelope.

Omega admission requires:

```
P satisfies E's declared execution contract
AND P produces U
AND P remains within R
AND P passes numerical and functional verification
AND unsupported inputs fail closed.
```

The invariant is not "maximum compatibility." The invariant is:

**MINIMUM NECESSARY ARCHITECTURE
+ DIRECT COUPLING
+ VERIFIED UTILITY
+ RESOURCE CLOSURE
+ EXPLICIT REJECTION
= CONSTRAINT-SATISFYING OMEGA**

---

## §15 — STATUS AND NEXT REQUIRED CLOSURE

NT XV declares the objective and the admission law. It does not declare the implementation complete.

The next closure is to **select and record the exact real-model profile, then run that artifact through the intended Darkith engine path.** The profile must be chosen from measured utility and resource results — not from model size, broad architecture availability, or compatibility prestige.

Until that closure passes, Omega's status remains:

```
OBJECTIVE DEFINED
SYNTHETIC NUMERICAL FIXTURES PASSED ON THE REPORTED PATH (F32 ≈ 2.36×10⁻⁷, Q8 ≈ 2.70×10⁻⁷ max abs logit diff)
REAL-MODEL PROFILE NOT YET LOCKED
TARGET-DEVICE ROI NOT YET VERIFIED
PRODUCTION ADMISSION NOT YET PASSED
```

Implementation status remains OPEN until the acceptance checklist (§12) is supported by reproducible evidence.

**Success is not the number of model formats supported.**
**Success is reliable, useful inference whose value exceeds its total resource and complexity cost.**

The model must satisfy Omega's contract. Omega must not drift into a universal compatibility layer.

---

## §16 — SOURCES AND ATTRIBUTION

**[S1]** ggml-org, "GGUF," official format documentation:
https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
The documentation describes GGUF as a model-storage format for inference with GGML-based executors and documents architecture metadata, tensor descriptors, tensor types, and format extensibility. Accessed 26 November 2026.

Interpretation used here: GGUF's ability to carry varied model metadata does not require Omega to implement every architecture or tensor type. That is the NT XV design rule derived from Darkith's stated objective, **not a claim made by the GGUF specification.**

END NT XV — OMEGA EDITION 1.0