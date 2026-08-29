const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EXTENSION_PATTERN = /^(?:md|markdown|txt|pdf|doc|docx|rtf|csv|json|yaml|yml|tex|bib|zip|png|jpg|jpeg|webp|gif|svg|xls|xlsx)$/;

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function parseToolFileUrl(rawUrl) {
  let url;
  try {
    const base = typeof window !== "undefined" && window.location?.origin ? window.location.origin : "http://local";
    url = new URL(rawUrl, base);
  } catch {
    return null;
  }
  const match = url.pathname.match(/^\/files\/tools\/([0-9a-f-]{36})\.([a-z0-9]{1,12})$/i);
  if (!match || !UUID_PATTERN.test(match[1]) || !EXTENSION_PATTERN.test(match[2].toLowerCase())) return null;
  const isRelative = rawUrl.startsWith("/");
  const isInternalHost = url.hostname === "api" || url.host === "api:5001" || url.hostname === "localhost";
  if (!isRelative && !isInternalHost) return null;
  return { id: match[1], extension: match[2].toLowerCase(), path: `/api/artifacts/${match[1]}.${match[2].toLowerCase()}` };
}

function artifactPath(rawUrl) {
  return parseToolFileUrl(rawUrl)?.path || null;
}

function isToolFileUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, "http://local");
    return url.pathname.startsWith("/files/tools/") && (rawUrl.startsWith("/") || url.hostname === "api" || url.hostname === "localhost");
  } catch {
    return false;
  }
}

function renderInline(value) {
  const source = String(value);
  const pattern = /(\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)|`([^`]+)`|\*\*([^*]+)\*\*)/g;
  let output = "";
  let cursor = 0;
  for (const match of source.matchAll(pattern)) {
    output += escapeHtml(source.slice(cursor, match.index));
    if (match[1]?.startsWith("[")) {
      const label = escapeHtml(match[2]);
      const rawUrl = match[3];
      const rewritten = artifactPath(rawUrl);
      if (rewritten) {
        output += `<a href="${rewritten}" download>${label}</a>`;
      } else if (isToolFileUrl(rawUrl)) {
        output += `<a href="#">${label}</a>`;
      } else if (/^https?:\/\//i.test(rawUrl)) {
        output += `<a href="${escapeHtml(rawUrl)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
      } else {
        output += `<a href="#">${label}</a>`;
      }
    } else if (match[4] !== undefined) {
      output += `<code>${escapeHtml(match[4])}</code>`;
    } else {
      output += `<strong>${escapeHtml(match[5])}</strong>`;
    }
    cursor = match.index + match[0].length;
  }
  return output + escapeHtml(source.slice(cursor));
}

export function renderMarkdown(markdown) {
  const lines = String(markdown || "").slice(0, 300_000).split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  let list = [];
  const flushParagraph = () => {
    if (paragraph.length) blocks.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (list.length) blocks.push(`<ul>${list.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>`);
    list = [];
  };
  for (const line of lines) {
    if (/^\s*$/.test(line)) {
      flushParagraph();
      flushList();
    } else if (/^\s*[-*]\s+/.test(line)) {
      flushParagraph();
      list.push(line.replace(/^\s*[-*]\s+/, ""));
    } else {
      flushList();
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        const level = heading[1].length;
        blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      } else {
        paragraph.push(line);
      }
    }
  }
  flushParagraph();
  flushList();
  return blocks.join("");
}
