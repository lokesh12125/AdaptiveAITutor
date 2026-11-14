import { expect, type Page, test } from "@playwright/test";

import { editorText, expectNoHorizontalOverflow, register, RIGHT_GREET, startDemoLearner, teacherInvite, typeCode, uniqueEmail, WRONG_GREET } from "./helpers";

test.describe("sign-in and roles", () => {
  test("real accounts work, and bad passwords get a clear message", async ({ page }) => {
    const email = uniqueEmail();
    await register(page, "Asha Learner", email, "a long enough password");
    await expect(page).toHaveURL(/onboarding/);
    await page.getByTestId("level-new").click();
    await page.getByTestId("finish-onboarding").click();
    await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/welcome/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("the wrong password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("do not match");
    await page.getByLabel("Password").fill("a long enough password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByTestId("recommendation")).toBeVisible();
    await expect(page.getByText("Demo session")).toHaveCount(0);
  });

  test("demo access is labelled as not secure", async ({ page }) => {
    await page.goto("/welcome");
    await expect(page.getByText("not a secure account")).toBeVisible();
    await page.getByTestId("demo-student").click();
    await expect(page.getByRole("status").filter({ hasText: "Demo session" })).toContainText("not a secure account");
  });

  test("a student cannot open the teacher pages", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/teacher");
    await expect(page.getByText("This page is only for teachers")).toBeVisible();
    const status = await page.evaluate(async () => (await fetch("/api/teacher/classes")).status);
    expect(status).toBe(403);
  });

  test("signed-out visitors are sent to sign in", async ({ page }) => {
    await page.goto("/progress");
    await expect(page).toHaveURL(/welcome/);
  });
});

test("beginner path: recommended exercise, wrong attempt, hint, right attempt, reflection", async ({ page }) => {
  await startDemoLearner(page);
  await expect(page.getByTestId("recommendation")).toContainText("Say Hello");
  await page.getByTestId("recommended-start").click();
  await expect(page.getByTestId("walkthrough")).toBeVisible();

  await typeCode(page, WRONG_GREET);
  await page.getByTestId("run").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "wrong_answer");
  await expect(page.getByTestId("results-pane")).toContainText("Hello, Ada!");

  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", /wrong_answer|partial/);
  await expect(page.getByTestId("next-action")).toBeVisible();
  const hint = page.getByTestId("hint");
  await expect(hint).toBeVisible();
  await page.getByRole("button", { name: "Why this hint?" }).click();
  await expect(page.getByTestId("hint-why")).not.toBeEmpty();

  await typeCode(page, RIGHT_GREET);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");
  await expect(page.getByTestId("plan")).toBeVisible();
  await expect(page.getByTestId("plan")).toContainText(/Next|try|Try/);
  await expect(page.getByText("Solved", { exact: true })).toBeVisible();

  const reflection = page.getByTestId("reflection");
  await expect(reflection).toBeVisible();
  await reflection.getByRole("textbox").fill("It builds the text from the name.");
  await reflection.getByRole("button", { name: "Save answer" }).click();
  // The tutor replies to what the learner wrote, then the learner closes the card.
  await expect(page.getByTestId("reflection-reply")).not.toBeEmpty();
  await page.getByTestId("reflection-done").click();
  await expect(reflection).toHaveCount(0);

  await page.goto("/progress");
  await expect(page.getByTestId("stats")).toContainText("Problems solved");
  await expect(page.getByTestId("topic-row").first()).toContainText("Python basics");
  await expect(page.getByText("It builds the text from the name.")).toBeVisible();
});

test("Run, Submit and Hint are separate: hints and runs are not graded attempts", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await page.getByTestId("run").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint")).toBeVisible();
  const metrics = await page.evaluate(async () => (await (await fetch("/api/progress")).json()).metrics);
  expect(metrics.graded_attempts).toBe(0);
  expect(metrics.submitted).toBe(0);
  expect(metrics.started, "working on a problem starts it, even without submitting").toBe(1);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", /wrong_answer|partial/);
  const after = await page.evaluate(async () => (await (await fetch("/api/progress")).json()).metrics);
  expect(after.graded_attempts).toBe(1);
});

test("repeated errors: after the first hint, help is offered, and asking climbs one step at a time", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  const levels: number[] = [];
  for (let attempt = 0; attempt < 3; attempt++) {
    await typeCode(page, `def sum_to_n(n):\n    return sum(range(1, n))  # attempt ${attempt}`);
    await page.getByTestId("submit").click();
    await expect(page.getByTestId("running")).toHaveCount(0, { timeout: 30_000 });
    await expect(page.getByTestId("verdict")).toBeVisible();
    if (attempt > 0) {
      // The same issue again, without asking: the next hint is offered, not shown, so the learner tries their own idea first.
      const offer = page.getByTestId("offer");
      await expect(offer).toBeVisible();
      await expect(page.getByTestId("hint")).toHaveCount(0);
      await offer.getByRole("button", { name: "Get a hint" }).click();
    }
    await expect(page.getByTestId("hint")).toBeVisible();
    levels.push(Number(await page.getByTestId("hint").getAttribute("data-level")));
    await page.waitForTimeout(300);
    expect(Number(await page.getByTestId("hint").getAttribute("data-level")), "no new hint appears on its own").toBe(levels[levels.length - 1]);
  }
  expect(levels).toEqual([...levels].sort((a, b) => a - b));
  expect(levels.every((level, i) => i === 0 || level - levels[i - 1] <= 1), `one step at a time: ${levels}`).toBe(true);
  expect(levels[levels.length - 1]).toBeGreaterThan(levels[0]);
  await expect(page.getByTestId("hint")).not.toContainText("def sum_to_n");
});

