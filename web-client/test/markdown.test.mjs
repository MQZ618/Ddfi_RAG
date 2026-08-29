import test from "node:test";
import assert from "node:assert/strict";
import { renderMarkdown, parseToolFileUrl } from "../public/markdown.mjs";

const TOOL_FILE_ID = "123e4567-e89b-12d3-a456-426614174000";

test("renderer escapes HTML and keeps ordinary links safe", () => {
  const html = renderMarkdown('<script>alert("x")</script>\n\n[论文](https://example.com/paper)');
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /href="https:\/\/example\.com\/paper"/);
  assert.match(html, /rel="noopener noreferrer"/);
});

test("renderer rewrites only validated Dify tool-file links to the same-origin proxy", () => {
  const html = renderMarkdown(
    `[下载](http://api:5001/files/tools/${TOOL_FILE_ID}.md?timestamp=old&signature=old)\n\n` +
      `[相对下载](/files/tools/${TOOL_FILE_ID}.pdf?timestamp=old&signature=old)`,
  );
  assert.match(html, new RegExp(`/api/artifacts/${TOOL_FILE_ID}\\.md`));
  assert.match(html, new RegExp(`/api/artifacts/${TOOL_FILE_ID}\\.pdf`));
  assert.doesNotMatch(html, /api:5001/);
  assert.match(html, /download/);
});

test("renderer does not rewrite malformed tool-file links", () => {
  const html = renderMarkdown("[bad](http://api:5001/files/tools/not-a-uuid.md)");
  assert.doesNotMatch(html, /api\/artifacts/);
  assert.doesNotMatch(html, /api:5001/);
  assert.match(html, /href="#"/);
});

test("tool-file parser extracts the artifact id from Dify message-file URLs", () => {
  assert.deepEqual(
    parseToolFileUrl(`http://api:5001/files/tools/${TOOL_FILE_ID}.docx?timestamp=old&sign=old`),
    { id: TOOL_FILE_ID, extension: "docx", path: `/api/artifacts/${TOOL_FILE_ID}.docx` },
  );
});
