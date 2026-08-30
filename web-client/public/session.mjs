export const SESSION_STORAGE_KEY = "research-workbench-session-v1";
const MAX_TEXT_LENGTH = 100_000;
const MAX_MESSAGES = 100;
const TRANSIENT_TOOL_URL_PATTERN = /(?:https?:\/\/(?:api(?::5001)?|localhost(?::\d+)?)|)\/files\/tools\/([0-9a-f-]{36})\.([a-z0-9]{1,12})(?:\?[^\s<)]*)?/gi;

function text(value) {
  const result = String(value ?? "");
  return result.length <= MAX_TEXT_LENGTH ? result : result.slice(0, MAX_TEXT_LENGTH);
}

function scrubTransientToolUrls(value) {
  return text(value).replace(TRANSIENT_TOOL_URL_PATTERN, (_, id, extension) => `/api/artifacts/${id}.${extension.toLowerCase()}`);
}

function normalizeMessage(message) {
  if (!message || !["user", "assistant"].includes(message.role) || typeof message.content !== "string") return null;
  return { role: message.role, content: scrubTransientToolUrls(message.content) };
}

export function readSession(storage) {
  let parsed;
  try {
    parsed = JSON.parse(storage?.getItem(SESSION_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (parsed.conversationId !== "" && typeof parsed.conversationId !== "string") return null;
  if (typeof parsed.draft !== "string" || !Array.isArray(parsed.messages)) return null;
  const messages = parsed.messages.map(normalizeMessage).filter(Boolean).slice(-MAX_MESSAGES);
  if (messages.length !== parsed.messages.length) return null;
  return { conversationId: text(parsed.conversationId), draft: text(parsed.draft), messages };
}

export function writeSession(storage, session) {
  if (!storage) return;
  const payload = {
    conversationId: text(session?.conversationId),
    draft: text(session?.draft),
    messages: (session?.messages || []).map(normalizeMessage).filter(Boolean).slice(-MAX_MESSAGES),
  };
  try {
    storage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Storage can be disabled or full; the live session remains usable.
  }
}

export function clearSession(storage) {
  try { storage?.removeItem(SESSION_STORAGE_KEY); } catch { /* ignore unavailable storage */ }
}