test.describe("editor", () => {
  test("drafts survive a refresh and a reset needs confirmation", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await typeCode(page, "# my draft line\ndef greet(name):\n    pass");
    await expect(page.getByTestId("save-status")).toHaveAttribute("data-state", "saved", { timeout: 10_000 });
    await page.reload();
    await expect(page.getByTestId("restored-note")).toBeVisible();
    expect(await editorText(page)).toContain("# my draft line");

    await page.getByTestId("reset").click();
    await expect(page.getByRole("alertdialog")).toContainText("cannot be recovered");
    await page.getByRole("button", { name: "Cancel" }).click();
    expect(await editorText(page)).toContain("# my draft line");
    await page.getByTestId("reset").click();
    await page.getByRole("button", { name: "Reset code" }).click();
    await expect.poll(() => editorText(page)).not.toContain("# my draft line");
    await page.reload();
    await expect(page.locator(".cm-content")).toContainText("Return the greeting");
  });

  test("results are labelled when the code has changed since they ran", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await page.getByTestId("run").click();
    await expect(page.getByTestId("verdict")).toBeVisible();
    await expect(page.getByTestId("stale-result")).toHaveCount(0);
    await page.locator(".cm-content").click();
    await page.keyboard.type("x");
    await expect(page.getByTestId("stale-result")).toContainText("earlier version");
  });

  test("the editor behaves like a code editor", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await expect(page.locator(".cm-lineNumbers")).toBeVisible();
    await expect(page.locator(".tok-keyword").first()).toHaveText("def");
    await typeCode(page, "");
    await page.keyboard.type("def f(");
    expect(await editorText(page), "brackets close themselves").toContain("def f()");
    await page.keyboard.press("End");
    await page.keyboard.type(":");
    await page.keyboard.press("Enter");
    const text = await editorText(page);
    expect(text.split("\n")[1]?.length ?? 0, "a new block is indented").toBeGreaterThan(0);
  });

  test("font size persists across sessions through settings", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    const size = () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--editor-font-size").trim());
    await expect.poll(size).toBe("14px");
    await page.getByTestId("font-larger").click();
    await expect.poll(size).toBe("15px");
    await page.reload();
    await expect(page.locator(".cm-content")).toBeVisible();
    await expect.poll(size).toBe("15px");
  });
});

test.describe("failure recovery", () => {
  test("a connection failure keeps the code, and retrying does not duplicate the attempt", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await typeCode(page, WRONG_GREET);
    let blocked = true;
    const keys: string[] = [];
    await page.route("**/api/problems/say-hello/submit", async (route) => {
      keys.push(route.request().postDataJSON().idempotency_key);
      if (blocked) {
        blocked = false;
        await route.abort("connectionfailed");
      } else {
        await route.continue();
      }
    });
    await page.getByTestId("submit").click();
    await expect(page.getByTestId("start-error")).toContainText("Your code is safe");
    expect(await editorText(page)).toContain("Hello ");
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", /wrong_answer|partial/);
    expect(keys.length).toBe(2);
    expect(keys[0], "the retry reuses the same key").toBe(keys[1]);
  });

  test("failing to save a draft is visible and retryable", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    let fail = true;
    await page.route("**/api/problems/say-hello/draft", async (route) => {
      if (fail) await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: { code: "x", message: "x" } }) });
      else await route.continue();
    });
    await typeCode(page, "# save me");
    await expect(page.getByTestId("save-status")).toHaveAttribute("data-state", "failed", { timeout: 10_000 });
    await expect(page.getByTestId("save-status")).toContainText("safe in this browser");
    fail = false;
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(page.getByTestId("save-status")).toHaveAttribute("data-state", "saved");
  });

  test("a service problem is not shown as a learner mistake", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await page.route("**/api/problems/say-hello/run", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "server_error", message: "Something went wrong on our side." } }) }));
    await page.getByTestId("run").click();
    await expect(page.getByTestId("start-error")).toContainText("on our side");
    await expect(page.getByTestId("verdict")).toHaveCount(0);
  });
});

test.describe("library and path", () => {
  test("search, filters and Python-only language display", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/problems");
    await expect(page.getByTestId("problem-row").first()).toBeVisible();
    await expect(page.getByText("JavaScript")).toHaveCount(0);
    await page.getByTestId("search").fill("linked");
    await expect(page.getByTestId("problem-row").first()).toContainText(/Linked List/i);
    await page.getByTestId("search").fill("zzzzzz");
    await expect(page.getByText("No problems match")).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await page.getByRole("combobox", { name: "Filter by difficulty" }).click();
    await page.getByRole("option", { name: "Hard" }).click();
    await expect(page).toHaveURL(/difficulty=hard/);
    for (const row of await page.getByTestId("problem-row").all()) await expect(row).toContainText("Hard");
  });

  test("the path recommends, explains, and leaves every topic open", async ({ page }) => {
    await startDemoLearner(page);
    await page.goto("/path");
    await expect(page.getByTestId("path-recommendation")).toContainText("first exercise");
    await expect(page.getByTestId("path-unit")).toHaveCount(17);
    await page.getByRole("link", { name: /Dynamic programming/ }).click();
    await expect(page.getByRole("heading", { name: "Dynamic programming", level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Key ideas" })).toBeVisible();
    await page.getByTestId("tab-practice").click();
    await expect(page.getByTestId("problem-row").first()).toBeVisible();
    await page.getByTestId("problem-row").first().click();
    await expect(page.locator(".cm-content")).toBeVisible();
  });

  test("an experienced learner can skip the introductions", async ({ page }) => {
    await page.goto("/welcome");
    await page.getByTestId("demo-student").click();
    await page.getByTestId("level-advanced").click();
    await page.getByTestId("goal-dsa").click();
    await page.getByTestId("finish-onboarding").click();
    await expect(page.getByTestId("recommendation")).not.toContainText("Say Hello");
    await page.goto("/problems/fizz-word");
    await expect(page.locator(".cm-content")).toBeVisible();
    await expect(page.getByTestId("walkthrough")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.dataset.density)).toBe("compact");
  });
});

test("Add Question: paste, review, generated tests, practise, edit, delete", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems");
  await page.getByTestId("add-question").click();
  await page.getByTestId("method-paste").click();
  await page.getByTestId("paste-text").fill(`Two Sum Practice
Easy
Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.

Example 1:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]

Example 2:
Input: nums = [3,2,4], target = 6
Output: [1,2]

Constraints:
2 <= nums.length <= 500
-100 <= nums[i] <= 100
`);
  await page.getByTestId("parse").click();
  await expect(page.getByTestId("draft-title")).toHaveValue("Two Sum Practice");
  await expect(page.getByTestId("draft-function")).toHaveValue("two_sum_practice");
  await page.getByTestId("draft-function").fill("two_sum");
  await page.getByTestId("to-tests").click();

  await expect(page.getByText("not the original platform's hidden tests")).toBeVisible();
  const cards = page.getByTestId("test-card");
  await expect(page.getByTestId("test-purpose").first(), "each generated test says what it checks").toBeVisible();
  await expect(cards.filter({ hasText: "Imported example" })).toHaveCount(2);
  await expect(cards.filter({ hasText: "Generated" }).first()).toBeVisible();
  await expect(page.getByTestId("needs-expected").first()).toBeVisible();
  const pending = cards.nth(2); // the first generated test, after the two pasted examples
  await expect(pending.getByTestId("needs-expected")).toBeVisible();
  await pending.getByTestId("expected-input").fill("[0, 1]");
  await expect(pending.getByTestId("needs-expected")).toHaveCount(0);
  await pending.getByRole("textbox").first().fill("[[1, 2], 3]");
  await page.getByTestId("add-test").click();
  await page.getByTestId("save-question").click();

  await expect(page.locator(".cm-content")).toContainText("def two_sum(nums, target)");
  await expect(page.getByText("Added by you")).toBeVisible();
  await typeCode(page, "def two_sum(nums, target):\n    return [0, 0]");
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  await expect(page.getByTestId("hint")).toBeVisible();

  await typeCode(page, "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i");
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");
  await expect(page.getByTestId("verdict")).toContainText("not the original platform's official test suite");

  await page.getByRole("tab", { name: "Problem" }).click();
  await page.getByRole("link", { name: "Edit" }).click();
  await expect(page.getByTestId("draft-title")).toHaveValue("Two Sum Practice");
  await page.getByTestId("draft-title").fill("Two Sum Renamed");
  await page.getByTestId("save-edit").click();
  await expect(page.getByRole("heading", { name: "Two Sum Renamed" })).toBeVisible();

  // The learner's own questions are listed apart, on Practice and on Add question.
  const questionUrl = page.url();
  await page.goto("/problems");
  const group = page.getByTestId("your-questions-group");
  await expect(group).toHaveAttribute("data-open", "true");
  await expect(group.getByTestId("problem-row")).toHaveCount(1);
  await expect(group.getByTestId("problem-row")).toContainText("Two Sum Renamed");
  await page.goto("/problems/new");
  // Importing comes first. Earlier questions sit below it, closed until asked for.
  await expect(page.getByTestId("method-paste")).toBeVisible();
  const importFirst = await page.evaluate(() => {
    const method = document.querySelector("[data-testid=method-paste]");
    const previous = document.querySelector("[data-testid=your-questions]");
    return !!method && !!previous && (method.compareDocumentPosition(previous) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
  });
  expect(importFirst, "the previous questions come after the import options").toBe(true);
  const toggle = page.getByTestId("previous-toggle");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(toggle).toContainText("Previously added questions (1)");
  await expect(page.getByTestId("your-question"), "closed by default").toHaveCount(0);
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  const listed = page.getByTestId("your-question");
  await expect(listed).toHaveCount(1);
  await expect(listed).toContainText("Two Sum Renamed");
  await expect(listed).toContainText("added");
  await expect(page.getByTestId("your-questions")).toContainText("1 solved");
  // The choice is kept while moving around the site, and Space closes it again.
  await page.goto("/problems");
  await page.goto("/problems/new");
  await expect(page.getByTestId("previous-toggle")).toHaveAttribute("aria-expanded", "true");
  await page.getByTestId("previous-toggle").press("Space");
  await expect(page.getByTestId("your-question")).toHaveCount(0);
  await page.goto(questionUrl);

  await page.getByRole("link", { name: "Edit" }).click();
  await page.getByTestId("delete-question").click();
  await page.getByRole("button", { name: "Delete question" }).click();
  await expect(page).toHaveURL(/\/problems$/);
  await page.getByTestId("search").fill("Two Sum Renamed");
  await expect(page.getByText("No problems match")).toBeVisible();
});

test("Add Question: unsupported links explain why and lead to pasting", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/new");
  await page.getByTestId("method-link").click();
  await page.getByTestId("link-input").fill("https://leetcode.com/problems/two-sum/");
  await page.getByTestId("lookup").click();
  await expect(page.getByTestId("lookup-result")).toHaveAttribute("data-status", "url_only");
  await expect(page.getByText("does not scrape")).toBeVisible();
  await expect(page.getByTestId("lookup-result")).toContainText("Still needed");
  await page.getByTestId("continue-paste").click();
  await expect(page.getByText("Source saved: Two sum")).toBeVisible();
  await expect(page.getByTestId("paste-text")).toBeVisible();
});

