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
  await page.getByRole("button", { name: "Request enterprise access" }).click();
  await expect(page.getByRole("status")).toContainText("has been saved");
  await page.route("**/api/v1/leads", route => route.fulfill({ status: 503, json: { detail: "Not configured" } }));
  await page.getByRole("button", { name: "Request enterprise access" }).click();
  await expect(page.getByRole("status")).toContainText("not open yet");
});


test("company signup rejects personal email before redirect", async ({ page }) => {
  await page.goto("/login?signup=1");
  await page.getByLabel("Work email", { exact: true }).fill("person@gmail.com");
  await page.getByRole("button", { name: /^Continue$/ }).click();
  await expect(page.getByText(/Personal email addresses are not accepted for signup/)).toBeVisible();
  await expect(page).toHaveURL(/signup=1/);
});

test("features and search identity are discoverable", async ({ page, request }) => {
  await page.goto("/features");
  await expect(page.getByRole("heading", {name: "Shipment visibility"})).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://www.atlasops.online/features");
  expect((await request.get("/favicon.png")).status()).toBe(200);
  const sitemap = await request.get("/sitemap.xml");
  expect(await sitemap.text()).toContain("https://www.atlasops.online/contact");
});

// UI-only regression: mocked failure is not hosted authentication evidence.
test("private demo password visibility and authentication error", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({status:401,json:{detail:"Unauthorized"}}));
  await page.route("**/api/v1/auth/demo-login", route => route.fulfill({status:401,json:{detail:"Invalid demo credentials"}}));
  await page.goto("/demo-login");
  const password = page.getByLabel("Password", {exact:true});
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", {name:"Show password",exact:true}).click();
  await expect(password).toHaveAttribute("type", "text");
  await page.getByRole("button", {name:"Hide password",exact:true}).click();
  await expect(password).toHaveAttribute("type", "password");
  await page.getByLabel("Login ID").fill("synthetic-reviewer");
  await password.fill("synthetic-invalid-password");
  await page.getByRole("button", {name:"Open demo",exact:true}).click();
  await expect(page.locator("form").getByRole("alert")).toContainText("Invalid demo credentials");
  await expect(page.getByRole("button", {name:"Open demo",exact:true})).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
