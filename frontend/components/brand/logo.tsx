import Link from "next/link";
import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "relative flex items-center justify-center rounded-[10px] bg-gradient-to-br from-primary to-blue-700 text-primary-foreground shadow-sm",
        className,
      )}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="h-[58%] w-[58%]"
        aria-hidden="true"
      >
        {/* Stylised "A" / orbital atlas mark */}
        <path
          d="M12 3 L20 19 H15.5 L12 11 L8.5 19 H4 Z"
          fill="currentColor"
          opacity="0.95"
        />
        <circle
          cx="12"
          cy="12"
          r="9.2"
          stroke="currentColor"
          strokeWidth="1.1"
          opacity="0.45"
        />
      </svg>
    </span>
  );
}

export function Logo({
  className,
  textClassName,
  href = "/",
}: {
  className?: string;
  textClassName?: string;
  href?: string | null;
}) {
  const content = (
    <span className={cn("flex items-center gap-2.5", className)}>
      <LogoMark className="h-8 w-8" />
      <span
        className={cn(
          "text-[17px] font-semibold tracking-tight text-foreground",
          textClassName,
        )}
      >
        ATLAS<span className="text-primary">OPS</span>
      </span>
    </span>
  );

  if (href === null) return content;
  return (
    <Link href={href} className="inline-flex">
      {content}
    </Link>
  );
}
