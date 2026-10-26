/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The interface's copy of the project code rule gives the same codes as the server's
 * (apps/api/plane/atlante/tests/test_nomi_progetti.py uses the same examples).
 */

import { projectCodeFromName } from "@/atlante/project-code";

describe("codice del progetto dalle prime quattro consonanti (zeta3-progetti#18)", () => {
  it.each([
    ["Delta Vini - Social", "DLTV"],
    ["Alfa Biscotti", "LFBS"],
    ["Città Studi", "CTTS"],
    ["Gamma Palestre: sito", "GMMP"],
    ["Aia", "AIA"],
    ["Tè 2", "TE2"],
    ["--- !!!", "PROG"],
  ])("%s diventa %s", (name, code) => {
    expect(projectCodeFromName(name)).toBe(code);
  });
});
