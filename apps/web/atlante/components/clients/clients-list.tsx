/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { Loader } from "@plane/blocks/skeleton";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { useMember } from "@/hooks/store/use-member";
import { AtlanteClientFormModal } from "./client-form-modal";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import { useAtlanteClientPermissions } from "@/atlante/hooks/use-client-permissions";
import { personName } from "@/atlante/person-name";

type Props = { workspaceSlug: string };

type TShown = "active" | "archived";

/** All the clients: name, code and color, contact, projects, open and overdue work items. */
export const AtlanteClientsList = observer(function AtlanteClientsList({ workspaceSlug }: Props) {
  const { t } = useTranslation();
  const { activeClients, archivedClients, fetchClients, fetchedWorkspaceSlug } = useAtlanteClient();
  const { canManage, canView } = useAtlanteClientPermissions();
  const { getUserDetails } = useMember();
  const [shown, setShown] = useState<TShown>("active");
  const [search, setSearch] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fresh numbers every time the list opens.
  const { isLoading } = useSWR(canView ? `ATLANTE_CLIENTS_LIST_${workspaceSlug}` : null, () =>
    fetchClients(workspaceSlug)
  );

  const clients = shown === "active" ? activeClients : archivedClients;
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("it");
    if (!query) return clients;
    return clients.filter(
      (client) =>
        client.name.toLocaleLowerCase("it").includes(query) || client.code.toLocaleLowerCase("it").includes(query)
    );
  }, [clients, search]);

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

  const loading = isLoading && fetchedWorkspaceSlug !== workspaceSlug;
  const noClientsAtAll = !loading && activeClients.length === 0 && archivedClients.length === 0;

  if (noClientsAtAll)
    return (
      <>
        <AtlanteClientFormModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          workspaceSlug={workspaceSlug}
        />
        <EmptyStateDetailed
          assetKey="customer"
          title={t("atlante.client.list.empty_title")}
          description={
            canManage ? t("atlante.client.list.empty_description") : t("atlante.client.list.empty_description_member")
          }
          actions={canManage ? [{ label: t("atlante.client.new"), onClick: () => setIsModalOpen(true) }] : []}
          align="center"
          rootClassName="py-20"
        />
      </>
    );

  return (
    <div className="flex h-full w-full flex-col" data-atlante="clients-list">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-subtle px-page-x py-3">
        <div className="flex items-center gap-1">
          {(["active", "archived"] as TShown[]).map((option) => (
            <Button
              key={option}
              variant={shown === option ? "secondary" : "ghost"}
              size="sm"
              stretch="auto"
              label={`${t(`atlante.client.list.${option}`)} (${option === "active" ? activeClients.length : archivedClients.length})`}
              onClick={() => setShown(option)}
            />
          ))}
        </div>
        <div className="w-64">
          <InputGroup size="md">
            <Input
              size="md"
              name="atlante-client-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t("atlante.client.search")}
              aria-label={t("atlante.client.search")}
            />
          </InputGroup>
        </div>
      </div>
      {loading ? (
        <Loader className="space-y-3 px-page-x py-4">
          <Loader.Item height="40px" />
          <Loader.Item height="40px" />
          <Loader.Item height="40px" />
        </Loader>
      ) : filtered.length === 0 ? (
        <p className="px-page-x py-10 text-center text-13 text-tertiary">
          {search ? t("atlante.client.list.no_results") : t("atlante.client.list.empty_archived")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-13">
            <thead className="text-tertiary">
              <tr className="border-b border-subtle">
                <th className="px-page-x py-2 font-medium">{t("atlante.client.list.columns.name")}</th>
                <th className="px-3 py-2 font-medium">{t("atlante.client.list.columns.code")}</th>
                <th className="px-3 py-2 font-medium">{t("atlante.client.list.columns.contact")}</th>
                <th className="px-3 py-2 text-right font-medium">{t("atlante.client.list.columns.projects")}</th>
                <th className="px-3 py-2 text-right font-medium">{t("atlante.client.list.columns.open")}</th>
                <th className="px-page-x py-2 text-right font-medium">{t("atlante.client.list.columns.overdue")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((client) => {
                const contact = client.internal_contact ? getUserDetails(client.internal_contact) : undefined;
                return (
                  <tr key={client.id} className="border-b border-subtle hover:bg-layer-transparent-hover">
                    <td className="px-page-x py-2.5">
                      <Link
                        href={`/${workspaceSlug}/clients/${client.id}`}
                        className="flex items-center gap-2 font-medium text-primary"
                      >
                        <span
                          className="h-3 w-3 flex-shrink-0 rounded-full"
                          style={{ backgroundColor: client.color }}
                        />
                        <span className="truncate">{client.name}</span>
                      </Link>
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className="rounded-sm px-1.5 py-0.5 text-11 font-medium"
                        style={{ color: client.color, backgroundColor: `${client.color}1A` }}
                      >
                        {client.code}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-secondary">{personName(contact)}</td>
                    <td className="px-3 py-2.5 text-right text-secondary">{client.project_count ?? 0}</td>
                    <td className="px-3 py-2.5 text-right text-secondary">{client.open_issues ?? 0}</td>
                    <td
                      className={cn("px-page-x py-2.5 text-right", {
                        "font-medium text-danger-primary": (client.overdue_issues ?? 0) > 0,
                        "text-secondary": !client.overdue_issues,
                      })}
                    >
                      {client.overdue_issues ?? 0}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
});
