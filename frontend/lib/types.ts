export type UserRole = "admin" | "operations_manager" | "analyst" | "executive";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
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
  id: number;
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
  supplier_id: number | null;
  warehouse_id: number | null;
  product_id: number | null;
}

export interface ShipmentEvent {
  id: number;
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
  id: number;
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
  id: number;
  warehouse_id: number;
  warehouse_name: string;
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity: number;
  reorder_point: number;
  safety_stock: number;
  max_stock: number;
  avg_daily_demand: number;
  days_of_supply: number;
  status: "ok" | "low_stock" | "overstock" | "stockout";
  reorder_recommendation: number;
}

export interface Supplier {
  id: number;
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
  id: number;
  category: RiskCategory;
  level: RiskLevel;
  score: number;
  title: string;
  description: string;
  recommendation: string;
  entity_type: string | null;
  entity_id: number | null;
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
  id: number;
  alert_type: AlertType;
  priority: AlertPriority;
  status: AlertStatus;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
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
  id: number;
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
  id: number;
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
  priority: RiskLevel;
  title: string;
  detail: string;
  expected_impact: string;
  estimated_cost: string;
  category: RiskCategory;
  entity_type: string | null;
  entity_id: number | null;
  score: number;
}

export interface CriticalAlertItem {
  id: number;
  title: string;
  message: string;
  priority: AlertPriority;
  alert_type: AlertType;
  created_at: string;
  recommended_response: string;
}

export interface MissionControlResponse {
  health: HealthScore;
  kpis: KPISet & { overall_risk_score: number; inventory_risk_count: number };
  situation_report: SituationReport;
  recommended_actions: RecommendedAction[];
  critical_alerts: CriticalAlertItem[];
  shipment_trend: { label: string; shipped: number; delivered: number; delayed: number }[];
  delay_trend: { label: string; avg_delay_days: number; delayed_pct: number }[];
  inventory_trend: { label: string; utilization: number }[];
  supplier_performance_trend: { label: string; supplier_score: number; delivery_reliability: number }[];
}

// ---- Network View ----
export interface NetworkNode {
  id: string;
  entity_id: number;
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
}

// ---- Data Sources / Connected Mode ----
export type ConnectorType =
  | "sap_erp"
  | "oracle_erp"
  | "salesforce_crm"
  | "ms_dynamics"
  | "wms"
  | "tms"
  | "rest_api"
  | "csv_upload"
  | "excel_upload";

export type ConnectorStatus =
  | "connected"
  | "disconnected"
  | "syncing"
  | "error"
  | "not_configured";

export type ConnectorHealth = "healthy" | "degraded" | "down" | "unknown";
export type ImportStatus = "success" | "partial" | "failed" | "running";

export interface DataSource {
  id: number;
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
  is_active: boolean;
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
  id: number;
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
  job_id: number;
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
