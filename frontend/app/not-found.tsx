import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 px-6 text-center">
      <h2 className="text-xl font-semibold">Page not found</h2>
      <p className="text-sm text-muted-foreground">
        That route does not exist in ATLASOPS.
      </p>
      <Link href="/mission-control" className="text-sm font-medium text-primary underline">
        Back to Mission Control
      </Link>
    </div>
  );
}
