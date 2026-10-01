export type HealthState = "healthy" | "warning" | "critical" | "unknown";

export interface HealthComponent {
  name: string;
  state: HealthState;
  detail: string;
}

export interface WorkerStats {
  state: HealthState;
  detail: string;
  active_workers: number;
  queued_jobs: number;
  running_jobs: number;
  failed_jobs_heartbeat: number | null;
  completed_jobs_heartbeat: number | null;
  retried_jobs_heartbeat?: number | null;
  heartbeat_at: string | null;
  heartbeat_raw: string | null;
  queue_known?: boolean;
}

export interface SystemHealth {
  overall: HealthState;
  checked_at: string;
  environment: string;
  inline_sync: boolean;
  components: HealthComponent[];
  workers: WorkerStats;
}

export interface TenantRow {
  id: string;
  name: string;
  slug: string;
  status: string;
  health: HealthState;
  user_count: number;
  connector_count: number;
  last_successful_sync_at: string | null;
  failed_jobs: number;
  open_dead_letters: number;
  last_activity_at: string | null;
  created_at: string | null;
  plan: string;
}

export interface TenantList {
  checked_at: string;
  counts: { tenants: number; warning: number; critical: number };
  items: TenantRow[];
}

export interface ConnectorRow {
  id: string;
  organization_id: string;
  organization_name?: string;
  name: string;
  connector_type: string;
  status: string;
  lifecycle_status: string;
  health: string;
  last_successful_sync_at: string | null;
  last_attempted_sync_at: string | null;
  next_sync_at: string | null;
  last_error: string | null;
  failure_class: string;
  retry_count: number;
  is_active: boolean;
  current_job_status: string;
}

export interface JobRow {
  id: string;
  kind: string;
  organization_id: string;
  organization_name: string | null;
  job_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number;
  retry_count: number;
  error_summary: string | null;
  failure_class: string;
  connection_id: string | null;
  can_retry: boolean;
}

export interface ErrorGroup {
  count: number;
  subsystem: string;
  severity: string;
  error_type: string;
  message: string;
  tenant_count: number;
  tenants: string[];
  last_seen_at: string | null;
  sample_id: string | null;
}

export function healthBadgeVariant(
  state: string
): "success" | "warning" | "destructive" | "muted" | "secondary" {
  if (state === "healthy" || state === "connected" || state === "success") return "success";
  if (state === "warning" || state === "syncing" || state === "degraded") return "warning";
  if (state === "critical" || state === "failed" || state === "error") return "destructive";
  return "muted";
}
