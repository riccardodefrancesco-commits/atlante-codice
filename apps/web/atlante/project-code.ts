/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The code of a new project: the first four consonants of its name, in capitals ("Delta Vini - Social"
 * becomes DLTV), decided by Rick on 21 October 2026 (zeta3-progetti#18). The server proposes it with
 * the number when the code is taken (apps/api/plane/atlante/project_names.py); this copy of the same
 * rule is used only when the server does not answer, and its tests use the same examples.
 */

const VOWELS = new Set(["A", "E", "I", "O", "U"]);
const CODE_LENGTH = 4;
const EMPTY_CODE = "PROG";

export function projectCodeFromName(name: string): string {
  const plain = name
    .normalize("NFKD")
    .replace(/[^ -~]/g, "")
    .toUpperCase();
  const characters = [...plain].filter((c) => /[A-Z0-9]/.test(c));
  const isConsonant = (c: string) => /[A-Z]/.test(c) && !VOWELS.has(c);
  const consonants = characters.filter(isConsonant);
  const code =
    consonants.length >= CODE_LENGTH
      ? consonants.slice(0, CODE_LENGTH)
      : [...consonants, ...characters.filter((c) => !isConsonant(c))].slice(0, CODE_LENGTH);
  return code.join("") || EMPTY_CODE;
}
