import type { UserRole } from "@/lib/types";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
}

export interface NavGroup {
  label: string | null;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: null,
    items: [{ href: "/mission-control", label: "Mission Control", icon: "Radar" }],
  },
  {
    label: "Operations",
    items: [
      { href: "/shipments", label: "Shipments", icon: "Truck" },
      { href: "/inventory", label: "Inventory", icon: "Boxes" },
      { href: "/warehouses", label: "Warehouses", icon: "Warehouse" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/suppliers", label: "Suppliers", icon: "Factory" },
      { href: "/risk", label: "Risks", icon: "ShieldAlert" },
      { href: "/alerts", label: "Alerts", icon: "Bell" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/analytics", label: "Analytics", icon: "BarChart3" },
      { href: "/network", label: "Network View", icon: "Share2" },
      { href: "/simulator", label: "Simulation Center", icon: "FlaskConical" },
    ],
  },
  {
    label: "Data Sources",
    items: [
      { href: "/data-sources", label: "Overview", icon: "Database" },
      { href: "/data-sources/connectors", label: "Connectors", icon: "Plug" },
      { href: "/data-sources/import", label: "CSV Import", icon: "Upload" },
      { href: "/data-sources/excel", label: "Excel Import", icon: "FileSpreadsheet" },
      { href: "/data-sources/pipeline", label: "Pipeline Monitor", icon: "Activity" },
    ],
  },
  {
    label: "AI",
    items: [{ href: "/advisor", label: "Operations Copilot", icon: "Sparkles" }],
  },
  {
    label: "Reports",
    items: [{ href: "/reports", label: "Executive Briefs", icon: "FileText" }],
  },
  {
    label: null,
    items: [{ href: "/settings", label: "Settings", icon: "Settings" }],
  },
];

// Flat list used by global search and breadcrumbs
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrator",
  operations_manager: "Operations Manager",
  analyst: "Analyst",
  executive: "Executive",
};

// Chart palette tuned for dark enterprise dashboards
export const CHART_COLORS = {
  primary: "#3b82f6",
  blue: "#3b82f6",
  cyan: "#06b6d4",
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
  violet: "#8b5cf6",
  pink: "#ec4899",
  slate: "#94a3b8",
};

export const STATUS_COLORS: Record<string, string> = {
  in_transit: CHART_COLORS.blue,
  delayed: CHART_COLORS.red,
  delivered: CHART_COLORS.green,
  at_warehouse: CHART_COLORS.cyan,
  customs_hold: CHART_COLORS.amber,
};

export const DEMO_CREDENTIALS = [
  { role: "Admin", email: "admin@atlasops.io", password: "admin1234" },
  { role: "Operations Manager", email: "ops@atlasops.io", password: "ops12345" },
  { role: "Analyst", email: "analyst@atlasops.io", password: "analyst123" },
  { role: "Executive", email: "exec@atlasops.io", password: "exec12345" },
];
