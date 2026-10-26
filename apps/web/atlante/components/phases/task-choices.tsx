/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { StackLayersOutline, MembersOutline, StateOutline, UserOutline, VideoOutline } from "@makeplane/propel/icons";
import { Select } from "@plane/blocks/select";
import { DateSelect } from "@plane/blocks/property-select";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { useUserProfile } from "@/hooks/store/user";
import { atlantePhasesService, useAtlanteRefreshTask, useAtlanteTaskChoices } from "@/atlante/hooks/use-phases";
import { AtlanteMissingResponsibleLabel } from "@/atlante/components/phases/role-badges";
import type { TAtlanteTaskChoicesUpdate } from "@/atlante/types";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

type TWorkType = { key: string; name: string };

const sameMembers = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));

/** Saves a choice of the task, then reads back executors and deadline: the phase rule may follow it. */
const useSaveChoice = ({ workspaceSlug, projectId, issueId }: Props) => {
  const { t } = useTranslation();
  const { mutate } = useAtlanteTaskChoices(workspaceSlug, projectId, issueId);
  const refreshTask = useAtlanteRefreshTask();
  return async (data: TAtlanteTaskChoicesUpdate) => {
    try {
      await mutate(await atlantePhasesService.setTaskChoices(workspaceSlug, projectId, issueId, data), {
        revalidate: false,
      });
      await refreshTask(workspaceSlug, projectId, issueId);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error ?? "";
      setToast({ type: "error", title: t("atlante.phases.toast.error"), message });
    }
  };
};

/** "Responsabile": the first of the three roles on every task (request 37). Without a choice on the
 * task it is the account of the project. */
export const AtlanteTaskResponsible = observer(function AtlanteTaskResponsible(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { data } = useAtlanteTaskChoices(workspaceSlug, projectId, issueId);
  const save = useSaveChoice(props);
  if (!data) return null;
  const missing = !data.responsabile.member_id;

  return (
    <SidebarPropertyListItem icon={UserOutline} label={t("atlante.phases.responsible")}>
      {/* Design system, table 14: "Manca il responsabile" and the button to choose one. */}
      {missing && <AtlanteMissingResponsibleLabel />}
      <MemberSelect
        testId="atlante-task-responsible"
        value={data.responsabile.member_id}
        onChange={(id) => void save({ responsabile: id || null })}
        projectId={projectId}
        variant="select-ghost-md"
        placeholder={missing ? t("atlante.phases.choose") : t("atlante.phases.nobody")}
        clearable
        clearLabel={t("atlante.phases.from_project")}
        disabled={disabled}
        tooltip={{
          heading:
            data.responsabile.source === "project"
              ? t("atlante.phases.responsible_from_project")
              : t("atlante.phases.responsible"),
        }}
      />
    </SidebarPropertyListItem>
  );
});

/** The other choices of the task: reviewers and the roles picked for this task (the editor), the
 * template dates and the rule of the current phase. */
export const AtlanteTaskChoices = observer(function AtlanteTaskChoices(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { data: userProfile } = useUserProfile();
  const { data } = useAtlanteTaskChoices(workspaceSlug, projectId, issueId);
  const save = useSaveChoice(props);
  if (!data) return null;

  return (
    <>
      {data.roles.map((role) => {
        const fromProject = role.member_ids.length === 0;
        return (
          <SidebarPropertyListItem key={role.key} icon={MembersOutline} label={role.name}>
            <MemberSelect
              testId={`atlante-task-role-${role.key}`}
              value={fromProject ? role.project_member_ids : role.member_ids}
              // Back to the project's people when the choice is emptied or equals them.
              onChange={(ids) =>
                void save({ [role.key]: ids.length === 0 || sameMembers(ids, role.project_member_ids) ? null : ids })
              }
              projectId={projectId}
              multiple
              variant="select-ghost-md"
              placeholder={
                role.key === "revisore_interno" ? t("atlante.phases.no_reviewers") : t("atlante.phases.nobody")
              }
              showLabel={(fromProject ? role.project_member_ids : role.member_ids).length <= 1}
              disabled={disabled}
              tooltip={{
                heading: fromProject ? t("atlante.phases.role_from_project", { role: role.name }) : role.name,
              }}
            />
          </SidebarPropertyListItem>
        );
      })}

      <SidebarPropertyListItem icon={StackLayersOutline} label={t("atlante.work_type.label")}>
        <Select<TWorkType>
          getValues={() => data.work_types}
          value={data.work_types.find((item) => item.key === data.work_type) ?? null}
          onChange={(key) => void save({ tipo: key || null })}
          disabled={disabled}
          placeholder={t("atlante.work_type.choose")}
          showSearch={false}
          pinSelected={false}
          getOptionValue={(option) => option.key}
          getOptionLabel={(option) => option.name}
        >
          <Select.Trigger<TWorkType>
            disabled={disabled}
            variant="select-ghost-md"
            data-testid="atlante-work-type-select"
            label={(items) => items[0]?.name ?? t("atlante.work_type.choose")}
            tooltip={{ heading: t("atlante.work_type.label") }}
          >
            {(items) => (
              <span className={items[0] ? "text-primary" : "text-placeholder"}>
                {items[0]?.name ?? t("atlante.work_type.choose")}
              </span>
            )}
          </Select.Trigger>
        </Select>
      </SidebarPropertyListItem>

      {/* The publication date has its own row, after "Consegna" (publish-date.tsx). */}
      {data.dates
        .filter((date) => date.key !== "pubblicazione")
        .map((date) => (
          <SidebarPropertyListItem key={date.key} icon={VideoOutline} label={date.name}>
            <DateSelect
              testId={`atlante-task-date-${date.key}`}
              placeholder={t("atlante.phases.add_date")}
              value={getDate(date.day) ?? null}
              onChange={(value) =>
                void save({ [date.key]: value ? (renderFormattedPayloadDate(value) ?? null) : null })
              }
              disabled={disabled}
              clearable
              weekStartsOn={userProfile?.start_of_the_week}
              variant="select-ghost-md"
              showTooltip
              tooltipHeading={date.name}
            />
          </SidebarPropertyListItem>
        ))}

      {data.phase && (
        <SidebarPropertyListItem icon={StateOutline} label={t("atlante.phases.rule")}>
          {/* What the rule did when the task entered the phase is in the history, and in the tooltip. */}
          <span
            className="flex min-h-7 items-center px-2 py-1 text-body-xs-regular whitespace-normal text-secondary"
            title={data.phase.rule}
            data-atlante="task-phase-rule"
          >
            {data.phase.executor_name} · {data.phase.deadline}
          </span>
        </SidebarPropertyListItem>
      )}
    </>
  );
});
