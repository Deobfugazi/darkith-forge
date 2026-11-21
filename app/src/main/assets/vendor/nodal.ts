const GENESIS_SEED = "DARKITH_NODAL_GENESIS_v1";
const LAW = "no undefined pass; every gate is a total function; order is precomputed, never negotiated";

const K: readonly number[] = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
];

function rotr(x: number, n: number): number {
  return (x >>> n) | (x << (32 - n));
}

function utf8Bytes(str: string): number[] {
  const out: number[] = [];
  for (let i = 0; i < str.length; i++) {
    const c = str.charCodeAt(i);
    if (c < 0x80) out.push(c);
    else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    else if (c < 0xd800 || c >= 0xe000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    else {
      i++;
      const cp = 0x10000 + (((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
      out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
    }
  }
  return out;
}

function sha256(str: string): string {
  const bytes = utf8Bytes(str);
  const h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const l = bytes.length;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  const bits = l * 8;
  for (let i = 7; i >= 0; i--) bytes.push((bits / Math.pow(2, i * 8)) & 0xff);

  const w = new Array<number>(64);
  for (let off = 0; off < bytes.length; off += 64) {
    for (let t = 0; t < 16; t++) {
      w[t] = (bytes[off + t * 4] << 24) | (bytes[off + t * 4 + 1] << 16) |
             (bytes[off + t * 4 + 2] << 8) | bytes[off + t * 4 + 3];
    }
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3);
      const s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10);
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
    }
    let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (hh + S1 + ch + K[t] + w[t]) | 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) | 0;
      hh = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0;
    h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
  }
  return h.map((x) => ("00000000" + (x >>> 0).toString(16)).slice(-8)).join("");
}

const GENESIS_WITNESS = sha256(GENESIS_SEED);

const Verdict = {
  ALLOW: "allow",
  DENY: "deny",
  ROUTE: "route",
  OBSERVE: "observe",
  DEGRADED: "degraded"
} as const;
type VerdictValue = (typeof Verdict)[keyof typeof Verdict];

const DegradedClass = {
  UPSTREAM_MISSING: "upstream_missing",
  UPSTREAM_STALE: "upstream_stale",
  STALE_EPOCH: "stale_epoch",
  INTERNAL_ERROR: "internal_error",
  POLICY_MISSING: "policy_missing",
  DOWNSTREAM_OF_DEGRADED: "downstream_of_degraded"
} as const;
type DegradedClassValue = (typeof DegradedClass)[keyof typeof DegradedClass];

const VERDICT_VALUES: readonly string[] = Object.values(Verdict);
const CLASS_VALUES: readonly string[] = Object.values(DegradedClass);

class SchemaViolation extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SchemaViolation";
  }
}

export interface ReceiptSpec {
  engineId: string;
  boundary: string;
  epoch: number;
  seq: number;
  lane: string;
  inputHash: string;
  verdict: string;
  clause: string;
  degradedClass?: string | null;
  upstreamIds?: readonly string[];
  policyVersion?: string;
  witness?: string;
  tWallNs?: number;
}

export interface Receipt {
  readonly engineId: string;
  readonly boundary: string;
  readonly epoch: number;
  readonly seq: number;
  readonly lane: string;
  readonly inputHash: string;
  readonly verdict: string;
  readonly clause: string;
  readonly degradedClass: string | null;
  readonly upstreamIds: readonly string[];
  readonly policyVersion: string;
  readonly witness: string;
  readonly tWallNs: number;
  readonly receiptId: string;
}

function receiptId(r: ReceiptSpec): string {
  return sha256(
    r.engineId + "|" + r.boundary + "|" + r.epoch + "|" + r.seq + "|" + r.lane + "|" +
    r.inputHash + "|" + r.verdict + "|" + r.clause + "|" +
    (r.degradedClass || "") + "|" +
    ((r.upstreamIds || []).slice().sort().join(",")) + "|" + (r.policyVersion || "v0") + "|" +
    (r.witness || "") + "|" + (r.tWallNs || 0)
  );
}

