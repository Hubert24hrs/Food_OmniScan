import { expect, test } from "@playwright/test";

// Upgrade prompts, the plans page, the scanner's handling of non-product codes, and the store-required legal pages.
const password = "E2eTest" + "Pass1";

async function registerFree(page: import("@playwright/test").Page) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e-plan-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("checkbox", { name: /I agree/ }).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding/, { timeout: 20_000 });
}

test("free users see Go Premium everywhere and locked features lead to the plans", async ({ page }) => {
  await registerFree(page);
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Go Premium" })).toBeVisible();
  await expect(page.getByText("Get more with Premium")).toBeVisible();
  await expect(page.getByText(/\d+ of \d+ free .+ left this month/)).toBeVisible();

  await page.goto("/pantry");
  const unlock = page.getByRole("link", { name: "Unlock with Plus" });
  await expect(unlock).toBeVisible({ timeout: 20_000 });
  await unlock.click();
  await expect(page).toHaveURL(/\/subscription\?tier=plus/);
  await expect(page.getByRole("heading", { name: "Unlock the full Food omniScan" })).toBeVisible();
  await expect(page.getByText("Most popular")).toBeVisible();
  await expect(page.getByRole("button", { name: /Yearly · save \d+%/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Get Plus" })).toBeVisible();
  await expect(page.getByText("Your allowance this month")).toBeVisible();
});

test("a paid action sends people to the plans with the reason", async ({ page }) => {
  await registerFree(page);
  // The assistant in Pidgin is a Plus feature: asking in it is refused (402) and the app opens the plans.
  await page.goto("/assistant");
  await page.getByLabel("Answer language").selectOption({ index: 1 });
  await page.getByLabel("Your question").fill("Wetin dey inside indomie?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page).toHaveURL(/\/subscription\?.*tier=plus/, { timeout: 20_000 });
  await expect(page.getByRole("status").filter({ hasText: /included with Plus/i })).toBeVisible();
});

test("typed or pasted non-product codes are explained instead of looked up", async ({ page }) => {
  await page.goto("/scan");
  await page.getByRole("tab", { name: "Enter code" }).click();
  await page.getByLabel("Barcode number").fill("https://example.com/menu");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("This code is a link")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open link" })).toHaveAttribute("href", "https://example.com/menu");

  await page.getByLabel("Barcode number").fill("WIFI:T:WPA;S:Cafe;P:secret;;");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("Wi-Fi network")).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy password" })).toBeVisible();

  await page.getByLabel("Barcode number").fill("12345");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("Barcodes have 8, 12, 13 or 14 digits.")).toBeVisible();
  await expect(page).toHaveURL(/\/scan$/);
});

test("privacy, terms and account deletion pages are public", async ({ page }) => {
  for (const [path, heading] of [
    ["/privacy", "Privacy Policy"],
    ["/terms", "Terms of Service"],
    ["/account-deletion", "Delete your Food omniScan account"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
  }
});