test("Add Question: a supported link imports metadata, shows its source, and asks for the statement", async ({ page }) => {
  await startDemoLearner(page);
  await page.route("**/api/imports/lookup", (route) =>
    route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        supported: true, status: "metadata_only", access: "official_api", extracted_fields: ["title", "tags"], missing_fields: ["description", "examples"], source_name: "Codeforces", message: "Found it. The statement is not available through the API, so please paste that in the next step.", guidance: null,
        draft: { title: "Two Vessels", description: "", difficulty: "easy", tags: ["math"], unit_id: "loops", mode: "stdio", source_name: "Codeforces", source_url: "https://codeforces.com/problemset/problem/1872/A", source_retrieved_at: new Date().toISOString(), missing_fields: ["description", "constraints", "examples"], warnings: [], examples: [], parameters: [] },
      }),
    }),
  );
  await page.goto("/problems/new");
  await page.getByTestId("method-link").click();
  await page.getByTestId("link-input").fill("1872A");
  await page.getByTestId("lookup").click();
  await expect(page.getByText("Found: Two Vessels")).toBeVisible();
  await page.getByTestId("continue-paste").click();
  await page.getByTestId("paste-text").fill("Two Vessels\nRead two numbers and print how many moves make them equal.\n\nSample Input 1\n1 3\nSample Output 1\n1\n");
  await page.getByTestId("parse").click();
  await expect(page.getByText("Source: Codeforces, https://codeforces.com/problemset/problem/1872/A")).toBeVisible();
  await page.getByTestId("to-tests").click();
  await expect(page.getByTestId("test-card").first()).toContainText("Imported example");
  await page.getByTestId("save-question").click();
  await expect(page.locator(".cm-content")).toBeVisible();
  await expect(page.getByText(/Source: Codeforces/)).toBeVisible();
  await expect(page.getByRole("link", { name: /View the original/ })).toHaveAttribute("href", /codeforces\.com/);
});

test("copy controls and lost connections are handled", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await startDemoLearner(page);
  await page.goto("/problems/say-hello");
  await page.getByRole("button", { name: "Copy this input" }).first().click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain("greet(");

  await page.route("**/api/evaluations/**", (route) => route.abort("connectionfailed"));
  await page.getByTestId("run").click();
  await expect(page.getByTestId("reconnecting")).toBeVisible({ timeout: 30_000 });
  await page.unroute("**/api/evaluations/**");
  await expect(page.getByTestId("verdict")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("reconnecting")).toHaveCount(0);
});

test.describe("appearance", () => {
  test("the theme is light at first, even on a dark system, then persists when chosen", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark" });
    const page = await context.newPage();
    await page.goto("/welcome");
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe("light");
    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
    await page.reload();
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
    await context.close();
  });

  test("reduced motion is respected", async ({ browser }) => {
    const context = await browser.newContext({ reducedMotion: "reduce" });
    const page = await context.newPage();
    await page.goto("/welcome");
    const duration = await page.evaluate(() => {
      const probe = document.createElement("div");
      probe.className = "spinner";
      document.body.append(probe);
      return getComputedStyle(probe).animationDuration;
    });
    expect(parseFloat(duration)).toBeLessThan(0.01);
    await context.close();
  });
});

