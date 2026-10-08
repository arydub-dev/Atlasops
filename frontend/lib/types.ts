export type RoleSlug =
  | "owner"
  | "admin"
  | "operations_director"
  | "operations_manager"
  | "analyst"
  | "viewer"
  | string;

/** @deprecated Use RoleSlug / currentMembership.role_slug */
export type UserRole = RoleSlug;

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  is_platform_admin?: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: string;
  plan: string;
  owner_user_id?: string | null;
  trial_ends_at?: string | null;
  settings?: Record<string, unknown>;
  branding?: Record<string, unknown>;
  created_at: string;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  role_slug: RoleSlug;
  status: string;
  organization_name?: string | null;
  organization_slug?: string | null;
}

export interface MeResponse {
  user: User;
  memberships: Membership[];
  current_organization: Organization | null;
  current_membership: Membership | null;
}

export interface BillingPlanInfo {
  slug: string;
  name: string;
  description: string;
  seat_limit: number;
  connector_limit: number;
  ai_credits_monthly: number;
  features: string[];
  trial_days: number;
}

export interface Invitation {
  id: string;
  email: string;
  role_slug: string;
  status: string;
  expires_at: string;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type ShipmentStatus =
  | "in_transit"
  | "delayed"
  | "delivered"
  | "at_warehouse"
  | "customs_hold";

export interface Shipment {
  id: string;
  reference: string;
  origin: string;
  destination: string;
  carrier: string;
  current_location: string;
  status: ShipmentStatus;
  delay_risk_score: number;
  units: number;
  value_usd: number;
  shipped_at: string;
  eta: string;
  delivered_at: string | null;
  delay_days: number;
  supplier_id: string | null;
  warehouse_id: string | null;
  product_id: string | null;
}

export interface ShipmentEvent {
  id: string;
  status: ShipmentStatus;
  location: string;
  note: string | null;
  occurred_at: string;
}

export interface ShipmentDetail extends Shipment {
  supplier_name: string | null;
  warehouse_name: string | null;
  events: ShipmentEvent[];
}

export interface Warehouse {
  id: string;
  name: string;
  location: string;
  region: string;
  latitude: number;
  longitude: number;
  capacity: number;
  current_inventory: number;
  utilization: number;
  risk_level: "low" | "medium" | "high";
}

export interface InventoryItem {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  product_id: string;
  product_sku: string;
  product_name: string;
  quantity: number;
  reorder_point: number;
  safety_stock: number;
  max_stock: number;
  avg_daily_demand: number;
  days_of_supply: number | null;
  status: "ok" | "low_stock" | "overstock" | "stockout";
  reorder_recommendation: number;
}

export interface Supplier {
  id: string;
  name: string;
  country: string;
  region: string;
  category: string;
  supplier_score: number;
  delivery_reliability: number;
  average_delay_days: number;
  order_fulfillment_rate: number;
  defect_rate: number;
  is_active: boolean;
}

export interface SupplierScorecard extends Supplier {
  rank: number;
  total_shipments: number;
  delayed_shipments: number;
  on_time_rate: number;
  monthly_trend: { label: string; score: number; reliability: number }[];
}

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RiskCategory = "supplier" | "shipment" | "inventory" | "geographic";

export interface RiskAssessment {
  id: string;
  category: RiskCategory;
  level: RiskLevel;
  score: number;
  title: string;
  description: string;
  recommendation: string;
  entity_type: string | null;
  entity_id: string | null;
  factors: Record<string, number> | null;
  created_at: string;
}

export interface RiskSummary {
  overall_score: number;
  overall_level: RiskLevel;
  by_category: Record<string, number>;
  counts: Record<string, number>;
  top_risks: RiskAssessment[];
}

export type AlertType =
  | "delayed_shipment"
  | "inventory_stockout_risk"
  | "supplier_failure_risk"
  | "forecasted_demand_spike";
export type AlertPriority = "low" | "medium" | "high" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface Alert {
  id: string;
  alert_type: AlertType;
  priority: AlertPriority;
  status: AlertStatus;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
}

export interface KPISet {
  total_shipments: number;
  active_shipments: number;
  delayed_shipments: number;
  on_time_delivery_rate: number;
  inventory_health_score: number;
  supplier_reliability_score: number;
  open_alerts: number;
  critical_risks: number;
}

export interface DashboardResponse {
  kpis: KPISet;
  shipment_trend: { label: string; shipped: number; delivered: number; delayed: number }[];
  inventory_trend: { label: string; utilization: number }[];
  delay_trend: { label: string; avg_delay_days: number; delayed_pct: number }[];
  supplier_performance_trend: { label: string; supplier_score: number; delivery_reliability: number }[];
  critical_alerts: Alert[];
  top_risks: RiskAssessment[];
  recommended_actions: { title: string; action: string; priority: string; score: number }[];
}

export type SimulationType =
  | "supplier_shutdown"
  | "port_closure"
  | "demand_spike"
  | "weather_disruption"
  | "warehouse_outage";

export interface SimulationResult {
  summary: string;
  scenario: string;
  metrics: Record<string, number>;
  impacts: {
    inventory_impact_pct: number;
    shipment_impact_pct: number;
    revenue_impact_usd: number;
  };
  timeline: { day: number; impact: number }[];
  mitigations: string[];
}

export interface Simulation {
  id: string;
  name: string;
  simulation_type: SimulationType;
  parameters: Record<string, unknown>;
  results: SimulationResult;
  inventory_impact: number;
  shipment_impact: number;
  revenue_impact_usd: number;
  created_at: string;
}

export interface AIReport {
  id: string;
  prompt: string;
  response: string;
  report_type: string;
  model: string;
  created_at: string;
}

// ---- Mission Control ----
export interface HealthScore {
  score: number;
  grade: string;
  label: string;
}

export interface SituationInsight {
  icon: string;
  severity: "low" | "medium" | "high";
  text: string;
}

export interface SituationReport {
  headline: string;
  insights: SituationInsight[];
}

export interface RecommendedAction {
  priority: RiskLevel | string;
  title: string;
  detail: string;
  reason?: string;
  expected_impact: string;
  estimated_impact?: string;
  estimated_cost: string;
  confidence?: number;
  recommended_next_step?: string;
  category: RiskCategory | string;
  entity_type: string | null;
  entity_id: string | null;
  affected_entities?: { type?: string | null; id?: string | null }[];
  score: number;
  estimate_label?: string;
}

export interface CriticalAlertItem {
  id: string;
  title: string;
  message: string;
  priority: AlertPriority;
  alert_type: AlertType;
  created_at: string;
  recommended_response: string;
}

export interface TimelineEvent {
  message?: string | null;
  id: string;
  title: string;
  summary?: string;
  severity?: string;
  actor?: string;
  source?: string;
  occurred_at?: string;
  entity_type?: string;
  entity_id?: string;
}

export interface MissionControlResponse {
  health: HealthScore;
  kpis: KPISet & {
    overall_risk_score: number;
    inventory_risk_count: number;
    open_purchase_orders?: number;
    open_sales_orders?: number;
  };
  situation_report: SituationReport;
  ai_situation_report?: SituationReport;
  recommended_actions: RecommendedAction[];
  critical_alerts: CriticalAlertItem[];
  shipment_trend: { label: string; shipped: number; delivered: number; delayed: number }[];
  delay_trend: { label: string; avg_delay_days: number; delayed_pct: number }[];
  inventory_trend: { label: string; utilization: number }[];
  supplier_performance_trend: { label: string; supplier_score: number; delivery_reliability: number }[];
  inventory_health?: Record<string, number>;
  risk_heatmap?: Record<string, number>;
  purchase_orders?: {
    open_count: number;
    recent: { id: string; reference: string; status: string; total_amount: number }[];
  };
  sales_orders?: {
    open_count: number;
    recent: {
      id: string;
      reference: string;
      status: string;
      customer_name?: string;
      total_amount: number;
    }[];
  };
  top_incidents?: { id: string; title: string; severity: string; status: string }[];
  operational_timeline?: TimelineEvent[];
  connector_status?: {
    total: number;
    by_status: Record<string, number>;
    healthy: number;
    error: number;
    items: {
      id: string;
      name: string;
      type: string;
      status: string;
      health: string;
      last_sync_at?: string | null;
    }[];
  };
  graph?: { node_counts?: Record<string, number>; total_nodes?: number; total_edges?: number };
  upcoming_risks?: { title: string; score: number; level: string }[];
  data_health?: {
    score?: number;
    grade?: string;
    confidence?: number;
    remediations?: { priority?: string; action?: string }[];
  };
  predictions?: {
    id: string;
    kind: string;
    title: string;
    confidence: number;
    score?: number;
  }[];
}

// ---- Network View ----
export interface NetworkNode {
  id: string;
  entity_id: string;
  type: "warehouse" | "supplier";
  name: string;
  location: string;
  region: string;
  lat: number;
  lon: number;
  risk_score: number;
  active_shipments: number;
  // warehouse-only
  capacity?: number;
  utilization?: number;
  risk_level?: "low" | "medium" | "high";
  open_alerts?: number;
  current_inventory?: number;
  // supplier-only
  supplier_score?: number;
}

export interface NetworkEdge {
  from: { name: string; lat: number; lon: number };
  to: { name: string; lat: number; lon: number };
  volume: number;
  delayed: number;
  delay_rate: number;
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  hotspots: { city: string; delayed: number; coords: [number, number] }[];
  summary: { warehouses: number; suppliers: number; active_routes: number };
  mapbox?: { enabled: boolean; token_configured: boolean };
  overlays?: {
    delayed_routes: number;
    high_risk_warehouses: number;
    low_score_suppliers: number;
  };
}

// ---- Incidents / Search / AI Orchestration ----
export interface IncidentSummary {
  id: string;
  title: string;
  severity: string;
  status: string;
  summary?: string | null;
  created_at?: string | null;
  affected_count?: number;
}

export interface IncidentDetail extends IncidentSummary {
  owner_user_id?: string | null;
  affected_entities?: { type: string; id: string; label?: string }[];
  timeline?: TimelineEvent[];
  recommendations?: string[];
  ai_summary?: string | null;
  resolution?: string | null;
  resolved_at?: string | null;
}

export interface SearchResultItem {
  entity_type: string;
  entity_id: string;
  title: string;
  summary: string;
  status?: string | null;
  risk_score?: number | null;
  href?: string;
}

export interface AIOrchestrateResponse {
  response: string;
  model: string;
  intent: string;
  tool: string;
  confidence: number | null;
  citations: { type?: string; id?: string; source?: string }[];
  report_id?: string;
  context?: Record<string, unknown>;
}

// ---- Data Sources / Connected Mode ----
export type ConnectorType =
  | "sap_erp"
  | "sap_business_one"
  | "oracle_erp"
  | "salesforce_crm"
  | "salesforce"
  | "ms_dynamics"
  | "dynamics_bc"
  | "wms"
  | "tms"
  | "rest_api"
  | "csv_upload"
  | "excel_upload"
  | "json_upload"
  | "ups";

export type ConnectorStatus =
  | "connected"
  | "disconnected"
  | "syncing"
  | "error"
  | "not_configured";

export type ConnectorHealth = "healthy" | "degraded" | "down" | "unknown";
export type ImportStatus =
  | "success"
  | "partial"
  | "failed"
  | "running"
  | "queued"
  | "retrying"
  | "rolled_back";

export interface DataSource {
  id: string;
  name: string;
  connector_type: ConnectorType;
  status: ConnectorStatus;
  health: ConnectorHealth;
  base_url: string | null;
  auth_method: string | null;
  api_key_masked: string | null;
  sync_frequency: string | null;
  webhook_url: string | null;
  record_count: number;
  last_sync_at: string | null;
  last_error: string | null;
  failure_class?: string | null;
  is_active: boolean;
  config?: Record<string, unknown>;
  credential_hints?: Record<string, string>;
}

export interface IntegrationTemplate {
  type: ConnectorType;
  name: string;
  category: string;
  description: string;
  auth_methods: string[];
  configured: boolean;
}

export interface ImportJob {
  id: string;
  source_name: string;
  source_type: string;
  entity_type: string;
  status: ImportStatus;
  rows_processed: number;
  rows_imported: number;
  rows_rejected: number;
  duration_ms: number;
  error_summary: { row: number; errors: string[] }[] | null;
  created_at: string;
}

export interface DataSummary {
  mode: "demo" | "connected";
  connected_systems: number;
  total_sources: number;
  available_integrations: number;
  last_sync_at: string | null;
  records_imported_total: number;
  records_imported_today: number;
  status_counts: Record<string, number>;
  failures: { source: string; health: string; status: string }[];
}

export interface EntityField {
  name: string;
  label: string;
  required: boolean;
  type: string;
  default?: unknown;
  unique?: boolean;
  fk?: string;
}

export interface EntitySpec {
  label: string;
  fields: EntityField[];
}

export interface ImportPreview {
  entity: string;
  columns: string[];
  sheets: string[];
  suggested_mapping: Record<string, string | null>;
  row_count: number;
  preview_rows: Record<string, unknown>[];
  validation: {
    total: number;
    valid: number;
    rejected: number;
    errors: { row: number; errors: string[] }[];
    sample: Record<string, unknown>[];
  };
}

export interface ImportResult {
  outcomes?: { created: number; updated: number; unchanged: number };
  job_id: string;
  entity: string;
  status: ImportStatus;
  rows_processed: number;
  rows_imported: number;
  rows_rejected: number;
  duration_ms: number;
  errors: { row: number; errors: string[] }[];
}

// ---- Executive Brief ----
export interface ExecutiveBrief {
  generated_at: string;
  health: HealthScore;
  executive_summary: string;
  current_risks: string[];
  operational_performance: string[];
  key_recommendations: string[];
  strategic_concerns: string[];
  situation_headline: string;
}
