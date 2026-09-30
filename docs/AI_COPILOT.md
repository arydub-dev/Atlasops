# Operations Copilot

The API checks `ai.chat`; retrieval checks domain permissions and organization scope. Report history is scoped to organization and user. The local engine supports deterministic offline answers. Optional OpenAI uses the authorized context; a context snapshot is saved with chat reports. Orchestration adds graph/timeline context and citations where available.

The launch audit fixed a PostgreSQL date-query failure that broke context retrieval. Optional data-source retrieval now uses a savepoint so an unavailable context does not poison the surrounding transaction, and reports that context as unavailable rather than fabricated demo data.

Generated text is not a verified fact merely because the prompt says “do not invent.” Review observed records, computed metrics, inferences and recommendations separately. Never execute supply-chain changes from a generated answer. Simulations use assumptions and estimates, not guaranteed forecasts.

Implemented limits: 20-second configured provider timeout, no automatic retries, 1,200 output-token cap and 40,000-character context cap (configurable). PostgreSQL row locks serialize credit checks through report commit. Orchestration passes the retrieved context into the provider; hard-coded confidence percentages were removed because no calibrated confidence model exists.

Remaining launch work: injection/adversarial evaluation on the real provider and cost alert delivery. Per-minute rate limits, quota locks and token caps are not proof of hallucination resistance. Do not enable paid AI at scale until these gates pass. Configure provider credentials only in the backend and use a provider budget limit. No live provider request was executed in this audit.

SDK timeout/retry controls were checked against the installed SDK and [official OpenAI Python documentation](https://developers.openai.com/api/reference/python). No live provider call was made.
