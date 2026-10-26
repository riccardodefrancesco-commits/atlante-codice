/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { IssueActivityBlockComponent } from "@/components/issues/issue-detail/issue-activity/activity/actions";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { AtlanteClientIcon } from "@/atlante/components/client-icon";

type Props = { activityId: string; ends: "top" | "bottom" | undefined };

const strong = (text: string | null | undefined) => <span className="font-medium text-primary">{text}</span>;

/** The history line written by the server when the client of a work item changes. */
export const AtlanteIssueClientActivity = observer(function AtlanteIssueClientActivity({ activityId, ends }: Props) {
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const activity = getActivityById(activityId);
  if (!activity) return null;

  const { old_value: oldName, new_value: newName } = activity;

  return (
    <IssueActivityBlockComponent
      icon={<AtlanteClientIcon className="h-3.5 w-3.5 text-secondary" />}
      activityId={activityId}
      ends={ends}
    >
      {newName && oldName ? (
        <>
          {t("atlante.client.activity.changed_from")} {strong(oldName)} {t("atlante.client.activity.to")}{" "}
          {strong(newName)}.
        </>
      ) : newName ? (
        <>
          {t("atlante.client.activity.set")} {strong(newName)}.
        </>
      ) : (
        <>
          {t("atlante.client.activity.removed")} {strong(oldName)}.
        </>
      )}
    </IssueActivityBlockComponent>
  );
});