function makeReceipt(spec: ReceiptSpec): Receipt {
  const r = {
    engineId: spec.engineId,
    boundary: spec.boundary,
    epoch: spec.epoch,
    seq: spec.seq,
    lane: spec.lane,
    inputHash: spec.inputHash,
    verdict: spec.verdict,
    clause: spec.clause,
    degradedClass: spec.degradedClass || null,
    upstreamIds: (spec.upstreamIds || []).slice(),
    policyVersion: spec.policyVersion || "v0",
    witness: spec.witness || "",
    tWallNs: spec.tWallNs || 0
  };

  if (!r.engineId || !r.boundary || !r.clause) throw new SchemaViolation("engineId, boundary, and clause are required and non-empty");
  if (!r.lane) throw new SchemaViolation("lane is required and non-empty");
  if (!(r.epoch >= 0)) throw new SchemaViolation("epoch must be a non-negative int, got " + r.epoch);
  if (!(r.seq >= 0)) throw new SchemaViolation("seq must be a non-negative int, got " + r.seq);
  if (VERDICT_VALUES.indexOf(r.verdict) < 0) throw new SchemaViolation("verdict must be a known Verdict, got " + r.verdict);
  if (r.verdict === Verdict.DEGRADED && !r.degradedClass) {
    throw new SchemaViolation("DEGRADED verdict requires a non-null degradedClass -- a degraded receipt with no named class is exactly the undefined-pass failure this schema exists to prevent.");
  }
  if (r.verdict !== Verdict.DEGRADED && r.degradedClass) {
    throw new SchemaViolation("verdict=" + r.verdict + " must not carry a degradedClass (got " + r.degradedClass + "); degradedClass is reserved for verdict=degraded.");
  }
  if (r.degradedClass && CLASS_VALUES.indexOf(r.degradedClass) < 0) {
    throw new SchemaViolation("unknown degradedClass: " + r.degradedClass);
  }

  const final = r as unknown as Receipt;
  Object.defineProperty(final, "receiptId", { value: receiptId(final), enumerable: true });
  Object.freeze(final.upstreamIds);
  return Object.freeze(final);
}

interface LedgerRow {
  receiptId: string;
  lane: string;
  seq: number;
  epoch: number;
  [key: string]: unknown;
}

export interface AppendResult {
  accepted: boolean;
  receiptId: string | null;
  reason: string | null;
  receipt: Receipt | null;
}

export class Ledger {
  private _rows: LedgerRow[];
  private _byId: Record<string, LedgerRow>;
  private _laneHead: Record<string, string>;
  private _laneMaxEpoch: Record<string, number>;

  constructor() {
    this._rows = [];
    this._byId = {};
    this._laneHead = {};
    this._laneMaxEpoch = {};
  }

  _exists(id: string): boolean {
    return !!this._byId[id];
  }

  append(draft: ReceiptSpec): AppendResult {
    const head = this._laneHead[draft.lane];
    const realWitness = head !== undefined ? head : GENESIS_WITNESS;

    const maxEpoch = this._laneMaxEpoch[draft.lane];
    if (maxEpoch !== undefined && draft.epoch < maxEpoch && draft.verdict !== Verdict.DEGRADED) {
      return {
        accepted: false,
        receiptId: null,
        reason: "stale epoch: " + draft.epoch + " < lane high-water " + maxEpoch + " on " + draft.lane + "; a stale writer may only append a degraded receipt",
        receipt: null
      };
    }

    let final: Receipt;
    try {
      final = makeReceipt({
        engineId: draft.engineId, boundary: draft.boundary, epoch: draft.epoch, seq: draft.seq,
        lane: draft.lane, inputHash: draft.inputHash, verdict: draft.verdict, clause: draft.clause,
        degradedClass: draft.degradedClass, upstreamIds: draft.upstreamIds,
        policyVersion: draft.policyVersion, witness: realWitness, tWallNs: draft.tWallNs
      });
    } catch (e) {
      return { accepted: false, receiptId: null, reason: String((e as Error).message || e), receipt: null };
    }

    if (final.verdict !== Verdict.DEGRADED) {
      const missing = final.upstreamIds.filter((u) => !this._byId[u]);
      if (missing.length) {
        return {
          accepted: false,
          receiptId: null,
          reason: "upstream_ids not found in ledger: " + JSON.stringify(missing) + ". Fire a DEGRADED/UPSTREAM_MISSING receipt instead of citing evidence that does not exist.",
          receipt: null
        };
      }
    }

    for (const row of this._rows) {
      if (row.lane === final.lane && row.seq === final.seq) {
        return { accepted: false, receiptId: null, reason: "integrity error (duplicate seq in lane)", receipt: null };
      }
    }

    this._rows.push(final as unknown as LedgerRow);
    this._byId[final.receiptId] = final as unknown as LedgerRow;
    this._laneHead[final.lane] = final.receiptId;
    if (maxEpoch === undefined || final.epoch > maxEpoch) this._laneMaxEpoch[final.lane] = final.epoch;
    return { accepted: true, receiptId: final.receiptId, reason: null, receipt: final };
  }

