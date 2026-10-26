/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssuePriorities } from "@plane/types";

/** The urgency (Rick, 22 October; design system, table 16): Asana's words with the working days next
 * to them, kept in Plane's priority field. The same days as the server (project_templates.URGENCY). */
export const ATLANTE_URGENCY: {
  key: TIssuePriorities;
  name: string;
  days: number | null;
  /** Colors as in Asana: red, yellow, orange, indigo (classes written out, so that Tailwind makes them). */
  badge: string;
  dot: string;
}[] = [
  {
    key: "urgent",
    name: "Urgente",
    days: 1,
    badge: "bg-label-crimson-bg text-label-crimson-text",
    dot: "bg-label-crimson-text",
  },
  {
    key: "high",
    name: "Prioritario",
    days: 3,
    badge: "bg-label-yellow-bg text-label-yellow-text",
    dot: "bg-label-yellow-text",
  },
  {
    key: "medium",
    name: "Standard",
    days: 7,
    badge: "bg-label-orange-bg text-label-orange-text",
    dot: "bg-label-orange-text",
  },
  {
    key: "low",
    name: "In blocco",
    days: 10,
    badge: "bg-label-indigo-bg text-label-indigo-text",
    dot: "bg-label-indigo-text",
  },
  { key: "none", name: "Nessuna", days: null, badge: "text-tertiary", dot: "bg-layer-3" },
];

/** "Prioritario (3 gg dopo assegnazione)" in the task page, "Prioritario (3 gg)" in the lists. */
export const urgencyLabel = (key: TIssuePriorities | null | undefined, short = false) => {
  const urgency = ATLANTE_URGENCY.find((item) => item.key === (key ?? "none")) ?? ATLANTE_URGENCY[4];
  if (urgency.days === null) return "Nessuna urgenza";
  return `${urgency.name} (${urgency.days} gg${short ? "" : " dopo assegnazione"})`;
};
