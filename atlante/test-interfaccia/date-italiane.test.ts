/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Plane's date helpers write in Italian (docs/regole/coerenza.md: "20 ott 2026", "8 ore fa").
 */

// The source, not the built package: the test checks the code as it is now.
import {
  calculateTimeAgo,
  formatDateRange,
  renderFormattedDate,
  renderFormattedDateWithoutYear,
} from "../../packages/utils/src/datetime";

describe("date all'italiana", () => {
  it("giorno, mese breve e anno", () => {
    expect(renderFormattedDate("2026-10-20")).toBe("20 ott 2026");
    expect(renderFormattedDateWithoutYear("2026-10-05")).toBe("5 ott");
  });
  it("intervalli nell'ordine italiano", () => {
    expect(formatDateRange(new Date(2026, 9, 17), new Date(2026, 9, 21))).toBe("17 - 21 ott 2026");
    expect(formatDateRange(new Date(2025, 0, 24), new Date(2025, 1, 6))).toBe("24 gen - 6 feb 2025");
    expect(formatDateRange(new Date(2024, 11, 28), new Date(2025, 0, 4))).toBe("28 dic 2024 - 4 gen 2025");
  });
  it("tempo passato", () => {
    const eightHoursAgo = new Date(Date.now() - 8 * 3600 * 1000);
    expect(calculateTimeAgo(eightHoursAgo)).toBe("circa 8 ore fa");
  });
});
