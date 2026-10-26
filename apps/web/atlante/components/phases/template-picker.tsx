/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
import { Select } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import { atlantePhasesService } from "@/atlante/hooks/use-phases";

type TTemplate = { key: string; name: string };

/** In the "Nuovo progetto" window: the template the project starts with (screen 17). Without one the
 * project has Plane's starting phases and no rules. */
export function AtlanteTemplatePicker({
  workspaceSlug,
  value,
  onChange,
}: {
  workspaceSlug: string;
  value: string | null;
  onChange: (key: string | null) => void;
}) {
  const { t } = useTranslation();
  const { data } = useSWR(workspaceSlug ? `ATLANTE_TEMPLATES_${workspaceSlug}` : null, () =>
    atlantePhasesService.getTemplates(workspaceSlug)
  );
  const templates: TTemplate[] = data ?? [];
  const label = (items: TTemplate[]) =>
    `${t("atlante.phases.template_label")}: ${items[0]?.name ?? t("atlante.phases.no_template_choice")}`;
  return (
    <div className="flex" data-atlante="template-picker">
      <Select<TTemplate>
        getValues={() => templates}
        value={templates.find((template) => template.key === value) ?? null}
        onChange={(key) => onChange(key || null)}
        placeholder={t("atlante.phases.no_template_choice")}
        showSearch={false}
        pinSelected={false}
        getOptionValue={(option) => option.key}
        getOptionLabel={(option) => option.name}
      >
        <Select.Trigger<TTemplate>
          variant="pill-md"
          className="max-w-none"
          data-testid="atlante-template-picker"
          label={label}
        >
          {(items) => <span className="min-w-0 grow truncate text-left">{label(items)}</span>}
        </Select.Trigger>
      </Select>
    </div>
  );
}

/** After the project is created: its phases and rules. False when it did not work (it can be done
 * from the project settings). */
export async function applyChosenTemplate(workspaceSlug: string, projectId: string, key: string | null) {
  if (!key) return true;
  try {
    await atlantePhasesService.applyTemplate(workspaceSlug, projectId, key);
    return true;
  } catch {
    return false;
  }
}
