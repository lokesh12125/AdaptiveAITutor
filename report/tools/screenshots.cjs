// Captures report screenshots from the running app (default http://127.0.0.1:5173).
// Run from the repository root:  NODE_PATH=frontend/node_modules node report/tools/screenshots.cjs
const { chromium } = require("@playwright/test");
const path = require("path");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5173";
const OUT = path.join(__dirname, "..", "figures", "screens");
const OFF_BY_ONE = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n";
const RIGHT = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n";

async function typeCode(page, code) {
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.insertText(code);
}

async function submitAndWait(page) {
  await page.getByTestId("submit").click();
  await page.waitForTimeout(800);
  await page.getByTestId("running").waitFor({ state: "detached", timeout: 60000 }).catch(() => {});
  await page.getByTestId("verdict").waitFor({ timeout: 60000 });
  await page.waitForTimeout(1200);
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name) });
  console.log("saved", name);
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, colorScheme: "light" });
  const page = await context.newPage();
  await page.goto(`${BASE}/welcome`);
  await page.evaluate(() => localStorage.setItem("codepath.theme", "light"));
  await page.getByTestId("demo-student").click();
  await page.getByTestId("finish-onboarding").click();
  await page.getByTestId("recommendation").waitFor();

  await page.goto(`${BASE}/problems/sum-to-n`);
  await page.locator(".cm-content").waitFor();
  await typeCode(page, OFF_BY_ONE);
  await submitAndWait(page);
  await page.getByTestId("hint").waitFor({ timeout: 30000 });
  await shot(page, "workspace_first_hint.png");

  await typeCode(page, OFF_BY_ONE.replace("return total", "return total  # checked"));
  await submitAndWait(page);
  await page.getByTestId("offer").waitFor({ timeout: 30000 });
  await shot(page, "offer_not_pushed.png");

  await page.getByTestId("offer").getByRole("button", { name: "Get a hint" }).click();
  await page.getByTestId("hint").waitFor({ timeout: 30000 });
  await page.waitForTimeout(1200);
  const why = page.getByRole("button", { name: "Why this hint?" });
  if (await why.count()) await why.first().click();
  await page.waitForTimeout(500);
  await shot(page, "second_hint_on_request.png");

  await typeCode(page, OFF_BY_ONE.replace("total = 0", "total = 0  # start"));
  await submitAndWait(page);
  const reflection = page.getByTestId("reflection");
  if (await reflection.count()) {
    await reflection.scrollIntoViewIfNeeded();
    await shot(page, "reflection_question.png");
    await reflection.getByRole("textbox").fill("no idea");
    await reflection.getByRole("button", { name: "Save answer" }).click();
    await page.getByTestId("reflection-reply").waitFor({ timeout: 15000 });
    await page.getByTestId("reflection-reply").scrollIntoViewIfNeeded();
    await shot(page, "reflection_reply.png");
    await page.getByTestId("reflection-done").click();
  }

  await typeCode(page, RIGHT);
  await submitAndWait(page);
  await page.getByTestId("plan").waitFor({ timeout: 30000 });
  await page.getByTestId("plan").scrollIntoViewIfNeeded();
  await shot(page, "solved_plan_route.png");

  await page.goto(`${BASE}/`);
  await page.getByTestId("route").waitFor({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  await shot(page, "home_route.png");

  await page.goto(`${BASE}/path/loops?tab=lesson`);
  await page.getByTestId("before-you-start").waitFor({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  await shot(page, "lesson.png");

  await page.goto(`${BASE}/problems`);
  await page.waitForTimeout(1500);
  await shot(page, "practice_library.png");

  await page.goto(`${BASE}/profile`);
  await page.waitForTimeout(2000);
  await shot(page, "profile.png");

  const teacher = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, colorScheme: "light" });
  const tpage = await teacher.newPage();
  await tpage.goto(`${BASE}/welcome`);
  await tpage.evaluate(() => localStorage.setItem("codepath.theme", "light"));
  await tpage.getByTestId("demo-teacher").click();
  await tpage.waitForURL(/teacher/, { timeout: 15000 });
  await tpage.waitForTimeout(2500);
  await shot(tpage, "teacher_dashboard.png");

  await browser.close();
})().catch((error) => { console.error(error); process.exit(1); });
