import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { once } from "node:events";
import { createServer, buildSignedToolFileUrl, readConfig } from "../server.mjs";

const SECRET = "test-dify-secret";
const TOOL_FILE_ID = "123e4567-e89b-12d3-a456-426614174000";

async function startServer(overrides = {}) {
  const upstream = await startUpstream();
  const config = {
    port: 0,
    difyApiBaseUrl: upstream.url,
    difyFileBaseUrl: upstream.url,
    difyApiKey: "test-app-key",
    difySecretKey: SECRET,
    difyUserId: "test-user",
    ...overrides,
  };
  const server = createServer(config);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const { port } = server.address();
  return { server, upstream, baseUrl: `http://127.0.0.1:${port}` };
}

async function startUpstream() {
  const requests = [];
  const server = await new Promise((resolve) => {
    const instance = createServer({
      port: 0,
      difyApiBaseUrl: "http://invalid.local",
      difyFileBaseUrl: "http://invalid.local",
      difyApiKey: "upstream-key",
      difySecretKey: SECRET,
      difyUserId: "upstream-user",
      upstreamHandler: async (request, response) => {
        const body = await readRequest(request);
        requests.push({ method: request.method, url: request.url, headers: request.headers, body });
        if (request.url === "/v1/chat-messages") {
          response.writeHead(200, { "content-type": "text/event-stream" });
          response.end('data: {"event":"message","answer":"hello"}\n\ndata: {"event":"message_end"}\n\n');
          return;
        }
        if (request.url === "/v1/files/upload") {
          response.writeHead(201, { "content-type": "application/json" });
          response.end(JSON.stringify({ id: "uploaded-file-1", name: "sample.md", size: 12 }));
          return;
        }
        if (request.url.startsWith("/files/tools/" + TOOL_FILE_ID + ".md")) {
          response.writeHead(200, {
            "content-type": "text/markdown",
            "content-disposition": 'attachment; filename="result.md"',
          });
          response.end("real artifact bytes");
          return;
        }
        response.writeHead(404);
        response.end("not found");
      },
    });
    instance.listen(0, "127.0.0.1", () => resolve(instance));
  });
  const { port } = server.address();
  return { server, requests, url: `http://127.0.0.1:${port}` };
}

