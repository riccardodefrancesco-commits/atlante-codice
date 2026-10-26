/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Atlante's version, decided by Rick on 21 October 2026 (zeta3-progetti#24):
 * - 0.1.0 alfa on 21 October 2026; 0.2.0 alfa on 22 October 2026 (pieces 11 and 12);
 *   0.3.0 alfa on 22 October 2026 (release 0.3, phases and templates);
 * - the second number goes up with every new piece (0.2.0, 0.3.0...), the third with fixes (0.2.1);
 * - "beta" when the team uses it on the test server; 1.0.0 when Asana is switched off.
 * Shown in "Informazioni su Atlante" and in the diagnosis (atlante/script/diagnosi.py reads it here).
 */

export const ATLANTE_VERSION = "0.3.0";
export const ATLANTE_STAGE: "alfa" | "beta" | "" = "alfa";

export const atlanteVersionLabel = () => [ATLANTE_VERSION, ATLANTE_STAGE].filter(Boolean).join(" ");
