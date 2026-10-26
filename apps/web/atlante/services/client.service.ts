/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";
import type {
  TAtlanteClient,
  TAtlanteClientFormData,
  TAtlanteClientIssues,
  TAtlanteClientProject,
  TAtlanteIssueClient,
  TAtlanteProjectClient,
} from "@/atlante/types";

/** Talks to Atlante's own endpoints, under /api/atlante/. */
export class AtlanteClientService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string) {
    return `/api/atlante/workspaces/${workspaceSlug}`;
  }

  private async unwrap<T>(call: Promise<{ data: T }>): Promise<T> {
    return call
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /** All the clients, archived ones too: work items of an archived client keep their label. */
  async getClients(workspaceSlug: string): Promise<TAtlanteClient[]> {
    return this.unwrap(this.get(`${this.base(workspaceSlug)}/clients/`, { params: { archived: "all" } }));
  }

  async getProjectClients(workspaceSlug: string): Promise<TAtlanteProjectClient[]> {
    return this.unwrap(this.get(`${this.base(workspaceSlug)}/project-clients/`));
  }

  async createClient(workspaceSlug: string, data: Partial<TAtlanteClientFormData>): Promise<TAtlanteClient> {
    return this.unwrap(this.post(`${this.base(workspaceSlug)}/clients/`, data));
  }

  async updateClient(
    workspaceSlug: string,
    clientId: string,
    data: Partial<TAtlanteClientFormData>
  ): Promise<TAtlanteClient> {
    return this.unwrap(this.patch(`${this.base(workspaceSlug)}/clients/${clientId}/`, data));
  }

  async archiveClient(workspaceSlug: string, clientId: string): Promise<TAtlanteClient> {
    return this.unwrap(this.post(`${this.base(workspaceSlug)}/clients/${clientId}/archive/`));
  }

  async restoreClient(workspaceSlug: string, clientId: string): Promise<TAtlanteClient> {
    return this.unwrap(this.post(`${this.base(workspaceSlug)}/clients/${clientId}/restore/`));
  }

  async getClientProjects(workspaceSlug: string, clientId: string): Promise<TAtlanteClientProject[]> {
    return this.unwrap(this.get(`${this.base(workspaceSlug)}/clients/${clientId}/projects/`));
  }

  async getClientIssues(workspaceSlug: string, clientId: string): Promise<TAtlanteClientIssues> {
    return this.unwrap(this.get(`${this.base(workspaceSlug)}/clients/${clientId}/issues/`));
  }

  /** The effective client of a work item, where it comes from and whether it can be changed. */
  async getIssueClient(workspaceSlug: string, projectId: string, issueId: string): Promise<TAtlanteIssueClient> {
    return this.unwrap(this.get(`${this.base(workspaceSlug)}/projects/${projectId}/issues/${issueId}/client/`));
  }

  /** Sets the own client of a work item (only in projects without a client), or removes it with null. */
  async setIssueClient(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    clientId: string | null
  ): Promise<{ issue_id: string; client_id: string | null }> {
    return this.unwrap(
      this.put(`${this.base(workspaceSlug)}/projects/${projectId}/issues/${issueId}/client/`, { client_id: clientId })
    );
  }

  /** Links a project to a client, or unlinks it with null. */
  async setProjectClient(
    workspaceSlug: string,
    projectId: string,
    clientId: string | null
  ): Promise<{ project_id: string; client_id: string | null }> {
    return this.unwrap(this.put(`${this.base(workspaceSlug)}/projects/${projectId}/client/`, { client_id: clientId }));
  }
}
