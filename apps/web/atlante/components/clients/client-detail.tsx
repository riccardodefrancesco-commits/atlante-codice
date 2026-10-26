/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { Tab, Tabs, TabsList, TabsPanel } from "@makeplane/propel/components/tabs";
import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { Loader } from "@plane/blocks/skeleton";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { useAtlanteClient, useAtlanteClientsLoader } from "@/atlante/hooks/use-atlante-client";
import { useAtlanteClientPermissions } from "@/atlante/hooks/use-client-permissions";
import { AtlanteClientArchiveDialog } from "./client-archive-dialog";
import { AtlanteClientFormModal } from "./client-form-modal";
import { AtlanteClientIssues } from "./client-issues";
import { AtlanteClientOverview } from "./client-overview";
import { AtlanteClientProjects } from "./client-projects";

type Props = { workspaceSlug: string; clientId: string };

const TABS = ["overview", "projects", "issues"] as const;

/** The client card: header with name, code, color and status, then Overview, Projects, Work items. */
export const AtlanteClientDetail = observer(function AtlanteClientDetail({ workspaceSlug, clientId }: Props) {
  const { t } = useTranslation();
  useAtlanteClientsLoader();
  const { getClientById, fetchedWorkspaceSlug, restoreClient } = useAtlanteClient();
  const { canManage, canView } = useAtlanteClientPermissions();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isArchiveOpen, setIsArchiveOpen] = useState(false);
  const client = getClientById(clientId);

  if (!canView)
    return (
      <EmptyStateDetailed
        assetKey="no-access"
        title={t("atlante.client.no_access_title")}
        description={t("atlante.client.no_access_description")}
        align="center"
        rootClassName="py-20"
      />
    );

  if (!client) {
    if (fetchedWorkspaceSlug !== workspaceSlug)
      return (
        <Loader className="space-y-3 px-page-x py-6">
          <Loader.Item height="48px" width="40%" />
          <Loader.Item height="200px" />
        </Loader>
      );
    return (
      <EmptyStateDetailed
        assetKey="error-404"
        title={t("atlante.client.not_found")}
        description={t("atlante.client.not_found_description")}
        align="center"
        rootClassName="py-20"
      />
    );
  }

  const isArchived = !!client.archived_at;

  const restore = async () => {
    try {
      await restoreClient(workspaceSlug, client.id);
      setToast({ type: "success", title: t("atlante.client.toast.restored"), message: client.name });
    } catch {
      setToast({ type: "error", title: t("atlante.client.toast.error"), message: client.name });
    }
  };

  return (
    <div className="h-full w-full overflow-y-auto px-page-x py-5" data-atlante="client-detail">
      <AtlanteClientFormModal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        workspaceSlug={workspaceSlug}
        client={client}
      />
      <AtlanteClientArchiveDialog
        isOpen={isArchiveOpen}
        onClose={() => setIsArchiveOpen(false)}
        workspaceSlug={workspaceSlug}
        client={client}
      />
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4">
        <div className="flex items-center gap-3">
          <span className="h-9 w-9 flex-shrink-0 rounded-md" style={{ backgroundColor: client.color }} />
          <div>
            <h2 className="text-20 font-semibold text-primary">{client.name}</h2>
            <div className="flex items-center gap-2 text-12">
              <span
                className="rounded-sm px-1.5 py-0.5 font-medium"
                style={{ color: client.color, backgroundColor: `${client.color}1A` }}
              >
                {client.code}
              </span>
              <span className={isArchived ? "text-tertiary" : "text-success-primary"}>
                {t(isArchived ? "atlante.client.status.archived" : "atlante.client.status.active")}
              </span>
            </div>
          </div>
        </div>
        {canManage && (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              label={t("atlante.client.actions.edit")}
              onClick={() => setIsEditOpen(true)}
            />
            {isArchived ? (
              <Button
                variant="secondary"
                size="md"
                stretch="auto"
                label={t("atlante.client.actions.restore")}
                onClick={() => void restore()}
              />
            ) : (
              <Button
                variant="ghost"
                size="md"
                stretch="auto"
                label={t("atlante.client.actions.archive")}
                onClick={() => setIsArchiveOpen(true)}
              />
            )}
          </div>
        )}
      </div>
      <Tabs variant="underline" defaultValue="overview">
        <TabsList>
          {TABS.map((tab) => (
            <Tab key={tab} value={tab} label={t(`atlante.client.tabs.${tab}`)} />
          ))}
        </TabsList>
        <TabsPanel value="overview">
          <AtlanteClientOverview workspaceSlug={workspaceSlug} client={client} />
        </TabsPanel>
        <TabsPanel value="projects">
          <AtlanteClientProjects workspaceSlug={workspaceSlug} client={client} canManage={canManage} />
        </TabsPanel>
        <TabsPanel value="issues">
          <AtlanteClientIssues workspaceSlug={workspaceSlug} client={client} />
        </TabsPanel>
      </Tabs>
    </div>
  );
});
