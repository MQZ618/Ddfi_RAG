import test from "node:test";
import assert from "node:assert/strict";
import { clearSession, readSession, writeSession } from "../public/session.mjs";

test("session storage keeps safe text state and excludes attachment payloads", () => {
  const storage = new Map();
  const adapter = {
    getItem(key) { return storage.get(key) ?? null; },
    setItem(key, value) { storage.set(key, value); },
    removeItem(key) { storage.delete(key); },
  };
  writeSession(adapter, {
    conversationId: "conversation-1",
    draft: "继续核对结论",
    messages: [{ role: "user", content: "请总结" }, { role: "assistant", content: "已完成" }],
  });
  assert.deepEqual(readSession(adapter), {
    conversationId: "conversation-1",
    draft: "继续核对结论",
    messages: [{ role: "user", content: "请总结" }, { role: "assistant", content: "已完成" }],
  });
  assert.doesNotMatch(storage.values().next().value, /upload_file_id|secret|binary/);
  clearSession(adapter);
  assert.equal(readSession(adapter), null);
});

test("session storage removes transient signed Dify file URLs", () => {
  const storage = new Map();
  const adapter = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  };
  writeSession(adapter, {
    conversationId: "conversation-2",
    draft: "",
    messages: [{
      role: "assistant",
      content: "下载：http://api:5001/files/tools/123e4567-e89b-42d3-a456-426614174000.md?timestamp=old&nonce=old&sign=secret",
    }],
  });
  const raw = storage.get("research-workbench-session-v1");
  assert.doesNotMatch(raw, /api:5001|timestamp=|nonce=|sign=secret/);
  assert.match(raw, /\/api\/artifacts\/123e4567-e89b-42d3-a456-426614174000\.md/);
});

test("session storage rejects malformed or oversized state", () => {
  const storage = new Map([["research-workbench-session-v1", JSON.stringify({ conversationId: 3, messages: "bad" })]]);
  const adapter = { getItem: (key) => storage.get(key) ?? null };
  assert.equal(readSession(adapter), null);
});
