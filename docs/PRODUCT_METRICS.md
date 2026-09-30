# Product metrics

Use organization-level pseudonymous identifiers. Do not put emails, uploaded rows, prompts, credentials or operational values into product analytics. Optional PostHog capture exists; it is not enabled or verified here. Full event coverage remains pending.

| Metric | Definition | Source |
|---|---|---|
| Demo conversion | accepted inquiries / eligible website sessions | inquiry store + consented web analytics |
| Activation | org imports valid data and reviews first dashboard within 7 days | import jobs + dashboard event (pending) |
| Time to value | first useful customer-confirmed insight minus org creation | pilot review register |
| Weekly active orgs | distinct orgs with meaningful operational actions in 7 days | approved event instrumentation |
| Import success | successful rows / processed rows; also track failed jobs | import_jobs |
| Connector health | success rate, lag, retries and failures | connector job logs/metrics |
| Copilot adoption | orgs using Copilot and useful answers confirmed | AI reports + customer feedback |
| Trial-to-paid | new paying orgs / eligible trials in cohort | Stripe reconciled billing records |
| MRR | normalized recurring contracted revenue excluding taxes/one-off fees | Stripe reconciliation |
| ARR | 12 × MRR | derived |
| Logo retention | retained beginning-cohort customers / beginning cohort | billing/customer register |
| Revenue retention | retained recurring revenue / starting cohort revenue | billing; separate expansion |

Event backlog: first login/dashboard/entity review, import start/completion, risk review, simulation, invite, checkout and subscription lifecycle. Validate duplicates and consent before activation. Do not infer active adoption from logins alone. Proposed pilot reporting is weekly; ownership must be assigned before customer onboarding.
