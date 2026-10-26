/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IGroupByColumn, TGetColumns } from "@plane/types";
import { store } from "@/lib/store-context";

/** The groups (columns, rows) when the board, list or table is grouped by client.
 *
 * Ids match the server: client ids, and "None" for items without a client.
 * In a project with a client only that client is offered; elsewhere all active
 * clients, so empty groups can be shown when "show empty groups" is on.
 */
export const getAtlanteClientColumns = ({ projectId, isWorkspaceLevel }: TGetColumns): IGroupByColumn[] => {
  const { activeClients, getClientById, getProjectClientId } = store.atlanteClient;
  const projectClient = !isWorkspaceLevel && projectId ? getClientById(getProjectClientId(projectId)) : undefined;
  const clients = projectClient ? [projectClient] : activeClients;

  const columns: IGroupByColumn[] = clients.map((client) => ({
    id: client.id,
    name: client.name,
    icon: <span className="h-[12px] w-[12px] rounded-full" style={{ backgroundColor: client.color }} />,
    payload: {},
  }));
  columns.push({
    id: "None",
    name: "Senza cliente",
    icon: <span className="h-[12px] w-[12px] rounded-full border border-dashed border-strong" />,
    payload: {},
  });
  return columns;
};
