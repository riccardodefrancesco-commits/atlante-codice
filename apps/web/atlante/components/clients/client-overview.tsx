/**
 * Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { useMember } from "@/hooks/store/use-member";
import type { TAtlanteClient } from "@/atlante/types";
import { useAtlanteClientIssues } from "./use-client-issues";
import { personName } from "@/atlante/person-name";

type Props = { workspaceSlug: string; client: TAtlanteClient };

/** Client details, internal notes and work items by phase. */
export const AtlanteClientOverview = observer(function AtlanteClientOverview({ workspaceSlug, client }: Props) {
  const { t } = useTranslation();
  const { getUserDetails } = useMember();
  const { data } = useAtlanteClientIssues(workspaceSlug, client.id);
  const contact = client.internal_contact ? getUserDetails(client.internal_contact) : undefined;

  const counts = data?.counts;
  const numbers = [
    { key: "to_do", value: counts ? counts.backlog + counts.unstarted : undefined },
    { key: "in_progress", value: counts?.started },
    { key: "done", value: counts?.completed },
    { key: "overdue", value: data?.overdue, alert: true },
  ];

  const details: { label: string; value: React.ReactNode }[] = [
    { label: t("atlante.client.form.code"), value: client.code },
    {
      label: t("atlante.client.form.contact"),
      value: contact ? personName(contact) : t("atlante.client.overview.no_contact"),
    },
    {
      label: t("atlante.client.form.email"),
      value: client.email ? (
        <a className="text-accent-primary hover:underline" href={`mailto:${client.email}`}>
          {client.email}
        </a>
      ) : (
        ""
      ),
    },
    {
      label: t("atlante.client.form.website"),
      value: client.website ? (
        <a
          className="text-accent-primary hover:underline"
          href={client.website}
          target="_blank"
          rel="noopener noreferrer"
        >
          {client.website}
        </a>
      ) : (
        ""
      ),
    },
  ];

  return (
    <div className="grid gap-4 py-4 lg:grid-cols-2" data-atlante="client-overview">
      <section className="rounded-md border border-subtle p-4">
        <h4 className="mb-3 text-13 font-semibold text-secondary">{t("atlante.client.overview.work")}</h4>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {numbers.map(({ key, value, alert }) => (
            <div key={key} className="rounded-md bg-layer-1 p-3">
              <p
                className={cn("text-20 font-semibold text-primary", {
                  "text-danger-primary": alert && (value ?? 0) > 0,
                })}
              >
                {value ?? "-"}
              </p>
              <p className="text-12 text-tertiary">{t(`atlante.client.overview.${key}`)}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-md border border-subtle p-4">
        <h4 className="mb-3 text-13 font-semibold text-secondary">{t("atlante.client.overview.details")}</h4>
        <dl className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-2 text-13">
          {details.map(({ label, value }) => (
            <div key={label} className="contents">
              <dt className="text-tertiary">{label}</dt>
              <dd className="truncate text-primary">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section className="rounded-md border border-subtle p-4 lg:col-span-2">
        <h4 className="mb-2 text-13 font-semibold text-secondary">{t("atlante.client.overview.notes")}</h4>
        <p className="text-13 whitespace-pre-wrap text-primary">
          {client.internal_notes || <span className="text-tertiary">{t("atlante.client.overview.no_notes")}</span>}
        </p>
      </section>
    </div>
  );
});