test("keyboard: skip link, shortcuts, leaving the editor", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();

  await page.goto("/problems/say-hello");
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+Enter");
  await expect(page.getByTestId("verdict")).toBeVisible();
  await page.locator(".cm-content").click();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("run")).toBeFocused();
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const separator = page.getByRole("separator").first();
  await separator.focus();
  const before = await page.locator('[data-panel-id="side"]').evaluate((el) => el.getBoundingClientRect().width);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const after = await page.locator('[data-panel-id="side"]').evaluate((el) => el.getBoundingClientRect().width);
  expect(after, "panels can be resized by keyboard").toBeGreaterThan(before);
});

test.describe("responsive", () => {
  test("phone: workspace uses tabs, and no page scrolls sideways", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 780 }, hasTouch: true });
    const page = await context.newPage();
    await startDemoLearner(page);
    await expectNoHorizontalOverflow(page);
    for (const path of ["/path", "/problems", "/progress", "/settings", "/problems/new"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoHorizontalOverflow(page);
    }
    await expect(page.getByRole("navigation", { name: "Main, mobile" })).toBeVisible();
    await page.goto("/problems/say-hello");
    await expect(page.getByRole("tab", { name: "Code" })).toHaveAttribute("aria-selected", "true");
    await typeCode(page, WRONG_GREET);
    await page.getByTestId("submit").click();
    await expect(page.getByRole("tab", { name: "Results" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("verdict")).toBeVisible();
    await page.getByRole("tab", { name: /Tutor/ }).click();
    await expect(page.getByTestId("hint")).toBeVisible();
    await page.getByRole("tab", { name: "Code" }).click();
    expect(await editorText(page), "code survives tab changes").toContain("Hello ");
    await expectNoHorizontalOverflow(page);
    await context.close();
  });

  test("tablet: two columns", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 900, height: 1100 } });
    const page = await context.newPage();
    await startDemoLearner(page);
    await page.goto("/problems/say-hello");
    await expect(page.getByRole("tab", { name: "Problem" })).toBeVisible();
    await expect(page.locator(".cm-content")).toBeVisible();
    await expect(page.getByTestId("results-pane")).toBeVisible();
    await page.getByTestId("ask-hint").click();
    await expect(page.getByTestId("hint")).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await context.close();
  });
});

test("class flow: a student's numbers match the teacher's, and access needs joining", async ({ browser }) => {
  const teacherContext = await browser.newContext();
  const teacher = await teacherContext.newPage();
  await register(teacher, "Ms Rao", uniqueEmail("teacher"), "a long enough password", teacherInvite());
  await expect(teacher).toHaveURL(/teacher/);
  await teacher.getByTestId("new-class").click();
  await teacher.getByTestId("class-name").fill("Python 101");
  await teacher.getByTestId("create-class").click();
  const code = (await teacher.getByTestId("join-code").innerText()).trim();

  const studentContext = await browser.newContext();
  const student = await studentContext.newPage();
  await register(student, "Dev Student", uniqueEmail("student"), "a long enough password");
  await student.getByTestId("finish-onboarding").click();
  await student.goto("/problems/say-hello");
  await typeCode(student, WRONG_GREET);
  await student.getByTestId("submit").click();
  await expect(student.getByTestId("verdict")).toBeVisible();
  await typeCode(student, RIGHT_GREET);
  await student.getByTestId("submit").click();
  await expect(student.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");

  await teacher.reload();
  await expect(teacher.getByText("No learners yet")).toBeVisible();

  await student.goto("/settings");
  await student.getByTestId("join-code-input").fill(code);
  await student.getByTestId("join-class").click();
  await expect(student.getByText("You joined Python 101").first()).toBeVisible();
  const mine = await student.evaluate(async () => (await (await fetch("/api/progress")).json()).metrics);

  await teacher.reload();
  await expect(teacher.getByTestId("learners-table")).toContainText("Dev Student");
  await expect(teacher.getByTestId("class-stats")).toContainText(`${mine.solved} solved of ${mine.started} started`);
  await expect(teacher.getByTestId("class-stats")).toContainText(`${mine.hints_total} hints in total`);
  await teacher.getByRole("link", { name: "Dev Student" }).first().click();
  await expect(teacher.getByRole("heading", { name: "Dev Student" })).toBeVisible();
  await teacherContext.close();
  await studentContext.close();
});

test("teacher demo labels its data as synthetic", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByTestId("demo-teacher").click();
  await expect(page.getByText("Synthetic demonstration data")).toBeVisible();
  await expect(page.getByTestId("needs-support")).toBeVisible();
  await expect(page.getByTestId("learners-table")).toContainText("(synthetic)");
});

test("knowledge checks are the only source of measured improvement", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/progress");
  await expect(page.getByText("never from the tutor's own estimates")).toBeVisible();
  await page.goto("/check/pre");
  await page.getByTestId("submit-check").click();
  await expect(page.getByText(/You answered/)).toBeVisible();
  await page.goto("/check/post");
  await page.getByRole("radio", { name: "3", exact: true }).first().check();
  await page.getByTestId("submit-check").click();
  await page.goto("/progress");
  await expect(page.getByTestId("gain")).toBeVisible();
});

test("student feedback survey", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/progress");
  await page.getByTestId("open-survey").click();
  const dialog = page.getByRole("dialog");
  for (const group of await dialog.getByRole("group").all()) await group.getByRole("button", { name: "4 of 5" }).click();
  await page.getByTestId("send-survey").click();
  await expect(page.getByText("Your feedback is recorded").first()).toBeVisible();
});

// ---- repeated hints, see docs/bug-repeated-hint.md
const REPORTED_SYNTAX = "def sum_to_n(n):\n    total = 0\n    x = = 1\n    return total\n";
const OFF_BY_ONE = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n";

async function askUntil(page: Page, number: number) {
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint-number")).toContainText(`Hint ${number} on this issue`);
  return page.getByTestId("hint").locator(".markdown").innerText();
}

