/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { newErrorCode, reportErrorCode } from "@/atlante/error-codes";

describe("codici di errore nell'interfaccia", () => {
  it("il codice è breve e facile da leggere", () => {
    for (let i = 0; i < 50; i++) expect(newErrorCode()).toMatch(/^ATL-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{4}$/);
  });
  it("mostra il codice del server una volta sola", () => {
    const toasts: unknown[] = [];
    const show = ((toast: unknown) => toasts.push(toast)) as unknown as Parameters<typeof reportErrorCode>[1];
    const error = { response: { status: 500, data: { codice: "ATL-7F3K" } } };
    reportErrorCode(error, show);
    reportErrorCode(error, show);
    reportErrorCode({ response: { status: 400, data: { error: "Nome già usato" } } }, show);
    expect(toasts).toEqual([
      { type: "error", title: "Qualcosa non ha funzionato", message: "Codice: ATL-7F3K. Riprova o segnalalo." },
    ]);
  });
});
