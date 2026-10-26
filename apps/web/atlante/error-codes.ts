/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The code of every error, in the interface (docs/proposta-codici-errore.md). The server answers an
 * unexpected error with a code: Atlante shows it once, so whoever reports the problem can give it.
 * A page that breaks in the browser gets its own code, shown on the error page and sent to the log.
 * Plain Italian here: this runs outside the screens, where the translation files cannot be read.
 */

import { setToast } from "@plane/blocks/toast";

// The same alphabet as the server (apps/api/plane/atlante/error_codes.py): no 0/O and 1/I.
const ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
const shown = new Set<string>();

export function newErrorCode(): string {
  const values = crypto.getRandomValues(new Uint32Array(4));
  return "ATL-" + Array.from(values, (value) => ALPHABET[value % ALPHABET.length]).join("");
}

/** Called for every failed answer of the server: shows the code once, when there is one. */
export function reportErrorCode(error: unknown, show: typeof setToast = setToast) {
  const code = (error as { response?: { data?: { codice?: unknown } } })?.response?.data?.codice;
  if (typeof code !== "string" || shown.has(code)) return;
  shown.add(code);
  show({ type: "error", title: "Qualcosa non ha funzionato", message: `Codice: ${code}. Riprova o segnalalo.` });
}
