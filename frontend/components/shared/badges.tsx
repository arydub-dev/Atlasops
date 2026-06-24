import { Badge } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";
import type { AlertPriority, RiskLevel, ShipmentStatus } from "@/lib/types";

const SHIPMENT_VARIANT: Record<ShipmentStatus, Parameters<typeof Badge>[0]["variant"]> = {
  in_transit: "default",
  delivered: "success",
  delayed: "destructive",
  at_warehouse: "secondary",
  customs_hold: "warning",
};

export function ShipmentStatusBadge({ status }: { status: ShipmentStatus }) {
  return <Badge variant={SHIPMENT_VARIANT[status]}>{titleCase(status)}</Badge>;
}

const LEVEL_VARIANT: Record<RiskLevel, Parameters<typeof Badge>[0]["variant"]> = {
  low: "success",
  medium: "warning",
  high: "destructive",
  critical: "destructive",
};

export function RiskLevelBadge({ level }: { level: RiskLevel }) {
  return (
    <Badge variant={LEVEL_VARIANT[level]} className={level === "critical" ? "animate-pulse-ring" : ""}>
      {titleCase(level)}
    </Badge>
  );
}

const PRIORITY_VARIANT: Record<AlertPriority, Parameters<typeof Badge>[0]["variant"]> = {
  low: "muted",
  medium: "warning",
  high: "destructive",
  critical: "destructive",
};

export function PriorityBadge({ priority }: { priority: AlertPriority }) {
  return <Badge variant={PRIORITY_VARIANT[priority]}>{titleCase(priority)}</Badge>;
}

export function RiskScore({ score }: { score: number }) {
  const color =
    score >= 80
      ? "text-destructive"
      : score >= 60
        ? "text-destructive"
        : score >= 35
          ? "text-warning"
          : "text-success";
  return <span className={`font-mono font-semibold tabular-nums ${color}`}>{score.toFixed(0)}</span>;
}
