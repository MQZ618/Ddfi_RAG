import { renderMarkdown, escapeHtml, parseToolFileUrl } from "./markdown.mjs";
import { activateNavigationItem, navigateToSection } from "./navigation.mjs";
import { artifactIdentity, canSubmit, validateUpload } from "./workflow.mjs";
import { clearSession, readSession, writeSession } from "./session.mjs";

const state = {
  conversationId: "",
  attachments: [],
  sending: false,
  artifactCount: 0,
  artifactKeys: new Set(),
  currentController: null,
  lastQuery: "",
  history: [],
};
const $ = (selector) => document.querySelector(selector);
const messages = $("#messages");
const queryInput = $("#query-input");
const sendButton = $("#send-button");
const stopButton = $("#stop-button");
const retryButton = $("#retry-button");
const attachmentList = $("#attachment-list");

function setText(selector, value) { const element = $(selector); if (element) element.textContent = value; }

function getBrowserStorage() {
  try { return window.localStorage; } catch { return null; }
}

function persistSession() {
  writeSession(getBrowserStorage(), { conversationId: state.conversationId, draft: queryInput.value, messages: state.history });
}

function setEvidence(mode, detail = "") {
  const dot = $(".large-status-dot");
  const status = $("#evidence-status");
  if (!dot || !status) return;
  dot.className = `large-status-dot ${mode === "running" ? "running" : mode === "complete" ? "complete" : "pending"}`;
  const title = mode === "running" ? "正在处理研究任务" : mode === "complete" ? "回答已返回" : "等待研究任务";
  const copy = detail || (mode === "running" ? "正在等待 Agent 根据任务边界推进" : "提交材料后开始建立证据边界");
  status.querySelector("strong").textContent = title;
  status.querySelector(".evidence-status-copy").textContent = copy;
}

function updateAttachmentView() {
  attachmentList.replaceChildren();
  for (const attachment of state.attachments) {
    const chip = document.createElement("span");
    chip.className = `attachment-chip ${attachment.status}`;
    chip.title = attachment.name;
    const status = attachment.status === "uploading" ? " · 上传中" : attachment.status === "error" ? " · 上传失败" : "";
    chip.append(`${attachment.name}${status}`);
    if (attachment.status === "error") {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.setAttribute("aria-label", `重试上传 ${attachment.name}`);
      retry.textContent = "重试";
      retry.addEventListener("click", () => uploadAttachment(attachment));
      chip.append(retry);
    }
    if (attachment.status !== "uploading") {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `移除 ${attachment.name}`);
      remove.textContent = "×";
      remove.addEventListener("click", () => {
        state.attachments = state.attachments.filter((item) => item !== attachment);
        updateAttachmentView();
        updateEvidenceInput();
      });
      chip.append(remove);
    }
    attachmentList.append(chip);
  }
  updateEvidenceInput();
}

function updateEvidenceInput() {
  const readyCount = state.attachments.filter((file) => file.status === "ready").length;
  const pendingCount = state.attachments.filter((file) => file.status === "uploading").length;
  const errorCount = state.attachments.filter((file) => file.status === "error").length;
  const detail = pendingCount ? `${pendingCount} 份上传中` : errorCount ? `${errorCount} 份上传失败` : readyCount ? `${readyCount} 份材料已上传` : "尚未上传";
  setText("#evidence-input", detail);
  const tag = $("#evidence-input-tag");
  if (tag) {
    tag.textContent = pendingCount ? "上传中" : errorCount ? "需处理" : readyCount ? "已载入" : "空";
    tag.className = `evidence-tag ${readyCount && !pendingCount && !errorCount ? "teal" : pendingCount ? "amber" : "neutral"}`;
  }
}

