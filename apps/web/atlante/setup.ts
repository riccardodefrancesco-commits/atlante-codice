/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Atlante's settings applied once, when the interface starts (called by apps/web/app/root.tsx).
 */

import { it as italian } from "date-fns/locale";
import { setDateSelectDefaults } from "@plane/blocks/property-select";

export function applyAtlanteSettings() {
  // Dates in Italian in every date picker: "20 ott 2026", "17 - 21 ott 2026", calendar months and days
  // in Italian (docs/regole/coerenza.md). Weeks already start on Monday in Plane's calendar.
  setDateSelectDefaults({ formatToken: "d MMM yyyy", locale: italian });
}
