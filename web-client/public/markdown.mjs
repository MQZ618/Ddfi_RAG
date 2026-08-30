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

function isArtifactProxyPath(rawUrl) {
  return /^\/api\/artifacts\/[0-9a-f-]{36}\.[a-z0-9]{1,12}$/i.test(String(rawUrl));
}

function renderInline(value) {
  const source = String(value);
  const pattern = /(\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)|`([^`]+)`|\*\*([^*]+)\*\*|(https?:\/\/(?:api(?::5001)?|localhost(?::\d+)?)\/files\/tools\/[0-9a-f-]{36}\.[a-z0-9]{1,12}(?:\?[^\s<]*)?|\/files\/tools\/[0-9a-f-]{36}\.[a-z0-9]{1,12}(?:\?[^\s<]*)?|\/api\/artifacts\/[0-9a-f-]{36}\.[a-z0-9]{1,12}))/gi;
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
      } else if (isArtifactProxyPath(rawUrl)) {
        output += `<a href="${escapeHtml(rawUrl)}" download>${label}</a>`;
      } else if (isToolFileUrl(rawUrl)) {
        output += `<a href="#">${label}</a>`;
      } else if (/^https?:\/\//i.test(rawUrl)) {
        output += `<a href="${escapeHtml(rawUrl)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
      } else {
        output += `<a href="#">${label}</a>`;
      }
    } else if (match[4] !== undefined) {
      output += `<code>${escapeHtml(match[4])}</code>`;
    } else if (match[6] !== undefined) {
      const rewritten = artifactPath(match[6]);
      const safePath = isArtifactProxyPath(match[6]) ? match[6] : rewritten;
      output += safePath ? `<a href="${escapeHtml(safePath)}" download>下载文件</a>` : escapeHtml(match[6]);
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
  let list = null;
  let quote = [];
  const flushParagraph = () => {
    if (paragraph.length) blocks.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (list?.items.length) blocks.push(`<${list.type}>${list.items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</${list.type}>`);
    list = null;
  };
  const flushQuote = () => {
    if (quote.length) blocks.push(`<blockquote>${renderInline(quote.join(" "))}</blockquote>`);
    quote = [];
  };
  const flushAll = () => {
    flushParagraph();
    flushList();
    flushQuote();
  };
  const parseTableCells = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
  const isTableSeparator = (line) => /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  const renderTable = (headerLine, bodyLines) => {
    const headers = parseTableCells(headerLine);
    const rows = bodyLines.map(parseTableCells);
    const head = `<thead><tr>${headers.map((cell) => `<th>${renderInline(cell)}</th>`).join("")}</tr></thead>`;
    const body = rows.length ? `<tbody>${rows.map((row) => `<tr>${headers.map((_, index) => `<td>${renderInline(row[index] || "")}</td>`).join("")}</tr>`).join("")}</tbody>` : "";
    blocks.push(`<table>${head}${body}</table>`);
  };
  let codeLanguage = null;
  let codeLines = [];
  const flushCode = () => {
    if (codeLanguage === null) return;
    const className = codeLanguage ? ` class="language-${escapeHtml(codeLanguage)}"` : "";
    blocks.push(`<pre><code${className}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    codeLanguage = null;
    codeLines = [];
  };
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (codeLanguage !== null) {
      if (/^\s*```\s*$/.test(line)) flushCode();
      else codeLines.push(line);
      continue;
    }
    const fence = line.match(/^\s*```\s*([\w+-]*)\s*$/);
    if (fence) {
      flushAll();
      codeLanguage = fence[1] || "";
      continue;
    }
    if (/^\s*$/.test(line)) {
      flushAll();
    } else if (line.trim().startsWith(">")) {
      flushParagraph();
      flushList();
      quote.push(line.replace(/^\s*>\s?/, ""));
    } else if (index + 1 < lines.length && isTableSeparator(lines[index + 1]) && line.includes("|")) {
      flushAll();
      const bodyLines = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|") && !/^\s*$/.test(lines[index])) {
        bodyLines.push(lines[index]);
        index += 1;
      }
      index -= 1;
      renderTable(line, bodyLines);
    } else if (/^\s*\d+\.\s+/.test(line)) {
      flushParagraph();
      flushQuote();
      if (!list || list.type !== "ol") flushList();
      list ||= { type: "ol", items: [] };
      list.items.push(line.replace(/^\s*\d+\.\s+/, ""));
    } else if (/^\s*[-*]\s+/.test(line)) {
      flushParagraph();
      flushQuote();
      if (!list || list.type !== "ul") flushList();
      list ||= { type: "ul", items: [] };
      list.items.push(line.replace(/^\s*[-*]\s+/, ""));
    } else {
      flushList();
      flushQuote();
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
  flushCode();
  flushAll();
  return blocks.join("");
}
