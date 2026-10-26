/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// ATLANTE: load the clients and the "project -> client" map with the workspace pages
import { useAtlanteClientsLoader } from "@/atlante/hooks/use-atlante-client";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const useWorkspaceIssuePropertiesExtended = (workspaceSlug: string | string[] | undefined) => {
  useAtlanteClientsLoader();
};