  readAsof(epoch: number, lane?: string): LedgerRow[] {
    return this._rows
      .filter((r) => r.epoch < epoch && (lane === undefined || r.lane === lane))
      .slice();
  }

  get(id: string): LedgerRow | null {
    return this._byId[id] || null;
  }

  laneReceipts(lane: string): LedgerRow[] {
    return this._rows
      .filter((r) => r.lane === lane)
      .sort((a, b) => a.seq - b.seq);
  }

  lanes(): string[] {
    const seen: Record<string, number> = {};
    const out: string[] = [];
    this._rows.forEach((r) => {
      if (!seen[r.lane]) { seen[r.lane] = 1; out.push(r.lane); }
    });
    return out.sort();
  }

  count(): number {
    return this._rows.length;
  }

  verifyChain(lane: string): string[] {
    const problems: string[] = [];
    let prevId = GENESIS_WITNESS;
    this.laneReceipts(lane).forEach((r) => {
      const recomputed = receiptId({
        engineId: r.engineId as string, boundary: r.boundary as string, epoch: r.epoch, seq: r.seq, lane: r.lane as string,
        inputHash: r.inputHash as string, verdict: r.verdict as string, clause: r.clause as string,
        degradedClass: r.degradedClass as string | null,
        upstreamIds: r.upstreamIds as string[], policyVersion: r.policyVersion as string,
        witness: prevId, tWallNs: r.tWallNs as number
      });
      if (r.witness !== prevId) problems.push("lane=" + lane + " seq=" + r.seq + ": witness=" + r.witness + " but expected " + prevId);
      if (recomputed !== r.receiptId) problems.push("lane=" + lane + " seq=" + r.seq + ": content hash mismatch (stored " + (r.receiptId as string).slice(0, 12) + ", recomputed " + recomputed.slice(0, 12) + ")");
      prevId = r.receiptId as string;
    });
    return problems;
  }

  verifyAll(): string[] {
    let problems: string[] = [];
    this.lanes().forEach((l) => { problems = problems.concat(this.verifyChain(l)); });
    return problems;
  }
}

export interface DecideOut {
  verdict: string;
  clause: string;
  degradedClass?: string | null;
}

export interface FireResult {
  accepted: boolean;
  receiptId: string | null;
  reason: string | null;
  receipt: Receipt;
  traceback: string | null;
  upstreamRows: LedgerRow[];
  readonly verdict: string;
}

export function hashInput(obj: unknown): string {
  let s: string;
  try { s = JSON.stringify(obj) as string; } catch { s = String(obj); }
  return sha256(s === undefined ? "undefined" : s);
}

export class NodalBot {
  engineId: string = "unnamed";
  boundary: string = "unnamed.boundary";
  policyVersion: string = "v0";
  lane: string;
  upstreamEngineIds: string[];
  ledger: Ledger;
  private _seq: number;

  constructor(ledger: Ledger, opts: { lane?: string; upstreamEngineIds?: string[] } = {}) {
    this.ledger = ledger;
    this.lane = opts.lane || this.engineId;
    this.upstreamEngineIds = opts.upstreamEngineIds || [];
    const rows = ledger.laneReceipts(this.lane);
    this._seq = rows.length ? (rows[rows.length - 1].seq as number) + 1 : 0;
  }

  decide(_inputObj: unknown, _upstreamRows: LedgerRow[]): DecideOut {
    throw new Error("decide() not implemented");
  }

