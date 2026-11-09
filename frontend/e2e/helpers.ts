import { readFileSync } from "node:fs";

import { expect, type Page } from "@playwright/test";

export const RIGHT_GREET = 'def greet(name): return f"Hello, {name}!"';
export const WRONG_GREET = 'def greet(name): return "Hello " + name';

export function teacherInvite(): string {
  const fromEnv = process.env.TEACHER_INVITE_CODE;
  if (fromEnv) return fromEnv;
  const match = readFileSync("../.env", "utf8").match(/^TEACHER_INVITE_CODE=(.+)$/m);
  if (!match) throw new Error("Set TEACHER_INVITE_CODE in .env for the end-to-end tests");
  return match[1].trim();
}

export async function startDemoLearner(page: Page, options: { skip?: boolean } = {}) {
  await page.goto("/welcome");
  await page.getByTestId("demo-student").click();
  await expect(page).toHaveURL(/onboarding/);
  await page.getByTestId(options.skip ? "skip-intro" : "finish-onboarding").click();
  await expect(page.getByTestId("recommendation")).toBeVisible();
}

export function uniqueEmail(prefix = "e2e"): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`;
}

export async function register(page: Page, name: string, email: string, password: string, invite?: string) {
  await page.goto("/welcome");
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Your name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  if (invite) {
    await page.getByLabel("Teacher").check();
    await page.getByLabel("Teacher invite code").fill(invite);
  }
  await page.getByRole("button", { name: "Create account" }).click();
}

/** Replace the editor's content the way a person does: focus, select all, type. */
export async function typeCode(page: Page, code: string) {
  const content = page.locator(".cm-content");
  await content.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.insertText(code);
}

export async function editorText(page: Page): Promise<string> {
  const lines = await page.locator(".cm-content .cm-line").allInnerTexts();
  return lines.join("\n");
}

export async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "the page must not scroll sideways").toBeLessThanOrEqual(1);
}
