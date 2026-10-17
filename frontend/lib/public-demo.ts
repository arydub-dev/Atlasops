/** Synthetic-only subset of Recovery Engine allocation rules. Never calls an API. */
export const KEY = 'atlasops-public-demo-v1';
export type Stage = 'investigating' | 'proposed' | 'approved' | 'confirmed' | 'resolved';
export type State = { version: 1; stage: Stage; rationale: string; owner: string; due: string; history: { at: string; detail: string }[] };
export const initial = (): State => ({ version: 1, stage: 'investigating', rationale: '', owner: '', due: '', history: [] });
export const fixture = { sku: 'SPARE-1', name: 'Pump seal assembly', stockA: 2, demandA: 5, stockB: 10, demandB: 9, requiredDay: 3, promisedDay: 5, leadDays: 1, inbound: 3, transferCost: 25, expediteCost: 90 };
// Day 0 is a fixed simulation clock, not today's operational evidence.
export function calculate(s = fixture, action: 'none' | 'transfer' | 'expedite' = 'none') {
  const shortage = Math.max(0, s.demandA - s.stockA);
  const transfer = action === 'transfer' ? Math.min(shortage, s.stockB) : 0;
  const arrival = action === 'expedite' ? s.leadDays : s.promisedDay;
  const incoming = arrival <= s.requiredDay ? s.inbound : 0;
  const transferredOnTime = s.leadDays <= s.requiredDay ? transfer : 0;
  return { shortage: Math.max(0, s.demandA - s.stockA - incoming - transferredOnTime), donorShortage: Math.max(0, s.demandB - (s.stockB - transfer)), donorSurplus: Math.max(0, s.stockB - s.demandB), arrival, transfer };
}
export function transition(state: State, next: Stage, fields?: { rationale: string; owner: string; due: string }): State {
  const stages: Stage[] = ['investigating', 'proposed', 'approved', 'confirmed', 'resolved'];
  if (stages.indexOf(next) !== stages.indexOf(state.stage) + 1) throw new Error('Complete the preceding workflow step first.');
  if (next === 'proposed' && (!fields?.rationale.trim() || !fields.owner.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(fields.due))) throw new Error('Enter a rationale, owner and tracking due date.');
  if (calculate(fixture, 'expedite').shortage) throw new Error('The expedite scenario does not restore readiness.');
  const descriptions = { investigating: '', proposed: 'Expedite proposal recorded. No supplier order sent.', approved: 'Simulated planner approval recorded. Physical inventory unchanged.', confirmed: 'Synthetic supplier confirmation: PO-1 promise corrected from Day 5 to Day 1. Source: demo confirmation; no external supplier contacted.', resolved: 'INC-001 resolved against the recorded synthetic confirmation. No physical receipt claimed.' };
  return { ...state, ...fields, stage: next, history: [...state.history, { at: new Date().toISOString(), detail: descriptions[next] }] };
}
export function restore(raw: string): State {
  const s = JSON.parse(raw); const stages = ['investigating', 'proposed', 'approved', 'confirmed', 'resolved'];
  if (s?.version !== 1 || !stages.includes(s.stage) || !['rationale','owner','due'].every(k => typeof s[k] === 'string') || !Array.isArray(s.history) || s.history.length !== stages.indexOf(s.stage) || !s.history.every((h: {at: unknown; detail: unknown}) => typeof h.at === 'string' && typeof h.detail === 'string')) throw new Error('Stored demo state is invalid. Restore the synthetic scenario to continue.');
  return s;
}
export function answer(question: string, state: State): string {
  const q = question.toLowerCase(); const confirmed = ['confirmed','resolved'].includes(state.stage);
  if (/another|other (org|tenant)|customer|secret|password/.test(q)) return 'Only the public synthetic records in this workspace are available. No customer or other organization data is connected.';
  if (/deliver|yesterday|10000|10,000|received/.test(q)) return 'Cannot verify that delivery from these records. PO-1 is a dated synthetic commitment, not proof of physical receipt.';
  if (/transfer|plant b|donor/.test(q)) { const r = calculate(fixture,'transfer'); return `Fact: Plant B holds ${fixture.stockB} units and needs ${fixture.demandB}. Calculation: transferring ${r.transfer} leaves ${fixture.stockB-r.transfer}, creating a ${r.donorShortage}-unit donor shortage. This option is blocked.`; }
  if (/expedite|cost|option/.test(q)) return 'Calculation: a 3-unit arrival on Day 1 covers Plant A’s Day 3 requirement. Recorded direct cost: $90 USD. Assumptions: permission AUTH-EXPEDITE and a one-day supplier lead time. Estimate only; transport costs and execution are not verified.';
  if (/short|spare|plant a|readiness/.test(q)) return confirmed ? 'Recorded synthetic correction: PO-1 promises 3 units on Day 1. Calculation: 2 on hand + 3 supported inbound = 5 needed by Day 3; readiness is READY. Physical receipt is not established.' : 'Facts: SPARE-1 has 2 units at Plant A; WO-A needs 5 by Day 3. PO-1 arrives on Day 5. Calculation: 5 − 2 = 3 units short by the required date.';
  return 'I cannot establish that from the available synthetic records. Try asking about the Plant A shortage, Plant B transfer risk, or expedite timing and cost. This is a deterministic record guide, not a live AI provider.';
}
