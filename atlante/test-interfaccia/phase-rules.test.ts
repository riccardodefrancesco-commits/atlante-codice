/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isTaskToAssign } from "@/atlante/phase-rules";

const rule = (state_id: string, executor: string | null) => ({
  state_id,
  phase: state_id,
  phase_name: state_id,
  executor,
  executor_name: "",
  deadline: "",
});
const phases = [rule("montaggio", "editor"), rule("fatto", null)];

describe("etichetta Da assegnare", () => {
  it("compare quando la fase dà il lavoro a un ruolo e nessuno ce l'ha", () => {
    expect(isTaskToAssign(phases, "montaggio", [])).toBe(true);
    expect(isTaskToAssign(phases, "montaggio", undefined)).toBe(true);
  });
  it("non compare se qualcuno ce l'ha, in una fase senza ruolo o fuori dal modello", () => {
    expect(isTaskToAssign(phases, "montaggio", ["elena"])).toBe(false);
    expect(isTaskToAssign(phases, "fatto", [])).toBe(false);
    expect(isTaskToAssign([], "in-corso", [])).toBe(false);
  });
});