test("asking repeatedly gives different help each time, then the tutor waits for a change", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, REPORTED_SYNTAX);
  const seen: string[] = [];
  for (let number = 1; number <= 3; number += 1) seen.push(await askUntil(page, number));
  seen.push(await askUntil(page, 4));
  await expect(page.getByTestId("hint").locator("pre"), "the fourth step is a worked example").toBeVisible();
  seen.push(await askUntil(page, 5));
  expect(new Set(seen).size, "every hint is different").toBe(5);
  expect(seen[0]).toContain("Python could not read line 3");
  expect(seen[1]).toContain("x = = 1");
  expect(seen[2]).toContain("Check every bracket");

  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint-waiting")).toContainText("You have seen all the help");
  await expect(page.getByTestId("hint-waiting")).toContainText("Try this next");
  await expect(page.getByTestId("hint")).toHaveCount(0);
  await expect(page.getByTestId("ask-hint"), "a plain request could only repeat something").toBeDisabled();
  await expect(page.getByTestId("ask-input"), "but a specific question is always welcome").toBeEnabled();

  await typeCode(page, `${REPORTED_SYNTAX}# a change\n`);
  await expect(page.getByTestId("ask-hint")).toBeEnabled();
  await page.getByTestId("ask-after-change").click();
  await expect(page.getByTestId("hint")).toHaveAttribute("data-strategy", "evidence_review");
  await expect(page.getByTestId("hint")).toContainText("You changed line");
});

test("after every hint has been shown, asking about selected lines still runs the agents and answers", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, OFF_BY_ONE);
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint-number")).toContainText("Hint 1");
  const levels: string[] = [];
  for (let step = 2; step <= 12; step += 1) {
    if (await page.getByTestId("hint-waiting").count()) break;
    await page.getByRole("button", { name: "I need more help" }).click();
    await expect(page.getByTestId("hint-number").or(page.getByTestId("hint-waiting"))).toBeVisible();
    await page.waitForTimeout(300);
    await page.getByTestId("tutor-working").waitFor({ state: "detached" });
    if (await page.getByTestId("hint").count()) levels.push((await page.getByTestId("hint").getAttribute("data-strategy")) ?? "");
  }
  await expect(page.getByTestId("hint-waiting")).toContainText("You have seen all the help");
  expect(levels, "more help walks every kind of help, without jumping over any").toEqual(["targeted_hint", "trace_failing_case", "print_debugging", "step_outline", "analogous_example", "direct_pointer"]);
  await expect(page.getByTestId("ask-hint")).toBeDisabled();

  // Point at the loop in the code, then ask.
  await page.locator(".cm-line").nth(2).click();
  await page.keyboard.press("Home");
  await page.keyboard.press("Shift+ArrowDown");
  await page.keyboard.press("Shift+End");
  await expect(page.getByTestId("ask-focus")).toContainText("Lines 3–4");
  await page.getByTestId("ask-input").fill("why does it stop too early?");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("asked")).toContainText("why does it stop too early?");
  await expect(page.getByTestId("hint")).toHaveAttribute("data-strategy", "answer_question");
  await expect(page.getByTestId("hint")).toContainText("ran");
  await expect(page.getByTestId("hint")).toContainText("was 1, then 2");
  await expect(page.getByTestId("asked")).toContainText("Lines 3–4");

  // A different question on the same lines gets a different answer, not a refusal.
  const first = await page.getByTestId("hint").locator(".markdown").innerText();
  await page.getByRole("button", { name: "Where is it wrong?" }).click();
  await expect(page.getByTestId("hint").locator(".markdown")).not.toHaveText(first);
  await expect(page.getByTestId("hint")).toHaveAttribute("data-strategy", "answer_question");

  // Clearing the selection is one click.
  await page.getByRole("button", { name: "Stop pointing at these lines" }).click();
  await expect(page.getByTestId("ask-focus")).toContainText("Select lines");
});

test("a missing import gets its real cause, with help that becomes more specific", async ({ page }) => {
  // The reported case: the tutor suggested printing values on a line that could never run.
  await startDemoLearner(page);
  await page.goto("/problems/count-multiples");
  const broken = "def count_multiples(n, limit):\n    counter = 0\n    for i in count(n, n):\n        if i <= limit:\n            counter += 1\n        else:\n            break\n    return counter\n";
  await typeCode(page, broken);
  await page.getByTestId("run").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  await page.getByTestId("ask-hint").click();
  const hint = page.getByTestId("hint");
  await expect(hint).toContainText("count");
  const seen = [await hint.locator(".markdown").innerText()];
  expect(seen[0]).not.toContain("itertools");
  await expect(page.getByTestId("verdict")).toContainText('Python cannot find anything named "count"');
  for (let step = 0; step < 5; step += 1) {
    await page.getByRole("button", { name: "I need more help" }).click();
    await expect(hint.locator(".markdown")).not.toHaveText(seen[seen.length - 1]);
    seen.push(await hint.locator(".markdown").innerText());
  }
  expect(seen.some((text) => text.includes("print("))).toBe(false);
  expect(seen[1]).toContain("itertools.count");
  expect(seen[seen.length - 1]).toContain("from itertools import count");
  await expect(page.getByTestId("diagnosis")).toContainText("itertools");
  await page.getByRole("button", { name: "Why this hint?" }).click();
  await expect(page.getByTestId("hint-why-details")).toContainText("What the tutor found");

  await typeCode(page, `from itertools import count\n\n${broken}`);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");
});

test("the Learn tab reads as one piece of theory, with a tab for each approach", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/pair-sum-exists-sorted");
  await page.getByTestId("tab-learn").click();
  const understand = page.getByTestId("learn-understand");
  await expect(understand).toContainText("a list of numbers");
  await expect(understand).toContainText("has_pair([1, 2, 4, 7], 6)");
  await expect(understand).toContainText("in increasing order");
  await expect(page.locator(".learn-section"), "no separate sections to open one by one").toHaveCount(0);
  const tabs = page.getByTestId("approach-tab");
  await expect(tabs.first()).toHaveText(/Brute force/);
  await expect(page.getByTestId("learn-approach")).toContainText("Intuition");
  await expect(page.getByTestId("approach-steps")).toContainText("second loop");
  await expect(page.getByTestId("approach-complexity")).toContainText("O(n²)");
  await tabs.last().click();
  await expect(tabs.last()).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("learn-approach")).toContainText("Start one position at each end");
  await expect(page.getByTestId("steps-hidden"), "the steps of the main approach wait one click, so the idea can be tried first").toBeVisible();
  await page.getByTestId("show-steps").click();
  await expect(page.getByTestId("approach-steps")).toContainText("one pointer at each end");
  await expect(page.getByTestId("approach-complexity")).toContainText("O(1)");

  await page.getByTestId("learn-ask-tutor").click();
  await expect(page.getByTestId("ask-input")).toBeFocused();

  await page.getByTestId("toggle-side").click();
  await expect(page.getByTestId("ask-input"), "the panel can be hidden for more room to code").toBeHidden();
  await page.getByTestId("toggle-side").click();
  await expect(page.getByTestId("ask-input")).toBeVisible();
});

