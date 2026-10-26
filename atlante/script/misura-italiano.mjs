/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Measures the cost of a complete Italian (compito 02, pezzo 12): how many English texts are written
 * inside Plane's code instead of the translation files, screen by screen and file by file, and how
 * many Italian translations are missing from Plane's translation files.
 *
 * Usage, from the repository root:
 *   node atlante/script/misura-italiano.mjs [--json out.json]
 *
 * It reads the code with TypeScript's own parser. It counts what a person can see: text between
 * tags, visible attributes (label, placeholder, title, aria-label...) and labels in objects
 * (label, title, message, description...). It is an estimate: a few strings are not visible, a few
 * visible ones are built at run time and escape it.
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const require = createRequire(join(ROOT, "apps", "web", "package.json"));
const ts = require("typescript");

const SOURCES = [
  "apps/web",
  "apps/admin",
  "apps/space",
  "packages/constants",
  "packages/utils",
  "packages/editor",
  "packages/blocks",
];
const SKIP_DIRS = new Set([
  "node_modules",
  "dist",
  "build",
  ".turbo",
  "atlante",
  "locales",
  "__tests__",
  "tests",
  "stories",
]);
const VISIBLE_ATTRIBUTES = new Set([
  "label",
  "placeholder",
  "title",
  "aria-label",
  "alt",
  "tooltipContent",
  "tooltipHeading",
  "description",
  "heading",
  "buttonText",
  "subtitle",
  "emptyText",
  "primaryButtonText",
  "secondaryButtonText",
  "content",
]);
const VISIBLE_KEYS = new Set([
  "label",
  "title",
  "message",
  "description",
  "placeholder",
  "tooltip",
  "heading",
  "subtitle",
  "text",
  "header",
  "subHeader",
  "subheading",
  "buttonText",
  "primaryButtonText",
  "secondaryButtonText",
  "emptyStateMessage",
]);
const I18N_KEY = /^[a-z0-9_-]+(\.[a-z0-9_-]+)*$/; // common.save, project_created_successfully
const ENGLISH = /[A-Za-z]{2,}/;

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      if (!SKIP_DIRS.has(name)) yield* files(path);
    } else if (/\.(tsx|ts)$/.test(name) && !/\.(d|test|spec|stories)\.tsx?$/.test(name)) yield path;
  }
}

