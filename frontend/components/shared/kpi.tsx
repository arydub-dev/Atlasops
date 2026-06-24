import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const KPI_INTENT: Record<string, string> = {
  default: "text-primary bg-primary/10",
  success: "text-success bg-success/10",
  warning: "text-warning bg-warning/10",
  danger: "text-destructive bg-destructive/10",
};

export interface KpiProps {
  label: string;
  value: string;
  icon: LucideIcon;
  intent?: "default" | "success" | "warning" | "danger";
  sub?: string;
}

export function Kpi({ label, value, icon: Icon, intent = "default", sub }: KpiProps) {
  return (
    <Card className="p-4 transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <p className="section-label">{label}</p>
        <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", KPI_INTENT[intent])}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </Card>
  );
}
