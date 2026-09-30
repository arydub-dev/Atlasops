# Go-to-market

Positioning: Turn supply chain complexity into operational decisions. ATLASOPS sits above fragmented operational systems and helps teams prioritize exceptions.

Funnel: public website → demo inquiry (`/contact`) → discovery → scoped pilot → account/org setup → validated import → useful operational review → configured paid subscription → additional users/sources.

Start with a small number of qualified distribution/manufacturing pilots that can provide structured exports. Do not advertise arbitrary ERP integration, certification, uptime, customer logos or quantified savings without evidence.

Pricing hypothesis: Starter for small teams (10 users, 3 connectors), Professional for regular operations (50 users, 15 connectors), Enterprise for scoped requirements. Keep existing internal Professional identifier; renaming it Growth adds no launch value. Actual feature limits live in `backend/app/billing/plans.py`; Stripe price IDs are environment configuration. Website quotes are not a binding price. Validate willingness to pay in discovery before publishing prices.

Compare categories honestly: ERP/WMS/TMS retain transactional workflows; BI supports general analysis; spreadsheets offer flexibility; ATLASOPS focuses on unified operational exception review and decision support. No claim about a named competitor has been researched or made here.

Next 30 days: first complete live release gates; then conduct discovery with qualified teams, run focused demos, onboard a small approved pilot cohort, review activation weekly and revise scope/pricing from observed customer value. No outbound messages or real-customer onboarding were performed.
