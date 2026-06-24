import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <p className="text-sm font-medium">Something went wrong</p>
      <p className="max-w-md text-xs text-muted-foreground">{message}</p>
    </Card>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  message = "No records match the current view.",
  icon: Icon = Inbox,
  action,
}: {
  title?: string;
  message?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <p className="text-sm font-medium">{title}</p>
      <p className="max-w-sm text-xs text-muted-foreground">{message}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

function Shimmer({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <Skeleton className={`shimmer ${className ?? ""}`} style={style} />;
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="p-5">
          <Shimmer className="h-3 w-20" />
          <Shimmer className="mt-3 h-7 w-16" />
          <Shimmer className="mt-4 h-3 w-24" />
        </Card>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <Card className="p-5">
      <Shimmer className="h-4 w-40" />
      <Shimmer className="mt-2 h-3 w-56" />
      <Shimmer className="mt-5 w-full" style={{ height }} />
    </Card>
  );
}

export function TableSkeleton({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-border p-4">
        <Shimmer className="h-4 w-40" />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex items-center gap-4 p-4">
            {Array.from({ length: cols }).map((_, c) => (
              <Shimmer key={c} className={`h-4 ${c === 0 ? "w-40" : "w-24"}`} />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

export function MissionSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Shimmer className="h-7 w-56" />
          <Shimmer className="h-3 w-80" />
        </div>
        <Shimmer className="h-24 w-44 rounded-xl" />
      </div>
      <CardGridSkeleton />
      <Shimmer className="h-40 w-full rounded-xl" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Shimmer className="h-72 w-full rounded-xl" />
        <Shimmer className="h-72 w-full rounded-xl" />
      </div>
    </div>
  );
}
