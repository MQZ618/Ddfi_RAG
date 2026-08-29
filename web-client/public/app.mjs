import { renderMarkdown, escapeHtml, parseToolFileUrl } from "./markdown.mjs";

const state = { conversationId: "", attachments: [], sending: false, artifactCount: 0 };
const $ = (selector) => document.querySelector(selector);
const messages = $("#messages");
const queryInput = $("#query-input");
const sendButton = $("#send-button");
const attachmentList = $("#attachment-list");

function setText(selector, value) { const element = $(selector); if (element) element.textContent = value; }

function setEvidence(mode, detail = "") {
  const dot = $(".large-status-dot");
  const status = $("#evidence-status");
  if (!dot || !status) return;
  dot.className = `large-status-dot ${mode === "running" ? "running" : "pending"}`;
  const title = mode === "running" ? "正在处理研究任务" : mode === "complete" ? "回答已返回" : "等待研究任务";
  const copy = detail || (mode === "running" ? "正在等待 Agent 根据任务边界推进" : "提交材料后开始建立证据边界");
  status.querySelector("strong").textContent = title;
  status.querySelector("span").textContent = copy;
}

function updateAttachmentView() {
  attachmentList.replaceChildren();
  for (const attachment of state.attachments) {
    const chip = document.createElement("span");
    chip.className = `attachment-chip${attachment.uploading ? " uploading" : ""}`;
    chip.title = attachment.name;
    chip.textContent = attachment.uploading ? `${attachment.name} · 上传中` : attachment.name;
    if (!attachment.uploading) {
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
  const count = state.attachments.length;
  setText("#evidence-input", count ? `${count} 份材料已上传` : "尚未上传");
  const tag = $("#evidence-input-tag");
  if (tag) { tag.textContent = count ? "已载入" : "空"; tag.className = `evidence-tag ${count ? "teal" : "neutral"}`; }
}

function appendMessage(role, content, pending = false) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}${pending ? " pending-message" : ""}`;
  article.innerHTML = `<div class="message-avatar">${role === "user" ? "我" : "研"}</div><div class="message-content"><div class="message-meta"><strong>${role === "user" ? "你" : "科研助手"}</strong><span>刚刚</span></div><div class="message-body"></div></div>`;
  const body = article.querySelector(".message-body");
  if (role === "user") body.textContent = content;
  else body.innerHTML = pending ? escapeHtml(content) : renderMarkdown(content);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return body;
}

function addArtifact(file) {
  const parsed = file?.url ? parseToolFileUrl(file.url) : null;
  const artifactId = parsed?.id || file?.tool_file_id;
  if (!artifactId) return;
  const extension = (parsed?.extension || file.extension || (file.filename || file.name || "").split(".").pop() || "bin").toLowerCase();
  const name = file.filename || file.name || `科研交付.${extension}`;
  if (!/^[a-z0-9]{1,12}$/.test(extension)) return;
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

function applyEvent(event, assistantBody, buffer) {
  if (!event || typeof event !== "object") return buffer;
  if (event.conversation_id) state.conversationId = event.conversation_id;
  if (event.event === "message_file") addArtifact(event);
  if (Array.isArray(event.files)) event.files.forEach(addArtifact);
  if (["message", "agent_message"].includes(event.event) && typeof event.answer === "string") {
    buffer += event.answer;
    assistantBody.innerHTML = renderMarkdown(buffer);
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
  while (true) {
    const { value, done } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const chunks = pending.split(/\r?\n\r?\n/);
    pending = chunks.pop() || "";
    for (const chunk of chunks) {
      const data = chunk.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
      if (!data || data === "[DONE]") continue;
      try { answer = applyEvent(JSON.parse(data), assistantBody, answer); } catch (error) { if (error.message !== "Unexpected end of JSON input") throw error; }
    }
    if (done) break;
  }
  if (pending.trim()) {
    const data = pending.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
    if (data && data !== "[DONE]") answer = applyEvent(JSON.parse(data), assistantBody, answer);
  }
  return answer;
}

async function sendMessage(event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query || state.sending || state.attachments.some((item) => item.uploading)) return;
  state.sending = true;
  sendButton.disabled = true;
  queryInput.value = "";
  appendMessage("user", query);
  const assistantBody = appendMessage("assistant", "正在连接科研助手……", true);
  setEvidence("running", state.attachments.length ? "材料已提交，正在等待 Agent 返回" : "任务已提交，正在等待 Agent 返回");
  setText("#evidence-route", "已提交 Production v3");
  setText("#evidence-route-tag", "运行中");
  $("#evidence-route-tag").className = "evidence-tag amber";
  setText("#trace-status", "Agent 处理中");
  try {
    const payload = { query, inputs: {}, user: "research-web-user", ...(state.conversationId ? { conversation_id: state.conversationId } : {}), ...(state.attachments.length ? { files: state.attachments.map((file) => ({ type: file.type, transfer_method: "local_file", upload_file_id: file.id })) } : {}) };
    const response = await fetch("/api/chat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || `请求失败（${response.status}）`);
    assistantBody.parentElement.parentElement.classList.remove("pending-message");
    const answer = await readSse(response, assistantBody);
    if (!answer) assistantBody.innerHTML = "<p>Agent 没有返回可展示的文本。请检查任务输入或运行日志。</p>";
    setEvidence("complete", "回答已返回；关键结论仍需独立核验");
    setText("#evidence-route", "Production v3 已返回");
    setText("#evidence-route-tag", "已完成");
    $("#evidence-route-tag").className = "evidence-tag teal";
    setText("#trace-status", "本轮回答已接收");
    setText("#conversation-id", state.conversationId ? `会话 ${state.conversationId.slice(0, 8)}` : "无会话 ID");
  } catch (error) {
    assistantBody.innerHTML = `<p class="error-copy">${escapeHtml(error.message || "请求失败，请稍后重试")}</p>`;
    setEvidence("pending", "本轮未能完成，请检查代理和 Dify 配置");
    setText("#evidence-route", "未完成");
    setText("#evidence-route-tag", "错误");
    $("#evidence-route-tag").className = "evidence-tag neutral";
    setText("#trace-status", "需要检查配置");
  } finally {
    state.sending = false;
    sendButton.disabled = false;
    queryInput.focus();
  }
}

async function uploadFiles(event) {
  const files = [...event.target.files];
  event.target.value = "";
  for (const file of files) {
    const placeholder = { name: file.name, type: file.type || "application/octet-stream", uploading: true };
    state.attachments.push(placeholder);
    updateAttachmentView();
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const response = await fetch("/api/files/upload", { method: "POST", body: form });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.id) throw new Error(payload.error || `上传失败（${response.status}）`);
      Object.assign(placeholder, { id: payload.id, uploading: false, name: payload.name || file.name });
    } catch (error) {
      state.attachments = state.attachments.filter((item) => item !== placeholder);
      appendMessage("assistant", `材料“${file.name}”未上传成功：${error.message || "未知错误"}`);
    }
    updateAttachmentView();
  }
}

function resetSession() {
  state.conversationId = ""; state.attachments = []; state.artifactCount = 0;
  messages.innerHTML = `<article class="message assistant-message welcome-message"><div class="message-avatar">研</div><div class="message-content"><div class="message-meta"><strong>科研助手</strong><span>现在</span></div><div class="message-body"><p>新的研究会话已准备好。请告诉我你想推进的具体动作，或先上传研究材料。</p></div></div></article>`;
  $("#artifact-list").replaceChildren(); $("#artifact-panel").hidden = true; setText("#artifact-count", "0"); queryInput.value = ""; updateAttachmentView(); setEvidence("pending"); setText("#evidence-route", "等待分类"); setText("#evidence-route-tag", "待定"); $("#evidence-route-tag").className = "evidence-tag neutral"; setText("#conversation-id", "新会话"); setText("#trace-status", "项目侧代理就绪");
}

document.querySelectorAll(".task-card").forEach((card) => card.addEventListener("click", () => { queryInput.value = card.dataset.query || ""; queryInput.focus(); queryInput.scrollIntoView({ behavior: "smooth", block: "center" }); }));
$("#chat-form").addEventListener("submit", sendMessage);
$("#file-input").addEventListener("change", uploadFiles);
$("#new-session").addEventListener("click", resetSession);
$("#mobile-menu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => { document.querySelectorAll(".nav-item").forEach((other) => other.classList.remove("active")); item.classList.add("active"); $("#sidebar").classList.remove("open"); }));

fetch("/api/health").then((response) => response.json()).then((payload) => {
  const stateElement = $("#connection-state");
  stateElement.innerHTML = `<span class="state-dot"></span>${payload.difyConfigured ? "代理配置已就绪" : "等待配置 Dify"}`;
  setText("#trace-status", payload.difyConfigured ? "项目侧代理就绪" : "需要配置 Dify 环境变量");
}).catch(() => { setText("#connection-state", "代理不可用"); setText("#trace-status", "无法连接项目侧代理"); });
