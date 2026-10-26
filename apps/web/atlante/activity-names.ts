/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ISSUE_PRIORITIES } from "@plane/constants";

/** The Italian name of a priority stored in the history ("high" -> "Alta"). */
export function priorityName(value: string | null | undefined): string {
  return ISSUE_PRIORITIES.find((priority) => priority.key === value)?.title ?? value ?? "";
}
