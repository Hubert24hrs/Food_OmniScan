import { expect, test } from "@playwright/test";

// Core user journeys. The API is real; Open Food Facts lookups go to the live service, so the
// barcode used here is a long-standing, well-populated record (Nutella 400 g).
const BARCODE = "3017620422003";
const password = "E2eTest" + "Pass1";

test("visitor can scan a barcode by number and see an explained score", async ({ page }) => {
  await page.goto("/scan");
  await page.getByRole("tab", { name: "Enter code" }).click();
  await page.getByLabel("Barcode number").fill(BARCODE);
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page).toHaveURL(/\/product\//, { timeout: 30_000 });
  await expect(page.getByRole("img", { name: /Score \d+ out of 100/ })).toBeVisible();
  await expect(page.getByText("Nutrition Facts").first()).toBeVisible();
  await expect(page.getByText(/Daily Value/).first()).toBeVisible();
});

test("invalid barcode shows a clear error", async ({ page }) => {
  await page.goto("/scan/3017620422004");
  await expect(page.getByRole("alert").filter({ hasText: "Something went wrong" })).toContainText(/check digit/i);
});

test("user registers, sets an allergy and gets a critical allergen alert", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("checkbox", { name: /I agree/ }).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding/, { timeout: 20_000 });
  await page.getByRole("button", { name: "Tree nuts" }).click();
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page).toHaveURL(/\/scan/, { timeout: 20_000 });

  await page.goto(`/scan/${BARCODE}`);
  await expect(page).toHaveURL(/\/product\//, { timeout: 30_000 });
  await expect(page.getByRole("alert").filter({ hasText: "Allergen alert" })).toContainText(/tree nuts/i);

  await page.goto("/history");
  await expect(page.getByRole("link", { name: /Nutella/i })).toBeVisible();
});

test("ingredient encyclopedia uses US names", async ({ page }) => {
  await page.goto("/ingredients");
  await page.getByLabel("Search ingredients").fill("red 40");
  await expect(page.getByRole("link", { name: /Red 40/ })).toBeVisible();
  await page.getByRole("link", { name: /Red 40/ }).click();
  await expect(page.getByText(/may have an adverse effect on activity and attention/).first()).toBeVisible();
});
