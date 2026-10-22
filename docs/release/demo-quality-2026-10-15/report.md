# AtlasOps QA Report

Overall: **FAIL** · Release: **NOT READY**

isolated synthetic SQLite / local provider / Chromium / development frontend; not hosted acceptance

{'total': 901, 'pass': 871, 'fail': 0, 'blocked': 4, 'skipped': 26}

## Areas

- AI factuality: **PASS**
- AI tenant isolation: **BLOCKED**
- authentication: **BLOCKED**
- authorization: **PASS**
- background jobs: **PASS**
- critical workflow: **PASS**
- database integrity: **PASS**
- imports: **PASS**
- inventory reconciliation: **PASS**
- production smoke: **BLOCKED**
- regression: **PASS**
- tenant isolation: **PASS**
- visual review: **BLOCKED**

## Actual failures


## Blocked / required actions

- **HOST-001**: No approved hosted synthetic tenant configured. Hosted authenticated import/action/persistence smoke remains unverified.
- **SSO-001**: WorkOS hosted login/invitation/session lifecycle needs a staging identity configuration.
- **AI-LIVE-001**: Local provider checks do not establish hosted LLM isolation or prompt-injection resistance.
- **VISUAL-REVIEW-001**: Screenshots and horizontal overflow checks supplement, but do not replace, human visual review.

## Warnings

- No numeric health score. Passing assertions establish only their named scope.
- Regression checks, browser checks and unmet release prerequisites are counted separately by ID.
- Shared seed is ordered: import updates HP-240 from 42 to 80; each run recreates its own database.

## Regression catalog and evidence

