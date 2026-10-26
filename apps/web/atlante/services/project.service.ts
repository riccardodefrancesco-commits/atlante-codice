/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

/** Atlante's endpoints about projects, under /api/atlante/. */
export class AtlanteProjectService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** The code Atlante proposes for a new project with this name (zeta3-progetti#18). */
  async getProjectCode(workspaceSlug: string, name: string): Promise<string> {
    return this.get(`/api/atlante/workspaces/${workspaceSlug}/project-code/`, { params: { name } })
      .then((response) => response?.data?.code as string)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
