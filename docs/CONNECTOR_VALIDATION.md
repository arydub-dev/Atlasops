# Connector validation for the supervised pilot

Status: all real external connector sandboxes NOT VERIFIED. Credentials belong in tenant-encrypted connector storage; never in NEXT_PUBLIC variables, test snapshots or documentation.

| Connector | Implemented authentication | Read direction / objects | Limits and caveats |
| --- | --- | --- | --- |
| Salesforce | client credentials, refresh token, or username/password (+ security token) | Salesforce Account → ATLASOPS Supplier; incremental SystemModstamp, configured API version default v59.0 | Default 50 pages/10,000 records; bounded retries; incomplete sync must not advance cursor. Developer Edition is not necessarily the test.salesforce.com sandbox login; use its actual My Domain/token configuration. |
| Dynamics BC | Microsoft OAuth client credentials or refresh token; tenant_id/client_id/client_secret | items → Products; salesOrders → Shipments through BC API v2.0 | Bounded pagination 50 pages/10,000 per collection; company/environment mapping required. Reconcile shipment mapping; do not assume order data is actual carrier tracking. |
| UPS | OAuth client credentials | Existing tenant shipment tracking numbers → shipment status/events | 1000 shipments/run maximum; narrow configured tracking scope when exceeded. No automatic discovery of all carrier shipments. |

The current connectors consume supplied OAuth credentials; a complete browser authorization-code enrollment/callback flow is not established by these implementations. Do not claim a turnkey “Connect with Salesforce” OAuth journey until implemented/verified. WorkOS callback is unrelated to connector OAuth.

## Sandbox setup and verification

For Salesforce, create/choose a Developer Edition org and provider-approved integration application/user with access to Account fields consumed by `salesforce.py` and the API/refresh-token permissions required by the selected grant. Provider app policy determines available grants/scopes; confirm them in the actual sandbox. Prefer scoped credentials over broad administrator access. Record the permitted objects/fields, provider API version, auth mode and application ID (not secret).

For BC, select a trial/sandbox tenant/environment and company, configure the Microsoft application/service principal permissions required by BC for the implemented objects, and grant only the needed company access. Confirm actual consent and permissions in that tenant before testing.

For UPS, use the developer/test endpoint and test credentials from the provider; set the configured base URL accordingly. Never point tests at customer tracking credentials. Verify returned statuses against the supported mapping.

For each connector:
1. Create two staging organizations; configure the sandbox in only one.
2. Test authentication/discovery, then enqueue a sync through the actual API and run the Render worker against Upstash.
3. Reconcile source object counts/IDs and field values with destination records; inspect rejects/duplicates. Repeat without adding source rows and confirm no duplicate creation.
4. Change a source record, verify incremental update/cursor, and test pagination beyond the first page.
5. Test invalid/revoked credentials, provider throttle/timeout, retry exhaustion, interrupted worker and recovery. Never induce faults in production.
6. Verify the other tenant cannot read configuration, records, job/import IDs or trigger the connection. Confirm errors/logs contain no tokens or provider payloads.
7. Record timestamp, release, environment, connection/job/import identifiers, expected versus actual counts, failures and operator sign-off.

If any result is missing, mark NOT VERIFIED. Keep beta connectors outside paid promises until this evidence is complete. Detailed vendor setup/scopes must be finalized against the actual sandbox configuration, rather than guessing permissions from the connector name.
