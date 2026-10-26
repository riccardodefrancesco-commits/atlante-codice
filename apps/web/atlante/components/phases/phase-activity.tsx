/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { StateOutline, UserOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { IssueActivityBlockComponent } from "@/components/issues/issue-detail/issue-activity/activity/actions";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

type Props = { activityId: string; ends: "top" | "bottom" | undefined };

/** The history lines written by the server: what a phase rule did ("atlante_phase", by the Atlante
 * automation) and the choices made on the task ("atlante_task", by a person). The server writes the
 * sentence in Italian. */
export const AtlantePhaseActivity = observer(function AtlantePhaseActivity({ activityId, ends }: Props) {
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const activity = getActivityById(activityId);
  if (!activity) return null;

  const byAutomation = activity.field === "atlante_phase";
  return (
    <IssueActivityBlockComponent
      icon={
        byAutomation ? (
          <StateOutline className="h-3.5 w-3.5 text-secondary" />
        ) : (
          <UserOutline className="h-3.5 w-3.5 text-secondary" />
        )
      }
      activityId={activityId}
      ends={ends}
      // The automation is not a person: no link to a profile.
      customUserName={activity.actor_detail?.is_bot ? t("atlante.phases.activity.automation") : undefined}
    >
      <span className="whitespace-normal">
        {byAutomation && activity.new_value && (
          <>
            {t("atlante.phases.activity.phase")} <span className="font-medium text-primary">{activity.new_value}</span>
            {". "}
          </>
        )}
        {activity.comment}
      </span>
    </IssueActivityBlockComponent>
  );
});
