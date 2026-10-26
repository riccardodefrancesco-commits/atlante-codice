/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { cn } from "@plane/utils";
import { useAtlanteClient, useAtlanteClientsLoader } from "@/atlante/hooks/use-atlante-client";

type Props = {
  clientId: string | null | undefined;
  /** The project of the work item: its client is used while the item's own value is not loaded yet
   * (Plane's answer to a new work item does not carry the client). */
  projectId?: string | null;
  /** "code": only the short code (cards); "name": the full name (table). */
  variant?: "code" | "name";
  className?: string;
};

/** The client label: small, in the client's color, the same in every view. */
export const AtlanteClientBadge = observer(function AtlanteClientBadge(props: Props) {
  const { clientId, projectId, variant = "code", className } = props;
  useAtlanteClientsLoader();
  const { getClientById, getProjectClientId } = useAtlanteClient();
  const client = getClientById(clientId === undefined ? getProjectClientId(projectId) : clientId);
  if (!client) return null;

  return (
    <Tooltip label={client.name}>
      <span
        className={cn(
          "inline-flex h-5 max-w-full items-center gap-1 truncate rounded-sm border-[0.5px] border-strong px-1.5 text-11 font-medium",
          className
        )}
        style={{ color: client.color, backgroundColor: `${client.color}1A` }}
        data-atlante="client-badge"
      >
        <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full" style={{ backgroundColor: client.color }} />
        <span className="truncate">{variant === "code" ? client.code : client.name}</span>
      </span>
    </Tooltip>
  );
});
