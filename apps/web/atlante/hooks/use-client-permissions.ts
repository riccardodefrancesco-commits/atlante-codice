/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useUserPermissions } from "@/hooks/store/user";

/** Who can do what with clients, as on the server: admins manage, the team sees, guests never. */
export const useAtlanteClientPermissions = () => {
  const { allowPermissions } = useUserPermissions();
  return {
    canManage: allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.WORKSPACE),
    canView: allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE),
  };
};
