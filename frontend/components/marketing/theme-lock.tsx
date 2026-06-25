"use client";

import { useEffect } from "react";
import { useTheme } from "next-themes";

/**
 * The public marketing site is always presented in the light theme,
 * regardless of any theme the visitor selected inside the application.
 */
export function MarketingThemeLock() {
  const { setTheme } = useTheme();
  useEffect(() => {
    setTheme("light");
  }, [setTheme]);
  return null;
}
