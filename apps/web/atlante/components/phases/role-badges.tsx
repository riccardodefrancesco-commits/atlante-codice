/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { CircleDashedOutline, InfoOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { cn } from "@plane/utils";
import { useAtlanteProjectTemplate, useAtlanteTaskChoices } from "@/atlante/hooks/use-phases";
import { isTaskToAssign } from "@/atlante/phase-rules";

/** The "i" next to "Esecutore" (design system, table 14, version A). */
export function AtlanteExecutorInfo() {
  const { t } = useTranslation();
  return (
    <Tooltip label={t("atlante.phases.executor_info")}>
      <span className="inline-flex text-tertiary" aria-label={t("atlante.phases.executor_info")}>
        <InfoOutline width={12} height={12} />
      </span>
    </Tooltip>
  );
}

/** "Da assegnare": a dashed circle where the executor's photo would be, and the warning label. */
export function AtlanteToAssignLabel({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1", className)} data-atlante="to-assign">
      <CircleDashedOutline width={14} height={14} className="text-tertiary" />
      <span className="rounded-sm bg-warning-subtle px-1.5 py-0.5 text-caption-sm-medium text-warning-primary">
        {t("atlante.phases.to_assign")}
      </span>
    </span>
  );
}

/** "Manca il responsabile", in the danger color. */
export function AtlanteMissingResponsibleLabel() {
  const { t } = useTranslation();
  return (
    <span
      className="shrink-0 rounded-sm bg-danger-subtle px-1.5 py-0.5 text-caption-sm-medium text-danger-primary"
      data-atlante="missing-responsible"
    >
      {t("atlante.phases.missing_responsible")}
    </span>
  );
}

type TaskProps = { workspaceSlug: string; projectId: string; issueId: string };

/** In the task page and side panel, next to the executor: the task waits for someone. */
export const AtlanteTaskToAssign = observer(function AtlanteTaskToAssign(props: TaskProps) {
  const { data } = useAtlanteTaskChoices(props.workspaceSlug, props.projectId, props.issueId);
  return data?.to_assign ? <AtlanteToAssignLabel /> : null;
});

/** In list rows and board cards: the task is in a phase that gives the work and nobody has it. */
export const AtlanteListToAssign = observer(function AtlanteListToAssign({
  workspaceSlug,
  issue,
}: {
  workspaceSlug: string;
  issue: TIssue;
}) {
  const { data } = useAtlanteProjectTemplate(workspaceSlug, issue.project_id ?? "");
  if (!data || !isTaskToAssign(data.phases, issue.state_id, issue.assignee_ids)) return null;
  return <AtlanteToAssignLabel className="h-5" />;
});