  fire(inputObj: unknown, epoch: number, upstreamIds: readonly string[] = []): FireResult {
    const visible: Record<string, LedgerRow> = {};
    this.ledger.readAsof(epoch).forEach((r) => { visible[r.receiptId as string] = r; });

    const upstreamRows: LedgerRow[] = [];
    const missing: string[] = [];
    upstreamIds.forEach((uid) => {
      if (visible[uid]) upstreamRows.push(visible[uid]);
      else missing.push(uid);
    });

    const inputH = hashInput(inputObj);
    const seq = this._seq++;
    const base: ReceiptSpec = {
      engineId: this.engineId, boundary: this.boundary, epoch: epoch, seq: seq, lane: this.lane,
      inputHash: inputH, upstreamIds: upstreamIds, policyVersion: this.policyVersion,
      tWallNs: Date.now() * 1e6
    } as ReceiptSpec;

    let traceback: string | null = null;
    let out: DecideOut;
    if (missing.length) {
      out = {
        verdict: Verdict.DEGRADED,
        clause: this.engineId + ".missing_upstream",
        degradedClass: DegradedClass.UPSTREAM_MISSING
      };
    } else {
      try {
        out = this.decide(inputObj, upstreamRows) || ({ verdict: undefined, clause: undefined } as unknown as DecideOut);
      } catch (err) {
        out = {
          verdict: Verdict.DEGRADED,
          clause: this.engineId + ".internal_error",
          degradedClass: DegradedClass.INTERNAL_ERROR
        };
        traceback = String((err as Error && (err as Error).stack) || err);
      }
    }

    base.verdict = out.verdict;
    base.clause = out.clause;
    base.degradedClass = out.degradedClass || null;
    return this._commit(base, traceback, upstreamRows);
  }

  private _commit(spec: ReceiptSpec, traceback: string | null, upstreamRows: LedgerRow[]): FireResult {
    let draft: Receipt;
    try {
      draft = makeReceipt(spec);
    } catch (e) {
      draft = makeReceipt({
        engineId: spec.engineId, boundary: spec.boundary, epoch: spec.epoch, seq: spec.seq,
        lane: spec.lane, inputHash: spec.inputHash, verdict: Verdict.DEGRADED,
        clause: spec.engineId + ".internal_error",
        degradedClass: DegradedClass.INTERNAL_ERROR, upstreamIds: spec.upstreamIds,
        policyVersion: spec.policyVersion, tWallNs: spec.tWallNs
      });
      traceback = traceback || String((e as Error).message || e);
    }
    const res = this.ledger.append(draft);
    const committed = (res.receipt || draft) as Receipt;
    return {
      accepted: res.accepted,
      receiptId: res.receiptId,
      reason: res.reason,
      receipt: committed,
      traceback: traceback,
      upstreamRows: upstreamRows,
      get verdict(): string { return committed.verdict; }
    };
  }
}

export interface BotRegistration {
  engineId: string;
  upstreamEngineIds?: readonly string[];
}

export function computeFireOrder(registrations: readonly BotRegistration[], epochId: string): string[] {
  const ids: Record<string, boolean> = {};
  const list: string[] = [];
  registrations.forEach((r) => {
    if (ids[r.engineId]) throw new Error("FireOrderViolation: engine " + r.engineId + " registered twice");
    ids[r.engineId] = true;
    list.push(r.engineId);
  });
  list.sort();

  const graph: Record<string, string[]> = {};
  list.forEach((id) => { graph[id] = []; });
  registrations.forEach((r) => {
    (r.upstreamEngineIds || []).forEach((up) => {
      if (!ids[up]) throw new Error("FireOrderViolation: engine " + r.engineId + " declares upstream " + up + " which is not registered");
      if (graph[up].indexOf(r.engineId) < 0) graph[up].push(r.engineId);
    });
  });

  let index = 0;
  const stack: string[] = [];
  const idx: Record<string, number> = {};
  const low: Record<string, number> = {};
  const onStack: Record<string, boolean> = {};
  const sccs: string[][] = [];
  function strongconnect(v: string): void {
    idx[v] = low[v] = index++;
    stack.push(v);
    onStack[v] = true;
    graph[v].slice().sort().forEach((w) => {
      if (idx[w] === undefined) { strongconnect(w); low[v] = Math.min(low[v], low[w]); }
      else if (onStack[w]) { low[v] = Math.min(low[v], idx[w]); }
    });
    if (low[v] === idx[v]) {
      const scc: string[] = [];
      for (;;) {
        const w = stack.pop() as string;
        onStack[w] = false;
        scc.push(w);
        if (w === v) break;
      }
      sccs.push(scc);
    }
  }
  list.forEach((v) => { if (idx[v] === undefined) strongconnect(v); });
  sccs.forEach((scc) => {
    if (scc.length > 1) throw new Error("FireOrderViolation: dependency cycle detected: " + JSON.stringify(scc.sort()));
  });

  const inDeg: Record<string, number> = {};
  list.forEach((id) => { inDeg[id] = 0; });
  Object.keys(graph).forEach((u) => { graph[u].forEach((d) => { inDeg[d]++; }); });

  const tiebreak = (id: string): string => sha256(id + "||" + epochId);
  const byTie = (a: string, b: string): number => (tiebreak(a) < tiebreak(b) ? -1 : 1);

  const ready = list.filter((id) => inDeg[id] === 0).sort(byTie);
  const order: string[] = [];
  while (ready.length) {
    const v = ready.shift() as string;
    order.push(v);
    graph[v].slice().sort(byTie).forEach((w) => {
      if (--inDeg[w] === 0) ready.push(w);
    });
    ready.sort(byTie);
  }
  if (order.length !== list.length) throw new Error("FireOrderViolation: topological sort failed despite an acyclic SCC check");
  return order;
}