function looksVisible(text) {
  const value = text.trim();
  if (value.length < 2 || !ENGLISH.test(value)) return false;
  if (I18N_KEY.test(value)) return false; // a translation key or an identifier, not a text
  if (/^(https?:|mailto:|\/|#|\.|@)/.test(value) || /[{}<>=;]/.test(value)) return false;
  return /\s/.test(value) || /^[A-Z]/.test(value);
}

/** Which screen a file belongs to, in words Rick knows. */
function screen(path) {
  const parts = path.split(sep);
  if (parts[0] === "apps" && parts[1] === "admin") return "Pannello amministratore";
  if (parts[0] === "apps" && parts[1] === "space") return "Pagine pubbliche";
  if (parts[0] === "packages") return `Pezzi condivisi: ${parts[1]}`;
  const area = parts[2] === "components" || parts[2] === "ce" ? parts[3] : parts[2];
  const sub = parts[4] ?? "";
  if (area === "issues" && /issue-layouts/.test(path) && /filters|display/.test(path)) return "Filtri e Visualizza";
  if (area === "issues" && /issue-layouts/.test(path)) return "Elenco e bacheca delle task";
  if (area === "issues" && /issue-detail|peek-overview|issue-modal/.test(path)) return "Scheda e finestra della task";
  if (["work-item-filters", "rich-filters", "filters"].includes(area)) return "Filtri e Visualizza";
  if (["sidebar", "navigation", "workspace"].includes(area) && /sidebar|navigation/.test(path)) return "Menu laterale";
  if (area === "power-k" || area === "command-palette") return "Ricerca e comandi";
  if (area === "app") return `Pagine: ${sub || "altre"}`;
  return area || "altro";
}

const found = []; // { file, screen, kind, text }
for (const source of SOURCES) {
  for (const path of files(join(ROOT, source))) {
    const file = relative(ROOT, path);
    const code = readFileSync(path, "utf8");
    const tree = ts.createSourceFile(
      path,
      code,
      ts.ScriptTarget.Latest,
      true,
      path.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
    );
    const lines = code.split("\n");
    // Lines marked ATLANTE are already in Italian (or a choice of ours): they are not counted.
    const ours = (node) => {
      const line = tree.getLineAndCharacterOfPosition(node.getStart()).line;
      return [lines[line], lines[line - 1], lines[line + 1]].some((text) => text?.includes("ATLANTE"));
    };
    const add = (kind, text, node) => {
      if (!ours(node)) found.push({ file, screen: screen(file), kind, text: text.trim().replace(/\s+/g, " ") });
    };
    const visit = (node) => {
      if (ts.isJsxText(node) && looksVisible(node.text)) add("testo", node.text, node);
      else if (ts.isJsxAttribute(node) && VISIBLE_ATTRIBUTES.has(node.name.getText())) {
        const value = node.initializer;
        const literal =
          value &&
          (ts.isStringLiteral(value)
            ? value
            : ts.isJsxExpression(value) && value.expression && ts.isStringLiteral(value.expression)
              ? value.expression
              : null);
        if (literal && looksVisible(literal.text)) add("attributo", literal.text, node);
      } else if (ts.isPropertyAssignment(node) && VISIBLE_KEYS.has(node.name.getText().replace(/["']/g, ""))) {
        if (ts.isStringLiteral(node.initializer) && looksVisible(node.initializer.text))
          add("etichetta", node.initializer.text, node);
      }
      ts.forEachChild(node, visit);
    };
    visit(tree);
  }
}

// Plane's own translation files: keys with English text and no Italian.
const flatten = (node, prefix = "", out = {}) => {
  for (const [key, value] of Object.entries(node)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object") flatten(value, path, out);
    else out[path] = value;
  }
  return out;
};
const locales = join(ROOT, "packages", "i18n", "src", "locales");
let keys = 0,
  missing = 0,
  same = 0;
for (const name of readdirSync(join(locales, "en"))) {
  if (name === "atlante.json") continue;
  const en = flatten(JSON.parse(readFileSync(join(locales, "en", name), "utf8")));
  const it = flatten(JSON.parse(readFileSync(join(locales, "it", name), "utf8")));
  for (const [key, value] of Object.entries(en)) {
    keys += 1;
    if (!it[key]) missing += 1;
    else if (it[key] === value && /\s/.test(value)) same += 1;
  }
}

const byScreen = new Map();
for (const item of found) {
  const entry = byScreen.get(item.screen) ?? { texts: 0, files: new Set() };
  entry.texts += 1;
  entry.files.add(item.file);
  byScreen.set(item.screen, entry);
}
const rows = [...byScreen.entries()]
  .map(([name, e]) => ({ name, texts: e.texts, files: e.files.size }))
  .toSorted((a, b) => b.texts - a.texts);
const allFiles = new Set(found.map((item) => item.file));
const number = (n) => n.toLocaleString("it-IT");

console.log(`Testi inglesi scritti nel codice di Plane: ${number(found.length)} in ${number(allFiles.size)} file.`);
console.log(
  `File di traduzione di Plane: ${number(keys)} testi; in italiano ne mancano ${number(missing)}, e ${number(same)} sono uguali all'inglese.`
);
console.log("Per schermata (testi, file):");
for (const row of rows) console.log(`  ${row.name}: ${number(row.texts)} testi in ${number(row.files)} file`);

const jsonAt = process.argv.indexOf("--json");
if (jsonAt > 0) {
  writeFileSync(
    process.argv[jsonAt + 1],
    JSON.stringify({ total: found.length, files: allFiles.size, keys, missing, same, rows, found }, null, 2)
  );
}