function appendMessage(role, content, pending = false, persist = true) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}${pending ? " pending-message" : ""}`;
  article.innerHTML = `<div class="message-avatar">${role === "user" ? "我" : "研"}</div><div class="message-content"><div class="message-meta"><strong>${role === "user" ? "你" : "科研助手"}</strong><span>刚刚</span></div><div class="message-body"></div></div>`;
  const body = article.querySelector(".message-body");
  if (role === "user") body.textContent = content;
  else body.innerHTML = pending ? escapeHtml(content) : renderMarkdown(content);
  article.dataset.historyIndex = String(state.history.length);
  state.history.push({ role, content });
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  if (persist) persistSession();
  return body;
}

function addArtifact(file) {
  const parsed = file?.url ? parseToolFileUrl(file.url) : null;
  const artifactId = parsed?.id || file?.tool_file_id;
  if (!artifactId) return;
  const extension = (parsed?.extension || file.extension || (file.filename || file.name || "").split(".").pop() || "bin").toLowerCase();
  const name = file.filename || file.name || `科研交付.${extension}`;
  if (!/^[a-z0-9]{1,12}$/.test(extension)) return;
  const key = artifactIdentity({ tool_file_id: artifactId, extension });
  if (!key || state.artifactKeys.has(key)) return;
  state.artifactKeys.add(key);
  const panel = $("#artifact-panel");
  const list = $("#artifact-list");
  state.artifactCount += 1;
  setText("#artifact-count", String(state.artifactCount));
  panel.hidden = false;
  const card = document.createElement("div");
  card.className = "artifact-card";
  card.innerHTML = `<span class="artifact-card-icon">${escapeHtml(extension.toUpperCase().slice(0, 5))}</span><span class="artifact-card-info"><strong>${escapeHtml(name)}</strong><span>真实文件 · 已接收</span></span><a class="artifact-download" href="/api/artifacts/${encodeURIComponent(artifactId)}.${encodeURIComponent(extension)}" download aria-label="下载 ${escapeHtml(name)}">↓</a>`;
  list.append(card);
}

function addArtifactsFromAnswer(answer) {
  const pattern = /(?:https?:\/\/(?:api(?::5001)?|localhost(?::\d+)?)|)\/files\/tools\/[0-9a-f-]{36}\.[a-z0-9]{1,12}(?:\?[^\s<)]+)/gi;
  for (const match of String(answer).matchAll(pattern)) {
    const parsed = parseToolFileUrl(match[0]);
    if (parsed) addArtifact({ url: match[0], name: `科研交付.${parsed.extension}` });
  }
}

function applyEvent(event, assistantBody, buffer, streamState) {
  if (!event || typeof event !== "object") return buffer;
  if (event.conversation_id) state.conversationId = event.conversation_id;
  if (event.event === "message_file") addArtifact(event);
  if (Array.isArray(event.files)) event.files.forEach(addArtifact);
  if (event.event === "agent_message") streamState.sawAgentMessage = true;
  if (event.event === "message" && streamState.sawAgentMessage) return buffer;
  if (["message", "agent_message"].includes(event.event) && typeof event.answer === "string") {
    buffer += event.answer;
    addArtifactsFromAnswer(buffer);
    assistantBody.innerHTML = renderMarkdown(buffer);
    const historyIndex = Number(assistantBody.closest(".message")?.dataset.historyIndex);
    if (Number.isInteger(historyIndex) && state.history[historyIndex]) {
      state.history[historyIndex].content = buffer;
      persistSession();
    }
    messages.scrollTop = messages.scrollHeight;
  }
  if (event.event === "error") throw new Error(event.message || "Dify 返回了错误");
  return buffer;
}

async function readSse(response, assistantBody) {
  if (!response.body) return "";
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let answer = "";
  const streamState = { sawAgentMessage: false };
  while (true) {
    const { value, done } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const chunks = pending.split(/\r?\n\r?\n/);
    pending = chunks.pop() || "";
    for (const chunk of chunks) {
      const data = chunk.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
      if (!data || data === "[DONE]") continue;
      try { answer = applyEvent(JSON.parse(data), assistantBody, answer, streamState); } catch (error) { if (error.message !== "Unexpected end of JSON input") throw error; }
    }
    if (done) break;
  }
  if (pending.trim()) {
    const data = pending.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
    if (data && data !== "[DONE]") answer = applyEvent(JSON.parse(data), assistantBody, answer, streamState);
  }
  return answer;
}

function setRequestControls(mode) {
  const running = mode === "running";
  stopButton.hidden = !running;
  retryButton.hidden = mode !== "retry";
  sendButton.hidden = running;
  sendButton.disabled = running;
  $("#new-session").disabled = running;
}

async function submitQuery(query) {
  query = String(query || "").trim();
  if (!canSubmit({ query, sending: state.sending, attachments: state.attachments })) return;
  state.sending = true;
  state.lastQuery = query;
  const controller = new AbortController();
  state.currentController = controller;
  setRequestControls("running");
  queryInput.value = "";
  appendMessage("user", query);
  const assistantBody = appendMessage("assistant", "正在连接科研助手……", true);
  setEvidence("running", state.attachments.length ? "材料已提交，正在等待 Agent 返回" : "任务已提交，正在等待 Agent 返回");
  setText("#evidence-route", "已提交科研助手");
  setText("#evidence-route-tag", "运行中");
  $("#evidence-route-tag").className = "evidence-tag amber";
  setText("#trace-status", "Agent 处理中");
  setText("#composer-status", "正在生成回答；你可以随时停止。已收到的内容会保留。");
  try {
    const readyFiles = state.attachments.filter((file) => file.status === "ready");
    const payload = { query, inputs: {}, user: "research-web-user", ...(state.conversationId ? { conversation_id: state.conversationId } : {}), ...(readyFiles.length ? { files: readyFiles.map((file) => ({ type: file.type, transfer_method: "local_file", upload_file_id: file.id })) } : {}) };
    const response = await fetch("/api/chat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload), signal: controller.signal });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || `请求失败（${response.status}）`);
    assistantBody.parentElement.parentElement.classList.remove("pending-message");
    const answer = await readSse(response, assistantBody);
    if (!answer) assistantBody.innerHTML = "<p>Agent 没有返回可展示的文本。请检查任务输入或运行日志。</p>";
    const historyIndex = Number(assistantBody.closest(".message")?.dataset.historyIndex);
    if (Number.isInteger(historyIndex) && state.history[historyIndex]) state.history[historyIndex].content = answer || "Agent 没有返回可展示的文本。请检查任务输入或运行日志。";
    setEvidence("complete", "回答已返回；关键结论仍需独立核验");
    setText("#evidence-route", "科研助手已返回");
    setText("#evidence-route-tag", "已完成");
    $("#evidence-route-tag").className = "evidence-tag teal";
    setText("#trace-status", "本轮回答已接收");
    setText("#conversation-id", state.conversationId ? `会话 ${state.conversationId.slice(0, 8)}` : "无会话 ID");
    setText("#composer-status", "回答已返回。请对关键论断进行独立核验。");
    setRequestControls("idle");
  } catch (error) {
    const stopped = controller.signal.aborted || error?.name === "AbortError";
    const message = stopped ? "已停止生成" : (error.message || "请求失败，请稍后重试");
    if (stopped && assistantBody.textContent.trim() && !assistantBody.closest(".pending-message")) {
      assistantBody.insertAdjacentHTML("beforeend", `<p class="request-note">${message}</p>`);
    } else {
      assistantBody.innerHTML = `<p class="error-copy">${escapeHtml(message)}</p>`;
    }
    const historyIndex = Number(assistantBody.closest(".message")?.dataset.historyIndex);
    if (Number.isInteger(historyIndex) && state.history[historyIndex]) state.history[historyIndex].content = assistantBody.textContent;
    queryInput.value = query;
    persistSession();
    setEvidence("pending", stopped ? "生成已由用户停止，可重试本轮" : "本轮未能完成，可检查配置后重试");
    setText("#evidence-route", "未完成");
    setText("#evidence-route-tag", stopped ? "已停止" : "错误");
    $("#evidence-route-tag").className = "evidence-tag neutral";
    setText("#trace-status", stopped ? "用户已停止本轮" : "需要检查配置");
    setText("#composer-status", stopped ? "本轮已停止，输入已恢复。" : "本轮失败，输入已恢复，可重试。");
    setRequestControls("retry");
  } finally {
    state.sending = false;
    if (state.currentController === controller) state.currentController = null;
    queryInput.focus();
  }
}

function sendMessage(event) {
  event.preventDefault();
  return submitQuery(queryInput.value);
}

async function uploadAttachment(attachment) {
  attachment.status = "uploading";
  attachment.error = "";
  updateAttachmentView();
  try {
    const form = new FormData();
    form.append("file", attachment.file, attachment.file.name);
    const response = await fetch("/api/files/upload", { method: "POST", body: form });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.id) throw new Error(payload.error || `上传失败（${response.status}）`);
    Object.assign(attachment, { id: payload.id, status: "ready", name: payload.name || attachment.file.name });
  } catch (error) {
    attachment.status = "error";
    attachment.error = error.message || "未知错误";
    appendMessage("assistant", `材料“${attachment.name}”未上传成功：${attachment.error}。你可以在材料标签中重试或移除。`);
  }
  updateAttachmentView();
}

async function uploadFiles(event) {
  const files = [...event.target.files];
  event.target.value = "";
  for (const file of files) {
    const error = validateUpload(file);
    if (error) {
      appendMessage("assistant", `材料“${file.name}”未上传：${error}。`);
      continue;
    }
    const attachment = { name: file.name, type: file.type || "application/octet-stream", file, status: "uploading", error: "" };
    state.attachments.push(attachment);
    await uploadAttachment(attachment);
  }
}

function resetSession() {
  state.currentController?.abort();
  clearSession(getBrowserStorage());
  state.conversationId = ""; state.attachments = []; state.artifactCount = 0; state.artifactKeys = new Set(); state.lastQuery = ""; state.history = [];
  messages.innerHTML = `<article class="message assistant-message welcome-message"><div class="message-avatar">研</div><div class="message-content"><div class="message-meta"><strong>科研助手</strong><span>现在</span></div><div class="message-body"><p>新的研究会话已准备好。请告诉我你想推进的具体动作，或先上传研究材料。</p></div></div></article>`;
  $("#artifact-list").replaceChildren(); $("#artifact-panel").hidden = true; setText("#artifact-count", "0"); queryInput.value = ""; updateAttachmentView(); setEvidence("pending"); setText("#evidence-route", "尚未提交"); setText("#evidence-route-tag", "待命"); $("#evidence-route-tag").className = "evidence-tag neutral"; setText("#conversation-id", "新会话"); setText("#trace-status", "项目侧代理就绪"); setText("#composer-status", "回答会受当前材料和 Agent 配置约束。请对关键论断进行独立核验。"); setRequestControls("idle");
}

document.querySelectorAll(".task-card").forEach((card) => card.addEventListener("click", () => { queryInput.value = card.dataset.query || ""; queryInput.focus(); queryInput.scrollIntoView({ behavior: "smooth", block: "center" }); }));
$("#chat-form").addEventListener("submit", sendMessage);
$("#file-input").addEventListener("change", uploadFiles);
$("#new-session").addEventListener("click", resetSession);
stopButton.addEventListener("click", () => state.currentController?.abort());
retryButton.addEventListener("click", () => submitQuery(state.lastQuery));
queryInput.addEventListener("input", persistSession);
queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $("#chat-form").requestSubmit();
  }
});
function setMobileMenu(open) {
  $("#sidebar").classList.toggle("open", open);
  $("#mobile-menu").setAttribute("aria-expanded", String(open));
  $("#mobile-menu").setAttribute("aria-label", open ? "关闭导航" : "打开导航");
}
$("#mobile-menu").addEventListener("click", () => setMobileMenu(!$("#sidebar").classList.contains("open")));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setMobileMenu(false);
});
const navItems = [...document.querySelectorAll(".nav-item")];
navItems.forEach((item) => item.addEventListener("click", () => {
  if (!navigateToSection(item, document)) return;
  activateNavigationItem(item, navItems);
  setMobileMenu(false);
}));

const savedSession = readSession(getBrowserStorage());
if (savedSession && (savedSession.messages.length || savedSession.draft)) {
  state.conversationId = savedSession.conversationId;
  state.history = [];
  if (savedSession.messages.length) {
    messages.replaceChildren();
    for (const message of savedSession.messages) appendMessage(message.role, message.content, false, false);
  }
  queryInput.value = savedSession.draft;
  setText("#conversation-id", state.conversationId ? `会话 ${state.conversationId.slice(0, 8)}` : "草稿");
  setText("#trace-status", "已恢复文字会话；附件需重新上传");
}

fetch("/api/health?probe=1").then((response) => response.json()).then((payload) => {
  const stateElement = $("#connection-state");
  const status = !payload.difyConfigured ? "等待配置 Dify" : payload.difyReachable ? "Dify 已连接" : "代理已配置，Dify 不可达";
  stateElement.innerHTML = `<span class="state-dot"></span>${status}`;
  setText("#trace-status", !payload.difyConfigured ? "需要配置 Dify 环境变量" : payload.difyReachable ? "项目侧代理就绪" : "请检查 Dify 服务");
}).catch(() => { setText("#connection-state", "代理不可用"); setText("#trace-status", "无法连接项目侧代理"); });
