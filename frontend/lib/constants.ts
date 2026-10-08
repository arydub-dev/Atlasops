export interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Minimum capability required to see this item in the sidebar. */
  access?: "any" | "write" | "operate" | "security" | "platform" | "internal";
}

export interface NavGroup {
  label: string | null;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: null,
    items: [{ href: "/mission-control", label: "Operational priorities", icon: "Radar" }],
  },
  {
    label: "Operations",
    items: [
      { href: "/shipments", label: "Shipments", icon: "Truck" },
      { href: "/inventory", label: "Inventory", icon: "Boxes" },
      { href: "/warehouses", label: "Warehouses", icon: "Warehouse" },
      { href: "/incidents", label: "Incidents", icon: "Siren" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/suppliers", label: "Suppliers", icon: "Factory" },
      { href: "/risk", label: "Risks", icon: "ShieldAlert" },
      { href: "/alerts", label: "Alerts", icon: "Bell" },
      { href: "/graph", label: "Knowledge Graph", icon: "GitBranch" },
      { href: "/predictions", label: "Predictions", icon: "TrendingUp" },
      { href: "/dashboards", label: "Exec Dashboards", icon: "LayoutDashboard" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/analytics", label: "Analytics", icon: "BarChart3" },
      { href: "/network", label: "Network View", icon: "Share2" },
      { href: "/simulator", label: "Simulation Center", icon: "FlaskConical" },
      { href: "/observability", label: "Observability", icon: "Gauge", access: "operate" },
      { href: "/platform-ops", label: "Platform Ops", icon: "Server", access: "operate" },
    ],
  },
  {
    label: "Data Sources",
    items: [
      { href: "/data-sources", label: "Overview", icon: "Database" },
      { href: "/connector-studio", label: "Connector Studio", icon: "Puzzle", access: "operate" },
      { href: "/data-sources/connectors", label: "Connectors", icon: "Plug", access: "operate" },
      { href: "/data-sources/import", label: "Import CSV / Excel", icon: "Upload", access: "write" },
      { href: "/data-sources/excel", label: "Excel Import", icon: "FileSpreadsheet", access: "write" },
      { href: "/data-sources/pipeline", label: "Pipeline Monitor", icon: "Activity", access: "operate" },
      { href: "/workflows", label: "Automations", icon: "Workflow", access: "operate" },
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
    items: [
      { href: "/admin", label: "Admin Console", icon: "ShieldCheck", access: "internal" },
      { href: "/customer-success", label: "Customer Success", icon: "Handshake", access: "platform" },
      { href: "/settings", label: "Settings", icon: "Settings" },
      { href: "/settings/security", label: "Security", icon: "Shield", access: "security" },
      { href: "/settings/admin", label: "Enterprise Admin", icon: "Building2", access: "security" },
    ],
  },
];

// Flat list used by global search and breadcrumbs
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

export function navVisibleForRole(
  access: NavItem["access"] | undefined,
  roleSlug: string | null | undefined,
  opts?: { isPlatformAdmin?: boolean }
): boolean {
  const level = access ?? "any";
  if (level === "internal") return !!opts?.isPlatformAdmin;
  if (level === "any") return true;
  if (!roleSlug) return false;
  if (level === "write") return roleSlug !== "viewer";
  if (level === "operate") {
    return ["owner", "admin", "operations_director", "operations_manager", "analyst"].includes(
      roleSlug
    );
  }
  if (level === "security" || level === "platform") {
    return ["owner", "admin"].includes(roleSlug);
  }
  return true;
}

export const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Administrator",
  operations_director: "Operations Director",
  operations_manager: "Operations Manager",
  analyst: "Analyst",
  viewer: "Viewer",
};

export function roleLabel(slug: string | null | undefined): string {
  if (!slug) return "";
  return ROLE_LABELS[slug] ?? slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

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

/** @deprecated Demo credentials removed for Supply v2 session auth. */
export const DEMO_CREDENTIALS: { role: string; email: string; password: string }[] = [];
