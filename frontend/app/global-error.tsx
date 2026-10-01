"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("global_error", error.digest || error.name);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
        <div className="space-y-4 text-center">
          <h2 className="text-xl font-semibold">Application error</h2>
          <p className="text-sm text-muted-foreground">
            An unexpected error occurred. Retry or reload the page.
          </p>
          <Button type="button" onClick={() => reset()}>
            Retry
          </Button>
        </div>
      </body>
    </html>
  );
}
