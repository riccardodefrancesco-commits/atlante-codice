/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Select } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import type { TIssuePriorities } from "@plane/types";
import { cn } from "@plane/utils";
import { ATLANTE_URGENCY, urgencyLabel } from "@/atlante/urgency";

type TUrgency = (typeof ATLANTE_URGENCY)[number];

/** The colored dot of an urgency, as in Asana: red, yellow, orange, indigo. */
function UrgencyDot({ urgency }: { urgency: TUrgency }) {
  return <span className={cn("size-2 shrink-0 rounded-full", urgency.dot)} />;
}

/** The urgency badge (design system, table 16): full in the task page. */
export function AtlanteUrgencyBadge({ priority }: { priority: TIssuePriorities | null | undefined }) {
  const urgency = ATLANTE_URGENCY.find((item) => item.key === (priority ?? "none")) ?? ATLANTE_URGENCY[4];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm px-1.5 py-0.5 text-left text-caption-sm-medium whitespace-normal",
        urgency.badge
      )}
    >
      <UrgencyDot urgency={urgency} />
      {urgencyLabel(priority)}
    </span>
  );
}

type Props = {
  value: TIssuePriorities | null | undefined;
  onChange: (value: TIssuePriorities) => void;
  disabled?: boolean;
};

/** The urgency row of the task page: Plane's select, with the urgency words and days written in full. */
export function AtlanteUrgencySelect({ value, onChange, disabled = false }: Props) {
  const { t } = useTranslation();
  const selected = ATLANTE_URGENCY.find((item) => item.key === (value ?? "none")) ?? null;
  return (
    <Select<TUrgency>
      getValues={() => ATLANTE_URGENCY}
      value={selected}
      onChange={(key) => onChange((key || "none") as TIssuePriorities)}
      disabled={disabled}
      placeholder={t("atlante.urgency.choose")}
      showSearch={false}
      pinSelected={false}
      getOptionValue={(option) => option.key}
      getOptionLabel={(option) => urgencyLabel(option.key)}
      getOptionIcon={(option) => <UrgencyDot urgency={option} />}
    >
      <Select.Trigger<TUrgency>
        disabled={disabled}
        variant="select-ghost-md"
        // The full words fit on two lines in the narrow column of the task page.
        className="h-auto min-h-7 py-1"
        data-testid="atlante-urgency-select"
        label={(items) => (items[0] ? urgencyLabel(items[0].key) : t("atlante.urgency.choose"))}
        tooltip={{ heading: t("atlante.urgency.label") }}
      >
        {(items) => <AtlanteUrgencyBadge priority={items[0]?.key ?? "none"} />}
      </Select.Trigger>
    </Select>
  );
}
