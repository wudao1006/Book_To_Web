import { expect, test } from "@playwright/test";

test("renders local demo mode and then switches to sandboxed remote mode", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("Current focus:")).toBeVisible();
  await expect(
    page.getByText("This preview shows how a chapter can become a small interactive reading artifact")
  ).toBeVisible();

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
  expect(uploadBody).toContain("book_id");
  const { book_id: bookId } = JSON.parse(uploadBody) as { book_id: string };

  const generate = await request.post(
    `http://127.0.0.1:8000/api/books/${bookId}/chapters/0/generate`
  );
  const generateBody = await generate.text();
  expect(generateBody).toContain("\"success\":true");
  expect(generate.ok()).toBeTruthy();

  await expect(page.getByText("LOADER CONTROLS")).toBeVisible();
  await page.getByRole("textbox", { name: "Book ID" }).fill(bookId);
  await page.getByRole("checkbox", { name: "Use backend API" }).check();
  await page.getByRole("checkbox", { name: "Allow unsafe code execution" }).check();

  const sandboxFrame = page.frameLocator(`iframe[title="Sandboxed component ${bookId}-0"]`);
  await expect(
    sandboxFrame.getByText("Interactive narrative placeholder")
  ).toBeVisible();
});
