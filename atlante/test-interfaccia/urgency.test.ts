/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ATLANTE_URGENCY, urgencyLabel } from "@/atlante/urgency";

describe("urgenza con le parole di Asana", () => {
  it("per intero nella scheda, in breve nell'elenco", () => {
    expect(urgencyLabel("high")).toBe("Prioritario (3 gg dopo assegnazione)");
    expect(urgencyLabel("high", true)).toBe("Prioritario (3 gg)");
    expect(urgencyLabel("urgent", true)).toBe("Urgente (1 gg)");
    expect(urgencyLabel("low")).toBe("In blocco (10 gg dopo assegnazione)");
    expect(urgencyLabel(null)).toBe("Nessuna urgenza");
  });
  it("gli stessi giorni del server e i colori di Asana", () => {
    expect(ATLANTE_URGENCY.map((item) => [item.key, item.days])).toEqual([
      ["urgent", 1],
      ["high", 3],
      ["medium", 7],
      ["low", 10],
      ["none", null],
    ]);
    expect(ATLANTE_URGENCY.slice(0, 4).map((item) => item.dot)).toEqual([
      "bg-label-crimson-text",
      "bg-label-yellow-text",
      "bg-label-orange-text",
      "bg-label-indigo-text",
    ]);
  });
});
