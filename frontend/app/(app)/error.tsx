"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Avoid dumping raw exception text to the console in production UIs.
    console.error("app_route_error", error.digest || error.name);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold tracking-tight">Something went wrong</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          This page failed to load. Your session may still be valid — retry, or return to
          Mission Control.
        </p>
        {error.digest ? (
          <p className="font-mono text-xs text-muted-foreground">Ref: {error.digest}</p>
        ) : null}
      </div>
      <div className="flex gap-2">
        <Button type="button" onClick={() => reset()}>
          Retry
        </Button>
        <Button type="button" variant="outline" asChild>
          <Link href="/mission-control">Mission Control</Link>
        </Button>
      </div>
    </div>
  );
}
