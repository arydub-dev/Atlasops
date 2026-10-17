"use client";

import { usePathname } from "next/navigation";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth";
import { DemoModeProvider } from "@/lib/demo-mode";

export function Providers({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  if (path === "/demo" || path.startsWith("/demo/")) return <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>{children}</ThemeProvider>;
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <AuthProvider>
        <DemoModeProvider>{children}</DemoModeProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
