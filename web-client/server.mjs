import http from "node:http";
import crypto from "node:crypto";
import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PUBLIC_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "public");
const MAX_JSON_BYTES = 2 * 1024 * 1024;
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EXTENSION_PATTERN = /^(?:md|markdown|txt|pdf|doc|docx|rtf|csv|json|yaml|yml|tex|bib|zip|png|jpg|jpeg|webp|gif|svg|xls|xlsx)$/;

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

export function parseDotEnv(contents, target = {}) {
  for (const line of String(contents).split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match || target[match[1]] !== undefined) continue;
    let value = match[2].trim();
    if ((value.startsWith("\"") && value.endsWith("\"")) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    target[match[1]] = value;
  }
  return target;
}

function loadLocalDotEnv() {
  try {
    parseDotEnv(fsSync.readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".env"), "utf8"), process.env);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}

loadLocalDotEnv();

export function normalizeBaseUrl(value, fallback = "http://localhost") {
  const candidate = String(value || fallback).trim();
  const url = new URL(candidate);
  let pathname = url.pathname.replace(/\/+$/, "");
  if (pathname === "/v1") pathname = "";
  url.pathname = pathname;
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

export function readConfig(env = process.env) {
  const rawPort = Number.parseInt(env.PORT || "3000", 10);
  const port = Number.isInteger(rawPort) && rawPort >= 0 && rawPort <= 65535 ? rawPort : 3000;
  return {
    port,
    difyApiBaseUrl: normalizeBaseUrl(env.DIFY_API_BASE_URL || "http://localhost"),
    difyFileBaseUrl: normalizeBaseUrl(env.DIFY_FILE_BASE_URL || env.DIFY_API_BASE_URL || "http://localhost"),
    difyApiKey: String(env.DIFY_API_KEY || "").trim(),
    difySecretKey: String(env.DIFY_SECRET_KEY || "").trim(),
    difyUserId: String(env.DIFY_USER_ID || "research-web-user").trim() || "research-web-user",
    difyAppId: String(env.DIFY_APP_ID || "").trim(),
  };
}

function assertConfigured(config, requirement) {
  const missing = requirement === "chat" ? ["difyApiKey"] : ["difySecretKey"];
  if (missing.some((key) => !config[key])) {
    const error = new Error("Dify integration is not configured");
    error.statusCode = 503;
    throw error;
  }
}

function jsonResponse(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "content-length": Buffer.byteLength(body),
  });
  response.end(body);
}

function errorMessage(error) {
  if (error?.statusCode === 400) return error.message;
  if (error?.statusCode === 413) return "Request is too large";
  if (error?.statusCode === 503) return "Dify integration is not configured";
  return "Request failed";
}

function fail(message, statusCode = 400) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

async function readBody(request, maxBytes) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    let settled = false;
    const rejectOnce = (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    };
    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > maxBytes) {
        request.destroy();
        rejectOnce(fail("Request is too large", 413));
        return;
      }
      chunks.push(chunk);
    });
    request.on("end", () => {
      if (!settled) {
        settled = true;
        resolve(Buffer.concat(chunks));
      }
    });
    request.on("error", rejectOnce);
  });
}

async function readJson(request) {
  let body;
  try {
    body = JSON.parse((await readBody(request, MAX_JSON_BYTES)).toString("utf8"));
  } catch (error) {
    if (error?.statusCode === 413) throw error;
    throw fail("Invalid JSON body");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) throw fail("JSON body must be an object");
  return body;
}

function validateFiles(files) {
  if (files === undefined) return undefined;
  if (!Array.isArray(files) || files.length > 20) throw fail("files must be an array with at most 20 items");
  return files.map((file) => {
    if (!file || typeof file !== "object" || Array.isArray(file)) throw fail("invalid file descriptor");
    const allowed = {};
    for (const key of ["type", "transfer_method", "upload_file_id", "url"]) {
      if (file[key] !== undefined) allowed[key] = file[key];
    }
    if (typeof allowed.type !== "string" || typeof allowed.transfer_method !== "string") {
      throw fail("file descriptor requires type and transfer_method");
    }
    if (allowed.transfer_method !== "local_file") throw fail("only local_file descriptors are supported");
    if (typeof allowed.upload_file_id !== "string" || allowed.upload_file_id.length > 200) {
      throw fail("local_file descriptor requires upload_file_id");
    }
    return allowed;
  });
}

function validateChatPayload(body, config) {
  if (typeof body.query !== "string" || body.query.trim() === "") throw fail("query is required");
  if (body.query.length > 100_000) throw fail("query is too long");
  if (body.inputs !== undefined && (!body.inputs || typeof body.inputs !== "object" || Array.isArray(body.inputs))) {
    throw fail("inputs must be an object");
  }
  if (body.user !== undefined && (typeof body.user !== "string" || body.user.length > 200)) {
    throw fail("user must be a short string");
  }
  if (body.conversation_id !== undefined && (typeof body.conversation_id !== "string" || body.conversation_id.length > 200)) {
    throw fail("conversation_id must be a short string");
  }
  return {
    inputs: body.inputs || {},
    query: body.query,
    user: body.user || config.difyUserId,
    response_mode: "streaming",
    ...(body.conversation_id ? { conversation_id: body.conversation_id } : {}),
    ...(body.files !== undefined ? { files: validateFiles(body.files) } : {}),
  };
}

