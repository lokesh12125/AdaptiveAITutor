import { expect, test } from "@playwright/test";

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
  await expect(page.getByText("Your answer is saved").first()).toBeVisible();
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
  expect(metrics.started).toBe(0);
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("verdict")).toHaveAttribute("data-verdict", /wrong_answer|partial/);
  const after = await page.evaluate(async () => (await (await fetch("/api/progress")).json()).metrics);
  expect(after.graded_attempts).toBe(1);
});

test("repeated errors raise support step by step, and the tutor waits between steps", async ({ page }) => {
  await startDemoLearner(page);
  await page.goto("/problems/sum-to-n");
  const levels: number[] = [];
  for (let attempt = 0; attempt < 3; attempt++) {
    await typeCode(page, `def sum_to_n(n):\n    return sum(range(1, n))  # attempt ${attempt}`);
    await page.getByTestId("submit").click();
    await expect(page.getByTestId("running")).toHaveCount(0, { timeout: 30_000 });
    await expect(page.getByTestId("verdict")).toBeVisible();
    await expect(page.getByTestId("hint")).toBeVisible();
    levels.push(Number(await page.getByTestId("hint").getAttribute("data-level")));
    await page.waitForTimeout(300);
    expect(Number(await page.getByTestId("hint").getAttribute("data-level")), "no new hint appears on its own").toBe(levels[levels.length - 1]);
  }
  expect(levels).toEqual([...levels].sort((a, b) => a - b));
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
    await expect(page.getByText("Key ideas")).toBeVisible();
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
  await expect(cards.filter({ hasText: "From your paste" })).toHaveCount(2);
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

  await page.getByRole("link", { name: "Edit" }).click();
  await expect(page.getByTestId("draft-title")).toHaveValue("Two Sum Practice");
  await page.getByTestId("draft-title").fill("Two Sum Renamed");
  await page.getByTestId("save-edit").click();
  await expect(page.getByRole("heading", { name: "Two Sum Renamed" })).toBeVisible();
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
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("does not scrape")).toBeVisible();
  await page.getByTestId("switch-to-paste").click();
  await expect(page.getByTestId("paste-text")).toBeVisible();
});

test("Add Question: a supported link imports metadata, shows its source, and asks for the statement", async ({ page }) => {
  await startDemoLearner(page);
  await page.route("**/api/imports/lookup", (route) =>
    route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        supported: true, source_name: "Codeforces", message: "Found it. The statement is not available through the API, so please paste that in the next step.", guidance: null,
        draft: { title: "Two Vessels", description: "", difficulty: "easy", tags: ["math"], unit_id: "loops", mode: "stdio", source_name: "Codeforces", source_url: "https://codeforces.com/problemset/problem/1872/A", source_retrieved_at: new Date().toISOString(), missing_fields: ["description", "constraints", "examples"], warnings: [], examples: [], parameters: [] },
      }),
    }),
  );
  await page.goto("/problems/new");
  await page.getByTestId("method-link").click();
  await page.getByTestId("link-input").fill("1872A");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("Found: Two Vessels")).toBeVisible();
  await page.getByTestId("continue-paste").click();
  await page.getByTestId("paste-text").fill("Two Vessels\nRead two numbers and print how many moves make them equal.\n\nSample Input 1\n1 3\nSample Output 1\n1\n");
  await page.getByTestId("parse").click();
  await expect(page.getByText("Source: Codeforces, https://codeforces.com/problemset/problem/1872/A")).toBeVisible();
  await page.getByTestId("to-tests").click();
  await expect(page.getByTestId("test-card").first()).toContainText("From your paste");
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
  test("the theme follows the system at first, then persists when chosen", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark" });
    const page = await context.newPage();
    await page.goto("/welcome");
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
    await page.getByRole("button", { name: "Switch to light theme" }).click();
    await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("light");
    await page.reload();
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe("light");
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
  const before = await page.locator('[data-panel-id="problem"]').evaluate((el) => el.getBoundingClientRect().width);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const after = await page.locator('[data-panel-id="problem"]').evaluate((el) => el.getBoundingClientRect().width);
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
  await expect(teacher.getByTestId("class-stats")).toContainText(`${mine.solved} solved of ${mine.started} attempted`);
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
