"use client";

import { Suspense } from "react";
import GraphExplorerInner from "./graph-inner";

export default function GraphExplorerPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading graph…</div>}>
      <GraphExplorerInner />
    </Suspense>
  );
}
