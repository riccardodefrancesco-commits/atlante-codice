/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// i18n
import { useTranslation } from "@plane/i18n";
// ui
import {
  CyclesOutline,
  DueDateOutline,
  EstimateOutline,
  LabelsOutline,
  MembersOutline,
  ModuleOutline,
  ParentOutline,
  PriorityOutline,
  StartDateOutline,
  StateOutline,
  UserOutline,
} from "@makeplane/propel/icons";
import { DateSelect } from "@plane/blocks/property-select";
import { cn, getDate, renderFormattedPayloadDate, shouldHighlightIssueDueDate } from "@plane/utils";
// components
import { EstimateSelect } from "@/components/dropdowns/estimate/estimate-select";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { StateSelect } from "@/components/dropdowns/state/state-select";
// hooks
import { useProjectEstimates } from "@/hooks/store/estimates";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserProfile } from "@/hooks/store/user";
// components
import { IssueParentSelectRoot } from "@/components/issues/parent-select-root";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { IssueCycleSelect } from "./cycle-select";
import { IssueLabel } from "./label";
import { IssueModuleSelect } from "./module-select";
import type { TIssueOperations } from "./root";
import { AtlanteIssueClientProperty } from "@/atlante/components/issue-client-property"; // ATLANTE
import { AtlanteTaskChoices, AtlanteTaskResponsible } from "@/atlante/components/phases/task-choices"; // ATLANTE
import { AtlanteExecutorInfo, AtlanteTaskToAssign } from "@/atlante/components/phases/role-badges"; // ATLANTE
import { AtlanteUrgencySelect } from "@/atlante/components/phases/urgency-select"; // ATLANTE
import { AtlanteTaskPublication } from "@/atlante/components/phases/publish-date"; // ATLANTE
import { ATLANTE_SHOW_START_DATE } from "@/atlante/hidden-features"; // ATLANTE

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  issueOperations: TIssueOperations;
  isEditable: boolean;
};

