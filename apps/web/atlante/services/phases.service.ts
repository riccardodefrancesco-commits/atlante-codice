/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";
import type {
  TAtlanteApproval,
  TAtlanteHomeTasks,
  TAtlanteProjectTemplate,
  TAtlanteTaskChoices,
  TAtlanteTaskChoicesUpdate,
} from "@/atlante/types";

/** Templates, roles and task choices, under /api/atlante/. */
export class AtlantePhasesService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private project(workspaceSlug: string, projectId: string) {
    return `/api/atlante/workspaces/${workspaceSlug}/projects/${projectId}`;
  }

  private async unwrap<T>(call: Promise<{ data: T }>): Promise<T> {
    return call
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async getProjectTemplate(workspaceSlug: string, projectId: string): Promise<TAtlanteProjectTemplate> {
    return this.unwrap(this.get(`${this.project(workspaceSlug, projectId)}/modello/`));
  }

  async applyTemplate(workspaceSlug: string, projectId: string, template: string): Promise<TAtlanteProjectTemplate> {
    return this.unwrap(this.post(`${this.project(workspaceSlug, projectId)}/modello/`, { template }));
  }

  async setProjectRole(
    workspaceSlug: string,
    projectId: string,
    role: string,
    memberIds: string[]
  ): Promise<TAtlanteProjectTemplate> {
    return this.unwrap(this.put(`${this.project(workspaceSlug, projectId)}/ruoli/`, { role, member_ids: memberIds }));
  }

  async getTaskChoices(workspaceSlug: string, projectId: string, issueId: string): Promise<TAtlanteTaskChoices> {
    return this.unwrap(this.get(`${this.project(workspaceSlug, projectId)}/issues/${issueId}/scelte/`));
  }

  async setTaskChoices(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: TAtlanteTaskChoicesUpdate
  ): Promise<TAtlanteTaskChoices> {
    return this.unwrap(this.patch(`${this.project(workspaceSlug, projectId)}/issues/${issueId}/scelte/`, data));
  }

  /** For the Home: tasks to assign of which the person is responsible, and those without one. */
  async getHomeTasks(workspaceSlug: string): Promise<TAtlanteHomeTasks> {
    return this.unwrap(this.get(`/api/atlante/workspaces/${workspaceSlug}/da-assegnare/`));
  }

  /** The project templates, to choose one for a new project. */
  async getTemplates(workspaceSlug: string): Promise<{ key: string; name: string }[]> {
    return this.unwrap(this.get(`/api/atlante/workspaces/${workspaceSlug}/modelli/`));
  }

  async getApproval(
    workspaceSlug: string,
    projectId: string,
    issueId: string
  ): Promise<{ approval: TAtlanteApproval | null }> {
    return this.unwrap(this.get(`${this.project(workspaceSlug, projectId)}/issues/${issueId}/approvazione/`));
  }

  /** The client's answer, recorded by the team until the portal. */
  async answerApproval(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: { esito: "inviata" | "approvata" | "modifiche" | "silenzio_assenso"; nota?: string; conta?: boolean }
  ): Promise<{ approval: TAtlanteApproval | null }> {
    return this.unwrap(this.post(`${this.project(workspaceSlug, projectId)}/issues/${issueId}/approvazione/`, data));
  }
}
