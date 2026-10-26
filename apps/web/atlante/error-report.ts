/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Sends the code of a page that broke in the browser to the server log (docs/proposta-codici-errore.md).
 * Kept apart from error-codes.ts: Plane's APIService imports that file, and this one imports APIService.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

class AtlanteErrorService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async send(code: string, kind: string) {
    return this.post("/api/atlante/errori/", { codice: code, pagina: window.location.pathname, tipo: kind });
  }
}

/** Sends the code of a page that broke in the browser to the log. Never the error's text. */
export function sendBrowserError(code: string, kind: string) {
  new AtlanteErrorService().send(code, kind).catch(() => {
    // The page is already broken: if the log cannot be reached, the code on screen is enough.
  });
}
