import AxeBuilder from "@axe-core/playwright";
import { type Browser, expect, type Page, test } from "@playwright/test";

import { startDemoLearner, typeCode, WRONG_GREET } from "./helpers";

async function audit(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
  expect.soft(summary, `${label} accessibility violations`).toEqual([]);
}

/** Light is the default, so the dark theme has to be chosen rather than inherited from the system. */
async function contextWithTheme(browser: Browser, theme: "light" | "dark") {
  const context = await browser.newContext({ colorScheme: theme, viewport: { width: 1440, height: 900 } });
  await context.addInitScript((choice) => localStorage.setItem("codepath.theme", choice), theme);
  return context;
}

for (const scheme of ["light", "dark"] as const) {
  test(`main screens pass automated accessibility checks in ${scheme} theme`, async ({ browser }) => {
    test.setTimeout(240_000);
    const context = await contextWithTheme(browser, scheme);
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
    await page.goto("/path/arrays-two-pointers");
    await page.getByTestId("before-you-start").waitFor();
    await audit(page, "topic lesson");
    await page.getByTestId("tryit-run").first().click();
    await page.getByTestId("tryit-output").first().waitFor();
    await page.getByTestId("tryit-edit").first().click();
    await audit(page, "topic lesson with a run example");
    await page.getByTestId("tab-practice").click();
    await page.getByTestId("problem-row").first().waitFor();
    await audit(page, "topic practice");
    await page.goto("/problems/say-hello");
    await page.locator(".cm-content").waitFor();
    await audit(page, "workspace");
    await typeCode(page, WRONG_GREET);
    await page.getByTestId("submit").click();
    await page.getByTestId("hint").waitFor();
    await audit(page, "workspace with results");
    await page.getByTestId("ask-input").fill("why does it fail?");
    await page.getByTestId("ask-send").click();
    await page.getByTestId("asked").waitFor();
    await page.getByTestId("tutor-working").waitFor({ state: "detached" });
    await audit(page, "tutor answer to a question");
    await page.getByTestId("tab-learn").click();
    await page.getByTestId("learn-understand").waitFor();
    await audit(page, "learn panel");
    await page.getByTestId("tab-history").click();
    await page.getByTestId("submission").first().waitFor();
    await page.getByTestId("submission").first().getByRole("button").first().click();
    await audit(page, "submission history");
    await page.getByTestId("view-cases").click();
    await page.getByTestId("add-case").click();
    await audit(page, "test cases");
    await page.goto("/search?q=recursion");
    await page.getByTestId("search-topic").first().waitFor();
    await audit(page, "search results");
    await page.goto("/progress");
    await page.getByTestId("stats").waitFor();
    await audit(page, "progress");
    await page.goto("/profile");
    await page.getByTestId("state-matrix").waitFor();
    await audit(page, "profile");
    await page.goto("/settings");
    await page.getByRole("heading", { name: "Settings" }).waitFor();
    await audit(page, "settings");
    await page.goto("/problems/new");
    await page.getByTestId("method-paste").waitFor();
    await audit(page, "add question");
    await page.getByTestId("previous-toggle").click();
    await page.getByTestId("your-questions").locator("[data-state=open]").first().waitFor();
    await audit(page, "add question with previous questions open");
    await context.close();
  });
}

test("teacher dashboard passes automated accessibility checks", async ({ browser }) => {
  for (const scheme of ["light", "dark"] as const) {
    const context = await contextWithTheme(browser, scheme);
    const page = await context.newPage();
    await page.goto("/welcome");
    await page.getByTestId("demo-teacher").click();
    await page.getByTestId("learners-table").waitFor();
    await audit(page, `teacher ${scheme}`);
    await page.getByTestId("learners-table").getByRole("rowheader").first().getByRole("link").click();
    await page.getByTestId("profile-stats").waitFor();
    await audit(page, `teacher student profile ${scheme}`);
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

test("new tutor and import states pass automated accessibility checks in both themes", async ({ browser }) => {
  for (const scheme of ["light", "dark"] as const) {
    const context = await contextWithTheme(browser, scheme);
    const page = await context.newPage();
    await startDemoLearner(page);
    await page.goto("/problems/sum-to-n");
    await typeCode(page, "def sum_to_n(n):\n    total = 0\n    x = = 1\n    return total\n");
    for (let number = 1; number <= 5; number += 1) {
      await page.getByTestId("ask-hint").click();
      await expect(page.getByTestId("hint-number")).toContainText(`Hint ${number} on this issue`);
    }
    await page.getByRole("button", { name: "Why this hint?" }).click();
    await audit(page, `worked example with evidence, ${scheme}`);
    await page.getByTestId("ask-hint").click();
    await page.getByTestId("hint-waiting").waitFor();
    await audit(page, `waiting for a code change, ${scheme}`);
    await typeCode(page, "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n");
    await page.getByTestId("ask-after-change").click();
    await page.getByTestId("progress-note").waitFor();
    await audit(page, `progress acknowledged, ${scheme}`);
    await page.goto("/problems/new");
    await page.getByTestId("method-link").click();
    await page.getByTestId("link-input").fill("https://leetcode.com/problems/two-sum/");
    await page.getByTestId("lookup").click();
    await page.getByTestId("lookup-result").waitFor();
    await page.waitForTimeout(400); // the button's colour transition must finish, or the contrast check reads a mid-animation colour
    await audit(page, `link result, ${scheme}`);
    await page.getByTestId("continue-paste").click();
    await page.getByTestId("optional-details").click();
    await page.getByTestId("paste-source").waitFor();
    await audit(page, `paste with optional details, ${scheme}`);
    await page.goto("/path");
    await page.getByTestId("path-position").waitFor();
    await audit(page, `learning path, ${scheme}`);
    await context.close();
  }
});