test("test cases are shown before running, can be edited and added, and get expected answers", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await expect(page.getByTestId("testcases")).toBeVisible();
  await expect(page.getByTestId("case-tab")).toHaveCount(2);
  await expect(page.locator(".case-name").first()).toHaveText("n");
  await expect(page.getByTestId("case-expected")).toBeVisible();
  await expect(page.getByTestId("case-source")).toHaveText("Example from the task");
  await page.getByTestId("cases-hidden").click();
  await expect(page.getByTestId("hidden-note")).toContainText("hidden test");
  // What the hidden tests cover, by kind of case, with what each kind checks, but never their inputs.
  const kinds = page.getByTestId("hidden-category");
  await expect(kinds.first()).toBeVisible();
  expect(await kinds.count()).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId("hidden-categories")).toContainText("Zero");
  await expect(page.getByTestId("hidden-categories")).toContainText("starting values");
  await page.getByTestId("cases-sample").click();
  await page.getByTestId("add-case").click();
  await expect(page.getByTestId("case-tab")).toHaveCount(3);
  await expect(page.getByTestId("case-source")).toHaveText("Your own case");
  await page.getByTestId("case-input").first().fill("5");
  await expect(page.getByTestId("case-expected-later")).toBeVisible();
  await typeCode(page, "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n");
  await page.getByTestId("run").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  const rows = page.locator(".test-row-head");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(2)).toContainText("Case 3");
  await rows.nth(2).click();
  await expect(page.locator(".test-detail").last()).toContainText("15");
  await expect(page.locator(".test-detail").last()).toContainText("10");
  await page.getByTestId("view-cases").click();
  await page.getByTestId("reset-cases").click();
  await expect(page.getByTestId("case-tab")).toHaveCount(2);
});

test("every submission is listed with its date, and its code can be loaded back", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/say-hello");
  await typeCode(page, WRONG_GREET);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  await page.getByTestId("tutor-working").waitFor({ state: "detached" }).catch(() => undefined);
  await typeCode(page, RIGHT_GREET);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");
  await page.getByTestId("tab-history").click();
  await expect(page.getByTestId("submission")).toHaveCount(2);
  await expect(page.getByTestId("submissions-summary")).toContainText("2 submissions, 1 accepted");
  await expect(page.getByText("Today")).toBeVisible();
  await expect(page.getByTestId("submission").first()).toContainText("All tests passed");
  await page.getByTestId("submission").last().getByRole("button").first().click();
  await page.getByTestId("load-submission").click();
  await page.getByRole("button", { name: "Load this code" }).click();
  expect(await editorText(page)).toContain('"Hello " + name');
});

test("topic notes explain, check understanding, and fold away for revision", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/path/hashing");
  await expect(page.getByTestId("why-it-matters")).toBeVisible();
  await expect(page.getByTestId("diagram")).toBeVisible();
  await expect(page.getByTestId("glossary")).toContainText("Collision");
  await expect(page.getByRole("heading", { name: "Time and space" })).toBeVisible();
  await expect(page.getByTestId("practice-recommendation")).toBeVisible();
  const check = page.getByTestId("knowledge-check").first();
  await check.getByRole("button", { name: "A list" }).click();
  await expect(check.getByTestId("check-feedback")).toContainText("Not quite");
  await check.getByRole("button", { name: "A tuple of numbers" }).click();
  await expect(check.getByTestId("check-feedback")).toContainText("That's right");

  await page.getByTestId("mode-revision").click();
  await expect(page.getByTestId("revision-summary")).toBeVisible();
  await expect(page.getByTestId("full-lesson")).toBeVisible();
  await expect(page.getByTestId("tryit").first(), "the long explanation folds away").toBeHidden();
  await page.getByText("Read the full lesson").click();
  await expect(page.getByTestId("tryit").first()).toBeVisible();
  await page.getByTestId("mode-guided").click();
});

test("search finds topics, lesson sections and problems", async ({ page }) => {
  await startDemoLearner(page);
  await page.getByTestId("nav-search").fill("time complexity");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/search\?q=time/);
  const topic = page.getByTestId("search-topic").first();
  await expect(topic).toContainText("Searching and sorting");
  await topic.click();
  await expect(page).toHaveURL(/searching-sorting#time-complexity/);
  await expect(page.getByRole("heading", { name: /Time complexity/ })).toBeVisible();

  await page.goto("/search");
  await page.getByTestId("search-input").fill("palindrome");
  await expect(page.getByTestId("search-problem").first()).toBeVisible();
  await page.getByTestId("search-input").fill("zzzzzz");
  await expect(page.getByText("Nothing found")).toBeVisible();
});

test("selecting code offers to ask about it, even with the tutor tab closed", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, OFF_BY_ONE);
  await expect(page.getByTestId("ask-input"), "the problem tab is showing").toBeHidden();
  await page.locator(".cm-line").nth(2).click();
  await page.keyboard.press("Home");
  await page.keyboard.press("Shift+End");
  await page.getByTestId("ask-about-lines").click();
  await expect(page.getByTestId("ask-input")).toBeFocused();
  await expect(page.getByTestId("ask-focus")).toContainText("Line 3");
  await page.keyboard.type("what does this line do?");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("hint")).toHaveAttribute("data-strategy", "answer_question");
  await expect(page.getByTestId("hint")).toContainText("for i in range(1, n):");
  await expect(page.getByTestId("hint")).toContainText("stops before b");
  await expect(page.getByTestId("asked")).toContainText("Line 3");
});

test("a topic teaches first, runs its examples, then offers problems grouped by technique", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/path/arrays-two-pointers");
  await expect(page.getByTestId("before-you-start")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sliding window", exact: true })).toBeVisible();
  await expect(page.getByTestId("problem-row"), "the lesson comes first").toHaveCount(0);
  const example = page.getByTestId("tryit").first();
  await example.getByTestId("tryit-run").click();
  await expect(example.getByTestId("tryit-output")).toHaveText("True", { timeout: 30_000 });
  await example.getByTestId("tryit-edit").click();
  await expect(example.locator(".cm-content")).toBeVisible();
  await page.getByTestId("start-practice").click();
  await expect(page).toHaveURL(/tab=practice/);
  await expect(page.getByRole("heading", { name: /Two pointers from both ends/ })).toBeVisible();
  const inTopic = await page.evaluate(async () => (await (await fetch("/api/problems?unit=arrays-two-pointers")).json()).length);
  expect(inTopic).toBeGreaterThanOrEqual(30);
  await expect(page.getByTestId("problem-row")).toHaveCount(inTopic);
  await page.reload();
  await expect(page.getByTestId("problem-row").first(), "the tab survives a reload").toBeVisible();
  await page.getByTestId("problem-row").first().click();
  await expect(page.getByTestId("next-problem")).toBeVisible();
  await page.getByTestId("concept-notes-toggle").click();
  await expect(page.getByTestId("concept-notes")).toContainText("When:");
});