function readRequest(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

test.afterEach(async () => {
  for (const server of activeServers.splice(0)) {
    server.close();
  }
});

const activeServers = [];

test("readConfig uses safe defaults and never requires a client-side secret", () => {
  const config = readConfig({ DIFY_API_KEY: "key", DIFY_SECRET_KEY: "secret" });
  assert.equal(config.port, 3000);
  assert.equal(config.difyUserId, "research-web-user");
  assert.equal(config.difyApiKey, "key");
  assert.equal(config.difySecretKey, "secret");
});

test("buildSignedToolFileUrl follows Dify's external HMAC format", () => {
  const timestamp = "1788000000";
  const nonce = "test-nonce";
  const url = buildSignedToolFileUrl({
    baseUrl: "http://localhost",
    toolFileId: TOOL_FILE_ID,
    extension: "md",
    secretKey: SECRET,
    timestamp,
    nonce,
  });
  const expectedData = `file-preview|${TOOL_FILE_ID}|${timestamp}|${nonce}`;
  const expected = crypto.createHmac("sha256", SECRET).update(expectedData).digest("base64").replace(/\+/g, "-").replace(/\//g, "_");
  assert.equal(new URL(url).searchParams.get("sign"), expected);
  assert.equal(new URL(url).searchParams.get("timestamp"), timestamp);
  assert.equal(new URL(url).searchParams.get("nonce"), nonce);
  assert.equal(new URL(url).searchParams.get("as_attachment"), "true");
});

test("static root serves the workbench without a Dify connection", async () => {
  const context = await startServer({ difyApiKey: "", difySecretKey: "" });
  activeServers.push(context.server, context.upstream.server);
  const response = await fetch(`${context.baseUrl}/`);
  assert.equal(response.status, 200);
  assert.match(await response.text(), /智慧科研工作台/);
});

test("health reports an unconfigured integration honestly", async () => {
  const context = await startServer({ difyApiKey: "", difySecretKey: "" });
  activeServers.push(context.server, context.upstream.server);
  const response = await fetch(`${context.baseUrl}/api/health`);
  assert.deepEqual(await response.json(), { ok: true, difyConfigured: false });
});

test("health reports configuration without exposing secret values", async () => {
  const context = await startServer();
  activeServers.push(context.server, context.upstream.server);
  const response = await fetch(`${context.baseUrl}/api/health`);
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.deepEqual(payload, { ok: true, difyConfigured: true });
  assert.doesNotMatch(JSON.stringify(payload), /test-dify-secret|test-app-key/);
});

test("chat proxy forwards only the validated payload and streams SSE", async () => {
  const context = await startServer();
  activeServers.push(context.server, context.upstream.server);
  const response = await fetch(`${context.baseUrl}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      query: "hello",
      inputs: { task_profile: "lightweight" },
      user: "browser-user",
      conversation_id: "conversation-1",
      files: [{ type: "document", transfer_method: "local_file", upload_file_id: "file-1" }],
      response_mode: "blocking",
      api_key: "should-not-forward",
    }),
  });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("content-type"), "text/event-stream");
  assert.equal(await response.text(), 'data: {"event":"message","answer":"hello"}\n\ndata: {"event":"message_end"}\n\n');
  const request = context.upstream.requests.find((item) => item.url === "/v1/chat-messages");
  assert.ok(request);
  const body = JSON.parse(request.body);
  assert.deepEqual(body, {
    inputs: { task_profile: "lightweight" },
    query: "hello",
    user: "browser-user",
    response_mode: "streaming",
    conversation_id: "conversation-1",
    files: [{ type: "document", transfer_method: "local_file", upload_file_id: "file-1" }],
  });
  assert.equal(request.headers.authorization, "Bearer test-app-key");
});

test("upload proxy forwards one multipart file and returns the real Dify metadata", async () => {
  const context = await startServer();
  activeServers.push(context.server, context.upstream.server);
  const form = new FormData();
  form.append("file", new Blob(["# sample\n"], { type: "text/markdown" }), "sample.md");
  const response = await fetch(`${context.baseUrl}/api/files/upload`, { method: "POST", body: form });
  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), { id: "uploaded-file-1", name: "sample.md", size: 12 });
  const request = context.upstream.requests.find((item) => item.url === "/v1/files/upload");
  assert.ok(request);
  assert.match(request.body, /name="file"/);
  assert.match(request.body, /filename="sample\.md"/);
  assert.match(request.body, /name="user"/);
  assert.match(request.body, /test-user/);
});

test("chat proxy rejects remote or unknown file transfer methods", async () => {
  const context = await startServer();
  activeServers.push(context.server, context.upstream.server);
  for (const file of [
    { type: "document", transfer_method: "remote_url", url: "https://example.com/file.pdf" },
    { type: "document", transfer_method: "sandbox_file", upload_file_id: "file-1" },
  ]) {
    const response = await fetch(`${context.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: "read", files: [file] }),
    });
    assert.equal(response.status, 400);
  }
});

test("artifact proxy validates identifiers, signs afresh, and returns real bytes", async () => {
  const context = await startServer();
  activeServers.push(context.server, context.upstream.server);
  const response = await fetch(`${context.baseUrl}/api/artifacts/${TOOL_FILE_ID}.md`);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "real artifact bytes");
  assert.equal(response.headers.get("content-disposition"), 'attachment; filename="result.md"');
  const request = context.upstream.requests.find((item) => item.url.startsWith("/files/tools/"));
  assert.ok(request);
  assert.match(request.url, /timestamp=/);
  assert.match(request.url, /nonce=/);
  assert.doesNotMatch(request.url, /test-dify-secret/);

  const invalid = await fetch(`${context.baseUrl}/api/artifacts/not-a-uuid.md`);
  assert.equal(invalid.status, 400);
  const invalidExtension = await fetch(`${context.baseUrl}/api/artifacts/${TOOL_FILE_ID}.exe`);
  assert.equal(invalidExtension.status, 400);
});