async function proxyResponse(response, upstream, streaming = false) {
  const contentType = upstream.headers.get("content-type") || (streaming ? "text/event-stream" : "application/json");
  const headers = {
    "content-type": contentType,
    "cache-control": streaming ? "no-cache, no-transform" : "no-store",
  };
  if (upstream.headers.get("content-disposition")) headers["content-disposition"] = upstream.headers.get("content-disposition");
  if (upstream.headers.get("content-length")) headers["content-length"] = upstream.headers.get("content-length");
  response.writeHead(upstream.status, headers);
  if (!upstream.body) {
    response.end();
    return;
  }
  for await (const chunk of upstream.body) response.write(chunk);
  response.end();
}

async function isDifyReachable(config) {
  if (!config.difyApiKey) return false;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3_000);
  try {
    const upstream = await fetch(`${config.difyApiBaseUrl}/v1/info`, {
      headers: { authorization: `Bearer ${config.difyApiKey}` },
      redirect: "manual",
      signal: controller.signal,
    });
    if (upstream.body) await upstream.body.cancel();
    return upstream.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

function abortWhenClientDisconnects(response) {
  const controller = new AbortController();
  const onClose = () => {
    if (!response.writableEnded) controller.abort();
  };
  response.on("close", onClose);
  return { controller, cleanup: () => response.off("close", onClose) };
}

export function buildSignedToolFileUrl({ baseUrl, toolFileId, extension, secretKey, timestamp, nonce }) {
  if (!UUID_PATTERN.test(toolFileId)) throw fail("invalid tool file id");
  if (!EXTENSION_PATTERN.test(extension)) throw fail("invalid file extension");
  if (!secretKey) throw fail("Dify file signing is not configured", 503);
  const signedTimestamp = String(timestamp ?? Math.floor(Date.now() / 1000));
  const signedNonce = String(nonce ?? crypto.randomBytes(16).toString("hex"));
  const data = `file-preview|${toolFileId}|${signedTimestamp}|${signedNonce}`;
  const signature = crypto.createHmac("sha256", secretKey).update(data).digest("base64").replace(/\+/g, "-").replace(/\//g, "_");
  const url = new URL(`/files/tools/${toolFileId}.${extension}`, normalizeBaseUrl(baseUrl));
  url.searchParams.set("timestamp", signedTimestamp);
  url.searchParams.set("nonce", signedNonce);
  url.searchParams.set("sign", signature);
  url.searchParams.set("as_attachment", "true");
  return url.toString();
}

function parseArtifactPath(pathname) {
  const match = pathname.match(/^\/api\/artifacts\/([0-9a-f-]{36})\.([a-z0-9]{1,12})$/i);
  if (!match || !UUID_PATTERN.test(match[1]) || !EXTENSION_PATTERN.test(match[2].toLowerCase())) throw fail("invalid artifact path");
  return { toolFileId: match[1], extension: match[2].toLowerCase() };
}

function parseMultipart(body, contentType) {
  const match = String(contentType || "").match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  if (!match) throw fail("multipart boundary is required");
  const boundary = Buffer.from(`--${match[1] || match[2]}`);
  let cursor = 0;
  while (cursor < body.length) {
    const marker = body.indexOf(boundary, cursor);
    if (marker < 0) break;
    const partStart = marker + boundary.length;
    if (body.subarray(partStart, partStart + 2).toString() === "--") break;
    const headersStart = partStart + 2;
    const headersEnd = body.indexOf(Buffer.from("\r\n\r\n"), headersStart);
    if (headersEnd < 0) break;
    const headersText = body.subarray(headersStart, headersEnd).toString("utf8");
    const dataStart = headersEnd + 4;
    const nextMarker = body.indexOf(Buffer.from(`\r\n${boundary.toString()}`), dataStart);
    if (nextMarker < 0) break;
    const disposition = headersText.match(/content-disposition:\s*([^\r\n]+)/i)?.[1] || "";
    const filename = disposition.match(/filename="([^"]*)"/i)?.[1];
    const name = disposition.match(/(?:^|;)\s*name="([^"]+)"/i)?.[1];
    if (name === "file" && filename) {
      const contentTypeHeader = headersText.match(/content-type:\s*([^\r\n]+)/i)?.[1]?.trim();
      return {
        filename: path.basename(filename) || "upload.bin",
        contentType: contentTypeHeader || "application/octet-stream",
        data: body.subarray(dataStart, nextMarker),
      };
    }
    cursor = nextMarker + 2;
  }
  throw fail("a file field is required");
}

