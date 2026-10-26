/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { Button } from "@makeplane/propel/components/button";
import { LinearProgress } from "@makeplane/propel/components/linear-progress";
import { Loader } from "@plane/blocks/skeleton";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { ProjectSelect } from "@/components/dropdowns/project/project-select";
import { CreateProjectModal } from "@/components/project/create-project-modal";
import { useProject } from "@/hooks/store/use-project";
import { useAtlanteClient } from "@/atlante/hooks/use-atlante-client";
import type { TAtlanteClient } from "@/atlante/types";
import { useAtlanteClientIssues, useAtlanteClientProjects } from "./use-client-issues";

type Props = { workspaceSlug: string; client: TAtlanteClient; canManage: boolean };

type TServerError = { error?: string; detail?: string } | undefined;

/** The projects of a client, with progress; admins link, unlink and create projects here. */
export const AtlanteClientProjects = observer(function AtlanteClientProjects(props: Props) {
  const { workspaceSlug, client, canManage } = props;
  const { t } = useTranslation();
  const { workspaceProjectIds } = useProject();
  const { getProjectClientId, setProjectClient, fetchClients } = useAtlanteClient();
  const { data: projects, isLoading, mutate } = useAtlanteClientProjects(workspaceSlug, client.id);
  const { mutate: mutateIssues } = useAtlanteClientIssues(workspaceSlug, client.id);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const projectsBeforeCreate = useRef<string[]>([]);
  const isArchived = !!client.archived_at;

  const refresh = async () => {
    await Promise.all([mutate(), mutateIssues(), fetchClients(workspaceSlug)]);
  };

  const link = async (projectId: string | null, clientId: string | null) => {
    if (!projectId) return;
    try {
      await setProjectClient(workspaceSlug, projectId, clientId);
      setToast({
        type: "success",
        title: t(clientId ? "atlante.client.toast.linked" : "atlante.client.toast.unlinked"),
        message: client.name,
      });
      await refresh();
    } catch (error) {
      const serverError = error as TServerError;
      setToast({
        type: "error",
        title: t("atlante.client.toast.error"),
        message: serverError?.error ?? serverError?.detail ?? "",
      });
    }
  };

  const openCreate = () => {
    projectsBeforeCreate.current = [...(workspaceProjectIds ?? [])];
    setIsCreateOpen(true);
  };

  // Plane's window does not say which project it created: the new one is the one that was not there.
  const closeCreate = async () => {
    setIsCreateOpen(false);
    const created = (workspaceProjectIds ?? []).filter((id) => !projectsBeforeCreate.current.includes(id));
    if (created.length === 1) await link(created[0], client.id);
  };

  const freeProjects = (workspaceProjectIds ?? []).filter((id) => !getProjectClientId(id));

  return (
    <div className="space-y-4 py-4" data-atlante="client-projects">
      {canManage && !isArchived && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="w-72">
            <ProjectSelect
              value={null}
              onChange={(projectId) => void link(projectId, client.id)}
              variant="select-md"
              projectList="all"
              filterOption={(projectId) => !getProjectClientId(projectId)}
              placeholder={
                freeProjects.length > 0
                  ? t("atlante.client.projects.link_placeholder")
                  : t("atlante.client.projects.no_free_projects")
              }
              disabled={freeProjects.length === 0}
            />
          </div>
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            label={t("atlante.client.projects.create")}
            onClick={openCreate}
          />
          <CreateProjectModal isOpen={isCreateOpen} onClose={() => void closeCreate()} workspaceSlug={workspaceSlug} />
        </div>
      )}
      {isLoading ? (
        <Loader className="space-y-3">
          <Loader.Item height="56px" />
          <Loader.Item height="56px" />
        </Loader>
      ) : !projects || projects.length === 0 ? (
        <p className="py-10 text-center text-13 text-tertiary">{t("atlante.client.projects.empty")}</p>
      ) : (
        <ul className="divide-y divide-subtle rounded-md border border-subtle">
          {projects.map((project) => {
            const progress = project.total_issues ? (project.completed_issues / project.total_issues) * 100 : 0;
            return (
              <li key={project.id} className="flex items-center gap-4 px-4 py-3">
                <Link
                  href={`/${workspaceSlug}/projects/${project.id}/issues/`}
                  className="min-w-0 flex-1 truncate text-13 font-medium text-primary hover:underline"
                >
                  {project.name}
                  <span className="font-normal ml-2 text-12 text-tertiary">{project.identifier}</span>
                  {project.archived_at && (
                    <span className="font-normal ml-2 text-12 text-tertiary">
                      ({t("atlante.client.projects.archived")})
                    </span>
                  )}
                </Link>
                <div className="flex w-56 flex-col gap-1">
                  <LinearProgress
                    value={progress}
                    size="md"
                    variant="brand"
                    showValue={false}
                    aria-label={project.name}
                  />
                  <span className="text-11 text-tertiary">
                    {t("atlante.client.projects.progress", {
                      done: project.completed_issues,
                      total: project.total_issues,
                    })}
                  </span>
                </div>
                <span className="w-20 text-12 text-secondary">
                  {t("atlante.client.projects.open_issues", { count: project.open_issues })}
                </span>
                <span
                  className={
                    project.overdue_issues > 0
                      ? "w-24 text-12 font-medium text-danger-primary"
                      : "w-24 text-12 text-tertiary"
                  }
                >
                  {t("atlante.client.projects.overdue_issues", { count: project.overdue_issues })}
                </span>
                {canManage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    stretch="auto"
                    label={t("atlante.client.projects.unlink")}
                    onClick={() => void link(project.id, null)}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
});
