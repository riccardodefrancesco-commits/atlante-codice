/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { renderFormattedDate } from "@plane/utils";
import { atlantePhasesService } from "@/atlante/hooks/use-phases";
import { AtlanteToAssignLabel } from "@/atlante/components/phases/role-badges";
import type { TAtlanteHomeApproval, TAtlanteHomeTask } from "@/atlante/types";

export const homeTasksKey = (workspaceSlug: string) => `ATLANTE_HOME_TASKS_${workspaceSlug}`;

function TaskRows({ workspaceSlug, tasks }: { workspaceSlug: string; tasks: TAtlanteHomeTask[] }) {
  return (
    <div className="divide-y divide-subtle-1">
      {tasks.map((task) => (
        <Link
          key={task.id}
          href={`/${workspaceSlug}/browse/${task.project_identifier}-${task.sequence_id}/`}
          className="flex items-center gap-3 px-4 py-2.5 hover:bg-layer-1"
        >
          <span className="w-20 shrink-0 text-caption-sm-medium text-tertiary">
            {task.project_identifier}-{task.sequence_id}
          </span>
          <span className="grow truncate text-body-xs-medium text-primary">{task.name}</span>
          {task.state_name && (
            <span className="flex shrink-0 items-center gap-1.5 text-caption-sm-regular text-secondary">
              <span className="size-2 rounded-full" style={{ backgroundColor: task.state_color ?? undefined }} />
              {task.state_name}
            </span>
          )}
          {task.target_date && (
            <span className="shrink-0 text-caption-sm-regular text-tertiary">
              {renderFormattedDate(task.target_date)}
            </span>
          )}
        </Link>
      ))}
    </div>
  );
}

function ApprovalRows({ workspaceSlug, rows }: { workspaceSlug: string; rows: TAtlanteHomeApproval[] }) {
  const { t } = useTranslation();
  return (
    <div className="divide-y divide-subtle-1">
      {rows.map((row) => {
        const days = row.days_left ?? 0;
        const urgent = row.to_confirm || row.reminder_day || days < 0;
        const when = row.ready
          ? t("atlante.approval.home_ready")
          : row.consent
            ? t("atlante.approval.home_consent")
            : row.to_confirm
              ? t("atlante.approval.home_to_confirm")
              : row.reminder_day
                ? t("atlante.approval.home_reminded", { days })
                : t("atlante.approval.home_days", { days });
        return (
          <Link
            key={row.id}
            href={`/${workspaceSlug}/browse/${row.project_identifier}-${row.sequence_id}/`}
            className="flex items-center gap-3 px-4 py-2.5 hover:bg-layer-1"
          >
            {row.client_code && (
              <span
                className="shrink-0 rounded-sm px-1.5 py-0.5 text-caption-sm-medium"
                style={{
                  color: row.client_color ?? undefined,
                  border: `1px solid ${row.client_color ?? "currentColor"}`,
                }}
              >
                {row.client_code}
              </span>
            )}
            <span className="grow truncate text-body-xs-medium text-primary">{row.name}</span>
            <span className={`shrink-0 text-caption-sm-regular ${urgent ? "text-warning-primary" : "text-tertiary"}`}>
              {when}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

/** In the Home (design system, table 14): the tasks waiting for an executor, for their responsible
 * person; the tasks without a responsible person, for the workspace admins. Nothing when both are empty. */
export const AtlanteHomeTasks = observer(function AtlanteHomeTasks({ workspaceSlug }: { workspaceSlug: string }) {
  const { t } = useTranslation();
  const { data } = useSWR(workspaceSlug ? homeTasksKey(workspaceSlug) : null, () =>
    atlantePhasesService.getHomeTasks(workspaceSlug)
  );
  if (!data) return null;
  const approvals = data.approvals ?? [];
  const sections = [
    { key: "to_assign", title: t("atlante.phases.home.to_assign"), tasks: data.to_assign },
    {
      key: "without_responsible",
      title: t("atlante.phases.home.without_responsible"),
      tasks: data.without_responsible ?? [],
    },
  ].filter((section) => section.tasks.length > 0);
  if (sections.length === 0 && approvals.length === 0) return null;

  return (
    <div className="flex flex-col gap-4" data-atlante="home-tasks">
      {/* Design system, table 15: the clients' approvals that wait, for who follows the client. */}
      {approvals.length > 0 && (
        <section className="rounded-lg border border-subtle bg-surface-1" data-atlante="home-approvals">
          <div className="flex items-center gap-2 border-b border-subtle px-4 py-3">
            <span className="text-body-sm-medium text-primary">{t("atlante.approval.home_title")}</span>
            <span className="text-caption-sm-regular text-tertiary">{approvals.length}</span>
          </div>
          <ApprovalRows workspaceSlug={workspaceSlug} rows={approvals} />
        </section>
      )}
      {sections.map((section) => (
        <section key={section.key} className="rounded-lg border border-subtle bg-surface-1">
          <div className="flex items-center gap-2 border-b border-subtle px-4 py-3">
            {section.key === "to_assign" ? (
              <>
                <AtlanteToAssignLabel />
                <span className="text-body-xs-regular text-secondary">{t("atlante.phases.home.to_assign_hint")}</span>
              </>
            ) : (
              <span className="text-body-sm-medium text-primary">{section.title}</span>
            )}
            <span className="text-caption-sm-regular text-tertiary">{section.tasks.length}</span>
          </div>
          <TaskRows workspaceSlug={workspaceSlug} tasks={section.tasks} />
        </section>
      ))}
    </div>
  );
});
