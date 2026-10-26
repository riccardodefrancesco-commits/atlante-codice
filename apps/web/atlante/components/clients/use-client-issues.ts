/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import { AtlanteClientService } from "@/atlante/services/client.service";

const clientService = new AtlanteClientService();

/** The work items of a client: one request shared by Overview and Work items. */
export const useAtlanteClientIssues = (workspaceSlug: string, clientId: string) =>
  useSWR(`ATLANTE_CLIENT_ISSUES_${clientId}`, () => clientService.getClientIssues(workspaceSlug, clientId));

export const useAtlanteClientProjects = (workspaceSlug: string, clientId: string) =>
  useSWR(`ATLANTE_CLIENT_PROJECTS_${clientId}`, () => clientService.getClientProjects(workspaceSlug, clientId));
