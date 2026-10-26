/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import { observer } from "mobx-react";
import { mutate } from "swr";
import { StartDateOutline } from "@makeplane/propel/icons";
import { DateSelect } from "@plane/blocks/property-select";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { useUserProfile } from "@/hooks/store/user";
import { StoreContext } from "@/lib/store-context";
import { atlantePhasesService, useAtlanteTaskChoices } from "@/atlante/hooks/use-phases";
import { refreshAfterPhaseChange, taskChoicesKey } from "@/atlante/store/phase-refresh";

/** Saves the publication date, puts it on the task in memory and reads back the delivery date (a
 * phase may count from it). */
const useSavePublishDate = () => {
  const { t } = useTranslation();
  const context = useContext(StoreContext);
  return async (workspaceSlug: string, projectId: string, issueId: string, day: string | null) => {
    try {
      await atlantePhasesService.setTaskChoices(workspaceSlug, projectId, issueId, { pubblicazione: day });
      context?.issue.issues.updateIssue(issueId, { atlante_publish_date: day });
      void mutate(taskChoicesKey(issueId));
      if (context) await refreshAfterPhaseChange(context.issue, workspaceSlug, projectId, issueId);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error ?? "";
      setToast({ type: "error", title: t("atlante.phases.toast.error"), message });
    }
  };
};

type RowProps = { workspaceSlug: string; projectId: string; issueId: string; disabled: boolean };

/** "Pubblicazione", the second date of every task (design system, table 16), after "Consegna". */
export const AtlanteTaskPublication = observer(function AtlanteTaskPublication(props: RowProps) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { data: userProfile } = useUserProfile();
  const { data } = useAtlanteTaskChoices(workspaceSlug, projectId, issueId);
  const save = useSavePublishDate();
  const date = data?.dates.find((item) => item.key === "pubblicazione");
  if (!date) return null;

  return (
    <SidebarPropertyListItem icon={StartDateOutline} label={date.name}>
      <DateSelect
        testId="atlante-task-date-pubblicazione"
        placeholder={t("atlante.phases.add_date")}
        value={getDate(date.day) ?? null}
        onChange={(value) =>
          void save(workspaceSlug, projectId, issueId, value ? (renderFormattedPayloadDate(value) ?? null) : null)
        }
        disabled={disabled}
        clearable
        weekStartsOn={userProfile?.start_of_the_week}
        variant="select-ghost-md"
        showTooltip
        tooltipHeading={date.name}
      />
    </SidebarPropertyListItem>
  );
});

/** In list rows and board cards, next to the delivery date: the publication date, with its own icon. */
export const AtlantePublishDateChip = observer(function AtlantePublishDateChip({
  workspaceSlug,
  issue,
  disabled,
}: {
  workspaceSlug: string;
  issue: TIssue;
  disabled: boolean;
}) {
  const { t } = useTranslation();
  const { data: userProfile } = useUserProfile();
  const save = useSavePublishDate();
  if (!issue.project_id) return null;
  const projectId = issue.project_id;

  return (
    <DateSelect
      testId="atlante-publish-date-chip"
      value={getDate(issue.atlante_publish_date) ?? null}
      onChange={(value) =>
        void save(workspaceSlug, projectId, issue.id, value ? (renderFormattedPayloadDate(value) ?? null) : null)
      }
      placeholder={t("atlante.dates.publication")}
      icon={<StartDateOutline />}
      clearable
      disabled={disabled}
      showTooltip
      tooltipHeading={t("atlante.dates.publication")}
      weekStartsOn={userProfile?.start_of_the_week}
      variant="pill-sm"
    />
  );
});