export interface ReconcileResult {
  agreed: boolean;
  canonicalId: string | null;
  derivativeIds: string[];
  clause: string;
  reason: string;
}

export function reconcile(receipts: readonly Receipt[], precedence: readonly string[]): ReconcileResult {
  if (!receipts.length) return { agreed: true, canonicalId: null, derivativeIds: [], clause: "coordina.reconcile.empty", reason: "no receipts to reconcile" };
  const rank: Record<string, number> = {};
  precedence.forEach((e, i) => { rank[e] = i; });
  const unknown = receipts.filter((r) => rank[r.engineId] === undefined).map((r) => r.engineId);
  if (unknown.length) {
    return {
      agreed: false,
      canonicalId: null,
      derivativeIds: receipts.map((r) => r.receiptId),
      clause: "coordina.reconcile.unranked",
      reason: "engines " + JSON.stringify(unknown.filter((v, i, a) => a.indexOf(v) === i).sort()) + " produced receipts but are not in the precomputed precedence; the order is not defined, so no receipt is canonical"
    };
  }
  const ordered = receipts.slice().sort((a, b) =>
    (rank[a.engineId] - rank[b.engineId]) || (a.epoch - b.epoch) || (a.seq - b.seq)
  );
  const canonical = ordered[0];
  const derivatives = ordered.slice(1).map((r) => r.receiptId);
  const disagreeing = ordered.slice(1).filter((r) => r.verdict !== canonical.verdict);
  if (disagreeing.length) {
    const named = disagreeing.map((r) => r.engineId + ":" + r.clause + "=" + r.verdict).join(", ");
    return {
      agreed: false,
      canonicalId: canonical.receiptId,
      derivativeIds: derivatives,
      clause: "coordina.reconcile.divergent",
      reason: "canonical " + canonical.engineId + ":" + canonical.clause + "=" + canonical.verdict + " is contradicted by " + named + "; canonical wins by precomputed precedence"
    };
  }
  return {
    agreed: true,
    canonicalId: canonical.receiptId,
    derivativeIds: derivatives,
    clause: "coordina.reconcile.agreed",
    reason: ordered.length + " receipts agree; " + canonical.engineId + " is canonical"
  };
}

export function propagateDegraded(receipt: Receipt, upstreamRows: readonly LedgerRow[] | null): DecideOut {
  const tainted = (upstreamRows || []).filter((row) => row.verdict === Verdict.DEGRADED);
  if (tainted.length) {
    return { verdict: Verdict.DEGRADED, clause: receipt.engineId + ".downstream_of_degraded", degradedClass: DegradedClass.DOWNSTREAM_OF_DEGRADED };
  }
  return { verdict: receipt.verdict, clause: receipt.clause, degradedClass: receipt.degradedClass || null };
}

const api: Record<string, unknown> = {
  LAW: LAW,
  GENESIS_WITNESS: GENESIS_WITNESS,
  Verdict: Verdict,
  DegradedClass: DegradedClass,
  SchemaViolation: SchemaViolation,
  sha256: sha256,
  makeReceipt: makeReceipt,
  receiptId: receiptId,
  Ledger: Ledger,
  NodalBot: NodalBot,
  hashInput: hashInput,
  computeFireOrder: computeFireOrder,
  reconcile: reconcile,
  propagateDegraded: propagateDegraded
};

export default api;
export const NodalLAW = LAW;
