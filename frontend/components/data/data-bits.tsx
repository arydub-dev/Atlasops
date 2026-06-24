import {
  Boxes,
  Cloud,
  Database,
  type LucideIcon,
  Network,
  Plug,
  Truck,
  Building2,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ConnectorHealth, ConnectorStatus, ConnectorType, ImportStatus } from "@/lib/types";

export const CONNECTOR_ICON: Record<string, LucideIcon> = {
  sap_erp: Database,
  oracle_erp: Database,
  salesforce_crm: Users,
  ms_dynamics: Cloud,
  wms: Building2,
  tms: Truck,
  rest_api: Network,
  csv_upload: Boxes,
  excel_upload: Boxes,
};

export function ConnectorIcon({ type, className }: { type: ConnectorType | string; className?: string }) {
  const Icon = CONNECTOR_ICON[type] ?? Plug;
  return <Icon className={className ?? "h-5 w-5"} />;
}

const STATUS_VARIANT: Record<ConnectorStatus, Parameters<typeof Badge>[0]["variant"]> = {
  connected: "success",
  syncing: "default",
  disconnected: "secondary",
  error: "destructive",
  not_configured: "muted",
};

const STATUS_LABEL: Record<ConnectorStatus, string> = {
  connected: "Connected",
  syncing: "Syncing",
  disconnected: "Disconnected",
  error: "Error",
  not_configured: "Not Configured",
};

export function StatusBadge({ status }: { status: ConnectorStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className={status === "syncing" ? "gap-1.5" : ""}>
      {status === "syncing" && (
        <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-primary-foreground" />
      )}
      {STATUS_LABEL[status]}
    </Badge>
  );
}

const HEALTH_COLOR: Record<ConnectorHealth, string> = {
  healthy: "bg-success",
  degraded: "bg-warning",
  down: "bg-destructive",
  unknown: "bg-muted-foreground/40",
};

export function HealthDot({ health, withLabel }: { health: ConnectorHealth; withLabel?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className={cn("inline-block h-2 w-2 rounded-full", HEALTH_COLOR[health])} />
      {withLabel && <span className="capitalize text-muted-foreground">{health}</span>}
    </span>
  );
}

const IMPORT_VARIANT: Record<ImportStatus, Parameters<typeof Badge>[0]["variant"]> = {
  success: "success",
  partial: "warning",
  failed: "destructive",
  running: "default",
};

export function ImportStatusBadge({ status }: { status: ImportStatus }) {
  return <Badge variant={IMPORT_VARIANT[status]}>{status[0].toUpperCase() + status.slice(1)}</Badge>;
}
