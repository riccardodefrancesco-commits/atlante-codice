/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Calendar days from today (on this computer) to the client's last day: 0 is today, negative is late. */
export function daysLeft(due: string, now: Date = new Date()): number {
  const [year, month, day] = due.split("-").map(Number);
  const last = Date.UTC(year, month - 1, day);
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((last - today) / 86_400_000);
}
