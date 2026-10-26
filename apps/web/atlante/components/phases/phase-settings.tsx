/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { SettingsHeading } from "@/components/settings/heading";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserPermissions } from "@/hooks/store/user";
import { atlantePhasesService, useAtlanteProjectTemplate } from "@/atlante/hooks/use-phases";

type Props = { workspaceSlug: string; projectId: string };

const errorMessage = (error: unknown) => (error as { error?: string } | undefined)?.error ?? "";

/** Below the list of phases: the template of the project, the people in its roles and the rule of
 * each phase. The table reads the names from the list above, so a renamed phase keeps its rule. */
export const AtlantePhaseSettings = observer(function AtlantePhaseSettings({ workspaceSlug, projectId }: Props) {
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const { getStateById, fetchProjectStates } = useProjectState();
  const { data, mutate } = useAtlanteProjectTemplate(workspaceSlug, projectId);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  if (!data) return null;
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  const current = data.templates.find((template) => template.key === data.template);

  const apply = async (key: string) => {
    setApplying(true);
    try {
      await mutate(await atlantePhasesService.applyTemplate(workspaceSlug, projectId, key), { revalidate: false });
      await fetchProjectStates(workspaceSlug, projectId);
      setToast({ type: "success", title: t("atlante.phases.toast.applied") });
    } catch (error) {
      setToast({ type: "error", title: t("atlante.phases.toast.error"), message: errorMessage(error) });
    } finally {
      setApplying(false);
      setConfirming(null);
    }
  };

  const setRole = async (role: string, memberIds: string[]) => {
    try {
      await mutate(await atlantePhasesService.setProjectRole(workspaceSlug, projectId, role, memberIds), {
        revalidate: false,
      });
    } catch (error) {
      setToast({ type: "error", title: t("atlante.phases.toast.error"), message: errorMessage(error) });
    }
  };

  return (
    <section className="mt-12 flex flex-col gap-6" data-atlante="phase-settings">
      <SettingsHeading
        variant="h4"
        title={t("atlante.phases.heading")}
        description={
          current ? t("atlante.phases.template_in_use", { name: current.name }) : t("atlante.phases.no_template")
        }
      />

      {current && isAdmin && data.missing_phases.length > 0 && (
        <div className="flex items-center justify-between gap-4 rounded-lg border border-subtle bg-layer-1 p-4">
          <p className="text-body-xs-regular text-secondary">
            {t("atlante.phases.missing_phases", { phases: data.missing_phases.join(", ") })}
          </p>
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            loading={applying}
            onClick={() => void apply(current.key)}
            label={t("atlante.phases.add_missing")}
          />
        </div>
      )}

      {!current && isAdmin && (
        <div className="flex flex-col gap-3 rounded-lg border border-subtle bg-layer-1 p-4">
          {data.templates.map((template) =>
            confirming === template.key ? (
              <div key={template.key} className="flex flex-col gap-3">
                <p className="text-body-xs-regular text-secondary">{t("atlante.phases.apply_explanation")}</p>
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="md"
                    stretch="auto"
                    loading={applying}
                    onClick={() => void apply(template.key)}
                    label={t("atlante.phases.apply_confirm", { name: template.name })}
                  />
                  <Button
                    variant="secondary"
                    size="md"
                    stretch="auto"
                    onClick={() => setConfirming(null)}
                    label={t("common.cancel")}
                  />
                </div>
              </div>
            ) : (
              <div key={template.key} className="flex items-center justify-between gap-4">
                <span className="text-body-sm-medium text-primary">{template.name}</span>
                <Button
                  variant="secondary"
                  size="md"
                  stretch="auto"
                  onClick={() => setConfirming(template.key)}
                  label={t("atlante.phases.apply")}
                />
              </div>
            )
          )}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <h5 className="text-body-sm-medium text-primary">{t("atlante.phases.roles_heading")}</h5>
        <p className="text-body-xs-regular text-tertiary">{t("atlante.phases.roles_description")}</p>
        <div className="divide-y divide-subtle-1 rounded-lg border border-subtle">
          {data.roles.map((role) => (
            <div
              key={role.key}
              className="flex items-center justify-between gap-4 px-4 py-2"
              data-atlante-role={role.key}
            >
              <span className="text-body-xs-medium text-secondary">{role.name}</span>
              <div className="w-1/2 max-w-80">
                <MemberSelect
                  value={role.member_ids}
                  onChange={(ids) => void setRole(role.key, ids)}
                  projectId={projectId}
                  multiple
                  variant="select-ghost-md"
                  placeholder={t("atlante.phases.nobody")}
                  disabled={!isAdmin}
                  tooltip={{ heading: role.name }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {data.phases.length > 0 && (
        <div className="flex flex-col gap-2">
          <h5 className="text-body-sm-medium text-primary">{t("atlante.phases.rules_heading")}</h5>
          <p className="text-body-xs-regular text-tertiary">{t("atlante.phases.rules_description")}</p>
          <div className="overflow-x-auto rounded-lg border border-subtle">
            <table className="w-full text-left text-body-xs-regular" data-atlante="phase-rules">
              <thead className="bg-layer-1 text-tertiary">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("atlante.phases.columns.phase")}</th>
                  <th className="px-4 py-2 font-medium">{t("atlante.phases.columns.role")}</th>
                  <th className="px-4 py-2 font-medium">{t("atlante.phases.columns.executor")}</th>
                  <th className="px-4 py-2 font-medium">{t("atlante.phases.columns.deadline")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-subtle-1 text-secondary">
                {data.phases.map((rule) => {
                  const state = getStateById(rule.state_id);
                  return (
                    <tr key={rule.state_id}>
                      <td className="px-4 py-2">
                        <span className="flex items-center gap-2 text-primary">
                          <span
                            className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                            style={{ backgroundColor: state?.color }}
                            aria-hidden
                          />
                          {state?.name ?? rule.phase_name}
                        </span>
                      </td>
                      <td className="px-4 py-2">{rule.phase_name}</td>
                      <td className="px-4 py-2">{rule.executor_name}</td>
                      <td className="px-4 py-2">{rule.deadline}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
});