test("practice lists every problem by topic, in learning order", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems");
  const groups = page.getByTestId("topic-group");
  await expect(groups).toHaveCount(17);
  await expect(groups.first()).toContainText("Python basics");
  await expect(groups.nth(9)).toContainText("Arrays and two pointers");
  await expect(page.getByRole("status").filter({ hasText: /problems in 17 topics/ })).toBeVisible();
  await expect(groups.nth(9).getByTestId("problem-row"), "other topics start closed").toHaveCount(0);
  await groups.nth(9).getByRole("button", { name: /Arrays and two pointers/ }).click();
  const inTopic = await page.evaluate(async () => (await (await fetch("/api/problems?unit=arrays-two-pointers")).json()).length);
  expect(inTopic).toBeGreaterThanOrEqual(30);
  await expect(groups.nth(9).getByTestId("problem-row")).toHaveCount(inTopic);
  await expect(groups.nth(9).getByRole("link", { name: "Read the lesson on Arrays and two pointers" })).toBeVisible();
});

test("I need more help moves up, and the reason is shown with its evidence", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, OFF_BY_ONE);
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint")).toHaveAttribute("data-level", "1");
  await page.getByRole("button", { name: "I need more help" }).click();
  await expect(page.getByTestId("hint")).toHaveAttribute("data-level", "2");
  await page.getByRole("button", { name: "Why this hint?" }).click();
  await expect(page.getByTestId("hint-why-details")).toContainText("Hints already seen on this issue");
  await expect(page.getByTestId("hint-why")).toContainText("more detail");
});

test("fixing an error is acknowledged, and the new issue starts small", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, REPORTED_SYNTAX);
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("hint-number")).toContainText("Hint 1");
  await typeCode(page, OFF_BY_ONE);
  await expect(page.getByTestId("hint-stale"), "the old hint is marked as being about earlier code").toBeVisible();
  await page.getByTestId("ask-hint").click();
  await expect(page.getByTestId("progress-note")).toContainText("syntax error is fixed");
  await expect(page.getByTestId("hint")).toHaveAttribute("data-strategy", "conceptual_question");
  await expect(page.getByTestId("hint-number")).toContainText("Hint 1 on this issue");
  await expect(page.getByTestId("hint-stale")).toHaveCount(0);
});

test("the editor offers find and replace, and shows the language", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await expect(page.getByTestId("language")).toHaveText("Python 3.12");
  await page.getByTestId("find").click();
  await expect(page.locator(".cm-search input[name=search]")).toBeVisible();
  await expect(page.locator(".cm-search input[name=replace]")).toBeVisible();
});

test("Add Question: a link is read, what is missing is shown, and the learner completes it", async ({ page }) => {
  await startDemoLearner(page);
  await page.route("**/api/imports/lookup", (route) =>
    route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        supported: true, status: "partial", access: "public_page", source_name: "practice.example.org", source_url: "https://practice.example.org/q", message: "Read from practice.example.org. Please check it before saving.",
        extracted_fields: ["title", "description", "examples"], missing_fields: ["constraints", "difficulty"], guidance: null,
        draft: {
          title: "Sum of Two", description: "Given two integers a and b, return their sum.", mode: "function", function_name: "sum_of_two", parameters: ["a", "b"], tags: [], unit_id: "functions", source_name: "practice.example.org", source_url: "https://practice.example.org/q",
          source_retrieved_at: new Date().toISOString(), examples: [{ input_text: "a = 1, b = 2", output_text: "3", args: [1, 2], expected: 3, parsed: true }], missing_fields: ["constraints", "difficulty"], extracted_fields: ["title", "description", "examples"], warnings: ["This was read automatically from a web page, so it may be incomplete or out of order. Please check every field."],
        },
      }),
    }),
  );
  await page.goto("/problems/new");
  await page.getByTestId("method-link").click();
  await page.getByTestId("link-input").fill("https://practice.example.org/q");
  await page.getByTestId("lookup").click();
  await expect(page.getByTestId("lookup-result")).toContainText("Found: title, description, examples");
  await expect(page.getByTestId("lookup-result")).toContainText("Still needed: constraints, difficulty");
  await page.getByTestId("continue-review").click();
  await expect(page.getByTestId("found-fields")).toContainText("description");
  await expect(page.getByTestId("missing-fields")).toContainText("constraints");
  await expect(page.getByTestId("draft-source")).toContainText("https://practice.example.org/q");
  await expect(page.getByTestId("draft-title")).toHaveValue("Sum of Two");
  await page.getByTestId("to-tests").click();
  await expect(page.getByTestId("test-card").first()).toContainText("Imported example");
  await expect(page.getByTestId("test-summary")).toContainText("1 imported");
  await page.getByTestId("save-question").click();
  await expect(page.locator(".cm-content")).toBeVisible();
  await expect(page.getByTestId("tests-not-official")).toContainText("not the original platform's hidden tests");
});

test("Add Question: a link that cannot be used leads straight to pasting", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/new");
  await page.getByTestId("method-link").click();
  await page.getByTestId("link-input").fill("http://169.254.169.254/latest/meta-data/");
  await page.getByTestId("lookup").click();
  await expect(page.getByTestId("lookup-result")).toHaveAttribute("data-status", "invalid");
  await page.getByTestId("switch-to-paste").click();
  await expect(page.getByTestId("paste-text")).toBeVisible();
});

test("Add Question: paste accepts a source, a topic and notes", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/new");
  await page.getByTestId("method-paste").click();
  await page.getByTestId("paste-text").fill("Sum of Two\nGiven two integers a and b, return their sum.\n\nExample 1:\nInput: a = 1, b = 2\nOutput: 3\n");
  await page.getByTestId("optional-details").click();
  await page.getByTestId("paste-source").fill("https://leetcode.com/problems/add-two-integers/");
  await page.getByTestId("paste-notes").fill("From my mock interview.");
  await page.getByTestId("parse").click();
  await expect(page.getByTestId("draft-source")).toContainText("LeetCode");
  await expect(page.getByTestId("draft-notes")).toHaveValue("From my mock interview.");
  await page.getByTestId("to-tests").click();
  await page.getByTestId("save-question").click();
  await expect(page.getByTestId("learner-notes")).toContainText("From my mock interview.");
  await expect(page.getByRole("link", { name: /View the original/ })).toHaveAttribute("href", /leetcode\.com/);
});

test("the learning path shows your position and lets you go anywhere", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/path");
  await expect(page.getByTestId("path-position")).toContainText("topics look secure");
  await expect(page.getByText("You are here")).toBeVisible();
  await expect(page.getByTestId("path-jump").getByRole("link", { name: "DSA topics" })).toBeVisible();
  await page.getByTestId("path-jump").getByRole("link", { name: "All problems" }).click();
  await expect(page).toHaveURL(/\/problems/);
});

