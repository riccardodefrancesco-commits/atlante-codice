/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissionsLevel } from "@plane/constants";
import { EUserWorkspaceRoles } from "@plane/types";
import type { TPowerKCommandConfig, TPowerKContext } from "@/components/power-k/core/types";
import { handlePowerKNavigate } from "@/components/power-k/utils/navigation";
import { useUser } from "@/hooks/store/user";
import { AtlanteClientIcon } from "@/atlante/components/client-icon";

/** Atlante's commands in Plane's command palette: "Go to Clients" (keys g, l), for the team only. */
export const useAtlanteNavigationCommands = (): TPowerKCommandConfig[] => {
  const {
    permission: { allowPermissions },
  } = useUser();
  const isTeam = (ctx: TPowerKContext) =>
    Boolean(ctx.params.workspaceSlug?.toString()) &&
    allowPermissions(
      [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER],
      EUserPermissionsLevel.WORKSPACE,
      ctx.params.workspaceSlug?.toString()
    );

  return [
    {
      id: "atlante_nav_clients",
      type: "action",
      group: "navigation",
      i18n_title: "atlante.client.command.open_clients",
      icon: AtlanteClientIcon,
      keySequence: "gl",
      keywords: ["clienti", "clients", "cliente"],
      action: (ctx) => handlePowerKNavigate(ctx, [ctx.params.workspaceSlug?.toString(), "clients"]),
      isEnabled: isTeam,
      isVisible: isTeam,
      closeOnSelect: true,
    },
  ];
};
