import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import { once } from "node:events";
import { chromium } from "playwright-core";
import { createServer } from "../server.mjs";

async function listen(server) {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  return `http://127.0.0.1:${server.address().port}`;
}

test("a user can stop, retry, and reset a real browser conversation", async (t) => {
  let attempts = 0;
  const upstream = http.createServer((request, response) => {
    if (request.url !== "/v1/chat-messages") {
      response.writeHead(404).end();
      return;
    }
    attempts += 1;
    response.writeHead(200, { "content-type": "text/event-stream" });
    if (attempts === 1) {
      response.write('data: {"event":"message","answer":"第一段"}\n\n');
      const timer = setTimeout(() => response.end('data: {"event":"message_end"}\n\n'), 2_000);
      response.on("close", () => clearTimeout(timer));
    } else {
      response.end('data: {"event":"message","answer":"重试成功"}\n\ndata: {"event":"message_end"}\n\n');
    }
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.getByLabel("输入研究任务").fill("请总结材料");
  await page.getByRole("button", { name: "发送任务" }).click();
  await page.getByText("第一段").waitFor();
  await page.getByRole("button", { name: "停止生成" }).click();

  await page.getByText("已停止生成").waitFor();
  assert.equal(await page.getByLabel("输入研究任务").inputValue(), "请总结材料");
  await page.getByRole("button", { name: "重试本轮" }).click();
  await page.getByText("重试成功").waitFor();
  assert.equal(attempts, 2);
  assert.equal(await page.locator("#evidence-status strong").textContent(), "回答已返回");

  await page.getByRole("button", { name: "新建研究会话" }).click();
  await page.getByText("新的研究会话已准备好").waitFor();
  assert.equal(await page.getByLabel("输入研究任务").inputValue(), "");
});

test("a failed upload can be retried and a real artifact is downloadable once", async (t) => {
  const artifactId = "123e4567-e89b-42d3-a456-426614174000";
  let uploadAttempts = 0;
  const upstream = http.createServer((request, response) => {
    if (request.url === "/v1/files/upload") {
      uploadAttempts += 1;
      if (uploadAttempts === 1) {
        response.writeHead(502, { "content-type": "application/json" });
        response.end(JSON.stringify({ message: "temporary upload failure" }));
      } else {
        response.writeHead(201, { "content-type": "application/json" });
        response.end(JSON.stringify({ id: "uploaded-file-1", name: "report.md", size: 9 }));
      }
      return;
    }
    if (request.url === "/v1/chat-messages") {
      response.writeHead(200, { "content-type": "text/event-stream" });
      response.end([
        `data: {"event":"message","answer":"已读取材料"}`,
        `data: {"event":"message_file","tool_file_id":"${artifactId}","filename":"result.md"}`,
        `data: {"event":"message_file","tool_file_id":"${artifactId}","filename":"result.md"}`,
        'data: {"event":"message_end","conversation_id":"conversation-file"}',
        "",
      ].join("\n\n"));
      return;
    }
    if (request.url?.startsWith(`/files/tools/${artifactId}.md`)) {
      response.writeHead(200, { "content-type": "text/markdown", "content-disposition": 'attachment; filename="result.md"' });
      response.end("real artifact bytes");
      return;
    }
    response.writeHead(404).end();
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.locator("#file-input").setInputFiles({ name: "report.md", mimeType: "text/markdown", buffer: Buffer.from("# report") });
  await page.getByText(/report\.md · 上传失败/).waitFor();
  await page.getByRole("button", { name: "重试上传 report.md" }).click();
  await page.locator(".attachment-chip.ready").waitFor();
  await page.getByLabel("输入研究任务").fill("请读取材料");
  await page.getByRole("button", { name: "发送任务" }).click();
  await page.getByText("已读取材料").waitFor();
  assert.equal(await page.locator("#artifact-list .artifact-card").count(), 1);
  assert.equal(await page.locator("#artifact-count").textContent(), "1");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "下载 result.md" }).click();
  const download = await downloadPromise;
  assert.equal(await readFile(await download.path(), "utf8"), "real artifact bytes");
});

test("a draft survives a page refresh", async (t) => {
  const upstream = http.createServer((request, response) => response.writeHead(404).end());
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.getByLabel("输入研究任务").fill("不要丢失这段研究草稿");
  await page.reload();
  assert.equal(await page.getByLabel("输入研究任务").inputValue(), "不要丢失这段研究草稿");
});

test("mobile users can use the menu and submit with Enter", async (t) => {
  const upstream = http.createServer((request, response) => {
    if (request.url !== "/v1/chat-messages") {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end('data: {"event":"message","answer":"键盘发送成功"}\n\ndata: {"event":"message_end"}\n\n');
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  const menu = page.locator("#mobile-menu");
  await menu.click();
  assert.equal(await menu.getAttribute("aria-expanded"), "true");
  await page.keyboard.press("Escape");
  assert.equal(await menu.getAttribute("aria-expanded"), "false");
  await page.getByLabel("输入研究任务").fill("键盘任务");
  await page.getByLabel("输入研究任务").press("Enter");
  await page.getByText("键盘发送成功").waitFor();
});

test("agent message deltas are not duplicated by the final message event", async (t) => {
  const upstream = http.createServer((request, response) => {
    if (request.url !== "/v1/chat-messages") {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end([
      'data: {"event":"agent_message","answer":"连接"}',
      'data: {"event":"agent_message","answer":"正常。"}',
      'data: {"event":"message","answer":"连接正常。"}',
      'data: {"event":"message_end"}',
      "",
    ].join("\n\n"));
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.getByLabel("输入研究任务").fill("测试增量");
  await page.getByRole("button", { name: "发送任务" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".assistant-message .message-body").item(1)?.textContent === "连接正常。");
  assert.equal(await page.locator(".assistant-message .message-body").nth(1).textContent(), "连接正常。");
});

test("an upstream failure preserves the query and allows a retry", async (t) => {
  let attempts = 0;
  const upstream = http.createServer((request, response) => {
    if (request.url !== "/v1/chat-messages") {
      response.writeHead(404).end();
      return;
    }
    attempts += 1;
    if (attempts === 1) {
      response.writeHead(503, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: "temporary upstream failure" }));
      return;
    }
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end('data: {"event":"message","answer":"重试后成功"}\n\ndata: {"event":"message_end"}\n\n');
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.getByLabel("输入研究任务").fill("失败后必须保留这个问题");
  await page.getByRole("button", { name: "发送任务" }).click();
  await page.getByRole("button", { name: "重试本轮" }).waitFor();
  assert.equal(await page.getByLabel("输入研究任务").inputValue(), "失败后必须保留这个问题");
  await page.getByRole("button", { name: "重试本轮" }).click();
  await page.getByText("重试后成功").waitFor();
  assert.equal(attempts, 2);
});

test("a bare tool-file URL becomes a downloadable artifact card", async (t) => {
  const artifactId = "123e4567-e89b-42d3-a456-426614174000";
  const upstream = http.createServer((request, response) => {
    if (request.url !== "/v1/chat-messages") {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end([
      `data: {"event":"message","answer":"下载：http://api:5001/files/tools/${artifactId}.md?timestamp=old&nonce=old&sign=old"}`,
      'data: {"event":"message_end"}',
      "",
    ].join("\n\n"));
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl);
  await page.getByLabel("输入研究任务").fill("请求交付");
  await page.getByRole("button", { name: "发送任务" }).click();
  await page.getByText("下载").last().waitFor();
  await page.waitForFunction(() => document.querySelector("#artifact-count")?.textContent === "1");
  assert.equal(await page.locator("#artifact-list .artifact-card").count(), 1);
  assert.match(await page.locator(".assistant-message").last().innerText(), /下载/);
});

test("the narrowest supported viewport has no horizontal overflow", async (t) => {
  const upstream = http.createServer((request, response) => {
    if (request.url === "/v1/info") {
      response.writeHead(200, { "content-type": "application/json" }).end("{}");
      return;
    }
    response.writeHead(404).end();
  });
  const upstreamUrl = await listen(upstream);
  const app = createServer({
    port: 0,
    difyApiBaseUrl: upstreamUrl,
    difyFileBaseUrl: upstreamUrl,
    difyApiKey: "browser-test-key",
    difySecretKey: "browser-test-secret",
    difyUserId: "browser-test-user",
  });
  const appUrl = await listen(app);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  t.after(async () => {
    await browser.close();
    app.close();
    upstream.close();
  });
  const page = await browser.newPage({ viewport: { width: 264, height: 356 } });
  page.setDefaultTimeout(3_000);
  await page.goto(appUrl, { waitUntil: "networkidle" });
  const dimensions = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }));
  assert.ok(dimensions.body <= dimensions.viewport, JSON.stringify(dimensions));
});
