import test from "node:test";
import assert from "node:assert/strict";
import {
  MAX_UPLOAD_BYTES,
  artifactIdentity,
  canSubmit,
  validateUpload,
} from "../public/workflow.mjs";

test("send stays unavailable for blank, busy, or unfinished-upload requests", () => {
  assert.equal(canSubmit({ query: "   ", sending: false, attachments: [] }), false);
  assert.equal(canSubmit({ query: "summarize", sending: true, attachments: [] }), false);
  assert.equal(canSubmit({ query: "summarize", sending: false, attachments: [{ status: "uploading" }] }), false);
  assert.equal(canSubmit({ query: "summarize", sending: false, attachments: [{ status: "ready" }] }), true);
});

test("upload validation rejects empty, oversized, and unsupported files", () => {
  assert.equal(validateUpload({ name: "paper.md", size: 0 }), "文件内容为空");
  assert.equal(validateUpload({ name: "paper.pdf", size: MAX_UPLOAD_BYTES + 1 }), "文件超过 50 MB 上限");
  assert.equal(validateUpload({ name: "payload.exe", size: 10 }), "不支持 .exe 文件");
  assert.equal(validateUpload({ name: "paper.PDF", size: 10 }), "");
});

test("artifact identity rejects malformed files and supports deduplication", () => {
  assert.equal(
    artifactIdentity({ tool_file_id: "123e4567-e89b-12d3-a456-426614174000", extension: "MD" }),
    "123e4567-e89b-12d3-a456-426614174000.md",
  );
  assert.equal(
    artifactIdentity({ tool_file_id: "123E4567-E89B-12D3-A456-426614174000", extension: "md" }),
    "123e4567-e89b-12d3-a456-426614174000.md",
  );
  assert.equal(artifactIdentity({ tool_file_id: "not-a-uuid", extension: "md" }), "");
  assert.equal(artifactIdentity({ tool_file_id: "123e4567-e89b-12d3-a456-426614174000", extension: "exe" }), "");
});
