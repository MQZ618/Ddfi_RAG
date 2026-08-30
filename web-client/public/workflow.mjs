export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SUPPORTED_EXTENSIONS = new Set([
  "md", "markdown", "txt", "pdf", "doc", "docx", "rtf", "csv", "json", "yaml",
  "yml", "tex", "bib", "zip", "png", "jpg", "jpeg", "webp", "gif", "svg", "xls", "xlsx",
]);

export function canSubmit({ query, sending, attachments }) {
  return Boolean(String(query || "").trim())
    && !sending
    && !attachments.some((file) => file.status !== "ready");
}

export function validateUpload(file) {
  if (!file?.size) return "文件内容为空";
  if (file.size > MAX_UPLOAD_BYTES) return "文件超过 50 MB 上限";
  const extension = String(file.name || "").split(".").pop()?.toLowerCase() || "";
  return SUPPORTED_EXTENSIONS.has(extension) ? "" : `不支持 .${extension || "未知"} 文件`;
}

export function artifactIdentity(file) {
  const id = String(file?.tool_file_id || "").toLowerCase();
  const extension = String(file?.extension || "").toLowerCase();
  return UUID_PATTERN.test(id) && SUPPORTED_EXTENSIONS.has(extension) ? `${id}.${extension}` : "";
}
