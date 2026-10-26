/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Controllo automatico a ogni salvataggio (git commit), al posto di lint-staged di Plane.
 *
 * Fa le stesse cose del controllo di Plane, con una differenza:
 * - formatta i file salvati con oxfmt, come Plane;
 * - controlla i file con oxlint e blocca il salvataggio se compare anche un solo avviso
 *   nuovo rispetto alla versione precedente del file;
 * - gli avvisi che erano già nei file di Plane non bloccano, e non vengono corretti
 *   (correggerli vorrebbe dire toccare righe di Plane che non ci servono);
 * - nei file nuovi non è ammesso nessun avviso;
 * - se cambia l'interfaccia, fa girare i test della nostra parte di interfaccia;
 * - cerca password e chiavi in quello che si salva (atlante/script/controllo-segreti.py).
 *
 * Non usa la correzione automatica di oxlint, per non cambiare righe di Plane senza volerlo.
 */

import { execFileSync } from "node:child_process";
import { existsSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join } from "node:path";

const FORMAT_EXT = new Set([".js", ".jsx", ".ts", ".tsx", ".cjs", ".mjs", ".cts", ".mts", ".json", ".css", ".md"]);
const LINT_EXT = new Set([".js", ".jsx", ".ts", ".tsx", ".cjs", ".mjs", ".cts", ".mts"]);

const run = (cmd, args, options = {}) =>
  execFileSync(cmd, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024, ...options });

const root = run("git", ["rev-parse", "--show-toplevel"]).trim();
process.chdir(root);

const list = (args) => run("git", args).split("\0").filter(Boolean);
const staged = list(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]);
if (staged.length === 0) process.exit(0);

// A file saved only in part would be formatted and saved whole: better stop and say it.
const unstaged = new Set(list(["diff", "--name-only", "-z"]));
const partial = staged.filter((file) => unstaged.has(file));
if (partial.length > 0) {
  console.error("Controllo Atlante: questi file hanno modifiche non aggiunte al salvataggio:");
  for (const file of partial) console.error(`  ${file}`);
  console.error("Aggiungile con git add, oppure mettile da parte, e riprova.");
  process.exit(1);
}

const toFormat = staged.filter((file) => FORMAT_EXT.has(extname(file)));
if (toFormat.length > 0) {
  run("pnpm", ["exec", "oxfmt", "--no-error-on-unmatched-pattern", ...toFormat], { stdio: "inherit" });
  run("git", ["add", "--", ...toFormat]);
}

// Passwords and keys never reach git: checked on what is really saved, after formatting.
try {
  run("python3", ["-I", "atlante/script/controllo-segreti.py", "--salvataggio"], { stdio: "inherit" });
} catch {
  process.exit(1);
}

/** Diagnostics of oxlint for some files, as "rule|message" keys grouped by file. */
const lint = (files) => {
  let output;
  try {
    output = run("pnpm", ["exec", "oxlint", "--format", "json", ...files]);
  } catch (error) {
    // oxlint exits with 1 when it finds errors; the JSON is still on stdout.
    output = error.stdout;
  }
  const byFile = new Map();
  for (const item of JSON.parse(output).diagnostics) {
    const key = `${item.severity} ${item.code}: ${item.message}`;
    if (!byFile.has(item.filename)) byFile.set(item.filename, []);
    byFile.get(item.filename).push({ key, line: item.labels?.[0]?.span?.line });
  }
  return byFile;
};

const toLint = staged.filter((file) => LINT_EXT.has(extname(file)));
const found = toLint.length > 0 ? lint(toLint) : new Map();
const added = [];

for (const [file, diagnostics] of found) {
  let before = [];
  const inHead = (() => {
    try {
      run("git", ["cat-file", "-e", `HEAD:${file}`], { stdio: "ignore" });
      return true;
    } catch {
      return false;
    }
  })();
  if (inHead) {
    // The previous version goes next to the file, so oxlint applies the same rules.
    const ext = extname(file);
    const previous = join(dirname(file), `${basename(file, ext)}.atlante-prima${ext}`);
    try {
      writeFileSync(previous, run("git", ["show", `HEAD:${file}`]));
      before = lint([previous]).get(previous) ?? [];
    } finally {
      if (existsSync(previous)) rmSync(previous);
    }
  }
  const remaining = new Map();
  for (const { key } of before) remaining.set(key, (remaining.get(key) ?? 0) + 1);
  for (const diagnostic of diagnostics) {
    const left = remaining.get(diagnostic.key) ?? 0;
    if (left > 0) remaining.set(diagnostic.key, left - 1);
    else added.push({ file, ...diagnostic });
  }
}

if (added.length > 0) {
  console.error("Controllo Atlante: il salvataggio aggiunge avvisi nuovi. Vanno tolti prima di salvare:");
  for (const { file, line, key } of added) console.error(`  ${file}${line ? `:${line}` : ""}  ${key}`);
  process.exit(1);
}

// Our interface code has its own tests (under a second): they run whenever it changes.
const touchesInterface = staged.some(
  (file) => file.startsWith("apps/web/") || file.startsWith("atlante/test-interfaccia/")
);
if (touchesInterface) {
  try {
    run("sh", ["atlante/script/test-interfaccia.sh", "--reporter=dot"], { stdio: "inherit" });
  } catch {
    console.error("Controllo Atlante: i test dell'interfaccia non passano. Vanno sistemati prima di salvare.");
    process.exit(1);
  }
}

const old = [...found.values()].reduce((sum, diagnostics) => sum + diagnostics.length, 0);
if (old > 0) console.log(`Controllo Atlante: nessun avviso nuovo (${old} già presenti in Plane, lasciati come sono).`);
