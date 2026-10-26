/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAtlantePhaseRule } from "@/atlante/types";

/** "Da assegnare" (design system, table 14): the task is in a phase whose role gives the work, and
 * nobody has it. The same rule as the server's is_to_assign. */
export const isTaskToAssign = (
  phases: readonly TAtlantePhaseRule[],
  stateId: string | null | undefined,
  assigneeIds: readonly string[] | null | undefined
) => (assigneeIds?.length ?? 0) === 0 && phases.some((rule) => rule.state_id === stateId && rule.executor !== null);
