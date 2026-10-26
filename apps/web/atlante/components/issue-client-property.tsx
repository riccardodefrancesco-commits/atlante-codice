/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { AtlanteClientBadge } from "@/atlante/components/client-badge";
import { AtlanteClientIcon } from "@/atlante/components/client-icon";
import { AtlanteClientSelect } from "@/atlante/components/client-select";
import { useAtlanteIssueClient, useAtlanteSetIssueClient } from "@/atlante/hooks/use-issue-client";
import { useAtlanteClientPermissions } from "@/atlante/hooks/use-client-permissions";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

/** The "Client" row of a work item (its page and the side panel). In a project with a client it shows
 * that client; in a project without one (Produzione video) the client is chosen here. */
export const AtlanteIssueClientProperty = observer(function AtlanteIssueClientProperty(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { canView } = useAtlanteClientPermissions();
  const { data } = useAtlanteIssueClient(workspaceSlug, projectId, issueId);
  const setIssueClient = useAtlanteSetIssueClient();

  // Guests never see clients.
  if (!canView || !data) return null;

  const change = async (clientId: string | null) => {
    try {
      await setIssueClient(workspaceSlug, projectId, issueId, clientId);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error ?? "";
      setToast({ type: "error", title: t("atlante.client.toast.error"), message });
    }
  };

  return (
    <SidebarPropertyListItem icon={AtlanteClientIcon} label={t("atlante.client.label")}>
      {data.editable ? (
        <AtlanteClientSelect
          value={data.client_id}
          onChange={(clientId) => void change(clientId)}
          variant="select-ghost-md"
          disabled={disabled}
        />
      ) : (
        <span className="flex h-7 items-center px-2" data-atlante="issue-client-from-project">
          <AtlanteClientBadge clientId={data.client_id} variant="name" />
        </span>
      )}
    </SidebarPropertyListItem>
  );
});
