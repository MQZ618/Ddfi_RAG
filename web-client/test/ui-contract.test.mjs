import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { activateNavigationItem, navigateToSection } from "../public/navigation.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const html = await readFile(resolve(here, "../public/index.html"), "utf8");
const app = await readFile(resolve(here, "../public/app.mjs"), "utf8");
const styles = await readFile(resolve(here, "../public/styles.css"), "utf8");

function fakeNavItem(target) {
  const classes = new Set();
  const attributes = {};
  return {
    dataset: { target },
    classList: {
      toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
      contains(name) { return classes.has(name); },
    },
    setAttribute(name, value) { attributes[name] = value; },
    removeAttribute(name) { delete attributes[name]; },
    getAttribute(name) { return attributes[name] ?? null; },
  };
}

test("navigation targets a real section and activates only after it exists", () => {
  const item = fakeNavItem("task-section");
  const target = { scrollIntoView(options) { this.options = options; } };
  const root = { getElementById(id) { return id === "task-section" ? target : null; } };

  assert.equal(navigateToSection(item, root), true);
  assert.deepEqual(target.options, { behavior: "smooth", block: "start" });

  const other = fakeNavItem("overview-section");
  activateNavigationItem(item, [item, other]);
  assert.equal(item.classList.contains("active"), true);
  assert.equal(other.classList.contains("active"), false);
  assert.equal(item.getAttribute("aria-current"), "page");
  assert.equal(other.getAttribute("aria-current"), null);
});

test("every primary navigation item maps to a real section", () => {
  const navButtons = [...html.matchAll(/<button class="nav-item[^>]*data-target="([^"]+)"[^>]*>/g)];
  assert.equal(navButtons.length, 4);
  for (const [, target] of navButtons) assert.match(html, new RegExp(`id="${target}"`));
  assert.doesNotMatch(html, />[^<]*我的课题/);
  assert.match(html, /<section class="evidence-panel scroll-target" id="evidence-section">/);
  assert.match(html, /<div class="evidence-status" id="evidence-status">/);
  assert.match(html, /class="evidence-status-copy"/);
  assert.match(app, /querySelector\("\.evidence-status-copy"\)/);
  assert.match(app, /mode === "complete" \? "complete"/);
  assert.match(styles, /\.large-status-dot\.complete/);
});
