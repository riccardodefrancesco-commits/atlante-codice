/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { daysLeft } from "@/atlante/approval-days";

describe("giorni per approvare", () => {
  const today = new Date(2026, 9, 22, 18, 30); // 22 ottobre, sera
  it("conta i giorni di calendario fino all'ultimo giorno del cliente", () => {
    expect(daysLeft("2026-11-06", today)).toBe(15);
    expect(daysLeft("2026-10-23", today)).toBe(1);
    expect(daysLeft("2026-10-22", today)).toBe(0);
  });
  it("dopo l'ultimo giorno è in ritardo", () => {
    expect(daysLeft("2026-10-20", today)).toBe(-2);
  });
});
