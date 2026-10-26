/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { daysLeft } from "@/atlante/approval-days";

/** In list rows and board cards: the task waits for the client (design system, table 15). */
export function AtlanteApprovalChip({ issue }: { issue: TIssue }) {
  const { t } = useTranslation();
  if (!issue.atlante_approval_due) return null;
  const days = daysLeft(issue.atlante_approval_due);
  const text =
    days < 0
      ? t("atlante.approval.chip_late")
      : days === 1
        ? t("atlante.approval.chip_one")
        : t("atlante.approval.chip", { days });
  return (
    <span
      className="inline-flex h-5 shrink-0 items-center gap-1 rounded-sm bg-info-subtle px-1.5 text-caption-sm-medium text-info-primary"
      data-atlante="approval-chip"
    >
      {text}
    </span>
  );
}