async function handleApi(request, response, config) {
  const url = new URL(request.url, "http://localhost");
  if (request.method === "GET" && url.pathname === "/api/health") {
    const difyConfigured = Boolean(config.difyApiKey && config.difySecretKey);
    const payload = { ok: true, difyConfigured };
    if (url.searchParams.get("probe") === "1") payload.difyReachable = difyConfigured && await isDifyReachable(config);
    jsonResponse(response, 200, payload);
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/chat") {
    assertConfigured(config, "chat");
    const payload = validateChatPayload(await readJson(request), config);
    const abort = abortWhenClientDisconnects(response);
    let upstream;
    try {
      upstream = await fetch(`${config.difyApiBaseUrl}/v1/chat-messages`, {
        method: "POST",
        headers: { authorization: `Bearer ${config.difyApiKey}`, "content-type": "application/json" },
        body: JSON.stringify(payload),
        redirect: "manual",
        signal: abort.controller.signal,
      });
    } catch {
      abort.cleanup();
      if (abort.controller.signal.aborted) return;
      throw fail("Dify chat is unavailable", 502);
    }
    try {
      await proxyResponse(response, upstream, true);
    } finally {
      abort.cleanup();
    }
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/files/upload") {
    assertConfigured(config, "chat");
    const uploaded = parseMultipart(await readBody(request, MAX_UPLOAD_BYTES), request.headers["content-type"]);
    const form = new FormData();
    form.append("file", new Blob([uploaded.data], { type: uploaded.contentType }), uploaded.filename);
    form.append("user", config.difyUserId);
    let upstream;
    try {
      upstream = await fetch(`${config.difyApiBaseUrl}/v1/files/upload`, {
        method: "POST",
        headers: { authorization: `Bearer ${config.difyApiKey}` },
        body: form,
        redirect: "manual",
      });
    } catch {
      throw fail("Dify file upload is unavailable", 502);
    }
    await proxyResponse(response, upstream);
    return;
  }

  if (request.method === "GET" && url.pathname.startsWith("/api/artifacts/")) {
    const artifact = parseArtifactPath(url.pathname);
    assertConfigured(config, "artifact");
    const signedUrl = buildSignedToolFileUrl({
      baseUrl: config.difyFileBaseUrl,
      toolFileId: artifact.toolFileId,
      extension: artifact.extension,
      secretKey: config.difySecretKey,
    });
    let upstream;
    try {
      upstream = await fetch(signedUrl, { redirect: "manual" });
    } catch {
      throw fail("Artifact is unavailable", 502);
    }
    if (!upstream.ok || upstream.status >= 300) {
      if (upstream.body) await upstream.body.cancel();
      throw fail("Artifact is unavailable", 502);
    }
    await proxyResponse(response, upstream);
    return;
  }

  throw fail("Not found", 404);
}

async function serveStatic(request, response) {
  if (!['GET', 'HEAD'].includes(request.method)) throw fail("Method not allowed", 405);
  const url = new URL(request.url, "http://localhost");
  let relativePath;
  try {
    relativePath = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
  } catch {
    throw fail("Not found", 404);
  }
  if (relativePath.includes("\0") || relativePath.split("/").includes("..")) throw fail("Not found", 404);
  const filePath = path.resolve(PUBLIC_ROOT, `.${relativePath}`);
  if (filePath !== PUBLIC_ROOT && !filePath.startsWith(`${PUBLIC_ROOT}${path.sep}`)) throw fail("Not found", 404);
  let data;
  try {
    data = await fs.readFile(filePath);
  } catch {
    throw fail("Not found", 404);
  }
  const extension = path.extname(filePath).toLowerCase();
  const headers = { "content-type": CONTENT_TYPES[extension] || "application/octet-stream", "cache-control": "no-cache" };
  if (request.method === "HEAD") {
    headers["content-length"] = data.length;
    response.writeHead(200, headers);
    response.end();
  } else {
    response.writeHead(200, headers);
    response.end(data);
  }
}

export function createServer(config = readConfig()) {
  return http.createServer((request, response) => {
    if (config.upstreamHandler) {
      Promise.resolve(config.upstreamHandler(request, response)).catch(() => {
        if (!response.headersSent) jsonResponse(response, 500, { error: "upstream test handler failed" });
      });
      return;
    }
    (async () => {
      try {
        if (request.url?.startsWith("/api/")) await handleApi(request, response, config);
        else await serveStatic(request, response);
      } catch (error) {
        const statusCode = Number.isInteger(error?.statusCode) ? error.statusCode : 500;
        if (!response.headersSent) jsonResponse(response, statusCode, { error: errorMessage(error) });
        else response.destroy();
      }
    })();
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const config = readConfig();
  const server = createServer(config);
  server.listen(config.port, "127.0.0.1", () => {
    const address = server.address();
    console.log(`Smart research workbench listening on http://127.0.0.1:${address.port}`);
  });
}
