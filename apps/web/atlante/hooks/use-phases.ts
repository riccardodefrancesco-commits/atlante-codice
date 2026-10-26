/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import useSWR from "swr";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useUserPermissions } from "@/hooks/store/user";
import { StoreContext } from "@/lib/store-context";
import { refreshAfterPhaseChange, taskChoicesKey } from "@/atlante/store/phase-refresh";
import { AtlantePhasesService } from "@/atlante/services/phases.service";

export const atlantePhasesService = new AtlantePhasesService();

export const projectTemplateKey = (projectId: string) => `ATLANTE_PROJECT_TEMPLATE_${projectId}`;
export { taskChoicesKey };

/** Project members and admins: guests never see roles and phase rules. */
export const useAtlanteCanSeePhases = (workspaceSlug: string, projectId: string) => {
  const { allowPermissions } = useUserPermissions();
  return allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
};

/** Template, roles and phase rules of a project. */
export const useAtlanteProjectTemplate = (workspaceSlug: string, projectId: string) => {
  const canSee = useAtlanteCanSeePhases(workspaceSlug, projectId);
  return useSWR(canSee && workspaceSlug && projectId ? projectTemplateKey(projectId) : null, () =>
    atlantePhasesService.getProjectTemplate(workspaceSlug, projectId)
  );
};

/** Responsible person, roles, dates and phase of one task. */
export const useAtlanteTaskChoices = (workspaceSlug: string, projectId: string, issueId: string) => {
  const canSee = useAtlanteCanSeePhases(workspaceSlug, projectId);
  return useSWR(canSee && workspaceSlug && projectId && issueId ? taskChoicesKey(issueId) : null, () =>
    atlantePhasesService.getTaskChoices(workspaceSlug, projectId, issueId)
  );
};

/** Reads back executors and deadline after a change the phase rule may follow. */
export const useAtlanteRefreshTask = () => {
  const context = useContext(StoreContext);
  return (workspaceSlug: string, projectId: string, issueId: string) =>
    context ? refreshAfterPhaseChange(context.issue, workspaceSlug, projectId, issueId) : undefined;
};
