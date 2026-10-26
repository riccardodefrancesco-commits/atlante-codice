/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IProject } from "@plane/types";

/**
 * The features every new project starts with (docs/specifica/10-funzioni-di-plane.md, zeta3-progetti#15):
 * Moduli (our Sezioni), Viste, Pagine and Richieste in arrivo. Cycles stay off.
 */
export const ATLANTE_STARTING_FEATURES: Partial<IProject> = {
  module_view: true,
  issue_views_view: true,
  page_view: true,
  inbox_view: true,
};

/**
 * Switches the starting features on right after the project is created, the same way as the switches
 * in the project settings: Plane creates the inbox of Richieste in arrivo only there.
 * Returns false when it did not work: the project exists and the features can be switched on by hand.
 */
export async function enableStartingFeatures(
  updateProject: (workspaceSlug: string, projectId: string, data: Partial<IProject>) => Promise<unknown>,
  workspaceSlug: string,
  projectId: string
): Promise<boolean> {
  try {
    await updateProject(workspaceSlug, projectId, ATLANTE_STARTING_FEATURES);
    return true;
  } catch {
    return false;
  }
}
