import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { startDemoLearner, typeCode, WRONG_GREET } from "./helpers";

async function audit(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
  expect.soft(summary, `${label} accessibility violations`).toEqual([]);
}

for (const scheme of ["light", "dark"] as const) {
  test(`main screens pass automated accessibility checks in ${scheme} theme`, async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: scheme, viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto("/welcome");
    await page.getByRole("heading", { name: "Sign in" }).waitFor();
    await audit(page, "welcome");
    await page.getByTestId("demo-student").click();
    await page.getByTestId("finish-onboarding").waitFor();
    await audit(page, "onboarding");
    await page.getByTestId("finish-onboarding").click();
    await page.getByTestId("recommendation").waitFor();
    await audit(page, "home");
    await page.goto("/problems");
    await page.getByTestId("problem-row").first().waitFor();
    await audit(page, "library");
    await page.goto("/path");
    await page.getByTestId("path-unit").first().waitFor();
    await audit(page, "path");
    await page.goto("/problems/say-hello");
    await page.locator(".cm-content").waitFor();
    await audit(page, "workspace");
    await typeCode(page, WRONG_GREET);
    await page.getByTestId("submit").click();
    await page.getByTestId("hint").waitFor();
    await audit(page, "workspace with results");
    await page.goto("/progress");
    await page.getByTestId("stats").waitFor();
    await audit(page, "progress");
    await page.goto("/settings");
    await page.getByRole("heading", { name: "Settings" }).waitFor();
    await audit(page, "settings");
    await page.goto("/problems/new");
    await page.getByTestId("method-paste").waitFor();
    await audit(page, "add question");
    await context.close();
  });
}

test("teacher dashboard passes automated accessibility checks", async ({ browser }) => {
  for (const scheme of ["light", "dark"] as const) {
    const context = await browser.newContext({ colorScheme: scheme, viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto("/welcome");
    await page.getByTestId("demo-teacher").click();
    await page.getByTestId("learners-table").waitFor();
    await audit(page, `teacher ${scheme}`);
    await context.close();
  }
});

test("demo login needs no secret, and workspace works after theme change", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/say-hello");
  await page.locator(".cm-content").waitFor();
  await page.getByRole("button", { name: /Switch to (light|dark) theme/ }).click();
  await expect(page.locator(".cm-content")).toBeVisible();
});
