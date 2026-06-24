import { type LucideIcon, TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  delta?: number;
  deltaLabel?: string;
  intent?: "default" | "success" | "warning" | "danger";
  invertDelta?: boolean;
}

const INTENT_RING: Record<NonNullable<StatCardProps["intent"]>, string> = {
  default: "text-primary bg-primary/10",
  success: "text-success bg-success/10",
  warning: "text-warning bg-warning/10",
  danger: "text-destructive bg-destructive/10",
};

export function StatCard({
  label,
  value,
  icon: Icon,
  delta,
  deltaLabel,
  intent = "default",
  invertDelta = false,
}: StatCardProps) {
  const hasDelta = delta !== undefined && delta !== null;
  const positive = invertDelta ? (delta ?? 0) < 0 : (delta ?? 0) >= 0;

  return (
    <Card className="relative overflow-hidden p-5 transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
        </div>
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", INTENT_RING[intent])}>
          <Icon className="h-4.5 w-4.5" />
        </div>
      </div>
      {hasDelta && (
        <div className="mt-3 flex items-center gap-1.5 text-xs">
          <span
            className={cn(
              "flex items-center gap-0.5 font-medium",
              positive ? "text-success" : "text-destructive"
            )}
          >
            {positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
            {Math.abs(delta!).toFixed(1)}%
          </span>
          {deltaLabel && <span className="text-muted-foreground">{deltaLabel}</span>}
        </div>
      )}
    </Card>
  );
}
