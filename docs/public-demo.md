# Public synthetic demo

Route: /demo. No authentication or backend requests. AuthProvider and DemoModeProvider are omitted only for the isolated /demo route tree; all normal routes retain them. No backend routes, database, migrations or production secrets are changed.

Day 0 is a fixed simulation clock, not current operational time. Fixture: Plant A stock 2 / demand 5; Plant B stock 10 / demand 9; confirmed inbound 3 on Day 5, maintenance Day 3; authorized expedite Day 1 / $90 direct cost. Transfer 3 / $25 produces donor shortage 2 and cannot be proposed.

Browser storage key atlasops-public-demo-v1 holds only synthetic proposal metadata and history. Reset requires confirmation and affects this key only. No passwords, identity guarantees, immutable audit trail, cross-device persistence, AI provider or supplier execution are provided. The owner field must contain fictional information. Errors saving storage prevent successful state transitions.

Node regression tests: node --experimental-strip-types --test frontend/tests/public-demo.test.mjs. Browser/Python parity was separately verified against Recovery Engine revision 364187b8d0d2a7d8c0de1e248a80a5be8e2df338: baseline, donor transfer and expedite quantities agree (6 assertions). This is a limited frontend demo calculator, not a replacement for the full backend engine.

Acceptance: open /demo, Explore Demo, inspect all modules, compare donor risk, propose expedite with owner/rationale/date, simulate approval, record supplier correction, resolve incident, refresh and reopen to inspect history. Restore original scenario and repeat on mobile. Keep enterprise hosted authentication/worker/AI/human acceptance gates separate.