test("the old product name is gone, and browser data moves to the new name", async ({ page }) => {
  await page.goto("/welcome");
  await page.evaluate(() => { localStorage.setItem("trellis.theme", "dark"); localStorage.setItem("trellis.draft.u.p.python", '{"code":"x","at":1}'); });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const stored = await page.evaluate(() => ({ keys: Object.keys(localStorage), theme: localStorage.getItem("codepath.theme"), draft: localStorage.getItem("codepath.draft.u.p.python") }));
  expect(stored.theme).toBe("dark");
  expect(stored.draft).toContain('"code":"x"');
  expect(stored.keys.filter((key) => key.startsWith("trellis."))).toEqual([]);
  await expect(page).toHaveTitle(/CodePath/);
  await startDemoLearner(page);
  for (const path of ["/", "/path", "/problems", "/progress", "/settings", "/problems/new", "/problems/sum-to-n"]) {
    await page.goto(path);
    await expect(page.locator("#root")).not.toBeEmpty();
    await page.waitForLoadState("networkidle");
    const text = await page.locator("body").innerText();
    expect(text, path).not.toMatch(/trellis|tellis/i);
    await expect(page, path).toHaveTitle(/CodePath/);
  }
});

test("the profile shows what was done, the learning state of each topic, and how the tutor matched it", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/say-hello");
  await typeCode(page, WRONG_GREET);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toBeVisible();
  await typeCode(page, RIGHT_GREET);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");

  // The workspace hides the main navigation to give the editor room, so start from the home page.
  await page.goto("/");
  await page.getByRole("link", { name: "Profile", exact: true }).first().click();
  await expect(page).toHaveURL(/\/profile$/);
  const stats = page.getByTestId("profile-stats");
  await expect(stats).toContainText("Problems solved");
  await expect(stats).toContainText("1 of 2 submissions");
  await expect(page.getByTestId("difficulty-easy")).toContainText(/^Easy\s*1\s*of \d+/);
  await expect(page.getByTestId("calendar")).toBeVisible();
  await expect(page.getByTestId("then-now-empty")).toBeVisible();

  const matrix = page.getByTestId("state-matrix");
  for (const column of ["Mastery", "Evidence", "Confidence", "Confusion", "Workload", "Progress"]) {
    await expect(matrix.getByRole("columnheader", { name: column })).toBeVisible();
  }
  const basics = matrix.getByRole("row").filter({ has: page.getByRole("rowheader", { name: "Python basics" }) });
  await expect(basics).toContainText(/1 \/ \d+/);
  await expect(basics).toContainText("%");
  await expect(page.getByTestId("vector-table").getByRole("row")).toHaveCount(15);
  await expect(page.getByTestId("similar-summary")).toContainText("Last match");

  // The account menu leads to the same page.
  await page.goto("/");
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByTestId("menu-profile").click();
  await expect(page).toHaveURL(/\/profile$/);
});

test("the teacher's table has a column for each measure, and a student's page shows their full profile", async ({ page }) => {
  await page.goto("/welcome");
  await page.getByTestId("demo-teacher").click();
  const table = page.getByTestId("learners-table");
  await table.waitFor();
  for (const column of ["Solved", "Completion", "Mastery", "Topics", "Confidence", "Confusion", "Workload", "Progress", "First try", "Submissions per solve", "Hints per solve", "Streak"]) {
    await expect(table.getByRole("columnheader", { name: column, exact: true })).toBeVisible();
  }
  await table.getByRole("rowheader").first().getByRole("link").click();
  await expect(page.getByTestId("profile-stats")).toBeVisible();
  await expect(page.getByTestId("state-matrix")).toBeVisible();
  await expect(page.getByRole("heading", { name: "How they have improved" })).toBeVisible();
});

test("Learn links from a problem open the topic's lesson, even in Practice mode", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/settings");
  await page.getByTestId("mode-practice").click();
  await expect(page.getByTestId("mode-practice")).toHaveAttribute("aria-checked", "true");
  await page.goto("/problems/sum-to-n");
  const [lesson] = await Promise.all([page.context().waitForEvent("page"), page.getByTestId("read-lesson").click()]);
  await expect(lesson).toHaveURL(/\/path\/loops\?tab=lesson/);
  await expect(lesson.getByTestId("before-you-start")).toBeVisible();
  await expect(lesson.getByTestId("tab-practice")).toHaveAttribute("aria-selected", "false");
  await lesson.close();
  // The Learn tab's theory link opens the matching section of the lesson.
  await page.getByTestId("tab-learn").click();
  const [section] = await Promise.all([page.context().waitForEvent("page"), page.getByTestId("learn-lesson-link").click()]);
  await expect(section).toHaveURL(/tab=lesson/);
  await expect(section.getByTestId("before-you-start")).toBeVisible();
  await section.close();
  // "Back to problems" still goes to the problem list, as it says.
  await page.getByRole("link", { name: "Back to problems" }).click();
  await expect(page).toHaveURL(/tab=practice/);
});

test("a reflection answer gets a reply, and the plan shows the route ahead", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  await typeCode(page, "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n");
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("hint")).toBeVisible();
  await typeCode(page, "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n");
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", "accepted");
  const card = page.getByTestId("reflection");
  await expect(card).toBeVisible();
  await card.getByRole("textbox").fill("I'm not sure, I just added one");
  await card.getByRole("button", { name: "Save answer" }).click();
  await expect(page.getByTestId("reflection-reply")).toBeVisible();
  await expect(page.getByTestId("reflection-your-answer")).toContainText("I'm not sure");
  await page.getByTestId("reflection-done").click();
  await expect(page.getByTestId("route")).toContainText("Loops");
});

test("a lesson opened in a new tab keeps the theme on screen, even in a browser that has not saved it", async ({ page, browser }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  if ((await page.locator("html").getAttribute("data-theme")) !== "dark") await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const link = page.getByTestId("read-lesson");
  await expect(link).toHaveAttribute("href", /tab=lesson&theme=dark/);
  // The same browser: the new tab opens dark, and the address is clean.
  const [lesson] = await Promise.all([page.context().waitForEvent("page"), link.click()]);
  await expect(lesson).toHaveURL(/\/path\/loops\?tab=lesson$/);
  await expect(lesson.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(lesson.getByTestId("before-you-start")).toBeVisible();
  await lesson.close();
  // Another browser with nothing saved, as when the desktop app opens the link elsewhere: still dark from the first frame.
  const elsewhere = await browser.newContext({ baseURL: new URL(page.url()).origin });
  const fresh = await elsewhere.newPage();
  await fresh.goto((await link.getAttribute("href"))!);
  await expect(fresh.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(new URL(fresh.url()).searchParams.get("theme")).toBeNull();
  await elsewhere.close();
});