export const IssueDetailsSidebar = observer(function IssueDetailsSidebar(props: Props) {
  const { t } = useTranslation();
  const { workspaceSlug, projectId, issueId, issueOperations, isEditable } = props;
  // store hooks
  const { getProjectById } = useProject();
  const { areEstimateEnabledByProjectId } = useProjectEstimates();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { getUserDetails } = useMember();
  const { getStateById } = useProjectState();
  const { data: userProfile } = useUserProfile();
  const issue = getIssueById(issueId);
  if (!issue) return <></>;

  const createdByDetails = getUserDetails(issue.created_by);

  // derived values
  const projectDetails = getProjectById(issue.project_id);
  const stateDetails = getStateById(issue.state_id);

  const minDate = issue.start_date ? getDate(issue.start_date) : null;
  minDate?.setDate(minDate.getDate());

  const maxDate = issue.target_date ? getDate(issue.target_date) : null;
  maxDate?.setDate(maxDate.getDate());

  return (
    <>
      <div className="flex h-full w-full flex-col items-center divide-y-2 divide-subtle-1 overflow-hidden">
        <div className="h-full w-full overflow-y-auto px-6">
          <h5 className="mt-5 text-body-xs-medium">{t("common.properties")}</h5>
          <div className={`mt-4 mb-2 space-y-2.5 truncate ${!isEditable ? "opacity-60" : ""}`}>
            {/* ATLANTE: the client of the work item */}
            <AtlanteIssueClientProperty
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={!isEditable}
            />
            <SidebarPropertyListItem icon={StateOutline} label={t("common.state")}>
              <StateSelect
                testId="work-item-state-select"
                value={issue?.state_id}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { state_id: val })}
                projectId={projectId}
                disabled={!isEditable}
                variant="select-ghost-md"
                tooltip
              />
            </SidebarPropertyListItem>

            {/* ATLANTE: the responsible person of the task (request 37) */}
            <AtlanteTaskResponsible
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={!isEditable}
            />

            {/* ATLANTE: "Esecutore", singular, with the "i" (design system, table 14) */}
            <SidebarPropertyListItem
              icon={MembersOutline}
              label={t("common.assignee")}
              appendElement={<AtlanteExecutorInfo />}
            >
              <AtlanteTaskToAssign workspaceSlug={workspaceSlug} projectId={projectId} issueId={issueId} />
              <MemberSelect
                testId="work-item-assignee-select"
                value={issue?.assignee_ids ?? []}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { assignee_ids: val })}
                disabled={!isEditable}
                projectId={projectId}
                placeholder={t("issue.add.assignee")}
                multiple
                variant="select-ghost-md"
                showLabel={(issue?.assignee_ids?.length ?? 0) <= 1}
                tooltip={{ heading: t("common.assignee") }} // ATLANTE: singular
              />
            </SidebarPropertyListItem>

            {/* ATLANTE: reviewers, roles chosen on the task, dates and the rule of the phase */}
            <AtlanteTaskChoices
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={!isEditable}
            />

            {/* ATLANTE: the urgency with the days, as in Asana (design system, table 16) */}
            <SidebarPropertyListItem icon={PriorityOutline} label={t("common.priority")}>
              <AtlanteUrgencySelect
                value={issue?.priority}
                onChange={(val) => issueOperations.update(workspaceSlug, projectId, issueId, { priority: val })}
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>

            {createdByDetails && (
              <SidebarPropertyListItem icon={UserOutline} label={t("common.created_by")}>
                <div className="flex gap-2 px-2">
                  <ButtonAvatars showTooltip userIds={createdByDetails.id} />
                  <span className="grow truncate text-body-xs-regular leading-5">{createdByDetails?.display_name}</span>
                </div>
              </SidebarPropertyListItem>
            )}

            {/* ATLANTE: the start date is hidden, the task has Consegna and Pubblicazione (table 16) */}
            {ATLANTE_SHOW_START_DATE && (
              <SidebarPropertyListItem icon={StartDateOutline} label={t("common.order_by.start_date")}>
                <DateSelect
                  testId="work-item-start-date-select"
                  placeholder={t("issue.add.start_date")}
                  value={getDate(issue.start_date) ?? null}
                  onChange={(val) =>
                    issueOperations.update(workspaceSlug, projectId, issueId, {
                      start_date: val ? renderFormattedPayloadDate(val) : null,
                    })
                  }
                  maxDate={maxDate ?? undefined}
                  disabled={!isEditable}
                  clearable
                  weekStartsOn={userProfile?.start_of_the_week}
                  variant="select-ghost-md"
                  showTooltip
                  tooltipHeading={t("common.order_by.start_date")}
                />
              </SidebarPropertyListItem>
            )}

            <SidebarPropertyListItem icon={DueDateOutline} label={t("common.order_by.due_date")}>
              <div className="flex w-full items-center gap-2">
                <DateSelect
                  testId="work-item-due-date-select"
                  placeholder={t("issue.add.due_date")}
                  value={getDate(issue.target_date) ?? null}
                  onChange={(val) =>
                    issueOperations.update(workspaceSlug, projectId, issueId, {
                      target_date: val ? renderFormattedPayloadDate(val) : null,
                    })
                  }
                  minDate={minDate ?? undefined}
                  disabled={!isEditable}
                  clearable
                  className={cn({
                    "text-danger-primary": shouldHighlightIssueDueDate(issue.target_date, stateDetails?.group),
                  })}
                  weekStartsOn={userProfile?.start_of_the_week}
                  variant="select-ghost-md"
                  showTooltip
                  tooltipHeading={t("common.order_by.due_date")}
                />
              </div>
            </SidebarPropertyListItem>

            {/* ATLANTE: "Pubblicazione", the second date of every task (table 16) */}
            <AtlanteTaskPublication
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={!isEditable}
            />

            {projectId && areEstimateEnabledByProjectId(projectId) && (
              <SidebarPropertyListItem icon={EstimateOutline} label={t("common.estimate")}>
                <EstimateSelect
                  value={issue?.estimate_point ?? undefined}
                  onChange={(val: string | null) =>
                    issueOperations.update(workspaceSlug, projectId, issueId, { estimate_point: val })
                  }
                  projectId={projectId}
                  disabled={!isEditable}
                  variant="select-ghost-md"
                  placeholder={t("common.none")}
                  tooltip
                />
              </SidebarPropertyListItem>
            )}

            {projectDetails?.module_view && (
              <SidebarPropertyListItem icon={ModuleOutline} label={t("common.modules")}>
                <IssueModuleSelect
                  className="w-full grow"
                  workspaceSlug={workspaceSlug}
                  projectId={projectId}
                  issueId={issueId}
                  issueOperations={issueOperations}
                  disabled={!isEditable}
                />
              </SidebarPropertyListItem>
            )}

            {projectDetails?.cycle_view && (
              <SidebarPropertyListItem icon={CyclesOutline} label={t("common.cycle")} appendElement={null}>
                <IssueCycleSelect
                  className="h-7.5 w-full grow"
                  workspaceSlug={workspaceSlug}
                  projectId={projectId}
                  issueId={issueId}
                  issueOperations={issueOperations}
                  disabled={!isEditable}
                />
              </SidebarPropertyListItem>
            )}

            <SidebarPropertyListItem icon={ParentOutline} label={t("common.parent")}>
              <IssueParentSelectRoot
                className="h-7.5 w-full grow"
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                issueId={issueId}
                issueOperations={issueOperations}
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>

            <SidebarPropertyListItem icon={LabelsOutline} label={t("common.labels")}>
              <IssueLabel
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                issueId={issueId}
                disabled={!isEditable}
              />
            </SidebarPropertyListItem>
          </div>
        </div>
      </div>
    </>
  );
});