| ID | Area | Status | Evidence |
|---|---|---|---|
| REG-316e39317a76 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_outside_summary_limit[chat] |
| REG-728a245b2da8 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_outside_summary_limit[orchestrate] |
| REG-3fb02f28f304 | inventory reconciliation | PASS | regression.xml#tests.test_advisor_factual_requests.test_broad_inventory_summary_remains_bounded |
| REG-3a4bf4e7a55c | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_without_evidence_abstains[chat] |
| REG-e61da2305d0e | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_without_evidence_abstains[orchestrate] |
| REG-4a7df534702a | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_with_evidence_identifies_record[chat] |
| REG-318d8068dc21 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_with_evidence_identifies_record[orchestrate] |
| REG-ffa1d1481500 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_healthy_sku_uses_zero_replenishment |
| REG-7e49ef332854 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_without_current_position_does_not_substitute_other_stock |
| REG-ee19e7496f85 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_sku_matching_is_whole_identifier |
| REG-fbfec7902863 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_specific_facts_do_not_depend_on_external_provider[chat] |
| REG-d2da65819423 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_specific_facts_do_not_depend_on_external_provider[orchestrate] |
| REG-681785ce5324 | tenant isolation | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_matching_only_other_tenant_still_abstains[chat] |
| REG-67867c0e741b | tenant isolation | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_matching_only_other_tenant_still_abstains[orchestrate] |
| REG-eb9725754f03 | tenant isolation | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_never_retrieves_same_sku_from_other_tenant |
| REG-2c71665d8116 | authorization | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_requires_both_read_permissions[shipments.read] |
| REG-acdd9eebac25 | authorization | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_requires_both_read_permissions[suppliers.read] |
| REG-e759b1abd2da | authorization | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_does_not_bypass_inventory_permissions[inventory.read] |
| REG-714739128187 | authorization | PASS | regression.xml#tests.test_advisor_factual_requests.test_explicit_sku_does_not_bypass_inventory_permissions[warehouses.read] |
| REG-150dc190a1a0 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[quantity] |
| REG-4b123e077696 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[date] |
| REG-02a9d2ba555d | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[status] |
| REG-e09a24a70ac6 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[timestamp] |
| REG-e6c15b4d915f | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_delivery_utc_day_boundaries |
| REG-6a805563e5fc | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered at least 10,000 units yesterday?] |
| REG-0f598bc503a6 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10,000 units yesterday in Tokyo?] |
| REG-c0844ca6a736 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10,000 units on 2026-02-30?] |
| REG-cd781ececded | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Did Acme deliver 10,000 units yesterday?] |
| REG-a46299416c76 | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10.5 units yesterday?] |
| REG-efd38c6ab31c | regression | PASS | regression.xml#tests.test_advisor_factual_requests.test_supplier_summary_still_answers_summary_question |
| REG-03b9bb88e0ce | AI factuality | PASS | regression.xml#tests.test_ai_providers.test_get_ai_provider_defaults_to_local |
| REG-0d8d87fb255f | AI factuality | PASS | regression.xml#tests.test_ai_providers.test_local_engine_grounds_in_context |
| REG-b4a311a2224c | inventory reconciliation | PASS | regression.xml#tests.test_ai_providers.test_simulation_prompt_does_not_invent_numbers |
| REG-b32cb993c428 | AI factuality | PASS | regression.xml#tests.test_ai_providers.test_provider_has_bounded_timeout_output_and_no_retries |
| REG-754a1be0a724 | AI factuality | PASS | regression.xml#tests.test_ai_providers.test_provider_context_limit_prevents_request |
| REG-36260049e3da | AI factuality | PASS | regression.xml#tests.test_ai_providers.test_orchestration_uses_retrieved_context_without_fake_confidence |
| REG-00ea226de827 | regression | PASS | regression.xml#tests.test_api_tokens.test_api_token_can_call_api |
| REG-72f4d39b6688 | regression | PASS | regression.xml#tests.test_api_tokens.test_revoked_api_token_rejected |
| REG-a78e48fa7805 | regression | PASS | regression.xml#tests.test_api_tokens.test_orphaned_token_creator_rejected |
| REG-489e4f13211e | authentication | PASS | regression.xml#tests.test_auth_guards.test_unauthenticated_domain_apis_return_401 |
| REG-23791741ba91 | authentication | PASS | regression.xml#tests.test_auth_guards.test_invalid_org_header_returns_400 |
| REG-24be3db16040 | authentication | PASS | regression.xml#tests.test_auth_guards.test_non_member_org_header_returns_403 |
| REG-8c47df5f0f5e | authentication | PASS | regression.xml#tests.test_auth_guards.test_logout_revokes_session |
| REG-6d461858a89e | tenant isolation | PASS | regression.xml#tests.test_auth_guards.test_cross_org_alert_and_connection_isolation |
| REG-22fb87b4b4ba | authentication | PASS | regression.xml#tests.test_auth_guards.test_invite_accept_http_flow |
| REG-0b285ffb400d | authentication | PASS | regression.xml#tests.test_auth_guards.test_cannot_escalate_to_owner_via_patch |
| REG-45d1d61d2708 | authentication | PASS | regression.xml#tests.test_auth_guards.test_auth_rate_limit_triggers |
| REG-cd176d174916 | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_plans_remain_public |
| REG-58b2e2b2e9ca | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/usage/{org_id}] |
| REG-c199261eae6b | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/account/{org_id}] |
| REG-e04c73775f8e | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/checkout/{org_id}] |
| REG-33a6acab78f2 | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/portal/{org_id}] |
| REG-82361e4cf743 | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/cancel/{org_id}] |
| REG-0a6c63ad8af2 | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/usage] |
| REG-0d25f7de3f84 | authentication | PASS | regression.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/account] |
| REG-9c4d383d7b2a | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/usage/{org_id}] |
| REG-693ae60c3c62 | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/account/{org_id}] |
| REG-cad0373e0942 | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/checkout/{org_id}] |
| REG-67ea0ca0e40d | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/portal/{org_id}] |
| REG-ea53d348bfb7 | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/cancel/{org_id}] |
| REG-f2981b2e8e59 | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/usage] |
| REG-c9182e634a72 | authentication | PASS | regression.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/account] |
| REG-e287870d9696 | authentication | PASS | regression.xml#tests.test_billing_authz.test_cross_org_billing_path_denied |
| REG-dcc1060556b8 | authentication | PASS | regression.xml#tests.test_billing_authz.test_spoofed_org_header_denied |
| REG-aed893c8fdf1 | authentication | PASS | regression.xml#tests.test_billing_authz.test_owner_can_read_own_billing_account |
| REG-e27b3afa20e7 | database integrity | PASS | regression.xml#tests.test_billing_authz.test_open_redirect_urls_rejected |
| REG-382f8d75b896 | regression | PASS | regression.xml#tests.test_business_email.test_personal_domains_rejected[user@gmail.com] |
| REG-cb7b9cadbc96 | regression | PASS | regression.xml#tests.test_business_email.test_personal_domains_rejected[user@GMAIL.COM] |
| REG-79f8d54cb48a | regression | PASS | regression.xml#tests.test_business_email.test_personal_domains_rejected[user@outlook.com] |
| REG-a36c2b106292 | regression | PASS | regression.xml#tests.test_business_email.test_personal_domains_rejected[user@sub.mailinator.com] |
| REG-297a8fc29107 | regression | PASS | regression.xml#tests.test_business_email.test_personal_domains_rejected[user@proton.me] |
| REG-093c86b066ac | regression | PASS | regression.xml#tests.test_business_email.test_company_domains_accepted[user@acme.com] |
| REG-921c26a84a84 | regression | PASS | regression.xml#tests.test_business_email.test_company_domains_accepted[user@logistics.co.uk] |
| REG-fd679bc887c4 | regression | PASS | regression.xml#tests.test_business_email.test_company_domains_accepted[user@gmail.com.acme.com] |
| REG-2a37f5c200cb | regression | PASS | regression.xml#tests.test_business_email.test_callback_cannot_create_personal_account |
| REG-96f5c6cfc2f4 | regression | PASS | regression.xml#tests.test_connector_credentials.test_encrypt_decrypt_roundtrip_dict |
| REG-f82f1961f175 | regression | PASS | regression.xml#tests.test_connector_credentials.test_legacy_encrypt_str_blob_normalizes_to_api_key |
| REG-68e560d50640 | regression | PASS | regression.xml#tests.test_connector_credentials.test_merge_credentials_preserves_existing |
| REG-02c2213b28b5 | regression | PASS | regression.xml#tests.test_connector_credentials.test_configure_source_stores_credentials_dict |
| REG-d0ebdc0deeef | regression | PASS | regression.xml#tests.test_connector_credentials.test_legacy_api_key_field_still_works |
| REG-dadae6ff0f98 | regression | PASS | regression.xml#tests.test_connector_credentials.test_cross_org_cannot_configure_connection |
| REG-f283790ed50d | inventory reconciliation | PASS | regression.xml#tests.test_core_inventory_workflow.test_inventory_health_matches_row_status_and_reorder |
| REG-e5e4d1172a45 | regression | PASS | regression.xml#tests.test_csrf.test_csrf_blocks_cross_origin_cookie_mutation |
| REG-1210e2359497 | regression | PASS | regression.xml#tests.test_csrf.test_csrf_allows_matching_origin |
| REG-6a6a6d1e4562 | regression | PASS | regression.xml#tests.test_csrf.test_csrf_skips_when_disabled |
| REG-392ad59b57ac | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_extract_email_domain |
| REG-db08aeb1c978 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_safe_return_path_blocks_open_redirects |
| REG-93d46481f621 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_discover_local_allowed_domain |
| REG-20c6e7994428 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_continue_requires_workos |
| REG-15b244f7114d | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_oauth_state_pkce_consume_once |
| REG-585bc8e5658e | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_callback_rejects_missing_or_bad_state |
| REG-799fe88b8dff | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_continue_email_first_sso_routing |
| REG-67acda31b72d | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_callback_with_pkce_creates_session |
| REG-b6ab27d7970f | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_session_idle_timeout |
| REG-c9eafd664ff4 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_authenticated_get_persists_last_seen |
| REG-1e762de84895 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_session_sliding_expiration |
| REG-f5f6d2c70757 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_list_revoke_logout_all_sessions |
| REG-10540ed9fa52 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_dev_login_hidden_outside_development |
| REG-f0899a664caa | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_invitation_preview_and_accept_flow |
| REG-0e34c4d72092 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_invitation_create_returns_share_link |
| REG-ed13d8abe548 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_security_login_history_and_settings |
| REG-14ec8ae09059 | authentication | PASS | regression.xml#tests.test_enterprise_auth.test_unauthorized_session_admin |
| REG-2369ea40d9c4 | inventory reconciliation | PASS | regression.xml#tests.test_enterprise_claims.test_missing_supplier_data_has_no_invented_average |
| REG-a6a8c1b325d6 | regression | PASS | regression.xml#tests.test_enterprise_claims.test_zero_supplier_scores_are_preserved |
| REG-e8ad68d2e42c | regression | PASS | regression.xml#tests.test_enterprise_claims.test_heuristic_confidence_is_not_exposed_as_probability |
| REG-4c4e89a33e03 | imports | SKIPPED | regression.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[between_rows], postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[between_rows] |
| REG-604b2a725ecf | imports | SKIPPED | regression.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[before_commit], postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[before_commit] |
| REG-a2a2861b5a4c | imports | SKIPPED | regression.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[after_commit], postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[after_commit] |
| REG-83a5273a3b93 | inventory reconciliation | PASS | regression.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[1.5] |
| REG-aee4f3fb2a16 | inventory reconciliation | PASS | regression.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[NaN] |
| REG-55457da7ee6f | inventory reconciliation | PASS | regression.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[Infinity] |
| REG-d7d14222208e | inventory reconciliation | PASS | regression.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[-1] |
| REG-d0bbc277bcbf | inventory reconciliation | PASS | regression.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[2147483648] |
| REG-8739dad58c56 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_product_cost[NaN] |
| REG-b80a51505578 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_product_cost[Infinity] |
| REG-1f1c1558bdd6 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_product_cost[-1] |
| REG-9256d5d5b332 | regression | PASS | regression.xml#tests.test_launch_hardening.test_malformed_csv[a,a\n1,2] |
| REG-fec7fd2dfc6a | regression | PASS | regression.xml#tests.test_launch_hardening.test_malformed_csv[a,b\n1,2,3] |
| REG-9bf526cc71ed | regression | PASS | regression.xml#tests.test_launch_hardening.test_malformed_csv[a\n\xff] |
| REG-0c9dc3a28c4e | regression | PASS | regression.xml#tests.test_launch_hardening.test_malformed_csv[a\n\x00] |
| REG-4b029fe56701 | regression | PASS | regression.xml#tests.test_launch_hardening.test_workbook_expansion_limit |
| REG-fb7197f4e196 | regression | PASS | regression.xml#tests.test_launch_hardening.test_excel_values_and_formula_rejection |
| REG-a19863ac88f7 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[[]] |
| REG-0ad9d09345f7 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[{] |
| REG-e7d80b6d6a76 | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[{"sku": 4}] |
| REG-a2217330477e | regression | PASS | regression.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[null] |
| REG-4358573c414c | imports | PASS | regression.xml#tests.test_launch_hardening.test_duplicate_import_preserves_valid_rows |
| REG-dc370a78e0b2 | regression | PASS | regression.xml#tests.test_launch_hardening.test_runtime_database_bypass_is_rejected[True-False] |
| REG-9a765a1ced07 | regression | PASS | regression.xml#tests.test_launch_hardening.test_runtime_database_bypass_is_rejected[False-True] |
| REG-bbfed1a4190c | regression | PASS | regression.xml#tests.test_launch_hardening.test_unknown_carrier_does_not_simulate_other_shipments |
| REG-48ace45b8df4 | regression | PASS | regression.xml#tests.test_launch_hardening.test_legacy_jwt_helper_round_trip_and_tamper |
| REG-de7282ccb527 | regression | PASS | regression.xml#tests.test_launch_hardening.test_enterprise_jobs_reject_unsigned_production_payloads |
| REG-e3c4e48d1737 | database integrity | PASS | regression.xml#tests.test_launch_hardening.test_provider_database_urls_use_installed_driver[postgres] |
| REG-0006a39e6bc5 | database integrity | PASS | regression.xml#tests.test_launch_hardening.test_provider_database_urls_use_installed_driver[postgresql] |
| REG-7dbb8a559505 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[https://:password@redis.example.com] |
| REG-d4eb8aa63e3e | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[redis://:password@redis.example.com] |
| REG-cd7231482959 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[rediss://user@redis.example.com] |
| REG-af4218a69324 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[redis://:password@localhost.attacker.example] |
| REG-4ad24b9930ab | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[rediss://:password@redis.example.com?ssl_cert_reqs=none] |
| REG-12f4ac44b218 | regression | PASS | regression.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[-2] |
| REG-15ea04296ec4 | regression | PASS | regression.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[-1] |
| REG-7c70f0e57230 | regression | PASS | regression.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[0] |
| REG-231b6ec3a478 | regression | PASS | regression.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[31001] |
| REG-4e99d0d2fd62 | background jobs | PASS | regression.xml#tests.test_launch_readiness.test_redis_alive_without_worker_is_not_ready |
| REG-a3b2c4fc9f27 | regression | PASS | regression.xml#tests.test_launch_readiness.test_unknown_demand_is_not_infinite_supply |
| REG-6a034f0351ca | regression | PASS | regression.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Every 15 min-900] |
| REG-66118deee003 | regression | PASS | regression.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Weekly-604800] |
| REG-7382a0978af4 | regression | PASS | regression.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Hourly-3600] |
| REG-b5a22d6094c3 | regression | PASS | regression.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Daily-86400] |
| REG-6673acefa069 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[Manual] |
| REG-af0529eaa4f1 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[Real-time] |
| REG-864b82b5542d | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[0m] |
| REG-1365a7b3dfa4 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[0h] |
| REG-9b4349d7bf11 | regression | PASS | regression.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[999999d] |
| REG-03aeb4ba648f | regression | PASS | regression.xml#tests.test_leads.test_capture_disabled |
| REG-08fe67f52a73 | regression | PASS | regression.xml#tests.test_leads.test_capture_encrypted_and_operator_only |
| REG-7594366ce111 | regression | PASS | regression.xml#tests.test_leads.test_honeypot_and_consent |
| REG-eaab30a394ec | regression | PASS | regression.xml#tests.test_leads.test_personal_email_cannot_submit_enterprise_request |
| REG-98300ea8e2c1 | regression | PASS | regression.xml#tests.test_mapped_connectors.test_salesforce_products_orders_refresh_without_duplicates |
| REG-d4048808280a | regression | PASS | regression.xml#tests.test_mapped_connectors.test_mapping_failure_rolls_back_earlier_entities |
| REG-a22225f96759 | inventory reconciliation | PASS | regression.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change0] |
| REG-6b78c64b0953 | inventory reconciliation | PASS | regression.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change1] |
| REG-2f4ef7d1891d | inventory reconciliation | PASS | regression.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change2] |
| REG-3f5c2115b002 | inventory reconciliation | PASS | regression.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change3] |
| REG-e78307a29ec0 | regression | PASS | regression.xml#tests.test_mapped_connectors.test_other_source_collision_rejected |
| REG-dabe583ccff6 | regression | PASS | regression.xml#tests.test_mapped_connectors.test_incomplete_page_is_not_success |
| REG-67480f8cb055 | regression | PASS | regression.xml#tests.test_mapped_connectors.test_mapping_rejects_query_injection_and_supplier_inference |
| REG-8b911bf8853c | regression | PASS | regression.xml#tests.test_mapped_connectors.test_salesforce_next_page_cannot_receive_token_on_other_host |
| REG-9a04bbd653e6 | authentication | PASS | regression.xml#tests.test_mapped_connectors.test_sap_http_session_pagination_and_refresh |
| REG-f397295e9a63 | database integrity | PASS | regression.xml#tests.test_mapped_connectors.test_sap_rejects_unapproved_or_cross_origin_urls |
| REG-3f41d79b7b41 | regression | PASS | regression.xml#tests.test_metrics_scoped.test_compute_kpis_scoped_to_org |
| REG-23053ced0bc8 | regression | PASS | regression.xml#tests.test_metrics_scoped.test_supplier_ranking_uses_few_queries |
| REG-9a6ca26b9f1d | regression | PASS | regression.xml#tests.test_migrations_schema.test_alembic_upgrade_empty_sqlite |
| REG-fb4e971238b0 | regression | PASS | regression.xml#tests.test_migrations_schema.test_stamp_and_upgrade_legacy_db |
| REG-4fce8b3a831e | regression | PASS | regression.xml#tests.test_orgs.test_create_org_via_api |
| REG-aa58789c4138 | regression | PASS | regression.xml#tests.test_orgs.test_invite_and_accept_token_flow |
| REG-8f827ab0e703 | regression | PASS | regression.xml#tests.test_orgs.test_dev_login_without_workos |
| REG-f20bd566a52b | regression | PASS | regression.xml#tests.test_orgs.test_billing_plans_without_stripe |
| REG-d9af64fc31b4 | regression | PASS | regression.xml#tests.test_orgs.test_stripe_checkout_fails_clearly_without_key |
| REG-c2e6564c7f06 | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_graph_neighbors_supplier |
| REG-ca9abc7cd36f | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_timeline_includes_alerts |
| REG-43842a296003 | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_search_suppliers |
| REG-9870acbd667d | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_mission_control_v2_fields |
| REG-d3f7fa421526 | critical workflow | PASS | regression.xml#tests.test_phase_b_intelligence.test_incident_lifecycle |
| REG-2765b8e3d6c7 | AI factuality | PASS | regression.xml#tests.test_phase_b_intelligence.test_ai_orchestrate |
| REG-784e8623f53d | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_observability |
| REG-124eb8312b4e | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_graph_api |
| REG-7bf58d95eb34 | regression | PASS | regression.xml#tests.test_phase_b_intelligence.test_timeline_api |
| REG-b7df073f0187 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_data_quality_assess |
| REG-d5011589783c | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_workflow_create_and_execute |
| REG-22f94bc848e7 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_predictions_generate |
| REG-70f8df3f8fd2 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_connector_studio_catalogue |
| REG-4618cd203130 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_connector_studio_detail |
| REG-0ac0c01093a7 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_workflows_api |
| REG-26b6fb2cdab6 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_data_quality_api |
| REG-1a33a224b216 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_dashboards_api |
| REG-0b94fae1e029 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_predictions_api |
| REG-567a9a4bc0f9 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_customer_success_api |
| REG-3e3bc1eb5452 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_security_center_api |
| REG-dd5c3be79177 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_platform_ops_api |
| REG-45c83c2c1369 | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_mission_control_data_health |
| REG-d7a8c2992e0a | regression | PASS | regression.xml#tests.test_phase_c_enterprise.test_documents_upload |
| REG-76c51dcacf97 | imports | PASS | regression.xml#tests.test_pilot_import_journey.test_import_to_reorder_incident_and_inventory_refresh |
| REG-0cc260b0051d | imports | PASS | regression.xml#tests.test_pilot_import_journey.test_shipment_eta_update_and_incident_progress |
| REG-05a550450019 | imports | PASS | regression.xml#tests.test_pilot_import_journey.test_repeated_product_update_preserves_unmapped_fields |
| REG-0677463c4e1f | imports | PASS | regression.xml#tests.test_pilot_import_journey.test_inventory_import_rejects_ambiguous_warehouse |
| REG-c566bf628ebe | imports | PASS | regression.xml#tests.test_pilot_import_journey.test_inventory_outcome_counts_reconcile |
| REG-012e8f06bcb1 | authorization | PASS | regression.xml#tests.test_pilot_regressions.test_network_permission_does_not_unlock_mission_context |
| REG-8c9bd403b544 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[None] |
| REG-dc96ccbdb361 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[] |
| REG-4cbcf96885ab | regression | PASS | regression.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[   ] |
| REG-08dbf16a55ba | regression | PASS | regression.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[42] |
| REG-8f26b51b777c | regression | PASS | regression.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[TimeoutError] |
| REG-919d9e981809 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[ConnectionError] |
| REG-c0dae1896c3c | regression | PASS | regression.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[ValueError] |
| REG-ca019c869b94 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[IndexError] |
| REG-70513a2384bb | regression | PASS | regression.xml#tests.test_pilot_regressions.test_error_requests_counted_and_ids_sanitized |
| REG-a88e7443e80a | regression | PASS | regression.xml#tests.test_pilot_regressions.test_request_id_length_is_bounded |
| REG-f153933fffc8 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_hardened_upload_never_acknowledges_missing_bytes |
| REG-bf0ffed31359 | database integrity | PASS | regression.xml#tests.test_pilot_regressions.test_connectors_validate_final_urls_before_sending_tokens |
| REG-1388df1bbe88 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_connector_errors_do_not_echo_provider_secrets[ups] |
| REG-b171a14e36b8 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_connector_errors_do_not_echo_provider_secrets[dynamics] |
| REG-6624c764ac99 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_sentry_removes_credentials_and_customer_payloads |
| REG-3ef962d970e9 | regression | PASS | regression.xml#tests.test_pilot_regressions.test_dynamics_follows_pages_and_rejects_cycles |
| REG-aecec70884ca | regression | PASS | regression.xml#tests.test_pilot_regressions.test_legacy_rebuild_refuses_data_before_dropping_tables |
| REG-6a43b62c2532 | AI factuality | PASS | regression.xml#tests.test_pilot_regressions.test_ai_provider_failures_are_observable |
| REG-a3cb74f9b7ca | regression | PASS | regression.xml#tests.test_platform_console.test_sanitize_error_redacts_secrets |
| REG-d6123eca4cbf | regression | PASS | regression.xml#tests.test_platform_console.test_classify_failure_kinds |
| REG-3f289d0dab01 | authentication | PASS | regression.xml#tests.test_platform_console.test_unauthenticated_admin_is_401 |
| REG-3148bdfe95ff | tenant isolation | PASS | regression.xml#tests.test_platform_console.test_tenant_owner_cannot_access_admin |
| REG-761b430a8a66 | regression | PASS | regression.xml#tests.test_platform_console.test_platform_admin_can_access_health |
| REG-482bc7302021 | tenant isolation | PASS | regression.xml#tests.test_platform_console.test_non_admin_cannot_read_other_tenant_via_admin |
| REG-6c7c4f3aad58 | tenant isolation | PASS | regression.xml#tests.test_platform_console.test_platform_admin_lists_both_tenants |
| REG-72c5b11ab935 | tenant isolation | PASS | regression.xml#tests.test_platform_console.test_platform_admin_tenant_detail_and_audit |
| REG-4b7d1f7bea42 | regression | PASS | regression.xml#tests.test_platform_console.test_api_token_cannot_use_admin_even_if_user_is_platform_admin |
| REG-1658440534a3 | regression | PASS | regression.xml#tests.test_platform_console.test_postgres_health_failure |
| REG-668773b92197 | regression | PASS | regression.xml#tests.test_platform_console.test_redis_unavailable_is_not_reported_healthy |
| REG-36afb8e579de | regression | PASS | regression.xml#tests.test_platform_console.test_connector_and_job_reporting |
| REG-6e474adf124e | regression | PASS | regression.xml#tests.test_platform_console.test_stale_connector_is_warning |
| REG-686f8d5df378 | regression | PASS | regression.xml#tests.test_platform_console.test_retry_enqueues_and_audits |
| REG-0e5fa03dd930 | regression | PASS | regression.xml#tests.test_platform_console.test_retry_wrong_org_is_404 |
| REG-c2b7604c223f | regression | PASS | regression.xml#tests.test_platform_foundation.test_parse_sync_frequency |
| REG-60bbbaa705f3 | regression | PASS | regression.xml#tests.test_platform_foundation.test_schedule_next_sets_future |
| REG-e78be2225e0e | regression | PASS | regression.xml#tests.test_platform_foundation.test_enqueue_due_connector_syncs_scans_orgs |
| REG-08590cecb41d | regression | PASS | regression.xml#tests.test_platform_foundation.test_email_skips_without_resend |
| REG-cd2b858b24f3 | regression | PASS | regression.xml#tests.test_platform_foundation.test_flags_defaults |
| REG-5bd74ada2a45 | regression | PASS | regression.xml#tests.test_platform_foundation.test_purchase_and_sales_orders_api |
| REG-34b039e4912b | authentication | PASS | regression.xml#tests.test_platform_foundation.test_orders_require_auth |
| REG-e78e66b3ce1f | database integrity | SKIPPED | regression.xml#tests.test_postgres_api_rls.test_set_local_guc_cleared_by_commit_but_restored_after_begin, postgres.xml#tests.test_postgres_api_rls.test_set_local_guc_cleared_by_commit_but_restored_after_begin |
| REG-bfe5c21cadc4 | database integrity | SKIPPED | regression.xml#tests.test_postgres_api_rls.test_api_request_path_returns_owned_shipment_ids, postgres.xml#tests.test_postgres_api_rls.test_api_request_path_returns_owned_shipment_ids |
| REG-49c48b27267d | database integrity | SKIPPED | regression.xml#tests.test_postgres_api_rls.test_api_cross_org_detail_invisible, postgres.xml#tests.test_postgres_api_rls.test_api_cross_org_detail_invisible |
| REG-d2159d50f84f | database integrity | SKIPPED | regression.xml#tests.test_postgres_api_rls.test_api_spoofed_org_header_rejected, postgres.xml#tests.test_postgres_api_rls.test_api_spoofed_org_header_rejected |
| REG-7b371e30e402 | tenant isolation | SKIPPED | regression.xml#tests.test_postgres_api_rls.test_missing_tenant_guc_sees_zero_protected_rows, postgres.xml#tests.test_postgres_api_rls.test_missing_tenant_guc_sees_zero_protected_rows |
| REG-0ce70ed0cb75 | imports | PASS | regression.xml#tests.test_priorities.test_import_detect_explain_act_resolve_and_refresh |
| REG-d01092d8f782 | tenant isolation | PASS | regression.xml#tests.test_priorities.test_unknown_or_other_tenant_priority_not_exposed |
| REG-6c1a7a92ca9a | critical workflow | PASS | regression.xml#tests.test_priorities.test_viewer_cannot_turn_priority_into_action |
| REG-009d51a161e5 | authentication | PASS | regression.xml#tests.test_private_demo_login.test_private_demo_session_and_write_denial |
| REG-8dc3dd7c7875 | regression | PASS | regression.xml#tests.test_private_demo_login.test_wrong_credentials_and_disabled |
| REG-fa73ab8601a8 | authentication | PASS | regression.xml#tests.test_private_demo_login.test_password_rotation_revokes_existing_session |
| REG-430a477bb7d5 | authentication | PASS | regression.xml#tests.test_private_demo_login.test_role_change_invalidates_demo_session |
| REG-5c0a577dd199 | regression | PASS | regression.xml#tests.test_private_demo_login.test_another_membership_blocks_login |
| REG-0844b2d1c52b | regression | PASS | regression.xml#tests.test_private_demo_login.test_demo_operator_can_act_without_administration |
| REG-4bafb65983c0 | authorization | PASS | regression.xml#tests.test_rbac.test_viewer_can_read_shipments |
| REG-11809713c9bf | authorization | PASS | regression.xml#tests.test_rbac.test_viewer_cannot_update_shipment |
| REG-fdcda9762837 | authorization | PASS | regression.xml#tests.test_rbac.test_owner_can_update_shipment |
| REG-e6a56d87e431 | regression | PASS | regression.xml#tests.test_recovery_engine.test_ready_shortage_and_reservations |
| REG-237e3edd391a | regression | PASS | regression.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change0-READY] |
| REG-b5b27f41358c | regression | PASS | regression.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change1-SHORTAGE] |
| REG-0051b7688110 | regression | PASS | regression.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change2-AT RISK] |
| REG-d032a817eaeb | regression | PASS | regression.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change3-AT RISK] |
| REG-eaacb1086640 | regression | PASS | regression.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change4-SHORTAGE] |
| REG-3c438caf83f3 | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[observed_quantity-None-UNKNOWN] |
| REG-bac4ddded469 | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[observed_quantity-99-UNKNOWN] |
| REG-5e8923349851 | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[reserved_quantity-None-UNKNOWN] |
| REG-700856a3beb8 | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[usability-unknown-UNKNOWN] |
| REG-318a5f82db2f | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[usability-quarantined-SHORTAGE] |
| REG-8b1f7c23a26f | regression | PASS | regression.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[source_updated_at-2020-01-01T00:00:00Z-AT RISK] |
| REG-d29228d864df | inventory reconciliation | PASS | regression.xml#tests.test_recovery_engine.test_inventory_and_inbound_never_double_counted |
| REG-3aeae8504d95 | regression | PASS | regression.xml#tests.test_recovery_engine.test_duplicate_po_line_not_counted |
| REG-f39c8ebbe0bb | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_vs_zero[None-UNKNOWN] |
| REG-9c0fa4185fb4 | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_vs_zero[0-READY] |
| REG-518dd4179e7f | regression | PASS | regression.xml#tests.test_recovery_engine.test_unknown_part_and_duplicate_stock |
| REG-851226ecad6b | regression | PASS | regression.xml#tests.test_recovery_engine.test_transfer_preserves_donor_and_is_nonmutating |
| REG-c201b2c92bdf | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change0] |
| REG-3cd4deee2a1a | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change1] |
| REG-c08e746995f4 | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change2] |
| REG-8e7080dc886f | regression | PASS | regression.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change3] |
| REG-9928347c3195 | authentication | PASS | regression.xml#tests.test_recovery_engine.test_substitute_requires_authorization_and_suitable_stock |
| REG-f3ef44270138 | regression | PASS | regression.xml#tests.test_recovery_engine.test_repair_timing_and_unknown_cost |
| REG-7f9a492621de | critical workflow | PASS | regression.xml#tests.test_recovery_engine.test_end_to_end_propose_approve_outcome_incident_and_audit |
| REG-4997975e702c | imports | PASS | regression.xml#tests.test_recovery_engine.test_import_retry_conflict_rollback_and_correction |
| REG-2b4203a78c7c | tenant isolation | PASS | regression.xml#tests.test_recovery_engine.test_recovery_permissions_tenant_isolation_and_copilot |
| REG-75d20d4dd3fb | regression | PASS | regression.xml#tests.test_recovery_engine.test_empty_copilot_abstains |
| REG-9a49521b3d22 | regression | PASS | regression.xml#tests.test_recovery_engine.test_overdue_unreceived_supply_is_not_guaranteed |
| REG-d2577d2450bd | regression | PASS | regression.xml#tests.test_recovery_engine.test_approved_alias_only_and_ambiguous_alias_abstention |
| REG-dbf369076b8b | regression | PASS | regression.xml#tests.test_recovery_engine.test_donor_preview_shows_created_shortage_and_missing_currency |
| REG-ee74e51b0281 | imports | PASS | regression.xml#tests.test_recovery_engine.test_import_invalid_row_rolls_back_entire_file |
| REG-8058354ab0bf | regression | PASS | regression.xml#tests.test_recovery_engine.test_source_change_blocks_stale_approval |
| REG-58da18168616 | regression | PASS | regression.xml#tests.test_recovery_engine.test_valid_case_denied_to_viewer_and_foreign_organization |
| REG-fb496b8f6285 | database integrity | SKIPPED | regression.xml#tests.test_recovery_engine.test_postgres_recovery_records_enforce_rls, postgres.xml#tests.test_recovery_engine.test_postgres_recovery_records_enforce_rls |
| REG-ebd8253b53a9 | regression | PASS | regression.xml#tests.test_recovery_engine.test_approval_rechecks_elapsed_evidence_without_source_edit |
| REG-411635c9e5a7 | inventory reconciliation | PASS | regression.xml#tests.test_recovery_engine.test_competing_proposals_revalidate_and_approval_has_no_inventory_effect |
| REG-22570b8ce652 | regression | PASS | regression.xml#tests.test_recovery_engine.test_recovery_source_instructions_cannot_replace_grounded_answer |
| REG-f411c2d9000a | database integrity | SKIPPED | regression.xml#tests.test_recovery_engine.test_postgres_recovery_cases_enforce_rls, postgres.xml#tests.test_recovery_engine.test_postgres_recovery_cases_enforce_rls |
| REG-09acfa6674df | database integrity | SKIPPED | regression.xml#tests.test_rls.test_rls_policies_exist, postgres.xml#tests.test_rls.test_rls_policies_exist |
| REG-fef269a90641 | database integrity | SKIPPED | regression.xml#tests.test_rls.test_rls_blocks_without_guc, postgres.xml#tests.test_rls.test_rls_blocks_without_guc |
| REG-6ab1c619c978 | database integrity | SKIPPED | regression.xml#tests.test_rls.test_app_role_does_not_bypass_rls, postgres.xml#tests.test_rls.test_app_role_does_not_bypass_rls |
| REG-974bbcd7d334 | background jobs | PASS | regression.xml#tests.test_salesforce_arq_redis.test_enqueue_and_arq_worker_processes_salesforce_sync |
| REG-9bd930d1bb1d | regression | PASS | regression.xml#tests.test_salesforce_sync.test_successful_connection_and_sync |
| REG-21c6854a232a | regression | PASS | regression.xml#tests.test_salesforce_sync.test_invalid_credentials_are_permanent |
| REG-6d86545c79d8 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_empty_dataset_succeeds |
| REG-f7e409c880df | regression | PASS | regression.xml#tests.test_salesforce_sync.test_pagination_fetches_every_page |
| REG-282d24ba33a7 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_large_dataset_multiple_pages |
| REG-d58c6738cab9 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_duplicate_sync_is_idempotent |
| REG-5f26935895a7 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_page_two_failure_does_not_report_success_or_advance_cursor |
| REG-ed3a50f635ca | regression | PASS | regression.xml#tests.test_salesforce_sync.test_incomplete_pagination_cap_is_not_success |
| REG-c4537962c0e3 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_incremental_cursor_filters_subsequent_query |
| REG-aba1145016ee | regression | PASS | regression.xml#tests.test_salesforce_sync.test_transient_429_retries_then_succeeds |
| REG-ebb64fe13f1d | regression | PASS | regression.xml#tests.test_salesforce_sync.test_timeout_is_retryable |
| REG-4eb9de47e58e | regression | PASS | regression.xml#tests.test_salesforce_sync.test_connection_failure_is_retryable |
| REG-d04462718262 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_http_500_is_retryable |
| REG-c2e83bb8a446 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_malformed_response_is_permanent |
| REG-19597b8f67bf | background jobs | PASS | regression.xml#tests.test_salesforce_sync.test_arq_permanent_failure_does_not_raise_retry |
| REG-e5bebe617901 | background jobs | PASS | regression.xml#tests.test_salesforce_sync.test_arq_transient_failure_raises_retry |
| REG-775c0b6cf188 | background jobs | PASS | regression.xml#tests.test_salesforce_sync.test_arq_max_tries_marks_failed |
| REG-964a727cee74 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_queued_job_created_on_enqueue |
| REG-74016ba97cc7 | background jobs | PASS | regression.xml#tests.test_salesforce_sync.test_worker_restart_recovers_stale_syncing |
| REG-c73541556529 | tenant isolation | PASS | regression.xml#tests.test_salesforce_sync.test_cross_tenant_sync_isolation |
| REG-f2be20f63cb3 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_credentials_never_in_api_response |
| REG-8d525e3065f0 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_disconnect_clears_credentials |
| REG-9361aba9ecee | regression | PASS | regression.xml#tests.test_salesforce_sync.test_delete_wipes_credentials_then_removes_row |
| REG-c7de5740839e | regression | PASS | regression.xml#tests.test_salesforce_sync.test_credentials_not_written_to_logs |
| REG-ac9894b36768 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_configured_without_sync_is_not_healthy |
| REG-e78fba0a519f | regression | PASS | regression.xml#tests.test_salesforce_sync.test_non_admin_cannot_trigger_admin_retry |
| REG-61c46689e737 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_test_connection_sanitizes_error |
| REG-bdc26fbe987f | tenant isolation | SKIPPED | regression.xml#tests.test_salesforce_sync.test_postgres_worker_session_cannot_see_other_tenant_suppliers, postgres.xml#tests.test_salesforce_sync.test_postgres_worker_session_cannot_see_other_tenant_suppliers |
| REG-9d7c4cbf0892 | regression | PASS | regression.xml#tests.test_salesforce_sync.test_create_queued_job_reuses_open_job |
| REG-b07579745d7f | tenant isolation | PASS | regression.xml#tests.test_security_attack_matrix.test_A_cross_tenant_shipment_uuid |
| REG-e1f6937dd7b3 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_B_spoofed_x_organization_id |
| REG-3bc4d3169b5c | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_H_viewer_cannot_create_simulation |
| REG-773488a63ab6 | authentication | PASS | regression.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://127.0.0.1/oauth] |
| REG-960b66ca149e | authentication | PASS | regression.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://localhost/oauth] |
| REG-253f88cae7f8 | authentication | PASS | regression.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://10.0.0.5/oauth] |
| REG-ada66eba4949 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://169.254.169.254/latest/meta-data] |
| REG-6e216a1fad85 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://metadata.google.internal/] |
| REG-e7a6aca294ad | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_L_executable_extension_rejected |
| REG-ca1bcd8761a8 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_M_oversized_upload_rejected |
| REG-78ac84a64ef4 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_document_extension_allowlist |
| REG-2daa76f94b84 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_stripe_metadata_cannot_override_customer_index |
| REG-a8116522f8d8 | authentication | PASS | regression.xml#tests.test_security_attack_matrix.test_P_ai_prompt_injection_does_not_bypass_auth |
| REG-78970e615225 | authentication | PASS | regression.xml#tests.test_security_attack_matrix.test_S_unauthenticated_sensitive_api |
| REG-a71149bde482 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_T_production_dev_login_blocked |
| REG-15b425e699a8 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_job_signature_rejects_tamper |
| REG-3559810c12c5 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_V_cors_star_rejected_in_production |
| REG-9ca89b5b5ccb | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_W_csrf_blocks_untrusted_origin |
| REG-fe5621aa4e85 | regression | PASS | regression.xml#tests.test_security_attack_matrix.test_document_upload_rejects_exe |
| REG-15bb0581e533 | regression | PASS | regression.xml#tests.test_security_hardening.test_cannot_invite_owner_via_any_role |
| REG-8998b7c18ebb | regression | PASS | regression.xml#tests.test_security_hardening.test_operations_director_cannot_invite_admin |
| REG-4afde28043cf | regression | PASS | regression.xml#tests.test_security_hardening.test_invite_owner_role_rejected_by_api |
| REG-3a9ff4451477 | regression | PASS | regression.xml#tests.test_security_hardening.test_outbound_url_rejects_metadata_and_http |
| REG-20442b11bf45 | regression | PASS | regression.xml#tests.test_security_hardening.test_slack_url_requires_known_host |
| REG-a3613a41f16f | regression | PASS | regression.xml#tests.test_security_hardening.test_config_rejects_plaintext_secrets |
| REG-23a92d6e7b9d | regression | PASS | regression.xml#tests.test_security_hardening.test_webhook_rejects_private_url |
| REG-5d94be6bd8cd | regression | PASS | regression.xml#tests.test_ssrf.test_allows_salesforce_login |
| REG-d5707e13e2f8 | regression | PASS | regression.xml#tests.test_ssrf.test_allows_salesforce_instance |
| REG-6c9521ebc2af | regression | PASS | regression.xml#tests.test_ssrf.test_rejects_private_ip |
| REG-ad38cccce8d9 | regression | PASS | regression.xml#tests.test_ssrf.test_rejects_http |
| REG-c12ecef82dd2 | regression | PASS | regression.xml#tests.test_ssrf.test_rejects_arbitrary_host |
| REG-4166b8899adb | regression | PASS | regression.xml#tests.test_ssrf.test_rejects_metadata_ip |
| REG-d541b2b798d9 | regression | PASS | regression.xml#tests.test_ssrf.test_configure_rejects_evil_base_url |
| REG-05307a2aec46 | database integrity | PASS | regression.xml#tests.test_ssrf.test_validate_config_urls_ok |
| REG-cf86c3a15108 | regression | PASS | regression.xml#tests.test_startup_checks.test_development_allows_default_secrets |
| REG-501a6348fd87 | authentication | PASS | regression.xml#tests.test_startup_checks.test_production_rejects_default_session_secret |
| REG-5c869c07b93e | regression | PASS | regression.xml#tests.test_startup_checks.test_production_rejects_missing_encryption_key |
| REG-6236ad123b3c | regression | PASS | regression.xml#tests.test_startup_checks.test_production_happy_path |
| REG-930d375e1098 | regression | PASS | regression.xml#tests.test_startup_checks.test_staging_requires_metrics_token |
| REG-fbc2860e5481 | regression | PASS | regression.xml#tests.test_startup_checks.test_staging_happy_path |
| REG-16d8dceb03aa | regression | PASS | regression.xml#tests.test_startup_checks.test_staging_rejects_inline_sync |
| REG-056aad599493 | regression | PASS | regression.xml#tests.test_startup_checks.test_production_requires_billing_enforce |
| REG-2c1e2e62f0bc | regression | PASS | regression.xml#tests.test_startup_checks.test_unknown_environment_fail_closed |
| REG-d3b93f3bb48d | regression | PASS | regression.xml#tests.test_startup_checks.test_staging_requires_csrf |
| REG-fb0635d82c4f | authentication | PASS | regression.xml#tests.test_startup_checks.test_production_rejects_unauthenticated_redis |
| REG-20d99ed640af | authentication | PASS | regression.xml#tests.test_startup_checks.test_staging_allows_local_redis_without_auth |
| REG-bbaef388f169 | background jobs | PASS | regression.xml#tests.test_startup_checks.test_worker_role_skips_workos |
| REG-ac61375bf63f | database integrity | PASS | regression.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[FRONTEND_URL-http://app.example.com] |
| REG-e4ddc0fbf2bc | database integrity | PASS | regression.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[WORKOS_REDIRECT_URI-http://api.example.com/callback] |
| REG-c57efbc25c0d | database integrity | PASS | regression.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[FRONTEND_URL-https://user:password@app.example.com] |
| REG-1af11b2e862a | database integrity | PASS | regression.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[CORS_ORIGINS-value3] |
| REG-2bcfd04d5b81 | database integrity | PASS | regression.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[DATABASE_URL-sqlite:///production.db] |
| REG-83c7ec3410cc | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_app_role_cannot_disable_row_security, postgres.xml#tests.test_stripe_force_rls.test_app_role_cannot_disable_row_security |
| REG-338055d96814 | tenant isolation | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_lookup_function_works_without_tenant_guc, postgres.xml#tests.test_stripe_force_rls.test_lookup_function_works_without_tenant_guc |
| REG-eb761fd85465 | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_invoice_paid_entitlement_update_without_guc, postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_entitlement_update_without_guc |
| REG-10fdc898d63c | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_invoice_paid_duplicate_is_idempotent, postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_duplicate_is_idempotent |
| REG-3853ef75f745 | tenant isolation | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_invoice_paid_unknown_customer_no_tenant_mutation, postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_unknown_customer_no_tenant_mutation |
| REG-0bf3270ad86b | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_checkout_then_invoice_paid_full_path, postgres.xml#tests.test_stripe_force_rls.test_checkout_then_invoice_paid_full_path |
| REG-ba9f873ccd73 | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_subscription_update_via_customer_lookup, postgres.xml#tests.test_stripe_force_rls.test_subscription_update_via_customer_lookup |
| REG-007d42a331d6 | database integrity | SKIPPED | regression.xml#tests.test_stripe_force_rls.test_webhook_signature_verification, postgres.xml#tests.test_stripe_force_rls.test_webhook_signature_verification |
| REG-c16a07e6ee4e | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_checkout_webhook_sets_billing_and_is_idempotent |
| REG-a226d5594d8f | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_invoice_paid_credit_reset_idempotent |
| REG-9256dd68b09e | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_invoice_paid_resolves_org_via_customer_id |
| REG-dea469a305c2 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_checkout_metadata_does_not_activate_unpaid_subscription |
| REG-80c21b480564 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_checkout_customer_mapping_overrides_conflicting_metadata |
| REG-b445ffe7d187 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_manual_invoice_cannot_reactivate_subscription |
| REG-6f62310b7f82 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_delayed_and_duplicate_invoice_cannot_reset_current_usage |
| REG-4be0cd1d4635 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_checkout_verification_failure_is_retryable |
| REG-9137a6f1bcbc | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_stale_subscription_event_uses_current_provider_status |
| REG-acbeb7114658 | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_verified_checkout_activates_paid_plan |
| REG-9aa1876c967b | regression | PASS | regression.xml#tests.test_stripe_webhooks.test_checkout_rejects_subscription_from_another_customer |
| REG-4a2699105b79 | regression | PASS | regression.xml#tests.test_subscription_access.test_expired_trial_blocks_operations_but_allows_billing |
| REG-ca0463f2a595 | regression | PASS | regression.xml#tests.test_subscription_access.test_active_subscription_and_failed_payment |
| REG-a0f6d671e6e7 | AI factuality | SKIPPED | regression.xml#tests.test_subscription_access.test_concurrent_ai_quota_is_serialized, postgres.xml#tests.test_subscription_access.test_concurrent_ai_quota_is_serialized |
| REG-20ab339806f3 | regression | PASS | regression.xml#tests.test_subscription_access.test_trial_cannot_create_paid_api_tokens |
| REG-71189bcca43a | regression | PASS | regression.xml#tests.test_sync_enqueue.test_sync_enqueues_when_not_inline |
| REG-553c202d4f07 | tenant isolation | PASS | regression.xml#tests.test_tenant_isolation.test_org_a_sees_only_own_shipments |
| REG-53014862a0c0 | tenant isolation | PASS | regression.xml#tests.test_tenant_isolation.test_org_b_cannot_fetch_org_a_shipment |
| REG-fd62bf8bd923 | tenant isolation | PASS | regression.xml#tests.test_tenant_isolation.test_org_b_list_excludes_org_a |
| REG-d347000988aa | tenant isolation | PASS | regression.xml#tests.test_tenant_isolation.test_spoofed_org_header_cannot_access_other_tenant |
| REG-96592a3a061f | tenant isolation | PASS | regression.xml#tests.test_tenant_isolation.test_cross_org_suppliers_and_alerts_isolated |
| REG-f905a17fec74 | regression | PASS | regression.xml#tests.test_vercel_configuration.test_marketplace_prefers_pooled_database |
| REG-8da3b4cc9016 | regression | PASS | regression.xml#tests.test_vercel_configuration.test_explicit_runtime_database_takes_precedence |
| REG-de8881bc03d0 | background jobs | SKIPPED | regression.xml#tests.test_worker_process_recovery.test_worker_kill_redis_restore_duplicate_and_restart, postgres.xml#tests.test_worker_process_recovery.test_worker_kill_redis_restore_duplicate_and_restart |
| REG-0230202d0446 | background jobs | SKIPPED | regression.xml#tests.test_worker_process_recovery.test_worker_bounded_retries_report_terminal_failure, postgres.xml#tests.test_worker_process_recovery.test_worker_bounded_retries_report_terminal_failure |
| REG-62c280c07fd9 | background jobs | SKIPPED | regression.xml#tests.test_worker_process_recovery.test_worker_database_connection_loss_recovers, postgres.xml#tests.test_worker_process_recovery.test_worker_database_connection_loss_recovers |
| REG-8e9f308c7284 | authorization | PASS | regression.xml#tests.test_workflows_e2e.test_workflow_invite_accept_permissions |
| REG-cd722384ed45 | imports | PASS | regression.xml#tests.test_workflows_e2e.test_workflow_csv_import_audit |
| REG-5d40166c5649 | regression | PASS | regression.xml#tests.test_workflows_e2e.test_workflow_api_token_rotate_and_org_binding |
| REG-8cce98900d5a | tenant isolation | PASS | regression.xml#tests.test_workflows_e2e.test_workflow_tenant_isolation |
| REG-f3dcef2e1965 | authentication | PASS | regression.xml#tests.test_workflows_e2e.test_workflow_logout_revokes_session |
| REG-dee9dde2cbc9 | authentication | PASS | regression.xml#tests.test_workos_sdk_contract.test_authorization_url_includes_pkce_method |
| REG-8ba265677e8b | authentication | PASS | regression.xml#tests.test_workos_sdk_contract.test_authentication_matches_installed_sdk_signature |
| REG-23924d824849 | regression | PASS | regression.xml#tests.test_yc_demo.test_requires_existing_verified_login |
| REG-114f29d0c4a3 | AI factuality | PASS | regression.xml#tests.test_yc_demo.test_demo_reconciles_and_ai_uses_actual_positions |
| REG-c1d4d7156999 | tenant isolation | PASS | regression.xml#tests.test_yc_demo.test_reset_requires_exact_allowlist_and_preserves_other_tenant |
| REG-30c60229c795 | imports | PASS | regression.xml#tests.test_yc_demo.test_demo_workbook_parses_through_real_importer |
| REG-ad1deeac9adc | regression | PASS | regression.xml#tests.test_yc_demo.test_demo_viewer_cannot_reset |
| REG-1cbd92336c4f | AI factuality | PASS | regression.xml#tests.test_yc_demo.test_demo_ai_does_not_include_other_company |
| PG-REG-316e39317a76 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_outside_summary_limit[chat] |
| PG-REG-728a245b2da8 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_outside_summary_limit[orchestrate] |
| PG-REG-3fb02f28f304 | inventory reconciliation | PASS | postgres.xml#tests.test_advisor_factual_requests.test_broad_inventory_summary_remains_bounded |
| PG-REG-3a4bf4e7a55c | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_without_evidence_abstains[chat] |
| PG-REG-e61da2305d0e | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_without_evidence_abstains[orchestrate] |
| PG-REG-4a7df534702a | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_with_evidence_identifies_record[chat] |
| PG-REG-318d8068dc21 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_with_evidence_identifies_record[orchestrate] |
| PG-REG-ffa1d1481500 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_healthy_sku_uses_zero_replenishment |
| PG-REG-7e49ef332854 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_without_current_position_does_not_substitute_other_stock |
| PG-REG-ee19e7496f85 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_sku_matching_is_whole_identifier |
| PG-REG-fbfec7902863 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_specific_facts_do_not_depend_on_external_provider[chat] |
| PG-REG-d2da65819423 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_specific_facts_do_not_depend_on_external_provider[orchestrate] |
| PG-REG-681785ce5324 | tenant isolation | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_matching_only_other_tenant_still_abstains[chat] |
| PG-REG-67867c0e741b | tenant isolation | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_matching_only_other_tenant_still_abstains[orchestrate] |
| PG-REG-eb9725754f03 | tenant isolation | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_never_retrieves_same_sku_from_other_tenant |
| PG-REG-2c71665d8116 | authorization | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_requires_both_read_permissions[shipments.read] |
| PG-REG-acdd9eebac25 | authorization | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_requires_both_read_permissions[suppliers.read] |
| PG-REG-e759b1abd2da | authorization | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_does_not_bypass_inventory_permissions[inventory.read] |
| PG-REG-714739128187 | authorization | PASS | postgres.xml#tests.test_advisor_factual_requests.test_explicit_sku_does_not_bypass_inventory_permissions[warehouses.read] |
| PG-REG-150dc190a1a0 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[quantity] |
| PG-REG-4b123e077696 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[date] |
| PG-REG-02a9d2ba555d | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[status] |
| PG-REG-e09a24a70ac6 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_eta_and_unrelated_deliveries_are_not_evidence[timestamp] |
| PG-REG-e6c15b4d915f | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_delivery_utc_day_boundaries |
| PG-REG-6a805563e5fc | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered at least 10,000 units yesterday?] |
| PG-REG-0f598bc503a6 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10,000 units yesterday in Tokyo?] |
| PG-REG-c0844ca6a736 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10,000 units on 2026-02-30?] |
| PG-REG-cd781ececded | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Did Acme deliver 10,000 units yesterday?] |
| PG-REG-a46299416c76 | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_unsupported_delivery_constraints_request_clarification[Which supplier delivered exactly 10.5 units yesterday?] |
| PG-REG-efd38c6ab31c | regression | PASS | postgres.xml#tests.test_advisor_factual_requests.test_supplier_summary_still_answers_summary_question |
| PG-REG-03b9bb88e0ce | AI factuality | PASS | postgres.xml#tests.test_ai_providers.test_get_ai_provider_defaults_to_local |
| PG-REG-0d8d87fb255f | AI factuality | PASS | postgres.xml#tests.test_ai_providers.test_local_engine_grounds_in_context |
| PG-REG-b4a311a2224c | inventory reconciliation | PASS | postgres.xml#tests.test_ai_providers.test_simulation_prompt_does_not_invent_numbers |
| PG-REG-b32cb993c428 | AI factuality | PASS | postgres.xml#tests.test_ai_providers.test_provider_has_bounded_timeout_output_and_no_retries |
| PG-REG-754a1be0a724 | AI factuality | PASS | postgres.xml#tests.test_ai_providers.test_provider_context_limit_prevents_request |
| PG-REG-36260049e3da | AI factuality | PASS | postgres.xml#tests.test_ai_providers.test_orchestration_uses_retrieved_context_without_fake_confidence |
| PG-REG-00ea226de827 | regression | PASS | postgres.xml#tests.test_api_tokens.test_api_token_can_call_api |
| PG-REG-72f4d39b6688 | regression | PASS | postgres.xml#tests.test_api_tokens.test_revoked_api_token_rejected |
| PG-REG-a78e48fa7805 | regression | PASS | postgres.xml#tests.test_api_tokens.test_orphaned_token_creator_rejected |
| PG-REG-489e4f13211e | authentication | PASS | postgres.xml#tests.test_auth_guards.test_unauthenticated_domain_apis_return_401 |
| PG-REG-23791741ba91 | authentication | PASS | postgres.xml#tests.test_auth_guards.test_invalid_org_header_returns_400 |
| PG-REG-24be3db16040 | authentication | PASS | postgres.xml#tests.test_auth_guards.test_non_member_org_header_returns_403 |
| PG-REG-8c47df5f0f5e | authentication | PASS | postgres.xml#tests.test_auth_guards.test_logout_revokes_session |
| PG-REG-6d461858a89e | tenant isolation | PASS | postgres.xml#tests.test_auth_guards.test_cross_org_alert_and_connection_isolation |
| PG-REG-22fb87b4b4ba | authentication | PASS | postgres.xml#tests.test_auth_guards.test_invite_accept_http_flow |
| PG-REG-0b285ffb400d | authentication | PASS | postgres.xml#tests.test_auth_guards.test_cannot_escalate_to_owner_via_patch |
| PG-REG-45d1d61d2708 | authentication | PASS | postgres.xml#tests.test_auth_guards.test_auth_rate_limit_triggers |
| PG-REG-cd176d174916 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_plans_remain_public |
| PG-REG-58b2e2b2e9ca | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/usage/{org_id}] |
| PG-REG-c199261eae6b | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/account/{org_id}] |
| PG-REG-e04c73775f8e | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/checkout/{org_id}] |
| PG-REG-33a6acab78f2 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/portal/{org_id}] |
| PG-REG-82361e4cf743 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[post-/api/v1/billing/cancel/{org_id}] |
| PG-REG-0a6c63ad8af2 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/usage] |
| PG-REG-0d25f7de3f84 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_billing_requires_authentication[get-/api/v1/billing/account] |
| PG-REG-9c4d383d7b2a | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/usage/{org_id}] |
| PG-REG-693ae60c3c62 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/account/{org_id}] |
| PG-REG-cad0373e0942 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/checkout/{org_id}] |
| PG-REG-67ea0ca0e40d | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/portal/{org_id}] |
| PG-REG-ea53d348bfb7 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[post-/api/v1/billing/cancel/{org_id}] |
| PG-REG-f2981b2e8e59 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/usage] |
| PG-REG-c9182e634a72 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_viewer_cannot_manage_billing[get-/api/v1/billing/account] |
| PG-REG-e287870d9696 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_cross_org_billing_path_denied |
| PG-REG-dcc1060556b8 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_spoofed_org_header_denied |
| PG-REG-aed893c8fdf1 | authentication | PASS | postgres.xml#tests.test_billing_authz.test_owner_can_read_own_billing_account |
| PG-REG-e27b3afa20e7 | database integrity | PASS | postgres.xml#tests.test_billing_authz.test_open_redirect_urls_rejected |
| PG-REG-382f8d75b896 | regression | PASS | postgres.xml#tests.test_business_email.test_personal_domains_rejected[user@gmail.com] |
| PG-REG-cb7b9cadbc96 | regression | PASS | postgres.xml#tests.test_business_email.test_personal_domains_rejected[user@GMAIL.COM] |
| PG-REG-79f8d54cb48a | regression | PASS | postgres.xml#tests.test_business_email.test_personal_domains_rejected[user@outlook.com] |
| PG-REG-a36c2b106292 | regression | PASS | postgres.xml#tests.test_business_email.test_personal_domains_rejected[user@sub.mailinator.com] |
| PG-REG-297a8fc29107 | regression | PASS | postgres.xml#tests.test_business_email.test_personal_domains_rejected[user@proton.me] |
| PG-REG-093c86b066ac | regression | PASS | postgres.xml#tests.test_business_email.test_company_domains_accepted[user@acme.com] |
| PG-REG-921c26a84a84 | regression | PASS | postgres.xml#tests.test_business_email.test_company_domains_accepted[user@logistics.co.uk] |
| PG-REG-fd679bc887c4 | regression | PASS | postgres.xml#tests.test_business_email.test_company_domains_accepted[user@gmail.com.acme.com] |
| PG-REG-2a37f5c200cb | regression | PASS | postgres.xml#tests.test_business_email.test_callback_cannot_create_personal_account |
| PG-REG-96f5c6cfc2f4 | regression | PASS | postgres.xml#tests.test_connector_credentials.test_encrypt_decrypt_roundtrip_dict |
| PG-REG-f82f1961f175 | regression | PASS | postgres.xml#tests.test_connector_credentials.test_legacy_encrypt_str_blob_normalizes_to_api_key |
| PG-REG-68e560d50640 | regression | PASS | postgres.xml#tests.test_connector_credentials.test_merge_credentials_preserves_existing |
| PG-REG-02c2213b28b5 | regression | PASS | postgres.xml#tests.test_connector_credentials.test_configure_source_stores_credentials_dict |
| PG-REG-d0ebdc0deeef | regression | PASS | postgres.xml#tests.test_connector_credentials.test_legacy_api_key_field_still_works |
| PG-REG-dadae6ff0f98 | regression | PASS | postgres.xml#tests.test_connector_credentials.test_cross_org_cannot_configure_connection |
| PG-REG-f283790ed50d | inventory reconciliation | PASS | postgres.xml#tests.test_core_inventory_workflow.test_inventory_health_matches_row_status_and_reorder |
| PG-REG-e5e4d1172a45 | regression | PASS | postgres.xml#tests.test_csrf.test_csrf_blocks_cross_origin_cookie_mutation |
| PG-REG-1210e2359497 | regression | PASS | postgres.xml#tests.test_csrf.test_csrf_allows_matching_origin |
| PG-REG-6a6a6d1e4562 | regression | PASS | postgres.xml#tests.test_csrf.test_csrf_skips_when_disabled |
| PG-REG-392ad59b57ac | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_extract_email_domain |
| PG-REG-db08aeb1c978 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_safe_return_path_blocks_open_redirects |
| PG-REG-93d46481f621 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_discover_local_allowed_domain |
| PG-REG-20c6e7994428 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_continue_requires_workos |
| PG-REG-15b244f7114d | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_oauth_state_pkce_consume_once |
| PG-REG-585bc8e5658e | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_callback_rejects_missing_or_bad_state |
| PG-REG-799fe88b8dff | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_continue_email_first_sso_routing |
| PG-REG-67acda31b72d | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_callback_with_pkce_creates_session |
| PG-REG-b6ab27d7970f | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_session_idle_timeout |
| PG-REG-c9eafd664ff4 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_authenticated_get_persists_last_seen |
| PG-REG-1e762de84895 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_session_sliding_expiration |
| PG-REG-f5f6d2c70757 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_list_revoke_logout_all_sessions |
| PG-REG-10540ed9fa52 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_dev_login_hidden_outside_development |
| PG-REG-f0899a664caa | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_invitation_preview_and_accept_flow |
| PG-REG-0e34c4d72092 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_invitation_create_returns_share_link |
| PG-REG-ed13d8abe548 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_security_login_history_and_settings |
| PG-REG-14ec8ae09059 | authentication | PASS | postgres.xml#tests.test_enterprise_auth.test_unauthorized_session_admin |
| PG-REG-2369ea40d9c4 | inventory reconciliation | PASS | postgres.xml#tests.test_enterprise_claims.test_missing_supplier_data_has_no_invented_average |
| PG-REG-a6a8c1b325d6 | regression | PASS | postgres.xml#tests.test_enterprise_claims.test_zero_supplier_scores_are_preserved |
| PG-REG-e8ad68d2e42c | regression | PASS | postgres.xml#tests.test_enterprise_claims.test_heuristic_confidence_is_not_exposed_as_probability |
| PG-REG-4c4e89a33e03 | imports | PASS | postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[between_rows] |
| PG-REG-604b2a725ecf | imports | PASS | postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[before_commit] |
| PG-REG-a2a2861b5a4c | imports | PASS | postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[after_commit] |
| PG-REG-83a5273a3b93 | inventory reconciliation | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[1.5] |
| PG-REG-aee4f3fb2a16 | inventory reconciliation | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[NaN] |
| PG-REG-55457da7ee6f | inventory reconciliation | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[Infinity] |
| PG-REG-d7d14222208e | inventory reconciliation | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[-1] |
| PG-REG-d0bbc277bcbf | inventory reconciliation | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_inventory_quantities[2147483648] |
| PG-REG-8739dad58c56 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_product_cost[NaN] |
| PG-REG-b80a51505578 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_product_cost[Infinity] |
| PG-REG-1f1c1558bdd6 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_product_cost[-1] |
| PG-REG-9256d5d5b332 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_malformed_csv[a,a\n1,2] |
| PG-REG-fec7fd2dfc6a | regression | PASS | postgres.xml#tests.test_launch_hardening.test_malformed_csv[a,b\n1,2,3] |
| PG-REG-9bf526cc71ed | regression | PASS | postgres.xml#tests.test_launch_hardening.test_malformed_csv[a\n\xff] |
| PG-REG-0c9dc3a28c4e | regression | PASS | postgres.xml#tests.test_launch_hardening.test_malformed_csv[a\n\x00] |
| PG-REG-4b029fe56701 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_workbook_expansion_limit |
| PG-REG-fb7197f4e196 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_excel_values_and_formula_rejection |
| PG-REG-a19863ac88f7 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[[]] |
| PG-REG-0ad9d09345f7 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[{] |
| PG-REG-e7d80b6d6a76 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[{"sku": 4}] |
| PG-REG-a2217330477e | regression | PASS | postgres.xml#tests.test_launch_hardening.test_invalid_mapping_is_client_error[null] |
| PG-REG-4358573c414c | imports | PASS | postgres.xml#tests.test_launch_hardening.test_duplicate_import_preserves_valid_rows |
| PG-REG-dc370a78e0b2 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_runtime_database_bypass_is_rejected[True-False] |
| PG-REG-9a765a1ced07 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_runtime_database_bypass_is_rejected[False-True] |
| PG-REG-bbfed1a4190c | regression | PASS | postgres.xml#tests.test_launch_hardening.test_unknown_carrier_does_not_simulate_other_shipments |
| PG-REG-48ace45b8df4 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_legacy_jwt_helper_round_trip_and_tamper |
| PG-REG-de7282ccb527 | regression | PASS | postgres.xml#tests.test_launch_hardening.test_enterprise_jobs_reject_unsigned_production_payloads |
| PG-REG-e3c4e48d1737 | database integrity | PASS | postgres.xml#tests.test_launch_hardening.test_provider_database_urls_use_installed_driver[postgres] |
| PG-REG-0006a39e6bc5 | database integrity | PASS | postgres.xml#tests.test_launch_hardening.test_provider_database_urls_use_installed_driver[postgresql] |
| PG-REG-7dbb8a559505 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[https://:password@redis.example.com] |
| PG-REG-d4eb8aa63e3e | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[redis://:password@redis.example.com] |
| PG-REG-cd7231482959 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[rediss://user@redis.example.com] |
| PG-REG-af4218a69324 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[redis://:password@localhost.attacker.example] |
| PG-REG-4ad24b9930ab | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_insecure_redis_config_rejected[rediss://:password@redis.example.com?ssl_cert_reqs=none] |
| PG-REG-12f4ac44b218 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[-2] |
| PG-REG-15ea04296ec4 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[-1] |
| PG-REG-7c70f0e57230 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[0] |
| PG-REG-231b6ec3a478 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_stale_or_permanent_heartbeat_not_ready[31001] |
| PG-REG-4e99d0d2fd62 | background jobs | PASS | postgres.xml#tests.test_launch_readiness.test_redis_alive_without_worker_is_not_ready |
| PG-REG-a3b2c4fc9f27 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_unknown_demand_is_not_infinite_supply |
| PG-REG-6a034f0351ca | regression | PASS | postgres.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Every 15 min-900] |
| PG-REG-66118deee003 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Weekly-604800] |
| PG-REG-7382a0978af4 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Hourly-3600] |
| PG-REG-b5a22d6094c3 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_ui_schedule_matches_scheduler[Daily-86400] |
| PG-REG-6673acefa069 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[Manual] |
| PG-REG-af0529eaa4f1 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[Real-time] |
| PG-REG-864b82b5542d | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[0m] |
| PG-REG-1365a7b3dfa4 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[0h] |
| PG-REG-9b4349d7bf11 | regression | PASS | postgres.xml#tests.test_launch_readiness.test_invalid_or_manual_frequency_not_scheduled[999999d] |
| PG-REG-03aeb4ba648f | regression | PASS | postgres.xml#tests.test_leads.test_capture_disabled |
| PG-REG-08fe67f52a73 | regression | PASS | postgres.xml#tests.test_leads.test_capture_encrypted_and_operator_only |
| PG-REG-7594366ce111 | regression | PASS | postgres.xml#tests.test_leads.test_honeypot_and_consent |
| PG-REG-eaab30a394ec | regression | PASS | postgres.xml#tests.test_leads.test_personal_email_cannot_submit_enterprise_request |
| PG-REG-98300ea8e2c1 | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_salesforce_products_orders_refresh_without_duplicates |
| PG-REG-d4048808280a | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_mapping_failure_rolls_back_earlier_entities |
| PG-REG-a22225f96759 | inventory reconciliation | PASS | postgres.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change0] |
| PG-REG-6b78c64b0953 | inventory reconciliation | PASS | postgres.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change1] |
| PG-REG-2f4ef7d1891d | inventory reconciliation | PASS | postgres.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change2] |
| PG-REG-3f5c2115b002 | inventory reconciliation | PASS | postgres.xml#tests.test_mapped_connectors.test_invalid_values_never_invent_defaults[change3] |
| PG-REG-e78307a29ec0 | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_other_source_collision_rejected |
| PG-REG-dabe583ccff6 | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_incomplete_page_is_not_success |
| PG-REG-67480f8cb055 | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_mapping_rejects_query_injection_and_supplier_inference |
| PG-REG-8b911bf8853c | regression | PASS | postgres.xml#tests.test_mapped_connectors.test_salesforce_next_page_cannot_receive_token_on_other_host |
| PG-REG-9a04bbd653e6 | authentication | PASS | postgres.xml#tests.test_mapped_connectors.test_sap_http_session_pagination_and_refresh |
| PG-REG-f397295e9a63 | database integrity | PASS | postgres.xml#tests.test_mapped_connectors.test_sap_rejects_unapproved_or_cross_origin_urls |
| PG-REG-3f41d79b7b41 | regression | PASS | postgres.xml#tests.test_metrics_scoped.test_compute_kpis_scoped_to_org |
| PG-REG-23053ced0bc8 | regression | PASS | postgres.xml#tests.test_metrics_scoped.test_supplier_ranking_uses_few_queries |
| PG-REG-9a6ca26b9f1d | regression | PASS | postgres.xml#tests.test_migrations_schema.test_alembic_upgrade_empty_sqlite |
| PG-REG-fb4e971238b0 | regression | PASS | postgres.xml#tests.test_migrations_schema.test_stamp_and_upgrade_legacy_db |
| PG-REG-4fce8b3a831e | regression | PASS | postgres.xml#tests.test_orgs.test_create_org_via_api |
| PG-REG-aa58789c4138 | regression | PASS | postgres.xml#tests.test_orgs.test_invite_and_accept_token_flow |
| PG-REG-8f827ab0e703 | regression | PASS | postgres.xml#tests.test_orgs.test_dev_login_without_workos |
| PG-REG-f20bd566a52b | regression | PASS | postgres.xml#tests.test_orgs.test_billing_plans_without_stripe |
| PG-REG-d9af64fc31b4 | regression | PASS | postgres.xml#tests.test_orgs.test_stripe_checkout_fails_clearly_without_key |
| PG-REG-c2e6564c7f06 | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_graph_neighbors_supplier |
| PG-REG-ca9abc7cd36f | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_timeline_includes_alerts |
| PG-REG-43842a296003 | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_search_suppliers |
| PG-REG-9870acbd667d | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_mission_control_v2_fields |
| PG-REG-d3f7fa421526 | critical workflow | PASS | postgres.xml#tests.test_phase_b_intelligence.test_incident_lifecycle |
| PG-REG-2765b8e3d6c7 | AI factuality | PASS | postgres.xml#tests.test_phase_b_intelligence.test_ai_orchestrate |
| PG-REG-784e8623f53d | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_observability |
| PG-REG-124eb8312b4e | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_graph_api |
| PG-REG-7bf58d95eb34 | regression | PASS | postgres.xml#tests.test_phase_b_intelligence.test_timeline_api |
| PG-REG-b7df073f0187 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_data_quality_assess |
| PG-REG-d5011589783c | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_workflow_create_and_execute |
| PG-REG-22f94bc848e7 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_predictions_generate |
| PG-REG-70f8df3f8fd2 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_connector_studio_catalogue |
| PG-REG-4618cd203130 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_connector_studio_detail |
| PG-REG-0ac0c01093a7 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_workflows_api |
| PG-REG-26b6fb2cdab6 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_data_quality_api |
| PG-REG-1a33a224b216 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_dashboards_api |
| PG-REG-0b94fae1e029 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_predictions_api |
| PG-REG-567a9a4bc0f9 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_customer_success_api |
| PG-REG-3e3bc1eb5452 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_security_center_api |
| PG-REG-dd5c3be79177 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_platform_ops_api |
| PG-REG-45c83c2c1369 | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_mission_control_data_health |
| PG-REG-d7a8c2992e0a | regression | PASS | postgres.xml#tests.test_phase_c_enterprise.test_documents_upload |
| PG-REG-76c51dcacf97 | imports | PASS | postgres.xml#tests.test_pilot_import_journey.test_import_to_reorder_incident_and_inventory_refresh |
| PG-REG-0cc260b0051d | imports | PASS | postgres.xml#tests.test_pilot_import_journey.test_shipment_eta_update_and_incident_progress |
| PG-REG-05a550450019 | imports | PASS | postgres.xml#tests.test_pilot_import_journey.test_repeated_product_update_preserves_unmapped_fields |
| PG-REG-0677463c4e1f | imports | PASS | postgres.xml#tests.test_pilot_import_journey.test_inventory_import_rejects_ambiguous_warehouse |
| PG-REG-c566bf628ebe | imports | PASS | postgres.xml#tests.test_pilot_import_journey.test_inventory_outcome_counts_reconcile |
| PG-REG-012e8f06bcb1 | authorization | PASS | postgres.xml#tests.test_pilot_regressions.test_network_permission_does_not_unlock_mission_context |
| PG-REG-8c9bd403b544 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[None] |
| PG-REG-dc96ccbdb361 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[] |
| PG-REG-4cbcf96885ab | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[   ] |
| PG-REG-08dbf16a55ba | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_invalid_provider_output_is_rejected[42] |
| PG-REG-8f26b51b777c | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[TimeoutError] |
| PG-REG-919d9e981809 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[ConnectionError] |
| PG-REG-c0dae1896c3c | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[ValueError] |
| PG-REG-ca019c869b94 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_provider_failures_fall_back_without_exception_details[IndexError] |
| PG-REG-70513a2384bb | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_error_requests_counted_and_ids_sanitized |
| PG-REG-a88e7443e80a | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_request_id_length_is_bounded |
| PG-REG-f153933fffc8 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_hardened_upload_never_acknowledges_missing_bytes |
| PG-REG-bf0ffed31359 | database integrity | PASS | postgres.xml#tests.test_pilot_regressions.test_connectors_validate_final_urls_before_sending_tokens |
| PG-REG-1388df1bbe88 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_connector_errors_do_not_echo_provider_secrets[ups] |
| PG-REG-b171a14e36b8 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_connector_errors_do_not_echo_provider_secrets[dynamics] |
| PG-REG-6624c764ac99 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_sentry_removes_credentials_and_customer_payloads |
| PG-REG-3ef962d970e9 | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_dynamics_follows_pages_and_rejects_cycles |
| PG-REG-aecec70884ca | regression | PASS | postgres.xml#tests.test_pilot_regressions.test_legacy_rebuild_refuses_data_before_dropping_tables |
| PG-REG-6a43b62c2532 | AI factuality | PASS | postgres.xml#tests.test_pilot_regressions.test_ai_provider_failures_are_observable |
| PG-REG-a3cb74f9b7ca | regression | PASS | postgres.xml#tests.test_platform_console.test_sanitize_error_redacts_secrets |
| PG-REG-d6123eca4cbf | regression | PASS | postgres.xml#tests.test_platform_console.test_classify_failure_kinds |
| PG-REG-3f289d0dab01 | authentication | PASS | postgres.xml#tests.test_platform_console.test_unauthenticated_admin_is_401 |
| PG-REG-3148bdfe95ff | tenant isolation | PASS | postgres.xml#tests.test_platform_console.test_tenant_owner_cannot_access_admin |
| PG-REG-761b430a8a66 | regression | PASS | postgres.xml#tests.test_platform_console.test_platform_admin_can_access_health |
| PG-REG-482bc7302021 | tenant isolation | PASS | postgres.xml#tests.test_platform_console.test_non_admin_cannot_read_other_tenant_via_admin |
| PG-REG-6c7c4f3aad58 | tenant isolation | PASS | postgres.xml#tests.test_platform_console.test_platform_admin_lists_both_tenants |
| PG-REG-72c5b11ab935 | tenant isolation | PASS | postgres.xml#tests.test_platform_console.test_platform_admin_tenant_detail_and_audit |
| PG-REG-4b7d1f7bea42 | regression | PASS | postgres.xml#tests.test_platform_console.test_api_token_cannot_use_admin_even_if_user_is_platform_admin |
| PG-REG-1658440534a3 | regression | PASS | postgres.xml#tests.test_platform_console.test_postgres_health_failure |
| PG-REG-668773b92197 | regression | PASS | postgres.xml#tests.test_platform_console.test_redis_unavailable_is_not_reported_healthy |
| PG-REG-36afb8e579de | regression | PASS | postgres.xml#tests.test_platform_console.test_connector_and_job_reporting |
| PG-REG-6e474adf124e | regression | PASS | postgres.xml#tests.test_platform_console.test_stale_connector_is_warning |
| PG-REG-686f8d5df378 | regression | PASS | postgres.xml#tests.test_platform_console.test_retry_enqueues_and_audits |
| PG-REG-0e5fa03dd930 | regression | PASS | postgres.xml#tests.test_platform_console.test_retry_wrong_org_is_404 |
| PG-REG-c2b7604c223f | regression | PASS | postgres.xml#tests.test_platform_foundation.test_parse_sync_frequency |
| PG-REG-60bbbaa705f3 | regression | PASS | postgres.xml#tests.test_platform_foundation.test_schedule_next_sets_future |
| PG-REG-e78be2225e0e | regression | PASS | postgres.xml#tests.test_platform_foundation.test_enqueue_due_connector_syncs_scans_orgs |
| PG-REG-08590cecb41d | regression | PASS | postgres.xml#tests.test_platform_foundation.test_email_skips_without_resend |
| PG-REG-cd2b858b24f3 | regression | PASS | postgres.xml#tests.test_platform_foundation.test_flags_defaults |
| PG-REG-5bd74ada2a45 | regression | PASS | postgres.xml#tests.test_platform_foundation.test_purchase_and_sales_orders_api |
| PG-REG-34b039e4912b | authentication | PASS | postgres.xml#tests.test_platform_foundation.test_orders_require_auth |
| PG-REG-e78e66b3ce1f | database integrity | PASS | postgres.xml#tests.test_postgres_api_rls.test_set_local_guc_cleared_by_commit_but_restored_after_begin |
| PG-REG-bfe5c21cadc4 | database integrity | PASS | postgres.xml#tests.test_postgres_api_rls.test_api_request_path_returns_owned_shipment_ids |
| PG-REG-49c48b27267d | database integrity | PASS | postgres.xml#tests.test_postgres_api_rls.test_api_cross_org_detail_invisible |
| PG-REG-d2159d50f84f | database integrity | PASS | postgres.xml#tests.test_postgres_api_rls.test_api_spoofed_org_header_rejected |
| PG-REG-7b371e30e402 | tenant isolation | PASS | postgres.xml#tests.test_postgres_api_rls.test_missing_tenant_guc_sees_zero_protected_rows |
| PG-REG-0ce70ed0cb75 | imports | PASS | postgres.xml#tests.test_priorities.test_import_detect_explain_act_resolve_and_refresh |
| PG-REG-d01092d8f782 | tenant isolation | PASS | postgres.xml#tests.test_priorities.test_unknown_or_other_tenant_priority_not_exposed |
| PG-REG-6c1a7a92ca9a | critical workflow | PASS | postgres.xml#tests.test_priorities.test_viewer_cannot_turn_priority_into_action |
| PG-REG-009d51a161e5 | authentication | PASS | postgres.xml#tests.test_private_demo_login.test_private_demo_session_and_write_denial |
| PG-REG-8dc3dd7c7875 | regression | PASS | postgres.xml#tests.test_private_demo_login.test_wrong_credentials_and_disabled |
| PG-REG-fa73ab8601a8 | authentication | PASS | postgres.xml#tests.test_private_demo_login.test_password_rotation_revokes_existing_session |
| PG-REG-430a477bb7d5 | authentication | PASS | postgres.xml#tests.test_private_demo_login.test_role_change_invalidates_demo_session |
| PG-REG-5c0a577dd199 | regression | PASS | postgres.xml#tests.test_private_demo_login.test_another_membership_blocks_login |
| PG-REG-0844b2d1c52b | regression | PASS | postgres.xml#tests.test_private_demo_login.test_demo_operator_can_act_without_administration |
| PG-REG-4bafb65983c0 | authorization | PASS | postgres.xml#tests.test_rbac.test_viewer_can_read_shipments |
| PG-REG-11809713c9bf | authorization | PASS | postgres.xml#tests.test_rbac.test_viewer_cannot_update_shipment |
| PG-REG-fdcda9762837 | authorization | PASS | postgres.xml#tests.test_rbac.test_owner_can_update_shipment |
| PG-REG-e6a56d87e431 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_ready_shortage_and_reservations |
| PG-REG-237e3edd391a | regression | PASS | postgres.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change0-READY] |
| PG-REG-b5b27f41358c | regression | PASS | postgres.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change1-SHORTAGE] |
| PG-REG-0051b7688110 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change2-AT RISK] |
| PG-REG-d032a817eaeb | regression | PASS | postgres.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change3-AT RISK] |
| PG-REG-eaacb1086640 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_inbound_dates_and_confirmation[change4-SHORTAGE] |
| PG-REG-3c438caf83f3 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[observed_quantity-None-UNKNOWN] |
| PG-REG-bac4ddded469 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[observed_quantity-99-UNKNOWN] |
| PG-REG-5e8923349851 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[reserved_quantity-None-UNKNOWN] |
| PG-REG-700856a3beb8 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[usability-unknown-UNKNOWN] |
| PG-REG-318a5f82db2f | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[usability-quarantined-SHORTAGE] |
| PG-REG-8b1f7c23a26f | regression | PASS | postgres.xml#tests.test_recovery_engine.test_stock_trust_never_false_ready[source_updated_at-2020-01-01T00:00:00Z-AT RISK] |
| PG-REG-d29228d864df | inventory reconciliation | PASS | postgres.xml#tests.test_recovery_engine.test_inventory_and_inbound_never_double_counted |
| PG-REG-3aeae8504d95 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_duplicate_po_line_not_counted |
| PG-REG-f39c8ebbe0bb | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_vs_zero[None-UNKNOWN] |
| PG-REG-9c0fa4185fb4 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_vs_zero[0-READY] |
| PG-REG-518dd4179e7f | regression | PASS | postgres.xml#tests.test_recovery_engine.test_unknown_part_and_duplicate_stock |
| PG-REG-851226ecad6b | regression | PASS | postgres.xml#tests.test_recovery_engine.test_transfer_preserves_donor_and_is_nonmutating |
| PG-REG-c201b2c92bdf | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change0] |
| PG-REG-3cd4deee2a1a | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change1] |
| PG-REG-c08e746995f4 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change2] |
| PG-REG-8e7080dc886f | regression | PASS | postgres.xml#tests.test_recovery_engine.test_missing_action_evidence_not_feasible[change3] |
| PG-REG-9928347c3195 | authentication | PASS | postgres.xml#tests.test_recovery_engine.test_substitute_requires_authorization_and_suitable_stock |
| PG-REG-f3ef44270138 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_repair_timing_and_unknown_cost |
| PG-REG-7f9a492621de | critical workflow | PASS | postgres.xml#tests.test_recovery_engine.test_end_to_end_propose_approve_outcome_incident_and_audit |
| PG-REG-4997975e702c | imports | PASS | postgres.xml#tests.test_recovery_engine.test_import_retry_conflict_rollback_and_correction |
| PG-REG-2b4203a78c7c | tenant isolation | PASS | postgres.xml#tests.test_recovery_engine.test_recovery_permissions_tenant_isolation_and_copilot |
| PG-REG-75d20d4dd3fb | regression | PASS | postgres.xml#tests.test_recovery_engine.test_empty_copilot_abstains |
| PG-REG-9a49521b3d22 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_overdue_unreceived_supply_is_not_guaranteed |
| PG-REG-d2577d2450bd | regression | PASS | postgres.xml#tests.test_recovery_engine.test_approved_alias_only_and_ambiguous_alias_abstention |
| PG-REG-dbf369076b8b | regression | PASS | postgres.xml#tests.test_recovery_engine.test_donor_preview_shows_created_shortage_and_missing_currency |
| PG-REG-ee74e51b0281 | imports | PASS | postgres.xml#tests.test_recovery_engine.test_import_invalid_row_rolls_back_entire_file |
| PG-REG-8058354ab0bf | regression | PASS | postgres.xml#tests.test_recovery_engine.test_source_change_blocks_stale_approval |
| PG-REG-58da18168616 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_valid_case_denied_to_viewer_and_foreign_organization |
| PG-REG-fb496b8f6285 | database integrity | PASS | postgres.xml#tests.test_recovery_engine.test_postgres_recovery_records_enforce_rls |
| PG-REG-ebd8253b53a9 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_approval_rechecks_elapsed_evidence_without_source_edit |
| PG-REG-411635c9e5a7 | inventory reconciliation | PASS | postgres.xml#tests.test_recovery_engine.test_competing_proposals_revalidate_and_approval_has_no_inventory_effect |
| PG-REG-22570b8ce652 | regression | PASS | postgres.xml#tests.test_recovery_engine.test_recovery_source_instructions_cannot_replace_grounded_answer |
| PG-REG-f411c2d9000a | database integrity | PASS | postgres.xml#tests.test_recovery_engine.test_postgres_recovery_cases_enforce_rls |
| PG-REG-09acfa6674df | database integrity | PASS | postgres.xml#tests.test_rls.test_rls_policies_exist |
| PG-REG-fef269a90641 | database integrity | PASS | postgres.xml#tests.test_rls.test_rls_blocks_without_guc |
| PG-REG-6ab1c619c978 | database integrity | PASS | postgres.xml#tests.test_rls.test_app_role_does_not_bypass_rls |
| PG-REG-974bbcd7d334 | background jobs | PASS | postgres.xml#tests.test_salesforce_arq_redis.test_enqueue_and_arq_worker_processes_salesforce_sync |
| PG-REG-9bd930d1bb1d | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_successful_connection_and_sync |
| PG-REG-21c6854a232a | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_invalid_credentials_are_permanent |
| PG-REG-6d86545c79d8 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_empty_dataset_succeeds |
| PG-REG-f7e409c880df | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_pagination_fetches_every_page |
| PG-REG-282d24ba33a7 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_large_dataset_multiple_pages |
| PG-REG-d58c6738cab9 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_duplicate_sync_is_idempotent |
| PG-REG-5f26935895a7 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_page_two_failure_does_not_report_success_or_advance_cursor |
| PG-REG-ed3a50f635ca | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_incomplete_pagination_cap_is_not_success |
| PG-REG-c4537962c0e3 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_incremental_cursor_filters_subsequent_query |
| PG-REG-aba1145016ee | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_transient_429_retries_then_succeeds |
| PG-REG-ebb64fe13f1d | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_timeout_is_retryable |
| PG-REG-4eb9de47e58e | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_connection_failure_is_retryable |
| PG-REG-d04462718262 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_http_500_is_retryable |
| PG-REG-c2e83bb8a446 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_malformed_response_is_permanent |
| PG-REG-19597b8f67bf | background jobs | PASS | postgres.xml#tests.test_salesforce_sync.test_arq_permanent_failure_does_not_raise_retry |
| PG-REG-e5bebe617901 | background jobs | PASS | postgres.xml#tests.test_salesforce_sync.test_arq_transient_failure_raises_retry |
| PG-REG-775c0b6cf188 | background jobs | PASS | postgres.xml#tests.test_salesforce_sync.test_arq_max_tries_marks_failed |
| PG-REG-964a727cee74 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_queued_job_created_on_enqueue |
| PG-REG-74016ba97cc7 | background jobs | PASS | postgres.xml#tests.test_salesforce_sync.test_worker_restart_recovers_stale_syncing |
| PG-REG-c73541556529 | tenant isolation | PASS | postgres.xml#tests.test_salesforce_sync.test_cross_tenant_sync_isolation |
| PG-REG-f2be20f63cb3 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_credentials_never_in_api_response |
| PG-REG-8d525e3065f0 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_disconnect_clears_credentials |
| PG-REG-9361aba9ecee | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_delete_wipes_credentials_then_removes_row |
| PG-REG-c7de5740839e | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_credentials_not_written_to_logs |
| PG-REG-ac9894b36768 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_configured_without_sync_is_not_healthy |
| PG-REG-e78fba0a519f | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_non_admin_cannot_trigger_admin_retry |
| PG-REG-61c46689e737 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_test_connection_sanitizes_error |
| PG-REG-bdc26fbe987f | tenant isolation | PASS | postgres.xml#tests.test_salesforce_sync.test_postgres_worker_session_cannot_see_other_tenant_suppliers |
| PG-REG-9d7c4cbf0892 | regression | PASS | postgres.xml#tests.test_salesforce_sync.test_create_queued_job_reuses_open_job |
| PG-REG-b07579745d7f | tenant isolation | PASS | postgres.xml#tests.test_security_attack_matrix.test_A_cross_tenant_shipment_uuid |
| PG-REG-e1f6937dd7b3 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_B_spoofed_x_organization_id |
| PG-REG-3bc4d3169b5c | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_H_viewer_cannot_create_simulation |
| PG-REG-773488a63ab6 | authentication | PASS | postgres.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://127.0.0.1/oauth] |
| PG-REG-960b66ca149e | authentication | PASS | postgres.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://localhost/oauth] |
| PG-REG-253f88cae7f8 | authentication | PASS | postgres.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://10.0.0.5/oauth] |
| PG-REG-ada66eba4949 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://169.254.169.254/latest/meta-data] |
| PG-REG-6e216a1fad85 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_IJK_ssrf_blocks[https://metadata.google.internal/] |
| PG-REG-e7a6aca294ad | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_L_executable_extension_rejected |
| PG-REG-ca1bcd8761a8 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_M_oversized_upload_rejected |
| PG-REG-78ac84a64ef4 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_document_extension_allowlist |
| PG-REG-2daa76f94b84 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_stripe_metadata_cannot_override_customer_index |
| PG-REG-a8116522f8d8 | authentication | PASS | postgres.xml#tests.test_security_attack_matrix.test_P_ai_prompt_injection_does_not_bypass_auth |
| PG-REG-78970e615225 | authentication | PASS | postgres.xml#tests.test_security_attack_matrix.test_S_unauthenticated_sensitive_api |
| PG-REG-a71149bde482 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_T_production_dev_login_blocked |
| PG-REG-15b425e699a8 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_job_signature_rejects_tamper |
| PG-REG-3559810c12c5 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_V_cors_star_rejected_in_production |
| PG-REG-9ca89b5b5ccb | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_W_csrf_blocks_untrusted_origin |
| PG-REG-fe5621aa4e85 | regression | PASS | postgres.xml#tests.test_security_attack_matrix.test_document_upload_rejects_exe |
| PG-REG-15bb0581e533 | regression | PASS | postgres.xml#tests.test_security_hardening.test_cannot_invite_owner_via_any_role |
| PG-REG-8998b7c18ebb | regression | PASS | postgres.xml#tests.test_security_hardening.test_operations_director_cannot_invite_admin |
| PG-REG-4afde28043cf | regression | PASS | postgres.xml#tests.test_security_hardening.test_invite_owner_role_rejected_by_api |
| PG-REG-3a9ff4451477 | regression | PASS | postgres.xml#tests.test_security_hardening.test_outbound_url_rejects_metadata_and_http |
| PG-REG-20442b11bf45 | regression | PASS | postgres.xml#tests.test_security_hardening.test_slack_url_requires_known_host |
| PG-REG-a3613a41f16f | regression | PASS | postgres.xml#tests.test_security_hardening.test_config_rejects_plaintext_secrets |
| PG-REG-23a92d6e7b9d | regression | PASS | postgres.xml#tests.test_security_hardening.test_webhook_rejects_private_url |
| PG-REG-5d94be6bd8cd | regression | PASS | postgres.xml#tests.test_ssrf.test_allows_salesforce_login |
| PG-REG-d5707e13e2f8 | regression | PASS | postgres.xml#tests.test_ssrf.test_allows_salesforce_instance |
| PG-REG-6c9521ebc2af | regression | PASS | postgres.xml#tests.test_ssrf.test_rejects_private_ip |
| PG-REG-ad38cccce8d9 | regression | PASS | postgres.xml#tests.test_ssrf.test_rejects_http |
| PG-REG-c12ecef82dd2 | regression | PASS | postgres.xml#tests.test_ssrf.test_rejects_arbitrary_host |
| PG-REG-4166b8899adb | regression | PASS | postgres.xml#tests.test_ssrf.test_rejects_metadata_ip |
| PG-REG-d541b2b798d9 | regression | PASS | postgres.xml#tests.test_ssrf.test_configure_rejects_evil_base_url |
| PG-REG-05307a2aec46 | database integrity | PASS | postgres.xml#tests.test_ssrf.test_validate_config_urls_ok |
| PG-REG-cf86c3a15108 | regression | PASS | postgres.xml#tests.test_startup_checks.test_development_allows_default_secrets |
| PG-REG-501a6348fd87 | authentication | PASS | postgres.xml#tests.test_startup_checks.test_production_rejects_default_session_secret |
| PG-REG-5c869c07b93e | regression | PASS | postgres.xml#tests.test_startup_checks.test_production_rejects_missing_encryption_key |
| PG-REG-6236ad123b3c | regression | PASS | postgres.xml#tests.test_startup_checks.test_production_happy_path |
| PG-REG-930d375e1098 | regression | PASS | postgres.xml#tests.test_startup_checks.test_staging_requires_metrics_token |
| PG-REG-fbc2860e5481 | regression | PASS | postgres.xml#tests.test_startup_checks.test_staging_happy_path |
| PG-REG-16d8dceb03aa | regression | PASS | postgres.xml#tests.test_startup_checks.test_staging_rejects_inline_sync |
| PG-REG-056aad599493 | regression | PASS | postgres.xml#tests.test_startup_checks.test_production_requires_billing_enforce |
| PG-REG-2c1e2e62f0bc | regression | PASS | postgres.xml#tests.test_startup_checks.test_unknown_environment_fail_closed |
| PG-REG-d3b93f3bb48d | regression | PASS | postgres.xml#tests.test_startup_checks.test_staging_requires_csrf |
| PG-REG-fb0635d82c4f | authentication | PASS | postgres.xml#tests.test_startup_checks.test_production_rejects_unauthenticated_redis |
| PG-REG-20d99ed640af | authentication | PASS | postgres.xml#tests.test_startup_checks.test_staging_allows_local_redis_without_auth |
| PG-REG-bbaef388f169 | background jobs | PASS | postgres.xml#tests.test_startup_checks.test_worker_role_skips_workos |
| PG-REG-ac61375bf63f | database integrity | PASS | postgres.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[FRONTEND_URL-http://app.example.com] |
| PG-REG-e4ddc0fbf2bc | database integrity | PASS | postgres.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[WORKOS_REDIRECT_URI-http://api.example.com/callback] |
| PG-REG-c57efbc25c0d | database integrity | PASS | postgres.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[FRONTEND_URL-https://user:password@app.example.com] |
| PG-REG-1af11b2e862a | database integrity | PASS | postgres.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[CORS_ORIGINS-value3] |
| PG-REG-2bcfd04d5b81 | database integrity | PASS | postgres.xml#tests.test_startup_checks.test_insecure_production_urls_rejected[DATABASE_URL-sqlite:///production.db] |
| PG-REG-83c7ec3410cc | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_app_role_cannot_disable_row_security |
| PG-REG-338055d96814 | tenant isolation | PASS | postgres.xml#tests.test_stripe_force_rls.test_lookup_function_works_without_tenant_guc |
| PG-REG-eb761fd85465 | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_entitlement_update_without_guc |
| PG-REG-10fdc898d63c | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_duplicate_is_idempotent |
| PG-REG-3853ef75f745 | tenant isolation | PASS | postgres.xml#tests.test_stripe_force_rls.test_invoice_paid_unknown_customer_no_tenant_mutation |
| PG-REG-0bf3270ad86b | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_checkout_then_invoice_paid_full_path |
| PG-REG-ba9f873ccd73 | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_subscription_update_via_customer_lookup |
| PG-REG-007d42a331d6 | database integrity | PASS | postgres.xml#tests.test_stripe_force_rls.test_webhook_signature_verification |
| PG-REG-c16a07e6ee4e | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_checkout_webhook_sets_billing_and_is_idempotent |
| PG-REG-a226d5594d8f | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_invoice_paid_credit_reset_idempotent |
| PG-REG-9256dd68b09e | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_invoice_paid_resolves_org_via_customer_id |
| PG-REG-dea469a305c2 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_checkout_metadata_does_not_activate_unpaid_subscription |
| PG-REG-80c21b480564 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_checkout_customer_mapping_overrides_conflicting_metadata |
| PG-REG-b445ffe7d187 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_manual_invoice_cannot_reactivate_subscription |
| PG-REG-6f62310b7f82 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_delayed_and_duplicate_invoice_cannot_reset_current_usage |
| PG-REG-4be0cd1d4635 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_checkout_verification_failure_is_retryable |
| PG-REG-9137a6f1bcbc | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_stale_subscription_event_uses_current_provider_status |
| PG-REG-acbeb7114658 | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_verified_checkout_activates_paid_plan |
| PG-REG-9aa1876c967b | regression | PASS | postgres.xml#tests.test_stripe_webhooks.test_checkout_rejects_subscription_from_another_customer |
| PG-REG-4a2699105b79 | regression | PASS | postgres.xml#tests.test_subscription_access.test_expired_trial_blocks_operations_but_allows_billing |
| PG-REG-ca0463f2a595 | regression | PASS | postgres.xml#tests.test_subscription_access.test_active_subscription_and_failed_payment |
| PG-REG-a0f6d671e6e7 | AI factuality | PASS | postgres.xml#tests.test_subscription_access.test_concurrent_ai_quota_is_serialized |
| PG-REG-20ab339806f3 | regression | PASS | postgres.xml#tests.test_subscription_access.test_trial_cannot_create_paid_api_tokens |
| PG-REG-71189bcca43a | regression | PASS | postgres.xml#tests.test_sync_enqueue.test_sync_enqueues_when_not_inline |
| PG-REG-553c202d4f07 | tenant isolation | PASS | postgres.xml#tests.test_tenant_isolation.test_org_a_sees_only_own_shipments |
| PG-REG-53014862a0c0 | tenant isolation | PASS | postgres.xml#tests.test_tenant_isolation.test_org_b_cannot_fetch_org_a_shipment |
| PG-REG-fd62bf8bd923 | tenant isolation | PASS | postgres.xml#tests.test_tenant_isolation.test_org_b_list_excludes_org_a |
| PG-REG-d347000988aa | tenant isolation | PASS | postgres.xml#tests.test_tenant_isolation.test_spoofed_org_header_cannot_access_other_tenant |
| PG-REG-96592a3a061f | tenant isolation | PASS | postgres.xml#tests.test_tenant_isolation.test_cross_org_suppliers_and_alerts_isolated |
| PG-REG-f905a17fec74 | regression | PASS | postgres.xml#tests.test_vercel_configuration.test_marketplace_prefers_pooled_database |
| PG-REG-8da3b4cc9016 | regression | PASS | postgres.xml#tests.test_vercel_configuration.test_explicit_runtime_database_takes_precedence |
| PG-REG-de8881bc03d0 | background jobs | PASS | postgres.xml#tests.test_worker_process_recovery.test_worker_kill_redis_restore_duplicate_and_restart |
| PG-REG-0230202d0446 | background jobs | PASS | postgres.xml#tests.test_worker_process_recovery.test_worker_bounded_retries_report_terminal_failure |
| PG-REG-62c280c07fd9 | background jobs | PASS | postgres.xml#tests.test_worker_process_recovery.test_worker_database_connection_loss_recovers |
| PG-REG-8e9f308c7284 | authorization | PASS | postgres.xml#tests.test_workflows_e2e.test_workflow_invite_accept_permissions |
| PG-REG-cd722384ed45 | imports | PASS | postgres.xml#tests.test_workflows_e2e.test_workflow_csv_import_audit |
| PG-REG-5d40166c5649 | regression | PASS | postgres.xml#tests.test_workflows_e2e.test_workflow_api_token_rotate_and_org_binding |
| PG-REG-8cce98900d5a | tenant isolation | PASS | postgres.xml#tests.test_workflows_e2e.test_workflow_tenant_isolation |
| PG-REG-f3dcef2e1965 | authentication | PASS | postgres.xml#tests.test_workflows_e2e.test_workflow_logout_revokes_session |
| PG-REG-dee9dde2cbc9 | authentication | PASS | postgres.xml#tests.test_workos_sdk_contract.test_authorization_url_includes_pkce_method |
| PG-REG-8ba265677e8b | authentication | PASS | postgres.xml#tests.test_workos_sdk_contract.test_authentication_matches_installed_sdk_signature |
| PG-REG-23924d824849 | regression | PASS | postgres.xml#tests.test_yc_demo.test_requires_existing_verified_login |
| PG-REG-114f29d0c4a3 | AI factuality | PASS | postgres.xml#tests.test_yc_demo.test_demo_reconciles_and_ai_uses_actual_positions |
| PG-REG-c1d4d7156999 | tenant isolation | PASS | postgres.xml#tests.test_yc_demo.test_reset_requires_exact_allowlist_and_preserves_other_tenant |
| PG-REG-30c60229c795 | imports | PASS | postgres.xml#tests.test_yc_demo.test_demo_workbook_parses_through_real_importer |
| PG-REG-ad1deeac9adc | regression | PASS | postgres.xml#tests.test_yc_demo.test_demo_viewer_cannot_reset |
| PG-REG-1cbd92336c4f | AI factuality | PASS | postgres.xml#tests.test_yc_demo.test_demo_ai_does_not_include_other_company |
| IMPORT-ATOMIC-001 | imports | PASS | postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[after_commit], postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[before_commit], postgres.xml#tests.test_import_process_recovery.test_import_process_death_and_retry[between_rows] |
| JOB-001 | background jobs | PASS | postgres.xml#tests.test_worker_process_recovery.test_worker_bounded_retries_report_terminal_failure, postgres.xml#tests.test_worker_process_recovery.test_worker_database_connection_loss_recovers, postgres.xml#tests.test_worker_process_recovery.test_worker_kill_redis_restore_duplicate_and_restart |
| PG-001 | database integrity | PASS | postgres.log, postgres.xml |
| AUTH-001 | authentication | PASS | browser.json#AUTH-001 |
| INV-001 | inventory reconciliation | PASS | browser.json#INV-001 |
| TENANT-001 | tenant isolation | PASS | browser.json#TENANT-001 |
| INCIDENT-001 | critical workflow | PASS | browser.json#INCIDENT-001 |
| IMPORT-001 | imports | PASS | browser.json#IMPORT-001 |
| IMPORT-007 | imports | PASS | browser.json#IMPORT-007 |
| AI-001 | AI factuality | PASS | browser.json#AI-001 |
| AI-002 | AI tenant isolation | PASS | browser.json#AI-002 |
| AI-003 | AI factuality | PASS | browser.json#AI-003 |
| AUTH-003 | authentication | PASS | browser.json#AUTH-003 |
| DASH-002 | inventory reconciliation | PASS | browser.json#DASH-002 |
| AI-004 | AI tenant isolation | PASS | browser.json#AI-004 |
| RECOVERY-001 | critical workflow | PASS | browser.json#RECOVERY-001 |
| IMPORT-002 | imports | PASS | scenarios.json#IMPORT-002 |
| INV-002 | inventory reconciliation | PASS | scenarios.json#INV-002 |
| IMPORT-003 | imports | PASS | scenarios.json#IMPORT-003 |
| SHIP-001 | imports | PASS | scenarios.json#SHIP-001 |
| AUTHZ-001 | authorization | PASS | scenarios.json#AUTHZ-001 |
| AUTH-002 | authentication | PASS | scenarios.json#AUTH-002 |
| IMPORT-004 | imports | PASS | scenarios.json#IMPORT-004 |
| IMPORT-006 | imports | PASS | scenarios.json#IMPORT-006 |
| IMPORT-005 | imports | PASS | scenarios.json#IMPORT-005 |
| HOST-001 | production smoke | BLOCKED |  |
| SSO-001 | authentication | BLOCKED |  |
| AI-LIVE-001 | AI tenant isolation | BLOCKED |  |
| VISUAL-REVIEW-001 | visual review | BLOCKED |  |
