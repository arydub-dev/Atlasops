/** Hosted public/authentication smoke checks. These do not verify provider checkout or signup. */
import { test, expect } from "@playwright/test";

const base = process.env.STAGING_BASE_URL || "";
const hasSecrets = Boolean(base);

test.describe("staging smoke", () => {
  test.skip(!hasSecrets, "STAGING_BASE_URL not configured");

  test("login page reachable on staging", async ({ page }) => {
    await page.goto(`${base}/login`);
    await expect(page.getByRole("button", { name: /^Continue$/i })).toBeVisible();
    await expect(page.getByLabel(/Work email/i)).toBeVisible();
  });

  test("unauthenticated mission-control redirects", async ({ page }) => {
    await page.goto(`${base}/mission-control`);
    await expect(page).toHaveURL(/login|onboarding|get-started/i, { timeout: 15_000 });
  });

  test("CSV import page requires session", async ({ page }) => {
    await page.goto(`${base}/data-sources/import`);
    await expect(page).toHaveURL(/\/login(?:\?|$)/, { timeout: 15_000 });
  });
});

/**
 * Full signup → checkout → Salesforce OAuth cannot be fully automated without
 * WorkOS/Stripe/Salesforce test credentials and mailbox access.
 * Operators should extend this file once STAGING_* secrets and MFA-bypass test
 * users are provisioned. Until then, API CI covers invite/CSV/token/isolation/logout
 * and Stripe webhook idempotency.
 */
