/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TPerson = { first_name?: string | null; last_name?: string | null; display_name?: string | null };

/** The full name ("Bruno Prova"); the short name of the profile only when first and last name are empty (#21). */
export function personName(person: TPerson | undefined | null): string {
  if (!person) return "";
  const full = [person.first_name, person.last_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(" ");
  return full || person.display_name || "";
}
