import { expect, test } from "@playwright/test";

test("shows generation progress and supports version rollback in API mode", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("Current focus:")).toBeVisible();

  const upload = await request.post("http://127.0.0.1:8000/api/books/upload", {
    multipart: {
      title: "Sandbox Smoke",
      author: "Playwright",
      file: {
        name: "sandbox.md",
        mimeType: "text/markdown",
        buffer: Buffer.from("# Chapter One\n\nDemand meets supply.", "utf-8")
      }
    }
  });

  expect(upload.ok()).toBeTruthy();
  const uploadBody = await upload.text();
  const { book_id: bookId } = JSON.parse(uploadBody) as { book_id: string };

  const firstGenerate = await request.post(
    `http://127.0.0.1:8000/api/books/${bookId}/chapters/0/generate`
  );
  expect(firstGenerate.ok()).toBeTruthy();

  await page.getByRole("textbox", { name: "Book ID" }).fill(bookId);
  await page.getByRole("checkbox", { name: "Use backend API" }).check();
  await page.getByRole("checkbox", { name: "Allow unsafe code execution" }).check();

  await page.getByRole("button", { name: "Generate Component" }).click();
  await expect(page.getByText("Task status: succeeded")).toBeVisible({ timeout: 20_000 });

  await expect(page.getByText("critic")).toBeVisible();
  await expect(page.getByText("compile")).toBeVisible();
  await expect(page.getByText("v2")).toBeVisible();

  const rollbackButton = page.getByRole("button", { name: "Rollback to stable" });
  await expect(rollbackButton).toBeEnabled();
  await rollbackButton.click();

  await page.getByRole("radio", { name: "stable" }).check();

  const sandboxFrame = page.frameLocator(`iframe[title="Sandboxed component ${bookId}-0"]`);
  await expect(sandboxFrame.getByText("Interactive narrative placeholder")).toBeVisible();
});
