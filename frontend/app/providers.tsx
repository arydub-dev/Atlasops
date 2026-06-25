"use client";

import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth";
import { DemoModeProvider } from "@/lib/demo-mode";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <AuthProvider>
        <DemoModeProvider>{children}</DemoModeProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
