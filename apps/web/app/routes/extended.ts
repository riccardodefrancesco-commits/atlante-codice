/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { RouteConfigEntry } from "@react-router/dev/routes";
import { layout, route } from "@react-router/dev/routes"; // ATLANTE: client pages

// ATLANTE: the client pages, inside Plane's workspace frame (merged with core routes by layout file)
const ATLANTE_CLIENTS = "./(all)/[workspaceSlug]/(projects)/(atlante)/clients";

export const extendedRoutes: RouteConfigEntry[] = [
  // ATLANTE: client list and client card
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      layout("./(all)/[workspaceSlug]/(projects)/layout.tsx", [
        layout(`${ATLANTE_CLIENTS}/layout.tsx`, [route(":workspaceSlug/clients", `${ATLANTE_CLIENTS}/page.tsx`)]),
        layout(`${ATLANTE_CLIENTS}/[clientId]/layout.tsx`, [
          route(":workspaceSlug/clients/:clientId", `${ATLANTE_CLIENTS}/[clientId]/page.tsx`),
        ]),
      ]),
    ]),
  ]),
];
