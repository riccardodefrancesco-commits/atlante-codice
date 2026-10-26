/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { BaseKanBanRoot } from "@/components/issues/issue-layouts/kanban/base-kanban-root";
import { BaseListRoot } from "@/components/issues/issue-layouts/list/base-list-root";
import { AllIssueQuickActions } from "@/components/issues/issue-layouts/quick-action-dropdowns";
import { useUserPermissions } from "@/hooks/store/user";

/** Board and list of the workspace's "all work items" (the agency board), made like Plane's
 * board of the "your work" page: work items of every project the person belongs to. */
const useCanEditInProject = () => {
  const { workspaceSlug } = useParams();
  const { allowPermissions } = useUserPermissions();
  return (projectId: string) =>
    allowPermissions(
      [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
      EUserPermissionsLevel.PROJECT,
      workspaceSlug?.toString(),
      projectId
    );
};

export const AtlanteWorkspaceKanBanLayout = observer(function AtlanteWorkspaceKanBanLayout() {
  const { globalViewId } = useParams();
  const canEditPropertiesBasedOnProject = useCanEditInProject();
  return (
    <BaseKanBanRoot
      QuickActions={AllIssueQuickActions}
      canEditPropertiesBasedOnProject={canEditPropertiesBasedOnProject}
      viewId={globalViewId?.toString()}
    />
  );
});

export const AtlanteWorkspaceListLayout = observer(function AtlanteWorkspaceListLayout() {
  const { globalViewId } = useParams();
  const canEditPropertiesBasedOnProject = useCanEditInProject();
  return (
    <BaseListRoot
      QuickActions={AllIssueQuickActions}
      canEditPropertiesBasedOnProject={canEditPropertiesBasedOnProject}
      viewId={globalViewId?.toString()}
    />
  );
});
