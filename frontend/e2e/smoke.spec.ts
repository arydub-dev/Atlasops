import { test, expect } from "@playwright/test";

/**
 * Browser smoke + Ready UI paths.
 *
 * Full multi-step SaaS workflows that require WorkOS / Stripe / connector sandboxes
 * are covered at the API layer in `backend/tests/test_workflows_e2e.py` and
 * `backend/tests/test_stripe_webhooks.py` until staging secrets are wired into CI.
 */

test.describe("public surfaces", () => {
  test("marketing home loads with brand", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("login page is email-first with Continue", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Welcome back/i })).toBeVisible();
    await expect(page.getByLabel(/Work email/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /^Continue$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /WorkOS|Google|Microsoft|GitHub/i })).toHaveCount(
      0
    );
  });

  test("protected app route redirects unauthenticated users", async ({ page }) => {
    await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 401, json: { detail: "Unauthorized" } }));
    await page.goto("/mission-control");
    await expect(page).toHaveURL(/\/login(?:\?|$)/);
  });
});

test.describe("data sources import UI", () => {
  test("import page requires auth (no anonymous commit)", async ({ page }) => {
    await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 401, json: { detail: "Unauthorized" } }));
    await page.goto("/data-sources/import");
    await expect(page).toHaveURL(/\/login(?:\?|$)/);
  });
});


test("demo inquiry has clear success and failure states", async ({ page }) => {
  await page.route("**/api/v1/leads", route => route.fulfill({ status: 202, json: { accepted: true } }));
  await page.goto("/contact");
  await page.getByLabel("Your name", { exact: true }).fill("Pilot User");
  await page.getByLabel("Work email", { exact: true }).fill("pilot@example.com");
  await page.getByLabel("Company", { exact: true }).fill("Example");
  await page.getByLabel("Role", { exact: true }).fill("Planner");
  await page.getByLabel("Company size", { exact: true }).fill("20");
  await page.getByLabel("What is your main operational challenge?").fill("Inventory shortages across warehouses");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Request a demo" }).click();
  await expect(page.getByRole("status")).toContainText("has been saved");
  await page.route("**/api/v1/leads", route => route.fulfill({ status: 503, json: { detail: "Not configured" } }));
  await page.getByRole("button", { name: "Request a demo" }).click();
  await expect(page.getByRole("status")).toContainText("not open yet");
});
